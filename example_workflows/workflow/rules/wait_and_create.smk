rule wait_and_create:
    output:
        "outputs/raw.txt",
    log:
        "logs/wait_and_create.log",
    shell:
        "(sleep 5 && echo 'hello from step 1' > {output}) &> {log}"
