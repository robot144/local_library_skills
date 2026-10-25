rule collect_results:
    input:
        expand("scratch/{case}/result.txt", case=CASES),
    output:
        "outputs/results.txt",
    script:
        "../scripts/collect_results.py"
