"""Unit tests for skills/local-library/scripts/clean-quarto.py."""
import pytest


@pytest.fixture
def clean_quarto(load_script):
    return load_script("skills/local-library/scripts/clean-quarto.py")


def test_is_our_pixi_toml_true(clean_quarto, tmp_path):
    p = tmp_path / "pixi.toml"
    p.write_text('[workspace]\nname = "local-library-quarto"\n')
    assert clean_quarto.is_our_pixi_toml(p) is True


def test_is_our_pixi_toml_false_for_foreign_manifest(clean_quarto, tmp_path):
    p = tmp_path / "pixi.toml"
    p.write_text('[workspace]\nname = "some-other-project"\n')
    assert clean_quarto.is_our_pixi_toml(p) is False


def test_is_our_pixi_toml_missing_file(clean_quarto, tmp_path):
    assert clean_quarto.is_our_pixi_toml(tmp_path / "nope.toml") is False


def test_is_our_quarto_yml_true(clean_quarto, tmp_path):
    p = tmp_path / "_quarto.yml"
    p.write_text("project:\n  type: website\n  output-dir: _site\n")
    assert clean_quarto.is_our_quarto_yml(p) is True


def test_is_our_quarto_yml_false_for_foreign_file(clean_quarto, tmp_path):
    p = tmp_path / "_quarto.yml"
    p.write_text("project:\n  type: book\n")
    assert clean_quarto.is_our_quarto_yml(p) is False


def test_is_our_index_qmd(clean_quarto, tmp_path):
    p = tmp_path / "index.qmd"
    p.write_text("---\ntitle: Home\n---\n\nBrowse the library structure in the sidebar.\n")
    assert clean_quarto.is_our_index_qmd(p) is True


def test_is_our_styles_css(clean_quarto, tmp_path):
    p = tmp_path / "styles.css"
    p.write_text(".sidebar-item-text { font-weight: 600; }\n")
    assert clean_quarto.is_our_styles_css(p) is True


def test_is_our_gitignore_true(clean_quarto, tmp_path):
    p = tmp_path / ".gitignore"
    p.write_text("_site/\n.pixi/\n.quarto/\n")
    assert clean_quarto.is_our_gitignore(p) is True


def test_is_our_gitignore_false_for_unrelated_gitignore(clean_quarto, tmp_path):
    p = tmp_path / ".gitignore"
    p.write_text("node_modules/\n*.pyc\n")
    assert clean_quarto.is_our_gitignore(p) is False


def test_is_our_wrapper_qmd_true(clean_quarto, tmp_path):
    doc_dir = tmp_path / "doc1"
    doc_dir.mkdir()
    (doc_dir / "doc1.md").write_text("content")
    qmd = doc_dir / "doc1.qmd"
    qmd.write_text('---\ntitle: "A Title"\n---\n\n{{< include doc1.md >}}\n')
    assert clean_quarto.is_our_wrapper_qmd(qmd) is True


def test_is_our_wrapper_qmd_false_without_matching_md(clean_quarto, tmp_path):
    doc_dir = tmp_path / "doc1"
    doc_dir.mkdir()
    qmd = doc_dir / "doc1.qmd"
    qmd.write_text('---\ntitle: "A Title"\n---\n\n{{< include doc1.md >}}\n')
    assert clean_quarto.is_our_wrapper_qmd(qmd) is False


def test_is_our_wrapper_qmd_false_for_index_qmd(clean_quarto, tmp_path):
    p = tmp_path / "index.qmd"
    p.write_text('---\ntitle: "A Title"\n---\n\n{{< include x.md >}}\n')
    assert clean_quarto.is_our_wrapper_qmd(p) is False


def test_revert_index_links(clean_quarto, tmp_path):
    index_path = tmp_path / "INDEX.md"
    index_path.write_text("**Files:** [PDF](doc1.pdf) · [markdown](doc1/doc1.qmd)\n")
    n = clean_quarto.revert_index_links(index_path, dry_run=False)
    assert n == 1
    assert "doc1/doc1.md)" in index_path.read_text()


def test_revert_index_links_dry_run_changes_nothing(clean_quarto, tmp_path):
    index_path = tmp_path / "INDEX.md"
    original = "**Files:** [PDF](doc1.pdf) · [markdown](doc1/doc1.qmd)\n"
    index_path.write_text(original)
    n = clean_quarto.revert_index_links(index_path, dry_run=True)
    assert n == 1
    assert index_path.read_text() == original


def test_strip_merged_quarto_dep_removes_line_from_ancestor(clean_quarto, tmp_path):
    (tmp_path / "pixi.toml").write_text(
        '[dependencies]\npython = ">=3.10"\n'
        'quarto = ">=1.9,<2"  # added by local-library init-quarto.py\n'
    )
    root = tmp_path / "lib"
    root.mkdir()
    manifest = clean_quarto.strip_merged_quarto_dep(root, dry_run=False)
    assert manifest == tmp_path / "pixi.toml"
    assert "added by local-library init-quarto.py" not in manifest.read_text()


def test_strip_merged_quarto_dep_noop_if_root_has_own_manifest(clean_quarto, tmp_path):
    root = tmp_path / "lib"
    root.mkdir()
    (root / "pixi.toml").write_text('[dependencies]\nquarto = ">=1.9,<2"\n')
    assert clean_quarto.strip_merged_quarto_dep(root, dry_run=False) is None


def _make_quarto_site(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / "pixi.toml").write_text('[workspace]\nname = "local-library-quarto"\n')
    (root / "_quarto.yml").write_text("project:\n  type: website\n  output-dir: _site\n")
    (root / "index.qmd").write_text(
        "---\ntitle: Home\n---\n\nBrowse the library structure in the sidebar.\n"
    )
    (root / "styles.css").write_text(".sidebar-item-text { font-weight: 600; }\n")
    (root / ".gitignore").write_text("_site/\n.pixi/\n.quarto/\n")
    (root / ".quarto").mkdir()
    (root / ".pixi").mkdir()
    (root / "_site").mkdir()
    doc_dir = root / "doc1"
    doc_dir.mkdir()
    (doc_dir / "doc1.md").write_text("content")
    (doc_dir / "doc1.qmd").write_text(
        '---\ntitle: "A Title"\n---\n\n{{< include doc1.md >}}\n'
    )
    (root / "doc1.pdf").write_text("x")
    (root / "INDEX.md").write_text(
        "### doc1 — A Title\n\n**Files:** [PDF](doc1.pdf) · [markdown](doc1/doc1.qmd)\n"
    )


def test_main_removes_quarto_site_and_reverts_links(clean_quarto, tmp_path, monkeypatch):
    root = tmp_path / "lib"
    _make_quarto_site(root)
    monkeypatch.setattr("sys.argv", ["clean-quarto.py", str(root)])
    exit_code = clean_quarto.main()
    assert exit_code == 0

    for name in ["pixi.toml", "_quarto.yml", "index.qmd", "styles.css", ".gitignore"]:
        assert not (root / name).exists()
    for name in [".quarto", ".pixi", "_site"]:
        assert not (root / name).exists()
    assert not (root / "doc1" / "doc1.qmd").exists()
    assert (root / "doc1" / "doc1.md").exists()
    assert (root / "doc1.pdf").exists()
    assert "doc1/doc1.md)" in (root / "INDEX.md").read_text()


def test_main_dry_run_changes_nothing(clean_quarto, tmp_path, monkeypatch):
    root = tmp_path / "lib"
    _make_quarto_site(root)
    monkeypatch.setattr("sys.argv", ["clean-quarto.py", str(root), "--dry-run"])
    clean_quarto.main()
    for name in ["pixi.toml", "_quarto.yml", "index.qmd", "styles.css", ".gitignore"]:
        assert (root / name).exists()
    assert (root / "doc1" / "doc1.qmd").exists()
    assert "doc1/doc1.qmd)" in (root / "INDEX.md").read_text()


def test_main_leaves_foreign_files_alone(clean_quarto, tmp_path, monkeypatch):
    """A pixi.toml/.gitignore that predates the Quarto setup and isn't
    ours must be left untouched."""
    root = tmp_path / "lib"
    root.mkdir()
    (root / "pixi.toml").write_text('[workspace]\nname = "some-other-project"\n')
    (root / ".gitignore").write_text("node_modules/\n")
    (root / "INDEX.md").write_text("# Library Index\n")
    monkeypatch.setattr("sys.argv", ["clean-quarto.py", str(root)])
    clean_quarto.main()
    assert (root / "pixi.toml").is_file()
    assert "some-other-project" in (root / "pixi.toml").read_text()
    assert (root / ".gitignore").is_file()


def test_main_sweeps_stray_html_outside_site(clean_quarto, tmp_path, monkeypatch):
    root = tmp_path / "lib"
    root.mkdir()
    (root / "INDEX.md").write_text("# Library Index\n")
    (root / "stray.html").write_text("<html></html>")
    monkeypatch.setattr("sys.argv", ["clean-quarto.py", str(root)])
    clean_quarto.main()
    assert not (root / "stray.html").exists()


def test_main_errors_on_nonexistent_root(clean_quarto, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["clean-quarto.py", str(tmp_path / "nope")])
    exit_code = clean_quarto.main()
    assert exit_code == 1
    assert "not a directory" in capsys.readouterr().err
