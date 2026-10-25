"""Unit tests for skills/agent-runner/scripts/run-agent.py.

These never actually launch a live agent session - subprocess.run is
mocked throughout, same pattern as test_summarize_workflow.py's
snakemake_summary tests. Launching a real nested `claude` session is a
different (and much heavier) kind of test - see the design doc's
testability discussion for why that's a deliberately separate concern.
"""
import json
import subprocess

import pytest


@pytest.fixture
def run_agent(load_script):
    return load_script("skills/agent-runner/scripts/run-agent.py")


# --- vendor resolution ---


def test_detect_vendor_from_env_present(run_agent, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    assert run_agent.detect_vendor_from_env() == "claude-code"


def test_detect_vendor_from_env_absent(run_agent, monkeypatch):
    monkeypatch.delenv("CLAUDECODE", raising=False)
    assert run_agent.detect_vendor_from_env() is None


def test_read_config_vendor_present(run_agent, tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("agent_vendor: claude-code\nother: 1\n")
    assert run_agent.read_config_vendor(config) == "claude-code"


def test_read_config_vendor_missing_file(run_agent, tmp_path):
    assert run_agent.read_config_vendor(tmp_path / "nope.yaml") is None


def test_read_config_vendor_key_absent(run_agent, tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("other: 1\n")
    assert run_agent.read_config_vendor(config) is None


def test_resolve_vendor_explicit_wins(run_agent, tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text("agent_vendor: codex\n")
    monkeypatch.setenv("CLAUDECODE", "1")
    assert run_agent.resolve_vendor("claude-code", config) == "claude-code"


def test_resolve_vendor_falls_back_to_config(run_agent, tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text("agent_vendor: claude-code\n")
    monkeypatch.delenv("CLAUDECODE", raising=False)
    assert run_agent.resolve_vendor(None, config) == "claude-code"


def test_resolve_vendor_falls_back_to_env(run_agent, tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    assert run_agent.resolve_vendor(None, tmp_path / "nope.yaml") == "claude-code"


def test_resolve_vendor_raises_when_nothing_resolves(run_agent, tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDECODE", raising=False)
    with pytest.raises(run_agent.VendorResolutionError):
        run_agent.resolve_vendor(None, tmp_path / "nope.yaml")


def test_write_default_vendor_to_config_writes_when_unset(run_agent, tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    config = tmp_path / "config.yaml"
    vendor = run_agent.write_default_vendor_to_config(config)
    assert vendor == "claude-code"
    assert "agent_vendor: claude-code" in config.read_text()


def test_write_default_vendor_to_config_preserves_existing_file_content(
    run_agent, tmp_path, monkeypatch
):
    monkeypatch.setenv("CLAUDECODE", "1")
    config = tmp_path / "config.yaml"
    config.write_text("some_param: 42\n")
    run_agent.write_default_vendor_to_config(config)
    text = config.read_text()
    assert "some_param: 42" in text
    assert "agent_vendor: claude-code" in text


def test_write_default_vendor_to_config_never_overwrites_existing_value(
    run_agent, tmp_path, monkeypatch
):
    monkeypatch.setenv("CLAUDECODE", "1")
    config = tmp_path / "config.yaml"
    config.write_text("agent_vendor: codex\n")
    vendor = run_agent.write_default_vendor_to_config(config)
    assert vendor == "codex"
    assert "agent_vendor: codex" in config.read_text()


def test_write_default_vendor_to_config_creates_parent_dir(run_agent, tmp_path, monkeypatch):
    """Regression test: confirmed by actually running the CLI end-to-end -
    scaffolding a config into a not-yet-existing workflow directory used to
    fail with FileNotFoundError because the parent dir was never created."""
    monkeypatch.setenv("CLAUDECODE", "1")
    config = tmp_path / "not_yet_created" / "config.yaml"
    vendor = run_agent.write_default_vendor_to_config(config)
    assert vendor == "claude-code"
    assert config.is_file()


def test_write_default_vendor_to_config_none_when_nothing_detected(
    run_agent, tmp_path, monkeypatch
):
    monkeypatch.delenv("CLAUDECODE", raising=False)
    config = tmp_path / "config.yaml"
    assert run_agent.write_default_vendor_to_config(config) is None
    assert not config.exists()


# --- ClaudeCodeAdapter.build_command (pure, no subprocess) ---


def test_build_command_basic(run_agent):
    adapter = run_agent.ClaudeCodeAdapter()
    cmd = adapter.build_command("hello", {})
    assert cmd == ["claude", "-p", "hello", "--output-format", "json"]


def test_build_command_with_settings(run_agent):
    adapter = run_agent.ClaudeCodeAdapter()
    cmd = adapter.build_command(
        "hello", {"model": "claude-sonnet-5", "permission_mode": "acceptEdits"}
    )
    assert "--model" in cmd and "claude-sonnet-5" in cmd
    assert "--permission-mode" in cmd and "acceptEdits" in cmd


def test_build_command_with_allowed_tools(run_agent):
    adapter = run_agent.ClaudeCodeAdapter()
    cmd = adapter.build_command("hello", {"allowed_tools": ["Bash(git *)", "Edit"]})
    i = cmd.index("--allowed-tools")
    assert cmd[i + 1 : i + 3] == ["Bash(git *)", "Edit"]


# --- size alias (small/medium/large -> this vendor's own model names) ---


@pytest.mark.parametrize(
    "size,expected_model",
    [("small", "haiku"), ("medium", "sonnet"), ("large", "opus")],
)
def test_build_command_size_alias_translates(run_agent, size, expected_model):
    adapter = run_agent.ClaudeCodeAdapter()
    cmd = adapter.build_command("hello", {"size": size})
    i = cmd.index("--model")
    assert cmd[i + 1] == expected_model


def test_build_command_explicit_model_wins_over_size(run_agent):
    adapter = run_agent.ClaudeCodeAdapter()
    cmd = adapter.build_command("hello", {"size": "large", "model": "claude-fable-5"})
    i = cmd.index("--model")
    assert cmd[i + 1] == "claude-fable-5"
    assert cmd.count("--model") == 1


def test_build_command_unknown_size_raises_clear_error(run_agent):
    adapter = run_agent.ClaudeCodeAdapter()
    with pytest.raises(ValueError, match="unknown size 'xl'"):
        adapter.build_command("hello", {"size": "xl"})


def test_build_command_no_model_flag_without_model_or_size(run_agent):
    adapter = run_agent.ClaudeCodeAdapter()
    cmd = adapter.build_command("hello", {})
    assert "--model" not in cmd


def test_launch_agent_rejects_unknown_size_cleanly(run_agent, tmp_path):
    with pytest.raises(ValueError, match="unknown size"):
        run_agent.launch_agent(
            "x", vendor="claude-code", cwd=tmp_path / "run",
            settings={"size": "xl"}, config_path=tmp_path / "nope.yaml",
        )


# --- list_available_models (pure parsing + subprocess wiring) ---

# Real response text, confirmed by actually running `claude -p "/model"
# --output-format json` (total_cost_usd: 0, free) - see agent-runner_design.md.
REAL_MODEL_LIST_RESULT = (
    "Current model: Sonnet 5 (default)\n"
    "Usage: /model <name>. Available: sonnet, opus, haiku, fable, best, "
    "sonnet[1m], opus[1m], fable[1m], opusplan, default, or a full model ID."
)


def test_list_available_models_parses_real_response(run_agent, monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        _fake_claude_run(stdout=json.dumps({"result": REAL_MODEL_LIST_RESULT})),
    )
    info = run_agent.list_available_models()
    assert info["current"] == "Sonnet 5 (default)"
    assert "sonnet" in info["available"]
    assert "fable" in info["available"]
    assert "opusplan" in info["available"]


def test_list_available_models_invokes_slash_model_command(run_agent, monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(
            cmd, returncode=0, stdout=json.dumps({"result": REAL_MODEL_LIST_RESULT}), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    run_agent.list_available_models()
    assert captured["cmd"] == ["claude", "-p", "/model", "--output-format", "json"]


def test_list_available_models_none_on_unparseable_response(run_agent, monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", _fake_claude_run(stdout=json.dumps({"result": "something unexpected"}))
    )
    assert run_agent.list_available_models() is None


def test_list_available_models_none_on_non_json_stdout(run_agent, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_claude_run(stdout="not json"))
    assert run_agent.list_available_models() is None


def test_list_available_models_none_when_claude_missing(run_agent, monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert run_agent.list_available_models() is None


# --- launch_agent, with subprocess.run mocked ---


def _fake_claude_run(stdout='{"result": "ok"}', returncode=0, stderr=""):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=returncode, stdout=stdout, stderr=stderr)

    return fake_run


def test_launch_agent_happy_path(run_agent, tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_claude_run())
    result = run_agent.launch_agent(
        "do something",
        vendor="claude-code",
        cwd=tmp_path / "run",
        config_path=tmp_path / "nope.yaml",
    )
    assert result.vendor == "claude-code"
    assert result.exit_code == 0
    assert result.structured_output == {"result": "ok"}
    assert (tmp_path / "run" / "agent_transcript.json").read_text() == '{"result": "ok"}'


def test_launch_agent_captures_nonzero_exit(run_agent, tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_claude_run(stdout="", returncode=1, stderr="boom"))
    result = run_agent.launch_agent(
        "do something",
        vendor="claude-code",
        cwd=tmp_path / "run",
        config_path=tmp_path / "nope.yaml",
    )
    assert result.exit_code == 1
    assert (tmp_path / "run" / "agent_stderr.log").read_text() == "boom"


def test_launch_agent_handles_non_json_stdout(run_agent, tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_claude_run(stdout="not json"))
    result = run_agent.launch_agent(
        "do something",
        vendor="claude-code",
        cwd=tmp_path / "run",
        config_path=tmp_path / "nope.yaml",
    )
    assert result.structured_output is None


def test_launch_agent_creates_cwd(run_agent, tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_claude_run())
    target = tmp_path / "does" / "not" / "exist" / "yet"
    run_agent.launch_agent(
        "x", vendor="claude-code", cwd=target, config_path=tmp_path / "nope.yaml"
    )
    assert target.is_dir()


def test_launch_agent_raises_for_unresolvable_vendor(run_agent, tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDECODE", raising=False)
    with pytest.raises(run_agent.VendorResolutionError):
        run_agent.launch_agent(
            "x", vendor=None, cwd=tmp_path / "run", config_path=tmp_path / "nope.yaml"
        )


def test_launch_agent_raises_for_unimplemented_vendor(run_agent, tmp_path):
    with pytest.raises(run_agent.VendorResolutionError):
        run_agent.launch_agent(
            "x", vendor="codex", cwd=tmp_path / "run", config_path=tmp_path / "nope.yaml"
        )


def test_launch_agent_passes_actual_command_to_subprocess(run_agent, tmp_path, monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    run_agent.launch_agent(
        "summarize this",
        vendor="claude-code",
        cwd=tmp_path / "run",
        settings={"model": "claude-sonnet-5"},
        config_path=tmp_path / "nope.yaml",
    )
    assert captured["cmd"][:3] == ["claude", "-p", "summarize this"]
    assert captured["cwd"] == tmp_path / "run"


# --- model-not-found detection, fetching available models (real response shapes) ---

# Confirmed by testing: `claude -p --model <bad> "..."` exits 0 (not a
# nonzero return code!) but sets is_error: true, api_error_status: 404.
BAD_MODEL_RESULT = {
    "is_error": True,
    "api_error_status": 404,
    "result": (
        "There's an issue with the selected model (totally-bogus-model-xyz). "
        "It may not exist or you may not have access to it. Run --model to "
        "pick a different model."
    ),
}


def _fake_run_with_model_followup(main_stdout):
    """Returns the given stdout for the main `claude -p <prompt> ...` call,
    and the real /model response for the follow-up discovery call."""

    def fake_run(cmd, **kwargs):
        if "/model" in cmd:
            return subprocess.CompletedProcess(
                cmd, returncode=0,
                stdout=json.dumps({"result": REAL_MODEL_LIST_RESULT}), stderr="",
            )
        return subprocess.CompletedProcess(cmd, returncode=0, stdout=main_stdout, stderr="")

    return fake_run


def test_launch_agent_fetches_available_models_on_bad_model_error(run_agent, tmp_path, monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", _fake_run_with_model_followup(json.dumps(BAD_MODEL_RESULT))
    )
    result = run_agent.launch_agent(
        "x",
        vendor="claude-code",
        cwd=tmp_path / "run",
        settings={"model": "totally-bogus-model-xyz"},
        config_path=tmp_path / "nope.yaml",
    )
    assert result.available_models is not None
    assert result.available_models["current"] == "Sonnet 5 (default)"
    assert "sonnet" in result.available_models["available"]


def test_launch_agent_no_available_models_on_success(run_agent, tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_claude_run(stdout='{"is_error": false, "result": "ok"}'))
    result = run_agent.launch_agent(
        "x", vendor="claude-code", cwd=tmp_path / "run", config_path=tmp_path / "nope.yaml"
    )
    assert result.available_models is None


def test_launch_agent_no_available_models_on_unrelated_error(run_agent, tmp_path, monkeypatch):
    """An is_error: true that has nothing to do with the model shouldn't
    trigger a (free, but unnecessary) available-models lookup."""
    monkeypatch.setattr(
        subprocess, "run",
        _fake_claude_run(stdout=json.dumps({"is_error": True, "result": "network timeout"})),
    )
    result = run_agent.launch_agent(
        "x", vendor="claude-code", cwd=tmp_path / "run", config_path=tmp_path / "nope.yaml"
    )
    assert result.available_models is None


# --- CLI entry point ---


def test_main_detect_vendor_prints_and_succeeds(run_agent, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setattr("sys.argv", ["run-agent.py", "--detect-vendor"])
    exit_code = run_agent.main()
    assert exit_code == 0
    assert "claude-code" in capsys.readouterr().out


def test_main_detect_vendor_fails_when_nothing_detected(run_agent, monkeypatch, capsys):
    monkeypatch.delenv("CLAUDECODE", raising=False)
    monkeypatch.setattr("sys.argv", ["run-agent.py", "--detect-vendor"])
    exit_code = run_agent.main()
    assert exit_code == 1
    assert "no vendor detected" in capsys.readouterr().err


def test_main_write_default_vendor(run_agent, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDECODE", "1")
    config = tmp_path / "config.yaml"
    monkeypatch.setattr("sys.argv", ["run-agent.py", "--write-default-vendor", str(config)])
    exit_code = run_agent.main()
    assert exit_code == 0
    assert "claude-code" in capsys.readouterr().out
    assert config.is_file()


def test_main_requires_prompt_or_prompt_file(run_agent, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["run-agent.py"])
    exit_code = run_agent.main()
    assert exit_code == 1
    assert "provide a prompt" in capsys.readouterr().err


def test_main_launches_with_prompt_and_writes_output(run_agent, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(subprocess, "run", _fake_claude_run(stdout='{"ok": true}'))
    monkeypatch.chdir(tmp_path)
    output_path = tmp_path / "result.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run-agent.py",
            "hello",
            "--vendor",
            "claude-code",
            "--cwd",
            str(tmp_path / "run"),
            "--output",
            str(output_path),
        ],
    )
    exit_code = run_agent.main()
    assert exit_code == 0
    assert output_path.is_file()
    out = capsys.readouterr().out
    assert "vendor=claude-code" in out
    assert "exit_code=0" in out


def test_main_size_flag_wires_through_to_model_flag(run_agent, tmp_path, monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, returncode=0, stdout='{"ok": true}', stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["run-agent.py", "hello", "--vendor", "claude-code", "--size", "small",
         "--cwd", str(tmp_path / "run")],
    )
    exit_code = run_agent.main()
    assert exit_code == 0
    i = captured["cmd"].index("--model")
    assert captured["cmd"][i + 1] == "haiku"


def test_main_list_models(run_agent, monkeypatch, capsys):
    monkeypatch.setattr(
        subprocess, "run",
        _fake_claude_run(stdout=json.dumps({"result": REAL_MODEL_LIST_RESULT})),
    )
    monkeypatch.setattr("sys.argv", ["run-agent.py", "--list-models"])
    exit_code = run_agent.main()
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Sonnet 5 (default)" in out
    assert "fable" in out


def test_main_list_models_fails_cleanly_when_unparseable(run_agent, monkeypatch, capsys):
    monkeypatch.setattr(subprocess, "run", _fake_claude_run(stdout="not json"))
    monkeypatch.setattr("sys.argv", ["run-agent.py", "--list-models"])
    exit_code = run_agent.main()
    assert exit_code == 1
    assert "could not determine available models" in capsys.readouterr().err


def test_main_reports_failure_for_bad_model_despite_zero_exit_code(
    run_agent, tmp_path, monkeypatch, capsys
):
    """Regression test, confirmed by testing: `claude -p --model <bad> ...`
    exits 0 even though is_error: true - main() must not report success
    just because the subprocess's own return code was 0."""
    monkeypatch.setattr(
        subprocess, "run", _fake_run_with_model_followup(json.dumps(BAD_MODEL_RESULT))
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["run-agent.py", "x", "--vendor", "claude-code", "--model", "totally-bogus-model-xyz",
         "--cwd", str(tmp_path / "run")],
    )
    exit_code = run_agent.main()
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "exit_code=0" in out  # the underlying process really did exit 0
    assert "Hint:" in out
    assert "fable" in out
