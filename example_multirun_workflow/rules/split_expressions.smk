rule split_expressions:
    input:
        "data/expressions.txt",
    output:
        expand("scratch/{case}/expression.txt", case=CASES),
    script:
        "../scripts/split_expressions.py"
