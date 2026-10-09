"""Generate voice-over MP3s with Microsoft Edge neural voices (edge-tts).

usage:
  uv run --python 3.12 --with edge-tts python -I tools/make_audio.py [--set steps|story|all] [--voice V] [--rate R] [--force] [--only 03,07]

Sets:
  steps  content/steps.json  (field "narration" of each step)  -> docs/assets/audio/step-NN.mp3
  story  content/story.json  (field "narration" of each scene) -> docs/assets/audio/scene-NN.mp3
Sentence timings go to work/audio/<name>.cues.json together with a hash of the text, so a
narration is only re-synthesised when its text changes (or with --force).
"""
import argparse, asyncio, hashlib, json, re, sys, time
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "docs" / "assets" / "audio"
CUES_DIR = ROOT / "work" / "audio"
SETS = {
    "steps": (ROOT / "content" / "steps.json", "steps", "step-{id}"),
    "story": (ROOT / "content" / "story.json", "scenes", "scene-{id}"),
}
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9'\"(])")


def split_sentences(text):
    return [s.strip() for s in SENT_SPLIT.split(text.strip()) if s.strip()]


def text_hash(text):
    return hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:12]


async def synth(name, text, voice, rate, force, sem):
    mp3 = AUDIO_DIR / f"{name}.mp3"
    cues_path = CUES_DIR / f"{name}.cues.json"
    sha = text_hash(text)
    if mp3.exists() and cues_path.exists() and not force:
        try:
            prev = json.loads(cues_path.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
        if prev.get("text_sha") == sha:
            return name, "kept", prev.get("duration", 0)
    async with sem:
        for attempt in range(3):
            try:
                try:
                    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="SentenceBoundary")
                    mode = "sentence"
                except TypeError:
                    comm = edge_tts.Communicate(text, voice, rate=rate)
                    mode = "word"
                audio, marks = bytearray(), []
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        audio.extend(chunk["data"])
                    elif chunk["type"] in ("SentenceBoundary", "WordBoundary"):
                        marks.append((chunk["offset"] / 1e7, chunk["duration"] / 1e7, chunk["text"]))
                if not audio:
                    raise RuntimeError("no audio returned")
                break
            except Exception as exc:
                if attempt == 2:
                    return name, f"FAILED: {exc}", 0
                await asyncio.sleep(2 + attempt * 3)
    mp3.write_bytes(audio)
    cues = []
    if mode == "sentence":
        cues = [{"start": round(t, 3), "end": round(t + d, 3), "text": txt.strip()} for t, d, txt in marks]
    else:
        wi = 0
        for s in split_sentences(text):
            n = len(s.split()); seg = marks[wi:wi + n]; wi += n
            if seg:
                cues.append({"start": round(seg[0][0], 3), "end": round(seg[-1][0] + seg[-1][1], 3), "text": s})
    duration = round(cues[-1]["end"] + 0.4, 3) if cues else 0
    CUES_DIR.mkdir(parents=True, exist_ok=True)
    cues_path.write_text(json.dumps({"voice": voice, "rate": rate, "mode": mode, "text_sha": sha, "duration": duration,
                                     "cues": cues}, ensure_ascii=False, indent=1), encoding="utf-8")
    return name, f"ok ({len(audio) // 1024} KB, {len(cues)} cues)", duration


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="all", choices=["steps", "story", "all"])
    ap.add_argument("--voice", default="en-US-AndrewMultilingualNeural")
    ap.add_argument("--rate", default="-4%")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--parallel", type=int, default=3)
    args = ap.parse_args()
    jobs = []
    for key in (["steps", "story"] if args.set == "all" else [args.set]):
        path, field, pattern = SETS[key]
        if not path.exists():
            continue
        items = json.loads(path.read_text(encoding="utf-8"))[field]
        if args.only:
            wanted = set(args.only.split(","))
            items = [it for it in items if it["id"] in wanted]
        jobs += [(pattern.format(id=it["id"]), it["narration"]) for it in items if it.get("narration")]
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(args.parallel)
    t0 = time.time()
    results = await asyncio.gather(*(synth(n, t, args.voice, args.rate, args.force, sem) for n, t in jobs))
    total = 0
    for name, status, dur in results:
        total += dur
        print(f"{name}: {status}  {dur:6.1f} s")
    print(f"total narration {total/60:.1f} min, done in {time.time()-t0:.0f} s")
    if any("FAILED" in r[1] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
