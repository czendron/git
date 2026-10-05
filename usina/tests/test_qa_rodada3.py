"""Rodada 3 de QA (docs/qa/rodada-3.md): divergências com a ata fechadas no código.
Lock de ciclo, livro de falhas no roteirista (D9.6), portão de estreia (D6), trend única/teto (D7),
gag pós-motion control (C5) e 4 variações do frame da trend (C5)."""
import json
import time

from test_pipeline import run, usina  # noqa: F401  (fixture reaproveitada)
from test_qa_rodada1 import EXAMPLE, item_json, plan, to_frames_approved


def write_lock(root, owner, age_s=0):
    (root / ".lock").write_text(json.dumps({"owner": owner, "host": "outra", "at": time.time() - age_s, "ttl_s": 7200}))


# ---------- 1. lock do ciclo ----------

def test_tick_lock_blocks_second_cycle_and_expires(usina):
    run(usina, "new", "gersinho", "Busao", "--idea", "porta")
    out = json.loads(run(usina, "tick-start", "--owner", "A").stdout)
    assert out["owner"] == "A" and (usina / ".lock").exists()
    assert plan(usina)["actions"]                       # o meu lock não me bloqueia
    r = run(usina, "tick-start", "--owner", "B", ok=False)
    assert r.returncode == 1 and "outro ciclo" in r.stderr
    write_lock(usina, "B")                              # outra sessão pegou o lock
    p = plan(usina)
    assert p["actions"] == [] and p.get("other_tick") and any("OUTRO CICLO" in n for n in p["notes"])
    assert run(usina, "tick-end", ok=False).returncode == 1   # não solto o lock de outro
    write_lock(usina, "B", age_s=3 * 3600)              # vencido: ignorado
    p = plan(usina)
    assert p["actions"] and any("vencido" in n for n in p["notes"])
    run(usina, "tick-start", "--owner", "A")
    run(usina, "tick-end")
    assert not (usina / ".lock").exists()
    assert "sem lock" in run(usina, "tick-end").stdout


def test_video_request_refuses_while_other_cycle_runs(usina):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    write_lock(usina, "OUTRA")
    r = run(usina, "video-request", ref, ok=False)
    assert r.returncode == 1 and "outro ciclo" in r.stderr
    run(usina, "tick-end", "--force")
    run(usina, "video-request", ref)
