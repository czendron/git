"""Teste ponta a ponta do pipeline em modo mock (sem rede, sem gastar)."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent


@pytest.fixture()
def usina(tmp_path):
    root = tmp_path / "usina"
    for d in ("pipeline", "pages", "prompts", "playbook"):
        if (HERE / d).exists():
            shutil.copytree(HERE / d, root / d, ignore=shutil.ignore_patterns("*.png", "__pycache__"))
    shutil.copy(HERE / "budget.yaml", root / "budget.yaml")
    bt = (root / "budget.yaml").read_text().replace("video_enabled: false", "video_enabled: true")
    (root / "budget.yaml").write_text(bt)
    (root / "data" / "queue").mkdir(parents=True)
    from PIL import Image
    refs = root / "pages" / "gersinho" / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), (90, 60, 40)).save(refs / "rosto.png")
    Image.new("RGB", (96, 64), (60, 60, 60)).save(refs / "silhueta.png")
    return root


def run(root, *args, ok=True):
    env = {**os.environ, "USINA_MOCK": "1"}
    r = subprocess.run([sys.executable, "-m", "pipeline", *args], cwd=root, capture_output=True, text=True, env=env)
    if ok:
        assert r.returncode == 0, r.stdout + r.stderr
    return r


def test_lint_example_ok(usina):
    run(usina, "lint", "prompts/examples/gersinho-busao.json")


def test_lint_rejects_bad_script(usina, tmp_path):
    s = json.loads((usina / "prompts/examples/gersinho-busao.json").read_text())
    s["character_actions_count"] = 4
    s["en"]["stages"][1]["text"] = "he dances slowly"
    s["caption"] = "camisa de time"
    f = tmp_path / "bad.json"
    f.write_text(json.dumps(s))
    r = run(usina, "lint", str(f), ok=False)
    assert r.returncode == 1
    assert "ações" in r.stdout and "slow" in r.stdout and "brand safety" in r.stdout


def test_full_flow_mock(usina, tmp_path):
    ref = run(usina, "new", "gersinho", "Busao", "--idea", "porta").stdout.strip()
    run(usina, "save-script", ref, "prompts/examples/gersinho-busao.json")
    plan = json.loads(run(usina, "plan").stdout)
    assert any(a.get("cmd", "").endswith("storyboard") for a in plan["actions"])
    run(usina, "image", ref, "storyboard")
    plan = json.loads(run(usina, "plan").stdout)
    assert any(a["do"] == "review_image" for a in plan["actions"])
    run(usina, "review", ref, "storyboard", "pass")
    plan = json.loads(run(usina, "plan").stdout)
    assert any(a["do"] == "await_caio" for a in plan["waiting_caio"])  # calibração: Caio aprova
    run(usina, "approve", ref, "storyboard")
    run(usina, "image", ref, "frames")
    item = json.loads(next((usina / "data/queue/gersinho").glob("*.json")).read_text())
    assert set(item["frames"]) == {"start", "end"}
    end_prompt = item["frames"]["end"]["prompt"]
    assert end_prompt.startswith("Edit image 1")          # frame B = edição do frame A
    run(usina, "review", ref, "frames", "pass")
    run(usina, "approve", ref, "frames")
    vr = json.loads(run(usina, "video-request", ref).stdout)
    assert vr["ready"] is False and {u["key"] for u in vr["upload_first"]} == {"start", "end", "storyboard"}
    for k, i in (("start", 1), ("end", 2), ("storyboard", 3)):
        run(usina, "record-upload", ref, k, "--hf-id", f"00000000-0000-0000-0000-00000000000{i}")
    vr = json.loads(run(usina, "video-request", ref).stdout)
    p = vr["requests"][0]["params"]
    assert p["generate_audio"] is False and p["model"] == "seedance_2_5"
    roles = [m["role"] for m in p["medias"]]
    assert roles[:2] == ["start_image", "end_image"] and roles.count("image_references") == 3
    assert "slow motion" in p["prompt"] and "@Image 3" in p["prompt"]
    vr = json.loads(run(usina, "video-request", ref, "--no-grid").stdout)
    assert "@Image 3" not in vr["requests"][0]["params"]["prompt"]
    run(usina, "record-video", ref, "--job", "22222222-2222-2222-2222-222222222222", "--credits", "65")
    run(usina, "record-video", ref, "--url", "https://example.invalid/v.mp4")
    mp4 = tmp_path / "t.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=360x640:rate=30:duration=10",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(mp4)], check=True)
    out = run(usina, "fetch-video", ref, "--file", str(mp4)).stdout
    assert "cortes detectados" in out
    run(usina, "review", ref, "video", "pass")
    run(usina, "approve", ref, "video")
    run(usina, "package", ref)
    pk = next((usina / "out/packages/gersinho").iterdir())
    assert (pk / "CHECKLIST.md").exists() and (pk / "legenda.txt").exists() and (pk / "capa.jpg").exists()
    status = run(usina, "status").stdout
    assert "pronto" in status


def test_pause_blocks_plan(usina):
    run(usina, "pause", "teste")
    plan = json.loads(run(usina, "plan").stdout)
    assert plan["paused"] and plan["actions"] == []
    run(usina, "resume")


def test_budget_blocks_video(usina):
    ref = run(usina, "new", "gersinho", "X", "--idea", "y").stdout.strip()
    # gasto do dia já no teto do Higgsfield
    led = usina / "data" / "ledger.jsonl"
    import time
    led.write_text(json.dumps({"at": time.time(), "page": "gersinho", "item": "z", "provider": "higgsfield",
                               "action": "video_submit", "usd": 12.0, "credits": 240, "job_id": "", "ok": True,
                               "note": ""}) + "\n")
    run(usina, "save-script", ref, "prompts/examples/gersinho-busao.json")
    for st in ("storyboard", "frames"):
        run(usina, "image", ref, st)
        run(usina, "review", ref, st, "pass")
        run(usina, "approve", ref, st)
    plan = json.loads(run(usina, "plan").stdout)
    assert any(a["do"] == "blocked" for a in plan["actions"])


def test_video_switch_off_by_default():
    import yaml
    b = yaml.safe_load((HERE / "budget.yaml").read_text())
    assert b["switches"]["video_enabled"] is False


def test_three_strikes_discard(usina):
    ref = run(usina, "new", "gersinho", "Y", "--idea", "y").stdout.strip()
    run(usina, "save-script", ref, "prompts/examples/gersinho-busao.json")
    for _ in range(3):
        run(usina, "image", ref, "storyboard")
        run(usina, "review", ref, "storyboard", "fail", "--notes", "G3 topete achatado")
        run(usina, "retry", ref, "storyboard")
    plan = json.loads(run(usina, "plan").stdout)
    assert any(a["do"] == "discard" for a in plan["actions"])
    assert (usina / "playbook" / "falhas.md").exists()


def test_media_archive_roundtrip(usina, tmp_path):
    ref = run(usina, "new", "gersinho", "M", "--idea", "m").stdout.strip()
    run(usina, "save-script", ref, "prompts/examples/gersinho-busao.json")
    run(usina, "image", ref, "storyboard")
    st = json.loads(run(usina, "media-status").stdout)
    assert [u["key"] for u in st["upload"]] == ["storyboard"]
    run(usina, "panel-asset", ref, "storyboard", "/_blob/" + "a" * 32)
    st = json.loads(run(usina, "media-status").stdout)
    assert st["upload"] == [] and st["restore"] == []
    sb = Path(st["how_upload"] and next((usina / "out").rglob("storyboard-v1.png")))
    backup = tmp_path / "bk.png"
    shutil.copy(sb, backup)
    sb.unlink()  # sessão nova: out/ sumiu
    st = json.loads(run(usina, "media-status").stdout)
    assert st["restore"] and st["restore"][0]["asset_id"] == "a" * 32
    run(usina, "media-restore", ref, "storyboard", "--file", str(backup))
    assert sb.exists()
