"""Stage 6: build the slideshow from order.csv.

16:9, black background, one picture/video per slide, fitted without crop/distortion and centered, no text.
Auto-advance via <p:transition advTm="..."/> injected into each slide's XML, right after <p:clrMapOvr>:
photos get equal time (show length = music length, see show_plan.py), videos advance when they end.
Videos are muted and start by themselves. The music (music.m4a) is an audio object placed off-slide on
slide 1 that starts with the show and plays across all slides (numSld = slide count).
Usage: python3 stage6_pptx.py [--order build/order.csv] [--out build/graduation_slideshow.pptx] [--no-music]
"""
import argparse
from pathlib import Path
from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Emu
from common import OUT
from show_plan import load

AUDIO_RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/audio"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
ap = argparse.ArgumentParser()
ap.add_argument("--order", default=str(OUT / "order.csv"))
ap.add_argument("--out", default=str(OUT / "graduation_slideshow.pptx"))
ap.add_argument("--no-music", action="store_true")
args = ap.parse_args()
base = Path(args.order).parent
rows, photo_ms = load(Path(args.order))

prs = Presentation()
prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)   # 13.333" x 7.5" = 16:9
SW, SH = prs.slide_width, prs.slide_height
blank = prs.slide_layouts[6]


def add_transition(slide, adv_ms):
    """<p:transition advTm=.../> right after <p:clrMapOvr> (schema order: cSld, clrMapOvr, transition, timing)."""
    sld = slide._element
    for old in sld.findall(qn("p:transition")):
        sld.remove(old)
    tr = etree.SubElement(sld, qn("p:transition"))
    tr.set("advTm", str(adv_ms))
    anchor = sld.find(qn("p:clrMapOvr"))
    if anchor is None:
        anchor = sld.find(qn("p:cSld"))
    anchor.addnext(tr)


def set_timing(slide, media):
    """media: list of (spid, dur_ms, 'video'|'audio', num_slides). All start when the slide starts."""
    sld = slide._element
    for old in sld.findall(qn("p:timing")):
        sld.remove(old)
    nid = iter(range(4, 100))
    calls = "".join(
        f'<p:par><p:cTn id="{next(nid)}" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold" '
        f'nodeType="{"afterEffect" if k else "withEffect"}"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
        f'<p:cmd type="call" cmd="playFrom(0.0)"><p:cBhvr><p:cTn id="{next(nid)}" dur="{d}" fill="hold"/>'
        f'<p:tgtEl><p:spTgt spid="{s}"/></p:tgtEl></p:cBhvr></p:cmd></p:childTnLst></p:cTn></p:par>'
        for k, (s, d, kind, n) in enumerate(media))
    nodes = ""
    for s, d, kind, n in media:
        if kind == "video":
            nodes += (f'<p:video><p:cMediaNode vol="0" mute="1"><p:cTn id="{next(nid)}" fill="hold" display="0">'
                      f'<p:stCondLst><p:cond delay="indefinite"/></p:stCondLst></p:cTn>'
                      f'<p:tgtEl><p:spTgt spid="{s}"/></p:tgtEl></p:cMediaNode></p:video>')
        else:
            nodes += (f'<p:audio><p:cMediaNode vol="80000" numSld="{n}"><p:cTn id="{next(nid)}" fill="hold" display="0">'
                      f'<p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:endCondLst>'
                      f'<p:cond evt="onStopAudio" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:endCondLst></p:cTn>'
                      f'<p:tgtEl><p:spTgt spid="{s}"/></p:tgtEl></p:cMediaNode></p:audio>')
    xml = (f'<p:timing xmlns:p="{P_NS}"><p:tnLst><p:par>'
           f'<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
           f'<p:par><p:cTn id="2" fill="hold"><p:stCondLst><p:cond delay="indefinite"/>'
           f'<p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>'
           f'<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
           f'{calls}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>'
           f'{nodes}</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>')
    sld.find(qn("p:transition")).addnext(etree.fromstring(xml))


def add_audio(slide, path):
    """Audio object off the visible slide area (so no icon shows)."""
    icon = OUT / "_audio_icon.png"
    Image.new("RGB", (16, 16), (0, 0, 0)).save(icon)
    shp = slide.shapes.add_movie(str(path), -Emu(500000), -Emu(500000), Emu(300000), Emu(300000),
                                 poster_frame_image=str(icon), mime_type="audio/mp4")
    vf = shp._element.find(".//" + qn("a:videoFile"))
    rid = vf.get(qn("r:link"))
    af = etree.Element(qn("a:audioFile"))
    af.set(qn("r:link"), rid)
    vf.addprevious(af)
    vf.getparent().remove(vf)
    rel = slide.part.rels[rid]
    rel._reltype = AUDIO_RT
    rel.__dict__["reltype"] = AUDIO_RT   # reltype is a cached (lazy) property
    return shp


for k, r in enumerate(rows):
    video = r["סוג"] == "וידאו"
    img = base / (r["פוסטר"] if video else r["קובץ"])
    w, h = Image.open(img).size
    scale = min(SW / w, SH / h)
    pw, ph = int(w * scale), int(h * scale)
    slide = prs.slides.add_slide(blank)
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(0, 0, 0)
    media = []
    if video:
        mov = slide.shapes.add_movie(str(base / r["קובץ"]), (SW - pw) // 2, (SH - ph) // 2, pw, ph,
                                     poster_frame_image=str(img), mime_type="video/mp4")
        media.append((mov.shape_id, r["ms"], "video", 1))
    else:
        slide.shapes.add_picture(str(img), (SW - pw) // 2, (SH - ph) // 2, pw, ph)
    if k == 0 and not args.no_music:
        snd = add_audio(slide, OUT / "music.m4a")
        media.append((snd.shape_id, sum(x["ms"] for x in rows), "audio", len(rows)))
    add_transition(slide, r["ms"])
    if media:
        set_timing(slide, media)

prs.save(args.out)
print(f"slides: {len(rows)}  photo {photo_ms} ms  -> {args.out}  ({Path(args.out).stat().st_size / 1e6:.0f} MB)")
