"""Lint e prompts dos tutoriais §11–15 (docs/qa/lint-tutoriais.md): atores com nome (B4.11), substantivos do frame
final no texto (§15), contraparte fora do quadro (B4.10), corte num plano-sequência, tempo do gag e trend (§12)."""
import json
import sys
from copy import deepcopy

import pytest

from test_pipeline import HERE

sys.path.insert(0, str(HERE))
from pipeline import lint as L  # noqa: E402
from pipeline import prompts  # noqa: E402
from pipeline.store import get_page  # noqa: E402

BUS = "prompts/examples/gersinho-busao.json"
TREND = "prompts/examples/gersinho-trend-calcadao.json"
QUEUE = sorted((HERE / "data/queue/gersinho").glob("*.json"))
FACING = "chest 45° toward frame-right, face 0° to the lens, eyes on the lens"
CP_FACING = "in profile facing frame-left toward him, 90° to the lens"


def _load(rel):
    return json.loads((HERE / rel).read_text())


@pytest.fixture()
def page():
    return get_page("gersinho")


@pytest.fixture()
def bus():
    return _load(BUS)


def _lint(s):
    return L.lint(s, get_page("gersinho").data)


def _with_cp(s, text, cp, idx=2):
    s = deepcopy(s)
    st = s["en"]["stages"][idx]
    st["text"] = text
    st["facing"] = FACING
    st["counterpart"] = cp
    return s


def _vendor(who="DONA CIDA, the pastel vendor", **kw):
    return {"who": who, "position": "frame-right, 1 m from him, same depth", "facing": CP_FACING, **kw}


# ---------------- roteiros reais ----------------

def test_queue_and_examples_have_no_errors_nor_new_warnings():
    pg = get_page("gersinho").data
    files = [json.loads(f.read_text())["script"] for f in QUEUE] + [_load(BUS), _load(TREND)]
    assert len(files) >= 5  # a fila cresce; todo roteiro salvo tem que passar
    for s in files:
        e, w = L.lint(s, pg)
        assert e == [], (s["title"], e)
        assert not any("§15" in x or "consentimento" in x or "deadpan" in x or "B4.10" in x for x in w), w


# ---------------- B4.11: atores com nome ----------------

@pytest.mark.parametrize("who", ["the man", "a man", "the other man", "a woman", "a person", "the guy", "um cara",
                                 "o homem", "uma mulher", "a pessoa", "someone"])
def test_generic_counterpart_is_an_error(bus, who):
    s = _with_cp(bus, "A pastel lands in front of his chest; he keeps the pose.", _vendor(who))
    assert any("counterpart.who" in x and "B4.11" in x for x in _lint(s)[0]), who


@pytest.mark.parametrize("who", ["the woman in a red apron", "the old woman", "DONA CIDA", "the pastel vendor",
                                 "the boxer in red gloves", "the grey seagull"])
def test_named_or_described_counterpart_passes(bus, who):
    s = _with_cp(bus, "He keeps the pose.", _vendor(who, task="wipes her hands on her apron"))
    assert not any("counterpart.who" in x for x in _lint(s)[0]), who


def test_counterpart_cannot_share_the_protagonist_noun(bus):
    s = _with_cp(bus, "He keeps the pose.", _vendor("the bald man in a red tracksuit", task="waits"))
    e = _lint(s)[0]
    assert any("mesmo substantivo do protagonista" in x and "'man'" in x for x in e)
    s = _with_cp(bus, "He keeps the pose.", _vendor("the other singer", task="waits"))
    assert any("'singer'" in x for x in _lint(s)[0])
    # Marlene é 'woman': a mesma contraparte com descritor não colide com o Gersinho
    assert L.protagonist_nouns("marlene") >= {"woman", "marlene"}
    assert "woman" in L.protagonist_nouns("", {"character": {"pronoun": "she", "nickname": "Tia Marlene"}})


def test_other_man_and_image_handle_as_subject_are_errors(bus):
    cp = _vendor(task="waits")
    s = _with_cp(bus, "He keeps the pose; the other man waits.", cp)
    assert any("'the other man'" in x for x in _lint(s)[0])
    s = _with_cp(bus, "@Image 3 hands him a pastel; he keeps the pose.", cp)
    assert any("'@Image 3' como sujeito" in x for x in _lint(s)[0])
    s = _with_cp(bus, "He keeps the pose; then @Image 4 waves.", cp)
    assert any("como sujeito" in x for x in _lint(s)[0])
    s = _with_cp(bus, "His face still matches @Image 1; he keeps the pose.", cp)
    assert not any("como sujeito" in x for x in _lint(s)[0])


def test_human_counterpart_is_called_by_its_name_in_the_text(bus):
    s = _with_cp(bus, "A man holds a pastel out toward his chest.", _vendor())
    assert any("'A man'" in x and "DONA CIDA" in x for x in _lint(s)[0])
    s = _with_cp(bus, "The pastel vendor holds a pastel out toward his chest.", _vendor())
    assert not any("B4.11" in x for x in _lint(s)[0])


def test_video_prompt_binds_each_reference_to_a_name(bus, page):
    v = prompts.video_prompt(bus, page, has_start=True, has_end=True, has_storyboard=True)
    refs = v.split("ACTIVE REFERENCES")[1].split("CAMERA")[0]
    assert "@Image 1 (the close-up face photo on grey) is GERSINHO's face reference" in refs
    assert "@Image 2 (the silhouette sheet on grey) is GERSINHO's silhouette reference" in refs
    body = v.split("CAMERA")[1]
    assert "the man" not in body.lower()
    assert "GERSINHO's face matches his face reference (@Image 1)" in v
    stages = [x for x in v.splitlines() if x.startswith("[Stage")]
    assert stages[0].startswith("[Stage 1 — 0-1s] GERSINHO holds the signature pose")
    assert all("GERSINHO" in x for x in stages)            # um beat por estágio, com o dono nomeado (C4)


def test_human_counterpart_is_named_in_references_and_owns_its_beat(bus, page):
    s = _with_cp(bus, "DONA CIDA holds a pastel out 20 cm in front of his chest.", _vendor())
    s["en"]["stages"][3]["counterpart"] = _vendor(task="wipes her hands on her apron, eyes on him")
    v = prompts.video_prompt(s, page, has_start=True, has_end=True, has_storyboard=False)
    refs = v.split("ACTIVE REFERENCES")[1].split("CAMERA")[0]
    assert "DONA CIDA, the pastel vendor is a different person from GERSINHO" in refs
    assert "named only by name: GERSINHO, DONA CIDA, the pastel vendor." in refs
    st3 = [x for x in v.splitlines() if x.startswith("[Stage 3")][0]
    assert st3.startswith("[Stage 3 — 6.5-8.5s] DONA CIDA holds a pastel")   # a contraparte é dona do beat
    st = {"t": "0-2s", "text": "A pastel appears in front of his chest.", "facing": FACING,
          "counterpart": {"who": "the vendor", "position": "frame-right", "facing": CP_FACING}, "owner": "the vendor"}
    assert prompts._named(st["text"], st, "GERSINHO").startswith("The vendor's beat: a pastel appears")


def test_full_nickname_is_the_name(page):
    assert prompts.name(page) == "GERSINHO"
    assert prompts.name(get_page("marlene")) == "TIA MARLENE"


# ---------------- §15: substantivos do frame final no texto ----------------

def test_end_nouns_extracts_props_not_body_parts():
    n = L.end_nouns("the two glass door leaves are closed; the front tip of the rigid black pompadour sticks out "
                    "through the seam; his deadpan face is seen through the glass with the right index finger raised")
    assert {"leaves", "tip", "pompadour", "seam", "glass"} <= set(n)
    assert not {"face", "finger", "lens"} & set(n)


def test_end_frame_noun_missing_from_last_stages_warns(bus):
    s = deepcopy(bus)
    s["en"]["stages"][2]["text"] = s["en"]["stages"][2]["text"].replace("in a seam at the center", "at the center")
    w = _lint(s)[1]
    assert any("§15" in x and "'seam'" in x for x in w)
    s["end_frame"] = ""
    s["en"]["end_change"] = ""
    s["en"]["end_props"] = ""
    assert not any("§15" in x for x in L.lint(s)[1])


def test_end_nouns_in_gag_followup():
    s = _load(TREND)
    s["gag_followup"]["en"]["end_change"] = "a grey seagull standing on top of his rigid pompadour, a feather on his shoulder"
    s["gag_followup"]["en"]["end_props"] = "one paper cup dropped on the ground"
    w = _lint(s)[1]
    assert any("gag_followup.en.stages" in x and "'cup'" in x for x in w)
    assert not any("'seagull'" in x for x in w)


# ---------------- B4.10: contraparte fora do quadro ----------------

def _glove(**kw):
    return {"who": "the boxer in red gloves", "position": "off-screen, enters from the frame-right edge",
            "limb": "his right red glove", **kw}


def test_offscreen_counterpart_needs_vector_not_facing(bus):
    text = "The boxer's right glove enters from the frame-right edge and stops against the side of his pompadour."
    e = _lint(_with_cp(bus, text, _glove()))[0]
    assert any("fora do quadro" in x and "vetor de tela" in x for x in e)
    assert not any("counterpart.facing" in x or "declare 'counterpart'" in x for x in e)
    ok = _with_cp(bus, text, _glove(vector="travels screen-right to screen-left and stops against the pompadour"))
    assert _lint(ok)[0] == []
    in_text = _with_cp(bus, "The boxer's right glove travels screen-right to screen-left and stops against his "
                            "pompadour.", _glove(position="off-screen frame-right"))
    assert _lint(in_text)[0] == []
    assert L.is_offscreen({"position": "enters from frame-right edge"})
    assert L.is_offscreen({"position": "off-screen frame-right"})
    assert not L.is_offscreen({"position": "frame-right, 1 m from him"})


def test_offscreen_counterpart_renders_only_the_limb(bus, page):
    s = _with_cp(bus, "The boxer's right glove travels screen-right to screen-left and stops against his pompadour.",
                 _glove(vector="travels screen-right to screen-left at shoulder height"))
    v = prompts.video_prompt(s, page, has_start=True, has_end=True, has_storyboard=False)
    st3 = [x for x in v.splitlines() if x.startswith("[Stage 3")][0]
    assert ("The boxer in red gloves stays off-screen beyond the frame-right edge; only his right red glove enters "
            "the frame; it travels screen-right to screen-left at shoulder height.") in st3
    assert "No face or body of the boxer in red gloves appears in the frame." in st3
    assert "90° to the lens" not in st3


def test_human_on_screen_in_two_stages_gets_info_warning(bus):
    s = _with_cp(bus, "DONA CIDA holds a pastel out in front of his chest.", _vendor())
    s["en"]["stages"][3]["counterpart"] = _vendor(task="wipes her hands, eyes on him")
    w = _lint(s)[1]
    assert any(x.startswith("info:") and "considere B4.10 passo 0" in x for x in w)
    s["en"]["stages"][3]["counterpart"]["position"] = "off-screen frame-right"
    s["en"]["stages"][3]["counterpart"]["vector"] = "her hand stays still at frame-right to frame-center height"
    assert not any("B4.10 passo 0" in x for x in _lint(s)[1])
    gull = _with_cp(bus, "A grey seagull lands on top of his pompadour.",
                    {"who": "the grey seagull", "position": "on top of his pompadour", "facing": CP_FACING})
    gull["en"]["stages"][3]["counterpart"] = {"who": "the grey seagull", "position": "on top of his pompadour",
                                             "facing": CP_FACING, "task": "preens a wing"}
    assert not any("B4.10 passo 0" in x for x in _lint(gull)[1])          # bicho não conta


# ---------------- corte num clipe de plano-sequência ----------------

@pytest.mark.parametrize("bad", ["Cut to a close-up of the pompadour.", "Hard cut: the door is closed.",
                                 "Shot 2: the door closes on the pompadour."])
def test_cut_words_are_errors_without_declared_cut(bus, bad):
    s = deepcopy(bus)
    s["en"]["stages"][2]["text"] = bad
    assert any("plano-sequência" in x for x in _lint(s)[0])
    s["cut"] = {"at": 6.5}
    assert not any("plano-sequência" in x for x in _lint(s)[0])


def test_declared_cut_is_validated_and_rendered(bus, page):
    s = deepcopy(bus)
    s["cut"] = {"at": 12}
    assert any("cut.at 12.0s fora do clipe" in x for x in _lint(s)[0])
    s["cut"] = {"why": "inserto"}
    assert any("diga quando é o corte" in x for x in _lint(s)[0])
    s["cut"] = {"at": 6.5}
    v = prompts.video_prompt(s, page, has_start=True, has_end=True, has_storyboard=False)
    assert "Exactly one HARD CUT at 6.5s; otherwise the camera holds still" in v
    assert "does not cut on its own" not in v
    assert "does not cut on its own" in prompts.video_prompt(bus, page, has_start=True, has_end=True,
                                                             has_storyboard=False)


# ---------------- tempo do gag ----------------

def _retime(s, spans):
    s = deepcopy(s)
    for st, t in zip(s["en"]["stages"], spans):
        st["t"] = t
    return s


def test_gag_stage_needs_two_seconds(bus):
    e = _lint(_retime(bus, ["0-1s", "1-7s", "7-8.5s", "8.5-10s"]))[0]
    assert any("en.stages[3]" in x and "o gag precisa de ≥2 s" in x for x in e)


def test_final_hold_needs_half_a_second(bus):
    e = _lint(_retime(bus, ["0-1s", "1-6.5s", "6.5-9.6s", "9.6-10s"]))[0]
    assert any("en.stages[4]" in x and "hold final" in x for x in e)
    assert not any("precisa de ≥" in x for x in _lint(bus)[0])


def test_gag_followup_last_stage_holds_gag_and_rest():
    s = _load(TREND)
    st = s["gag_followup"]["en"]["stages"]
    st[0]["t"], st[1]["t"] = "0-3s", "3-5s"
    assert any("gag_followup.en.stages[2]" in x and "≥2.5 s" in x for x in _lint(s)[0])


# ---------------- trend (§12) ----------------

def test_trend_warns_without_consent_and_deadpan_source():
    s = _load(TREND)
    del s["trend"]["consent"]
    del s["en"]["source_expression"]
    e, w = _lint(s)
    assert e == []
    assert any("consentimento" in x for x in w)
    assert any("dançarino da fonte" in x and "deadpan" in x for x in w)
    s["trend"]["source_hint"] += "; gravada pelo Caio"
    s["en"]["location"] += "; the source dancer keeps a deadpan face"
    w = _lint(s)[1]
    assert not any("consentimento" in x or "dançarino da fonte" in x for x in w)


# ---------------- C2: frame B com a luz do A ----------------

def test_frame_b_keeps_light_and_sharpness_of_frame_a(bus, page):
    assert "Same light direction, exposure and sharpness as image 1." in prompts.frame_b_prompt(bus, page)


# ---------------- falsos positivos do lote 2 (roteiros-gersinho-lote2.md) ----------------

@pytest.mark.parametrize("text,noun", [("the white string hangs above him", "string"),
                                       ("the ceiling of the elevator", "ceiling"),
                                       ("the striped awning over the stall", "awning"),
                                       ("the metal railing", "railing"),
                                       ("the yellow building at frame-left", "building"),
                                       ("the folding chair", "chair")])
def test_end_nouns_keeps_ing_nouns(text, noun):
    n = L.end_nouns(text)
    assert n[0] == noun, n
    assert "white" not in n and "folding" not in n


def test_end_nouns_still_drops_participles():
    assert L.end_nouns("the man standing near the cart, the boy waving") == ["cart", "boy"]


def test_end_nouns_skips_comparatives_and_quantifiers():
    n = L.end_nouns("two fewer cups on the tray, one more balloon, the less crowded side, a few more")
    assert {"cups", "tray", "balloon"} <= set(n)
    assert not {"fewer", "more", "less", "few"} & set(n)


def test_static_end_props_are_not_required(bus):
    s = deepcopy(bus)
    s["en"]["end_props"] = "the grey poles unchanged, the fruit stall, the two moored boats at frame-left"
    assert not any("§15" in x for x in _lint(s)[1])
    assert L.end_props_changed(s["en"]["end_props"]) == ""
    s["en"]["end_props"] = "the grey poles unchanged, the fruit stall now knocked over onto the curb"
    w = _lint(s)[1]
    assert any("§15" in x and "'stall'" in x for x in w)
    assert not any("'poles'" in x for x in w)
    assert L.end_props_changed("the helmet perched on top of the pompadour, the red motorcycle unchanged at "
                               "frame-left") == "the helmet perched on top of the pompadour"
    assert "end_change" in L.end_text({"end_change": "the end_change noun"})


def test_offscreen_limb_holding_still_needs_position_only(bus):
    s = _with_cp(bus, "The boxer's right glove enters from the frame-right edge and stops against his pompadour.",
                 _glove(vector="travels screen-right to screen-left and stops against the pompadour"))
    st = s["en"]["stages"][3]
    st["facing"] = FACING
    st["counterpart"] = _glove(task="the glove holds still against the pompadour")
    assert not any("vetor de tela" in x for x in _lint(s)[0])
    st["counterpart"] = _glove()
    st["text"] = "He keeps the pose; the boxer's right glove stays still against his pompadour."
    assert not any("vetor de tela" in x for x in _lint(s)[0])
    st["text"] = "He keeps the pose; the boxer's right glove pulls back out of the frame."
    assert any(x.startswith("en.stages[4].counterpart") and "vetor de tela" in x for x in _lint(s)[0])
    st["counterpart"] = _glove(vector="travels screen-left to screen-right and exits the frame")
    assert not any("vetor de tela" in x for x in _lint(s)[0])


@pytest.mark.parametrize("who", ["the black vulture", "o urubu do Ver-o-Peso", "the grey pigeon", "o pombo",
                                 "the stray dog", "o cachorro", "o vira-lata caramelo", "the cat", "o gato",
                                 "the chicken", "a galinha", "the horse", "o cavalo", "the donkey", "o jegue",
                                 "the parrot", "o papagaio", "the capybara", "a capivara", "the monkey", "o mico",
                                 "o macaco", "the cow", "a vaca", "the goat", "o bode"])
def test_common_brazilian_animals_are_not_human(who):
    assert not L.is_human({"who": who})
    assert not L.needs_sheet({"who": who, "position": "frame-right"})


def test_counterpart_kind_is_authoritative(bus):
    assert not L.is_human({"who": "SEU ZÉ", "kind": "animal"})
    assert not L.is_human({"who": "DONA CIDA", "kind": "object"})
    assert L.is_human({"who": "the dog-costume mascot", "kind": "human"})
    assert L.is_human({"who": "DONA CIDA, the pastel vendor"})
    assert not L.is_human({"who": "the red sandbag"})
    named = {"who": "SEU ZÉ", "kind": "animal", "position": "on top of his pompadour", "facing": CP_FACING}
    s = _with_cp(bus, "SEU ZÉ lands on top of his pompadour.", named)
    s["en"]["stages"][3]["counterpart"] = {**named, "task": "folds his wings"}
    assert not any("B4.10 passo 0" in x for x in _lint(s)[1])  # info de rosto humano só para gente
    human = {**named, "kind": "human", "position": "frame-right, 1 m from him"}
    s = _with_cp(bus, "SEU ZÉ holds a pastel out in front of his chest.", human)
    s["en"]["stages"][3]["counterpart"] = {**human, "task": "wipes his hands, eyes on him"}
    assert any("B4.10 passo 0" in x for x in _lint(s)[1])
