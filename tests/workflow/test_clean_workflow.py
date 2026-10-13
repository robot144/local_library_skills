"""Unit tests for skills/workflow/scripts/clean-workflow.py."""
import pytest


@pytest.fixture
def clean_workflow(load_script):
    return load_script("skills/workflow/scripts/clean-workflow.py")


def test_has_content_empty_dir(clean_workflow, tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    assert clean_workflow.has_content(d) is False


def test_has_content_only_gitkeep(clean_workflow, tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    (d / ".gitkeep").touch()
    assert clean_workflow.has_content(d) is False


def test_has_content_real_file(clean_workflow, tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    (d / "result.csv").write_text("data")
    assert clean_workflow.has_content(d) is True


def test_empty_and_keep_removes_and_recreates(clean_workflow, tmp_path):
    d = tmp_path / "scratch"
    d.mkdir()
    (d / "case1").mkdir()
    (d / "case1" / "out.txt").write_text("x")
    changed = clean_workflow.empty_and_keep(d, dry_run=False)
    assert changed is True
    assert d.is_dir()
    assert (d / ".gitkeep").exists()
    assert not (d / "case1").exists()


def test_empty_and_keep_dry_run_changes_nothing(clean_workflow, tmp_path):
    d = tmp_path / "scratch"
    d.mkdir()
    (d / "case1").mkdir()
    changed = clean_workflow.empty_and_keep(d, dry_run=True)
    assert changed is True
    assert (d / "case1").exists()


def test_empty_and_keep_noop_when_already_empty(clean_workflow, tmp_path):
    d = tmp_path / "scratch"
    d.mkdir()
    (d / ".gitkeep").touch()
    changed = clean_workflow.empty_and_keep(d, dry_run=False)
    assert changed is False


def test_empty_cache_removes_outright(clean_workflow, tmp_path):
    d = tmp_path / ".snakemake"
    d.mkdir()
    (d / "log").write_text("x")
    changed = clean_workflow.empty_cache(d, dry_run=False)
    assert changed is True
    assert not d.exists()


def test_empty_cache_noop_when_missing(clean_workflow, tmp_path):
    assert clean_workflow.empty_cache(tmp_path / "nope", dry_run=False) is False


def _make_workflow_with_content(root):
    for name, content in [
        ("scratch/case1/run.txt", "x"),
        ("outputs/result.csv", "y"),
        ("logs/run.log", "z"),
    ]:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    (root / ".snakemake").mkdir()
    (root / ".snakemake" / "metadata").write_text("m")


def test_main_default_only_cleans_scratch(clean_workflow, tmp_path, monkeypatch):
    root = tmp_path / "wf"
    _make_workflow_with_content(root)
    monkeypatch.setattr("sys.argv", ["clean-workflow.py", str(root)])
    clean_workflow.main()
    assert not (root / "scratch" / "case1").exists()
    assert (root / "outputs" / "result.csv").exists()
    assert (root / "logs" / "run.log").exists()
    assert (root / ".snakemake").exists()


def test_main_all_cleans_everything(clean_workflow, tmp_path, monkeypatch):
    root = tmp_path / "wf"
    _make_workflow_with_content(root)
    monkeypatch.setattr("sys.argv", ["clean-workflow.py", str(root), "--all"])
    clean_workflow.main()
    assert not (root / "scratch" / "case1").exists()
    assert not (root / "outputs" / "result.csv").exists()
    assert not (root / "logs" / "run.log").exists()
    assert not (root / ".snakemake").exists()


def test_main_dry_run_changes_nothing(clean_workflow, tmp_path, monkeypatch):
    root = tmp_path / "wf"
    _make_workflow_with_content(root)
    monkeypatch.setattr("sys.argv", ["clean-workflow.py", str(root), "--all", "--dry-run"])
    clean_workflow.main()
    assert (root / "scratch" / "case1").exists()
    assert (root / "outputs" / "result.csv").exists()
    assert (root / "logs" / "run.log").exists()
    assert (root / ".snakemake").exists()


def test_main_nothing_to_clean_message(clean_workflow, tmp_path, monkeypatch, capsys):
    root = tmp_path / "wf"
    root.mkdir()
    monkeypatch.setattr("sys.argv", ["clean-workflow.py", str(root)])
    clean_workflow.main()
    assert "Nothing to clean" in capsys.readouterr().out
