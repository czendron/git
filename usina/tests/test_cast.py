"""Elenco recorrente por página (docs/qa/elenco.md): pages/<p>/cast/<id>.yaml, `cast ...`, `image <p> cast-sheet`,
a aprovação na Caixa e as fichas do elenco nos frames, no vídeo e na trend. Só mock: nada vai à OpenAI nem ao
Higgsfield."""
import json
import sys

import yaml

from test_pipeline import HERE, run, usina  # noqa: F401  (fixture reaproveitada)

sys.path.insert(0, str(HERE))
from pipeline import cast as castmod  # noqa: E402
from pipeline import lint as L  # noqa: E402
from pipeline import prompts  # noqa: E402
from pipeline.store import get_page  # noqa: E402

BUS = "prompts/examples/gersinho-busao.json"
TREND = "prompts/examples/gersinho-trend-calcadao.json"
FACING = "chest 45° toward frame-right, face 0° to the lens, eyes on the lens"
NEIDE = {"who": "DONA NEIDE", "cast_id": "dona-neide", "position": "frame-right, 1 m from him, same depth",
         "facing": "in profile facing frame-left toward him, 90° to the lens"}


def _script(cp=NEIDE, extras=None):
    s = json.loads((HERE / BUS).read_text())
    st = s["en"]["stages"][2]
    st["text"], st["facing"], st["counterpart"] = "DONA NEIDE holds a pastel out 20 cm in front of his chest.", FACING, dict(cp)
    s["en"]["stages"][3]["counterpart"] = dict(cp, task="wipes her hands on her apron, eyes on him")
    if extras is not None:
        s["en"]["featured_extras"] = extras
    return s


def _save(root, tmp_path, s, title="Neide"):
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


def _member(root, cid):
    return yaml.safe_load((root / "pages/gersinho/cast" / f"{cid}.yaml").read_text())


def _storyboard_ok(root, ref):
    run(root, "image", ref, "storyboard")
    run(root, "review", ref, "storyboard", "pass")
    run(root, "approve", ref, "storyboard")


# ---------------- o elenco semeado ----------------

def test_seeded_cast_is_valid_and_fictional():
    cast = castmod.load("gersinho")
    assert {"seu-tadeu", "dona-neide", "seu-juvenal"} <= set(cast)
    for cid, m in cast.items():
        assert castmod.validate(m) == [], cid
        assert m["status"] == "rascunho" and not (m.get("refs") or {}).get("sheet")   # o Caio aprova a ficha uma vez
    assert "spiral" in cast["seu-tadeu"]["look"] and "Gersinho" in cast["seu-tadeu"]["role"]
    text = "".join((HERE / "pages/gersinho/cast" / f"{c}.yaml").read_text() for c in cast)
    assert "fictícia" in text


def test_cast_cli_new_show_list_and_sheet(usina):
    r = run(usina, "cast", "new", "gersinho", "seu-ze", "--name", "Seu Zé do Pastel", "--role", "pasteleiro",
            "--look", "a heavy man in his sixties with a white paper hat and a grease-stained apron")
    assert "cast-sheet seu-ze" in r.stdout
    assert run(usina, "cast", "new", "gersinho", "seu-ze", "--name", "x", "--role", "y", "--look", "z", ok=False).returncode == 1
    show = json.loads(run(usina, "cast", "show", "gersinho", "seu-ze").stdout)
    assert show["state"] == "sem ficha" and show["status"] == "rascunho"
    # aprovar sem ficha não vale
    assert "sem ficha" in run(usina, "cast", "approve", "gersinho", "seu-ze", ok=False).stderr
    run(usina, "image", "gersinho", "cast-sheet", "seu-ze")
    m = _member(usina, "seu-ze")
    assert m["refs"]["sheet"] == "cast/sheets/seu-ze-v1.png" and (usina / "pages/gersinho" / m["refs"]["sheet"]).exists()
    prompt = (usina / "pages/gersinho/cast/sheets/seu-ze-v1.prompt.txt").read_text()
    assert "SEU ZÉ DO PASTEL" in prompt and "non-recognizable" in prompt and "2x2" in prompt
    assert "no pompadour" in prompt                       # outra pessoa, nada do protagonista
    assert "já existe" in run(usina, "image", "gersinho", "cast-sheet", "seu-ze").stdout   # não gasta de novo
    rows = {r["cast_id"]: r for r in json.loads(run(usina, "cast", "list", "gersinho").stdout)}
    assert rows["seu-ze"]["state"] == "aguardando" and rows["seu-tadeu"]["state"] == "sem ficha"
    run(usina, "cast", "approve", "gersinho", "seu-ze", "--reject", "--notes", "parece um ator famoso")
    assert json.loads(run(usina, "cast", "show", "gersinho", "seu-ze").stdout)["state"] == "recusada"
    run(usina, "image", "gersinho", "cast-sheet", "seu-ze")   # recusada: refaz sem --force, com a nota do Caio
    assert "parece um ator famoso" in (usina / "pages/gersinho/cast/sheets/seu-ze-v2.prompt.txt").read_text()
    run(usina, "cast", "approve", "gersinho", "seu-ze")
    assert _member(usina, "seu-ze")["status"] == "aprovado"
    assert "image_cast_sheet" in (usina / "data/ledger.jsonl").read_text()


# ---------------- lint ----------------

def test_lint_warns_generic_people_and_errors_unknown_cast():
    page = get_page("gersinho").data
    s = _script(cp={k: v for k, v in NEIDE.items() if k != "cast_id"} | {"who": "the pastel vendor"})
    s["en"]["stages"][2]["text"] = "The pastel vendor holds a pastel out 20 cm in front of his chest."
    _, w = L.lint(s, page)
    assert any("sem cast_id nem look" in x for x in w)
    s = _script(extras=[{"position": "frame-left, 2 m behind the counter", "task": "counts coins"}])
    _, w = L.lint(s, page)
    assert any("figurante em destaque" in x and "sem cast_id nem look" in x for x in w)
    s = _script(cp=dict(NEIDE, cast_id="dona-inexistente"))
    e, _ = L.lint(s, page)
    assert any("dona-inexistente" in x for x in e)
    e, w = L.lint(_script(extras=[{"cast_id": "seu-juvenal", "position": "frame-left, 3 m away", "task": "counts coins"}]), page)
    assert e == [] and not any("elenco" in x or "figurante" in x for x in w)


def test_sheet_people_split_cast_and_oneoff():
    s = _script(extras=[{"cast_id": "seu-juvenal", "position": "left", "task": "counts coins"},
                        {"who": "the girl with the red umbrella", "look": "a teenage girl with a red umbrella",
                         "position": "right", "task": "waits"}])
    assert [p["cast_id"] for p in L.cast_people(s)] == ["dona-neide", "seu-juvenal"]
    assert [p["who"] for p in L.oneoff_people(s)] == ["the girl with the red umbrella"]


# ---------------- plano e frames ----------------

def test_plan_asks_cast_sheet_then_caio_then_frames_with_sheet(usina, tmp_path):
    ref = _save(usina, tmp_path, _script())
    _storyboard_ok(usina, ref)
    a = next(x for x in _plan(usina)["actions"] if x.get("item") == ref)
    assert a["cmd"] == "python -m pipeline image gersinho cast-sheet dona-neide" and a["provider"] == "openai"
    assert "image" in run(usina, "image", ref, "frames", ok=False).stderr     # o image frames também recusa
    run(usina, "image", "gersinho", "cast-sheet", "dona-neide")
    pl = _plan(usina)
    assert any(w.get("stage") == "elenco" and w.get("cast_id") == "dona-neide" for w in pl["waiting_caio"])
    assert not any(x.get("item") == ref for x in pl["actions"])
    # o Caio aprova no card Elenco da Caixa
    run(usina, "panel-export")
    batch = json.loads((usina / "out/panel/batch.json").read_text())
    el = next(w for w in batch if w["collection"] == "elenco" and w["doc_id"] == "gersinho--dona-neide")["data"]
    assert el["state"] == "aguardando" and ref in el["usedBy"] and el["sheetAt"] > 0
    sau = next(w for w in batch if w["collection"] == "saude")["data"]
    assert sau["budget"] == {"mcPerS": 8, "maxCreditsIdea": 160, "dayCapCredits": 240}
    dec = tmp_path / "dec.json"
    dec.write_text(json.dumps([{"id": "d-el", "data": {"ref": "gersinho/dona-neide", "stage": "elenco",
                                                       "verdict": "approve", "notes": "", "at": el["sheetAt"] + 1000}}]))
    out = json.loads(run(usina, "panel-apply", str(dec)).stdout.strip().splitlines()[-1])
    assert out["applied_ids"] == ["d-el"] and _member(usina, "dona-neide")["status"] == "aprovado"
    assert "já aplicada" in run(usina, "panel-apply", str(dec)).stdout
    # agora os frames, com a ficha do elenco como imagem a mais e ligada ao nome
    a = next(x for x in _plan(usina)["actions"] if x.get("item") == ref)
    assert a["cmd"].endswith(f"image {ref} frames")    # sem ficha avulsa: quem tem cast_id usa o elenco
    run(usina, "image", ref, "frames")
    it = _item(usina, ref)
    assert not it["counterpart"]
    assert "DONA NEIDE is defined only by image 4" in it["frames"]["start"]["prompt"]   # rosto, silhueta, grade, ficha
    assert "DONA NEIDE is defined only by image 4" in it["frames"]["end"]["prompt"]     # frame A, rosto, silhueta, ficha


def test_video_request_feeds_cast_sheet_with_role_line(usina, tmp_path):
    ref = _save(usina, tmp_path, _script())
    _storyboard_ok(usina, ref)
    run(usina, "image", "gersinho", "cast-sheet", "dona-neide")
    run(usina, "cast", "approve", "gersinho", "dona-neide")
    run(usina, "image", ref, "frames")
    run(usina, "review", ref, "frames", "pass")
    run(usina, "approve", ref, "frames")
    for k in ("start", "end", "storyboard"):
        run(usina, "record-upload", ref, k, "--hf-id", f"id-{k}")
    vr = json.loads(run(usina, "video-request", ref).stdout)
    assert vr["ready"] is False and vr["upload_first"] == [{"key": "cast:dona-neide", "path": vr["upload_first"][0]["path"], "type": "image"}]
    run(usina, "record-upload", ref, "cast:dona-neide", "--hf-id", "id-neide")
    assert _member(usina, "dona-neide")["refs"]["higgsfield_id"] == "id-neide"
    vr = json.loads(run(usina, "video-request", ref).stdout)
    medias = vr["requests"][0]["params"]["medias"]
    assert [m["value"] for m in medias if m["role"] == "image_references"][-1] == "id-neide"
    p = vr["requests"][0]["params"]["prompt"]
    assert "@Image 4 (the 4-panel reference sheet of another person on grey) is DONA NEIDE's reference" in p


def test_ref_cap_is_a_clear_error(usina, tmp_path):
    for i in range(14):
        run(usina, "cast", "new", "gersinho", f"extra-{i:02d}", "--name", f"Extra {i}", "--role", "figurante",
            "--look", f"an ordinary person number {i}")
        run(usina, "image", "gersinho", "cast-sheet", f"extra-{i:02d}")
        run(usina, "cast", "approve", "gersinho", f"extra-{i:02d}")
    extras = [{"cast_id": f"extra-{i:02d}", "position": "background", "task": "walks"} for i in range(14)]
    ref = _save(usina, tmp_path, _script(cp=dict(NEIDE, cast_id="extra-00", who="EXTRA 0"), extras=extras))
    _storyboard_ok(usina, ref)
    r = run(usina, "image", ref, "frames", ok=False)
    assert "limite de 16" in r.stderr


def test_media_status_archives_cast_sheet(usina):
    run(usina, "image", "gersinho", "cast-sheet", "seu-tadeu")
    st = json.loads(run(usina, "media-status").stdout)
    up = next(u for u in st["upload"] if u["key"] == "cast_sheet")
    assert up["ref"] == "cast:gersinho/seu-tadeu" and "cast asset gersinho seu-tadeu" in up["then"]
    run(usina, "cast", "asset", "gersinho", "seu-tadeu", "/_blob/" + "b" * 32)
    st = json.loads(run(usina, "media-status").stdout)
    assert not any(u["key"] == "cast_sheet" for u in st["upload"])
    (usina / "pages/gersinho" / _member(usina, "seu-tadeu")["refs"]["sheet"]).unlink()
    st = json.loads(run(usina, "media-status").stdout)
    rs = next(r for r in st["restore"] if r["key"] == "cast_sheet")
    assert rs["asset_id"] == "b" * 32 and "cast restore" in rs["then"]


# ---------------- trend: troca por gente do elenco ----------------

def test_trend_frame_prompt_handles_multiple_swaps():
    page = get_page("gersinho")
    s = json.loads((HERE / TREND).read_text())
    ik = {"swaps": [{"target": "the dancer in white, center", "replace_with": {"kind": "protagonist"}},
                    {"target": "the man in the cap, left", "replace_with": {"kind": "cast", "cast_id": "seu-tadeu"}},
                    {"target": "the green bottle", "replace_with": {"kind": "object", "description": "a closed black umbrella"}},
                    {"target": "the woman, right", "replace_with": {"kind": "new_character", "description": "a tall woman in a yellow raincoat"}}]}
    f = prompts.motion_frame_prompt(s, page, ik, [("seu-tadeu", "SEU TADEU CARIMBO")])
    assert f.startswith("Edit image 1. Make exactly these replacements")
    assert "1. Replace the dancer in white, center with GERSON BRILHANTINA" in f or "1. Replace the dancer in white, center with" in f
    assert "2. Replace the man in the cap, left with SEU TADEU CARIMBO, the person on the reference sheet in image 4" in f
    assert "3. Replace the green bottle with a closed black umbrella" in f
    assert "4. Replace the woman, right with a tall woman in a yellow raincoat: an invented, fictional person" in f
    assert "lips closed" in f
    scene = prompts.motion_scene_prompt(s, page, True, ik, [("seu-tadeu", "SEU TADEU CARIMBO")])
    assert "Image 4 (the 4-panel reference sheet of another person on grey) is SEU TADEU CARIMBO's identity reference" in scene
    assert prompts.swap_cast_order(ik) == ["seu-tadeu"]
    # pedido antigo (só replace_subject): o frame de sempre
    assert prompts.motion_frame_prompt(s, page, {"replace_subject": "the dancer, left"}).startswith(
        "Edit image 1. Replace the dancer")
