#!/usr/bin/env python3
"""Coloca um post/story na fila como RASCUNHO (o agente usa isto).

Exemplos:
  python3 scripts/enqueue.py --date 2026-11-03 --slot radar --type story --image /tmp/story-radar.png
  python3 scripts/enqueue.py --date 2026-11-04 --slot feed --type carousel \
      --image s1.png --image s2.png --image s3.png --caption-file legenda.txt

--slot usa os horários do config.json (radar, noticia, voce_sabia, pergunta, feed)
ou --time HH:MM para um horário específico.
Depois: git add -A && git commit && git push.
"""
import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

p = argparse.ArgumentParser()
p.add_argument("--date", required=True, help="AAAA-MM-DD")
p.add_argument("--slot", required=True, help="radar | noticia | voce_sabia | pergunta | feed | outro nome")
p.add_argument("--type", required=True, choices=["story", "feed", "carousel"])
p.add_argument("--image", action="append", required=True)
p.add_argument("--caption-file")
p.add_argument("--time", help="HH:MM (substitui o horário do slot)")
p.add_argument("--summary", default="", help="tema em uma linha, para a prévia")
a = p.parse_args()

hhmm = a.time or (CFG["feed_slot"] if a.slot == "feed" else CFG["stories_slots"].get(a.slot))
if not hhmm:
    raise SystemExit(f"slot sem horário: {a.slot}; use --time")
h, m = map(int, hhmm.split(":"))
y, mo, d = map(int, a.date.split("-"))
at = datetime(y, mo, d, h, m, tzinfo=ZoneInfo(CFG["timezone"]))

item_id = f"{a.date}-{a.type}-{a.slot}"
mdir = ROOT / "media" / a.date
mdir.mkdir(parents=True, exist_ok=True)
rels = []
for i, src in enumerate(a.image, 1):
    ext = Path(src).suffix.lower() or ".png"
    if ext not in (".jpg", ".jpeg", ".png"):
        raise SystemExit("imagem precisa ser JPG ou PNG")
    name = f"{a.type}-{a.slot}" + (f"-{i:02d}" if len(a.image) > 1 else "") + ext
    shutil.copyfile(src, mdir / name)
    rels.append(f"media/{a.date}/{name}")

item = {
    "id": item_id,
    "type": a.type,
    "slot": a.slot,
    "summary": a.summary,
    "media": rels,
    "caption": Path(a.caption_file).read_text(encoding="utf-8").strip() if a.caption_file else "",
    "publish_at": at.isoformat(),
    "status": "rascunho",
    "created_at": datetime.now(ZoneInfo(CFG["timezone"])).isoformat(),
}
out = ROOT / "queue" / f"{item_id}.json"
out.write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(out.relative_to(ROOT))
