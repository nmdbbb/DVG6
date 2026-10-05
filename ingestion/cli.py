"""CLI nạp dữ liệu.

python -m ingestion.cli list-sources
python -m ingestion.cli run --source source_demo --since 2022-01-01 --limit 1000
python -m ingestion.cli run --source source_demo --endpoint mock
python -m ingestion.cli run --source source_demo --dry-run
python -m ingestion.cli run-all

--endpoint mặc định lấy từ biến môi trường SOURCE_MODE (live nếu không đặt), nên
`make ingest SOURCE_MODE=mock` chuyển cả pipeline sang mock mà không đổi lệnh.
"""

from __future__ import annotations

import os
from datetime import date, datetime

import typer

from ingestion import loader, registry
from ingestion.base import SOURCE_MODES

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _parse_since(value: str | None) -> date | None:
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def _mode(value: str | None, since: str | None = None) -> str:
    mode = (value or os.environ.get("SOURCE_MODE") or "live").strip().lower()
    if mode not in SOURCE_MODES:
        raise typer.BadParameter(f"--endpoint / SOURCE_MODE phải là {' | '.join(SOURCE_MODES)}")
    if mode == "mock" and since:
        # Kiểm trước khi tạo lô, để không sinh lô failed vô nghĩa.
        raise typer.BadParameter(
            "mock phát lại snapshot live gần nhất, không lọc --since. "
            "Chạy live với --since trước, rồi mới chạy mock."
        )
    return mode


ENDPOINT_HELP = "live (nguồn thật) | mock (mock_server). Mặc định: $SOURCE_MODE, không có thì live."


def _report(result: loader.BatchResult) -> None:
    color = "green" if result.status == "success" else "yellow"
    typer.secho(
        f"[{result.source}] {result.mode} {result.status}: fetched={result.rows_fetched} "
        f"new_rows={result.row_count} batch={result.batch_id}"
        + (f" snapshot={result.snapshot_dir}" if result.snapshot_dir else ""),
        fg=color,
    )


@app.command("list-sources")
def list_sources() -> None:
    for name, cls in sorted(registry.SOURCES.items()):
        typer.echo(f"{name:20s} -> {cls.raw_table}  (mock: {cls.mock_format})")


@app.command()
def run(
    source: str = typer.Option(..., "--source", "-s", help="Tên nguồn trong registry."),
    endpoint: str = typer.Option(None, "--endpoint", "-e", help=ENDPOINT_HELP),
    since: str = typer.Option(None, help="Chỉ lấy bản ghi từ ngày này (YYYY-MM-DD). Chỉ live."),
    limit: int = typer.Option(None, help="Giới hạn số bản ghi, để chạy thử nhanh."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Chỉ đếm bản ghi, không ghi gì."),
) -> None:
    _report(
        loader.run(
            registry.get(source), _parse_since(since), limit, dry_run, _mode(endpoint, since)
        )
    )


@app.command("run-all")
def run_all(
    endpoint: str = typer.Option(None, "--endpoint", "-e", help=ENDPOINT_HELP),
    since: str = typer.Option(None, help="YYYY-MM-DD"),
    limit: int = typer.Option(None),
) -> None:
    mode = _mode(endpoint, since)
    for name in sorted(registry.SOURCES):
        _report(loader.run(registry.get(name), _parse_since(since), limit, mode=mode))


if __name__ == "__main__":
    app()
