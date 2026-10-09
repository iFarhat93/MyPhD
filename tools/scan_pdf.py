"""Render low-res page thumbnails and index every Figure/Table caption of a PDF.

usage: python -I tools/scan_pdf.py <pdf> <outdir>
writes <outdir>/pNNN.png and <outdir>/captions.json
"""
import sys, json, re, io
import pymupdf

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
pdf, outdir = sys.argv[1], sys.argv[2]
doc = pymupdf.open(pdf)
caps = []
for i, page in enumerate(doc):
    page.get_pixmap(dpi=60).save(f"{outdir}/p{i+1:03d}.png")
    for b in page.get_text("blocks"):
        x0, y0, x1, y1, txt = b[0], b[1], b[2], b[3], b[4].strip().replace("\n", " ")
        m = re.match(r"^(Fig\.|Table)\s+(\d+\.\d+)\s*[:.]?\s*(.*)", txt)
        if m:
            caps.append({"page": i + 1, "kind": m.group(1), "num": m.group(2),
                         "caption": m.group(3)[:200],
                         "bbox": [round(x0), round(y0), round(x1), round(y1)],
                         "page_w": round(page.rect.width), "page_h": round(page.rect.height)})
json.dump(caps, open(f"{outdir}/captions.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(caps), "captions found")
for c in caps:
    print(f"p{c['page']:3d} {c['kind']:5} {c['num']:>5}  y={c['bbox'][1]:>3}  {c['caption'][:100]}")
