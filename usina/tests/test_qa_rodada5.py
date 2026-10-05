"""Rodada 5 de QA (docs/qa/rodada-5.md): limite de 12 ações, livro de falhas do pipeline em data/falhas.jsonl,
folha do clipe do gag arquivada, lint do playbook B4 (contraparte) e folga do teto diário para o gag de MC pago.
"""
import glob
import json
import time

from test_pipeline import HERE, run, usina  # noqa: F401  (fixture reaproveitada)
from test_qa_rodada1 import EXAMPLE, item_json, ledger, plan, to_frames_approved
from test_qa_rodada2 import TREND, clip
from test_qa_rodada3 import trend_in_revisao


# ---------- 1. limite de 12 ações por ciclo ----------

def test_cap_actions_keeps_paid_work_and_cuts_new_spend_first():
    from pipeline import tick
    acts = [{"do": "new_ideas", "page": "gersinho", "count": 3}]
    acts += [{"do": "write_script", "item": f"g/w{i}"} for i in range(5)]
    acts += [{"do": "video_submit", "item": "g/vs", "provider": "higgsfield"}]
    acts += [{"do": "run", "item": f"g/img{i}", "cmd": f"python -m pipeline image g/img{i} storyboard",
              "provider": "openai"} for i in range(3)]
    acts += [{"do": "blocked", "item": "g/b", "why": "teto"}]
    acts += [{"do": "review_image", "item": f"g/r{i}"} for i in range(2)]
    acts += [{"do": "run", "item": "g/p", "cmd": "python -m pipeline package g/p"}]
    acts += [{"do": "run", "item": "g/f", "cmd": "python -m pipeline fetch-video g/f"}]
    acts += [{"do": "review_video", "item": "g/rv"}, {"do": "video_poll", "item": "g/vp"}]
    acts += [{"do": "check_balance"}]
    out = {"actions": acts, "notes": []}
    tick.cap_actions(out)
    work = [a for a in out["actions"] if a["do"] != "blocked"]
    assert len(work) == 12 and any(a["do"] == "blocked" for a in out["actions"])   # aviso não ocupa vaga
    assert [a["do"] for a in work[:4]] == ["check_balance", "run", "review_video", "video_poll"]
    assert {a.get("item") for a in work} >= {"g/f", "g/rv", "g/vp", "g/p", "g/r0", "g/r1", "g/img0", "g/vs"}
    cut = out["truncated"]
    assert [a["do"] for a in cut] == ["write_script"] * 4 + ["new_ideas"]           # gasto novo sai primeiro
    assert any("Limite de 12" in n and "new_ideas gersinho" in n for n in out["notes"])


def test_plan_enforces_cap_end_to_end(usina):
    for i in range(14):
        run(usina, "new", "gersinho", f"Ideia {i}", "--idea", f"ideia numero {i}")
    p = plan(usina)
    assert len([a for a in p["actions"] if a["do"] != "blocked"]) <= 12
    assert len(p["truncated"]) >= 2 and all(a["do"] == "write_script" for a in p["truncated"])
    assert any("Limite de 12" in n for n in p["notes"])


# ---------- 2. livro de falhas do pipeline: data/falhas.jsonl ----------

def test_failures_go_to_jsonl_memory_reads_both_and_digest(usina, tmp_path):
    (usina / "playbook" / "falhas.md").write_text(
        "# Livro\n\n- dica curada: nunca câmera lenta\n- marlene: laquê derrete\n")
    before = (usina / "playbook" / "falhas.md").read_text()
    ref = run(usina, "new", "gersinho", "Busao", "--idea", "x").stdout.strip()
    run(usina, "save-script", ref, EXAMPLE)
    run(usina, "image", ref, "storyboard")
    run(usina, "review", ref, "storyboard", "fail", "--notes", "G3 topete achatado [topete]")
    run(usina, "retry", ref, "storyboard")
    run(usina, "image", ref, "storyboard")
    run(usina, "review", ref, "storyboard", "pass")
    run(usina, "approve", ref, "storyboard", "--reject", "--notes", "topete torto [topete]")
    assert (usina / "playbook" / "falhas.md").read_text() == before            # o pipeline não escreve no playbook
    rows = [json.loads(x) for x in (usina / "data/falhas.jsonl").read_text().splitlines()]
    assert [r["category"] for r in rows] == ["topete", "topete"]
    assert rows[0]["page"] == "gersinho" and rows[0]["stage"] == "storyboard" and rows[1]["notes"].startswith("(Caio)")
    with (usina / "data/falhas.jsonl").open("a") as f:                       # linha cortada (merge, queda): ignorada
        f.write('{"quebrada": \n')
        f.write(json.dumps({"at": time.time(), "date": "2026-10-05", "page": "marlene", "item": "m1",
                            "stage": "video", "category": "laquê", "notes": "laquê derreteu"}) + "\n")
    out = run(usina, "memory", "gersinho").stdout
    assert "nunca câmera lenta" in out and "G3 topete achatado" in out and "(Caio) topete torto" in out
    assert "laquê" not in out                                                # falha de outra página não entra
    dg = run(usina, "falhas-digest").stdout
    assert dg.startswith("# Digest") and "## topete (2x)" in dg and "## laquê (1x)" in dg and "portões: G3" in dg
    dg = run(usina, "falhas-digest", "--page", "marlene").stdout
    assert "topete" not in dg and "laquê derreteu" in dg


def test_gitattributes_union_merge_for_failure_log():
    assert "usina/data/falhas.jsonl merge=union" in (HERE.parent / ".gitattributes").read_text()


# ---------- 3. folha do clipe do gag arquivada ----------

def test_gag_clip_sheet_is_archived_and_restorable(usina, tmp_path):
    ref = trend_in_revisao(usina, tmp_path)
    run(usina, "record-upload", ref, "last", "--hf-id", "LAST")
    run(usina, "record-video", ref, "--gag", "--job", "G1", "--credits", "32.5")
    run(usina, "record-video", ref, "--gag", "--url", "https://x/g.mp4")
    run(usina, "fetch-video", ref, "--gag", "--file", str(clip(tmp_path / "g.mp4", dur=4)))
    st = json.loads(run(usina, "media-status").stdout)
    up = {u["key"]: u for u in st["upload"]}
    assert {"gag_clip", "gag_clip_sheet"} <= set(up) and up["gag_clip_sheet"]["path"].endswith("gag-v1-sheet.jpg")
    run(usina, "panel-asset", ref, "gag_clip_sheet", "/_blob/" + "b" * 32, "--path", up["gag_clip_sheet"]["path"])
    assert not any(u["key"] == "gag_clip_sheet" for u in json.loads(run(usina, "media-status").stdout)["upload"])
    (usina / up["gag_clip_sheet"]["path"]).unlink()                          # container novo
    st = json.loads(run(usina, "media-status").stdout)
    assert [r["key"] for r in st["restore"]] == ["gag_clip_sheet"]
    run(usina, "review", ref, "gag", "fail", "--notes", "emenda pulou")
    run(usina, "retry", ref, "gag")
    assert "gag_clip_sheet" not in item_json(usina)["post"].get("assets", {})


# ---------- 4. lint do playbook B4 (contraparte) ----------

FACING = "chest 45° toward the boxer at frame-right, face 0° to the lens, eyes on the lens"


def boxer(position="frame-right, 1 m from him, same depth",
          facing="in profile facing frame-left toward him, 90° to the lens", **kw):
    return {"who": "the boxer", "position": position, "facing": facing, **kw}


def stage(text, cp=None, t="0-2s", facing=FACING):
    return {"t": t, "text": text, "facing": facing, "end_state": "the pompadour back in place",
            **({"counterpart": cp} if cp else {})}


def test_b4_playbook_example_is_clean():
    from pipeline.lint import lint_counterpart
    e, w = lint_counterpart([
        stage("The boxer's right glove travels screen-right to screen-left and stops against his pompadour.", boxer()),
        stage("On contact, the pompadour tilts 10° and springs back as one block; he does not move his face.",
              boxer(task="bounces on his toes, guard up, eyes on him"))])
    assert e == [] and w == []


def test_b4_counterpart_behind_is_error_unless_gag_requires():
    from pipeline.lint import lint_counterpart
    behind = [stage("The boxer swings at his pompadour.", boxer(position="behind him, 1 m away"))]
    e, _ = lint_counterpart(behind)
    assert any("atrás dele" in x and "gag_requires" in x for x in e)
    assert lint_counterpart(behind, allow_behind=True)[0] == []
    atras = [stage("The boxer swings at his pompadour.", boxer(position="atrás dele, a 1 m"))]
    assert lint_counterpart(atras)[0]
    implied = [stage("The boxer swings at his pompadour.", boxer(facing="facing his back, 0° to the lens"))]
    assert lint_counterpart(implied)[0]
    mine = [stage("The boxer swings at his pompadour.", boxer(), facing="his back turned to the boxer, 0° to the lens")]
    assert any("atrás dele" in x for x in lint_counterpart(mine)[0])
    counter = [stage("The vendor holds a pastel out toward him.",
                     {"who": "the vendor", "position": "behind the counter at frame-left, 1 m from him",
                      "facing": "3/4 toward him, 45° to the lens"})]
    assert lint_counterpart(counter)[0] == []                                 # atrás do balcão não é atrás dele


def test_b4_more_than_one_contact_per_clip():
    from pipeline.lint import lint_counterpart
    e, _ = lint_counterpart([stage("The boxer jabs his pompadour.", boxer()),
                             stage("The boxer slaps his cheek.", boxer(), t="2-4s")])
    assert any("2 contatos" in x and "B4.7" in x for x in e)
    e, _ = lint_counterpart([stage("The boxer punches his pompadour twice.", boxer())])
    assert any("contatos" in x for x in e)


def test_b4_one_actor_per_stage():
    from pipeline.lint import lint_counterpart
    e, _ = lint_counterpart([stage("The boxer punches his pompadour; he ducks and spins to frame-left.", boxer())])
    assert any("mesmo estágio" in x and "B4.5" in x for x in e)
    e, _ = lint_counterpart([stage("The boxer punches his pompadour; he keeps staring into the lens.", boxer())])
    assert not any("mesmo estágio" in x for x in e)


def test_b4_idle_counterpart_needs_task_warning():
    from pipeline.lint import lint_counterpart
    e, w = lint_counterpart([stage("He sways his hips to frame-left on the beat.", boxer()),
                             stage("He raises his finger.", None, t="2-4s"),
                             stage("The boxer swings at his pompadour.", boxer(), t="4-6s")])
    assert e == []
    assert any("[1].counterpart" in x and "task" in x for x in w)
    assert any("some entre os estágios 1 e 3" in x for x in w)


def test_b4_rules_through_full_lint_and_gag_requires(usina, tmp_path):
    from pipeline.lint import lint
    s = json.loads((usina / TREND).read_text())
    g = s["gag_followup"]["en"]["stages"]
    g[1]["counterpart"]["position"] = "behind him, perched on the railing"
    assert any("gag_followup.en.stages[2].counterpart" in x for x in lint(s)[0])
    s["gag_requires"] = "behind"
    assert not any("atrás" in x for x in lint(s)[0])


def test_queue_and_examples_pass_new_rules():
    from pipeline.lint import lint
    files = sorted(glob.glob(str(HERE / "data/queue/gersinho/*.json"))) + sorted(glob.glob(str(HERE / "prompts/examples/*.json")))
    assert len(files) >= 5
    for f in files:
        d = json.loads(open(f).read())
        e, _ = lint(d.get("script") if "script" in d else d)
        assert e == [], (f, e)


def test_counterpart_task_reaches_prompt():
    from pipeline import prompts
    st = stage("He raises his finger.", boxer(task="bounces on his toes, guard up, eyes on him"))
    assert "Meanwhile the boxer bounces on his toes" in prompts._orient(st)


# ---------- 5. folga do teto diário para o gag de MC pago ----------

def spend_today(root, usd):
    with (root / "data/ledger.jsonl").open("a") as f:
        f.write(json.dumps({"at": time.time(), "page": "gersinho", "item": "outro", "provider": "higgsfield",
                            "action": "video_submit", "usd": usd, "credits": 0, "job_id": "", "ok": True,
                            "note": ""}) + "\n")


def gag_action(root, ref):
    return [a for a in plan(root)["actions"] if a.get("item") == ref][0]


def test_gag_uses_20pct_over_daily_cap_when_mc_paid(usina, tmp_path):
    ref = trend_in_revisao(usina, tmp_path)               # MC pago: 64 créditos = US$ 3,20
    spend_today(usina, 7.8)                                # hoje: US$ 11,00; o gag (US$ 1,63) passa dos 12
    a = gag_action(usina, ref)
    assert a["do"] == "video_submit" and a["gag"] and a["day_overflow"] and "folga de 20%" in a["how"]
    run(usina, "record-upload", ref, "last", "--hf-id", "LAST")
    assert json.loads(run(usina, "video-request", ref, "--gag").stdout)["requests"]
    spend_today(usina, 2.0)                                # hoje: US$ 13,00 + 1,63 > 14,40 (12 + 20%)
    a = gag_action(usina, ref)
    assert a["do"] == "blocked" and "folga" in a["why"]
    r = run(usina, "video-request", ref, "--gag", ok=False)
    assert r.returncode == 1 and "teto diário" in r.stderr


def test_gag_overflow_never_passes_month_cap_nor_helps_other_spend(usina, tmp_path):
    from pipeline import budget
    ref = trend_in_revisao(usina, tmp_path)
    spend_today(usina, 7.8)
    import yaml
    b = yaml.safe_load((usina / "budget.yaml").read_text())
    b["month_cap"] = 11.5                                  # o mês não deixa: nada de folga
    (usina / "budget.yaml").write_text(yaml.safe_dump(b))
    a = gag_action(usina, ref)
    assert a["do"] == "blocked" and "mês" in a["why"]
    # a folga é só para o gag de MC pago: item sem gasto não ganha folga, e o vídeo comum segue no teto puro
    assert budget.GAG_DAY_OVERFLOW == 0.20
    assert budget.gag_overflow("gersinho", "item-que-nao-existe") == 0.0
