"""Crítica de prompts (docs/qa/critica-prompts.md): o que o pipeline emite tem de impedir a falha do boxe
(ele de costas quando o outro socou) e as contradições achadas nos prompts renderizados."""
import json
import re
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


def _load(rel):
    return json.loads((HERE / rel).read_text())


@pytest.fixture()
def page():
    return get_page("gersinho")


@pytest.fixture()
def bus():
    return _load(BUS)


def _boxing(s):
    """O caso que motivou a crítica: um boxeador soca na direção dele no estágio do gag."""
    s = deepcopy(s)
    st = s["en"]["stages"][2]
    st["text"] = ("A boxer in red gloves steps in from frame-left and throws a right jab that stops 5 cm from his "
                  "cheek; he keeps the pose.")
    st.pop("counterpart", None)
    return s


def _errors(s):
    return L.lint(s, {"slug": "gersinho", "character": {"bpm": 95}})[0]


# ---------------- lint: orientação e quem encara quem ----------------

def test_queue_and_examples_pass_lint():
    for f in QUEUE:
        e, _ = L.lint(json.loads(f.read_text())["script"])
        assert e == [], (f.name, e)
    for rel in (BUS, TREND):
        e, _ = L.lint(_load(rel))
        assert e == [], (rel, e)


def test_interaction_without_counterpart_is_an_error(bus):
    e = _errors(_boxing(bus))
    assert any("counterpart" in x and "stages[3]" in x for x in e)


def test_counterpart_needs_degrees(bus):
    s = _boxing(bus)
    s["en"]["stages"][2]["counterpart"] = {"who": "the boxer", "position": "frame-left, 60 cm from him",
                                           "facing": "toward him"}
    assert any("counterpart.facing" in x for x in _errors(s))
    s["en"]["stages"][2]["counterpart"]["facing"] = "in profile facing frame-right toward him, 90° to the lens"
    assert not any("counterpart" in x for x in _errors(s))


def test_every_stage_needs_facing_in_degrees_from_the_lens(bus):
    s = deepcopy(bus)
    s["en"]["stages"][1].pop("facing")
    assert any("stages[2]: falta 'facing'" in x for x in _errors(s))
    s["en"]["stages"][1]["facing"] = "toward the camera"
    assert any("stages[2].facing" in x and "graus" in x for x in _errors(s))


def test_back_to_the_lens_is_blocked_unless_it_is_the_joke(bus):
    s = deepcopy(bus)
    s["en"]["stages"][2]["facing"] = "back to the lens, 180° from the lens"
    assert any("costas" in x for x in _errors(s))
    s["premise"] += " A piada é ele de costas."
    assert not any("costas" in x for x in _errors(s))


def test_trend_gag_needs_counterpart_for_the_seagull():
    s = _load(TREND)
    s["gag_followup"]["en"]["stages"][1].pop("counterpart")
    e, _ = L.lint(s)
    assert any("gag_followup.en.stages[2]" in x and "counterpart" in x for x in e)


def test_vague_verbs_and_abstract_end_states_warn(bus):
    s = deepcopy(bus)
    s["en"]["stages"][1]["text"] = "Real-time, at 95 BPM: he dances on the step."
    s["en"]["stages"][3]["end_state"] = "frozen result, readable as a cover."
    w = L.lint(s)[1]
    assert any("verbo vago 'dances'" in x for x in w)
    assert any("end_state abstrato" in x for x in w)


# ---------------- lint: figurantes, mãos, FOV ----------------

def test_task_count():
    assert L.task_count("two joggers pass, one vendor arranges coconuts, one woman walks a dog") == 4
    assert L.task_count("three passengers read, one looks out, and one pedestrian walks") == 5
    assert L.task_count("people doing stuff") is None


def test_passersby_without_tasks_is_an_error(bus):
    s = deepcopy(bus)
    s["en"]["extras_count"] = 7
    assert any("5 de 7 figurantes" in x for x in _errors(s))


def test_crowd_words_contradict_the_exact_count(bus):
    s = deepcopy(bus)
    s["en"]["location"] = "a crowded bus stop"
    assert any("'crowded'" in x for x in _errors(s))


def test_hands_in_frame_with_passersby_is_an_error(bus):
    s = deepcopy(bus)
    s["en"]["hands"] = "Exactly two hands in frame, both his: left hand on his belly."
    assert any("hands in frame" in x for x in _errors(s))


def test_fov_must_match_the_camera_mode(bus):
    s = deepcopy(bus)
    s["camera"]["fov_deg"] = 47
    assert any("não bate com o modo" in x for x in _errors(s))


def test_selfie_hands_must_hold_the_phone(bus):
    s = deepcopy(bus)
    s["camera"].update(mode="selfie_pov", fov_deg=84)
    assert any("selfie" in x for x in _errors(s))
    s["en"]["hands"] = "He has exactly two hands: right hand holds the phone, left hand flat on his belly."
    assert not any("selfie" in x for x in _errors(s))


def test_different_shot_labels_in_a_locked_shot_warn(bus):
    s = deepcopy(bus)
    s["storyboard_panels"][2]["shot"] = "CU do topete"
    assert any("enquadramentos diferentes" in x for x in L.lint(s)[1])


# ---------------- prompts renderizados ----------------

def test_video_prompt_states_orientation_per_stage_and_counterpart_in_the_same_line(bus, page):
    s = _boxing(bus)
    s["en"]["stages"][2]["counterpart"] = {"who": "the boxer", "position": "frame-left, 60 cm from him",
                                           "facing": "in profile facing frame-right toward him, 90° to the lens"}
    v = prompts.video_prompt(s, page, has_start=True, has_end=True, has_storyboard=True)
    stage3 = next(line for line in v.splitlines() if line.startswith("[Stage 3"))
    assert "Orientation: chest 0° to the lens" in stage3
    assert "The boxer: frame-left, 60 cm from him, in profile facing frame-right toward him, 90° to the lens." in stage3
    assert "Unless a stage names a turn" in v


def test_orientation_is_repeated_only_when_it_changes(bus, page):
    v = prompts.video_prompt(bus, page, has_start=True, has_end=True, has_storyboard=False)
    stages = [line for line in v.splitlines() if line.startswith("[Stage")]
    assert "Orientation:" in stages[0] and "Orientation:" in stages[1] and "Orientation:" in stages[2]
    assert "Orientation:" not in stages[3]   # igual ao estágio 3: o "Unless a stage names a turn" segura


def test_last_end_state_is_concrete(bus, page):
    with_end = prompts.video_prompt(bus, page, has_start=True, has_end=True, has_storyboard=False)
    no_end = prompts.video_prompt(bus, page, has_start=True, has_end=False, has_storyboard=False)
    last = lambda t: [x for x in t.splitlines() if x.startswith("[Stage")][-1]  # noqa: E731
    assert "pinched" in last(with_end)
    assert prompts._lc(bus["en"]["end_change"]) in last(no_end)   # sem end_image, o end_change vai por extenso
    for f in QUEUE:
        s = json.loads(f.read_text())["script"]
        if not s or s.get("format") == "trend":  # trend usa motion_scene_prompt, não o C4
            continue
        for has_end in (True, False):
            v = prompts.video_prompt(s, page, has_start=True, has_end=has_end, has_storyboard=True)
            assert "readable as a cover" not in v and "frozen result" not in v


def test_reference_handles_name_the_material(bus, page):
    v = prompts.video_prompt(bus, page, has_start=True, has_end=True, has_storyboard=True)
    assert "@Image 1 (the close-up face photo on grey)" in v
    assert "@Image 2 (the silhouette sheet on grey)" in v
    assert "@Image 3 (the 4-panel storyboard grid)" in v
    assert "never change the start- or end-frame composition" in v
    # handles ficam no mapa de referências, nunca na prosa da ação (regra 10)
    assert not any("@Image" in x for x in v.splitlines() if x.startswith("[Stage"))


def test_video_prompt_identity_text_is_minimal(bus, page):
    v = prompts.video_prompt(bus, page, has_start=True, has_end=True, has_storyboard=True)
    scene = v.split("ACTIVE REFERENCES")[0]
    assert "silk shirt" not in scene and "gold chain" not in scene   # o figurino vem da silhueta (regra 8)
    assert v.count("twice the height of his own head") == 1           # a marca não se repete no PHYSICS
    assert v.count("Real-time") <= 2


def test_storyboard_carries_stage_orientation_and_the_whole_clip_prop_lock(bus, page):
    sb = json.loads(prompts.storyboard_prompt(bus, page)[0])
    assert all(p["orientation"].startswith("chest") and "°" in p["orientation"] for p in sb["panels"])
    assert "closed in the center in the last frame" in sb["rules"]   # não o estado do frame A para todos os painéis
    assert [p["time"] for p in sb["panels"]] == [st["t"] for st in bus["en"]["stages"]]


def test_frames_keep_the_face_big_and_state_orientation(bus, page):
    a = prompts.frame_a_prompt(bus, page, True)
    assert "3 m away" in a and "4 m" not in a
    assert "fills 80% of the frame height" in a
    assert "Orientation: chest 0° to the lens" in a
    b = prompts.frame_b_prompt(bus, page)
    assert "Orientation: chest 0° to the lens, face 0° to the lens, eyes on the lens through the glass." in b


def test_silhouette_text_agrees_with_the_page_bible(page):
    _, sil = prompts.silhouette(page)
    assert "twice the height of his own head" in sil and "twice the height of his head" in page.character["look"]
    assert "25 cm" not in sil


def test_motion_scene_writes_each_passerby_task_and_sheet_roles(page):
    s = _load(TREND)
    p = prompts.motion_scene_prompt(s, page)
    assert s["en"]["extras_tasks"] in p                       # a fonte não traz fundo (videos-analisados §8)
    assert "not extra people" in p and "image 3" in p          # ficha em toda geração (§5)
    assert "image 2" not in prompts.motion_scene_prompt(s, page, with_sheet=False)


def test_motion_frame_keeps_subject_size_and_clears_the_dance_path(page):
    p = prompts.motion_frame_prompt(_load(TREND), page)
    assert "subject size" in p and "at least 1.5 m from him" in p


def test_gag_prompt_has_counterpart_logline_and_no_duplicate_final_state(page):
    g = prompts.gag_prompt(_load(TREND), page)
    assert "Final state:" not in g
    assert "The grey seagull: standing on the top of his pompadour" in g
    assert "a grey seagull lands on top of his rigid pompadour" in g.split("ACTIVE REFERENCES")[0]
    assert "locked off, no zoom" in g


def test_rendered_prompts_have_no_slow_words_and_fixed_fov(page):
    slow = re.compile(r"\b(slowly|graceful|smooth)\b|\bslow (?!deliberate blink|blink|motion)", re.I)  # "no slow motion" é a proibição pelo nome (regra 19)
    for f in QUEUE:
        s = json.loads(f.read_text())["script"]
        if not s or s.get("format") == "trend":  # trend: motion_*_prompt (outro teste)
            continue
        texts = [prompts.storyboard_prompt(s, page)[0], prompts.frame_a_prompt(s, page, True),
                 prompts.frame_b_prompt(s, page),
                 prompts.video_prompt(s, page, has_start=True, has_end=True, has_storyboard=True)]
        for t in texts:
            assert not slow.search(t), (f.name, slow.search(t).group(0))
        assert "63°" in texts[3] and "47°" not in texts[3]
