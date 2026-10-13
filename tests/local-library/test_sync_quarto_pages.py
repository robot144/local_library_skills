"""Unit tests for skills/local-library/scripts/sync-quarto-pages.py."""
import pytest
import yaml


@pytest.fixture
def sync_quarto_pages(load_script):
    return load_script("skills/local-library/scripts/sync-quarto-pages.py")


def test_yaml_quote_escapes_double_quotes(sync_quarto_pages):
    assert sync_quarto_pages.yaml_quote('A "quoted" title') == 'A \\"quoted\\" title'


def test_section_title_from_h1(sync_quarto_pages, tmp_path):
    index_path = tmp_path / "INDEX.md"
    index_path.write_text("# Optimization — Topic Index\n\nbody\n")
    assert sync_quarto_pages.section_title(index_path) == "Optimization"


def test_section_title_falls_back_to_dirname(sync_quarto_pages, tmp_path):
    topic_dir = tmp_path / "optimization"
    topic_dir.mkdir()
    index_path = topic_dir / "INDEX.md"
    index_path.write_text("no heading here\n")
    assert sync_quarto_pages.section_title(index_path) == "optimization"


def test_subtopic_index_files(sync_quarto_pages, tmp_path):
    (tmp_path / "sub1").mkdir()
    (tmp_path / "sub1" / "INDEX.md").write_text("# S1")
    (tmp_path / "not_a_topic").mkdir()
    result = sync_quarto_pages.subtopic_index_files(tmp_path)
    assert result == [tmp_path / "sub1" / "INDEX.md"]


def test_all_index_files_recurses(sync_quarto_pages, tmp_path):
    (tmp_path / "INDEX.md").write_text("# Root")
    topic = tmp_path / "topic"
    topic.mkdir()
    (topic / "INDEX.md").write_text("# Topic")
    sub = topic / "sub"
    sub.mkdir()
    (sub / "INDEX.md").write_text("# Sub")

    result = sync_quarto_pages.all_index_files(tmp_path)
    assert set(result) == {
        tmp_path / "INDEX.md",
        topic / "INDEX.md",
        sub / "INDEX.md",
    }


def _make_doc_entry(index_path, name="doc1", title="A Title"):
    index_path.write_text(
        f"# Library Index\n\n"
        f"### {name} — {title}\n\n"
        f"**Files:** [PDF]({name}.pdf) · [markdown]({name}/{name}.md)\n"
    )
    doc_dir = index_path.parent / name
    doc_dir.mkdir()
    (doc_dir / f"{name}.md").write_text("# Doc content")
    return doc_dir


def test_write_wrappers_creates_qmd_and_rewrites_link(sync_quarto_pages, tmp_path):
    index_path = tmp_path / "INDEX.md"
    doc_dir = _make_doc_entry(index_path)

    changed = sync_quarto_pages.write_wrappers_and_fix_links(index_path)
    assert changed is True

    qmd_file = doc_dir / "doc1.qmd"
    assert qmd_file.is_file()
    content = qmd_file.read_text()
    assert 'title: "A Title"' in content
    assert "{{< include doc1.md >}}" in content

    new_text = index_path.read_text()
    assert "doc1/doc1.qmd" in new_text
    assert "doc1/doc1.md)" not in new_text


def test_write_wrappers_second_run_on_converted_link_reports_unchanged(
    sync_quarto_pages, tmp_path
):
    index_path = tmp_path / "INDEX.md"
    _make_doc_entry(index_path)
    sync_quarto_pages.write_wrappers_and_fix_links(index_path)
    changed_again = sync_quarto_pages.write_wrappers_and_fix_links(index_path)
    assert changed_again is False


def test_write_wrappers_does_not_regenerate_missing_wrapper_on_rerun(
    sync_quarto_pages, tmp_path
):
    """Characterizes actual (not documented) behavior, confirmed by
    testing: once an INDEX.md entry's link already points at .qmd, a
    later run does NOT recreate the wrapper file even if it's missing -
    the module's docstring claims wrappers are "regenerated each time,"
    but the regex only matches .md-suffixed links, so a link already
    converted to .qmd is never revisited. Worth fixing, but pinning the
    real behavior here rather than the aspirational one."""
    index_path = tmp_path / "INDEX.md"
    doc_dir = _make_doc_entry(index_path)
    sync_quarto_pages.write_wrappers_and_fix_links(index_path)
    qmd_file = doc_dir / "doc1.qmd"
    qmd_file.unlink()

    sync_quarto_pages.write_wrappers_and_fix_links(index_path)
    assert not qmd_file.exists()


def test_write_wrappers_skips_entry_without_md_file(sync_quarto_pages, tmp_path):
    index_path = tmp_path / "INDEX.md"
    index_path.write_text(
        "### doc1 — A Title\n\n**Files:** [PDF](doc1.pdf) · [markdown](doc1/doc1.md)\n"
    )
    # doc1/doc1.md deliberately not created - PDF-only entry
    changed = sync_quarto_pages.write_wrappers_and_fix_links(index_path)
    assert changed is False
    assert not (tmp_path / "doc1").exists()


def test_sidebar_node_flat_topic(sync_quarto_pages, tmp_path):
    (tmp_path / "INDEX.md").write_text("# Root")
    topic = tmp_path / "topic"
    topic.mkdir()
    (topic / "INDEX.md").write_text("# Topic")
    node = sync_quarto_pages.sidebar_node(topic / "INDEX.md", tmp_path)
    assert node == {"text": "Topic", "href": "topic/INDEX.md"}


def test_sidebar_node_topic_with_subtopic(sync_quarto_pages, tmp_path):
    (tmp_path / "INDEX.md").write_text("# Root")
    topic = tmp_path / "topic"
    topic.mkdir()
    (topic / "INDEX.md").write_text("# Topic")
    sub = topic / "sub"
    sub.mkdir()
    (sub / "INDEX.md").write_text("# Sub")

    node = sync_quarto_pages.sidebar_node(topic / "INDEX.md", tmp_path)
    assert node["section"] == "Topic"
    assert node["href"] == "topic/INDEX.md"
    assert node["contents"] == [{"text": "Sub", "href": "topic/sub/INDEX.md"}]


def test_rebuild_sidebar_writes_contents_and_drops_auto(sync_quarto_pages, tmp_path):
    (tmp_path / "INDEX.md").write_text("# Root")
    (tmp_path / "_quarto.yml").write_text(
        "project:\n  type: website\nwebsite:\n  sidebar:\n    contents: auto\n"
    )
    topic = tmp_path / "topic"
    topic.mkdir()
    (topic / "INDEX.md").write_text("# Topic")

    sync_quarto_pages.rebuild_sidebar(tmp_path)

    config = yaml.safe_load((tmp_path / "_quarto.yml").read_text())
    assert "auto" not in config["website"]["sidebar"]
    contents = config["website"]["sidebar"]["contents"]
    assert contents[0] == "index.qmd"
    assert contents[1] == {"text": "Root", "href": "INDEX.md"}
    assert {"text": "Topic", "href": "topic/INDEX.md"} in contents


def test_main_runs_without_quarto_yml(sync_quarto_pages, tmp_path, monkeypatch, capsys):
    (tmp_path / "INDEX.md").write_text("# Library Index\n")
    monkeypatch.setattr("sys.argv", ["sync-quarto-pages.py", str(tmp_path)])
    exit_code = sync_quarto_pages.main()
    assert exit_code == 0
    assert "No _quarto.yml found" in capsys.readouterr().out


def test_main_end_to_end(sync_quarto_pages, tmp_path, monkeypatch, capsys):
    index_path = tmp_path / "INDEX.md"
    _make_doc_entry(index_path)
    (tmp_path / "_quarto.yml").write_text(
        "project:\n  type: website\nwebsite:\n  sidebar:\n    contents: auto\n"
    )
    monkeypatch.setattr("sys.argv", ["sync-quarto-pages.py", str(tmp_path)])
    exit_code = sync_quarto_pages.main()
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Rebuilt sidebar in _quarto.yml" in out
    assert (tmp_path / "doc1" / "doc1.qmd").is_file()


def test_main_errors_on_nonexistent_root(sync_quarto_pages, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["sync-quarto-pages.py", str(tmp_path / "nope")])
    exit_code = sync_quarto_pages.main()
    assert exit_code == 1
    assert "not a directory" in capsys.readouterr().err
