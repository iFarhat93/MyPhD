"""Crop every figure of a PDF to PNG, located by its caption block.

usage: python -I tools/extract_figures.py <pdf> <captions.json> <outdir> [dpi]
Strategy: for a caption "Fig. X.Y" the figure sits in the band between the previous
caption on the page (or the page top) and the caption. Vector drawings and images in
that band are clustered by vertical gaps; the cluster nearest the caption is the figure.
Text blocks overlapping that cluster vertically (axis labels, box names) are added.
"""
import sys, json, io
import pymupdf

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
pdf, capfile, outdir = sys.argv[1:4]
dpi = int(sys.argv[4]) if len(sys.argv) > 4 else 160
doc = pymupdf.open(pdf)
caps = json.load(open(capfile, encoding="utf-8"))
by_page = {}
for c in caps:
    by_page.setdefault(c["page"], []).append(c)

def figure_rect(page, cap, anchors):
    cy0 = cap["bbox"][1]
    tops = [a["bbox"][3] for a in anchors if a is not cap and a["bbox"][3] <= cy0 - 1]
    band_top = max(tops) if tops else 30
    rects = []
    for d in page.get_drawings():
        r = d["rect"]
        if r.y0 >= band_top - 2 and r.y1 <= cy0 + 2 and (r.width > 0.5 or r.height > 0.5):
            rects.append(pymupdf.Rect(r))
    for info in page.get_image_info():
        r = pymupdf.Rect(info["bbox"])
        if r.y0 >= band_top - 2 and r.y1 <= cy0 + 2:
            rects.append(r)
    blocks = [pymupdf.Rect(b[:4]) for b in page.get_text("blocks")]
    if rects:
        rects.sort(key=lambda r: r.y0)
        clusters, cur_y1 = [[rects[0]]], rects[0].y1
        for r in rects[1:]:
            if r.y0 - cur_y1 > 14:
                clusters.append([r]); cur_y1 = r.y1
            else:
                clusters[-1].append(r); cur_y1 = max(cur_y1, r.y1)
        u = pymupdf.Rect(clusters[-1][0])
        for r in clusters[-1]:
            u |= r
        for br in blocks:  # pull in labels that sit beside/inside the drawing
            if br.y1 <= cy0 + 1 and br.y0 >= band_top - 1 and br.y1 > u.y0 - 3 and br.y0 < u.y1 + 3:
                u |= br
        return u, "graphics"
    # fallback: everything after the last paragraph-like block above the caption
    body = [b for b in blocks if b.y1 <= cy0 and b.y0 >= band_top and b.width > 0.6 * page.rect.width and b.height > 20]
    top = max((b.y1 for b in body), default=band_top)
    u = None
    for br in blocks:
        if br.y0 >= top - 1 and br.y1 <= cy0 + 1:
            u = br if u is None else (u | br)
    return (u, "text-only") if u else (None, "none")

n = 0
for pno, anchors in sorted(by_page.items()):
    page = doc[pno - 1]
    for cap in anchors:
        if cap["kind"] != "Fig.":
            continue
        u, how = figure_rect(page, cap, anchors)
        if u is None:
            print(f"fig {cap['num']:>5} p{pno}: NOT FOUND"); continue
        clip = (u + (-8, -8, 8, 8)) & page.rect; clip.y1 = min(clip.y1, cap["bbox"][1] - 1)
        pix = page.get_pixmap(clip=clip, dpi=dpi)
        out = f"{outdir}/fig_{cap['num'].replace('.', '_')}.png"
        pix.save(out); n += 1
        print(f"fig {cap['num']:>5} p{pno:3d} {how:9s} {pix.width}x{pix.height}  {cap['caption'][:70]}")
print(n, "figures written")
