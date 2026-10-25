rule transform:
    input:
        "outputs/raw.txt",
    output:
        "outputs/transformed.txt",
    log:
        "logs/transform.log",
    script:
        "../scripts/transform.py"
