"""Unit tests for skills/local-library/scripts/count-docs.py."""
import pytest


@pytest.fixture
def count_docs(load_script):
    return load_script("skills/local-library/scripts/count-docs.py")


def test_count_pdfs(count_docs, tmp_path):
    (tmp_path / "a.pdf").write_text("x")
    (tmp_path / "b.PDF").write_text("x")
    (tmp_path / "c.md").write_text("x")
    (tmp_path / "subdir").mkdir()
    assert count_docs.count_pdfs(tmp_path) == 2


def test_subtopics_requires_index_md(count_docs, tmp_path):
    (tmp_path / "topic_with_index").mkdir()
    (tmp_path / "topic_with_index" / "INDEX.md").write_text("# T")
    (tmp_path / "not_a_topic").mkdir()
    (tmp_path / "a.pdf").write_text("x")
    assert [p.name for p in count_docs.subtopics(tmp_path)] == ["topic_with_index"]


def test_count_topic_recurses_into_subtopics(count_docs, tmp_path):
    topic = tmp_path / "topic"
    topic.mkdir()
    (topic / "INDEX.md").write_text("# T")
    (topic / "a.pdf").write_text("x")
    sub = topic / "sub"
    sub.mkdir()
    (sub / "INDEX.md").write_text("# S")
    (sub / "b.pdf").write_text("x")
    (sub / "c.pdf").write_text("x")
    total = count_docs.count_topic(topic, depth=0)
    assert total == 3


def test_count_topic_flags_subtopic_threshold(count_docs, tmp_path, capsys):
    topic = tmp_path / "topic"
    topic.mkdir()
    (topic / "INDEX.md").write_text("# T")
    for i in range(count_docs.SUBTOPIC_THRESHOLD + 1):
        (topic / f"doc{i}.pdf").write_text("x")
    count_docs.count_topic(topic, depth=0)
    out = capsys.readouterr().out
    assert "exceeds the ~" in out
    assert "subtopic folders" in out


def test_count_topic_no_threshold_note_below_limit(count_docs, tmp_path, capsys):
    topic = tmp_path / "topic"
    topic.mkdir()
    (topic / "INDEX.md").write_text("# T")
    (topic / "doc.pdf").write_text("x")
    count_docs.count_topic(topic, depth=0)
    assert "exceeds the ~" not in capsys.readouterr().out


def test_main_flat_library_totals(count_docs, tmp_path, monkeypatch, capsys):
    (tmp_path / "a.pdf").write_text("x")
    (tmp_path / "b.pdf").write_text("x")
    monkeypatch.setattr("sys.argv", ["count-docs.py", str(tmp_path)])
    exit_code = count_docs.main()
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Top-level (unassigned): 2" in out
    assert "Total: 2 (2 top-level, 0 in topics)" in out


def test_main_top_level_threshold_note(count_docs, tmp_path, monkeypatch, capsys):
    for i in range(count_docs.THRESHOLD + 1):
        (tmp_path / f"doc{i}.pdf").write_text("x")
    monkeypatch.setattr("sys.argv", ["count-docs.py", str(tmp_path)])
    count_docs.main()
    out = capsys.readouterr().out
    assert "exceeds the ~" in out
    assert "organize into topics" in out


def test_main_with_topics_and_subtopics(count_docs, tmp_path, monkeypatch, capsys):
    (tmp_path / "top.pdf").write_text("x")
    topic = tmp_path / "optimization"
    topic.mkdir()
    (topic / "INDEX.md").write_text("# Optimization")
    (topic / "a.pdf").write_text("x")
    sub = topic / "history"
    sub.mkdir()
    (sub / "INDEX.md").write_text("# History")
    (sub / "b.pdf").write_text("x")

    monkeypatch.setattr("sys.argv", ["count-docs.py", str(tmp_path)])
    count_docs.main()
    out = capsys.readouterr().out
    assert "Top-level (unassigned): 1" in out
    assert "Total: 3 (1 top-level, 2 in topics)" in out


def test_main_errors_on_nonexistent_root(count_docs, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["count-docs.py", str(tmp_path / "nope")])
    exit_code = count_docs.main()
    assert exit_code == 1
    assert "not a directory" in capsys.readouterr().err
