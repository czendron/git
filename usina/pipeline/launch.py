"""Portão de estreia (ata D6): quando uma página pode gerar e quando pode fazer o 1º post.

- `rascunho` nunca gera.
- `ativo` só gera com a ficha aprovada: refs face + silhouette com `higgsfield_id` no page.yaml.
- P2 (Marlene) só no D+10 do Gersinho e P3 (Wanderley) só no D+20, contados do `launched_at` dele
  (sem `launched_at`, o 1º post registrado).
- O 1º post da P2/P3 só com 10 vídeos prontos em estoque.

O código nunca muda o `status` de uma página: só diz se o portão está aberto (`launch-check`, notes do plan).
Regras por página no page.yaml (`launch: {after: gersinho, min_days: 10, min_stock: 10}`) sobrepõem as padrão.
"""
from __future__ import annotations

import time

from .store import Page, get_page, list_items, StoreError

DEFAULTS = {
    "marlene": {"after": "gersinho", "min_days": 10, "min_stock": 10},
    "wanderley": {"after": "gersinho", "min_days": 20, "min_stock": 10},
}


def rules(page: Page) -> dict:
    r = dict(DEFAULTS.get(page.slug, {}))
    r.update(page.data.get("launch") or {})
    return r


def launched_at(page: Page) -> tuple[float | None, str]:
    """Estreia da página: `launched_at` do page.yaml ou o 1º post registrado."""
    v = page.data.get("launched_at")
    if v:
        try:
            return time.mktime(time.strptime(str(v), "%Y-%m-%d")), f"launched_at {v}"
        except ValueError:
            return None, f"launched_at inválido ({v!r}; use AAAA-MM-DD)"
    posted = [i.post.get("posted_at") for i in list_items(page.slug) if i.state == "postado" and i.post.get("posted_at")]
    if posted:
        ts = min(posted)
        return ts, f"1º post em {time.strftime('%Y-%m-%d', time.gmtime(ts))}"
    return None, "sem launched_at nem post registrado"


def has_posted(page: Page) -> bool:
    return any(i.state == "postado" for i in list_items(page.slug))


def check(page: Page, now: float | None = None) -> dict:
    now = now or time.time()
    r = rules(page)
    checks = []
    status = page.data.get("status")
    checks.append({"check": "status", "ok": status == "ativo",
                   "detail": f"status: {status}" + ("" if status == "ativo" else " (rascunho nunca gera; só o Caio ativa)")})
    by_role = {x.get("role"): x for x in page.data.get("refs") or []}
    miss = [role for role in ("face", "silhouette") if not (by_role.get(role) or {}).get("higgsfield_id")]
    checks.append({"check": "ficha", "ok": not miss,
                   "detail": "ficha aprovada (face + silhouette com higgsfield_id)" if not miss else
                   f"ficha não aprovada: falta higgsfield_id em {', '.join(miss)} (sheet → split-sheet → upload)"})
    if r.get("after"):
        try:
            base = get_page(r["after"])
            ts, how = launched_at(base)
        except StoreError as e:
            ts, how = None, str(e)
        need = int(r.get("min_days", 0))
        days = (now - ts) / 86400 if ts else None
        ok = days is not None and days >= need
        checks.append({"check": "dias", "ok": ok,
                       "detail": f"D+{need} de {r['after']}: " + (f"D+{days:.0f} ({how})" if days is not None else how)})
    stock_need = int(r.get("min_stock", 0))
    launched = has_posted(page)
    ready = sum(1 for i in list_items(page.slug) if i.state == "pronto")
    if stock_need and not launched:
        checks.append({"check": "estoque", "ok": ready >= stock_need,
                       "detail": f"{ready}/{stock_need} prontos antes do 1º post"})
    gen = all(c["ok"] for c in checks if c["check"] in ("status", "ficha", "dias"))
    post_first = gen and all(c["ok"] for c in checks if c["check"] == "estoque")
    failing = [c["detail"] for c in checks if not c["ok"]]
    # rodada 4: o motivo de "não gera" só lista o que bloqueia geração; o estoque bloqueia só o 1º post
    # (antes a mensagem dizia "não gera (…; 0/10 prontos)", como se faltasse estoque para gerar o estoque)
    gen_failing = [c["detail"] for c in checks if not c["ok"] and c["check"] != "estoque"]
    return {"page": page.slug, "status": status, "can_generate": gen, "can_post": launched or post_first,
            "launched": launched, "ready": ready, "min_stock": 0 if launched else stock_need, "checks": checks,
            "summary": "portão aberto" if gen and (launched or post_first) else "; ".join(failing),
            "gen_summary": "pode gerar" if gen else "; ".join(gen_failing)}
