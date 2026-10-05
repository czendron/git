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


# ---------- 2. livro de falhas no roteirista (D9.6) ----------

def test_memory_shows_failure_book_for_page_and_general(usina):
    fails = usina / "playbook" / "falhas.md"
    rows = [f"| 2026-10-0{1 + i % 9} | gersinho | video | item{i} | falha gersinho {i} |" for i in range(20)]
    rows += ["| 2026-10-02 | marlene | frames | m1 | falha da marlene |",
             "| 2026-10-02 | geral | video | - | vento mexe o topete |",
             "- dica livre: nunca usar câmera lenta",
             "- marlene: laquê derrete"]
    fails.write_text("# Livro\n\n| data | página | etapa | item | o que falhou |\n|---|---|---|---|---|\n" + "\n".join(rows))
    out = run(usina, "memory", "gersinho").stdout
    assert "falha gersinho 19" in out and "falha gersinho 5" in out and "| item4 |" not in out  # últimas 15
    assert "vento mexe o topete" in out and "câmera lenta" in out
    assert "marlene" not in out


def test_save_script_warns_repeated_place(usina, tmp_path):
    a = run(usina, "new", "gersinho", "Busao", "--idea", "porta").stdout.strip()
    assert "cenário repete" not in run(usina, "save-script", a, EXAMPLE).stdout
    b = run(usina, "new", "gersinho", "Busao 2", "--idea", "outra").stdout.strip()
    out = run(usina, "save-script", b, EXAMPLE).stdout          # mesmo ponto de ônibus
    assert "aviso: cenário repete" in out
    s = json.loads((usina / EXAMPLE).read_text())
    s["location"]["place"] = "feira livre de domingo, banca de pastel"
    s["en"]["location"] = "a crowded Sunday street market, pastel stall with a deep fryer, plastic awnings"
    f = tmp_path / "feira.json"
    f.write_text(json.dumps(s))
    c = run(usina, "new", "gersinho", "Feira", "--idea", "feira").stdout.strip()
    assert "cenário repete" not in run(usina, "save-script", c, str(f)).stdout
