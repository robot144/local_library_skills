from pathlib import Path

with open(snakemake.input[0]) as f:
    expressions = [line.strip() for line in f if line.strip()]

assert len(expressions) == len(snakemake.output), (
    "number of expressions must match the case count computed in the Snakefile"
)

for out_path, expression in zip(snakemake.output, expressions):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(expression + "\n")
