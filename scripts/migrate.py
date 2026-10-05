"""Áp dụng migration trong db/migrations theo thứ tự, rồi cấp quyền theo db/roles.sql.

- Mỗi file NNN_*.sql chạy đúng một lần, trong một transaction, rồi ghi vào meta.schema_version.
- Checksum lệch nghĩa là có người sửa file đã áp dụng: báo lỗi, exit 1, không chạy gì thêm.
  Muốn đổi schema thì viết file mới với số lớn hơn.

    python -m scripts.migrate            # áp dụng
    python -m scripts.migrate --status   # chỉ in trạng thái
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import typer
from psycopg import sql

from common.db import REPO_ROOT, connect

MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"
ROLES_FILE = REPO_ROOT / "db" / "roles.sql"

BOOTSTRAP = """
create schema if not exists meta;
create table if not exists meta.schema_version (
    version    text primary key,
    filename   text not null,
    checksum   text not null,
    applied_at timestamptz not null default now()
);
comment on table meta.schema_version is
    'Migration đã áp dụng. Ghi bởi scripts/migrate.py, checksum dùng để phát hiện file cũ bị sửa.';
"""

app = typer.Typer(add_completion=False)


def checksum(path: Path) -> str:
    # Chuẩn hóa xuống dòng để checkout CRLF trên Windows không làm lệch checksum.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def migration_files() -> list[tuple[str, Path]]:
    files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
    versions = [f.name.split("_", 1)[0] for f in files]
    dupes = {v for v in versions if versions.count(v) > 1}
    if dupes:
        raise SystemExit(f"Trùng số migration: {sorted(dupes)}")
    return list(zip(versions, files, strict=True))


def apply_roles(conn) -> None:
    text = ROLES_FILE.read_text(encoding="utf-8")
    for placeholder, env in [
        ("__ETL_WRITER_PASSWORD__", "ETL_WRITER_PASSWORD"),
        ("__API_READER_PASSWORD__", "API_READER_PASSWORD"),
        ("__ANALYST_PASSWORD__", "ANALYST_PASSWORD"),
    ]:
        literal = sql.Literal(os.environ.get(env, "change_me")).as_string(conn)
        text = text.replace(placeholder, literal)
    with conn.transaction():
        conn.execute(text)


@app.command()
def main(status: bool = typer.Option(False, "--status", help="Chỉ in trạng thái, không áp dụng.")):
    with connect("admin", autocommit=True) as conn:
        conn.execute(BOOTSTRAP)
        applied = dict(conn.execute("select version, checksum from meta.schema_version").fetchall())

        pending: list[tuple[str, Path, str]] = []
        for version, path in migration_files():
            digest = checksum(path)
            if version in applied:
                if applied[version] != digest:
                    typer.secho(
                        f"LỖI: {path.name} đã áp dụng nhưng nội dung bị sửa (checksum lệch). "
                        "Không sửa migration cũ — hãy viết file mới.",
                        fg="red",
                        err=True,
                    )
                    sys.exit(1)
                typer.echo(f"  ok       {path.name}")
            else:
                pending.append((version, path, digest))
                typer.echo(f"  pending  {path.name}")

        if status:
            return

        for version, path, digest in pending:
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute(
                    "insert into meta.schema_version (version, filename, checksum) "
                    "values (%s, %s, %s)",
                    (version, path.name, digest),
                )
            typer.secho(f"  applied  {path.name}", fg="green")

        apply_roles(conn)
        total = conn.execute("select count(*) from meta.schema_version").fetchone()[0]
        typer.echo(f"Migration xong: {len(pending)} mới, {total} tổng. Đã cấp lại quyền role.")


if __name__ == "__main__":
    app()
