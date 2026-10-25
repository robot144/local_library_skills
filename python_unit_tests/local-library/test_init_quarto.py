"""Unit tests for skills/local-library/scripts/init-quarto.py."""
import pytest


@pytest.fixture
def init_quarto(load_script):
    return load_script("skills/local-library/scripts/init-quarto.py")


def test_write_if_missing_creates(init_quarto, tmp_path):
    target = tmp_path / "f.txt"
    init_quarto.write_if_missing(target, "content")
    assert target.read_text() == "content"


def test_write_if_missing_preserves_existing(init_quarto, tmp_path):
    target = tmp_path / "f.txt"
    target.write_text("original")
    init_quarto.write_if_missing(target, "new")
    assert target.read_text() == "original"


def test_merge_quarto_into_adds_dependency(init_quarto, tmp_path):
    manifest = tmp_path / "pixi.toml"
    manifest.write_text('[dependencies]\npython = ">=3.10"\n')
    status = init_quarto.merge_quarto_into(manifest)
    assert status == "added"
    assert "quarto = " in manifest.read_text()


def test_merge_quarto_into_idempotent(init_quarto, tmp_path):
    manifest = tmp_path / "pixi.toml"
    manifest.write_text('[dependencies]\nquarto = ">=1.9,<2"\n')
    status = init_quarto.merge_quarto_into(manifest)
    assert status == "already-present"


def test_setup_pixi_manifest_uses_own(init_quarto, tmp_path):
    root = tmp_path / "lib"
    root.mkdir()
    (root / "pixi.toml").write_text('[dependencies]\npython = ">=3.10"\n')
    manifest = init_quarto.setup_pixi_manifest(root)
    assert manifest == root / "pixi.toml"


def test_setup_pixi_manifest_merges_into_ancestor(init_quarto, tmp_path):
    (tmp_path / "pixi.toml").write_text('[dependencies]\npython = ">=3.10"\n')
    root = tmp_path / "sub" / "lib"
    root.mkdir(parents=True)
    manifest = init_quarto.setup_pixi_manifest(root)
    assert manifest == tmp_path / "pixi.toml"
    assert "quarto" in manifest.read_text()
    assert not (root / "pixi.toml").exists()


def test_setup_pixi_manifest_creates_fresh_if_none_found(init_quarto, tmp_path):
    root = tmp_path / "lib"
    root.mkdir()
    manifest = init_quarto.setup_pixi_manifest(root)
    assert manifest == root / "pixi.toml"
    assert "quarto" in manifest.read_text()


def test_setup_pixi_manifest_own_preexisting_without_quarto_not_checked(
    init_quarto, tmp_path
):
    """Documents local-library's actual (different from reporting's)
    behavior: if the library root already has its own pixi.toml, it's
    trusted as-is and never merged into, even if it's missing quarto -
    unlike reporting's init-quarto.py, which was fixed to always check."""
    root = tmp_path / "lib"
    root.mkdir()
    (root / "pixi.toml").write_text('[dependencies]\npython = ">=3.10"\n')
    init_quarto.setup_pixi_manifest(root)
    assert "quarto" not in (root / "pixi.toml").read_text()


def test_main_scaffolds_quarto_site(init_quarto, tmp_path, monkeypatch):
    root = tmp_path / "lib"
    root.mkdir()
    monkeypatch.setattr("sys.argv", ["init-quarto.py", str(root)])
    exit_code = init_quarto.main()
    assert exit_code == 0
    for name in ["pixi.toml", "_quarto.yml", "index.qmd", "styles.css", ".gitignore"]:
        assert (root / name).is_file()


def test_main_requires_preexisting_root(init_quarto, tmp_path, monkeypatch, capsys):
    """Unlike init-library.py/init-workflow.py, this script does not
    create the root itself - it only scaffolds a Quarto site into an
    already-existing library root."""
    root = tmp_path / "not_created_yet"
    monkeypatch.setattr("sys.argv", ["init-quarto.py", str(root)])
    exit_code = init_quarto.main()
    assert exit_code == 1
    assert "not a directory" in capsys.readouterr().err
    assert not root.exists()


def test_main_is_idempotent(init_quarto, tmp_path, monkeypatch):
    root = tmp_path / "lib"
    root.mkdir()
    monkeypatch.setattr("sys.argv", ["init-quarto.py", str(root)])
    init_quarto.main()
    (root / "styles.css").write_text("/* custom */")
    init_quarto.main()
    assert (root / "styles.css").read_text() == "/* custom */"


def test_main_errors_on_nonexistent_root(init_quarto, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["init-quarto.py", str(tmp_path / "nope")])
    exit_code = init_quarto.main()
    assert exit_code == 1
    assert "not a directory" in capsys.readouterr().err
