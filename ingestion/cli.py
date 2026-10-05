"""CLI nạp dữ liệu.

python -m ingestion.cli list-sources
python -m ingestion.cli run --source source_demo --since 2022-01-01 --limit 1000
python -m ingestion.cli run --source source_demo --dry-run
python -m ingestion.cli run-all
"""

from __future__ import annotations

from datetime import date, datetime

import typer

from ingestion import loader, registry

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _parse_since(value: str | None) -> date | None:
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def _report(result: loader.BatchResult) -> None:
    color = "green" if result.status == "success" else "yellow"
    typer.secho(
        f"[{result.source}] {result.status}: fetched={result.rows_fetched} "
        f"new_rows={result.row_count} batch={result.batch_id} file={result.raw_file}",
        fg=color,
    )


@app.command("list-sources")
def list_sources() -> None:
    for name, cls in sorted(registry.SOURCES.items()):
        typer.echo(f"{name:20s} -> {cls.raw_table}")


@app.command()
def run(
    source: str = typer.Option(..., "--source", "-s", help="Tên nguồn trong registry."),
    since: str = typer.Option(None, help="Chỉ lấy bản ghi từ ngày này (YYYY-MM-DD)."),
    limit: int = typer.Option(None, help="Giới hạn số bản ghi, để chạy thử nhanh."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Chỉ đếm bản ghi, không ghi gì."),
) -> None:
    _report(loader.run(registry.get(source), _parse_since(since), limit, dry_run))


@app.command("run-all")
def run_all(
    since: str = typer.Option(None, help="YYYY-MM-DD"),
    limit: int = typer.Option(None),
) -> None:
    for name in sorted(registry.SOURCES):
        _report(loader.run(registry.get(name), _parse_since(since), limit))


if __name__ == "__main__":
    app()
