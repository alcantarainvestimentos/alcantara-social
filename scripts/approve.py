#!/usr/bin/env python3
"""Aprova ou recusa rascunhos da fila (o agente usa isto quando o Kaynander responde).

  python3 scripts/approve.py --date 2026-11-03                 # aprova todos os rascunhos do dia
  python3 scripts/approve.py --date 2026-11-03 --slot pergunta --reject
  python3 scripts/approve.py --list                            # mostra a fila
Depois: git add -A && git commit && git push.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
TZ = ZoneInfo(json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["timezone"])

p = argparse.ArgumentParser()
p.add_argument("--date")
p.add_argument("--slot", action="append", help="aprova/recusa só estes slots (pode repetir)")
p.add_argument("--reject", action="store_true")
p.add_argument("--list", action="store_true")
a = p.parse_args()

files = sorted((ROOT / "queue").glob("*.json"))
if a.list:
    for f in files:
        it = json.loads(f.read_text(encoding="utf-8"))
        print(f"{it['publish_at'][:16]}  {it['status']:<10} {it['type']:<8} {it['slot']:<11} {it.get('summary','')}")
    raise SystemExit
if not a.date:
    raise SystemExit("use --date AAAA-MM-DD")

changed = 0
for f in files:
    it = json.loads(f.read_text(encoding="utf-8"))
    if not it["id"].startswith(a.date) or it["status"] != "rascunho":
        continue
    if a.slot and it["slot"] not in a.slot:
        continue
    it["status"] = "recusado" if a.reject else "aprovado"
    it["reviewed_at"] = datetime.now(TZ).isoformat()
    f.write_text(json.dumps(it, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{it['status']}: {f.name}")
    changed += 1
print(f"{changed} item(ns) alterado(s)")
