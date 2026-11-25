"""Stage 6: build the slideshow from order.csv.

16:9, black background, one picture per slide, fitted without crop/distortion and centered, no text,
auto-advance every 3 s via <p:transition advTm="3000"/> injected into each slide's XML.
Video slides: the (muted) video fills the slide the same way, starts by itself when the slide appears
(timing XML replaced with an on-slide-start play command), and the slide advances when the video ends
(advTm = video length, rounded up to 0.1 s).
Usage: python3 stage6_pptx.py [--order build/order.csv] [--out build/graduation_slideshow.pptx]
"""
import argparse, csv, math
from pathlib import Path
from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Emu
from common import OUT as BUILD

ADV_MS = 3000
ap = argparse.ArgumentParser()
ap.add_argument("--order", default=str(BUILD / "order.csv"))
ap.add_argument("--out", default=str(BUILD / "graduation_slideshow.pptx"))
args = ap.parse_args()
base = Path(args.order).parent

prs = Presentation()
prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)   # 13.333" x 7.5" = 16:9
SW, SH = prs.slide_width, prs.slide_height
blank = prs.slide_layouts[6]


def autoplay(slide, spid, dur_ms):
    """Replace python-pptx's click-to-play timing with: play from 0 as soon as the slide starts."""
    sld = slide._element
    for old in sld.findall(qn("p:timing")):
        sld.remove(old)
    xml = f"""<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:tnLst><p:par>
<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>
<p:par><p:cTn id="2" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>
<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>
<p:par><p:cTn id="4" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold" nodeType="afterEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>
<p:cmd type="call" cmd="playFrom(0.0)"><p:cBhvr><p:cTn id="5" dur="{dur_ms}" fill="hold"/><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:cmd>
</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>
<p:video><p:cMediaNode vol="0" mute="1"><p:cTn id="6" fill="hold" display="0"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst></p:cTn><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cMediaNode></p:video>
</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>"""
    timing = etree.fromstring(xml.replace("\n", ""))
    tr = sld.find(qn("p:transition"))
    (tr if tr is not None else sld.find(qn("p:clrMapOvr"))).addnext(timing)


def add_transition(slide, adv_ms=ADV_MS):
    """Insert <p:transition advTm=.../> right after <p:clrMapOvr> (schema order: cSld, clrMapOvr, transition, timing)."""
    sld = slide._element
    for old in sld.findall(qn("p:transition")):
        sld.remove(old)
    tr = etree.Element(qn("p:transition"))
    tr.set("advTm", str(adv_ms))
    anchor = sld.find(qn("p:clrMapOvr"))
    if anchor is None:
        anchor = sld.find(qn("p:cSld"))
    anchor.addnext(tr)


rows = list(csv.DictReader(open(args.order, encoding="utf-8-sig")))
for r in rows:
    video = r.get("סוג") == "וידאו"
    img = base / (r["פוסטר"] if video else r["קובץ"])
    w, h = Image.open(img).size
    scale = min(SW / w, SH / h)
    pw, ph = int(w * scale), int(h * scale)
    slide = prs.slides.add_slide(blank)
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(0, 0, 0)
    if video:
        dur_ms = int(math.ceil(float(r["משך"]) * 10)) * 100
        mov = slide.shapes.add_movie(str(base / r["קובץ"]), (SW - pw) // 2, (SH - ph) // 2, pw, ph,
                                     poster_frame_image=str(img), mime_type="video/mp4")
        add_transition(slide, dur_ms)
        autoplay(slide, mov.shape_id, dur_ms)
    else:
        slide.shapes.add_picture(str(img), (SW - pw) // 2, (SH - ph) // 2, pw, ph)
        add_transition(slide)

prs.save(args.out)
print(f"slides: {len(rows)} -> {args.out}")
