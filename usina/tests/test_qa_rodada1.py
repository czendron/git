"""Regressões da rodada 1 de QA (docs/qa/rodada-1.md). Cada teste trava um bug corrigido."""
import json
import subprocess
import time
from pathlib import Path

import pytest

from test_pipeline import HERE, run, usina  # noqa: F401  (fixture reaproveitada)

EXAMPLE = "prompts/examples/gersinho-busao.json"


def item_json(root):
    return json.loads(next((root / "data/queue/gersinho").glob("*.json")).read_text())


def ledger(root):
    f = root / "data" / "ledger.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.exists() else []


def to_frames_approved(root, title="Busao"):
    ref = run(root, "new", "gersinho", title, "--idea", "porta").stdout.strip()
    run(root, "save-script", ref, EXAMPLE)
    run(root, "image", ref, "storyboard")
    run(root, "review", ref, "storyboard", "pass")
    run(root, "approve", ref, "storyboard")
    run(root, "image", ref, "frames")
    run(root, "review", ref, "frames", "pass")
    return ref


def plan(root):
    return json.loads(run(root, "plan").stdout)


def mp4(path: Path, size="360x640", codec="libx264", audio=False):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=24:duration=3"]
    if audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-shortest"]
    cmd += ["-c:v", codec]
    if codec == "libx264":
        cmd += ["-pix_fmt", "yuv420p"]
    subprocess.run(cmd + [str(path)], check=True)
    return path


# ---------- fluxo / estados ----------

def test_frames_rejected_by_caio_never_submits_video(usina):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames", "--reject", "--notes", "rosto errado")
    acts = plan(usina)["actions"]
    assert not any(a["do"] == "video_submit" for a in acts)
    assert any(a.get("cmd", "").endswith(f"retry {ref} frames") for a in acts)


def test_record_video_same_job_counts_once(usina):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    for _ in range(2):
        run(usina, "record-video", ref, "--job", "J1", "--credits", "65")
    assert item_json(usina)["attempts"]["video"] == 1
    assert len([r for r in ledger(usina) if r["action"] == "video_submit"]) == 1


def test_failed_job_does_not_get_stuck(usina):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    run(usina, "record-video", ref, "--job", "J1", "--credits", "65")
    run(usina, "record-video", ref, "--failed", "nsfw")
    it = item_json(usina)
    assert it["state"] == "frames" and it["video"]["history"][-1]["failed"] == "nsfw"
    assert any(a["do"] == "video_submit" for a in plan(usina)["actions"])


def test_per_idea_credit_cap_discards(usina):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    run(usina, "record-video", ref, "--job", "J1", "--credits", "65")
    run(usina, "record-video", ref, "--failed")
    run(usina, "record-video", ref, "--job", "J2", "--credits", "65")
    run(usina, "record-video", ref, "--failed")
    # 130 gastos + 65 da próxima > 160 (ata D5)
    acts = plan(usina)["actions"]
    assert any(a["do"] == "discard" and "160" in a["how"] for a in acts)


def test_state_guards_make_reruns_safe(usina):
    ref = run(usina, "new", "gersinho", "Busao", "--idea", "porta").stdout.strip()
    assert run(usina, "review", ref, "storyboard", "pass", ok=False).returncode == 1  # nada para revisar
    run(usina, "save-script", ref, EXAMPLE)
    run(usina, "image", ref, "storyboard")
    n = len(ledger(usina))
    assert run(usina, "image", ref, "storyboard", ok=False).returncode == 1   # re-run não gera nem cobra de novo
    assert len(ledger(usina)) == n
    assert run(usina, "save-script", ref, EXAMPLE, ok=False).returncode == 1  # não regride sem --force
    run(usina, "save-script", ref, EXAMPLE, "--force")
    assert item_json(usina)["state"] == "roteiro" and "storyboard" not in item_json(usina)["gates"]


def test_new_refuses_draft_page_and_duplicate(usina):
    assert run(usina, "new", "marlene", "x", ok=False).returncode == 1
    run(usina, "new", "gersinho", "Busão", "--idea", "a")
    assert run(usina, "new", "gersinho", "Busao", "--idea", "b", ok=False).returncode == 1


def test_video_review_rerun_counts_once_and_package_needs_caio(usina, tmp_path):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    run(usina, "record-video", ref, "--job", "J1", "--credits", "65", "--url", "https://x.invalid/v.mp4")
    run(usina, "fetch-video", ref, "--file", str(mp4(tmp_path / "v.mp4")))
    run(usina, "review", ref, "video", "fail", "--notes", "G4 [blocking-broken]")
    run(usina, "review", ref, "video", "fail", "--notes", "G4 [blocking-broken]")
    assert len([r for r in ledger(usina) if r["action"] == "video_review"]) == 1
    assert (usina / "playbook/falhas.md").read_text().count("blocking-broken") == 1
    run(usina, "retry", ref, "video")
    run(usina, "record-video", ref, "--job", "J2", "--credits", "1", "--url", "https://x.invalid/v2.mp4")
    run(usina, "fetch-video", ref, "--file", str(mp4(tmp_path / "v.mp4")))
    run(usina, "review", ref, "video", "pass")
    assert run(usina, "package", ref, ok=False).returncode == 1   # portão humano obrigatório (D3)
    run(usina, "approve", ref, "video")
    run(usina, "package", ref)
    pk = next((usina / "out/packages/gersinho").iterdir())
    assert "AI info" in (pk / "CHECKLIST.md").read_text()


def test_pause_blocks_video_request(usina):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    run(usina, "pause", "teste")
    r = run(usina, "video-request", ref, ok=False)
    assert r.returncode == 1 and "pausado" in r.stderr


# ---------- caminhos portáveis ----------

def test_queue_paths_are_relative_and_legacy_absolute_resolves(usina):
    ref = to_frames_approved(usina)
    it = item_json(usina)
    assert not it["storyboard"]["path"].startswith("/")
    assert all(not f["path"].startswith("/") for f in it["frames"].values())
    import sys
    sys.path.insert(0, str(usina))
    try:
        from pipeline import store
        legacy = "/outra/maquina/usina/" + it["storyboard"]["path"]
        assert store.local(legacy) == store.ROOT / it["storyboard"]["path"]
    finally:
        sys.path.pop(0)
        for m in [m for m in sys.modules if m == "pipeline" or m.startswith("pipeline.")]:
            del sys.modules[m]


def test_frames_refuse_when_storyboard_file_missing(usina):
    ref = run(usina, "new", "gersinho", "Busao", "--idea", "porta").stdout.strip()
    run(usina, "save-script", ref, EXAMPLE)
    run(usina, "image", ref, "storyboard")
    run(usina, "review", ref, "storyboard", "pass")
    run(usina, "approve", ref, "storyboard")
    (usina / item_json(usina)["storyboard"]["path"]).unlink()   # clone novo: out/ não vem no git
    r = run(usina, "image", ref, "frames", ok=False)
    assert r.returncode == 1 and "storyboard" in r.stderr
    run(usina, "image", ref, "frames", "--sem-storyboard")
    assert "image 3" not in item_json(usina)["frames"]["start"]["prompt"]


# ---------- fallback Higgsfield ----------

def test_higgsfield_fallback_respects_switch_and_two_steps(usina):
    ref = run(usina, "new", "gersinho", "Busao", "--idea", "porta").stdout.strip()
    run(usina, "save-script", ref, EXAMPLE)
    run(usina, "image", ref, "storyboard")
    run(usina, "review", ref, "storyboard", "pass")
    run(usina, "approve", ref, "storyboard")
    assert run(usina, "image", ref, "frames", "--provider", "higgsfield", ok=False).returncode == 1
    b = usina / "budget.yaml"
    b.write_text(b.read_text().replace("image_fallback_allowed: false", "image_fallback_allowed: true"))
    first = json.loads(run(usina, "image", ref, "frames", "--provider", "higgsfield").stdout)
    assert len(first["requests"]) == 1 and "<job_id" not in json.dumps(first["requests"])
    run(usina, "record-image", ref, "frames", "start", "--hf-job", "A1")
    second = json.loads(run(usina, "image", ref, "frames", "--provider", "higgsfield").stdout)
    assert second["requests"][0]["params"]["medias"][0]["value"] == "A1"   # image 1 = frame A
    run(usina, "record-image", ref, "frames", "end", "--hf-job", "B1")
    run(usina, "record-image", ref, "frames", "end", "--hf-job", "B1")
    it = item_json(usina)
    assert it["attempts"]["frames"] == 1 and set(it["frames"]) == {"start", "end"}
    assert len([r for r in ledger(usina) if r["action"] == "image_frames"]) == 2


# ---------- painel ----------

def test_panel_apply_is_robust_idempotent_and_skips_stale(usina, tmp_path):
    ref = run(usina, "new", "gersinho", "Busao", "--idea", "porta").stdout.strip()
    run(usina, "save-script", ref, EXAMPLE)
    run(usina, "image", ref, "storyboard")
    run(usina, "review", ref, "storyboard", "pass")
    dec = {"documents": [
        {"doc_id": "d1", "version": 1, "data": {"ref": ref, "stage": "storyboard", "verdict": "reject",
                                                 "notes": "topete achatado", "at": int(time.time() * 1000) + 1000}},
        {"doc_id": "d2", "data": {"stage": "video", "verdict": "approve"}},   # sem ref
        "lixo", 3]}
    f = tmp_path / "d.json"
    f.write_text(json.dumps(dec))
    out = json.loads(run(usina, "panel-apply", str(f)).stdout.strip().splitlines()[-1])
    assert out["applied_ids"] == ["d1", "d2"] and out["invalid_ids"] == ["d2"]
    run(usina, "panel-apply", str(f))   # 2ª vez: nada muda, nada duplicado no livro de falhas
    assert (usina / "playbook/falhas.md").read_text().count("topete achatado") == 1
    # a etapa é refeita; a mesma decisão (velha) com outro id não pode reprovar a versão nova
    run(usina, "retry", ref, "storyboard")
    run(usina, "image", ref, "storyboard")
    run(usina, "review", ref, "storyboard", "pass")
    dec["documents"][0]["doc_id"] = "d1-copia"
    dec["documents"][0]["data"]["at"] = 1000
    f.write_text(json.dumps(dec))
    out = json.loads(run(usina, "panel-apply", str(f)).stdout.strip().splitlines()[-1])
    assert out["obsolete_ids"] == ["d1-copia"]
    assert item_json(usina)["gates"]["storyboard"]["caio"] == "pending"
    bad = tmp_path / "bad.json"
    bad.write_text("{nao é json")
    assert run(usina, "panel-apply", str(bad), ok=False).returncode == 1


def test_panel_export_keeps_discarded_and_clears_stale_assets(usina):
    ref = run(usina, "new", "gersinho", "Busao", "--idea", "porta").stdout.strip()
    run(usina, "save-script", ref, EXAMPLE)
    run(usina, "image", ref, "storyboard")
    run(usina, "panel-asset", ref, "storyboard", "https://claude.ai/asset/v1")
    run(usina, "review", ref, "storyboard", "fail", "--notes", "G3")
    run(usina, "retry", ref, "storyboard")
    run(usina, "image", ref, "storyboard")
    assert "storyboard" not in item_json(usina)["post"].get("assets", {})   # Caixa não mostra a v1 como se fosse a v2
    run(usina, "discard", ref, "--why", "teste")
    run(usina, "panel-export")
    batch = json.loads((usina / "out/panel/batch.json").read_text())
    fila = [w for w in batch if w["collection"] == "fila"]
    assert fila and fila[0]["data"]["state"] == "descartado"
    assert (usina / "out/panel/batch-01.json").exists()


# ---------- mídia ----------

def test_normalize_without_audio_and_c2pa_safe_copy(usina, tmp_path):
    import sys
    sys.path.insert(0, str(HERE))
    from pipeline import media
    src = mp4(tmp_path / "a.mp4", size="720x1000", codec="mpeg4")   # fora do padrão e sem áudio
    out = media.normalize_reels(src, tmp_path / "out.mp4")
    info = media.probe(out)
    assert (info["width"], info["height"], info["vcodec"]) == (1080, 1920, "h264") and info["acodec"] == "aac"
    ok = mp4(tmp_path / "ok.mp4", size="720x1280")                    # já compatível: cópia byte a byte
    dst = media.normalize_reels(ok, tmp_path / "ok-out.mp4")
    assert dst.read_bytes() == ok.read_bytes()
    with_audio = mp4(tmp_path / "au.mp4", size="720x1000", codec="mpeg4", audio=True)
    assert media.probe(media.normalize_reels(with_audio, tmp_path / "au-out.mp4"))["acodec"] == "aac"


# ---------- prompts e lint ----------

def _prompts():
    import sys
    sys.path.insert(0, str(HERE))
    from pipeline import prompts
    from pipeline.store import get_page
    return prompts, get_page("gersinho"), json.loads((HERE / EXAMPLE).read_text())


def test_video_prompt_has_no_speed_words_and_repair_skeleton():
    import re
    prompts, page, s = _prompts()
    v = prompts.video_prompt(s, page, has_start=True, has_end=True, has_storyboard=True, repair="in Stage 2 his chest stays square")
    cleaned = v.replace("no slow motion", "").replace("slow deliberate blink", "").replace("slow blink", "")
    assert not re.search(r"\b(slow|slowly|smooth|smoothly|graceful)\b", cleaned, re.I)
    assert v.startswith("REPAIR SCOPE\nKeep the framing") and "Change only: in Stage 2" in v and "Protect:" in v
    assert v.index("CAMERA") < v.index("LOCATION MAP") and v.index("ACTIVE REFERENCES") < v.index("CAMERA")


def test_camera_modes_accepted_by_lint_have_prompts():
    from copy import deepcopy
    prompts, page, s = _prompts()
    import sys
    sys.path.insert(0, str(HERE))
    from pipeline import lint
    for mode in lint.CAMERA_MODES:
        assert mode in prompts.CAMERA, mode
    s2 = deepcopy(s)
    s2["camera"]["mode"] = "tracking_side"
    assert "moving sideways" in prompts.video_prompt(s2, page, has_start=True, has_end=True, has_storyboard=False)


def test_prompts_with_zero_extras_and_script_lighting():
    from copy import deepcopy
    prompts, page, s = _prompts()
    s2 = deepcopy(s)
    s2["en"]["extras_count"] = 0
    s2["en"]["lighting"] = "Cold fluorescent ceiling light inside a steel elevator, 4000K."
    for txt in (prompts.video_prompt(s2, page, has_start=True, has_end=False, has_storyboard=False),
                prompts.frame_a_prompt(s2, page, False), prompts.frame_b_prompt(s2, page),
                prompts.storyboard_prompt(s2, page)[0], prompts.motion_scene_prompt(s2, page)):
        assert "0 passersby" not in txt
    sb = prompts.storyboard_prompt(s2, page)[0]
    assert "natural daylight" not in sb and "fluorescent" in sb
    v = prompts.video_prompt(s2, page, has_start=True, has_end=False, has_storyboard=False)
    assert "matches the end frame" not in v   # sem end_image não se cita frame final
    assert "\n\n\n" not in prompts.frame_b_prompt(s2, page)


def test_lint_malformed_script_is_error_not_traceback(usina, tmp_path):
    s = json.loads((usina / EXAMPLE).read_text())
    s["character_actions_count"] = "duas"
    s["beats"] = ["texto solto"]
    f = tmp_path / "m.json"
    f.write_text(json.dumps(s))
    r = run(usina, "lint", str(f), ok=False)
    assert r.returncode == 1 and "malformado" in r.stdout and "Traceback" not in r.stderr


# ---------- painel (index.html) ----------

def test_panel_js_parses_and_reads_exported_collections(tmp_path):
    import re
    import shutil as sh
    html = (HERE / "index.html").read_text(encoding="utf-8")
    js = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    for col in ("fila", "paginas", "decisoes", "placar"):
        assert f'"{col}"' in js, col
    assert 'doc("saude/atual")' in js
    if not sh.which("node"):
        pytest.skip("node ausente")
    f = tmp_path / "panel.js"
    f.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
