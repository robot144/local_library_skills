from pathlib import Path

import yaml

with open(snakemake.input[0]) as f:
    test_cases = yaml.safe_load(f) or []

assert len(test_cases) == len(snakemake.output.first) == len(snakemake.output.second), (
    "test_cases.yaml entries must match the case count computed in the Snakefile"
)

# Absolute, so prompt text is correct regardless of how deep the subject's
# cwd (scratch/{case}/{size}/run) is nested relative to this workflow dir.
PLACEHOLDERS = {
    "{EXAMPLE_DOCS}": str(Path("../example_docs").resolve()),
    "{LOCAL_LIBRARY_SKILL}": str(Path("../skills/local-library/SKILL.md").resolve()),
}


def fill(text):
    for placeholder, value in PLACEHOLDERS.items():
        text = text.replace(placeholder, value)
    return text


for tc, first_path, second_path in zip(test_cases, snakemake.output.first, snakemake.output.second):
    first_path = Path(first_path)
    second_path = Path(second_path)
    first_path.parent.mkdir(parents=True, exist_ok=True)
    first_path.write_text(fill(tc["first"]))
    second_path.write_text(fill(tc["second"]))
