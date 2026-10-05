"""Regressões da rodada 2 de QA (docs/qa/rodada-2.md): arquivo de mídia, trilha de trend, paradas automáticas,
estorno e placar. Cada teste trava um bug corrigido ou uma regra da ata que passou a valer no código."""
import json
import subprocess
import time
from pathlib import Path

import pytest

from test_pipeline import HERE, run, usina  # noqa: F401  (fixture reaproveitada)
from test_qa_rodada1 import EXAMPLE, item_json, ledger, plan, to_frames_approved

TREND = "prompts/examples/gersinho-trend-calcadao.json"


def clip(path: Path, dur=8, size="360x640", cut=False):
    if cut:  # dois planos colados: corte seco no meio
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=30:duration={dur / 2}",
               "-f", "lavfi", "-i", f"color=red:size={size}:rate=30:duration={dur / 2}",
               "-filter_complex", "[0][1]concat=n=2"]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=30:duration={dur}"]
    subprocess.run(cmd + ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def trend_item(root, tmp_path, with_source=True):
    ref = run(root, "new", "gersinho", "Trend", "--idea", "gang gang").stdout.strip()
    run(root, "save-script", ref, TREND)
    if with_source:
        run(root, "motion-source", ref, "--file", str(clip(tmp_path / "src.mp4")))
    return ref


def set_item(root, **kw):
    f = next((root / "data/queue/gersinho").glob("*.json"))
    d = json.loads(f.read_text())
    d.update(kw)
    f.write_text(json.dumps(d))


def health(root, **kw):
    f = root / "data" / "health.json"
    h = json.loads(f.read_text()) if f.exists() else {}
    h.update(kw)
    f.write_text(json.dumps(h))


# ---------- trilha de trend ----------

def test_motion_source_refuses_cuts_and_bad_duration(usina, tmp_path):
    ref = trend_item(usina, tmp_path, with_source=False)
    r = run(usina, "motion-source", ref, "--file", str(clip(tmp_path / "c.mp4", cut=True)), ok=False)
    assert r.returncode == 1 and "cortes" in r.stderr
    r = run(usina, "motion-source", ref, "--file", str(clip(tmp_path / "l.mp4", dur=20)), ok=False)
    assert r.returncode == 1 and "3-15" in r.stderr
    assert not item_json(usina)["motion"]
    run(usina, "motion-source", ref, "--file", str(tmp_path / "c.mp4"), "--force")   # intencional: aceita com aviso
    assert item_json(usina)["motion"]["cuts"]


def test_new_source_invalidates_frames_and_old_upload(usina, tmp_path):
    ref = trend_item(usina, tmp_path)
    run(usina, "motion-source", ref, "--hf-id", "SRC1")
    run(usina, "image", ref, "frames")
    run(usina, "review", ref, "frames", "pass")
    assert run(usina, "motion-source", ref, "--file", str(tmp_path / "src.mp4"), ok=False).returncode == 1
    run(usina, "motion-source", ref, "--file", str(tmp_path / "src.mp4"), "--force")
    it = item_json(usina)
    assert it["state"] == "roteiro" and it["frames"] == {} and "frames" not in it["gates"]
    assert "source_hf_id" not in it["motion"]            # o id antigo apontaria para a fonte velha
    assert it["motion"]["source_path"].endswith("source-v2.mp4")   # versão nova, arquivo novo (arquivo de mídia)
    assert it["motion"]["history"][0]["source_hf_id"] == "SRC1"


def test_hf_id_without_source_file_is_refused(usina, tmp_path):
    ref = trend_item(usina, tmp_path, with_source=False)
    assert run(usina, "motion-source", ref, "--hf-id", "X", ok=False).returncode == 1


def test_trend_without_source_waits_then_discards_after_7_days(usina, tmp_path):
    ref = trend_item(usina, tmp_path, with_source=False)
    assert any(w["stage"] == "fonte" for w in plan(usina)["waiting_caio"])
    set_item(usina, created_at=time.time() - 8 * 86400)
    assert any(a["do"] == "discard" and a["item"] == ref for a in plan(usina)["actions"])


def test_trend_lint_malformed_and_zero_extras_prompt(usina, tmp_path):
    s = json.loads((usina / TREND).read_text())
    s["duration_s"] = "dez"
    f = tmp_path / "t.json"
    f.write_text(json.dumps(s))
    r = run(usina, "lint", str(f), ok=False)
    assert r.returncode == 1 and "malformado" in r.stdout and "Traceback" not in r.stderr
    import sys
    sys.path.insert(0, str(HERE))
    from pipeline import prompts
    from pipeline.store import get_page
    s = json.loads((HERE / TREND).read_text())
    s["en"]["extras_count"] = 0
    p = prompts.motion_frame_prompt(s, get_page("gersinho"))
    assert "exactly 0" not in p and "only person" in p


def test_trend_higgsfield_fallback_uses_source_first_frame_as_image_1(usina, tmp_path):
    bt = (usina / "budget.yaml").read_text().replace("image_fallback_allowed: false", "image_fallback_allowed: true")
    (usina / "budget.yaml").write_text(bt)
    ref = trend_item(usina, tmp_path)
    out = json.loads(run(usina, "image", ref, "frames", "--provider", "higgsfield").stdout)
    assert out["ready"] is False and out["upload_first"][0]["key"] == "source_first"
    run(usina, "record-upload", ref, "source_first", "--hf-id", "FIRST")
    out = json.loads(run(usina, "image", ref, "frames", "--provider", "higgsfield").stdout)
    assert out["requests"][0]["params"]["medias"][0]["value"] == "FIRST"
    run(usina, "record-image", ref, "frames", "start", "--hf-job", "HJ1")   # trend sai de roteiro, sem storyboard
    it = item_json(usina)
    assert it["state"] == "frames" and it["frames"]["start"]["higgsfield_id"] == "HJ1"
    assert not any(a["do"] == "run" and "higgsfield" in a.get("cmd", "") for a in plan(usina)["actions"])


def test_trend_blocked_above_80_pct_and_model_recorded(usina, tmp_path):
    ref = trend_item(usina, tmp_path)
    run(usina, "image", ref, "frames")
    run(usina, "review", ref, "frames", "pass")
    run(usina, "approve", ref, "frames")
    run(usina, "record-upload", ref, "start", "--hf-id", "A")
    run(usina, "motion-source", ref, "--hf-id", "S")
    (usina / "data/ledger.jsonl").write_text(json.dumps({"at": time.time(), "page": "x", "item": "y", "provider": "openai",
                                                        "action": "old", "usd": 245.0, "credits": 0}) + "\n")
    acts = plan(usina)["actions"]
    assert any(a["do"] == "blocked" and "Genjutsu" in a["why"] for a in acts)
    r = run(usina, "video-request", ref, ok=False)
    assert r.returncode == 1 and "Genjutsu" in r.stderr
    (usina / "data/ledger.jsonl").write_text("")
    run(usina, "video-request", ref)
    run(usina, "record-video", ref, "--job", "T1")
    it = item_json(usina)
    assert it["video"]["model"] == "hf_mult_motion_control"
    assert ledger(usina)[-1]["credits"] == 8 * 8.0   # 8 s de fonte x 8 créditos/s


def test_record_upload_rejects_phantom_keys(usina):
    ref = to_frames_approved(usina)
    run(usina, "record-upload", ref, "start", "--hf-id", "A")
    for key in ("source", "foo"):
        assert run(usina, "record-upload", ref, key, "--hf-id", "B", ok=False).returncode == 1
    run(usina, "image", ref, "frames", "--force")
    assert "higgsfield_id" not in item_json(usina)["frames"]["start"]


# ---------- arquivo de mídia ----------

def test_media_status_reports_lost_and_restore_refuses_old_version(usina, tmp_path):
    ref = run(usina, "new", "gersinho", "M", "--idea", "m").stdout.strip()
    run(usina, "save-script", ref, EXAMPLE)
    run(usina, "image", ref, "storyboard")
    v1 = next((usina / "out").rglob("storyboard-v1.png"))
    run(usina, "panel-asset", ref, "storyboard", "https://claude.ai/x/_blob/" + "b" * 32,
        "--path", str(v1.relative_to(usina)))
    bk = tmp_path / "v1.png"
    bk.write_bytes(v1.read_bytes())
    run(usina, "review", ref, "storyboard", "fail", "--notes", "G1")
    run(usina, "retry", ref, "storyboard")
    run(usina, "image", ref, "storyboard")
    # a sessão morreu antes de subir a v2: sumiu, e o arquivo guardado é a v1
    for f in (usina / "out").rglob("storyboard-v*.png"):
        f.unlink()
    st = json.loads(run(usina, "media-status").stdout)
    assert st["restore"] == [] and st["lost"][0]["archived_version"].endswith("storyboard-v1.png")
    r = run(usina, "media-restore", ref, "storyboard", "--file", str(bk), ok=False)
    assert r.returncode == 1 and "versão" in r.stderr
    run(usina, "media-restore", ref, "storyboard", "--file", str(bk), "--force")


def test_media_restore_checks_file_type_and_panel_asset_checks_version(usina, tmp_path):
    ref = run(usina, "new", "gersinho", "M", "--idea", "m").stdout.strip()
    run(usina, "save-script", ref, EXAMPLE)
    run(usina, "image", ref, "storyboard")
    r = run(usina, "panel-asset", ref, "storyboard", "/_blob/" + "c" * 32, "--path", "out/x/velho.png", ok=False)
    assert r.returncode == 1 and "media-status" in r.stderr
    run(usina, "panel-asset", ref, "storyboard", "https://claude.ai/a", "--asset-id", "D" * 32)
    assert item_json(usina)["post"]["media"]["storyboard"]["asset"] == "d" * 32
    bad = tmp_path / "erro.html"
    bad.write_text("<html>403</html>")
    r = run(usina, "media-restore", ref, "storyboard", "--file", str(bad), ok=False)
    assert r.returncode == 1 and "não parece" in r.stderr


def test_trend_source_is_archived(usina, tmp_path):
    ref = trend_item(usina, tmp_path)
    keys = {u["key"] for u in json.loads(run(usina, "media-status").stdout)["upload"]}
    assert {"source", "source_first"} <= keys


# ---------- custos, retries e estorno ----------

def test_failed_is_idempotent_and_refund_frees_idea_cap(usina):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    for job in ("J1", "J2"):
        run(usina, "record-video", ref, "--job", job, "--credits", "65")
        run(usina, "record-video", ref, "--failed", "nsfw", "--refunded")
        run(usina, "record-video", ref, "--failed", "nsfw", "--refunded")   # sessão re-executada
    it = item_json(usina)
    assert it["attempts"]["video"] == 2 and len(it["video"]["history"]) == 2
    assert len([r for r in ledger(usina) if r["action"] == "video_refund"]) == 2
    run(usina, "record-video", ref, "--refunded", "--job", "J1")              # estorno de novo: não duplica
    assert len([r for r in ledger(usina) if r["action"] == "video_refund"]) == 2
    # 2 x 65 estornados: o teto de 160 por ideia continua livre (sem estorno, 130 + 65 descartaria)
    assert any(a["do"] == "video_submit" for a in plan(usina)["actions"])
    assert run(usina, "record-video", ref, "--refunded", "--job", "NAO", ok=False).returncode == 1


def test_video_request_enforces_idea_caps(usina):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    for job in ("J1", "J2"):
        run(usina, "record-video", ref, "--job", job, "--credits", "65")
        run(usina, "record-video", ref, "--failed")
    r = run(usina, "video-request", ref, ok=False)
    assert r.returncode == 1 and "160" in r.stderr


# ---------- paradas automáticas (ata D5) ----------

def test_three_consecutive_errors_pause_and_success_resets(usina):
    ref = to_frames_approved(usina)
    run(usina, "record-error", "rede caiu")
    run(usina, "record-error", "rede caiu")
    run(usina, "approve", ref, "frames")          # deu certo: zera a sequência
    run(usina, "record-error", "a")
    run(usina, "record-error", "b")
    assert not (usina / "PAUSE").exists()
    out = run(usina, "record-error", "c").stdout
    assert "PAUSADO" in out and (usina / "PAUSE").exists()
    assert plan(usina)["actions"] == []
    run(usina, "resume")
    run(usina, "record-error", "d")
    assert not (usina / "PAUSE").exists()          # resume zerou a contagem


def test_balance_unknown_low_and_ok(usina):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    (usina / "data/health.json").unlink()
    p = plan(usina)
    assert p["actions"][0]["do"] == "check_balance" and not any(a["do"] == "video_submit" for a in p["actions"])
    assert "saldo" in run(usina, "video-request", ref, ok=False).stderr
    run(usina, "balance", "320")                    # 320 - 65 < 300
    p = plan(usina)
    assert any(a["do"] == "blocked" and "mínimo" in a["why"] for a in p["actions"])
    health(usina, balance={"credits": 5000, "at": time.time() - 2 * 86400})   # leitura velha
    assert plan(usina)["actions"][0]["do"] == "check_balance"
    run(usina, "balance", "5000")
    assert any(a["do"] == "video_submit" for a in plan(usina)["actions"])


def test_unposted_cap_stops_spending_but_keeps_polling(usina):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    run(usina, "record-video", ref, "--job", "J1", "--credits", "65")
    qdir = usina / "data/queue/gersinho"
    for i in range(6):
        (qdir / f"pronto-{i}.json").write_text(json.dumps({"page": "gersinho", "id": f"pronto-{i}", "state": "pronto"}))
    p = plan(usina)
    dos = [a["do"] for a in p["actions"]]
    assert "video_poll" in dos and "new_ideas" not in dos   # vídeo já pago continua sendo buscado
    assert any("prontos sem postar" in n for n in p["notes"])


def test_panel_kill_switch_applies_in_order(usina, tmp_path):
    f = tmp_path / "d.json"
    f.write_text(json.dumps([
        {"id": "k2", "data": {"ref": "usina/kill-switch", "stage": "usina", "verdict": "resume", "at": 2000}},
        {"id": "k1", "data": {"ref": "usina/kill-switch", "stage": "usina", "verdict": "pause", "at": 1000}}]))
    out = run(usina, "panel-apply", str(f)).stdout
    assert not (usina / "PAUSE").exists() and '"k1", "k2"' in out
    f.write_text(json.dumps([{"id": "k3", "data": {"stage": "usina", "verdict": "pause", "notes": "viagem", "at": 3}}]))
    run(usina, "panel-apply", str(f))
    assert "viagem" in (usina / "PAUSE").read_text()


# ---------- placar e gatilho de cadência (ata D5) ----------

def test_placar_trigger_suggests_but_never_changes_cadence(usina, tmp_path):
    qdir = usina / "data/queue/gersinho"
    qdir.mkdir(parents=True, exist_ok=True)
    week = time.time() - 8 * 86400
    (qdir / "p0.json").write_text(json.dumps({"page": "gersinho", "id": "p0", "state": "postado",
                                              "post": {"posted_at": week}}))
    for i in range(4):
        (qdir / f"s{i}.json").write_text(json.dumps({"page": "gersinho", "id": f"s{i}", "state": "pronto",
                                                     "gates": {"video": {"qa": "pass", "caio": "approved"}}}))
    f = tmp_path / "placar.json"
    f.write_text(json.dumps({"documents": [
        {"id": "a", "data": {"ref": "gersinho/p0", "page": "gersinho", "views": 900, "views7": 4000, "createdAt": 1}},
        {"id": "b", "data": {"ref": "gersinho/p1", "views": 3000, "createdAt": 1}}, "lixo", {"data": {"ref": None}}]}))
    assert json.loads(run(usina, "placar-import", str(f)).stdout)["imported"] == 2
    c = json.loads(run(usina, "cadence-check").stdout)[0]
    assert c["criteria"]["stock_ok"] and c["criteria"]["d7_ok"] and not c["trigger"]   # mediana 3500 < 5k
    f.write_text(json.dumps([{"ref": "gersinho/p1", "views": 3000, "views7": 60000, "updatedAt": 5}]))
    run(usina, "placar-import", str(f))
    c = json.loads(run(usina, "cadence-check").stdout)[0]
    assert c["trigger"] and "2 posts/dia" in c["suggestion"]
    assert any("2 posts/dia" in n for n in plan(usina)["notes"])
    assert "posts_per_day: 1" in (usina / "pages/gersinho/page.yaml").read_text()   # só sugere
    f.write_text(json.dumps([{"ref": "gersinho/p1", "views": 10, "createdAt": 1}]))   # export velho
    run(usina, "placar-import", str(f))
    assert json.loads((usina / "data/placar.json").read_text())["gersinho/p1"]["views7"] == 60000


def test_panel_has_kill_switch_views7_and_health_cards():
    html = (HERE / "index.html").read_text(encoding="utf-8")
    for s in ('id="b-pause"', 'id="pl-views7"', "views7", "Paradas automáticas", 'stage:"usina"'):
        assert s in html, s


# ---------- coerência ata x CLI x painel ----------

def test_panel_veto_discards_idea_before_spending(usina, tmp_path):
    ref = run(usina, "new", "gersinho", "Veto", "--idea", "x").stdout.strip()
    f = tmp_path / "d.json"
    f.write_text(json.dumps([{"id": "v1", "data": {"ref": ref, "stage": "ideia", "verdict": "reject", "at": 1}}]))
    out = run(usina, "panel-apply", str(f)).stdout
    assert item_json(usina)["state"] == "descartado" and '"v1"' in out


def test_calibration_window_starts_at_first_post_without_launched_at(usina):
    import sys
    sys.path.insert(0, str(usina))
    qdir = usina / "data/queue/gersinho"
    qdir.mkdir(parents=True, exist_ok=True)
    (qdir / "p0.json").write_text(json.dumps({"page": "gersinho", "id": "p0", "state": "postado",
                                              "post": {"posted_at": time.time() - 15 * 86400}}))
    r = subprocess.run([sys.executable, "-c", "from pipeline.tick import needs_caio; from pipeline.store import get_page;"
                        "p=get_page('gersinho'); print(needs_caio(p,'frames'), needs_caio(p,'video'))"],
                       cwd=usina, capture_output=True, text=True)
    assert r.stdout.split() == ["False", "True"], r.stderr   # vídeo final: sempre o Caio (D3)


def test_panel_smoke_in_chromium(usina, tmp_path):
    """Painel de verdade no Chromium (Playwright), com o banco falso lendo o export da CLI. Pula sem Playwright."""
    import glob
    import os
    import shutil as sh
    node_path = os.environ.get("NODE_PATH") or "/opt/node-tools/node_modules"
    chrome = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    if not sh.which("node") or not Path(node_path, "playwright").exists() or not chrome:
        pytest.skip("Playwright/Chromium ausente")
    run(usina, "new", "gersinho", "Postado", "--idea", "y")
    f = next((usina / "data/queue/gersinho").glob("*.json"))
    f.write_text(json.dumps({**json.loads(f.read_text()), "state": "postado"}))
    run(usina, "new", "gersinho", "Ideia do painel", "--idea", "x")
    run(usina, "record-error", "teste")
    run(usina, "panel-export")
    r = subprocess.run(["node", str(HERE / "tests/panel_smoke.js"), str(usina / "out/panel/batch.json"),
                        str(HERE / "index.html"), chrome[-1]], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "NODE_PATH": node_path})
    out = r.stdout
    assert r.returncode == 0 and "PAGEERROR" not in out, out + r.stderr
    assert "Erros seguidos: 1 de 3" in out and "Saldo Higgsfield: ~5000" in out
    assert "PREFILL views7= 7000" in out and "Pedido de pausa salvo" in out
    assert '"stage":"usina","verdict":"pause"' in out and '"stage":"ideia","verdict":"reject"' in out
