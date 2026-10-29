"""Robô horário (GitHub Actions): manda push para os celulares cadastrados e, se configurado, Telegram.
Lê data/atual.json. Horário sempre de São Paulo. Itens com enviar_as nos últimos 90 min que ainda não foram avisados.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SP = ZoneInfo("America/Sao_Paulo")
SITE = os.environ.get("SITE", "").rstrip("/") + "/"
estado_dir = Path(".avisos-estado")
estado_dir.mkdir(exist_ok=True)
estado = estado_dir / "enviados.json"
try:
    ja = json.loads(estado.read_text())
except Exception:
    ja = {}

agora = datetime.now(SP)
if os.environ.get("HORA"):
    agora = agora.replace(hour=int(os.environ["HORA"]), minute=0)
hoje = agora.date().isoformat()
nowm = agora.hour * 60 + agora.minute


def minutos(hm):
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


dados = json.loads(Path("data/atual.json").read_text(encoding="utf-8"))
fila = [i for i in dados["itens"] if i["data"] == hoje and nowm - 90 <= minutos(i["enviar_as"]) <= nowm + 5 and i["id"] not in ja]
teste = os.environ.get("TESTE") in ("1", "true")
print(f"{agora:%Y-%m-%d %H:%M} SP · semana {dados.get('semana')} · {len(fila)} item(ns) para avisar" + (" · TESTE" if teste else ""))

subs = json.loads(os.environ.get("PUSH_SUBS") or "[]")
priv, email = os.environ.get("VAPID_PRIVATE"), os.environ.get("VAPID_EMAIL")


def push(payload):
    if not (subs and priv):
        return
    from pywebpush import webpush, WebPushException
    for s in subs:
        try:
            webpush(s, json.dumps(payload, ensure_ascii=False), vapid_private_key=priv, vapid_claims={"sub": email or "mailto:avisos@example.com"}, ttl=3600)
            print("push ok ->", s.get("endpoint", "")[:40])
        except WebPushException as e:
            print("push falhou:", e)


tok = os.environ.get("TG_TOKEN")
chats = json.loads(os.environ.get("TG_CHATS") or "{}")


def tg(metodo, campos):
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{metodo}", data=urllib.parse.urlencode(campos).encode())
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def telegram(item):
    if not (tok and chats):
        return
    chat = chats.get(item["clube"]) or chats.get("todos")
    if not chat:
        return
    texto = f"🕗 Enviar agora ({item['enviar_as']} SP) · {item['clube_nome']}\n\n{item['texto_whatsapp']}\n\n🔗 {SITE}#{item['id']}"
    imgs = item.get("imagens", [])
    img = next((SITE + x for x in imgs if x.endswith("-feed.png")), SITE + imgs[0] if imgs else None)
    try:
        if img and len(texto) <= 1024:
            tg("sendPhoto", {"chat_id": chat, "photo": img, "caption": texto})
        else:
            tg("sendMessage", {"chat_id": chat, "text": texto, "disable_web_page_preview": "false"})
        print("telegram ok ->", chat)
    except Exception as e:
        print("telegram falhou:", e)


if teste:
    push({"title": "✅ Avisos ligados", "body": "Este celular vai receber a grade às 9h e os lembretes 1 hora antes (horário de São Paulo).", "url": SITE, "tag": "teste"})
    if tok and chats:
        for k, chat in chats.items():
            try:
                tg("sendMessage", {"chat_id": chat, "text": f"✅ Avisos pelo GitHub ligados ({k})."})
            except Exception as e:
                print("telegram teste falhou:", e)

for it in fila:
    titulo = f"{it['enviar_as']} · {'Grade do dia' if it['tipo'] == 'grade' else 'Lembrete'} · {it['clube_nome']}"
    corpo = it["resumo"] if it["tipo"] == "grade" else it["titulo"]
    imgs = it.get("imagens", [])
    push({"title": titulo, "body": corpo, "url": f"{SITE}#{it['id']}", "image": (SITE + imgs[0]) if imgs else "", "tag": it["id"]})
    telegram(it)
    ja[it["id"]] = agora.isoformat(timespec="minutes")
    print("avisado:", it["id"])

estado.write_text(json.dumps(ja))
