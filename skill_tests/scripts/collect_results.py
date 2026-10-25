import json
from pathlib import Path


def load_structured(path):
    data = json.loads(Path(path).read_text())
    return data.get("structured_output") or {}


def format_seconds(duration_ms):
    if duration_ms is None:
        return None
    return f"{duration_ms / 1000:.2f}s"


lines = []
for subject_path, judge_path in zip(snakemake.input.subject, snakemake.input.judge):
    subject_path = Path(subject_path)
    size = subject_path.parent.name
    case = subject_path.parent.parent.name
    label = case if size == "default" else f"{case} [{size}]"

    subject = load_structured(subject_path)
    judge = load_structured(judge_path)

    verdict_text = (judge.get("result") or "(no result)").strip()
    upper = verdict_text.upper()
    if upper.startswith("PASS"):
        verdict = "PASS"
    elif upper.startswith("FAIL"):
        verdict = "FAIL"
    else:
        verdict = "UNKNOWN"

    subject_cost = subject.get("total_cost_usd")
    judge_cost = judge.get("total_cost_usd")
    # duration_ms is claude's own total wall-clock time for the call (not
    # duration_api_ms, which excludes local overhead) - the number that
    # actually matches what "speed" means when comparing models/runs.
    subject_time = format_seconds(subject.get("duration_ms"))
    judge_time = format_seconds(judge.get("duration_ms"))

    lines.append(f"{label}: {verdict}")
    if subject_cost is not None or subject_time is not None:
        cost_part = f"${subject_cost:.4f}" if subject_cost is not None else "?"
        time_part = subject_time or "?"
        lines.append(f"  action cost: {cost_part}  time: {time_part}")
    if judge_cost is not None or judge_time is not None:
        cost_part = f"${judge_cost:.4f}" if judge_cost is not None else "?"
        time_part = judge_time or "?"
        lines.append(f"  judge cost: {cost_part}  time: {time_part} (verification overhead)")
    lines.append(f"  judge said: {verdict_text}")
    lines.append("")

Path(snakemake.output[0]).write_text("\n".join(lines) + "\n")
print(f"Wrote summary for {len(snakemake.input.subject)} case(s) to {snakemake.output[0]}")
