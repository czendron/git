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


# ---------- 3. portão de estreia (D6) ----------

def set_page(root, slug, **kw):
    import yaml
    f = root / "pages" / slug / "page.yaml"
    d = yaml.safe_load(f.read_text())
    d.update(kw)
    f.write_text(yaml.safe_dump(d, allow_unicode=True))


def days_ago(n):
    return time.strftime("%Y-%m-%d", time.localtime(time.time() - n * 86400))


def test_draft_page_never_generates(usina, tmp_path):
    ref = run(usina, "new", "marlene", "Teste", "--idea", "x", "--force").stdout.strip()
    s = json.loads((usina / EXAMPLE).read_text())
    s["page"] = "marlene"
    f = tmp_path / "m.json"
    f.write_text(json.dumps(s))
    run(usina, "save-script", ref, str(f))
    r = run(usina, "image", ref, "storyboard", "--force", ok=False)
    assert r.returncode == 1 and "rascunho" in r.stderr
    c = json.loads(run(usina, "launch-check", "marlene").stdout)
    assert c["can_generate"] is False and c["status"] == "rascunho"
    assert not any(a.get("page") == "marlene" or a.get("item", "").startswith("marlene/") for a in plan(usina)["actions"])


def test_launch_gate_ficha_days_and_stock(usina):
    refs = [{"role": "face", "file": "refs/rosto.png", "higgsfield_id": "F"},
            {"role": "silhouette", "file": "refs/silhueta.png", "higgsfield_id": "S"}]
    set_page(usina, "marlene", status="ativo")                      # o Caio ativou, mas sem ficha
    c = json.loads(run(usina, "launch-check", "marlene").stdout)
    assert not c["can_generate"] and "ficha" in c["summary"]
    p = plan(usina)
    assert any("marlene: portão de estreia fechado" in n for n in p["notes"])
    assert not any(a.get("page") == "marlene" for a in p["actions"])
    assert run(usina, "new", "marlene", "x", "--idea", "y", ok=False).returncode == 1
    set_page(usina, "marlene", refs=refs)
    set_page(usina, "gersinho", launched_at=days_ago(5))
    c = json.loads(run(usina, "launch-check", "marlene").stdout)
    assert not c["can_generate"] and "D+10" in c["summary"]
    set_page(usina, "gersinho", launched_at=days_ago(12))
    c = json.loads(run(usina, "launch-check", "marlene").stdout)
    assert c["can_generate"] and not c["can_post"] and "0/10 prontos" in c["summary"]
    p = plan(usina)
    ni = [a for a in p["actions"] if a["do"] == "new_ideas" and a["page"] == "marlene"]
    assert ni and ni[0]["count"] == 10                                # estoque de estreia, não 3
    assert any("estreia: 0/10" in n for n in p["notes"])
    set_page(usina, "wanderley", status="ativo", refs=refs)
    c = json.loads(run(usina, "launch-check", "wanderley").stdout)
    assert not c["can_generate"] and "D+20" in c["summary"]           # P3 só no D+20
    import yaml
    assert yaml.safe_load((usina / "pages/wanderley/page.yaml").read_text())["status"] == "ativo"  # nada muda sozinho
    g = json.loads(run(usina, "launch-check", "gersinho").stdout)
    assert g["can_generate"] and g["can_post"]                        # P1: só a ficha


# ---------- 4. trend única na semana e teto de 30% (D7) ----------

TREND = "prompts/examples/gersinho-trend-calcadao.json"


def activate_marlene(root):
    refs = [{"role": "face", "file": "refs/rosto.png", "higgsfield_id": "F"},
            {"role": "silhouette", "file": "refs/silhueta.png", "higgsfield_id": "S"}]
    set_page(root, "marlene", status="ativo", refs=refs)
    set_page(root, "gersinho", launched_at=days_ago(15))


def test_same_trend_never_on_two_pages_same_week(usina, tmp_path):
    activate_marlene(usina)
    for i in range(3):   # gersinho com 3 roteiros próprios: a trend cabe nos 30%
        r = run(usina, "new", "gersinho", f"P{i}", "--idea", "x").stdout.strip()
        run(usina, "save-script", r, EXAMPLE)
    g = run(usina, "new", "gersinho", "Trend", "--idea", "gang").stdout.strip()
    out = run(usina, "save-script", g, TREND).stdout
    assert "teto" not in out
    s = json.loads((usina / TREND).read_text())
    s["page"] = "marlene"
    s["trend"]["name"] = "GANG  gang! (versão remix)"          # mesmo nome normalizado
    f = tmp_path / "m.json"
    f.write_text(json.dumps(s))
    m = run(usina, "new", "marlene", "Trend", "--idea", "gang").stdout.strip()
    r = run(usina, "save-script", m, str(f), ok=False)
    assert r.returncode == 1 and "duas páginas na mesma semana" in r.stdout
    # passados 7 dias, pode
    q = next((usina / "data/queue/gersinho").glob("*-trend.json"))
    d = json.loads(q.read_text())
    d["created_at"] -= 8 * 86400
    q.write_text(json.dumps(d))
    out = run(usina, "save-script", m, str(f)).stdout
    assert "teto" in out                                         # 1 de 1 roteiro da marlene = 100%: aviso


def test_trend_cap_30pct_plan_warns_and_stops_suggesting(usina, tmp_path):
    p = [a for a in plan(usina)["actions"] if a["do"] == "new_ideas"][0]
    assert p["allow_trend"] is False                             # 1º roteiro como trend = 100%
    for i in range(3):
        r = run(usina, "new", "gersinho", f"P{i}", "--idea", "x").stdout.strip()
        run(usina, "save-script", r, EXAMPLE)
    for f in (usina / "data/queue/gersinho").glob("*.json"):     # sai do estoque para o plano pedir ideias
        d = json.loads(f.read_text()); d["state"] = "postado"; f.write_text(json.dumps(d))
    pl = plan(usina)
    assert [a for a in pl["actions"] if a["do"] == "new_ideas"][0]["allow_trend"] is True   # 1/4 = 25%
    g = run(usina, "new", "gersinho", "Trend", "--idea", "gang").stdout.strip()
    run(usina, "save-script", g, TREND)
    t2 = run(usina, "new", "gersinho", "Trend2", "--idea", "outra").stdout.strip()
    s = json.loads((usina / TREND).read_text()); s["trend"]["name"] = "Outra trend"
    f = tmp_path / "t2.json"; f.write_text(json.dumps(s))
    assert "acima do teto" in run(usina, "save-script", t2, str(f)).stdout    # 2/5 = 40%
    pl = plan(usina)
    assert any("acima do teto" in n and "gersinho" in n for n in pl["notes"])
    ni = [a for a in pl["actions"] if a["do"] == "new_ideas"]
    assert ni and all(not a["allow_trend"] and "NÃO crie trend" in a["how"] for a in ni)
