import psycopg
import pytest

from api.tests.conftest import assert_envelope
from common.db import conninfo


def test_tables_have_comments(client):
    data = assert_envelope(client.get("/catalog/tables").json())
    by_name = {f"{t['schema_name']}.{t['table_name']}": t for t in data}
    for name in ["meta.ingestion_batch", "raw.source_demo_records", "core.fct_main"]:
        assert name in by_name
        assert by_name[name]["comment"], f"{name} thiếu COMMENT ON"


def test_tables_filter_by_schema(client):
    data = assert_envelope(client.get("/catalog/tables", params={"schema": "core"}).json())
    assert data and all(t["schema_name"] == "core" for t in data)


def test_columns_of_fact(client):
    data = assert_envelope(client.get("/catalog/tables/core.fct_main/columns").json())
    cols = {c["column_name"]: c for c in data}
    assert {"record_id", "entity_key", "measure_value"} <= set(cols)
    assert cols["record_id"]["comment"]
    assert cols["measure_value"]["null_rate"] is not None


@pytest.mark.parametrize("name", ["core.does_not_exist", "pg_catalog.pg_class", "fct_main"])
def test_columns_unknown_table_404(client, name):
    assert client.get(f"/catalog/tables/{name}/columns").status_code == 404


def test_api_reader_cannot_read_raw_or_core():
    """Phân quyền là thật: role của API không SELECT được dữ liệu raw/core."""
    with psycopg.connect(conninfo("api_reader")) as conn:
        for table in ["raw.source_demo_records", "core.fct_main"]:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(f"select 1 from {table} limit 1")
            conn.rollback()
