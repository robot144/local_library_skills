from pathlib import Path

with open(snakemake.output[0], "w") as out:
    for path in snakemake.input:
        out.write(Path(path).read_text())
