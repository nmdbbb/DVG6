"""So khớp lô live và lô mock của một nguồn — nghiệm thu đường dự phòng mock_server.

    python -m scripts.compare_batches --source source_demo
    python -m scripts.compare_batches --live <batch_id> --mock <batch_id>

Mặc định lấy lô success mới nhất của mỗi mode. Đạt khi hai lô có cùng số dòng, cùng tập
_row_hash, và mọi _row_hash đều có dòng trong bảng raw. Exit 1 nếu lệch.
"""

from __future__ import annotations

import sys

import typer
from psycopg import sql

from common.db import connect
from ingestion import registry

app = typer.Typer(add_completion=False)


def _latest(conn, source: str, mode: str) -> str | None:
    row = conn.execute(
        "select batch_id::text from meta.ingestion_batch where source_name = %s "
        "and source_mode = %s and status = 'success' order by started_at desc limit 1",
        (source, mode),
    ).fetchone()
    return row[0] if row else None


@app.command()
def main(
    source: str = typer.Option("source_demo", "--source", "-s"),
    live: str = typer.Option(None, "--live", help="batch_id lô live (mặc định: mới nhất)."),
    mock: str = typer.Option(None, "--mock", help="batch_id lô mock (mặc định: mới nhất)."),
) -> None:
    schema, table = registry.get(source).raw_table.split(".")
    raw = sql.Identifier(schema, table)

    with connect("etl_writer") as conn:
        live = live or _latest(conn, source, "live")
        mock = mock or _latest(conn, source, "mock")
        if not live or not mock:
            typer.secho(
                f"Thiếu lô: live={live} mock={mock}. Chạy `make ingest SOURCE_MODE=live` "
                "rồi `make ingest SOURCE_MODE=mock`.",
                fg="red",
            )
            sys.exit(1)

        def stats(batch: str, other: str) -> dict:
            fetched, mode = conn.execute(
                "select rows_fetched, source_mode from meta.ingestion_batch where batch_id = %s",
                (batch,),
            ).fetchone()
            hashes = conn.execute(
                "select count(*) from meta.ingestion_batch_row where batch_id = %s", (batch,)
            ).fetchone()[0]
            in_raw = conn.execute(
                sql.SQL(
                    "select count(*) from {raw} r join meta.ingestion_batch_row b "
                    "on b.row_hash = r._row_hash where b.batch_id = %s"
                ).format(raw=raw),
                (batch,),
            ).fetchone()[0]
            only_here = conn.execute(
                "select count(*) from (select row_hash from meta.ingestion_batch_row "
                "where batch_id = %s except select row_hash from meta.ingestion_batch_row "
                "where batch_id = %s) d",
                (batch, other),
            ).fetchone()[0]
            return {
                "batch_id": batch,
                "source_mode": mode,
                "rows_fetched": fetched,
                "distinct _row_hash": hashes,
                "dòng trong raw": in_raw,
                "chỉ có ở lô này": only_here,
            }

        a, b = stats(live, mock), stats(mock, live)

    typer.echo(f"{'':22s} {'LIVE':>38s} {'MOCK':>38s}")
    for key in a:
        typer.echo(f"{key:22s} {a[key]!s:>38s} {b[key]!s:>38s}")

    ok = (
        a["rows_fetched"] == b["rows_fetched"]
        and a["distinct _row_hash"] == b["distinct _row_hash"] == a["dòng trong raw"]
        and b["distinct _row_hash"] == b["dòng trong raw"]
        and a["chỉ có ở lô này"] == b["chỉ có ở lô này"] == 0
    )
    if not ok:
        typer.secho("LỆCH: lô mock không trùng khớp lô live.", fg="red", bold=True)
        sys.exit(1)
    typer.secho(
        f"KHỚP: {a['distinct _row_hash']} bản ghi, cùng tập _row_hash, đều có trong {schema}.{table}.",
        fg="green",
        bold=True,
    )


if __name__ == "__main__":
    app()
