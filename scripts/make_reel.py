#!/usr/bin/env python3
"""Gera um Reel vertical (1080x1920, MP4/H.264) sem rosto, no visual da Alcantara.

Uso:
  python3 scripts/make_reel.py <spec.json> <saida.mp4> [--capa capa.jpg]

spec.json:
{
  "date": "07 NOV 2026",
  "scenes": [
    {"tag": "RADAR", "dur": 3.5, "body": "<h1 class='a' style='font-size:110px'>O dólar <span class='gold'>bateu R$ 5,49</span></h1>"},
    {"tag": "POR QUE", "dur": 5, "body": "<p class='a'>...</p><p class='a' style='--d:.4s'>...</p>"},
    ...
  ],
  "src": "Fonte: ...",            (opcional, aparece na última cena)
  "audio": true                  (trilha ambiente sintetizada, discreta; padrão true)
}

Elementos com class 'a' entram com fade+subida; use style='--d:.4s' para atrasar.
A última cena recebe automaticamente "Siga @alcantarainvestimentos".
Mantenha ~250px do topo e ~420px do rodapé livres (interface do Reels).
"""
import base64
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
EMB = ROOT / "assets" / "emblem.png"
FPS = 24

CSS = """*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;background:#070707}
.c{position:relative;width:1080px;height:1920px;overflow:hidden;font-family:'Inter',sans-serif;color:#efe6d2;
 background:radial-gradient(1000px 800px at 85% 8%,rgba(201,154,60,.16),transparent 60%),radial-gradient(800px 700px at 0% 100%,rgba(201,154,60,.09),transparent 60%),#070707}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(214,175,92,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(214,175,92,.05) 1px,transparent 1px);background-size:90px 90px;animation:drift 12s linear both}
@keyframes drift{from{transform:translateY(0)}to{transform:translateY(-90px)}}
.top{position:absolute;left:90px;right:90px;top:250px;display:flex;justify-content:space-between;align-items:center}
.tag{font-size:28px;letter-spacing:.4em;color:#d6af5c;font-weight:500}
.tag:before{content:"";display:inline-block;width:50px;height:1px;background:#d6af5c;vertical-align:middle;margin-right:20px}
.date{font-size:24px;letter-spacing:.15em;color:#9e937d}
.body{position:absolute;left:90px;right:90px;top:420px;bottom:440px;display:flex;flex-direction:column;justify-content:center;gap:44px}
.gold{font-weight:700;background:linear-gradient(100deg,#f7dc8f 0%,#d6a640 45%,#fff0b8 60%,#b9862c 100%);-webkit-background-clip:text;color:transparent}
h1{font-family:'TeX Gyre Pagella',serif;font-weight:400;color:#f4ecdb;line-height:1.06;font-size:100px}
p{font-size:42px;line-height:1.45;color:#cbbfa6;font-weight:300}
p b{color:#efe6d2;font-weight:500}
.big{font-family:'TeX Gyre Pagella',serif;font-size:180px;line-height:1}
.box{border:1px solid rgba(214,175,92,.6);background:linear-gradient(180deg,rgba(214,175,92,.10),rgba(214,175,92,.02));padding:44px 50px}
.foot{position:absolute;left:90px;right:90px;bottom:300px;display:flex;justify-content:space-between;align-items:center}
.foot img{width:70px}
.foot span{font-size:24px;letter-spacing:.3em;color:#d6af5c}
.src{position:absolute;left:90px;right:90px;bottom:400px;font-size:24px;color:#7d7462}
.a{opacity:0;animation:up .7s cubic-bezier(.2,.7,.2,1) var(--d,0s) both}
@keyframes up{from{opacity:0;transform:translateY(40px)}to{opacity:1;transform:none}}
.scene{animation:out .35s ease-in var(--end) both}
@keyframes out{to{opacity:0}}
.cta{font-size:34px;letter-spacing:.06em;color:#efe6d2}
"""


def page(scene, date, emb, last, src):
    extra = ""
    if last:
        extra += "<p class='a cta' style='--d:.9s'>Siga <span class='gold'>@alcantarainvestimentos</span></p>"
    s = f"<div class='src'>{src}</div>" if (last and src) else ""
    end = max(scene["dur"] - 0.35, 0.1)
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"
            f"<div class='c'><div class='grid'></div><div class='scene' style='--end:{end}s;position:absolute;inset:0'>"
            f"<div class='top'><span class='tag a'>{scene['tag']}</span><span class='date a'>{date}</span></div>"
            f"<div class='body'>{scene['body']}{extra}</div>{s}"
            f"<div class='foot'><span>ALCANTARA INVESTIMENTOS</span><img src='data:image/png;base64,{emb}'></div>"
            f"</div></div></body></html>")


def main():
    spec_path, out = sys.argv[1], sys.argv[2]
    capa = sys.argv[sys.argv.index("--capa") + 1] if "--capa" in sys.argv else None
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    emb = base64.b64encode(EMB.read_bytes()).decode()
    tmp = Path(tempfile.mkdtemp(prefix="reel-"))
    n = 0
    total = 0.0
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        scenes = spec["scenes"]
        for i, sc in enumerate(scenes):
            last = i == len(scenes) - 1
            html = tmp / f"s{i}.html"
            html.write_text(page(sc, spec.get("date", ""), emb, last, spec.get("src", "")), encoding="utf-8")
            pg.goto(html.as_uri())
            pg.wait_for_timeout(250)
            pg.evaluate("document.getAnimations().forEach(a=>a.pause())")
            frames = int(sc["dur"] * FPS)
            for f in range(frames):
                t = f * 1000 / FPS
                pg.evaluate(f"document.getAnimations().forEach(a=>a.currentTime={t})")
                pg.screenshot(path=str(tmp / f"f{n:05d}.jpg"), type="jpeg", quality=92)
                if capa and i == 0 and f == frames - 1:
                    shutil.copyfile(tmp / f"f{n:05d}.jpg", capa)
                n += 1
            total += sc["dur"]
        b.close()

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%05d.jpg")]
    if spec.get("audio", True):
        # trilha ambiente sintetizada (acorde suave) com fade in/out
        cmd += ["-f", "lavfi", "-t", f"{total:.2f}", "-i",
                "aevalsrc=0.05*sin(2*PI*110*t)+0.035*sin(2*PI*164.8*t)+0.03*sin(2*PI*220*t)+0.02*sin(2*PI*277.2*t)*(0.6+0.4*sin(2*PI*0.25*t)):s=44100:c=stereo"]
        afade = f"afade=t=in:d=1.2,afade=t=out:st={max(total - 1.5, 0):.2f}:d=1.5,lowpass=f=1800"
        cmd += ["-af", afade, "-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-r", "30", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"ok: {out} ({total:.1f}s)")


if __name__ == "__main__":
    main()
