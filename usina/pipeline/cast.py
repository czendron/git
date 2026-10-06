"""Elenco recorrente de cada página (pages/<page>/cast/<cast_id>.yaml): gente que volta em vários vídeos.

Por que existe: figurante com rosto, gerado só pelo texto, sai "gente genérica de IA" e muda de cara a cada vídeo.
Quem aparece de rosto (contraparte humana ou figurante em destaque) e é recorrente ganha uma ficha C1 2x2 (OpenAI),
aprovada uma vez pelo Caio na Caixa e reusada em todo vídeo: o mesmo rosto em todo lugar.

Regra de uso ("às vezes"): passante de fundo fica só no prompt; figurante em destaque (rosto visível, em 2+ estágios
ou perto da câmera) ganha ficha: do elenco (cast_id) ou avulsa (só `look`, a ficha da contraparte da rodada 7).

YAML de cada membro:
  cast_id, name, pronoun (he|she), role (PT), look (EN), status (rascunho|aprovado),
  refs: {sheet: cast/sheets/<id>-vN.png (relativo à pasta da página), higgsfield_id, asset, url}
  review: {caio: pending|rejected|approved, notes, at}   (decisão da Caixa)
A pasta cast/sheets/ não vai para o git (como refs/): o arquivo fica no asset store do painel (`media-status`).
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import yaml

from .store import PAGES, StoreError, get_page

STATUSES = ("rascunho", "aprovado")
CAST_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
REQUIRED = ("cast_id", "name", "look", "role")


def cast_dir(slug: str) -> Path:
    return PAGES / slug / "cast"


def load(slug: str) -> dict[str, dict]:
    """Membros do elenco da página, por cast_id (vazio se a página não tem elenco)."""
    out: dict[str, dict] = {}
    d = cast_dir(slug)
    for f in sorted(d.glob("*.yaml")) if d.exists() else []:
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        cid = str(data.get("cast_id") or f.stem)
        if cid != f.stem:
            raise StoreError(f"{f}: cast_id '{cid}' diferente do nome do arquivo '{f.stem}'")
        data["cast_id"] = cid
        data.setdefault("refs", {})
        data.setdefault("status", "rascunho")
        out[cid] = data
    return out


def get(slug: str, cid: str) -> dict:
    m = load(slug).get(str(cid or ""))
    if not m:
        raise StoreError(f"{slug}: elenco sem '{cid}' (pages/{slug}/cast/{cid}.yaml). `python -m pipeline cast list {slug}`")
    return m


def save(slug: str, m: dict) -> Path:
    d = cast_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{m['cast_id']}.yaml"
    body = {k: m[k] for k in ("cast_id", "name", "pronoun", "role", "look", "status", "recurring", "notes", "refs",
                              "review") if k in m}
    head = f"# Elenco de {slug}: {m.get('name', m['cast_id'])}. Pessoa fictícia, sem semelhança com gente real.\n"
    f.write_text(head + yaml.safe_dump(body, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
    return f


def sheet_file(slug: str, m: dict) -> Path | None:
    p = (m.get("refs") or {}).get("sheet")
    return (PAGES / slug / p) if p else None


def has_sheet(slug: str, m: dict) -> bool:
    f = sheet_file(slug, m)
    r = m.get("refs") or {}
    return bool((f and f.exists()) or r.get("higgsfield_id") or r.get("asset"))


def approved(m: dict) -> bool:
    return m.get("status") == "aprovado" and bool((m.get("refs") or {}).get("sheet") or (m.get("refs") or {}).get("higgsfield_id"))


def state(slug: str, m: dict) -> str:
    """'aprovado' | 'aguardando' (ficha pronta, falta o Caio) | 'recusada' | 'sem ficha'."""
    if approved(m):
        return "aprovado"
    rv = m.get("review") or {}
    if rv.get("caio") == "rejected":
        return "recusada"
    return "aguardando" if has_sheet(slug, m) else "sem ficha"


def validate(m: dict) -> list[str]:
    errs = [f"falta '{k}'" for k in REQUIRED if not str(m.get(k) or "").strip()]
    if m.get("cast_id") and not CAST_ID.match(str(m["cast_id"])):
        errs.append("cast_id: minúsculas, números e hífen (ex.: seu-tadeu)")
    if m.get("status") not in STATUSES:
        errs.append(f"status deve ser {' ou '.join(STATUSES)}")
    if m.get("pronoun", "he") not in ("he", "she"):
        errs.append("pronoun deve ser he ou she")
    return errs


def new(slug: str, cid: str, name: str, look: str, role: str, pronoun: str = "he") -> dict:
    get_page(slug)
    if cid in load(slug):
        raise StoreError(f"{slug}: '{cid}' já existe no elenco")
    m = {"cast_id": cid, "name": name, "pronoun": pronoun, "role": role, "look": look, "status": "rascunho",
         "recurring": True, "refs": {"sheet": None, "higgsfield_id": None}}
    errs = validate(m)
    if errs:
        raise StoreError("; ".join(errs))
    save(slug, m)
    return m


def decide(slug: str, cid: str, approve: bool, notes: str = "") -> dict:
    """Decisão do Caio (Caixa ou `cast approve`). Aprovar sem ficha não vale; recusar manda refazer a ficha."""
    m = get(slug, cid)
    if approve and not has_sheet(slug, m):
        raise StoreError(f"{slug}/{cid}: sem ficha para aprovar (`python -m pipeline image {slug} cast-sheet {cid}`)")
    m["status"] = "aprovado" if approve else "rascunho"
    m["review"] = {"caio": "approved" if approve else "rejected", "notes": notes, "at": time.time()}
    save(slug, m)
    return m


def who(m: dict) -> str:
    """Nome do membro no prompt (B4.11: nome próprio, nunca 'the man')."""
    return str(m.get("name") or m["cast_id"]).strip().upper()
