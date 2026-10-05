"""Chạy check chất lượng, ghi meta.quality_run, profile bảng, và CHẶN pipeline khi có lỗi.

    python -m quality.runner                    # check trong rules.yml
    python -m quality.runner --with-dbt         # + dbt test (make quality dùng lệnh này)
    python -m quality.runner --severity error   # chỉ check mức error

Exit code 1 nếu có bất kỳ check severity=error nào fail. Kết quả mới nhất cũng được ghi ra
docs/quality_report.md.
"""

from __future__ import annotations

import operator
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import typer
import yaml
from psycopg import sql

from common.db import REPO_ROOT, connect

RULES_FILE = Path(__file__).with_name("rules.yml")
REPORT_FILE = REPO_ROOT / "docs" / "quality_report.md"
DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", str(REPO_ROOT / "transform"))
PROFILED_SCHEMAS = ("raw", "staging", "core", "analytics", "meta")

OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}

app = typer.Typer(add_completion=False)


@dataclass
class CheckResult:
    name: str
    source: str  # rules | dbt
    severity: str  # error | warning
    passed: bool
    observed: Decimal | float | int | None
    threshold: str | None
    message: str | None = None


def load_rules() -> list[dict]:
    rules = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8")) or []
    for rule in rules:
        missing = {"name", "severity", "sql", "expect"} - set(rule)
        if missing:
            raise SystemExit(f"rules.yml: check {rule.get('name')} thiếu {sorted(missing)}")
        if rule["severity"] not in ("error", "warning"):
            raise SystemExit(f"rules.yml: severity không hợp lệ ở {rule['name']}")
        if rule["expect"]["operator"] not in OPS:
            raise SystemExit(f"rules.yml: operator không hợp lệ ở {rule['name']}")
    return rules


def run_rules(conn, rules: list[dict]) -> list[CheckResult]:
    results = []
    for rule in rules:
        op, value = rule["expect"]["operator"], rule["expect"]["value"]
        threshold = f"{op} {value}"
        try:
            with conn.transaction():  # savepoint: một check lỗi SQL không làm hỏng các check khác
                row = conn.execute(rule["sql"]).fetchone()
            observed = row[0] if row else None
            passed = observed is not None and OPS[op](Decimal(str(observed)), Decimal(str(value)))
            message = None if observed is not None else "Câu SQL trả về NULL"
        except Exception as exc:  # noqa: BLE001 — lỗi SQL là một check fail, không phải crash
            observed, passed, message = None, False, f"{type(exc).__name__}: {exc}".strip()
        results.append(
            CheckResult(
                rule["name"], "rules", rule["severity"], passed, observed, threshold, message
            )
        )
    return results


def run_dbt_tests() -> list[CheckResult]:
    from dbt.cli.main import dbtRunner

    res = dbtRunner().invoke(
        ["test", "--project-dir", DBT_PROJECT_DIR, "--profiles-dir", DBT_PROJECT_DIR, "--quiet"]
    )
    if res.result is None or res.exception is not None:
        return [CheckResult("dbt:test", "dbt", "error", False, None, None, str(res.exception))]

    results = []
    for r in res.result.results:
        severity = "warning" if str(r.node.config.severity).lower() == "warn" else "error"
        status = str(r.status).lower()
        results.append(
            CheckResult(
                name=f"dbt:{r.node.name}",
                source="dbt",
                severity=severity,
                passed=status == "pass",
                observed=r.failures,
                threshold="== 0",
                message=None if status == "pass" else (r.message or status),
            )
        )
    return results


def profile_tables(conn, run_id: str) -> None:
    tables = conn.execute(
        """
        select n.nspname, c.relname, array_agg(a.attname order by a.attnum)
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        join pg_attribute a on a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped
        where n.nspname = any(%s) and c.relkind in ('r', 'v', 'm', 'p')
        group by 1, 2 order by 1, 2
        """,
        (list(PROFILED_SCHEMAS),),
    ).fetchall()

    for schema, table, columns in tables:
        query = sql.SQL("select count(*), {} from {}").format(
            sql.SQL(", ").join(sql.SQL("count({})").format(sql.Identifier(c)) for c in columns),
            sql.Identifier(schema, table),
        )
        counts = conn.execute(query).fetchone()
        total = counts[0]
        conn.execute(
            "insert into meta.table_profile (run_id, schema_name, table_name, row_count) "
            "values (%s, %s, %s, %s)",
            (run_id, schema, table, total),
        )
        with conn.cursor() as cur:
            cur.executemany(
                "insert into meta.column_profile "
                "(run_id, schema_name, table_name, column_name, null_count, null_rate) "
                "values (%s, %s, %s, %s, %s, %s)",
                [
                    (run_id, schema, table, col, total - nn, (total - nn) / total if total else 0)
                    for col, nn in zip(columns, counts[1:], strict=True)
                ],
            )


def write_report(run_id: str, results: list[CheckResult]) -> None:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    failed_errors = sum(1 for r in results if r.severity == "error" and not r.passed)
    failed_warnings = sum(1 for r in results if r.severity == "warning" and not r.passed)
    lines = [
        "# Báo cáo chất lượng dữ liệu",
        "",
        "> File sinh tự động bởi `make quality` (quality/runner.py). Không sửa tay.",
        "",
        f"- Lần chạy: `{run_id}` lúc {now}",
        f"- Tổng check: {len(results)} · error fail: **{failed_errors}** · "
        f"warning fail: **{failed_warnings}**",
        f"- Kết luận: {'**CHẶN** — pipeline dừng' if failed_errors else 'Đạt — pipeline được đi tiếp'}",
        "",
        "| Kết quả | Mức | Nguồn | Check | Đo được | Ngưỡng |",
        "|---|---|---|---|---|---|",
    ]
    order = sorted(results, key=lambda r: (r.passed, r.severity != "error", r.name))
    for r in order:
        mark = "PASS" if r.passed else "FAIL"
        observed = "" if r.observed is None else _fmt(r.observed)
        lines.append(
            f"| {mark} | {r.severity} | {r.source} | `{r.name}` | {observed} | {r.threshold or ''} |"
        )
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt(value) -> str:
    d = Decimal(str(value))
    return f"{d:.4f}".rstrip("0").rstrip(".") if d != d.to_integral() else str(int(d))


@app.command()
def main(
    severity: str = typer.Option("all", help="error | warning | all"),
    with_dbt: bool = typer.Option(False, "--with-dbt", help="Chạy thêm dbt test."),
    profile: bool = typer.Option(True, help="Đo số dòng/tỉ lệ NULL cho Overview và Catalog."),
) -> None:
    rules = load_rules()
    if severity != "all":
        rules = [r for r in rules if r["severity"] == severity]

    results: list[CheckResult] = run_dbt_tests() if with_dbt else []
    run_id = str(uuid.uuid4())

    with connect("etl_writer") as conn:
        results = run_rules(conn, rules) + results
        batch = conn.execute(
            "select batch_id from meta.ingestion_batch where status = 'success' "
            "order by finished_at desc limit 1"
        ).fetchone()
        with conn.cursor() as cur:
            cur.executemany(
                "insert into meta.quality_run (run_id, batch_id, check_name, check_source, "
                "severity, passed, observed_value, threshold, message) "
                "values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [
                    (
                        run_id,
                        batch[0] if batch else None,
                        r.name,
                        r.source,
                        r.severity,
                        r.passed,
                        r.observed,
                        r.threshold,
                        r.message,
                    )
                    for r in results
                ],
            )
        if profile:
            profile_tables(conn, run_id)
        conn.commit()

    write_report(run_id, results)

    for r in sorted(results, key=lambda r: (r.passed, r.name)):
        color = "green" if r.passed else ("red" if r.severity == "error" else "yellow")
        observed = "-" if r.observed is None else _fmt(r.observed)
        typer.secho(
            f"  {'PASS' if r.passed else 'FAIL'}  {r.severity:7s}  {r.name:60s} "
            f"{observed:>10s}  {r.threshold or ''}",
            fg=color,
        )
        if r.message and not r.passed:
            typer.secho(f"        {r.message.splitlines()[0][:160]}", fg=color)

    errors = [r for r in results if r.severity == "error" and not r.passed]
    warnings = [r for r in results if r.severity == "warning" and not r.passed]
    typer.echo(
        f"\nrun_id={run_id}: {len(results)} check, {len(errors)} error, {len(warnings)} warning"
    )
    if errors:
        typer.secho("QUALITY GATE FAILED — pipeline dừng.", fg="red", bold=True)
        sys.exit(1)
    typer.secho("Quality gate passed.", fg="green", bold=True)


if __name__ == "__main__":
    app()
