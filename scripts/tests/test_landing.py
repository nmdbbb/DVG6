from pathlib import Path

import pytest

from scripts import landing

HEADER = (
    "# Landing\n\n| # | Nguồn | File | Ngày tải | Người tải | Kích thước | sha256 |\n"
    "|---|---|---|---|---|---|---|\n| | | | | | | |\n"
)


@pytest.fixture
def env(tmp_path: Path):
    doc = tmp_path / "docs" / "sources_landing.md"
    doc.parent.mkdir()
    doc.write_text(HEADER, encoding="utf-8")
    src = tmp_path / "data" / "landing" / "vaers"
    src.mkdir(parents=True)
    (src / "a.zip").write_bytes(b"hello")
    return tmp_path, doc, tmp_path / "data" / "landing"


def reg(env, **kw):
    root, doc, landing_dir = env
    return landing.register("vaers", doc, landing_dir, root, "Tester", "2026-10-17")


def test_register_adds_exactly_one_row_with_sha(env):
    added = reg(env)
    assert len(added) == 1
    assert "`data/landing/vaers/a.zip`" in added[0]
    assert "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824" in added[0]
    rows = landing.parse_rows(env[1])
    assert [r["n"] for r in rows] == [1]
    assert "| | | | | | | |" not in env[1].read_text(encoding="utf-8")  # dòng mẫu đã bị thay


def test_register_is_idempotent(env):
    reg(env)
    assert reg(env) == []
    assert len(landing.parse_rows(env[1])) == 1


def test_verify_passes_then_fails_after_one_byte_change(env):
    reg(env)
    root, doc, _ = env
    assert landing.verify(doc, root) == []
    (root / "data/landing/vaers/a.zip").write_bytes(b"hellp")
    errors = landing.verify(doc, root)
    assert len(errors) == 1 and "Checksum lệch" in errors[0]


def test_changed_file_adds_new_row_and_old_row_untouched(env):
    reg(env)
    root, doc, _ = env
    (root / "data/landing/vaers/a.zip").write_bytes(b"hellp")
    assert len(reg(env)) == 1
    rows = landing.parse_rows(doc)
    assert [r["n"] for r in rows] == [1, 2]
    assert landing.verify(doc, root) == []  # dòng mới nhất của file là chuẩn


def test_verify_reports_missing_file(env):
    reg(env)
    root, doc, _ = env
    (root / "data/landing/vaers/a.zip").unlink()
    assert "Thiếu file" in landing.verify(doc, root)[0]


def test_verify_with_empty_table_passes(env):
    assert landing.verify(env[1], env[0]) == []


def test_register_without_files_exits(env):
    (env[0] / "data/landing/vaers/a.zip").unlink()
    with pytest.raises(SystemExit):
        reg(env)


def test_verify_only_skips_other_sources(env):
    reg(env)
    root, doc, _ = env
    (root / "data/landing/vaers/a.zip").unlink()
    assert landing.verify(doc, root, only="source_demo") == []
    assert landing.verify(doc, root, only="vaers_data") != []
    assert landing.verify(doc, root, only="vaers") != []
