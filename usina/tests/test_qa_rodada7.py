"""Rodada 7 (docs/qa/rodada-7.md): trava de gasto no Higgsfield (switches.higgsfield_spend_enabled) e a ficha da
contraparte humana no quadro (lacuna do lint-tutoriais: B4.11 "ficha própria antes de qualquer vídeo"). Só mock."""
import json
import sys
from copy import deepcopy

import yaml

from test_pipeline import HERE, run, usina  # noqa: F401  (fixture reaproveitada)

sys.path.insert(0, str(HERE))
from pipeline import lint as L  # noqa: E402
from pipeline import prompts  # noqa: E402
from pipeline.store import get_page  # noqa: E402

BUS = "prompts/examples/gersinho-busao.json"
TREND = "prompts/examples/gersinho-trend-calcadao.json"
FACING = "chest 45° toward frame-right, face 0° to the lens, eyes on the lens"
CIDA = {"who": "DONA CIDA, the pastel vendor", "position": "frame-right, 1 m from him, same depth",
        "facing": "in profile facing frame-left toward him, 90° to the lens",
        "look": "a short woman in her sixties with grey curly hair and a flowered apron"}


def _set_switch(root, value: bool):
    b = root / "budget.yaml"
    d = yaml.safe_load(b.read_text())
    d["switches"]["higgsfield_spend_enabled"] = value
    b.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False))


def _script(cp=CIDA, text="DONA CIDA holds a pastel out 20 cm in front of his chest."):
    s = json.loads((HERE / BUS).read_text())
    st = s["en"]["stages"][2]
    st["text"], st["facing"], st["counterpart"] = text, FACING, dict(cp)
    s["en"]["stages"][3]["counterpart"] = dict(cp, task="wipes her hands on her apron, eyes on him")
    return s


def _save(root, tmp_path, s, title="Cida"):
    ref = run(root, "new", "gersinho", title, "--idea", "pastel").stdout.strip()
    f = tmp_path / f"{title}.json"
    f.write_text(json.dumps(s))
    run(root, "save-script", ref, str(f))
    return ref


def _item(root, ref):
    page, iid = ref.split("/")
    return json.loads((root / "data/queue" / page / f"{iid}.json").read_text())


def _plan(root):
    return json.loads(run(root, "plan").stdout)


def _to_storyboard_ok(root, ref):
    run(root, "image", ref, "storyboard")
    run(root, "review", ref, "storyboard", "pass")
    run(root, "approve", ref, "storyboard")


# ---------------- 1. trava do Higgsfield ----------------

def test_repo_budget_has_the_lock_off():
    b = yaml.safe_load((HERE / "budget.yaml").read_text())
    assert b["switches"]["higgsfield_spend_enabled"] is False


def test_video_request_refuses_in_every_mode(usina, tmp_path):
    ref = _save(usina, tmp_path, json.loads((HERE / BUS).read_text()), "Bus")
    for st in ("storyboard", "frames"):
        run(usina, "image", ref, st)
        run(usina, "review", ref, st, "pass")
        run(usina, "approve", ref, st)
    _set_switch(usina, False)
    for extra in ([], ["--repair", "keep the door"], ["--no-grid"], ["--gag"]):
        r = run(usina, "video-request", ref, *extra, ok=False)
        assert r.returncode == 1 and "switches.higgsfield_spend_enabled" in r.stderr, extra
        assert "requests" not in r.stdout
    trend = run(usina, "new", "gersinho", "Trend", "--idea", "t").stdout.strip()
    run(usina, "save-script", trend, TREND)
    r = run(usina, "video-request", trend, ok=False)
    assert "higgsfield_spend_enabled" in r.stderr


def test_higgsfield_image_and_sheet_fallbacks_refuse(usina, tmp_path):
    b = usina / "budget.yaml"
    b.write_text(b.read_text().replace("image_fallback_allowed: false", "image_fallback_allowed: true"))
    _set_switch(usina, False)
    ref = _save(usina, tmp_path, json.loads((HERE / BUS).read_text()), "Bus")
    for args in (["image", ref, "storyboard", "--provider", "higgsfield"],
                 ["sheet", "gersinho", "--provider", "higgsfield"]):
        r = run(usina, *args, ok=False)
        assert "higgsfield_spend_enabled" in r.stderr and "mcp__Higgsfield" not in r.stdout, args
    trend = run(usina, "new", "gersinho", "Trend", "--idea", "t").stdout.strip()
    run(usina, "save-script", trend, TREND)
    r = run(usina, "image", trend, "frames", "--variants", "4", "--provider", "higgsfield", ok=False)
    assert "higgsfield_spend_enabled" in r.stderr
    run(usina, "image", ref, "storyboard")                      # OpenAI segue
    from pipeline import budget  # noqa: F401  (só para o caminho de import)


def test_plan_and_morning_show_the_lock(usina, tmp_path):
    ref = _save(usina, tmp_path, json.loads((HERE / BUS).read_text()), "Bus")
    for st in ("storyboard", "frames"):
        run(usina, "image", ref, st)
        run(usina, "review", ref, st, "pass")
        run(usina, "approve", ref, st)
    assert any(a["do"] == "video_submit" for a in _plan(usina)["actions"])
    _set_switch(usina, False)
    pl = _plan(usina)
    assert pl["blockers"] and "higgsfield_spend_enabled" in pl["blockers"][0]
    assert any("BLOQUEIO" in n for n in pl["notes"])
    blk = [a for a in pl["actions"] if a["do"] == "blocked" and a.get("item") == ref]
    assert blk and "higgsfield_spend_enabled" in blk[0]["why"]
    assert not any(a["do"] in ("video_submit", "check_balance") for a in pl["actions"])
    out = run(usina, "status", "--morning").stdout
    bl = out.split("Bloqueios:")[1].split("Portão de estreia:")[0]
    assert "Gasto no Higgsfield travado" in bl and "higgsfield_spend_enabled" in bl


def test_missing_key_fails_closed(usina):
    b = usina / "budget.yaml"
    d = yaml.safe_load(b.read_text())
    d["switches"].pop("higgsfield_spend_enabled")
    b.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False))
    assert "higgsfield_spend_enabled" in run(usina, "video-request", "gersinho/x", ok=False).stderr


def test_skill_has_the_rule():
    s = (HERE.parent / ".claude/skills/usina/SKILL.md").read_text()
    rules = s.split("## Regras que nunca quebram")[1].split("## 0.")[0]
    assert "higgsfield_spend_enabled" in rules and "video_analysis_create" in rules and "Caio" in rules


# ---------------- 2. ficha da contraparte humana ----------------

def test_sheet_counterparts_only_for_on_screen_humans():
    assert [c["who"] for c in L.sheet_counterparts(_script())] == ["DONA CIDA, the pastel vendor"]
    off = dict(CIDA, position="off-screen, enters from the frame-right edge", vector="her hand travels screen-right "
               "to screen-left")
    assert L.sheet_counterparts(_script(off)) == []
    gull = dict(CIDA, who="the grey seagull")
    assert L.sheet_counterparts(_script(gull, "The grey seagull lands on top of his pompadour.")) == []
    bag = dict(CIDA, who="the red punching bag")
    assert L.sheet_counterparts(_script(bag, "The red punching bag swings toward his chest.")) == []
    assert L.sheet_counterparts(_script(dict(CIDA, who="the statue of a vendor", kind="human"))) != []
    assert L.sheet_counterparts(json.loads((HERE / TREND).read_text())) == []      # gaivota do gag


def test_counterpart_sheet_prompt_is_c1_fictional_and_not_him():
    pg = get_page("gersinho")
    p = json.loads(prompts.counterpart_sheet_prompt(_script(), pg, L.sheet_counterparts(_script())[0]))
    assert p["type"].startswith("character reference sheet") and set(p["layout"]) == {
        "top_left", "top_right", "bottom_left", "bottom_right"}
    ch = p["character"]
    assert "flowered apron" in ch and "fictional" in ch and "non-recognizable" in ch and "lookalike" in ch
    assert "different person from GERSINHO" in ch and "no pompadour" in ch


def test_video_and_frame_prompts_name_the_sheet():
    pg = get_page("gersinho")
    s = _script()
    v = prompts.video_prompt(s, pg, has_start=True, has_end=True, has_storyboard=True,
                             counterpart=("DONA CIDA, the pastel vendor", 4))
    refs = v.split("ACTIVE REFERENCES")[1].split("CAMERA")[0]
    assert "@Image 4 (the 4-panel reference sheet of another person on grey) is DONA CIDA, the pastel vendor's " \
           "reference" in refs
    assert "nothing of GERSINHO comes from @Image 4" in refs
    plain = prompts.video_prompt(s, pg, has_start=True, has_end=True, has_storyboard=True)
    assert "@Image 4" not in plain and "is a different person from GERSINHO" in plain
    a = prompts.frame_a_prompt(s, pg, True, ("DONA CIDA, the pastel vendor", 4))
    assert "defined only by image 4" in a and "\n\n" not in a
    assert "defined only by image" not in prompts.frame_a_prompt(s, pg, True)
    assert "defined only by image 4" in prompts.frame_b_prompt(s, pg, ("DONA CIDA, the pastel vendor", 4))


def test_counterpart_flow_mock(usina, tmp_path):
    ref = _save(usina, tmp_path, _script())
    _to_storyboard_ok(usina, ref)
    acts = [a for a in _plan(usina)["actions"] if a.get("item") == ref]
    assert acts[0]["cmd"].endswith(f"image {ref} counterpart") and acts[0]["provider"] == "openai"
    r = run(usina, "image", ref, "frames", ok=False)                 # frames sem a ficha: recusa
    assert f"image {ref} counterpart" in r.stderr
    run(usina, "image", ref, "counterpart")
    it = _item(usina, ref)
    assert it["counterpart"]["who"] == "DONA CIDA, the pastel vendor"
    assert (usina / it["counterpart"]["path"]).exists()
    assert "image_counterpart" in (usina / "data/ledger.jsonl").read_text()
    assert "já existe" in run(usina, "image", ref, "counterpart").stdout   # não gasta de novo
    acts = [a for a in _plan(usina)["actions"] if a.get("item") == ref]
    assert acts[0]["cmd"].endswith(f"image {ref} frames")
    run(usina, "image", ref, "frames")
    it = _item(usina, ref)
    assert "defined only by image 4" in it["frames"]["start"]["prompt"]    # rosto, silhueta, storyboard, ficha
    assert "defined only by image 4" in it["frames"]["end"]["prompt"]      # frame A, rosto, silhueta, ficha
    rv = [a for a in _plan(usina)["actions"] if a.get("item") == ref and a["do"] == "review_image"][0]
    assert it["counterpart"]["path"] in rv["file"] and "sósia" in rv["how"]
    ms = json.loads(run(usina, "media-status").stdout)
    assert any(u["key"] == "counterpart" and u["ref"] == ref for u in ms["upload"])
    run(usina, "panel-asset", ref, "counterpart", "/_blob/" + "c" * 32, "--path", it["counterpart"]["path"])
    assert _item(usina, ref)["post"]["media"]["counterpart"]["asset"] == "c" * 32
    run(usina, "review", ref, "frames", "pass")
    run(usina, "approve", ref, "frames")
    vr = json.loads(run(usina, "video-request", ref).stdout)
    assert {u["key"] for u in vr["upload_first"]} == {"start", "end", "storyboard", "counterpart"}
    for k, i in (("start", 1), ("end", 2), ("storyboard", 3), ("counterpart", 4)):
        run(usina, "record-upload", ref, k, "--hf-id", f"00000000-0000-0000-0000-00000000000{i}")
    p = json.loads(run(usina, "video-request", ref).stdout)["requests"][0]["params"]
    assert p["medias"][-1] == {"role": "image_references", "value": "00000000-0000-0000-0000-000000000004"}
    assert "@Image 4 (the 4-panel reference sheet" in p["prompt"]
    p = json.loads(run(usina, "video-request", ref, "--no-grid").stdout)["requests"][0]["params"]
    assert "@Image 3 (the 4-panel reference sheet" in p["prompt"] and "@Image 4" not in p["prompt"]


def test_offscreen_and_animal_skip_the_sheet(usina, tmp_path):
    off = dict(CIDA, position="off-screen, enters from the frame-right edge", limb="her right hand",
               vector="travels screen-right to screen-left and stops 20 cm in front of his chest")
    off.pop("facing")
    s = _script(off, "DONA CIDA's right hand holds a pastel out 20 cm in front of his chest.")
    ref = _save(usina, tmp_path, s, "Off")
    _to_storyboard_ok(usina, ref)
    acts = [a for a in _plan(usina)["actions"] if a.get("item") == ref]
    assert acts[0]["cmd"].endswith(f"image {ref} frames")
    assert "não tem contraparte humana" in run(usina, "image", ref, "counterpart", ok=False).stderr
    run(usina, "image", ref, "frames")
    assert "defined only by image" not in _item(usina, ref)["frames"]["start"]["prompt"]


def test_rewrite_with_another_counterpart_drops_the_old_sheet(usina, tmp_path):
    ref = _save(usina, tmp_path, _script())
    run(usina, "image", ref, "counterpart")
    assert _item(usina, ref)["counterpart"]
    s = _script(dict(CIDA, who="SEU ZÉ, the newsstand owner", look="a thin man in his seventies"),
                "SEU ZÉ, the newsstand owner holds a newspaper out 20 cm in front of his chest.")
    f = tmp_path / "ze.json"
    f.write_text(json.dumps(s))
    run(usina, "save-script", ref, str(f))
    assert _item(usina, ref)["counterpart"] == {}
    acts = [a for a in _plan(usina)["actions"] if a.get("item") == ref]
    assert acts and "storyboard" in acts[0]["cmd"]


def test_lost_counterpart_has_a_fix(usina, tmp_path):
    ref = _save(usina, tmp_path, _script())
    run(usina, "image", ref, "counterpart")
    (usina / _item(usina, ref)["counterpart"]["path"]).unlink()
    lost = json.loads(run(usina, "media-status").stdout)["lost"]
    assert any(x["key"] == "counterpart" and "image" in x["fix"] and "counterpart" in x["fix"] for x in lost)


def test_rubric_and_script_docs():
    rf = (HERE / "prompts/review_frames.md").read_text()
    assert "ficha" in rf and "sósia" in rf
    sm = (HERE / "prompts/script.md").read_text()
    assert '"look"' in sm and "image <ref> counterpart" in sm
