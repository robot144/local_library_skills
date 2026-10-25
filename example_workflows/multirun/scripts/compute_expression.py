import math
import sys
from pathlib import Path

with open(snakemake.log[0], "w") as log:
    sys.stderr = sys.stdout = log

    expression = Path(snakemake.input[0]).read_text().strip()

    # Restricted namespace: math functions/constants only, no builtins -
    # this "model" only ever needs to evaluate an arithmetic expression,
    # not run arbitrary code.
    allowed_names = {
        name: getattr(math, name) for name in dir(math) if not name.startswith("_")
    }
    answer = eval(expression, {"__builtins__": {}}, allowed_names)

    Path(snakemake.output[0]).write_text(f"{expression} = {answer}\n")
    print(f"computed {expression} -> {answer}")
