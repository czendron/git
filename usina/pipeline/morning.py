"""`status --morning` (rodada 6): o resumo do dia para o Caio, em PT-BR, curto. É a base do relatório final do SKILL.

Quatro blocos: o que espera o Caio (com o nome da etapa como o painel mostra), o que saiu e quanto custou nas
últimas 24 h, o que bloqueia a usina e o portão de estreia de cada página.
"""
from __future__ import annotations

import os
import time

from . import budget, launch, lock
from .store import list_items, load_pages

# Onde cada espera aparece no painel (index.html: STAGE_LABEL da Caixa, botões da Fila, avisos da Saúde)
PANEL_STAGE = {
    "storyboard": "Caixa › Storyboard",
    "frames": "Caixa › Primeiro e último frame",
    "video": "Caixa › Vídeo final",
    "fonte": "Saúde › falta o vídeo-fonte da trend (.mp4)",
    "postar": "Fila › Baixar MP4 e Postei",
}
DONE_STATES = {"storyboard": "roteiro pronto", "frames": "storyboard aprovado", "video": "frames aprovados",
               "revisao": "vídeo gerado", "pronto": "pacote pronto", "postado": "postado", "descartado": "descartado"}


def waiting_caio(now: float | None = None) -> list[dict]:
    """O que espera o Caio, mesmo com PAUSE ou com outro ciclo rodando (o `plan` não lista nada nesses casos)."""
    from .tick import ACTIVE, plan_item
    now = now or time.time()
    b = budget.load_budget()
    out = []
    for page in load_pages(include_drafts=False):
        for it in list_items(page.slug):
            if it.state not in ACTIVE:
                continue
            try:
                acts = plan_item(it, page, b, now)
            except Exception:  # noqa: BLE001 - item torto não derruba o resumo
                continue
            out += [{**a, "title": (it.idea or {}).get("title") or it.id} for a in acts if a["do"] == "await_caio"]
    return out


def blockers(now: float | None = None) -> list[str]:
    now = now or time.time()
    b = budget.load_budget()
    sw = b.get("switches", {}) or {}
    out = []
    p = budget.paused()
    if p:
        out.append(f"PAUSADO: {p}. Retome na aba Saúde do painel.")
    if sw.get("image_provider", "openai") == "openai" and not os.getenv("OPENAI_API_KEY"):
        out.append("OPENAI_API_KEY ausente no ambiente: nenhuma imagem sai"
                   + (" (fallback Higgsfield liberado)." if sw.get("image_fallback_allowed") else
                      " (libere api.openai.com e a chave nas configurações do ambiente)."))
    if not budget.higgsfield_spend_enabled(b):
        out.append("Gasto no Higgsfield travado (budget.yaml, switches.higgsfield_spend_enabled: false; você pediu em "
                   "05/10): nenhum vídeo, gag ou imagem pelo Higgsfield até você liberar.")
    if not sw.get("video_enabled", False):
        out.append("Vídeo desligado (budget.yaml, switches.video_enabled: false): nada vai ao Higgsfield.")
    for page in load_pages(include_drafts=False):
        miss = [r.name for r in page.ref_paths() if not r.exists()]
        if miss:
            out.append(f"{page.slug}: refs locais faltando ({', '.join(miss)}): `fetch-refs {page.slug}`.")
    st, est = budget.balance_status(now)
    if st == "low":
        out.append(f"Saldo do Higgsfield ~{est:.0f} créditos, abaixo do mínimo de {b.get('min_higgsfield_credits')}: recarregar.")
    h = budget.health()
    if h.get("consecutive_errors"):
        out.append(f"{h['consecutive_errors']} erro(s) seguido(s); último: {(h.get('errors') or [{}])[-1].get('msg', '?')}")
    other = lock.held_by_other(now)
    if other:
        out.append(f"Outro ciclo rodando: {lock.describe(other, now)}.")
    return out


def last_24h(now: float | None = None) -> tuple[list[str], dict]:
    now = now or time.time()
    since = now - 86400
    moves = []
    for it in list_items():
        for h in it.history or []:
            if float(h.get("at") or 0) >= since and h.get("to") in DONE_STATES:
                moves.append((float(h["at"]), f"{it.page}/{(it.idea or {}).get('title') or it.id}: {DONE_STATES[h['to']]}"))
    rows = [r for r in budget.rows() if float(r.get("at") or 0) >= since]
    spent: dict[str, float] = {}
    for r in rows:
        spent[r["provider"]] = spent.get(r["provider"], 0.0) + float(r.get("usd") or 0)
    return [m for _, m in sorted(moves)], {"by_provider": spent, "rows": len(rows),
                                            "credits": sum(float(r.get("credits") or 0) for r in rows)}


def render(now: float | None = None) -> str:
    now = now or time.time()
    b = budget.load_budget()
    zone = budget.tz(b)
    loc = budget.local_dt(now, zone)
    s = budget.spend(now)
    L = [f"Usina: bom dia, Caio ({loc.strftime('%d/%m %H:%M')} {getattr(zone, 'key', None) or zone.tzname(None)})", ""]

    wait = waiting_caio(now)
    L.append(f"Esperando você ({len(wait)}):")
    for w in wait:
        L.append(f"- {PANEL_STAGE.get(w['stage'], w['stage'])}: {w['item']} ({w['title']})")
    if not wait:
        L.append("- nada")

    moves, sp = last_24h(now)
    tot = sum(sp["by_provider"].values())
    L += ["", "Últimas 24 h:"]
    L += [f"- {m}" for m in moves[-8:]] + ([f"- (+{len(moves) - 8} movimentos)"] if len(moves) > 8 else [])
    if not moves:
        L.append("- nada produzido")
    by = ", ".join(f"{k} US$ {v:.2f}" for k, v in sorted(sp["by_provider"].items())) or "nada"
    L.append(f"- gasto: US$ {tot:.2f} ({by}" + (f"; {sp['credits']:g} créditos" if sp["credits"] else "") + ")")
    caps = ", ".join(f"{k} US$ {s.today.get(k, 0.0):.2f}/{float(v):.0f}" for k, v in (s.day_cap or {}).items())
    L.append(f"- hoje ({loc.strftime('%d/%m')}, vira à meia-noite local): {caps}; mês US$ {s.month_usd:.2f}/"
             f"{s.month_cap:.0f} ({s.month_pct:.0f}%)")

    bl = blockers(now)
    L += ["", "Bloqueios:"] + ([f"- {x}" for x in bl] or ["- nenhum"])

    L += ["", "Portão de estreia:"]
    for page in load_pages():
        g = launch.check(page, now)
        if page.data.get("status") != "ativo":
            rest = [c["detail"] for c in g["checks"] if not c["ok"] and c["check"] not in ("status", "estoque")]
            st = "rascunho (só você ativa)" + (f"; ao ativar ainda falta: {'; '.join(rest)}" if rest else "")
        elif g["can_generate"] and g["can_post"]:
            st = "aberto"
        elif g["can_generate"]:
            st = f"gera; 1º post só com {g['ready']}/{g['min_stock']} prontos"
        else:
            st = f"fechado: {g['gen_summary']}"
        L.append(f"- {page.slug}: {st}")
    return "\n".join(L)
