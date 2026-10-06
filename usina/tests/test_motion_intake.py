"""Aba Motion control do painel → motion-intake → motion-source → roteiro de trend (docs/qa/motion-tab.md).

Nenhum teste fala com o Higgsfield nem com a OpenAI: o pipeline roda em USINA_MOCK=1."""
import json
import subprocess
import sys
from pathlib import Path

from test_pipeline import HERE, run, usina  # noqa: F401  (fixture reaproveitada)
from test_qa_rodada2 import TREND, clip

ASSET = "a" * 32


def doc(**kw):
    d = {"page": "gersinho", "title": "Gang gang no calçadão", "label": "gang gang", "sourceAssetId": ASSET,
         "sourceUrl": "/_blob/" + ASSET, "firstFrameAssetId": "f" * 32, "startS": 2, "endS": 10,
         "crop": {"x": 0.5}, "cuts": [], "flags": {"multiple_people": False}, "status": "novo",
         "replace_subject": "the dancer in the white tank top, center",
         "people": [{"id": "p1", "descriptor": "the dancer in the white tank top, center"}],
         "scene_prompt": "A São Paulo sidewalk at overcast midday. Static phone camera at chest height. Two passersby "
                         "walk past frame-left to frame-right, one checks a phone.",
         "frame_prompt": "Edit image 1. Replace the dancer in the white tank top, center with the man from image 2 and "
                         "image 3. Keep the exact pose and framing.",
         "consent": "fonte gravada pelo Caio, autorizada", "source_expression": "the source dancer is deadpan",
         "sourceDeadpan": True, "createdAt": 1}
    d.update(kw)
    return d


def write(tmp_path, rows, name="motion.json"):
    f = tmp_path / name
    f.write_text(json.dumps(rows))
    return f


def intake(root, f):
    r = run(root, "motion-intake", str(f))
    return json.loads(r.stdout.strip().splitlines()[-1])


def item(root):
    return json.loads(next((root / "data/queue/gersinho").glob("*.json")).read_text())


def test_intake_creates_trend_item_and_is_idempotent(usina, tmp_path):
    f = write(tmp_path, {"documents": [{"id": "gersinho-1", "data": doc()}]})
    out = intake(usina, f)
    assert out["applied_ids"] == ["gersinho-1"] and len(out["created"]) == 1
    assert out["restore"][0]["asset_id"] == ASSET
    it = item(usina)
    assert it["state"] == "ideia" and it["idea"]["format"] == "trend"
    ik = it["intake"]
    assert ik["doc_id"] == "gersinho-1" and ik["source_asset"] == ASSET
    assert ik["replace_subject"].startswith("the dancer") and ik["consent"] and ik["people"]
    upd = json.loads((usina / "out/panel/motion-updates.json").read_text())
    assert upd[0]["op"] == "update" and upd[0]["data"]["status"] == "na fila"
    # de novo: nada novo, nenhum item a mais
    out2 = intake(usina, f)
    assert out2["created"] == [] and out2["already"] == ["gersinho-1"]
    assert len(list((usina / "data/queue/gersinho").glob("*.json"))) == 1


def test_intake_rejects_bad_docs_with_reason(usina, tmp_path):
    rows = [{"id": "m-draft", **doc(page="marlene")},
            {"id": "m-cut", **doc(cuts=[4.2])},
            {"id": "m-nosubj", **doc(replace_subject="")},
            {"id": "m-long", **doc(startS=0, endS=35)},
            {"id": "m-done", **doc(status="na fila")}]
    out = intake(usina, write(tmp_path, rows))
    reasons = {i["id"]: i["reason"] for i in out["invalid"]}
    assert "ata D6" in reasons["m-draft"] and "cortes" in reasons["m-cut"]
    assert "replace_subject" in reasons["m-nosubj"] and "3–30" in reasons["m-long"]
    assert "m-done" not in out["applied_ids"] and not out["created"]
    # o falso alarme marcado pelo Caio libera
    out = intake(usina, write(tmp_path, [{"id": "m-ok", **doc(cuts=[4.2], cutsFalseAlarm=True)}], "b.json"))
    assert len(out["created"]) == 1
    # os erros voltam para o painel no panel-export
    run(usina, "panel-export")
    batch = json.loads((usina / "out/panel/batch.json").read_text())
    mo = {w["doc_id"]: w for w in batch if w["collection"] == "motion"}
    assert mo["m-cut"]["op"] == "update" and mo["m-cut"]["data"]["status"] == "erro"
    assert mo["m-ok"]["data"]["status"] == "na fila"


def test_plan_restore_then_source_then_script_with_intake(usina, tmp_path):
    intake(usina, write(tmp_path, [{"id": "d1", **doc()}]))
    ref = f"gersinho/{item(usina)['id']}"
    plan = json.loads(run(usina, "plan").stdout)
    a = next(x for x in plan["actions"] if x.get("item") == ref)
    assert a["do"] == "restore_source" and a["asset_id"] == ASSET and "motion-source" in a["how"]
    # o clipe do painel chega em webm (MediaRecorder sem mp4): vira MP4
    webm = tmp_path / "clip.webm"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=360x640:rate=30:duration=8",
                    "-c:v", "libvpx", "-b:v", "1M", str(webm)], check=True)
    run(usina, "motion-source", ref, "--file", str(webm))
    it = item(usina)
    assert it["state"] == "ideia" and it["motion"]["source_path"].endswith(".mp4")
    assert Path(usina / it["motion"]["source_path"]).read_bytes()[4:8] == b"ftyp"
    plan = json.loads(run(usina, "plan").stdout)
    a = next(x for x in plan["actions"] if x.get("item") == ref)
    assert a["do"] == "write_script" and a["intake"]["replace_subject"].startswith("the dancer")
    assert "intake" in a["how"] and abs(a["duration_s"] - 8) < 0.5
    run(usina, "panel-export")
    batch = json.loads((usina / "out/panel/batch.json").read_text())
    assert next(w for w in batch if w["collection"] == "motion")["data"]["status"] == "fonte registrada"
    # roteiro salvo: a duração é a da fonte, o item segue o fluxo normal (4 variações do frame)
    s = json.loads((usina / TREND).read_text())
    s["duration_s"] = 12
    (tmp_path / "s.json").write_text(json.dumps(s))
    run(usina, "save-script", ref, str(tmp_path / "s.json"))
    it = item(usina)
    assert it["state"] == "roteiro" and abs(it["script"]["duration_s"] - 8) < 0.5
    plan = json.loads(run(usina, "plan").stdout)
    assert any(x.get("cmd", "").endswith("frames --variants 4") for x in plan["actions"] if x.get("item") == ref)


def test_mp4_from_panel_is_already_archived(usina, tmp_path):
    intake(usina, write(tmp_path, [{"id": "d2", **doc()}]))
    ref = f"gersinho/{item(usina)['id']}"
    run(usina, "motion-source", ref, "--file", str(clip(tmp_path / "src.mp4")))
    st = json.loads(run(usina, "media-status").stdout)
    keys = {u["key"] for u in st["upload"] if u["ref"] == ref}
    assert "source" not in keys and "source_first" in keys   # o clipe já é o asset do painel; só o 1º frame sobe


def test_cut_false_alarm_lets_motion_source_through(usina, tmp_path):
    intake(usina, write(tmp_path, [{"id": "d3", **doc(cuts=[4.0], cutsFalseAlarm=True)}]))
    ref = f"gersinho/{item(usina)['id']}"
    r = run(usina, "motion-source", ref, "--file", str(clip(tmp_path / "c.mp4", cut=True)))
    assert "falso alarme" in r.stdout


def test_prompts_prefer_intake_and_keep_locks():
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    from pipeline import prompts
    from pipeline.store import get_page
    page = get_page("gersinho")
    s = json.loads((HERE / TREND).read_text())
    ik = {"scene_prompt": "A São Paulo sidewalk at overcast midday. CUSTOM_SCENE.",
          "frame_prompt": "Edit image 1. Replace the dancer on frame-left with the man from image 2 and image 3. CUSTOM_FRAME.",
          "replace_subject": "the dancer on frame-left"}
    scene = prompts.motion_scene_prompt(s, page, with_sheet=True, intake=ik)
    assert "CUSTOM_SCENE" in scene and scene.startswith("Image 1 is the only character")
    assert "rigid" in scene and "deadpan" in scene and "likeness of any real person" in scene
    frame = prompts.motion_frame_prompt(s, page, ik)
    assert frame.startswith("Edit image 1. Replace the dancer on frame-left") and "CUSTOM_FRAME" in frame
    assert "lips closed" in frame and "likeness of any real person" in frame
    # sem intake, nada muda
    assert "CUSTOM" not in prompts.motion_scene_prompt(s, page) and \
        prompts.motion_frame_prompt(s, page).startswith("Edit image 1. Replace the dancer")
    # frame_prompt do painel sem o começo padrão ganha o "Edit image 1. Replace ..."
    f2 = prompts.motion_frame_prompt(s, page, {"frame_prompt": "Keep the pose.", "replace_subject": "the woman, right"})
    assert f2.startswith("Edit image 1. Replace the dancer") or f2.startswith("Edit image 1. Replace the woman")


def test_panel_motion_tab_round_trip(usina, tmp_path):
    """Chromium: a aba Motion control carrega o vídeo, acha o corte, pede o falso alarme, identifica a pessoa, escreve os
    prompts e grava o doc em `motion` (assets/sample/downloads/MediaRecorder falsos). O doc gravado entra no
    motion-intake e vira item de trend: o formato do painel e o da CLI batem."""
    import glob
    import os
    import shutil
    node_path = os.environ.get("NODE_PATH") or "/opt/node-tools/node_modules"
    chrome = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    if not shutil.which("node") or not Path(node_path, "playwright").exists() or not chrome:
        import pytest
        pytest.skip("Playwright/Chromium ausente")
    vid = tmp_path / "cut.webm"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=3",
                    "-f", "lavfi", "-i", "color=red:size=640x360:rate=30:duration=3", "-filter_complex",
                    "[0][1]concat=n=2", "-c:v", "libvpx", "-b:v", "1M", str(vid)], check=True)
    run(usina, "panel-export")
    r = subprocess.run(["node", str(HERE / "tests/panel_smoke.js"), str(usina / "out/panel/batch.json"),
                        str(HERE / "index.html"), chrome[-1], str(vid)], capture_output=True, text=True, timeout=180,
                       env={**os.environ, "NODE_PATH": node_path})
    out = r.stdout
    assert r.returncode == 0 and "PAGEERROR" not in out, out + r.stderr
    assert "MC missing: []" in out and "MC accept: video/* | adv open: false" in out
    assert "MC min3: 0.0 3.0" in out and "crop shown: true" in out             # fonte horizontal: recorte 9:16
    assert "Clipe pronto" in out and "MC cuts: Possível corte" in out
    assert "MC send blocked by cut: true" in out and "MC send before deadpan: true" in out
    assert "true:the dancer in the red shirt" in out and "Mais de uma pessoa" in out
    assert "Pedido salvo" in out and "MC overflow at 375px: false" in out
    assert '"type":"video/webm"' in out and '"type":"image/jpeg"' in out and "motion-gersinho-" in out
    # conversa com o agente, trocas editáveis, edição manual vence, aviso de custo, Caixa/aba Elenco, sem sample
    assert "MC chat shown: true" in out and "MC swaps after 1: 2 seu-tadeu" in out and "O agente pergunta" in out
    assert "MC ctx has: true,true,true,true,true" in out
    assert "MC turn2 turns: 4 | sent manual scene: true | history: true" in out
    assert "MC manual wins: Edit image 1. MANUAL frame edit" in out
    assert "MC cost load: Estimativa: ≈ 180 créditos" in out and "acima do teto de 160" in out and "msg bad" in out
    assert "CAIXA elenco: 1" in out and "Escreva o motivo" in out
    assert 'ELENCO decision: [{"ref":"gersinho/seu-tadeu","verdict":"approve"}]' in out and "CAIXA elenco after: 0" in out
    assert "ELENCO tab: 4" in out and "ELENCO overflow at 375px: false" in out
    assert "NOSAMPLE chat hidden: true" in out and "2. Replace the green bottle with a closed black umbrella" in out
    docs = json.loads(out.split("MOTION DOC: ", 1)[1].splitlines()[0])
    d = docs[0]
    assert d["status"] == "novo" and d["page"] == "gersinho" and d["cutsFalseAlarm"] is True
    assert "SCENE_MOCK turn 3" in d["scene_prompt"] and d["consent"] and d["sourceDeadpan"] is True
    assert [x["replace_with"]["kind"] for x in d["swaps"]] == ["protagonist", "cast"] and d["instructions"].startswith("troca")
    assert len(d["chat"]) == 6 and d["chat"][0]["role"] == "user" and d["replace_subject"] == "the dancer in the red shirt, center"
    res = intake(usina, write(tmp_path, [{"id": d.pop("id"), "data": d}]))
    assert len(res["created"]) == 1 and res["created"][0]["asset_id"] == "c" * 31 + "1"
    ik = item(usina)["intake"]
    assert ik["swaps"][1]["replace_with"]["cast_id"] == "seu-tadeu" and len(ik["chat"]) == 6


SWAPS = [{"target": "the dancer in the white tank top, center",
          "replace_with": {"kind": "protagonist", "description": "Gersinho"}},
         {"target": "the man in the cap, far left", "replace_with": {"kind": "cast", "cast_id": "seu-tadeu",
                                                                      "description": "Seu Tadeu"}},
         {"target": "the green bottle", "replace_with": {"kind": "object", "description": "a closed black umbrella"}}]


def test_intake_keeps_swaps_instructions_and_chat(usina, tmp_path):
    d = doc(replace_subject="", swaps=SWAPS, instructions="troca o dançarino de branco pelo Gersinho e o cara de boné "
                                                         "pelo Seu Tadeu; a garrafa vira guarda-chuva",
            chat=[{"role": "user", "text": "troca só o da esquerda"}, {"role": "assistant", "text": "Feito."}])
    out = intake(usina, write(tmp_path, [{"id": "s1", "data": d}]))
    assert len(out["created"]) == 1 and out["warnings"] == []
    ik = item(usina)["intake"]
    assert ik["replace_subject"] == "the dancer in the white tank top, center"   # back-compat: 1ª troca pelo protagonista
    assert [s["replace_with"]["kind"] for s in ik["swaps"]] == ["protagonist", "cast", "object"]
    assert ik["swaps"][1]["replace_with"]["cast_id"] == "seu-tadeu"
    assert ik["instructions"].startswith("troca o dançarino") and ik["chat"][0] == {"role": "user", "text": "troca só o da esquerda"}
    assert ik["cost"]["est_credits"] == 64 and ik["cost"]["cap_idea"] == 160
    # cast inexistente ou nenhuma troca pelo personagem: erro com motivo
    bad = [{"id": "s2", **doc(replace_subject="", swaps=[SWAPS[1]])},
           {"id": "s3", **doc(swaps=[{"target": "x", "replace_with": {"kind": "cast", "cast_id": "ninguem"}}])}]
    reasons = {i["id"]: i["reason"] for i in intake(usina, write(tmp_path, bad, "bad.json"))["invalid"]}
    assert "replace_subject" in reasons["s2"] and "ninguem" in reasons["s3"]


def test_intake_30s_warns_cost_and_plan_blocks_before_images(usina, tmp_path):
    out = intake(usina, write(tmp_path, [{"id": "long", **doc(startS=0, endS=30)}]))
    assert len(out["created"]) == 1
    w = out["warnings"][0]["warning"]
    assert "240 créditos" in w and "160" in w and "20 s" in w
    ref = f"gersinho/{item(usina)['id']}"
    long = tmp_path / "long.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=360x640:rate=30:duration=30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(long)], check=True)
    r = run(usina, "motion-source", ref, "--file", str(long))
    assert "loop melhor no Reels" in r.stdout and "240 créditos" in r.stdout
    s = json.loads((usina / TREND).read_text())
    s["duration_s"] = 30
    (tmp_path / "s.json").write_text(json.dumps(s))
    r = run(usina, "save-script", ref, str(tmp_path / "s.json"))
    plan = json.loads(run(usina, "plan").stdout)
    a = next(x for x in plan["actions"] if x.get("item") == ref)
    assert a["do"] == "blocked" and "240 créditos" in a["why"] and "teto de 160" in a["why"]
    assert item(usina)["intake"]["cost"]["est_credits"] == 240


def test_trend_with_cast_swap_needs_approved_sheet_then_frames(usina, tmp_path):
    intake(usina, write(tmp_path, [{"id": "c1", **doc(swaps=SWAPS[:2])}]))
    ref = f"gersinho/{item(usina)['id']}"
    run(usina, "motion-source", ref, "--file", str(clip(tmp_path / "src.mp4")))
    run(usina, "save-script", ref, TREND)
    a = next(x for x in json.loads(run(usina, "plan").stdout)["actions"] if x.get("item") == ref)
    assert a["cmd"] == "python -m pipeline image gersinho cast-sheet seu-tadeu"
    run(usina, "image", "gersinho", "cast-sheet", "seu-tadeu")
    assert "cast approve" in run(usina, "image", ref, "frames", "--variants", "4", ok=False).stderr
    run(usina, "cast", "approve", "gersinho", "seu-tadeu")
    run(usina, "image", ref, "frames", "--variants", "4")
    it = item(usina)
    p = it["variants"][0]["prompt"]
    assert "Replace the man in the cap, far left with SEU TADEU CARIMBO" in p and "image 4" in p
