"""Unit tests for skills/reporting/scripts/find-docs.py."""
import pytest


@pytest.fixture
def find_docs_mod(load_script):
    return load_script("skills/reporting/scripts/find-docs.py")


MARKED_QMD = """\
---
title: "My Report"
date: 2026-10-01
reporting-skill-doc: v1
reporting-skill-kind: report
---

body
"""

UNMARKED_QMD = """\
---
title: "Unrelated"
---

body
"""


def test_parse_frontmatter_extracts_fields(find_docs_mod):
    fields = find_docs_mod.parse_frontmatter(MARKED_QMD)
    assert fields["title"] == "My Report"
    assert fields["reporting-skill-doc"] == "v1"
    assert fields["reporting-skill-kind"] == "report"


def test_parse_frontmatter_no_frontmatter(find_docs_mod):
    assert find_docs_mod.parse_frontmatter("just text, no frontmatter\n") == {}


def test_find_docs_finds_marked_only(find_docs_mod, tmp_path):
    (tmp_path / "a.qmd").write_text(MARKED_QMD)
    (tmp_path / "b.qmd").write_text(UNMARKED_QMD)
    docs = find_docs_mod.find_docs(tmp_path)
    assert len(docs) == 1
    assert docs[0][0] == tmp_path / "a.qmd"


def test_find_docs_excludes_templates_dir(find_docs_mod, tmp_path):
    """Regression test: the skill's own bundled templates/*.qmd carry the
    same marker every scaffolded document inherits, and must not show up
    as if they were real user documents."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "report.qmd").write_text(MARKED_QMD)
    assert find_docs_mod.find_docs(tmp_path) == []


def test_find_docs_excludes_cache_dirs(find_docs_mod, tmp_path):
    for d in (".quarto", ".pixi", ".git", ".snakemake"):
        p = tmp_path / d
        p.mkdir()
        (p / "x.qmd").write_text(MARKED_QMD)
    assert find_docs_mod.find_docs(tmp_path) == []


def test_find_docs_recurses_into_real_subdirs(find_docs_mod, tmp_path):
    sub = tmp_path / "reports" / "2026"
    sub.mkdir(parents=True)
    (sub / "weekly.qmd").write_text(MARKED_QMD)
    docs = find_docs_mod.find_docs(tmp_path)
    assert len(docs) == 1


def test_main_groups_by_kind_and_shows_preview_command(
    find_docs_mod, tmp_path, monkeypatch, capsys
):
    (tmp_path / "a.qmd").write_text(MARKED_QMD)
    monkeypatch.setattr("sys.argv", ["find-docs.py", str(tmp_path)])
    exit_code = find_docs_mod.main()
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "report (1):" in out
    assert "My Report" in out
    assert "pixi run quarto preview a.qmd" in out


def test_main_reports_nothing_found(find_docs_mod, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["find-docs.py", str(tmp_path)])
    exit_code = find_docs_mod.main()
    assert exit_code == 0
    assert "No reporting-skill documents found" in capsys.readouterr().out


def test_main_errors_on_nonexistent_root(find_docs_mod, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["find-docs.py", str(tmp_path / "nope")])
    exit_code = find_docs_mod.main()
    assert exit_code == 1
    assert "not a directory" in capsys.readouterr().err
