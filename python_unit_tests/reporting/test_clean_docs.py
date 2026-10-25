"""Unit tests for skills/reporting/scripts/clean-docs.py."""
import pytest


@pytest.fixture
def clean_docs(load_script):
    return load_script("skills/reporting/scripts/clean-docs.py")


MARKED_QMD = """\
---
title: "My Report"
reporting-skill-doc: v1
reporting-skill-kind: report
---

body
"""


def test_parse_frontmatter(clean_docs):
    fields = clean_docs.parse_frontmatter(MARKED_QMD)
    assert fields["reporting-skill-doc"] == "v1"


def test_find_docs_excludes_templates(clean_docs, tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "report.qmd").write_text(MARKED_QMD)
    assert clean_docs.find_docs(tmp_path) == []


def test_remove_file_dry_run(clean_docs, tmp_path):
    f = tmp_path / "x.html"
    f.write_text("x")
    removed = []
    clean_docs.remove(f, dry_run=True, removed=removed)
    assert f.exists()
    assert removed == [f]


def test_remove_file_real(clean_docs, tmp_path):
    f = tmp_path / "x.html"
    f.write_text("x")
    removed = []
    clean_docs.remove(f, dry_run=False, removed=removed)
    assert not f.exists()


def test_remove_dir_real(clean_docs, tmp_path):
    d = tmp_path / "x_files"
    d.mkdir()
    (d / "a.png").write_text("x")
    removed = []
    clean_docs.remove(d, dry_run=False, removed=removed)
    assert not d.exists()


def _make_doc_with_outputs(root, name="doc"):
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.qmd").write_text(MARKED_QMD)
    (root / f"{name}.html").write_text("<html></html>")
    (root / f"{name}.pdf").write_text("%PDF-1.4 fake")
    files_dir = root / f"{name}_files"
    files_dir.mkdir()
    (files_dir / "fig.png").write_text("img")
    return root


def test_main_default_removes_html_pdf_and_files(clean_docs, tmp_path, monkeypatch):
    root = _make_doc_with_outputs(tmp_path / "docs")
    monkeypatch.setattr("sys.argv", ["clean-docs.py", str(tmp_path)])
    clean_docs.main()
    assert not (root / "doc.html").exists()
    assert not (root / "doc.pdf").exists()
    assert not (root / "doc_files").exists()
    assert (root / "doc.qmd").exists()


def test_main_dry_run_changes_nothing(clean_docs, tmp_path, monkeypatch):
    root = _make_doc_with_outputs(tmp_path / "docs")
    monkeypatch.setattr("sys.argv", ["clean-docs.py", str(tmp_path), "--dry-run"])
    clean_docs.main()
    assert (root / "doc.html").exists()
    assert (root / "doc.pdf").exists()
    assert (root / "doc_files").exists()


def test_main_all_scopes_cache_cleanup_to_doc_dir_only(clean_docs, tmp_path, monkeypatch):
    """Regression test: --all must only remove .quarto/.pixi that sit in
    a document's own directory, never an unrelated one found elsewhere in
    the search tree - an earlier version did an unscoped tree-wide search
    that would have deleted other projects' environments."""
    doc_root = _make_doc_with_outputs(tmp_path / "docs")
    (doc_root / ".pixi").mkdir()
    (doc_root / ".pixi" / "envs").mkdir()
    (doc_root / ".quarto").mkdir()

    unrelated_root = tmp_path / "unrelated_project"
    unrelated_root.mkdir()
    (unrelated_root / ".pixi").mkdir()
    (unrelated_root / ".pixi" / "envs").mkdir()

    monkeypatch.setattr("sys.argv", ["clean-docs.py", str(tmp_path), "--all"])
    clean_docs.main()

    assert not (doc_root / ".pixi").exists()
    assert not (doc_root / ".quarto").exists()
    assert (unrelated_root / ".pixi").exists(), "must not touch an unrelated project's .pixi/"


def test_main_default_does_not_touch_cache_dirs(clean_docs, tmp_path, monkeypatch):
    root = _make_doc_with_outputs(tmp_path / "docs")
    (root / ".pixi").mkdir()
    monkeypatch.setattr("sys.argv", ["clean-docs.py", str(tmp_path)])
    clean_docs.main()
    assert (root / ".pixi").exists()


def test_main_ignores_unmarked_qmd_outputs(clean_docs, tmp_path, monkeypatch):
    other = tmp_path / "other"
    other.mkdir()
    (other / "unrelated.qmd").write_text("---\ntitle: x\n---\nbody")
    (other / "unrelated.html").write_text("<html></html>")
    monkeypatch.setattr("sys.argv", ["clean-docs.py", str(tmp_path)])
    clean_docs.main()
    assert (other / "unrelated.html").exists()
