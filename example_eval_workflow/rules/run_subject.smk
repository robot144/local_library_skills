rule run_subject:
    input:
        prompt="scratch/{case}/first.txt",
    output:
        result="scratch/{case}/{size}/subject_result.json",
        transcript="scratch/{case}/{size}/run/subject_transcript.json",
    log:
        "logs/{case}/{size}/run_subject.log",
    params:
        # "default" -> no --size flag at all, not --size default (agent-runner
        # doesn't recognize "default" as one of its own size aliases).
        size_flag=lambda wc: "" if wc.size == "default" else f"--size {wc.size}",
        # Only test cases that need Write/Bash (not just a text response)
        # set permission_mode in test_cases.yaml.
        perm_flag=lambda wc: (
            f"--permission-mode {PERMISSION_MODES[wc.case]}" if PERMISSION_MODES.get(wc.case) else ""
        ),
    shell:
        "python3 ../skills/agent-runner/scripts/run-agent.py "
        "--prompt-file {input.prompt} --cwd scratch/{wildcards.case}/{wildcards.size}/run "
        "--config config.yaml {params.size_flag} {params.perm_flag} --output {output.result} &> {log} "
        "&& cp scratch/{wildcards.case}/{wildcards.size}/run/agent_transcript.json {output.transcript}"
