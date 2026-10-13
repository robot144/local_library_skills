rule split_test_cases:
    input:
        "data/test_cases.yaml",
    output:
        first=expand("scratch/{case}/first.txt", case=CASES),
        second=expand("scratch/{case}/second.txt", case=CASES),
    script:
        "../scripts/split_test_cases.py"
