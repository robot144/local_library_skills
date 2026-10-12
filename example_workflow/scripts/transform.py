import sys

with open(snakemake.log[0], "w") as log:
    sys.stderr = sys.stdout = log

    with open(snakemake.input[0]) as f:
        content = f.read()

    transformed = content.strip().upper() + "\n"

    with open(snakemake.output[0], "w") as f:
        f.write(transformed)

    print(f"transformed {snakemake.input[0]} -> {snakemake.output[0]}")
