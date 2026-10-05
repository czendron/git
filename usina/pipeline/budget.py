"""Livro-caixa (data/ledger.jsonl) e travas de gasto (budget.yaml). Ata D5."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

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


def _day(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def _month(ts: float) -> str:
    return time.strftime("%Y-%m", time.gmtime(ts))


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
    today: dict[str, float] = {}
    month = 0.0
    for r in rows():
        if _month(r["at"]) == _month(now):
            month += r["usd"]
        if _day(r["at"]) == _day(now):
            today[r["provider"]] = today.get(r["provider"], 0.0) + r["usd"]
    return Spend(today=today, month_usd=round(month, 2), month_cap=float(b["month_cap"]), day_cap=b["day_cap"])


def can_spend(provider: str, usd: float, now: float | None = None) -> tuple[bool, str]:
    """Checa teto diário do provedor e teto do mês antes de uma geração paga."""
    reason = paused()
    if reason:
        return False, f"pausado: {reason}"
    s = spend(now)
    cap = float(s.day_cap.get(provider, 0) or 0)
    if cap and s.today.get(provider, 0.0) + usd > cap:
        return False, f"teto diário de {provider} (US$ {cap:.2f}) seria passado"
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
