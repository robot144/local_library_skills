rule judge_result:
    input:
        prompt="scratch/{case}/second.txt",
        # the judge's cwd (below) IS the subject's output dir for this same
        # (case, size) - declaring subject_transcript.json as an input (even
        # though the judge reads it itself, not Snakemake) gives Snakemake
        # the dependency edge it needs.
        subject_transcript="scratch/{case}/{size}/run/subject_transcript.json",
    output:
        result="scratch/{case}/{size}/judge_result.json",
    log:
        "logs/{case}/{size}/judge_result.log",
    shell:
        f"python3 {AGENT_RUNNER} "
        "--prompt-file {input.prompt} --cwd scratch/{wildcards.case}/{wildcards.size}/run "
        "--config config.yaml --output {output.result} &> {log}"
