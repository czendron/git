"""Rodada 3 de QA (docs/qa/rodada-3.md): divergências com a ata fechadas no código.
Lock de ciclo, livro de falhas no roteirista (D9.6), portão de estreia (D6), trend única/teto (D7),
gag pós-motion control (C5) e 4 variações do frame da trend (C5)."""
import json
import time

from test_pipeline import run, usina  # noqa: F401  (fixture reaproveitada)
from test_qa_rodada1 import EXAMPLE, item_json, ledger, plan, to_frames_approved


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
    s["en"]["location"] = "a Sunday street market, pastel stall with a deep fryer, plastic awnings"
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


# ---------- 6. 4 variações do frame da trend (C5) ----------

def trend_with_source(root, tmp_path):
    from test_qa_rodada2 import clip
    ref = run(root, "new", "gersinho", "Trend", "--idea", "gang").stdout.strip()
    run(root, "save-script", ref, TREND)
    run(root, "motion-source", ref, "--file", str(clip(tmp_path / "src.mp4")))
    return ref


def test_trend_frame_variants_and_pick(usina, tmp_path):
    ref = trend_with_source(usina, tmp_path)
    acts = [a for a in plan(usina)["actions"] if a.get("item") == ref]
    assert acts[0]["cmd"].endswith("frames --variants 4") and acts[0]["cost_usd"] > 0.5
    out = run(usina, "image", ref, "frames", "--variants", "4").stdout
    assert out.count("ok: ") == 4
    it = item_json(usina)
    assert len(it["variants"]) == 4 and it["frames"] == {} and it["attempts"]["frames"] == 1
    assert len([r for r in ledger(usina) if r["action"] == "image_frames"]) == 4   # 4 imagens lançadas
    rv = [a for a in plan(usina)["actions"] if a.get("item") == ref][0]
    assert rv["do"] == "review_image" and rv.get("pick") and len(rv["file"]) == 4
    assert run(usina, "review", ref, "frames", "pass", ok=False).returncode == 1     # pick antes
    assert run(usina, "pick", ref, "frames", "7", ok=False).returncode == 1
    run(usina, "pick", ref, "frames", "3")
    it = item_json(usina)
    assert it["frames"]["start"]["picked"] == 3 and it["frames"]["start"]["path"].endswith("-o3.png")
    run(usina, "review", ref, "frames", "pass")
    assert run(usina, "pick", ref, "frames", "2", ok=False).returncode == 1          # já revisado
    vr = json.loads(run(usina, "video-request", ref).stdout)
    assert vr["ready"] is False and vr["upload_first"][0]["path"].endswith("-o3.png")
    # variações só na trend
    other = run(usina, "new", "gersinho", "Busao", "--idea", "porta").stdout.strip()
    run(usina, "save-script", other, EXAMPLE)
    assert run(usina, "image", other, "frames", "--variants", "4", "--force", ok=False).returncode == 1


def test_trend_variants_higgsfield_fallback(usina, tmp_path):
    bt = (usina / "budget.yaml").read_text().replace("image_fallback_allowed: false", "image_fallback_allowed: true")
    (usina / "budget.yaml").write_text(bt)
    ref = trend_with_source(usina, tmp_path)
    run(usina, "record-upload", ref, "source_first", "--hf-id", "SF")
    out = json.loads(run(usina, "image", ref, "frames", "--provider", "higgsfield", "--variants", "4").stdout)
    assert len(out["requests"]) == 4 and all("var" in t for t in out["then"]) and "pick" in out["depois"]
    for k in (1, 2):
        run(usina, "record-image", ref, "frames", f"var{k}", "--hf-job", f"HJ{k}")
    it = item_json(usina)
    assert it["state"] == "frames" and len(it["variants"]) == 2 and it["attempts"]["frames"] == 1
    run(usina, "pick", ref, "frames", "2")
    assert item_json(usina)["frames"]["start"]["higgsfield_id"] == "HJ2"


# ---------- 5. gag pós-motion control (C5) ----------

def dur(path):
    import subprocess
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True, check=True).stdout)


def trend_in_revisao(root, tmp_path):
    from test_qa_rodada2 import clip
    ref = trend_with_source(root, tmp_path)
    run(root, "image", ref, "frames", "--variants", "4")
    run(root, "pick", ref, "frames", "1")
    run(root, "review", ref, "frames", "pass")
    run(root, "approve", ref, "frames")
    run(root, "record-upload", ref, "start", "--hf-id", "ST")
    run(root, "motion-source", ref, "--hf-id", "SRC")
    run(root, "record-video", ref, "--job", "MC1", "--credits", "64")
    run(root, "record-video", ref, "--url", "https://x/mc.mp4")
    run(root, "fetch-video", ref, "--file", str(clip(tmp_path / "mc.mp4", dur=6)))
    run(root, "review", ref, "video", "pass")
    return ref


def test_gag_lint(usina, tmp_path):
    s = json.loads((usina / TREND).read_text())
    s["gag_followup"]["duration_s"] = 8
    s["gag_followup"]["en"]["stages"] = s["gag_followup"]["en"]["stages"][:1]
    del s["gag_followup"]["en"]["end_change"]
    f = tmp_path / "g.json"
    f.write_text(json.dumps(s))
    out = run(usina, "lint", str(f), ok=False).stdout
    assert "4–5 s" in out and "use 2" in out and "end_change" in out


def test_gag_followup_flow_and_concat(usina, tmp_path):
    from test_qa_rodada2 import clip
    ref = trend_in_revisao(usina, tmp_path)
    acts = [a for a in plan(usina)["actions"] if a.get("item") == ref]
    assert acts and acts[0]["do"] == "video_submit" and acts[0]["gag"]
    assert not any(a.get("cmd", "").startswith("python -m pipeline package") for a in acts)
    vr = json.loads(run(usina, "video-request", ref, "--gag").stdout)
    assert vr["ready"] is False and vr["upload_first"][0]["key"] == "last"
    run(usina, "record-upload", ref, "last", "--hf-id", "LAST")
    vr = json.loads(run(usina, "video-request", ref, "--gag").stdout)
    p = vr["requests"][0]["params"]
    assert p["model"] == "seedance_2_5" and p["duration"] == 5
    assert p["medias"][0] == {"role": "start_image", "value": "LAST"}
    assert "seagull" in p["prompt"] and "last frame" in p["prompt"]
    run(usina, "record-video", ref, "--gag", "--job", "G1", "--credits", "40")
    run(usina, "record-video", ref, "--gag", "--job", "G1", "--credits", "40")     # idempotente
    assert len([r for r in ledger(usina) if r["action"] == "video_submit" and r["note"] == "gag"]) == 1
    assert run(usina, "video-request", ref, "--gag", ok=False).returncode == 1     # já enviado
    assert [a for a in plan(usina)["actions"] if a.get("item") == ref][0]["do"] == "video_poll"
    run(usina, "record-video", ref, "--gag", "--url", "https://x/gag.mp4")
    run(usina, "fetch-video", ref, "--gag", "--file", str(clip(tmp_path / "gag.mp4", dur=4)))
    a = [a for a in plan(usina)["actions"] if a.get("item") == ref][0]
    assert a["do"] == "review_video" and a["stage"] == "gag"
    run(usina, "approve", ref, "video")
    r = run(usina, "package", ref, ok=False)
    assert r.returncode == 1 and "gag" in r.stderr                               # gag sem QA
    run(usina, "review", ref, "gag", "pass")
    assert any(x.get("cmd", "").endswith(f"package {ref}") for x in plan(usina)["actions"])
    out = run(usina, "package", ref).stdout
    assert "sem reencode" in out
    it = item_json(usina)
    mp4 = usina / it["post"]["package"] / f"{ref.replace('/', '-')}.mp4"
    assert abs(dur(mp4) - 10) < 0.3 and it["post"]["with_gag"]
    assert "AI info' no post é OBRIGATÓRIO" in (usina / it["post"]["package"] / "CHECKLIST.md").read_text()


def test_gag_dropped_after_two_fails_packages_mc_only(usina, tmp_path):
    from test_qa_rodada2 import clip
    ref = trend_in_revisao(usina, tmp_path)
    run(usina, "record-upload", ref, "last", "--hf-id", "LAST")
    for n in (1, 2):
        run(usina, "record-video", ref, "--gag", "--job", f"G{n}", "--credits", "30")
        run(usina, "record-video", ref, "--gag", "--url", f"https://x/g{n}.mp4")
        run(usina, "fetch-video", ref, "--gag", "--file", str(clip(tmp_path / f"g{n}.mp4", dur=4)))
        run(usina, "review", ref, "gag", "fail", "--notes", "emenda pulou")
        if n == 1:
            assert any(a.get("cmd", "").endswith(f"retry {ref} gag") for a in plan(usina)["actions"])
            run(usina, "retry", ref, "gag")
    it = item_json(usina)
    assert it["video"]["gag"]["dropped"] and it["attempts"]["gag"] == 2
    assert run(usina, "video-request", ref, "--gag", ok=False).returncode == 1
    run(usina, "approve", ref, "video")
    assert "emendado" not in run(usina, "package", ref).stdout                # sai só o motion control
    assert "gag" in (usina / "playbook" / "falhas.md").read_text()


def test_gag_mismatched_clip_is_reencoded(usina, tmp_path):
    from test_qa_rodada2 import clip
    ref = trend_in_revisao(usina, tmp_path)
    run(usina, "record-upload", ref, "last", "--hf-id", "LAST")
    run(usina, "record-video", ref, "--gag", "--job", "G0", "--credits", "30")
    run(usina, "record-video", ref, "--gag", "--failed", "nsfw")                  # job falhou: pede de novo
    assert "já registrada" in run(usina, "record-video", ref, "--gag", "--failed", "nsfw").stdout
    assert [a for a in plan(usina)["actions"] if a.get("item") == ref][0]["do"] == "video_submit"
    run(usina, "record-video", ref, "--gag", "--job", "G1", "--credits", "30")
    run(usina, "record-video", ref, "--gag", "--url", "https://x/g1.mp4")
    run(usina, "fetch-video", ref, "--gag", "--file", str(clip(tmp_path / "g1.mp4", dur=4, size="720x1280")))
    run(usina, "review", ref, "gag", "pass")
    run(usina, "approve", ref, "video")
    assert "reencodado" in run(usina, "package", ref).stdout
    it = item_json(usina)
    assert abs(dur(usina / it["post"]["package"] / f"{ref.replace('/', '-')}.mp4") - 10) < 0.3
