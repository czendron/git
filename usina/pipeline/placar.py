"""Placar (métricas lançadas pelo Caio no painel) e o gatilho de cadência da ata D5.

D5: o Gersinho começa com 1 post por dia e sobe para 2 quando houver >= 4 vídeos aprovados no estoque
E o D7 mostrar tração (mediana > 5k views ou um Reel > 50k). O código só SUGERE: quem muda
`cadence.posts_per_day` no page.yaml é o Caio.
"""
from __future__ import annotations

import json
import statistics
import time

from .store import ROOT, list_items, load_pages

PLACAR = ROOT / "data" / "placar.json"
MEDIAN_VIEWS = 5000
TOP_VIEWS = 50000
MIN_STOCK = 4
DAYS = 7


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f >= 0 else None


def rows_from_export(raw) -> list[dict]:
    """Aceita a saída do ArtifactData list (lista, {documents|docs|items|rows|results|data: [...]}, {id: doc})."""
    if isinstance(raw, dict):
        for k in ("documents", "docs", "items", "rows", "results", "data"):
            if isinstance(raw.get(k), list):
                raw = raw[k]
                break
        else:
            raw = [dict(v, id=k) if isinstance(v, dict) else v for k, v in raw.items()]
    out = []
    for r in raw if isinstance(raw, list) else []:
        if not isinstance(r, dict):
            continue
        d = r.get("data") if isinstance(r.get("data"), dict) else r
        ref = d.get("ref")
        if not isinstance(ref, str) or "/" not in ref:
            continue
        out.append(d)
    return out


def load() -> dict:
    if not PLACAR.exists():
        return {}
    try:
        return json.loads(PLACAR.read_text(encoding="utf-8")) or {}
    except (OSError, json.JSONDecodeError):
        return {}


def import_rows(raw) -> dict:
    """Grava data/placar.json ({ref: {...}}). Linha nova do mesmo vídeo substitui a anterior (o Caio corrige)."""
    cur = load()
    n = 0
    for d in rows_from_export(raw):
        row = {"page": d.get("page") or d["ref"].split("/", 1)[0], "title": d.get("title", ""),
               "views": _num(d.get("views")), "views7": _num(d.get("views7")), "shares": _num(d.get("shares")),
               "follows": _num(d.get("follows")), "ret3": _num(d.get("ret3")),
               "at": _num(d.get("updatedAt") or d.get("createdAt"))}
        old = cur.get(d["ref"])
        if old and (old.get("at") or 0) > (row["at"] or 0):
            continue  # export velho não sobrescreve número mais novo
        cur[d["ref"]] = row
        n += 1
    PLACAR.parent.mkdir(parents=True, exist_ok=True)
    PLACAR.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"imported": n, "total": len(cur)}


def cadence_check(now: float | None = None) -> list[dict]:
    """Avalia o gatilho da D5 por página ativa que ainda está em 1 post/dia. Nunca muda nada."""
    now = now or time.time()
    data = load()
    out = []
    for page in load_pages(include_drafts=False):
        ppd = int(page.data.get("cadence", {}).get("posts_per_day", 1) or 1)
        items = list_items(page.slug)
        stock = [i for i in items if i.state in ("revisao", "pronto")
                 and i.gates.get("video", {}).get("caio") == "approved"]
        posted = [i.post.get("posted_at") for i in items if i.state == "postado" and i.post.get("posted_at")]
        start = None
        launched = page.data.get("launched_at")
        if launched:
            try:
                start = time.mktime(time.strptime(str(launched), "%Y-%m-%d"))
            except ValueError:
                start = None
        if start is None and posted:
            start = min(posted)
        days = (now - start) / 86400 if start else 0.0
        views = []
        for ref, r in data.items():
            if (r.get("page") or ref.split("/", 1)[0]) != page.slug:
                continue
            v = r.get("views7") if r.get("views7") is not None else r.get("views")
            if v is not None:
                views.append(v)
        median = statistics.median(views) if views else None
        top = max(views) if views else None
        traction = bool(views) and (median > MEDIAN_VIEWS or top > TOP_VIEWS)
        crit = {"approved_stock": len(stock), "stock_ok": len(stock) >= MIN_STOCK,
                "days_since_start": round(days, 1), "d7_ok": days >= DAYS,
                "posts_with_numbers": len(views), "median_views": median, "top_views": top,
                "traction_ok": traction}
        fire = ppd < 2 and crit["stock_ok"] and crit["d7_ok"] and traction
        missing = [txt for ok, txt in ((crit["stock_ok"], f"estoque aprovado {len(stock)}/{MIN_STOCK}"),
                                       (crit["d7_ok"], f"dia {days:.0f} de {DAYS} desde o 1º post"),
                                       (traction, f"tração (mediana > {MEDIAN_VIEWS} ou um Reel > {TOP_VIEWS})"))
                   if not ok]
        out.append({
            "page": page.slug, "posts_per_day": ppd, "trigger": fire, "criteria": crit,
            "missing": [] if fire else missing,
            "suggestion": (f"Gatilho da ata D5 atingido: sugerir ao Caio subir {page.slug} para 2 posts/dia "
                           f"(cadence.posts_per_day: 2 em pages/{page.slug}/page.yaml). O código não muda sozinho."
                           if fire else ""),
        })
    return out
