"""Rodada 6 de QA (docs/qa/rodada-6.md): ensaio dos passos de git do SKILL com um remoto --bare local e dois
clones (dois containers), tetos no fuso do Caio, até 3 ideias novas por ciclo e `status --morning`.
Sem rede: tudo em repositórios locais.
"""
import json
import os
import sys
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from test_pipeline import HERE, run, usina  # noqa: F401  (fixture reaproveitada)
from test_qa_rodada1 import EXAMPLE, plan

SKILL = HERE.parent / ".claude" / "skills" / "usina" / "SKILL.md"
ITEM = "data/queue/gersinho/20261005-131106-busao-topete-preso.json"


# ---------- 1. git: remoto --bare e dois clones ----------

def g(cwd, *args, ok=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if ok:
        assert r.returncode == 0, r.stdout + r.stderr
    return r


@pytest.fixture()
def repos(tmp_path):
    """origin.git (bare) + clones A e B, com a usina numa subpasta como no repo de verdade."""
    seed = tmp_path / "seed"
    u = seed / "usina"
    for d in ("pipeline", "pages", "prompts", "playbook"):
        shutil.copytree(HERE / d, u / d, ignore=shutil.ignore_patterns("*.png", "__pycache__"))
    for f in ("budget.yaml", ".gitignore"):
        shutil.copy(HERE / f, u / f)
    (u / "data" / "queue" / "gersinho").mkdir(parents=True)
    shutil.copy(HERE / ITEM, u / ITEM)
    for f in ("ledger.jsonl", "falhas.jsonl"):
        (u / "data" / f).write_text(json.dumps({"at": 0, "seed": f}) + "\n")
    (u / "data" / "health.json").write_text(json.dumps({"balance": {"credits": 5000, "at": time.time()}}))
    shutil.copy(HERE.parent / ".gitattributes", seed / ".gitattributes")
    g(tmp_path, "init", "-q", "-b", "usina-de-virais", str(seed))
    for k, v in (("user.email", "seed@x"), ("user.name", "seed")):
        g(seed, "config", k, v)
    g(seed, "add", "-A")
    g(seed, "commit", "-qm", "seed")
    g(tmp_path, "clone", "-q", "--bare", str(seed), str(tmp_path / "origin.git"))
    out = {"origin": tmp_path / "origin.git"}
    for c in ("A", "B", "C"):
        g(tmp_path, "clone", "-q", "-b", "usina-de-virais", str(tmp_path / "origin.git"), str(tmp_path / c))
        g(tmp_path / c, "config", "user.email", f"{c}@x")
        g(tmp_path / c, "config", "user.name", c)
        out[c] = tmp_path / c / "usina"
    return out


def P(root, *args, ok=True):
    os.environ.pop("USINA_TICK_OWNER", None)
    return run(root, *args, ok=ok)


def origin_file(repos, path):
    r = g(repos["origin"], "show", f"usina-de-virais:usina/{path}", ok=False)
    return r.stdout if r.returncode == 0 else None


def edit_item(root, **kw):
    f = root / ITEM
    d = json.loads(f.read_text())
    d.update(kw)
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2))


def append(root, name, row):
    with (root / "data" / name).open("a") as f:
        f.write(json.dumps(row) + "\n")


def test_skill_git_paths_fixed():
    s = SKILL.read_text()
    assert "git add usina/.lock" not in s                 # rodava de dentro de usina/: pathspec inexistente
    assert "P tick-start --git" in s and "P tick-end --git" in s and "git-resolve" in s
    assert "P status --morning" in s


def test_lock_push_pull_and_concurrent_tick_refused(repos):
    a, b = repos["A"], repos["B"]
    out = json.loads(P(a, "tick-start", "--git").stdout)
    assert out["pushed"] and json.loads(origin_file(repos, ".lock"))["owner"] == out["owner"]
    head = g(repos["origin"], "rev-parse", "usina-de-virais").stdout
    r = P(b, "tick-start", "--git", ok=False)
    assert r.returncode == 1 and "outro ciclo rodando" in r.stderr
    assert g(repos["origin"], "rev-parse", "usina-de-virais").stdout == head   # B não empurrou nada
    assert json.loads((b / ".lock").read_text())["owner"] == out["owner"]    # B puxou e enxerga o lock de A
    assert "OUTRO CICLO" in " ".join(json.loads(P(b, "plan").stdout)["notes"])
    # A termina: lock some do remoto; B consegue
    append(a, "ledger.jsonl", {"at": 1, "who": "A"})
    end = json.loads(P(a, "tick-end", "--git").stdout)
    assert end["pushed"] and origin_file(repos, ".lock") is None
    assert '"who": "A"' in origin_file(repos, "data/ledger.jsonl")
    assert json.loads(P(b, "tick-start", "--git").stdout)["pushed"]


def test_stale_lock_is_taken_over(repos):
    a, b = repos["A"], repos["B"]
    P(a, "tick-start", "--git")
    d = json.loads((a / ".lock").read_text())
    d["at"] = time.time() - 3 * 3600                     # sessão A caiu há 3 h sem tick-end
    (a / ".lock").write_text(json.dumps(d))
    g(a, "commit", "-qam", "lock velho")
    g(a, "push", "-q")
    r = P(b, "tick-start", "--git")
    assert "lock vencido ignorado" in r.stdout
    assert json.loads(origin_file(repos, ".lock"))["owner"] != d["owner"]


def test_lock_push_rejected_retries_once(repos, tmp_path):
    """Corrida: alguém (outro agente) empurra entre o pull e o push do lock. O push é recusado, o pipeline desfaz o
    commit do lock, puxa e tenta de novo, sem perder o commit alheio."""
    a, c = repos["A"], repos["C"]
    (c / "playbook" / "novo.md").write_text("tutorial\n")
    g(c, "add", "-A")
    g(c, "commit", "-qm", "playbook do outro agente")
    hook = a.parent / ".git" / "hooks" / "pre-push"
    flag = tmp_path / "pushed-once"
    hook.write_text(f"#!/bin/sh\n[ -e {flag} ] && exit 0\ntouch {flag}\nunset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE\ncd {c} && git push -q origin HEAD >/dev/null 2>&1\n"
                    f"exit 1\n")
    hook.chmod(0o755)
    r = P(a, "tick-start", "--git")
    assert "push do lock recusado" in r.stdout and json.loads(r.stdout[r.stdout.index("{"):])["pushed"]
    assert origin_file(repos, "playbook/novo.md") == "tutorial\n"
    assert origin_file(repos, ".lock") is not None
    log = g(a, "log", "--format=%s", "-3").stdout.splitlines()
    assert log[0] == "usina: lock" and log.count("usina: lock") == 1           # um lock só, sem o commit desfeito


def test_tick_end_merges_logs_and_resolves_queue_conflict(repos):
    """A (lento) e B (assumiu o lock vencido de A) mexem no mesmo item e acrescentam linhas nos dois jsonl."""
    a, b = repos["A"], repos["B"]
    P(a, "tick-start", "--git")
    d = json.loads((a / ".lock").read_text())
    d["at"] = time.time() - 3 * 3600
    (a / ".lock").write_text(json.dumps(d))
    g(a, "commit", "-qam", "lock velho")
    g(a, "push", "-q")
    P(b, "tick-start", "--git")                                        # B assume
    base = json.loads((a / ITEM).read_text())
    edit_item(a, state="storyboard", updated_at=base["updated_at"] + 10, notes="A")
    append(a, "ledger.jsonl", {"at": 2, "who": "A"})
    append(a, "falhas.jsonl", {"at": 2, "who": "A"})
    # A termina com B ainda rodando: o .lock (A apagou, B renovou) e nada mais em conflito
    r = P(a, "tick-end", "--git")
    assert "assumiu" in r.stdout
    assert json.loads(origin_file(repos, ".lock"))["owner"] != d["owner"]   # o lock vivo de B ficou
    # B mexe no mesmo item (e pagou um vídeo nele) e termina depois
    edit_item(b, state="video", updated_at=base["updated_at"] + 5, notes="B",
              video={"job_id": "JOB-B", "provider": "higgsfield"})
    append(b, "ledger.jsonl", {"at": 3, "who": "B"})
    append(b, "falhas.jsonl", {"at": 3, "who": "B"})
    r = P(b, "tick-end", "--git")
    assert json.loads(r.stdout[r.stdout.index("{"):])["pushed"] and "conflito" in r.stdout
    led = origin_file(repos, "data/ledger.jsonl")
    fal = origin_file(repos, "data/falhas.jsonl")
    assert all(f'"who": "{w}"' in led and f'"who": "{w}"' in fal for w in "AB")   # merge=union: nada se perde
    assert "<<<<<<<" not in led + fal
    item = json.loads(origin_file(repos, ITEM))
    assert item["notes"] == "B" and item["video"]["job_id"] == "JOB-B"          # quem tem job pago vence
    kept = g(repos["origin"], "ls-tree", "--name-only", "usina-de-virais", "usina/data/conflicts/").stdout.split()
    assert len(kept) == 1 and json.loads(origin_file(repos, kept[0][len("usina/"):]))["notes"] == "A"
    assert origin_file(repos, ".lock") is None
    assert not g(b.parent, "status", "--porcelain").stdout.strip()


def test_unresolvable_conflict_goes_to_side_branch(repos):
    a, b = repos["A"], repos["B"]
    for root, txt in ((a, "A"), (b, "B")):
        f = root / "prompts" / "script.md"
        f.write_text(f.read_text() + f"\nlinha {txt}\n")
    P(a, "tick-end", "--git")
    head = g(repos["origin"], "rev-parse", "usina-de-virais").stdout
    r = P(b, "tick-end", "--git", ok=False)
    assert r.returncode == 1 and "conflito sem regra" in r.stderr and "usina-conflito-" in r.stderr
    assert g(repos["origin"], "rev-parse", "usina-de-virais").stdout == head      # o ramo da usina ficou intacto
    side = [x for x in g(repos["origin"], "branch", "--format=%(refname:short)").stdout.split() if "conflito" in x]
    assert side and "linha B" in g(repos["origin"], "show", f"{side[0]}:usina/prompts/script.md").stdout
    assert not (b.parent / ".git" / "MERGE_HEAD").exists()                      # merge abortado, árvore limpa


def test_git_resolve_by_hand(repos):
    """`git pull --no-rebase` à mão com conflito no item: `git-resolve` aplica as mesmas regras."""
    a, b = repos["A"], repos["B"]
    edit_item(a, notes="A", updated_at=1)
    g(a.parent, "commit", "-qam", "A")
    g(a.parent, "push", "-q")
    edit_item(b, notes="B", updated_at=2)
    g(b.parent, "commit", "-qam", "B")
    assert g(b.parent, "pull", "-q", "--no-rebase", "--no-edit", ok=False).returncode != 0
    r = P(b, "git-resolve")
    assert "merge concluído" in r.stdout and json.loads((b / ITEM).read_text())["notes"] == "B"
    assert list((b / "data" / "conflicts").glob("*.json"))


def test_conflict_rules_pure(monkeypatch):
    from pipeline import gitsync, lock
    paid = {"state": "video", "updated_at": 1, "video": {"job_id": "J1", "history": [{"job_id": "J0"}]}}
    newer = {"state": "frames", "updated_at": 9}
    assert gitsync.pick_item(newer, paid)[0] is paid                   # job pago pesa mais que recência
    assert gitsync.pick_item({"state": "frames", "updated_at": 1}, newer)[0] is newer
    assert gitsync.pick_item(None, newer)[0] is newer
    monkeypatch.setattr(lock, "my_owner", lambda: "me")
    now = time.time()
    mine, other, dead = ({"owner": o, "at": t} for o, t in (("me", now), ("x", now), ("y", now - 9000)))
    assert gitsync.pick_lock(mine, other, now)["owner"] == "x"
    assert gitsync.pick_lock(mine, dead, now)["owner"] == "me"
    assert gitsync.pick_lock(None, dead, now) is None
    h = gitsync.merge_health({"consecutive_errors": 1, "balance": {"credits": 900, "at": 5}, "errors": [{"at": 1}]},
                             {"consecutive_errors": 2, "balance": {"credits": 700, "at": 9}, "errors": [{"at": 2}]})
    assert h["balance"]["credits"] == 700 and h["consecutive_errors"] == 2 and len(h["errors"]) == 2
    assert gitsync.union_lines("a\nb\n", "a\nc\n") == "a\nb\nc\n"


def test_refs_png_are_ignored():
    r = subprocess.run(["git", "check-ignore", "-q", "usina/pages/gersinho/refs/rosto.png"], cwd=HERE.parent)
    assert r.returncode == 0                           # o `git add -A usina` do fim do ciclo não sobe o rosto


# ---------- 2. tetos no fuso do Caio ----------

SYD = ZoneInfo("Australia/Sydney")


def ts(y, mo, d, h, mi=0, zone=SYD):
    return datetime(y, mo, d, h, mi, tzinfo=zone).timestamp()


@pytest.fixture()
def ledger_env(tmp_path, monkeypatch):
    from pipeline import budget
    bud = tmp_path / "budget.yaml"
    bud.write_text((HERE / "budget.yaml").read_text())
    monkeypatch.setattr(budget, "BUDGET", bud)
    monkeypatch.setattr(budget, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(budget, "PAUSE_FILE", tmp_path / "PAUSE")
    return budget, bud


def test_day_cap_resets_at_sydney_midnight(ledger_env):
    budget, _ = ledger_env
    assert yaml.safe_load((HERE / "budget.yaml").read_text())["timezone"] == "Australia/Sydney"
    late = ts(2026, 10, 6, 23, 30)                     # 23:30 em Sydney = 12:30 UTC do mesmo dia 6
    budget.record("gersinho", "x", "higgsfield", "video_submit", usd=11.0, at=late)
    assert not budget.can_spend("higgsfield", 2.0, now=ts(2026, 10, 6, 23, 50))[0]
    after = ts(2026, 10, 7, 0, 10)                     # 00:10 em Sydney = 13:10 UTC, AINDA dia 6 em UTC
    assert datetime.fromtimestamp(after, ZoneInfo("UTC")).day == 6
    assert budget.can_spend("higgsfield", 2.0, now=after)[0]
    assert budget.spend(after).today == {}
    # e o contrário: 09:00 em Sydney do dia 7 é 22:00 UTC do dia 6, mesmo dia local que 00:10
    budget.record("gersinho", "x", "openai", "image", usd=1.9, at=after)
    assert not budget.can_spend("openai", 0.2, now=ts(2026, 10, 7, 9))[0]


def test_month_cap_by_local_month(ledger_env):
    budget, _ = ledger_env
    budget.record("gersinho", "x", "higgsfield", "video_submit", usd=250.0, at=ts(2026, 10, 31, 23))
    nov = ts(2026, 11, 1, 1)                            # 1º/11 01:00 em Sydney = 31/10 14:00 UTC
    assert budget.spend(nov).month_usd == 0
    assert budget.spend(ts(2026, 10, 31, 23, 30)).month_usd == 250.0


def test_timezone_configurable_and_bad_value_falls_back(ledger_env):
    budget, bud = ledger_env
    budget.record("gersinho", "x", "openai", "image", usd=1.5, at=ts(2026, 10, 6, 23, 30))
    now = ts(2026, 10, 7, 0, 10)
    assert budget.spend(now).today == {}
    bud.write_text(bud.read_text().replace("timezone: Australia/Sydney", "timezone: UTC"))
    assert budget.spend(now).today == {"openai": 1.5}                 # em UTC ainda é o mesmo dia
    bud.write_text(bud.read_text().replace("timezone: UTC", "timezone: Marte/Olympus"))
    assert budget.tz().key == "Australia/Sydney" and budget.spend(now).today == {}


# ---------- 3. até 3 ideias novas por ciclo ----------

def set_yaml(path, **kw):
    d = yaml.safe_load(path.read_text())
    d.update(kw)
    path.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False))


def new_ideas(root, page="gersinho"):
    return [a for a in plan(root)["actions"] if a["do"] == "new_ideas" and a["page"] == page]


def test_new_ideas_capped_per_cycle_and_configurable(usina):
    pg = usina / "pages" / "gersinho" / "page.yaml"
    d = yaml.safe_load(pg.read_text())
    d.setdefault("cadence", {})["posts_per_day"] = 3                 # estoque-alvo 9
    pg.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False))
    ni = new_ideas(usina)
    assert ni[0]["count"] == 3 and ni[0]["stock_missing"] == 9 and "Escolha 3 ideia" in ni[0]["how"]
    assert any("faltam 9 ideias" in n for n in plan(usina)["notes"])
    set_yaml(usina / "budget.yaml", new_ideas_per_cycle=5)
    assert new_ideas(usina)[0]["count"] == 5
    set_yaml(pg, new_ideas_per_cycle=1)                              # a página sobrepõe o budget
    assert new_ideas(usina)[0]["count"] == 1
    set_yaml(pg, new_ideas_per_cycle="x")                            # valor torto cai no do budget
    assert new_ideas(usina)[0]["count"] == 5


# ---------- 4. status --morning ----------

def test_morning_digest(usina):
    ref = run(usina, "new", "gersinho", "Busao", "--idea", "porta").stdout.strip()
    run(usina, "save-script", ref, EXAMPLE)
    run(usina, "image", ref, "storyboard")
    run(usina, "review", ref, "storyboard", "pass")                 # 2 semanas de calibração: espera o Caio
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    out = subprocess.run([sys.executable, "-m", "pipeline", "status", "--morning"], cwd=usina,
                         capture_output=True, text=True, env=env).stdout
    assert "bom dia, Caio" in out and "Australia/Sydney" in out
    assert "Esperando você (1):" in out and f"Caixa › Storyboard: {ref} (Busao)" in out
    assert "gersinho/Busao: roteiro pronto" in out and "gasto: US$" in out and "vira à meia-noite local" in out
    assert "OPENAI_API_KEY ausente" in out and "Vídeo desligado" not in out and "refs locais faltando" not in out
    assert "- gersinho: aberto" in out and "- marlene: rascunho" in out and "D+20" in out
    (usina / "pages/gersinho/refs/rosto.png").unlink()
    set_yaml(usina / "budget.yaml", switches={"video_enabled": False, "image_provider": "openai"})
    run(usina, "pause", "férias")
    out = subprocess.run([sys.executable, "-m", "pipeline", "status", "--morning"], cwd=usina,
                         capture_output=True, text=True, env=env).stdout
    assert "PAUSADO: férias" in out and "Vídeo desligado" in out and "refs locais faltando (rosto.png)" in out
    assert "Caixa › Storyboard" in out                               # com PAUSE a espera continua visível
    assert len(out.splitlines()) <= 25


def test_panel_export_waiting_survives_pause(usina):
    ref = run(usina, "new", "gersinho", "Busao", "--idea", "porta").stdout.strip()
    run(usina, "save-script", ref, EXAMPLE)
    run(usina, "image", ref, "storyboard")
    run(usina, "review", ref, "storyboard", "pass")
    run(usina, "pause", "x")
    run(usina, "panel-export")
    b = json.loads((usina / "out/panel/batch.json").read_text())
    saude = [w for w in b if w.get("collection") == "saude"][0]["data"]
    assert saude["waiting"] == [f"{ref} · storyboard"]
