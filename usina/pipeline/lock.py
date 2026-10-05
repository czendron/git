"""Lock de ciclo (rodada 3, sugestão 1 da rodada 2): duas Routines no mesmo tick não podem submeter o mesmo vídeo.

`tick-start` grava usina/.lock (dono, pid, host, hora) e `tick-end` apaga. Lock com mais de 2 h é considerado
morto (sessão que caiu sem `tick-end`) e é ignorado. O dono desta máquina fica em out/.tick-owner, para o
`plan` e o `video-request` saberem se o lock é "meu" ou de outro ciclo.

O arquivo .lock pode ir para o git: com `git pull` antes do `tick-start` e um push logo depois, sessões em
containers diferentes também se enxergam (ver SKILL).
"""
from __future__ import annotations

import json
import os
import socket
import time
import uuid

from .store import OUT, ROOT

LOCK = ROOT / ".lock"
OWNER_FILE = OUT / ".tick-owner"
TTL_S = 2 * 3600


def read() -> dict | None:
    if not LOCK.exists():
        return None
    try:
        d = json.loads(LOCK.read_text(encoding="utf-8")) or {}
    except (OSError, json.JSONDecodeError):
        d = {"owner": "?", "at": LOCK.stat().st_mtime}  # lock corrompido ainda vale pela idade do arquivo
    return d


def stale(d: dict | None, now: float | None = None) -> bool:
    if not d:
        return True
    try:
        return (now or time.time()) - float(d.get("at") or 0) > float(d.get("ttl_s") or TTL_S)
    except (TypeError, ValueError):
        return True


def my_owner() -> str:
    try:
        return OWNER_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def held_by_other(now: float | None = None) -> dict | None:
    """O lock vivo de OUTRO ciclo (ou None). Lock vencido ou meu não conta."""
    d = read()
    if not d or stale(d, now):
        return None
    if d.get("owner") and d.get("owner") == my_owner():
        return None
    return d


def describe(d: dict, now: float | None = None) -> str:
    now = now or time.time()
    age = (now - float(d.get("at") or now)) / 60
    left = (float(d.get("ttl_s") or TTL_S) / 60) - age
    return f"{d.get('owner', '?')} (host {d.get('host', '?')}) há {age:.0f} min; vence em {max(left, 0):.0f} min"


def acquire(owner: str | None = None, now: float | None = None) -> tuple[bool, str, dict]:
    now = now or time.time()
    cur = read()
    # Reentrante (QA rodada 4): sem --owner, a mesma sessão (out/.tick-owner) reusa o seu dono. Antes, o 2º
    # tick-start da mesma sessão (Routine que dispara de novo na mesma conversa) inventava um dono novo e
    # recusava o próprio lock por 2 h, enquanto o `plan` dizia que o lock era meu.
    owner = owner or os.getenv("USINA_TICK_OWNER") or my_owner() \
        or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
    msg = ""
    if cur and not stale(cur, now) and cur.get("owner") != owner:
        return False, f"outro ciclo rodando: {describe(cur, now)}", cur
    if cur and stale(cur, now):
        msg = f"lock vencido ignorado ({cur.get('owner', '?')})"
    elif cur and cur.get("owner") == owner:
        msg = "o lock já era deste ciclo: renovado"
    d = {"owner": owner, "pid": os.getpid(), "host": socket.gethostname(), "at": now, "ttl_s": TTL_S,
         "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))}
    LOCK.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    OWNER_FILE.parent.mkdir(parents=True, exist_ok=True)
    OWNER_FILE.write_text(owner, encoding="utf-8")
    return True, msg, d


def release(owner: str | None = None, force: bool = False, now: float | None = None) -> tuple[bool, str]:
    cur = read()
    owner = owner or my_owner()
    if not cur:
        return True, "sem lock"
    if cur.get("owner") != owner and not force and not stale(cur, now):
        return False, f"o lock é de outro ciclo: {describe(cur, now)} (use --force se ele morreu)"
    LOCK.unlink()
    if OWNER_FILE.exists() and my_owner() == cur.get("owner"):
        OWNER_FILE.unlink()
    return True, "lock liberado"
