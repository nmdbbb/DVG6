"""Đăng ký và kiểm checksum file nguồn tải tay trong data/landing/.

    python -m scripts.landing register --source vaers [--by "Tên"]
    python -m scripts.landing verify

- `register` quét data/landing/<source>/, tính sha256 từng file, thêm một dòng vào
  docs/sources_landing.md cho file chưa có. File đổi nội dung thì thêm dòng mới, không sửa dòng cũ.
- `verify` so sha256 hiện tại của mọi file đã đăng ký với dòng mới nhất của file đó.
  Lệch hoặc mất file thì in lý do và exit 1; `make ingest` gọi lệnh này trước khi nạp.
"""

from __future__ import annotations

import getpass
import hashlib
import os
import re
import sys
from datetime import date
from pathlib import Path

import typer

REPO_ROOT = Path(__file__).resolve().parents[1]
LANDING_DIR = REPO_ROOT / "data" / "landing"
LANDING_DOC = REPO_ROOT / "docs" / "sources_landing.md"

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
IGNORED_NAMES = {".gitkeep"}

app = typer.Typer(add_completion=False)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_rows(doc: Path) -> list[dict]:
    """Đọc các dòng dữ liệu của bảng; bỏ qua dòng trống, dòng tiêu đề và dòng không có sha256."""
    rows = []
    for line in doc.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 7:
            continue
        sha = cells[6].strip("`")
        if not SHA_RE.match(sha):
            continue
        rows.append(
            {
                "n": int(cells[0]) if cells[0].isdigit() else 0,
                "source": cells[1],
                "path": cells[2].strip("`"),
                "sha256": sha,
            }
        )
    return rows


def latest_by_path(rows: list[dict]) -> dict[str, dict]:
    return {r["path"]: r for r in rows}  # dòng sau ghi đè dòng trước


def _rel(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def register(
    source: str, doc: Path, landing: Path, repo_root: Path, by: str, today: str
) -> list[str]:
    """Thêm dòng cho mọi file chưa đăng ký của nguồn. Trả về các dòng đã thêm."""
    src_dir = landing / source
    if not src_dir.is_dir():
        raise SystemExit(f"Không có thư mục {_rel(src_dir, repo_root)} — tải file vào đó trước.")
    files = sorted(p for p in src_dir.rglob("*") if p.is_file() and p.name not in IGNORED_NAMES)
    if not files:
        raise SystemExit(f"{_rel(src_dir, repo_root)} chưa có file nào.")

    rows = parse_rows(doc)
    known = {(r["path"], r["sha256"]) for r in rows}
    next_n = max((r["n"] for r in rows), default=0) + 1
    added = []
    for p in files:
        rel, sha = _rel(p, repo_root), sha256_of(p)
        if (rel, sha) in known:
            continue
        added.append(
            f"| {next_n} | {source} | `{rel}` | {today} | {by} | {p.stat().st_size} bytes | `{sha}` |"
        )
        next_n += 1
    if added:
        text = doc.read_text(encoding="utf-8")
        text = re.sub(r"\n\|\s*\|\s*\|\s*\|\s*\|\s*\|\s*\|\s*\|\s*(?=\n|$)", "", text)  # dòng mẫu
        doc.write_text(text.rstrip("\n") + "\n" + "\n".join(added) + "\n", encoding="utf-8")
    return added


def _matches(row_source: str, only: str | None) -> bool:
    # Nguồn đăng ký là "vaers", connector là "vaers_data" / "vaers_vax" / ...
    return only is None or only == row_source or only.startswith(row_source + "_")


def verify(doc: Path, repo_root: Path, only: str | None = None) -> list[str]:
    """Trả về danh sách lỗi (rỗng nghĩa là mọi file khớp). `only`: tên connector cần nạp."""
    errors = []
    for rel, row in latest_by_path(parse_rows(doc)).items():
        if not _matches(row["source"], only):
            continue
        path = repo_root / rel
        if not path.is_file():
            errors.append(
                f"Thiếu file {rel} (nguồn {row['source']}). Tải lại đúng file có sha256 "
                f"{row['sha256']} theo docs/runbook.md."
            )
            continue
        actual = sha256_of(path)
        if actual != row["sha256"]:
            errors.append(
                f"Checksum lệch: {rel}\n  ghi trong sources_landing.md: {row['sha256']}\n"
                f"  file hiện tại:                {actual}\n"
                "  File đã bị sửa hoặc nguồn đổi dữ liệu. Nếu chủ ý dùng file mới: chạy "
                "`make landing-register` và ghi decision_log.md; nếu không: tải lại file gốc."
            )
    return errors


@app.command("register")
def register_cmd(
    source: str = typer.Option(..., "--source", "-s", help="Tên thư mục con của data/landing/."),
    by: str = typer.Option("", "--by", help="Người tải (mặc định: $LANDING_BY, rồi tên user)."),
) -> None:
    by = by or os.environ.get("LANDING_BY") or getpass.getuser()
    added = register(source, LANDING_DOC, LANDING_DIR, REPO_ROOT, by, date.today().isoformat())
    if not added:
        typer.echo("Mọi file đã đăng ký với đúng sha256; không thêm dòng nào.")
        return
    for line in added:
        typer.echo(f"Đã thêm: {line}")


@app.command("verify")
def verify_cmd(
    only: str = typer.Option(
        "", "--only", help="Chỉ kiểm file của connector này (mặc định: tất cả)."
    ),
) -> None:
    errors = verify(LANDING_DOC, REPO_ROOT, only or None)
    if errors:
        for e in errors:
            typer.echo(f"LỖI: {e}", err=True)
        raise typer.Exit(1)
    n = len(
        [
            r
            for r in latest_by_path(parse_rows(LANDING_DOC)).values()
            if _matches(r["source"], only or None)
        ]
    )
    typer.echo(f"Landing: {n} file khớp checksum.")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):  # console Windows mặc định cp1252
        stream.reconfigure(encoding="utf-8")
    app()
