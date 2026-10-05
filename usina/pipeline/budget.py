"""Livro-caixa (data/ledger.jsonl) e travas de gasto (budget.yaml). Ata D5."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from .store import ROOT

LEDGER = ROOT / "data" / "ledger.jsonl"
BUDGET = ROOT / "budget.yaml"
PAUSE_FILE = ROOT / "PAUSE"


def load_budget() -> dict:
    return yaml.safe_load(BUDGET.read_text(encoding="utf-8"))


def paused() -> str | None:
    """Kill switch (ata D8): existe o arquivo PAUSE na raiz da usina? Devolve o motivo."""
    if PAUSE_FILE.exists():
        return PAUSE_FILE.read_text(encoding="utf-8").strip() or "PAUSE ativo"
    return None


def record(page: str, item: str, provider: str, action: str, *, usd: float = 0.0, credits: float = 0.0,
           job_id: str = "", ok: bool = True, note: str = "", at: float | None = None) -> dict:
    budget = load_budget()
    if credits and not usd:
        usd = round(credits * float(budget.get("higgsfield_credit_usd", 0.05)), 4)
    row = {"at": at or time.time(), "page": page, "item": item, "provider": provider, "action": action,
           "usd": round(float(usd), 4), "credits": float(credits), "job_id": job_id, "ok": ok, "note": note}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def rows() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


DEFAULT_TZ = "Australia/Sydney"   # rodada 6: o Caio mora na Austrália; os tetos viram à meia-noite dele


def tz(b: dict | None = None):
    """Fuso dos tetos diário e mensal (`timezone` no budget.yaml). Fuso inválido cai no padrão, nunca em UTC calado."""
    name = str((b if b is not None else load_budget()).get("timezone") or DEFAULT_TZ)
    for n in (name, DEFAULT_TZ):
        try:
            return ZoneInfo(n)
        except (ZoneInfoNotFoundError, ValueError):
            continue
    # container sem base de fusos (nem /usr/share/zoneinfo nem o pacote tzdata): AEDT fixo, nunca UTC
    from datetime import timedelta, timezone
    return timezone(timedelta(hours=11), DEFAULT_TZ)


def local_dt(ts: float, zone: ZoneInfo | None = None) -> datetime:
    return datetime.fromtimestamp(float(ts), zone or tz())


def _day(ts: float, zone: ZoneInfo | None = None) -> str:
    return local_dt(ts, zone).strftime("%Y-%m-%d")


def _month(ts: float, zone: ZoneInfo | None = None) -> str:
    return local_dt(ts, zone).strftime("%Y-%m")


@dataclass
class Spend:
    today: dict
    month_usd: float
    month_cap: float
    day_cap: dict

    @property
    def month_pct(self) -> float:
        return 100.0 * self.month_usd / self.month_cap if self.month_cap else 0.0


def spend(now: float | None = None) -> Spend:
    now = now or time.time()
    b = load_budget()
    zone = tz(b)
    day_now, month_now = _day(now, zone), _month(now, zone)
    today: dict[str, float] = {}
    month = 0.0
    for r in rows():
        if _month(r["at"], zone) == month_now:
            month += r["usd"]
        if _day(r["at"], zone) == day_now:
            today[r["provider"]] = today.get(r["provider"], 0.0) + r["usd"]
    return Spend(today=today, month_usd=round(month, 2), month_cap=float(b["month_cap"]), day_cap=b["day_cap"])


# Rodada 5 (nota de implementação na ata, D5 intacta): o gag de uma trend cujo motion control já foi pago pode
# usar até 20% acima do teto diário do Higgsfield, se o teto do mês deixar. Senão a virada do dia empurra o gag
# para o dia seguinte e o MC pago fica parado ("não desperdiçar o que já foi pago").
GAG_DAY_OVERFLOW = 0.20


def can_spend(provider: str, usd: float, now: float | None = None, day_overflow: float = 0.0) -> tuple[bool, str]:
    """Checa teto diário do provedor e teto do mês antes de uma geração paga.

    `day_overflow` (fração) estica só o teto diário; o teto do mês nunca estica."""
    reason = paused()
    if reason:
        return False, f"pausado: {reason}"
    s = spend(now)
    cap = float(s.day_cap.get(provider, 0) or 0)
    if cap and s.today.get(provider, 0.0) + usd > cap * (1 + max(0.0, day_overflow)) + 1e-9:
        extra = f" nem com a folga de {day_overflow:.0%}" if day_overflow > 0 else ""
        return False, f"teto diário de {provider} (US$ {cap:.2f}) seria passado{extra}"
    if s.month_usd + usd > s.month_cap:
        return False, f"teto do mês (US$ {s.month_cap:.0f}) seria passado"
    return True, "ok"


def degraded_mode(now: float | None = None) -> bool:
    """Acima de 80% do mês: só modelos baratos (sem Seedance 1080p / Genjutsu)."""
    b = load_budget()
    return spend(now).month_pct >= max(b.get("alerts_pct", [80]))


def yield_last(n: int = 10) -> float | None:
    """Aproveitamento das últimas n gerações de vídeo (aprovadas / avaliadas)."""
    vids = [r for r in rows() if r["action"] == "video_review"]
    vids = vids[-n:]
    if len(vids) < n:
        return None
    return sum(1 for r in vids if r["ok"]) / len(vids)


def item_spend(page: str, item: str) -> dict:
    """Créditos e dólares já gastos numa ideia (ata D5: 160 créditos por ideia), lidos do livro-caixa."""
    cr = usd = 0.0
    for r in rows():
        if r.get("page") == page and r.get("item") == item:
            cr += float(r.get("credits") or 0)
            usd += float(r.get("usd") or 0)
    return {"credits": round(cr, 2), "usd": round(usd, 4)}


# ---------- saúde: erros seguidos e saldo do Higgsfield (ata D5, "paradas automáticas") ----------

HEALTH = ROOT / "data" / "health.json"
BALANCE_MAX_AGE_S = 24 * 3600   # saldo lido há mais de 24 h não vale: a sessão relê com mcp__Higgsfield__balance


def health() -> dict:
    h = {}
    if HEALTH.exists():
        try:
            h = json.loads(HEALTH.read_text(encoding="utf-8")) or {}
        except (OSError, json.JSONDecodeError):
            h = {}
    h.setdefault("consecutive_errors", 0)
    h.setdefault("errors", [])
    h.setdefault("balance", None)
    return h


def save_health(h: dict) -> None:
    HEALTH.parent.mkdir(parents=True, exist_ok=True)
    tmp = HEALTH.with_suffix(".tmp")
    tmp.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(HEALTH)


def record_error(msg: str, ref: str = "", now: float | None = None) -> dict:
    """Conta um erro. No limite (max_consecutive_errors, padrão 3), o próprio código cria o PAUSE (ata D5)."""
    h = health()
    h["consecutive_errors"] = int(h.get("consecutive_errors") or 0) + 1
    h["errors"] = (h.get("errors") or [])[-49:] + [{"at": now or time.time(), "ref": ref, "msg": msg[:300]}]
    limit = int(load_budget().get("max_consecutive_errors", 3) or 3)
    h["paused_by_errors"] = False
    if h["consecutive_errors"] >= limit and not paused():
        PAUSE_FILE.write_text(f"{h['consecutive_errors']} erros seguidos (último: {msg[:160]})", encoding="utf-8")
        h["paused_by_errors"] = True
    save_health(h)
    return h


def reset_errors() -> None:
    """Um comando de produção que deu certo zera a sequência ("3 erros SEGUIDOS")."""
    h = health()
    if h.get("consecutive_errors"):
        h["consecutive_errors"] = 0
        save_health(h)


def record_balance(credits: float, now: float | None = None) -> dict:
    h = health()
    h["balance"] = {"credits": float(credits), "at": now or time.time()}
    save_health(h)
    return h


def balance_status(now: float | None = None) -> tuple[str, float | None]:
    """('unknown'|'stale'|'low'|'ok', saldo estimado). Estimado = último saldo lido menos os créditos lançados depois."""
    now = now or time.time()
    bal = health().get("balance")
    if not bal or bal.get("credits") is None:
        return "unknown", None
    at = float(bal.get("at") or 0)
    used = sum(float(r.get("credits") or 0) for r in rows() if r.get("provider") == "higgsfield" and r["at"] > at)
    est = round(float(bal["credits"]) - used, 2)
    if now - at > BALANCE_MAX_AGE_S:
        return "stale", est
    if est < float(load_budget().get("min_higgsfield_credits", 0) or 0):
        return "low", est
    return "ok", est


def gag_overflow(page: str, item: str) -> float:
    """Folga do teto diário para o gag: só quando o motion control do item já foi pago (créditos no livro-caixa)."""
    return GAG_DAY_OVERFLOW if item_spend(page, item)["credits"] > 0 else 0.0


def over_day_cap(provider: str, usd: float, now: float | None = None) -> bool:
    """O gasto passaria do teto diário puro (sem folga)? Serve para avisar que a folga do gag foi usada."""
    s = spend(now)
    cap = float(s.day_cap.get(provider, 0) or 0)
    return bool(cap) and s.today.get(provider, 0.0) + usd > cap + 1e-9


def can_spend_higgsfield(credits: float, now: float | None = None, day_overflow: float = 0.0) -> tuple[bool, str]:
    """Tetos em dólar + saldo mínimo de créditos (ata D5: saldo < 300 créditos, para)."""
    usd = credits * float(load_budget().get("higgsfield_credit_usd", 0.05))
    ok, why = can_spend("higgsfield", usd, now, day_overflow)
    if not ok:
        return ok, why
    st, est = balance_status(now)
    floor = float(load_budget().get("min_higgsfield_credits", 0) or 0)
    if st in ("unknown", "stale"):
        return False, ("saldo do Higgsfield desconhecido ou com mais de 24 h: rode mcp__Higgsfield__balance e "
                       "`python -m pipeline balance <créditos>`")
    if est - credits < floor:
        return False, f"saldo do Higgsfield (~{est:.0f} créditos) ficaria abaixo do mínimo de {floor:.0f} (ata D5)"
    return True, "ok"
