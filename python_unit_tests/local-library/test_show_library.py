"""Unit tests for skills/local-library/scripts/show-library.py."""
import pytest


@pytest.fixture
def show_library(load_script):
    return load_script("skills/local-library/scripts/show-library.py")


INDEX_MD = """\
# Library Index

### kalman1960_filter — A New Approach to Linear Filtering

**Summary:** Foundational paper on the Kalman filter.
**Keywords:** filtering, estimation
**Key results:** the filter equations.
**Files:** [PDF](kalman1960_filter.pdf)

### jones2023_opt — Convex Optimization Methods

**Summary:** Survey of convex optimization methods.
**Files:** [PDF](jones2023_opt.pdf)
"""


def test_parse_index_extracts_entries_and_summaries(show_library, tmp_path):
    index_path = tmp_path / "INDEX.md"
    index_path.write_text(INDEX_MD)
    entries = show_library.parse_index(index_path)
    assert len(entries) == 2
    assert entries[0]["name"] == "kalman1960_filter"
    assert entries[0]["title"] == "A New Approach to Linear Filtering"
    assert "Foundational paper" in entries[0]["summary"]
    assert entries[1]["name"] == "jones2023_opt"


def test_parse_index_empty_file(show_library, tmp_path):
    index_path = tmp_path / "INDEX.md"
    index_path.write_text("# Library Index\n\nNo entries yet.\n")
    assert show_library.parse_index(index_path) == []


def test_truncate_short_text_unchanged(show_library):
    assert show_library.truncate("short text", width=140) == "short text"


def test_truncate_long_text_gets_ellipsis(show_library):
    text = "x" * 200
    result = show_library.truncate(text, width=140)
    assert len(result) == 140
    assert result.endswith("…")


def test_subtopics_requires_index_md(show_library, tmp_path):
    (tmp_path / "topic").mkdir()
    (tmp_path / "topic" / "INDEX.md").write_text("# T")
    (tmp_path / "not_topic").mkdir()
    assert [p.name for p in show_library.subtopics(tmp_path)] == ["topic"]


def test_describe_dir_flags_missing_pdf(show_library, tmp_path):
    index_path = tmp_path / "INDEX.md"
    index_path.write_text(
        "### missing_doc — A Title\n\n**Summary:** no PDF on disk for this one.\n"
    )
    lines = []
    total, missing, orphans, topics = show_library.describe_dir(
        tmp_path, "Top-level documents", lines, recurse_subtopics=False
    )
    assert total == 1
    assert missing == 1
    assert orphans == 0
    joined = "\n".join(lines)
    assert "MISSING PDF" in joined
    assert "indexed but PDF missing on disk: missing_doc" in joined


def test_describe_dir_flags_orphan_pdf(show_library, tmp_path):
    (tmp_path / "INDEX.md").write_text("# Library Index\n")
    (tmp_path / "orphan_doc.pdf").write_text("x")
    lines = []
    total, missing, orphans, topics = show_library.describe_dir(
        tmp_path, "Top-level documents", lines, recurse_subtopics=False
    )
    assert total == 0
    assert orphans == 1
    assert "PDF on disk but not in INDEX.md: orphan_doc" in "\n".join(lines)


def test_describe_dir_pdf_plus_md_status(show_library, tmp_path):
    index_path = tmp_path / "INDEX.md"
    index_path.write_text("### doc — Title\n\n**Summary:** has both PDF and markdown.\n")
    (tmp_path / "doc.pdf").write_text("x")
    doc_dir = tmp_path / "doc"
    doc_dir.mkdir()
    (doc_dir / "doc.md").write_text("markdown content")
    lines = []
    show_library.describe_dir(tmp_path, "Top-level documents", lines, recurse_subtopics=False)
    assert "[PDF+md]" in "\n".join(lines)


def test_describe_dir_recurses_subtopics(show_library, tmp_path):
    (tmp_path / "INDEX.md").write_text("# Library Index\n")
    topic = tmp_path / "topic"
    topic.mkdir()
    (topic / "INDEX.md").write_text(
        "### doc — Title\n\n**Summary:** in a subtopic.\n"
    )
    (topic / "doc.pdf").write_text("x")
    lines = []
    total, missing, orphans, topic_count = show_library.describe_dir(
        tmp_path, "Top-level documents", lines, recurse_subtopics=True
    )
    assert total == 1
    assert topic_count == 1


def test_main_reads_title_from_claude_md(show_library, tmp_path, monkeypatch, capsys):
    (tmp_path / "CLAUDE.md").write_text("<!-- local-library-root: v1 -->\n# My Research Library\n")
    (tmp_path / "INDEX.md").write_text("# Library Index\n")
    monkeypatch.setattr("sys.argv", ["show-library.py", str(tmp_path)])
    exit_code = show_library.main()
    assert exit_code == 0
    assert "Library: My Research Library" in capsys.readouterr().out


def test_main_no_claude_md(show_library, tmp_path, monkeypatch, capsys):
    (tmp_path / "INDEX.md").write_text("# Library Index\n")
    monkeypatch.setattr("sys.argv", ["show-library.py", str(tmp_path)])
    show_library.main()
    assert "no CLAUDE.md title found" in capsys.readouterr().out


def test_main_status_line_clean(show_library, tmp_path, monkeypatch, capsys):
    index_path = tmp_path / "INDEX.md"
    index_path.write_text("### doc — Title\n\n**Summary:** clean.\n")
    (tmp_path / "doc.pdf").write_text("x")
    monkeypatch.setattr("sys.argv", ["show-library.py", str(tmp_path)])
    show_library.main()
    out = capsys.readouterr().out
    assert "all indexed entries have a PDF on disk" in out


def test_main_status_line_with_drift(show_library, tmp_path, monkeypatch, capsys):
    index_path = tmp_path / "INDEX.md"
    index_path.write_text("### missing_doc — Title\n\n**Summary:** drifted.\n")
    monkeypatch.setattr("sys.argv", ["show-library.py", str(tmp_path)])
    show_library.main()
    out = capsys.readouterr().out
    assert "missing-PDF entries" in out


def test_main_errors_on_nonexistent_root(show_library, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["show-library.py", str(tmp_path / "nope")])
    exit_code = show_library.main()
    assert exit_code == 1
    assert "not a directory" in capsys.readouterr().err
