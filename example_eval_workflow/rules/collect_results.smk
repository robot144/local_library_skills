rule collect_results:
    input:
        subject=[f"scratch/{c}/{s}/subject_result.json" for c, s in CASE_SIZE_PAIRS],
        judge=[f"scratch/{c}/{s}/judge_result.json" for c, s in CASE_SIZE_PAIRS],
    output:
        "outputs/eval_summary.txt",
    script:
        "../scripts/collect_results.py"
