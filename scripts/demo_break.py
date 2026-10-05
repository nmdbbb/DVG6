"""Cố tình làm hỏng dữ liệu để chứng minh quality là cổng chặn (nghiệm thu M3).

Chèn vào core.fct_main một dòng trỏ tới entity_key không tồn tại. Sau đó:
    make quality     -> exit 1 (fct_main_no_orphan_entity + dbt relationships fail)
    make transform   -> dbt dựng lại fct_main, dòng hỏng biến mất
    make quality     -> xanh trở lại
"""

from __future__ import annotations

import typer

from common.db import connect


def main() -> None:
    with connect("etl_writer") as conn:
        conn.execute(
            "insert into core.fct_main (record_id, entity_key, event_date, measure_value, batch_id) "
            "select 'BROKEN-' || md5(random()::text), 999999, current_date, 1, batch_id "
            "from core.fct_main limit 1"
        )
        conn.commit()
    typer.secho(
        "Đã chèn 1 dòng mồ côi vào core.fct_main. Chạy `make quality` để thấy pipeline bị chặn.",
        fg="yellow",
    )


if __name__ == "__main__":
    typer.run(main)
