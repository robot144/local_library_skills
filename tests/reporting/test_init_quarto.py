"""Unit tests for skills/reporting/scripts/init-quarto.py."""
import pytest


@pytest.fixture
def init_quarto(load_script):
    return load_script("skills/reporting/scripts/init-quarto.py")


def test_write_if_missing_creates(init_quarto, tmp_path):
    target = tmp_path / "f.txt"
    init_quarto.write_if_missing(target, "content")
    assert target.read_text() == "content"


def test_write_if_missing_preserves_existing(init_quarto, tmp_path):
    target = tmp_path / "f.txt"
    target.write_text("original")
    init_quarto.write_if_missing(target, "new")
    assert target.read_text() == "original"


def test_merge_deps_into_adds_missing(init_quarto, tmp_path):
    manifest = tmp_path / "pixi.toml"
    manifest.write_text('[dependencies]\npython = ">=3.10"\n')
    added = init_quarto.merge_deps_into(
        manifest, {"quarto": ">=1.9,<2", "jupyter": ">=1.0,<2"}
    )
    assert set(added) == {"quarto", "jupyter"}
    text = manifest.read_text()
    assert "quarto = " in text and "jupyter = " in text


def test_merge_deps_into_idempotent(init_quarto, tmp_path):
    manifest = tmp_path / "pixi.toml"
    manifest.write_text('[dependencies]\nquarto = ">=1.9,<2"\n')
    added = init_quarto.merge_deps_into(manifest, {"quarto": ">=1.9,<2"})
    assert added == []


def test_merge_deps_into_no_dependencies_section(init_quarto, tmp_path):
    manifest = tmp_path / "pixi.toml"
    manifest.write_text('[workspace]\nname = "x"\n')
    added = init_quarto.merge_deps_into(manifest, {"quarto": ">=1.9,<2"})
    assert added == ["quarto"]
    assert "[dependencies]" in manifest.read_text()


def test_setup_pixi_manifest_uses_own(init_quarto, tmp_path):
    target_dir = tmp_path / "docs"
    target_dir.mkdir()
    (target_dir / "pixi.toml").write_text('[dependencies]\npython = ">=3.10"\n')
    manifest = init_quarto.setup_pixi_manifest(target_dir, {"quarto": ">=1.9,<2"})
    assert manifest == target_dir / "pixi.toml"
    assert "quarto" in manifest.read_text()


def test_setup_pixi_manifest_merges_into_ancestor(init_quarto, tmp_path):
    (tmp_path / "pixi.toml").write_text('[dependencies]\npython = ">=3.10"\n')
    target_dir = tmp_path / "sub" / "docs"
    target_dir.mkdir(parents=True)
    manifest = init_quarto.setup_pixi_manifest(target_dir, {"quarto": ">=1.9,<2"})
    assert manifest == tmp_path / "pixi.toml"
    assert "quarto" in manifest.read_text()
    assert not (target_dir / "pixi.toml").exists()


def test_setup_pixi_manifest_does_not_assume_existing_own_manifest_is_complete(init_quarto, tmp_path):
    """Regression test: a pre-existing pixi.toml at the target dir must be
    checked/merged like any other, not trusted just because it exists -
    confirmed necessary by testing (a manifest with no quarto dependency
    installed fine but failed at render time)."""
    target_dir = tmp_path / "docs"
    target_dir.mkdir()
    (target_dir / "pixi.toml").write_text('[dependencies]\npython = ">=3.10"\n')
    init_quarto.setup_pixi_manifest(target_dir, {"quarto": ">=1.9,<2", "jupyter": ">=1.0,<2"})
    text = (target_dir / "pixi.toml").read_text()
    assert "quarto" in text and "jupyter" in text


def test_setup_pixi_manifest_creates_fresh_if_none_found(init_quarto, tmp_path):
    target_dir = tmp_path / "docs"
    target_dir.mkdir()
    manifest = init_quarto.setup_pixi_manifest(
        target_dir, {"quarto": ">=1.9,<2", "jupyter": ">=1.0,<2"}
    )
    assert manifest == target_dir / "pixi.toml"
    text = manifest.read_text()
    assert "quarto" in text and "jupyter" in text and "python" in text


def test_main_default_template_and_format(init_quarto, tmp_path, monkeypatch):
    target = tmp_path / "report.qmd"
    monkeypatch.setattr("sys.argv", ["init-quarto.py", str(target)])
    exit_code = init_quarto.main()
    assert exit_code == 0
    content = target.read_text()
    assert "format: html" in content
    assert "reporting-skill-kind: report" in content


def test_main_log_template(init_quarto, tmp_path, monkeypatch):
    target = tmp_path / "log.qmd"
    monkeypatch.setattr("sys.argv", ["init-quarto.py", str(target), "--template", "log"])
    init_quarto.main()
    content = target.read_text()
    assert "reporting-skill-kind: log" in content


def test_main_pdf_format_rewrites_frontmatter_and_adds_xz(init_quarto, tmp_path, monkeypatch):
    target = tmp_path / "report.qmd"
    monkeypatch.setattr("sys.argv", ["init-quarto.py", str(target), "--format", "pdf"])
    init_quarto.main()
    content = target.read_text()
    assert "format: pdf" in content
    assert "format: html" not in content
    manifest_text = (tmp_path / "pixi.toml").read_text()
    assert "xz" in manifest_text


def test_main_html_format_does_not_add_xz(init_quarto, tmp_path, monkeypatch):
    target = tmp_path / "report.qmd"
    monkeypatch.setattr("sys.argv", ["init-quarto.py", str(target)])
    init_quarto.main()
    manifest_text = (tmp_path / "pixi.toml").read_text()
    assert "xz" not in manifest_text


def test_main_invalid_format_errors(init_quarto, tmp_path, monkeypatch, capsys):
    target = tmp_path / "report.qmd"
    monkeypatch.setattr("sys.argv", ["init-quarto.py", str(target), "--format", "docx"])
    exit_code = init_quarto.main()
    assert exit_code == 1
    assert "must be 'html' or 'pdf'" in capsys.readouterr().err


def test_main_unknown_template_errors(init_quarto, tmp_path, monkeypatch, capsys):
    target = tmp_path / "x.qmd"
    monkeypatch.setattr("sys.argv", ["init-quarto.py", str(target), "--template", "nope"])
    exit_code = init_quarto.main()
    assert exit_code == 1
    assert "no such template" in capsys.readouterr().err


def test_main_idempotent(init_quarto, tmp_path, monkeypatch):
    target = tmp_path / "report.qmd"
    monkeypatch.setattr("sys.argv", ["init-quarto.py", str(target)])
    init_quarto.main()
    target.write_text("custom content")
    init_quarto.main()
    assert target.read_text() == "custom content"
