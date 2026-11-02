#!/usr/bin/env python3
"""Publica no Instagram os itens APROVADOS da fila (queue/*.json) cujo horário já chegou.

Roda no GitHub Actions a cada 15 minutos. Publica no máximo 1 item por execução,
para os posts nunca saírem amontoados. Usa o token do segredo IG_TOKEN.

Status possíveis de um item:
  rascunho  -> criado pelo agente, esperando aprovação do Kaynander
  aprovado  -> liberado para publicar no horário (publish_at)
  publicado -> já está no Instagram
  erro      -> falhou max_attempts vezes (ver campo "error")
  expirado  -> foi aprovado tarde demais (mais de max_delay_hours depois do horário)
  recusado  -> o Kaynander não aprovou
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
TOKEN = os.environ.get("IG_TOKEN", "").strip()
API = f"{CFG['graph_host']}/{CFG['graph_version']}"
IG = CFG["ig_user_id"]


def graph(method, path, params):
    params = dict(params)
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        # nunca imprime o token
        raise RuntimeError(f"HTTP {e.code} em {path}: {body[:500]}") from None


def wait_ready(container_id, tries=30):
    for _ in range(tries):
        st = graph("GET", container_id, {"fields": "status_code,status"})
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {code}: {st.get('status')}")
        time.sleep(5)
    raise RuntimeError("container não ficou pronto a tempo")


def url_for(rel):
    return CFG["raw_base"] + urllib.parse.quote(rel)


def publish(item):
    kind = item["type"]
    media = item["media"]
    caption = item.get("caption", "")
    if kind == "story":
        c = graph("POST", f"{IG}/media", {"media_type": "STORIES", "image_url": url_for(media[0])})
        cid = c["id"]
    elif kind == "feed":
        c = graph("POST", f"{IG}/media", {"image_url": url_for(media[0]), "caption": caption})
        cid = c["id"]
    elif kind == "carousel":
        if not 2 <= len(media) <= 10:
            raise RuntimeError("carrossel precisa de 2 a 10 imagens")
        children = []
        for m in media:
            ch = graph("POST", f"{IG}/media", {"image_url": url_for(m), "is_carousel_item": "true"})
            wait_ready(ch["id"])
            children.append(ch["id"])
        c = graph("POST", f"{IG}/media", {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption})
        cid = c["id"]
    else:
        raise RuntimeError(f"tipo desconhecido: {kind}")
    wait_ready(cid)
    res = graph("POST", f"{IG}/media_publish", {"creation_id": cid})
    return res["id"]


def main():
    if not TOKEN:
        print("IG_TOKEN não configurado nos Secrets do repositório.")
        sys.exit(1)
    now = datetime.now(timezone.utc)
    files = sorted((ROOT / "queue").glob("*.json"))
    due = []
    for f in files:
        item = json.loads(f.read_text(encoding="utf-8"))
        if item.get("status") != "aprovado":
            continue
        at = datetime.fromisoformat(item["publish_at"])
        if at > now:
            continue
        if now - at > timedelta(hours=item.get("max_delay_hours", CFG["max_delay_hours"])):
            item["status"] = "expirado"
            item["error"] = "aprovado tarde demais; não publicado para não postar conteúdo velho"
            f.write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"expirado: {f.name}")
            continue
        due.append((at, f, item))

    if not due:
        print("nada para publicar agora")
        return
    due.sort(key=lambda x: x[0])
    _, f, item = due[0]  # 1 por execução
    try:
        mid = publish(item)
        item["status"] = "publicado"
        item["ig_media_id"] = mid
        item["published_at"] = now.isoformat()
        item.pop("error", None)
        print(f"publicado: {f.name} -> {mid}")
    except Exception as e:  # noqa: BLE001
        item["attempts"] = item.get("attempts", 0) + 1
        item["error"] = str(e)
        if item["attempts"] >= CFG["max_attempts"]:
            item["status"] = "erro"
        print(f"falhou ({item['attempts']}x): {f.name}: {e}")
    f.write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
