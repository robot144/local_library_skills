"""Unit tests for skills/workflow/scripts/summarize-workflow.py."""
import subprocess

import pytest


@pytest.fixture
def summarize_workflow(load_script):
    return load_script("skills/workflow/scripts/summarize-workflow.py")


def test_get_purpose_reads_title(summarize_workflow, tmp_path):
    (tmp_path / "CLAUDE.md").write_text("<!-- marker -->\n# My Workflow\n\nbody")
    assert summarize_workflow.get_purpose(tmp_path) == "My Workflow"


def test_get_purpose_missing_file(summarize_workflow, tmp_path):
    assert "no CLAUDE.md" in summarize_workflow.get_purpose(tmp_path)


def test_get_purpose_missing_title_line(summarize_workflow, tmp_path):
    (tmp_path / "CLAUDE.md").write_text("no heading here\n")
    assert "no title line" in summarize_workflow.get_purpose(tmp_path)


def test_declared_rules(summarize_workflow, tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "a.smk").write_text("rule foo:\n    output: 'x'\n")
    (rules_dir / "b.smk").write_text(
        "rule bar:\n    output: 'y'\n\nrule baz:\n    output: 'z'\n"
    )
    rules = summarize_workflow.declared_rules(tmp_path)
    assert set(rules) == {"foo", "bar", "baz"}
    assert str(rules["foo"]) == "rules/a.smk"


def test_declared_rules_no_rules_dir(summarize_workflow, tmp_path):
    assert summarize_workflow.declared_rules(tmp_path) == {}


def test_included_rule_files(summarize_workflow, tmp_path):
    (tmp_path / "Snakefile").write_text(
        'configfile: "config.yaml"\ninclude: "rules/a.smk"\ninclude: "rules/b.smk"\n'
    )
    included = summarize_workflow.included_rule_files(tmp_path)
    assert included == {"rules/a.smk", "rules/b.smk"}


def test_included_rule_files_missing_snakefile(summarize_workflow, tmp_path):
    assert summarize_workflow.included_rule_files(tmp_path) == set()


def test_immediate_subdirs(summarize_workflow, tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "file.txt").write_text("x")
    assert summarize_workflow.immediate_subdirs(tmp_path) == {"a", "b"}


def test_top_level_file_count_ignores_gitkeep(summarize_workflow, tmp_path):
    (tmp_path / ".gitkeep").touch()
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.txt").write_text("y")
    assert summarize_workflow.top_level_file_count(tmp_path) == 2


def _make_rule_drift_workflow(root):
    rules_dir = root / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "orphan.smk").write_text("rule orphan:\n    output: 'o'\n")
    (root / "Snakefile").write_text(
        'configfile: "config.yaml"\ninclude: "rules/missing.smk"\n'
    )
    (root / "config.yaml").write_text("{}\n")


def test_main_flags_rule_drift(summarize_workflow, tmp_path, monkeypatch, capsys):
    _make_rule_drift_workflow(tmp_path)
    monkeypatch.setattr("sys.argv", ["summarize-workflow.py", str(tmp_path)])
    summarize_workflow.main()
    out = capsys.readouterr().out
    assert "orphan" in out and "NOT included in Snakefile" in out
    assert "rules/missing.smk" in out and "doesn't exist" in out


def test_main_flat_outputs_not_falsely_flagged(summarize_workflow, tmp_path, monkeypatch, capsys):
    """Regression test: a case present in scratch/ but 'missing' from a
    *flat* outputs/ (no per-case subfolders at all) must not be flagged
    as having run without producing output - outputs/ simply isn't
    organized per-case here, so there's nothing to compare against."""
    (tmp_path / "scratch" / "case1").mkdir(parents=True)
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "combined.csv").write_text("x")
    monkeypatch.setattr("sys.argv", ["summarize-workflow.py", str(tmp_path)])
    summarize_workflow.main()
    out = capsys.readouterr().out
    assert "ran but no kept output yet" not in out
    assert "not checked per-case" in out


def test_main_per_case_flags_missing_output(summarize_workflow, tmp_path, monkeypatch, capsys):
    """A case with its own scratch/ subfolder but no matching outputs/
    subfolder (both per-case) should be flagged."""
    (tmp_path / "scratch" / "case1").mkdir(parents=True)
    (tmp_path / "outputs" / "case2").mkdir(parents=True)
    monkeypatch.setattr("sys.argv", ["summarize-workflow.py", str(tmp_path)])
    summarize_workflow.main()
    out = capsys.readouterr().out
    assert "case1: scratch=y outputs=n" in out
    assert "ran but no kept output yet" in out


def test_snakemake_summary_invokes_pixi_run_snakemake(summarize_workflow, tmp_path, monkeypatch):
    calls = {}

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        calls["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="summary output\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    rc = summarize_workflow.snakemake_summary(tmp_path, "outputs/x.csv")
    assert rc == 0
    assert calls["cmd"] == ["pixi", "run", "snakemake", "--summary", "outputs/x.csv"]
    assert calls["cwd"] == tmp_path


def test_snakemake_summary_propagates_nonzero_exit(summarize_workflow, tmp_path, monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    rc = summarize_workflow.snakemake_summary(tmp_path, "target")
    assert rc == 1


def test_snakemake_summary_missing_pixi_command(summarize_workflow, tmp_path, monkeypatch, capsys):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "run", fake_run)
    rc = summarize_workflow.snakemake_summary(tmp_path, "target")
    assert rc == 1
    assert "'pixi' command" in capsys.readouterr().err
