rule compute_expression:
    input:
        "scratch/{case}/expression.txt",
    output:
        "scratch/{case}/result.txt",
    log:
        "logs/{case}/compute_expression.log",
    script:
        "../scripts/compute_expression.py"
