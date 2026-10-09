"""Assemble the GitHub Pages site in docs/.

usage: python -I tools/build_site.py

Reads  tools/pages/story.html       the story in 10 scenes (page fragment: <title>, <style>, <!-- body -->, content)
       tools/pages/platforms.html   the Silicon Ladder (page fragment)
       tools/template.html          the narrated walkthrough template (page fragment + __DATA_JSON__)
       content/phd.json, content/steps.json, content/glossary.json, content/story.json
       work/audio/*.cues.json       sentence timings written by tools/make_audio.py
       work/figures/*.png           figure crops written by tools/extract_figures.py
Writes docs/index.html, docs/explainer.html, docs/platforms.html   (complete HTML documents)
       docs/assets/figures/*.png    only the figures the pages use
       work/artifact/*.html         the same pages as fragments, for publishing as claude.ai artifacts
A page fragment keeps its <title>, <link> and <style> before the "<!-- body -->" marker; wrap() moves
that part into <head> and the rest into <body>.
"""
import json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES, DOCS, ART = ROOT / "tools" / "pages", ROOT / "docs", ROOT / "work" / "artifact"
FIG_SRC, FIG_DST = ROOT / "work" / "figures", DOCS / "assets" / "figures"
AUDIO, CUES = DOCS / "assets" / "audio", ROOT / "work" / "audio"
HEAD = ('<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>html{color-scheme:light}body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>')


def load(name):
    return json.loads((ROOT / "content" / name).read_text(encoding="utf-8"))


def wrap(fragment):
    if "<!-- body -->" not in fragment:
        raise SystemExit("fragment lacks the <!-- body --> marker")
    head, body = fragment.split("<!-- body -->", 1)
    return f"<!doctype html>\n<html lang=\"en\">\n<head>\n{HEAD}\n{head.strip()}\n</head>\n<body>\n{body.strip()}\n</body>\n</html>\n"


def audio_info(name):
    mp3, cues = AUDIO / f"{name}.mp3", CUES / f"{name}.cues.json"
    if not mp3.exists():
        return None
    info = json.loads(cues.read_text(encoding="utf-8")) if cues.exists() else {"duration": 0, "cues": []}
    return {"src": f"assets/audio/{name}.mp3", "duration": info.get("duration", 0), "cues": info.get("cues", [])}


def copy_figures(names):
    FIG_DST.mkdir(parents=True, exist_ok=True)
    missing, copied = [], 0
    for f in sorted(set(names)):
        src, dst = FIG_SRC / f, FIG_DST / f
        if not src.exists() and not dst.exists():
            missing.append(f); continue
        if src.exists() and (not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime):
            shutil.copyfile(src, dst); copied += 1
    if missing:
        raise SystemExit("MISSING FIGURES: " + ", ".join(missing))
    return copied


def emit(name, fragment):
    ART.mkdir(parents=True, exist_ok=True)
    (ART / f"{name}.html").write_text(fragment, encoding="utf-8")
    out = DOCS / ("index.html" if name == "index" else f"{name}.html")
    out.write_text(wrap(fragment), encoding="utf-8")
    return out


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / ".nojekyll").touch()
    figs = []

    # 1. narrated walkthrough
    phd, steps, glossary = load("phd.json"), load("steps.json"), load("glossary.json")
    total, with_audio = 0.0, 0
    for step in steps["steps"]:
        figs += [f["file"] for f in step.get("figures", []) if "file" in f]
        a = audio_info(f"step-{step['id']}")
        if a:
            step["audio"] = a; with_audio += 1; total += a["duration"]
    data = {"phd": phd, "parts": steps["parts"], "charts": steps.get("charts", {}), "steps": steps["steps"],
            "glossary": glossary, "total_audio": round(total)}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    emit("explainer", (ROOT / "tools" / "template.html").read_text(encoding="utf-8").replace("__DATA_JSON__", payload))

    # 2. the story (hand-written page; scene audio durations injected as data attributes)
    story_html = (PAGES / "story.html").read_text(encoding="utf-8")
    story = load("story.json") if (ROOT / "content" / "story.json").exists() else {"scenes": []}
    durations = {}
    for sc in story["scenes"]:
        a = audio_info(f"scene-{sc['id']}")
        if a:
            durations[sc["id"]] = round(a["duration"])
    story_html = story_html.replace("__SCENE_AUDIO__", json.dumps(durations))
    figs += re.findall(r"assets/figures/(fig_[\w]+\.png)", story_html)
    emit("index", story_html)

    # 3. the Silicon Ladder
    plat = (PAGES / "platforms.html").read_text(encoding="utf-8")
    figs += re.findall(r"assets/figures/(fig_[\w]+\.png)", plat)
    emit("platforms", plat)

    copied = copy_figures(figs)
    print(f"docs/: index, explainer ({len(steps['steps'])} steps, audio {with_audio}/{len(steps['steps'])}, "
          f"{total/60:.1f} min), platforms · figures copied: {copied} · scene audio: {len(durations)}")


if __name__ == "__main__":
    main()
