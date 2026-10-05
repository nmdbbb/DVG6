"""FastAPI app. Tài liệu OpenAPI: http://localhost:8000/docs (web/ sinh type từ /openapi.json)."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import Connection, text

from api.deps import get_conn
from api.routers import analysis, catalog, explore, meta

app = FastAPI(
    title="QTDL Warehouse API",
    version="0.1.0",
    description="Đọc schema analytics và meta. Mọi response bọc trong {data, meta}.",
)

app.include_router(meta.router)
app.include_router(catalog.router)
app.include_router(explore.router)
app.include_router(analysis.router)


class Health(BaseModel):
    status: str
    database: str
    schema_version: str | None


@app.get("/health", response_model=Health, tags=["health"])
def health(conn: Connection = Depends(get_conn)):
    version = conn.execute(text("select max(version) from meta.schema_version")).scalar()
    return {"status": "ok", "database": "ok", "schema_version": version}
