"""Unit tests for skills/workflow/scripts/init-workflow.py."""
import pytest


@pytest.fixture
def init_workflow(load_script):
    return load_script("skills/workflow/scripts/init-workflow.py")


def test_write_if_missing_creates_file(init_workflow, tmp_path):
    target = tmp_path / "foo.txt"
    init_workflow.write_if_missing(target, "hello")
    assert target.read_text() == "hello"


def test_write_if_missing_does_not_overwrite(init_workflow, tmp_path):
    target = tmp_path / "foo.txt"
    target.write_text("original")
    init_workflow.write_if_missing(target, "new content")
    assert target.read_text() == "original"


def test_main_creates_full_structure(init_workflow, tmp_path, monkeypatch):
    root = tmp_path / "myworkflow"
    monkeypatch.setattr("sys.argv", ["init-workflow.py", str(root)])
    exit_code = init_workflow.main()
    assert exit_code == 0

    for name in init_workflow.FOLDERS:
        assert (root / name).is_dir()

    for name in ["CLAUDE.md", "Snakefile", "config.yaml", "pixi.toml", ".gitignore"]:
        assert (root / name).is_file()

    # scratch/ is gitignored wholesale, so it doesn't get a .gitkeep; the
    # rest do, since they were created empty.
    assert not (root / "scratch" / ".gitkeep").exists()
    for name in init_workflow.GITKEEP_FOLDERS:
        assert (root / name / ".gitkeep").exists()


def test_main_is_idempotent(init_workflow, tmp_path, monkeypatch):
    root = tmp_path / "myworkflow"
    monkeypatch.setattr("sys.argv", ["init-workflow.py", str(root)])
    init_workflow.main()
    (root / "CLAUDE.md").write_text("custom content")
    init_workflow.main()
    assert (root / "CLAUDE.md").read_text() == "custom content"


def test_main_default_root(init_workflow, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["init-workflow.py"])
    init_workflow.main()
    assert (tmp_path / init_workflow.DEFAULT_ROOT).is_dir()


def test_gitkeep_not_added_once_content_exists(init_workflow, tmp_path, monkeypatch):
    """A folder that already has real content (e.g. a pre-existing data/
    file) shouldn't get a .gitkeep added on top of it."""
    root = tmp_path / "myworkflow"
    (root / "data").mkdir(parents=True)
    (root / "data" / "real.csv").write_text("a,b\n1,2\n")
    monkeypatch.setattr("sys.argv", ["init-workflow.py", str(root)])
    init_workflow.main()
    assert not (root / "data" / ".gitkeep").exists()


def test_config_yaml_is_a_valid_mapping(init_workflow, tmp_path, monkeypatch):
    """Regression test: config.yaml must stay a mapping, not an empty/null
    file - Snakemake's configfile: directive rejects the latter."""
    root = tmp_path / "myworkflow"
    monkeypatch.setattr("sys.argv", ["init-workflow.py", str(root)])
    init_workflow.main()
    assert "{}" in (root / "config.yaml").read_text()
