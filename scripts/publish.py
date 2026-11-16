"""Đẩy `core`, `analytics`, `meta` từ warehouse local lên kho Postgres dùng chung.

Vì sao chỉ ba schema này (decision #35): `raw` chứa `SYMPTOM_TEXT` và cột `_payload` nên nặng
hơn 1 GB, vượt gói miễn phí 500 MB của Neon/Supabase. `staging` chỉ là view dựng lại được từ raw.
Dashboard vốn chỉ đọc `analytics` + `meta` (role `api_reader`), còn notebook đọc thêm `core`.

    make publish              # đẩy lên $SHARED_DATABASE_URL
    make publish DRY_RUN=1    # chỉ in ra sẽ làm gì, không ghi

Kho chung là **bản sao chỉ-đọc** của warehouse local: mỗi lần publish thay toàn bộ ba schema.
Không ai sửa trực tiếp trên đó; muốn đổi số liệu thì chạy lại pipeline local rồi publish lại.

Cổng chất lượng (decision #40): chỉ publish khi lần `make quality` gần nhất không có check
`severity = error` nào fail, và lần chạy đó mới hơn lô nạp gần nhất. Trước đây đây chỉ là quy ước
trong runbook; giờ lệnh tự từ chối.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg
import typer
from psycopg import sql

from common.db import assert_local, conninfo, is_local_host

SCHEMAS = ("core", "analytics", "meta")

# Một dòng cho mỗi bản ghi mỗi lô — chỉ dùng cho `make mock-check` ở local, và với VAERS là
# vài triệu dòng. Không đẩy lên kho chung để tiết kiệm dung lượng.
EXCLUDE_TABLES = ("meta.ingestion_batch_row",)

app = typer.Typer(add_completion=False)


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, text=True, capture_output=True, **kw)
    if proc.returncode != 0:
        typer.secho(f"Lệnh thất bại: {cmd[0]}", fg="red", err=True)
        typer.echo((proc.stderr or proc.stdout or "").strip()[:4000], err=True)
        sys.exit(proc.returncode)
    return proc


def _target_url() -> str:
    url = os.environ.get("SHARED_DATABASE_URL", "").strip()
    if not url:
        raise SystemExit(
            "Thiếu SHARED_DATABASE_URL.\n"
            "Lấy connection string của kho chung (Neon/Supabase) và đặt vào .env:\n"
            "  SHARED_DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require"
        )
    return url


def _target_host(url: str) -> str:
    try:
        return psycopg.conninfo.conninfo_to_dict(url).get("host", "") or ""
    except psycopg.ProgrammingError as exc:
        raise SystemExit(f"SHARED_DATABASE_URL không hợp lệ: {exc}") from None


def quality_gate(dsn: str) -> tuple[bool, str]:
    """(được publish?, lý do). Đọc meta của warehouse local.

    Từ chối khi: chưa từng chạy quality; lần chạy gần nhất có check error fail; hoặc đã nạp lô mới
    sau lần chạy quality đó (số liệu sắp publish chưa được kiểm).
    """
    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            """
            with last_run as (
                select run_id, max(ran_at) as ran_at
                from meta.quality_run
                group by run_id
                order by max(ran_at) desc
                limit 1
            )
            select
                l.run_id::text,
                l.ran_at,
                (select count(*) from meta.quality_run q
                  where q.run_id = l.run_id and q.severity = 'error' and not q.passed),
                (select count(*) from meta.quality_run q where q.run_id = l.run_id),
                (select max(finished_at) from meta.ingestion_batch where status = 'success')
            from last_run l
            """
        ).fetchone()
    if row is None:
        return False, "chưa có lần chạy quality nào — chạy `make quality` trước."
    run_id, ran_at, n_error, n_checks, last_batch = row
    if n_error:
        return False, (
            f"lần chạy quality gần nhất ({run_id[:8]}, {ran_at:%Y-%m-%d %H:%M}) có {n_error} check "
            "error fail. Sửa dữ liệu/model rồi chạy lại `make quality`."
        )
    if last_batch is not None and last_batch > ran_at:
        return False, (
            f"có lô nạp mới ({last_batch:%Y-%m-%d %H:%M}) sau lần chạy quality gần nhất "
            f"({ran_at:%Y-%m-%d %H:%M}). Chạy `make transform && make quality` trước."
        )
    return (
        True,
        f"quality {run_id[:8]} lúc {ran_at:%Y-%m-%d %H:%M}: {n_checks} check, 0 error fail.",
    )


def _server_version(dsn: str) -> int:
    with psycopg.connect(dsn) as conn:
        return int(conn.execute("show server_version_num").fetchone()[0])


# pg_dump 17 phát `SET transaction_timeout = 0;` — tham số chỉ có từ PostgreSQL 17, server cũ hơn
# báo lỗi "unrecognized configuration parameter". Bỏ dòng này khi đích chạy bản dưới 17.
_PG17_ONLY_SETS = ("SET transaction_timeout",)


def _strip_newer_than_target(dump: Path, target_version: int) -> int:
    if target_version >= 170000:
        return 0
    lines = dump.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [ln for ln in lines if not ln.startswith(_PG17_ONLY_SETS)]
    dump.write_text("".join(kept), encoding="utf-8")
    return len(lines) - len(kept)


def _counts(dsn: str) -> dict[str, int]:
    """Số dòng từng bảng trong ba schema, để so hai bên sau khi publish."""
    out: dict[str, int] = {}
    with psycopg.connect(dsn) as conn:
        tables = conn.execute(
            """
            select n.nspname, c.relname
            from pg_class c join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = any(%s) and c.relkind in ('r', 'p')
            order by 1, 2
            """,
            (list(SCHEMAS),),
        ).fetchall()
        for schema, table in tables:
            name = f"{schema}.{table}"
            if name in EXCLUDE_TABLES:
                continue
            out[name] = conn.execute(f'select count(*) from "{schema}"."{table}"').fetchone()[0]
    return out


GRANTS = """
do $$
begin
    if not exists (select from pg_roles where rolname = 'api_reader') then
        create role api_reader login;
    end if;
    if not exists (select from pg_roles where rolname = 'analyst') then
        create role analyst login;
    end if;
end
$$;

grant usage on schema analytics, meta to api_reader;
grant select on all tables in schema analytics, meta to api_reader;

grant usage on schema core, analytics to analyst;
grant select on all tables in schema core, analytics to analyst;
"""


def _apply_grants(target: str) -> None:
    """Tạo role chỉ-đọc trên kho chung và cấp quyền. Chạy lại được nhiều lần."""
    with psycopg.connect(target, autocommit=True) as conn:
        conn.execute(GRANTS)
        for role, env in (("api_reader", "API_READER_PASSWORD"), ("analyst", "ANALYST_PASSWORD")):
            password = sql.Literal(os.environ.get(env, "change_me")).as_string(conn)
            conn.execute(f"alter role {role} with login password {password}")


@app.command()
def main(
    dry_run: bool = typer.Option(False, "--dry-run", help="Chỉ in kế hoạch, không ghi gì."),
    allow_local_target: bool = typer.Option(
        False,
        "--allow-local-target",
        help="Cho phép đích là Postgres local. Chỉ dùng để tự kiểm thử đường publish.",
    ),
    skip_quality_gate: bool = typer.Option(
        False,
        "--skip-quality-gate",
        help="Bỏ qua cổng chất lượng. Chỉ dùng khi sự cố, và phải ghi decision_log.",
    ),
) -> None:
    assert_local("publish (nguồn phải là warehouse local)")
    target = _target_url()
    host = _target_host(target)
    if is_local_host(host) and not allow_local_target:
        raise SystemExit(
            f"TỪ CHỐI: SHARED_DATABASE_URL trỏ vào host local ({host!r}).\n"
            "Kho chung phải là một Postgres khác. Thêm --allow-local-target nếu đang tự kiểm thử."
        )

    source = conninfo("admin")
    excludes = [f"--exclude-table={t}" for t in EXCLUDE_TABLES]
    schema_args = [f"--schema={s}" for s in SCHEMAS]

    typer.echo(f"Nguồn : warehouse local ({os.environ.get('POSTGRES_HOST', 'localhost')})")
    typer.echo(f"Đích  : {host}")
    typer.echo(f"Schema: {', '.join(SCHEMAS)}  (bỏ qua {', '.join(EXCLUDE_TABLES)})")

    ok, reason = quality_gate(source)
    if ok:
        typer.secho(f"Cổng   : ĐẠT — {reason}", fg="green")
    elif skip_quality_gate:
        typer.secho(f"Cổng   : BỎ QUA (--skip-quality-gate) — {reason}", fg="yellow")
    elif dry_run:
        typer.secho(f"Cổng   : SẼ CHẶN — {reason}", fg="red")
    else:
        typer.secho(f"TỪ CHỐI publish: {reason}", fg="red", err=True)
        sys.exit(1)

    before = _counts(source)
    typer.echo(f"Local có {len(before)} bảng, {sum(before.values()):,} dòng.")
    if dry_run:
        for name, n in before.items():
            typer.echo(f"  {name:40s} {n:>12,}")
        typer.secho("--dry-run: không ghi gì lên kho chung.", fg="yellow")
        return

    with tempfile.TemporaryDirectory() as tmp:
        dump = Path(tmp) / "publish.sql"
        typer.echo("pg_dump…")
        _run(
            [
                "pg_dump",
                "--dbname",
                source,
                *schema_args,
                *excludes,
                "--no-owner",
                "--no-privileges",
                "--file",
                str(dump),
            ]
        )
        size_mb = dump.stat().st_size / 1024 / 1024
        target_version = _server_version(target)
        stripped = _strip_newer_than_target(dump, target_version)
        note = f", bỏ {stripped} dòng SET chỉ có ở PG17" if stripped else ""
        typer.echo(f"  dump {size_mb:.1f} MB · đích PostgreSQL {target_version // 10000}{note}")

        # Thay toàn bộ: kho chung là bản sao của local, không phải nơi tích lũy riêng.
        typer.echo("Xóa schema cũ trên kho chung…")
        drops = "".join(f'drop schema if exists "{s}" cascade;\n' for s in SCHEMAS)
        _run(["psql", "--dbname", target, "-v", "ON_ERROR_STOP=1", "-q", "-c", drops])

        typer.echo("Nạp dữ liệu…")
        _run(["psql", "--dbname", target, "-v", "ON_ERROR_STOP=1", "-q", "--file", str(dump)])

    typer.echo("Cấp quyền role chỉ-đọc…")
    _apply_grants(target)

    after = _counts(target)
    missing = sorted(set(before) - set(after))
    extra = sorted(set(after) - set(before))
    diff = {k: (before[k], after[k]) for k in before if k in after and before[k] != after[k]}

    if missing or extra or diff:
        typer.secho("LỆCH giữa local và kho chung:", fg="red", bold=True)
        for name in missing:
            typer.echo(f"  thiếu trên kho chung: {name}")
        for name in extra:
            typer.echo(f"  thừa trên kho chung: {name}")
        for name, (a, b) in diff.items():
            typer.echo(f"  {name}: local {a:,} != kho chung {b:,}")
        sys.exit(1)

    typer.secho(
        f"KHỚP: {len(after)} bảng, {sum(after.values()):,} dòng đã lên kho chung.",
        fg="green",
        bold=True,
    )


if __name__ == "__main__":
    app()
