# VVC in Silicon — my PhD, explained

A small static site that explains a PhD thesis to two audiences at once: people who want the whole idea in ten
scenes, and people who want the depth. The first instance is Ibrahim Farhat's thesis
*Efficient hardware designs of the new Versatile Video Coding (VVC) tools for ASIC platforms*
(INSA Rennes / IETR, defended 31 May 2022, HAL `tel-04477217`).

The site is in `docs/` and is served as is by GitHub Pages:

| page | what it is |
|------|------------|
| `docs/index.html` | **The story in 10 scenes.** 3D and animated visuals (three.js), two sentences per scene, a “Go deeper” fold with the thesis figures and numbers, optional voice-over. |
| `docs/explainer.html` | **Narrated walkthrough.** 21 steps, 30 minutes of narration with a highlighted transcript, expert notes, glossary, record. |
| `docs/platforms.html` | **The Silicon Ladder.** CPU, GPU, FPGA and ASIC level by level, with a 20-question quiz. |

Everything is relative paths and static files: no build step is needed to serve it, and the three pages work
from disk, from `python -m http.server --directory docs`, or from GitHub Pages.

## Publish on GitHub Pages

```powershell
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Then on GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main`,
folder: `/docs` → Save.** The site appears at `https://<you>.github.io/<repo>/` a minute later.
`docs/.nojekyll` is there so GitHub serves the files untouched.

## How it is built

```
content/        what a human writes
  phd.json        record, people, organisations, timeline, publications, sources
  steps.json      the 21-step walkthrough: parts, steps (points, figures, expert note, sources, narration), charts
  story.json      the ten scene narrations
  glossary.json   terms and one-line definitions
tools/          the pipeline
  pages/story.html      the story page (hand-written: scenes, three.js code, charts)
  pages/platforms.html  the Silicon Ladder (hand-written)
  template.html         the walkthrough template, filled from content/ by build_site.py
  scan_pdf.py           page thumbnails + an index of every figure/table caption of a PDF
  extract_figures.py    crops each figure to PNG by locating its caption
  make_audio.py         narration MP3 + sentence timings (edge-tts, free neural voices), only for changed text
  build_site.py         writes docs/ (and page fragments under work/artifact/ for claude.ai artifacts)
docs/           the published site (committed)
work/, site/    intermediate outputs (ignored)
sources/        the manuscript, papers and metadata, kept local only (ignored; the manuscript and papers are open access on HAL/arXiv)
```

Rebuild after any change:

```powershell
# figures (once per thesis)
uv run --python 3.12 --with pymupdf python -I tools/scan_pdf.py sources/thesis/<thesis>.pdf work/thumbs
uv run --python 3.12 --with pymupdf python -I tools/extract_figures.py sources/thesis/<thesis>.pdf work/thumbs/captions.json work/figures 160
# voice-over (only narrations whose text changed are re-synthesised)
uv run --python 3.12 --with edge-tts python -I tools/make_audio.py
# the site
python -I tools/build_site.py
```

## Reusing it for another PhD

1. Put the manuscript in `sources/thesis/` and run the two figure commands; `work/thumbs/captions.json` lists every
   figure with its page.
2. Fill `content/phd.json` from the HAL / theses.fr record (the HAL REST API is open; the HTML pages are bot-walled,
   `curl -A "curl/8.4.0"` fetches the PDF).
3. Write `content/steps.json` (the deep layer) and `content/story.json` (the ten narrations); adapt the scenes in
   `tools/pages/story.html` to the thesis's own mechanisms.
4. Generate the audio, build, push.

## What is public here, and what is not

The site names the academic supervision (directors and supervisor at INSA Rennes / IETR) and refers to the
industrial partner without naming it or its staff. Published co-author lists in the publications section are
reproduced as printed.

## Sources

Thesis manuscript (HAL tel-04477217); HAL and theses.fr metadata; the thesis papers (ICASSP 2020, IEEE TCE 2021,
IEEE TCE 2022, PCS 2022) and later IETR papers; Google Scholar; insa-rennes.fr; IETR / OpenVVC pages; Horowitz
(ISSCC 2014), Hameed et al. (ISCA 2010), Kuon & Rose (IEEE TCAD 2007), Hennessy & Patterson (CACM 2019).
