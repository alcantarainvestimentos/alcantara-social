#!/usr/bin/env python3
"""Confere cada perfil de radar/perfis.json pela API oficial (business_discovery)
e grava radar/perfis_check.json com: existe/comercial, seguidores, nº de posts,
média de curtidas e comentários dos últimos 6 posts e data do último post."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish as P  # reaproveita graph() e resolve()

ROOT = Path(__file__).resolve().parent.parent


def main():
    if not P.TOKEN:
        sys.exit("IG_TOKEN ausente")
    P.resolve()
    perfis = json.loads((ROOT / "radar/perfis.json").read_text(encoding="utf-8"))["perfis"]
    out = []
    for p in perfis:
        u = p["u"]
        fields = (f"business_discovery.username({u})"
                  "{username,name,followers_count,media_count,"
                  "media.limit(6){like_count,comments_count,timestamp}}")
        try:
            r = P.graph("GET", P.IG, {"fields": fields})["business_discovery"]
            media = r.get("media", {}).get("data", [])
            likes = [m.get("like_count", 0) or 0 for m in media]
            coms = [m.get("comments_count", 0) or 0 for m in media]
            out.append({
                "u": u, "cat": p["cat"], "ok": True, "nome": r.get("name"),
                "seguidores": r.get("followers_count"), "posts": r.get("media_count"),
                "media_curtidas": round(sum(likes) / len(likes)) if likes else 0,
                "media_comentarios": round(sum(coms) / len(coms)) if coms else 0,
                "ultimo_post": media[0]["timestamp"][:10] if media else None,
            })
            print(f"ok  {u}: {r.get('followers_count')} seguidores")
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            out.append({"u": u, "cat": p["cat"], "ok": False, "erro": msg[:160]})
            print(f"--  {u}: {msg[:120]}")
    (ROOT / "radar/perfis_check.json").write_text(json.dumps(
        {"verificado_em": datetime.now(timezone.utc).isoformat(), "perfis": out},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
