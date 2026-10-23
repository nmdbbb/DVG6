"""Đăng ký, kiểm checksum và chia sẻ file nguồn tải tay trong data/landing/.

    python -m scripts.landing register --source vaers [--by "Tên"]
    python -m scripts.landing verify
    python -m scripts.landing upload --source vaers    # cần GH_TOKEN
    python -m scripts.landing fetch

- `register` quét data/landing/<source>/, tính sha256 từng file, thêm một dòng vào
  docs/sources_landing.md cho file chưa có. File đổi nội dung thì thêm dòng mới, không sửa dòng cũ.
- `verify` so sha256 hiện tại của mọi file đã đăng ký với dòng mới nhất của file đó.
  Lệch hoặc mất file thì in lý do và exit 1; `make ingest` gọi lệnh này trước khi nạp.
- `upload` đẩy file đã đăng ký lên GitHub Release — chỉ người tải tay chạy, một lần cho mỗi file.
- `fetch` tải các file đã đăng ký còn thiếu từ Release đó về, kiểm sha256 rồi mới giữ lại.

Vì sao cần upload/fetch: nguồn như VAERS có CAPTCHA nên phải tải tay, mà CDC dựng lại file hàng
tuần. Mỗi người tự vào tải sẽ ra file khác nhau và sha256 lệch. Nên một người tải, đưa lên Release
(bất biến), cả nhóm lấy đúng bản đó.
"""

from __future__ import annotations

import getpass
import hashlib
import os
import re
import sys
from datetime import date
from pathlib import Path

import httpx
import typer

REPO_ROOT = Path(__file__).resolve().parents[1]
LANDING_DIR = REPO_ROOT / "data" / "landing"
LANDING_DOC = REPO_ROOT / "docs" / "sources_landing.md"

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
IGNORED_NAMES = {".gitkeep"}

# Release giữ file landing. Repo public nên `fetch` tải được mà không cần đăng nhập.
RELEASE_REPO = os.environ.get("LANDING_RELEASE_REPO", "nmdbbb/DVG6")
RELEASE_TAG = os.environ.get("LANDING_RELEASE_TAG", "landing")
GITHUB_API = "https://api.github.com"

app = typer.Typer(add_completion=False)


def asset_name(rel_path: str) -> str:
    """`data/landing/vaers/2026-10-23/x.zip` -> `vaers__2026-10-23__x.zip`.

    Tên asset của GitHub không chứa dấu `/`, nên làm phẳng đường dẫn. Hai chiều đổi được cho nhau
    nên `fetch` dựng lại đúng vị trí file trong data/landing/.
    """
    return rel_path.removeprefix("data/landing/").replace("/", "__")


def path_of_asset(name: str) -> str:
    return "data/landing/" + name.replace("__", "/")


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


def _release(client: httpx.Client, create: bool) -> dict:
    """Release đang giữ file landing. `create=True` thì tạo nếu chưa có."""
    r = client.get(f"{GITHUB_API}/repos/{RELEASE_REPO}/releases/tags/{RELEASE_TAG}")
    if r.status_code == 200:
        return r.json()
    if r.status_code != 404:
        r.raise_for_status()
    if not create:
        raise SystemExit(
            f"Chưa có release '{RELEASE_TAG}' trên {RELEASE_REPO}.\n"
            "Người giữ file chạy `make landing-upload SOURCE=<nguồn>` trước."
        )
    r = client.post(
        f"{GITHUB_API}/repos/{RELEASE_REPO}/releases",
        json={
            "tag_name": RELEASE_TAG,
            "name": "File nguồn tải tay (landing)",
            "body": (
                "Bản sao bất biến của các file nguồn phải tải tay (xem docs/sources.md).\n\n"
                "Dùng để cả nhóm chạy pipeline trên cùng một bộ dữ liệu: nguồn gốc cập nhật "
                "định kỳ nên mỗi người tự tải sẽ ra file khác nhau.\n\n"
                "sha256 của từng file ghi trong `docs/sources_landing.md`. "
                "Lấy về bằng `make landing-fetch`."
            ),
        },
    )
    r.raise_for_status()
    return r.json()


@app.command("upload")
def upload_cmd(
    source: str = typer.Option(..., "--source", "-s", help="Nguồn cần đẩy lên Release."),
) -> None:
    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        raise SystemExit("Thiếu GH_TOKEN. Chạy qua `make landing-upload SOURCE=...`.")

    rows = [r for r in latest_by_path(parse_rows(LANDING_DOC)).values() if r["source"] == source]
    if not rows:
        raise SystemExit(
            f"Nguồn {source!r} chưa có dòng nào trong sources_landing.md — register trước."
        )

    headers = {"Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"}
    with httpx.Client(headers=headers, timeout=httpx.Timeout(300.0, connect=15.0)) as client:
        release = _release(client, create=True)
        existing = {a["name"]: a["id"] for a in release.get("assets", [])}

        for row in rows:
            path = REPO_ROOT / row["path"]
            if not path.is_file():
                raise SystemExit(f"Không thấy {row['path']} trên máy này.")
            actual = sha256_of(path)
            if actual != row["sha256"]:
                raise SystemExit(f"Checksum lệch, không đẩy lên: {row['path']}")

            name = asset_name(row["path"])
            if name in existing:
                typer.echo(f"  thay bản cũ: {name}")
                client.delete(
                    f"{GITHUB_API}/repos/{RELEASE_REPO}/releases/assets/{existing[name]}"
                ).raise_for_status()

            size_mb = path.stat().st_size / 1024 / 1024
            typer.echo(f"  đang đẩy {name} ({size_mb:.1f} MB)…")
            upload_url = release["upload_url"].split("{")[0]
            with path.open("rb") as fh:
                resp = client.post(
                    upload_url,
                    params={"name": name},
                    content=fh,
                    headers={"Content-Type": "application/octet-stream"},
                )
            resp.raise_for_status()
            typer.secho(f"  xong: {name}", fg="green")

    typer.secho(
        f"Đã đẩy {len(rows)} file lên release '{RELEASE_TAG}'. "
        "Người khác lấy về bằng `make landing-fetch`.",
        fg="green",
        bold=True,
    )


@app.command("fetch")
def fetch_cmd(
    only: str = typer.Option("", "--only", help="Chỉ lấy file của nguồn này."),
    force: bool = typer.Option(False, "--force", help="Tải lại cả file đã có và đúng checksum."),
) -> None:
    rows = [
        r
        for r in latest_by_path(parse_rows(LANDING_DOC)).values()
        if _matches(r["source"], only or None)
    ]
    if not rows:
        typer.echo("sources_landing.md chưa đăng ký file nào — không có gì để tải.")
        return

    todo = []
    for row in rows:
        path = REPO_ROOT / row["path"]
        if not force and path.is_file() and sha256_of(path) == row["sha256"]:
            typer.echo(f"  đã có   {row['path']}")
            continue
        todo.append(row)
    if not todo:
        typer.secho(f"Landing: đủ {len(rows)} file, checksum khớp.", fg="green")
        return

    base = f"https://github.com/{RELEASE_REPO}/releases/download/{RELEASE_TAG}"
    with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(300.0, connect=15.0)) as client:
        for row in todo:
            name = asset_name(row["path"])
            path = REPO_ROOT / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            typer.echo(f"  tải     {name}…")
            tmp = path.with_suffix(path.suffix + ".part")
            try:
                with client.stream("GET", f"{base}/{name}") as resp:
                    if resp.status_code == 404:
                        raise SystemExit(
                            f"Release '{RELEASE_TAG}' không có asset {name}.\n"
                            "Người giữ file chạy `make landing-upload SOURCE="
                            f"{row['source']}` trước."
                        )
                    resp.raise_for_status()
                    with tmp.open("wb") as fh:
                        for chunk in resp.iter_bytes(1 << 20):
                            fh.write(chunk)
                actual = sha256_of(tmp)
                if actual != row["sha256"]:
                    raise SystemExit(
                        f"Checksum lệch sau khi tải {name}:\n"
                        f"  cần: {row['sha256']}\n  được: {actual}\n"
                        "Asset trên Release không khớp sources_landing.md — báo người đã upload."
                    )
                tmp.replace(path)
                typer.secho(f"  xong    {row['path']}", fg="green")
            finally:
                tmp.unlink(missing_ok=True)

    typer.secho(f"Đã tải {len(todo)} file, checksum khớp.", fg="green", bold=True)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):  # console Windows mặc định cp1252
        stream.reconfigure(encoding="utf-8")
    app()
