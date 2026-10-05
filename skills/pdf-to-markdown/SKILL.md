---
name: pdf-to-markdown
description: Convert a PDF to searchable markdown using marker-pdf, a local GPU/CPU-accelerated OCR pipeline (no API key, no internet needed after first-run model download). Use when a PDF is too large to read page-by-page, when you need to grep/search/cite specific content repeatedly, or when you want its tables and equations as structured markdown/LaTeX rather than page images. Auto-installs its own pixi environment on first use and auto-chunks PDFs of any size. Not a substitute for reading the PDF directly when verifying something that matters — see "Accuracy" below.
---

# PDF to Markdown

Converts a PDF to markdown using [marker](https://github.com/datalab-to/marker) (`marker-pdf`), running fully locally via a `llama.cpp` VLM backend. Built from hands-on testing across several real documents (an 18-page ML paper with its arXiv LaTeX source for ground truth, a 16-page math-heavy statistics tutorial, and a 651-page engineering manual) — the workflow below reflects what actually worked, not just what the tool claims to do.

## Platform check — do this first, before running any script

All scripts here are bash (`.sh`). **Check your own environment info for the platform before invoking any of them** — a native Windows shell (cmd.exe/PowerShell) cannot execute a `.sh` file at all, so a script has no way to detect or report that itself; the check has to happen before you try to run one. If the platform isn't Linux or macOS: tell the user these scripts need a bash environment — WSL on Windows is the standard option — and don't attempt to run them directly in a native Windows shell. (Untested on WSL/Git Bash/Cygwin specifically — if you're in one of those, it may work, but say so rather than assuming.)

## Prerequisites

**Required:**
- `bash` (all scripts here are bash — see "Platform check" above)
- [`pixi`](https://pixi.sh/) — `install.sh` checks for it explicitly and fails with a clear error if it's missing; this skill does not install `pixi` itself
- Internet access, at least for first install (pulls packages via `pixi`) and the first conversion (downloads ~1.8GB of models from Hugging Face) — fully offline after that
- A few GB of free disk space (pixi environment + cached models)

**Optional, degrades rather than fails if missing:**
- `pdfinfo` (from the `poppler-utils` package on most Linux distros, or `poppler` via Homebrew on macOS) — used for page-count detection. Without it, auto-chunking silently gets skipped, which re-exposes the memory-exhaustion crash chunking exists to prevent on large PDFs. Worth installing if you'll convert anything big: `apt install poppler-utils` / `brew install poppler` / `dnf install poppler-utils`.
- `nvidia-smi` or `vulkaninfo` — used only by `estimate.sh`'s GPU-detection heuristic, for the time estimate's human-readable message. You don't need to separately install either of these: `nvidia-smi` ships with the NVIDIA driver itself (present automatically if you have a working NVIDIA GPU setup), and `vulkaninfo` comes from `vulkan-tools` (Debian/Ubuntu) or your distro's Vulkan utilities package, often already present on graphics-capable systems. If neither is found, `estimate.sh` just assumes CPU and gives a more conservative (slower) estimate — actual conversion still does its own independent, correct GPU detection regardless of what `estimate.sh` guessed.

**Not needed by the skill itself:** `git`/`gh` are only involved in *getting* this skill onto disk in the first place (see the parent repo's README) — once installed, none of these scripts invoke either.

## When to use this

Good fit: a PDF you'll search/reference repeatedly, a large PDF (tens to hundreds of pages) impractical to read page-by-page, or a PDF whose tables/equations you want as structured markdown/LaTeX for grepping or quoting.

Not needed: a short PDF (a few pages) you're only going to look at once — just read it directly with your PDF-reading tool. Converting has a real cost (install time on first use, conversion time scaling with page count and OCR mode) that isn't worth paying for a one-off skim.

## Quick start

```bash
scripts/pdf2md.sh input.pdf                    # -> input/input.md, next to the PDF
scripts/pdf2md.sh input.pdf --force_ocr         # see "force_ocr or not" below
scripts/pdf2md.sh input.pdf --output_dir ./out  # explicit output location
```

First call auto-installs a dedicated pixi environment at `~/.local/share/pdf2md-env` (override with `PDF2MD_ENV_DIR`) — this does **not** touch the target project's own files or dependencies. Install takes a few minutes; the ~1.8GB of models download separately, on the **first actual conversion** (install only runs `--help`/`--version` checks, which don't touch them).

Both are one-time costs — but note the model cache (`~/.cache/huggingface`, `~/.cache/datalab`) is **global to the machine, not scoped to `$PDF2MD_ENV_DIR`**. Removing and recreating the environment (e.g. via `uninstall.sh` then reinstalling) won't trigger a re-download; the next conversion just reuses the existing cache. Conversely, if you ever run `uninstall.sh --models`, that clears the cache for *every* environment on the machine that uses these models, not just the one being uninstalled.

Output layout, for `foo.pdf`: `foo/foo.md` (markdown), `foo/foo_meta.json` (table of contents with page numbers, per-page block counts — see "Citing back into the PDF" below), `foo/_page_N_*.jpeg` (extracted figures/diagrams).

## Before converting: estimate, and confirm if it's long

**Run `scripts/estimate.sh input.pdf [--force_ocr]` before `pdf2md.sh` whenever the page count is non-trivial (tens of pages or more) or unknown.** It detects GPU vs. CPU and prints a time estimate plus a machine-parseable summary line, without running the actual conversion:

```
$ scripts/estimate.sh thesis.pdf --force_ocr
No GPU detected. Converting this 34-page document (--force_ocr mode) is estimated to take around 1h 25m (~150s/page, rough estimate - formula/table-dense content can be slower).

pages=34 device=CPU mode=--force_ocr seconds=5100
```

If you're an agent using this skill on a user's behalf: parse the `seconds=` field, and if it's more than a few minutes, **ask the user for confirmation before running `pdf2md.sh`** — don't silently kick off a long background conversion they didn't sign up for. Surface the human-readable line (it already names the device and gives a plain-language estimate) rather than re-deriving your own phrasing. Estimates are rough — flat per-page rates measured on one machine, not a model of the specific document's content — so treat the number as "the right order of magnitude to decide whether to ask," not a precise forecast. The CPU + default-mode case is the least reliable (see the script's own caveat note): every display equation goes through the VLM regardless of `--force_ocr`, so an equation-dense document can run several times longer than the flat estimate.

## `--force_ocr` or not

This is a real quality/speed tradeoff, not a default to blindly pick — decide based on the document:

- **Formula/math-heavy document** (inline equations, statistics/physics/ML papers): use `--force_ocr`. Without it, inline math is extracted as plain PDF text with stray `<sup>` tags instead of LaTeX, and symbols get mangled (Σ silently becomes a literal "P", primes become "0", subscripts render as superscripts). With `--force_ocr`, inline formulas come out as real `$...$` LaTeX. Costs roughly 3-5x the conversion time of the default path — worth it when the math is the point.
- **Text/table-heavy document** (manuals, reports, prose with occasional simple tables): the default (no `--force_ocr`) is usually fine and meaningfully faster — it uses the PDF's text layer directly instead of full-page OCR.
- Both modes produce good LaTeX for *display* equations (the `$$...$$` block kind) already — `--force_ocr`'s main value-add is inline math and symbol fidelity, not display equations.

## Rough timing

Measured, not estimated — all on a 24-core hybrid laptop CPU (Intel Ultra 9 275HX) with an NVIDIA RTX PRO 4000 Blackwell GPU (Vulkan offload, automatic):

| Document | Mode | Device | Pages | Total | ~sec/page |
|---|---|---|---|---|---|
| ML paper, mostly text/figures | `--force_ocr` | GPU | 18 | 124 s | **6.9 s** |
| Statistics paper, ~95 display equations (very math-dense) | `--force_ocr` | GPU | 16 | 177 s | **11 s** |
| Engineering manual, mixed content, chunked | `--force_ocr` | GPU | 651 | 102.5 min | **9.4 s** (varied 5-18 s/page chunk-to-chunk) |
| Statistics paper (1 page) | default | CPU-only (forced) | 1 | 80 s wall | — mostly fixed ~15-20 s startup, not a clean per-page rate |
| Statistics paper (1 page) | `--force_ocr` | CPU-only (forced) | 1 | 386 s wall | — same startup caveat |

**Rule of thumb: ~7-12 sec/page on GPU with `--force_ocr`**, varying with how equation/table-dense the content is — text-only pages are faster, formula-dense pages slower. We don't have a clean large-document GPU benchmark for the default (non-`--force_ocr`) path; single-page tests suggest most of its cost is fixed startup rather than per-page work, so it should scale *better* than `--force_ocr` per page, not worse — but that's inference from the mechanism, not a measurement.

**No GPU, or forcing CPU-only**: expect roughly an order of magnitude slower for `--force_ocr` work specifically — a direct same-page, same-hardware comparison (GPU vs. CPU-only, same binary, same page) measured **~15x slower on CPU** (372 s vs. 24.8 s marker time). A historical reference point from an *untuned* CPU (auto thread-detect, no GPU, old llama.cpp binary, default mode): ~15 sec/page on a mostly-text 18-page document — but a 16-page document that was unusually equation-dense (~6 display equations/page) hit ~274 sec/page in the same (CPU, default, no `--force_ocr`) mode, because **every display equation goes through the VLM regardless of `--force_ocr`** — only *inline* math is gated by that flag. Equation density, not just page count, is the real cost driver on CPU.

## Large PDFs: automatic, but know what's happening

PDFs over 100 pages (`PDF2MD_CHUNK_THRESHOLD`) are automatically split into 50-page chunks (`PDF2MD_CHUNK_SIZE`), each converted in its own process, then merged — markdown concatenated in order, images copied (marker names them with absolute page numbers, so no collisions), `_meta.json` merged by concatenating its list fields. This exists because a single `marker_single` process converting a 651-page manual with `--force_ocr` silently exhausted memory and crashed after 34 minutes with zero output — chunking resets memory between chunks and sidesteps this entirely. The chunking is resumable: a failed run's completed chunks are skipped on retry, not redone.

You don't need to do anything for this to work — it's automatic. Just be aware that a genuinely huge document will take a while (the 651-page test case took ~100 minutes with `--force_ocr`), and that's expected, not a hang.

## Accuracy: verify anything that matters before relying on it

**Treat the markdown as a fast, searchable index into the document — not as ground truth.** It's good enough to navigate, search, and get the gist, but specific claims (a number, a formula, a quoted sentence, a citation) should be checked against the actual PDF page before you present them as fact, the same way you'd double-check a paraphrase. This isn't a vague disclaimer — these are the specific failure modes found by diffing conversions against known-correct sources:

- **Silently dropped content.** A sentence, or an entire section heading plus its opening text, can vanish from the markdown body with no trace — not truncated, not marked, just absent — typically at a column or page-layout boundary. The `_meta.json` table of contents can still list a heading that's missing from the markdown body; that mismatch is itself a tell.
- **Broken/malformed cross-reference links.** Citation and equation references (`[12]`, `(3.4)`) sometimes become dead links to nonexistent anchors, and occasionally a citation like `[36,41]` gets split into two separate malformed links with mismatched brackets.
- **Row-vector / matrix equation garbling.** A simple row vector next to a matrix inverse, e.g. `(c₁₂ c₁₃)`, can come out as a broken pseudo-matrix with a phantom row and a duplicated entry. Seen reproducibly across multiple unrelated documents — a genuine weak point of this pipeline's equation parsing, not a one-off glitch.
- **Compound subscripts/accents getting mangled or dropped.** Range subscripts like `x_{0:t}` can lose the range and collapse to `x_t`; stacked accents (e.g. a tilde *and* a dot on the same symbol, used to distinguish "noise-adjusted" from "velocity" in a derivation) can collapse to just one accent, making two genuinely different quantities look identical. If a sentence says "X will be adjusted to Y" but the markdown shows the identical symbol on both sides, that's the tell — a self-contradiction is often more informative than a diff would be, since you frequently won't have a ground-truth source to diff against.
- **Table columns silently misaligned.** A spurious extra header cell can shift every subsequent column by one position for every row — including shifting a quantity out of the table entirely. Checking whether a table's claims match the prose discussing the same quantity nearby is a decent internal-consistency check.
- **CPU vs. GPU runs are not byte-identical.** The same binary converting the same page can produce different (not just differently-timed) output depending on whether inference ran on CPU or GPU — floating-point differences shift the VLM's token-by-token decoding. Re-running the exact same conversion on the exact same hardware *is* deterministic; comparing runs across different machines or forcing CPU-only for a benchmark is not guaranteed to match a GPU run's content, only its correctness.

**Practical workflow**: read the PDF directly (most PDF-reading tools handle this natively, page-range-limited for large files) to check anything load-bearing, rather than trusting the conversion. For citing a specific claim, see below.

## Citing back into the PDF

`<name>_meta.json`'s `table_of_contents` list gives each heading's `page_id` — the **0-indexed physical PDF page** it starts on (not the document's own printed page number, which is often offset by front matter). To find what page a piece of content is on:

1. Find the relevant heading (or the nearest one before your content) in `table_of_contents`.
2. Its `page_id` + 1 = the PDF page to read directly for verification/citation.
3. If no heading is close enough, find the nearest `![](_page_N_...)` image reference in the markdown instead — `N` is also an absolute, 0-indexed page number.

This is how you'd answer "what page is X on" or "give me a citation" without re-deriving it by scrolling: grep the markdown, locate a nearby heading or image reference, map it to a page number via `_meta.json`, then optionally confirm by reading that PDF page directly.

## Tuning notes (optional, situational)

- **GPU offload is automatic and usually desirable, but is two separate paths with different requirements — no CUDA Toolkit install needed either way, just the right driver for whichever path applies:**
  - `llama-server` (the VLM doing OCR/equations — most of the work) uses **Vulkan** (confirmed via `ldd` showing `libggml-vulkan.so.0`/`libvulkan.so.1`), which works across NVIDIA, AMD, and Intel GPUs with a working Vulkan driver.
  - PyTorch's layout-detection model separately auto-selects **CUDA** specifically (`torch.cuda.is_available()`), which is NVIDIA-only — on AMD/Intel GPUs this step silently falls back to CPU even while `llama-server` is using the GPU fine via Vulkan.
  - Either way, no need to separately install the CUDA Toolkit SDK — the `pixi`-installed PyTorch wheel bundles its own CUDA runtime; you just need a working NVIDIA driver already present for that bundled runtime to find the GPU. No configuration needed for any of this — it's automatic, not something to "fix."
- **Hybrid CPU (P+E core) machines**: if conversions seem to only use a handful of cores even without a GPU, llama.cpp's thread auto-detect may have badly under-counted — see the note `install.sh` prints after setup, and set `LLAMA_CPP_EXTRA_ARGS="-t N -tb N"` (N = P-core count) in the env's `pixi.toml`. Counterintuitively, using *all* cores (P+E mixed) can be slower than P-cores only, since llama.cpp's decode loop syncs every thread each token and E-cores become the straggler.
- Env vars for the installed environment: `PDF2MD_ENV_DIR` (default `~/.local/share/pdf2md-env`), `PDF2MD_CHUNK_THRESHOLD` (default 100), `PDF2MD_CHUNK_SIZE` (default 50), `PDF2MD_KEEP_CHUNKS` (unset by default — set to inspect per-chunk raw output after a large conversion).

## Uninstalling

```bash
scripts/uninstall.sh              # removes the environment at PDF2MD_ENV_DIR
scripts/uninstall.sh --models     # also removes the ~1.8GB of downloaded models
```

Safe to do wholesale (no surgical manifest editing needed) because `install.sh` always creates a fresh, dedicated environment rather than reusing or modifying an existing project's `pixi.toml` — unlike installing marker-pdf directly into a project. Refuses to touch anything that doesn't contain a `pixi.toml`, or that resolves to `$HOME` or `/`, as a guard against a misconfigured `PDF2MD_ENV_DIR`. Models live in shared caches (`~/.cache/datalab`, `~/.cache/huggingface`) outside the environment directory, so they're kept by default even when removing the environment — pass `--models` to also remove them.
