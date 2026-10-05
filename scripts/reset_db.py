"""Xóa toàn bộ schema của warehouse để dựng lại từ số không (make reset).

Role giữ nguyên (thuộc cấp cluster); migrate.py sẽ cấp lại quyền.
File gốc trong data/raw cũng giữ nguyên — đó là bằng chứng của nguồn.
"""

from __future__ import annotations

import typer

from common.db import connect

SCHEMAS = ["analytics", "core", "staging", "raw", "meta"]


def main() -> None:
    with connect("admin", autocommit=True) as conn:
        for schema in SCHEMAS:
            conn.execute(f'drop schema if exists "{schema}" cascade')
            typer.echo(f"  dropped  {schema}")
    typer.echo("Warehouse trống. Chạy make migrate để dựng lại.")


if __name__ == "__main__":
    typer.run(main)
