"""Unit tests for skills/local-library/scripts/init-library.py."""
import pytest


@pytest.fixture
def init_library(load_script):
    return load_script("skills/local-library/scripts/init-library.py")


def test_write_if_missing_creates(init_library, tmp_path):
    target = tmp_path / "f.txt"
    init_library.write_if_missing(target, "content")
    assert target.read_text() == "content"


def test_write_if_missing_preserves_existing(init_library, tmp_path):
    target = tmp_path / "f.txt"
    target.write_text("original")
    init_library.write_if_missing(target, "new")
    assert target.read_text() == "original"


def test_main_creates_claude_md_and_index(init_library, tmp_path, monkeypatch):
    root = tmp_path / "mylib"
    monkeypatch.setattr("sys.argv", ["init-library.py", str(root)])
    exit_code = init_library.main()
    assert exit_code == 0
    assert (root / "CLAUDE.md").is_file()
    assert (root / "INDEX.md").is_file()


def test_claude_md_has_discovery_marker(init_library, tmp_path, monkeypatch):
    root = tmp_path / "mylib"
    monkeypatch.setattr("sys.argv", ["init-library.py", str(root)])
    init_library.main()
    assert "<!-- local-library-root: v1 -->" in (root / "CLAUDE.md").read_text()


def test_main_is_idempotent(init_library, tmp_path, monkeypatch):
    root = tmp_path / "mylib"
    monkeypatch.setattr("sys.argv", ["init-library.py", str(root)])
    init_library.main()
    (root / "CLAUDE.md").write_text("# My Custom Library\ncustom content")
    init_library.main()
    assert "My Custom Library" in (root / "CLAUDE.md").read_text()


def test_main_default_root(init_library, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["init-library.py"])
    init_library.main()
    assert (tmp_path / init_library.DEFAULT_ROOT).is_dir()
