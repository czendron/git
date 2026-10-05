"""Rodada 4 de QA (docs/qa/rodada-4.md): ensaio do ciclo diário inteiro, como o SKILL manda.

Regressões dos bugs achados no ensaio e o próprio ensaio como teste (`test_e2e_daily_cycle_as_skill`): um item
próprio do Gersinho (ideia → postado), uma trend (fonte → variações/pick → MC → gag → pacote → postado) e um item
da Marlene barrado pelo portão de estreia, com o painel, o Higgsfield e o asset store simulados.
"""
import glob
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import yaml

from test_pipeline import HERE, run, usina  # noqa: F401  (fixture reaproveitada)
from test_qa_rodada1 import EXAMPLE, item_json, ledger, plan, to_frames_approved
from test_qa_rodada2 import TREND, clip
from test_qa_rodada3 import activate_marlene, set_page, trend_in_revisao, trend_with_source, write_lock


def items(root):
    out = {}
    for f in (root / "data/queue").glob("*/*.json"):
        d = json.loads(f.read_text())
        out[f"{d['page']}/{d['id']}"] = d
    return out


def it_of(root, ref):
    page, iid = ref.split("/", 1)
    return json.loads((root / "data/queue" / page / f"{iid}.json").read_text())


def decisions(root, docs):
    f = root / "out/panel/decisoes.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"documents": docs}))
    return json.loads(run(root, "panel-apply", str(f)).stdout.strip().splitlines()[-1])


def dec(did, ref, stage, verdict, notes="", at=None):
    return {"id": did, "version": "v1", "data": {"ref": ref, "stage": stage, "verdict": verdict, "notes": notes,
                                                 "at": at or int(time.time() * 1000), "applied": False}}


# ---------- bug A: lock reentrante ----------

def test_tick_start_reentrant_same_session(usina):
    first = json.loads(run(usina, "tick-start").stdout)
    again = run(usina, "tick-start")                     # antes: "outro ciclo rodando" com o próprio dono
    out = again.stdout
    assert json.loads(out[out.index("{"):])["owner"] == first["owner"] and "renovado" in out
    assert plan(usina).get("other_tick") is None
    write_lock(usina, "OUTRA")                           # outro dono continua barrado
    assert run(usina, "tick-start", ok=False).returncode == 1
    run(usina, "tick-end", "--force")


# ---------- bug B: triagem C6 gravada ----------

def test_triage_opts_persist_after_failed_job(usina):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    for k in ("start", "end", "storyboard"):
        run(usina, "record-upload", ref, k, "--hf-id", f"H{k}")
    vr = json.loads(run(usina, "video-request", ref, "--no-grid", "--repair", "porta fecha mais devagar").stdout)
    assert vr["triage"] == {"no_grid": True, "repair": "porta fecha mais devagar"}
    run(usina, "record-video", ref, "--job", "J1", "--credits", "65")
    run(usina, "record-video", ref, "--failed", "nsfw")          # volta para frames
    act = next(a for a in plan(usina)["actions"] if a.get("item") == ref)
    assert act["do"] == "video_submit" and act["triage"]["no_grid"] and "Triagem" in act["how"]
    vr = json.loads(run(usina, "video-request", ref).stdout)      # o comando puro do plano mantém a triagem
    p = vr["requests"][0]["params"]
    assert "@Image 3" not in p["prompt"] and len(p["medias"]) == 4 and "porta fecha mais devagar" in p["prompt"]
    vr = json.loads(run(usina, "video-request", ref, "--reset-opts").stdout)
    assert vr["triage"] == "nenhuma" and "@Image 3" in vr["requests"][0]["params"]["prompt"]


# ---------- bug C: kill switch e veto idempotentes ----------

def test_killswitch_and_veto_idempotent(usina):
    ref = run(usina, "new", "gersinho", "Vetada", "--idea", "x").stdout.strip()
    docs = [dec("ks1", "usina/kill-switch", "usina", "pause"), dec("v1", ref, "ideia", "reject", "vetado na Fila")]
    r = decisions(usina, docs)
    assert set(r["applied_ids"]) == {"ks1", "v1"} and (usina / "PAUSE").exists()
    run(usina, "resume")                                  # o Caio retomou pelo terminal
    r = decisions(usina, docs)                           # o painel ainda não marcou applied: não reaplica
    assert not (usina / "PAUSE").exists() and set(r["applied_ids"]) == {"ks1", "v1"} and not r["obsolete_ids"]
    assert it_of(usina, ref)["state"] == "descartado"


# ---------- bug D: estorno do gag ----------

def test_gag_refund(usina, tmp_path):
    ref = trend_in_revisao(usina, tmp_path)
    run(usina, "record-upload", ref, "last", "--hf-id", "LAST")
    run(usina, "record-video", ref, "--gag", "--job", "G1", "--credits", "32.5")
    run(usina, "record-video", ref, "--gag", "--failed", "cancelled", "--refunded")
    rows = [r for r in ledger(usina) if r["job_id"] == "G1"]
    assert [r["action"] for r in rows] == ["video_submit", "video_failed", "video_refund"]
    assert rows[-1]["credits"] == -32.5
    assert "já lançado" in run(usina, "record-video", ref, "--gag", "--refunded", "--job", "G1").stdout
    r = run(usina, "record-video", ref, "--gag", "--refunded", "--job", "NAOEXISTE", ok=False)
    assert r.returncode == 1 and "--gag --failed" in r.stderr


# ---------- bug E: D3, o Caio aprova o vídeo final (MC + gag) ----------

def test_caio_approves_trend_only_after_gag(usina, tmp_path):
    ref = trend_in_revisao(usina, tmp_path)
    p = plan(usina)
    assert not any(w["item"] == ref and w["stage"] == "video" for w in p["waiting_caio"])   # sem card ainda
    run(usina, "panel-export")
    doc = next(w["data"] for w in json.loads((usina / "out/panel/batch.json").read_text())
               if w["collection"] == "fila" and w["data"]["ref"] == ref)
    assert doc["gagPending"] is True
    assert "gag" in run(usina, "approve", ref, "video", ok=False).stderr
    r = decisions(usina, [dec("early", ref, "video", "approve")])          # aprovação antes do gag: obsoleta
    assert r["obsolete_ids"] == ["early"] and it_of(usina, ref)["gates"]["video"]["caio"] == "pending"
    run(usina, "record-upload", ref, "last", "--hf-id", "LAST")
    run(usina, "record-video", ref, "--gag", "--job", "G1", "--credits", "32.5")
    run(usina, "record-video", ref, "--gag", "--url", "https://x/g.mp4")
    run(usina, "fetch-video", ref, "--gag", "--file", str(clip(tmp_path / "g.mp4", dur=4)))
    run(usina, "review", ref, "gag", "pass")
    assert any(w["item"] == ref and w["stage"] == "video" for w in plan(usina)["waiting_caio"])
    r = decisions(usina, [dec("early", ref, "video", "approve", at=int((time.time() - 60) * 1000))])
    assert it_of(usina, ref)["gates"]["video"]["caio"] == "pending"        # decisão de antes do gag não vale
    decisions(usina, [dec("late", ref, "video", "approve")])
    assert it_of(usina, ref)["gates"]["video"]["caio"] == "approved"


# ---------- bug F: mídia que só existia no container ----------

def test_media_status_archives_package_and_variants(usina, tmp_path):
    ref = trend_with_source(usina, tmp_path)
    run(usina, "image", ref, "frames", "--variants", "4")
    keys = {u["key"] for u in json.loads(run(usina, "media-status").stdout)["upload"]}
    assert {"var1", "var2", "var3", "var4", "source", "source_first"} <= keys
    st = json.loads(run(usina, "media-status").stdout)
    v3 = next(u for u in st["upload"] if u["key"] == "var3")
    run(usina, "panel-asset", ref, "var3", "/_blob/" + "a" * 32, "--path", v3["path"])
    run(usina, "pick", ref, "frames", "3")
    st = json.loads(run(usina, "media-status").stdout)
    assert not any(u["key"] in ("start", "var1") for u in st["upload"])  # a opção escolhida já está arquivada
    shutil.rmtree(usina / "out" / "gersinho")                          # a sessão caiu: container novo
    st = json.loads(run(usina, "media-status").stdout)
    lost = {x["key"]: x["fix"] for x in st["lost"]}
    assert "motion-source" in lost["source"] and "retry" not in lost["source"]
    assert [x["key"] for x in st["restore"]] == ["start"]                # a opção escolhida volta do arquivo
    r = run(usina, "pick", ref, "frames", "3", ok=False)
    assert r.returncode == 1 and "media-status" in r.stderr and f"retry {ref} frames" in r.stderr


def test_package_archived_and_cover_is_gag_end(usina, tmp_path):
    ref = trend_in_revisao(usina, tmp_path)
    run(usina, "record-upload", ref, "last", "--hf-id", "LAST")
    run(usina, "record-video", ref, "--gag", "--job", "G1", "--credits", "30")
    run(usina, "record-video", ref, "--gag", "--url", "https://x/g.mp4")
    gag = tmp_path / "g.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=red:size=360x640:rate=30:duration=4",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(gag)], check=True)
    run(usina, "fetch-video", ref, "--gag", "--file", str(gag))
    run(usina, "review", ref, "gag", "pass")
    run(usina, "approve", ref, "video")
    run(usina, "package", ref)
    it = it_of(usina, ref)
    from PIL import Image
    r, g, b = Image.open(usina / it["post"]["package"] / "capa.jpg").convert("RGB").resize((1, 1)).getpixel((0, 0))
    assert r > 180 and g < 80 and b < 80                                  # a capa é o fim do gag (vermelho)
    assert not (usina / it["post"]["package"] / "_last.jpg").exists()
    up = [u for u in json.loads(run(usina, "media-status").stdout)["upload"] if u["key"] == "package"]
    assert up and up[0]["path"].endswith(f"{ref.replace('/', '-')}.mp4") and Path(up[0]["file"]).exists()


# ---------- bug G: pronto -> postado sem terminal ----------

def test_posted_via_panel_and_via_placar(usina, tmp_path):
    refs = []
    for t in ("A", "B"):
        ref = to_frames_approved(usina, t)
        run(usina, "approve", ref, "frames")
        run(usina, "record-video", ref, "--job", f"J{t}", "--credits", "65")
        run(usina, "record-video", ref, "--url", "https://x/v.mp4")
        run(usina, "fetch-video", ref, "--file", str(clip(tmp_path / f"{t}.mp4", dur=10)))
        run(usina, "review", ref, "video", "pass")
        run(usina, "approve", ref, "video")
        run(usina, "package", ref)
        refs.append(ref)
    w = plan(usina)["waiting_caio"]
    assert {x["item"] for x in w if x["stage"] == "postar"} == set(refs)
    r = decisions(usina, [dec("p1", refs[0], "post", "posted", "https://instagram.com/reel/1"),
                          dec("p2", "gersinho/nao-existe", "post", "posted")])
    assert r["invalid_ids"] == ["p2"]
    a = it_of(usina, refs[0])
    assert a["state"] == "postado" and a["post"]["link"] == "https://instagram.com/reel/1"
    assert "já postado" in run(usina, "panel-apply", str(usina / "out/panel/decisoes.json")).stdout
    f = tmp_path / "placar.json"
    f.write_text(json.dumps([{"id": "x", "data": {"ref": refs[1], "views": 900, "shares": 4, "follows": 1, "ret3": 30,
                                                  "createdAt": int(time.time() * 1000)}}]))
    out = json.loads(run(usina, "placar-import", str(f)).stdout)
    assert out["marked_posted"] == [refs[1]] and it_of(usina, refs[1])["state"] == "postado"


# ---------- fricções transformadas em regra ----------

def test_review_video_action_carries_cuts_and_sheets(usina, tmp_path):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    run(usina, "record-video", ref, "--job", "J1", "--credits", "65")
    run(usina, "record-video", ref, "--url", "https://x/v.mp4")
    run(usina, "fetch-video", ref, "--file", str(clip(tmp_path / "c.mp4", dur=10, cut=True)))
    a = next(x for x in plan(usina)["actions"] if x.get("item") == ref)
    assert a["do"] == "review_video" and a["cuts"] and "cortes detectados" in a["how"]
    assert any(f.endswith("-sheet.jpg") for f in a["file"]) and any(f.endswith("-last.jpg") for f in a["file"])


def test_redo_video_at_credit_cap_goes_straight_to_discard(usina, tmp_path):
    ref = to_frames_approved(usina)
    run(usina, "approve", ref, "frames")
    for j in ("J1", "J2"):
        run(usina, "record-video", ref, "--job", j, "--credits", "65")
        if j == "J1":
            run(usina, "record-video", ref, "--failed", "timeout")
    run(usina, "record-video", ref, "--url", "https://x/v.mp4")
    run(usina, "fetch-video", ref, "--file", str(clip(tmp_path / "v.mp4", dur=10)))
    run(usina, "review", ref, "video", "pass")
    decisions(usina, [dec("rej", ref, "video", "reject", "piada não lê sem som")])
    a = next(x for x in plan(usina)["actions"] if x.get("item") == ref)       # 130 + 65 > 160
    assert a["do"] == "discard" and "160" in a["how"]


def test_fetch_refs_fails_loudly_and_accepts_local_files(usina, tmp_path):
    refs = usina / "pages/gersinho/refs"
    for f in refs.glob("*.png"):
        f.unlink()
    p = yaml.safe_load((usina / "pages/gersinho/page.yaml").read_text())
    for r in p["refs"]:
        r["url"] = "file:///nao/existe.png"
    (usina / "pages/gersinho/page.yaml").write_text(yaml.safe_dump(p, allow_unicode=True))
    r = run(usina, "fetch-refs", "gersinho", ok=False)
    assert r.returncode == 1 and "--face" in r.stderr
    from PIL import Image
    Image.new("RGB", (8, 8)).save(tmp_path / "f.png")
    Image.new("RGB", (8, 8)).save(tmp_path / "s.png")
    run(usina, "fetch-refs", "gersinho", "--face", str(tmp_path / "f.png"), "--silhouette", str(tmp_path / "s.png"))
    assert (refs / "rosto.png").exists() and (refs / "silhueta.png").exists()


def test_launch_gate_message_lists_only_generation_blockers(usina):
    activate_marlene(usina)
    set_page(usina, "gersinho", launched_at=time.strftime("%Y-%m-%d"))
    ref = run(usina, "new", "marlene", "Laquê", "--idea", "x", "--force").stdout.strip()
    s = json.loads((usina / EXAMPLE).read_text())
    s["page"] = "marlene"
    (usina / "m.json").write_text(json.dumps(s))
    run(usina, "save-script", ref, "m.json")
    err = run(usina, "image", ref, "storyboard", ok=False).stderr
    assert "D+10" in err and "prontos" not in err


def test_panel_hides_video_card_while_gag_pending_and_posts(usina, tmp_path):
    """Painel no Chromium: card de vídeo some com gagPending; pronto mostra Baixar MP4 e o Postei grava a decisão."""
    node_path = os.environ.get("NODE_PATH") or "/opt/node-tools/node_modules"
    chrome = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    if not shutil.which("node") or not Path(node_path, "playwright").exists() or not chrome:
        pytest.skip("Playwright/Chromium ausente")
    t = trend_in_revisao(usina, tmp_path)
    ref = to_frames_approved(usina, "Pronto")
    run(usina, "approve", ref, "frames")
    run(usina, "record-video", ref, "--job", "J1", "--credits", "65")
    run(usina, "record-video", ref, "--url", "https://x/v.mp4")
    run(usina, "fetch-video", ref, "--file", str(clip(tmp_path / "v.mp4", dur=10)))
    run(usina, "review", ref, "video", "pass")
    run(usina, "approve", ref, "video")
    run(usina, "package", ref)
    st = json.loads(run(usina, "media-status").stdout)
    pk = next(u for u in st["upload"] if u["key"] == "package")
    run(usina, "panel-asset", ref, "package", "/_blob/" + "b" * 32, "--path", pk["path"])
    run(usina, "panel-export")
    r = subprocess.run(["node", str(HERE / "tests/panel_smoke.js"), str(usina / "out/panel/batch.json"),
                        str(HERE / "index.html"), chrome[-1]], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "NODE_PATH": node_path})
    out = r.stdout
    assert r.returncode == 0 and "PAGEERROR" not in out, out + r.stderr
    assert "CAIXA cards: 0" in out                                   # trend com gag pendente: sem card de vídeo
    assert f'"/_blob/{"b" * 32}"' in out and "post buttons: 1" in out and "post after: 0" in out
    assert f'"stage":"post","verdict":"posted","ref":"{ref}","notes":"https://instagram.com/reel/abc"' in out
    assert t


# ---------- o ensaio inteiro, automatizado ----------

class Rehearsal:
    """Executa o ciclo do SKILL contra a CLI, simulando o painel (decisoes/placar/assets) e o Higgsfield.

    Cada ciclo é um container novo: out/ apagado, mídia restaurada do "asset store" (uma pasta), lock, painel,
    `plan` e as ações na ordem (o executor roda o `cmd`/`how` do jeito que o plano emite), sync do painel e tick-end.
    """

    def __init__(self, root: Path, tmp: Path):
        self.root, self.tmp = root, tmp
        self.store = tmp / "asset-store"
        self.store.mkdir()
        self.panel = {}          # decisoes do painel: id -> doc
        self.placar = []
        self.log = []
        self.jobs = {}           # job_id -> arquivo de resultado
        self.n = 0
        self.media = {
            "cut": clip(tmp / "cut.mp4", dur=10, size="720x1280", cut=True),
            "own": clip(tmp / "own.mp4", dur=10, size="720x1280"),
            "mc": clip(tmp / "mc.mp4", dur=10, size="720x1280"),
            "gag": clip(tmp / "gag.mp4", dur=5, size="720x1280"),
            "source": clip(tmp / "source.mp4", dur=9, size="720x1280"),
        }
        # roteiro do QA: o que o revisor de IA e o provedor fazem em cada tentativa (consumido em ordem)
        self.qa = {("own", "storyboard"): ["fail", "pass"], ("trend", "frames"): ["fail", "pass"]}
        self.outcome = {"own": ["cut", "failed", "own"], "trend": ["mc"], "gag": ["failed", "gag"]}
        self.caio = {("own", "storyboard"): ["reject", "approve"]}
        self.ideas = [("gersinho", "Busão: topete preso", "own"), ("gersinho", "Padaria: topete no forno", "veto"),
                      ("gersinho", "Trend do calçadão", "trend")]
        self.kind = {}

    # --- infraestrutura ---
    def P(self, *args, ok=True):
        r = run(self.root, *args, ok=ok)
        self.log.append((args, r.returncode))
        return r

    def J(self, *args):
        return json.loads(self.P(*args).stdout)

    def new_container(self):
        shutil.rmtree(self.root / "out", ignore_errors=True)
        st = self.J("media-status")
        assert st["lost"] == [], st["lost"]
        for x in st["restore"]:
            self.P("media-restore", x["ref"], x["key"], "--file", str(self.store / x["asset_id"]))
        assert self.J("media-status")["restore"] == []

    def sync_panel(self):
        st = self.J("media-status")
        for u in st["upload"]:
            aid = hashlib.md5((u["path"] + str(Path(u["file"]).stat().st_size)).encode()).hexdigest()
            shutil.copy(u["file"], self.store / aid)
            self.P("panel-asset", u["ref"], u["key"], f"https://claude.ai/_blob/{aid}", "--path", u["path"])
        assert self.J("media-status")["upload"] == []
        self.P("panel-export")
        self.batch = json.loads((self.root / "out/panel/batch.json").read_text())

    def apply_panel(self):
        f = self.root / "out/panel/decisoes.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps([{"id": k, "version": "v1", "data": v} for k, v in self.panel.items()]))
        out = json.loads(self.P("panel-apply", str(f)).stdout.strip().splitlines()[-1])
        for i in out["applied_ids"]:
            self.panel[i]["applied"] = True          # ArtifactData update {"applied": true}
        f = self.root / "out/panel/placar.json"
        f.write_text(json.dumps({"documents": [{"id": d["ref"].replace("/", "--"), "data": d} for d in self.placar]}))
        return self.J("placar-import", str(f))

    def decide(self, ref, stage, verdict, notes=""):
        self.n += 1
        at = int(time.time() * 1000) + self.n
        self.panel[f"{ref.replace('/', '--')}--{stage}--{at}"] = {"ref": ref, "stage": stage, "verdict": verdict,
                                                                   "notes": notes, "at": at, "applied": False}

    # --- o Caio no painel, entre ciclos ---
    def caio_acts(self):
        fila = {w["data"]["ref"]: w["data"] for w in self.batch if w["collection"] == "fila"}
        for ref, f in fila.items():
            kind = self.kind.get(ref)
            for st in ("storyboard", "frames", "video"):
                g = f["gates"].get(st) or {}
                ready = {"storyboard": "storyboard", "frames": "frames", "video": "revisao"}[st] == f["state"]
                if not (ready and g.get("qa") == "pass" and g.get("caio") == "pending"):
                    continue
                if st == "video" and f.get("gagPending"):
                    continue
                if any(d["ref"] == ref and d["stage"] == st and not d["applied"] for d in self.panel.values()):
                    continue
                assert f["assets"].get({"storyboard": "storyboard", "frames": "start", "video": "sheet"}[st]), \
                    f"card sem imagem: {ref} {st}"
                v = (self.caio.get((kind, st)) or ["approve"]).pop(0) if self.caio.get((kind, st)) else "approve"
                self.decide(ref, st, v, "topete achatado no painel 3" if v == "reject" else "")
            if kind == "veto" and f["state"] in ("ideia", "roteiro", "storyboard") and \
                    not any(d["ref"] == ref and d["stage"] == "ideia" for d in self.panel.values()):
                self.decide(ref, "ideia", "reject", "vetado na Fila")
            if f["state"] == "pronto":
                pk = f["assets"].get("package", "")
                aid = pk.rsplit("/", 1)[-1]
                assert aid and (self.store / aid).exists(), f"pacote de {ref} não está no painel"
                self.downloaded = getattr(self, "downloaded", {})
                self.downloaded[ref] = self.store / aid
                if kind == "trend":                    # posta e clica "Postei"
                    self.decide(ref, "post", "posted", "https://instagram.com/reel/trend")
                elif not any(p["ref"] == ref for p in self.placar):   # posta e lança números no Placar
                    self.placar.append({"ref": ref, "page": f["page"], "title": f["title"], "views": 1500,
                                        "shares": 10, "follows": 2, "ret3": 41, "createdAt": int(time.time() * 1000)})

    # --- o operador (sessão do Claude) executando o plano ---
    def kind_of(self, ref):
        return self.kind.get(ref, "own")

    def execute(self, a):
        do, ref = a["do"], a.get("item")
        if do == "new_ideas":
            for page, title, kind in list(self.ideas):
                if page != a["page"] or (kind == "trend" and not a["allow_trend"]):
                    continue
                self.ideas.remove((page, title, kind))
                ref = self.P("new", page, title, "--idea", title).stdout.strip()
                self.kind[ref] = kind
                return True
            return False
        if do == "check_balance":
            self.P("balance", "5000")
            return True
        if do == "write_script":
            src = TREND if self.kind_of(ref) == "trend" else EXAMPLE
            dst = self.root / "out/scripts" / f"{ref.split('/')[1]}.json"
            dst.parent.mkdir(parents=True, exist_ok=True)
            s = json.loads((self.root / src).read_text())
            s["title"] = it_of(self.root, ref)["idea"]["title"]
            dst.write_text(json.dumps(s))
            assert f"save-script {ref} out/scripts/" in a["how"]
            self.P("save-script", ref, str(dst.relative_to(self.root)))
            return True
        if do in ("run", "discard"):
            cmd = shlex.split(a.get("cmd") or a["how"])
            assert cmd[:3] == ["python", "-m", "pipeline"], cmd
            self.P(*cmd[3:])
            return True
        if do == "review_image":
            kind, st = self.kind_of(ref), a["stage"]
            files = a["file"] if isinstance(a["file"], list) else [a["file"]]
            assert all((self.root / f).exists() for f in files), f"revisor sem arquivo: {files}"
            v = self.qa.get((kind, st), ["pass"]).pop(0) if self.qa.get((kind, st)) else "pass"
            if a.get("pick"):
                self.P("pick", ref, "frames", "3" if v == "pass" else "1")
            self.P("review", ref, st, v, "--notes", "G3 topete baixo [identidade]" if v == "fail" else "ok")
            return True
        if do == "video_submit":
            gag = ["--gag"] if a.get("gag") else []
            vr = self.J("video-request", ref, *gag)
            if not vr["ready"]:
                for u in vr["upload_first"]:
                    hf = f"hf-{u['key']}-{self.n}"
                    if u["key"] == "source":
                        self.P("motion-source", ref, "--hf-id", hf)
                    else:
                        self.P("record-upload", ref, u["key"], "--hf-id", hf)
                vr = self.J("video-request", ref, *gag)
            assert vr["ready"] and vr["mcp_tool"] == "mcp__Higgsfield__generate_video_batch"
            assert "--job <job_id>" in vr["then"]
            self.n += 1
            job = f"job-{self.n}"
            kind = "gag" if gag else self.kind_of(ref)
            self.jobs[job] = self.outcome[kind].pop(0)
            est = a["est_credits"]
            self.P("record-video", ref, *gag, "--job", job, "--credits", str(est))
            return True
        if do == "video_poll":
            gag = ["--gag"] if a.get("gag") else []
            res = self.jobs[a["job_id"]]
            if res == "failed":   # jobs_wait: failed; transactions mostra o estorno
                self.P("record-video", ref, *gag, "--failed", "nsfw", "--refunded")
            else:
                self.P("record-video", ref, *gag, "--url", self.media[res].as_uri())
            return True
        if do == "review_video":
            files = a["file"] if isinstance(a["file"], list) else [a["file"]]
            assert files and all((self.root / f).exists() for f in files), files
            st = a.get("stage", "video")
            v = "fail" if a.get("cuts") else "pass"
            self.P("review", ref, st, v, "--notes", f"G1 corte seco em {a.get('cuts')} [corte]" if v == "fail" else "ok")
            if v == "fail" and st == "video":
                assert "triagem" in json.dumps(next(x for x in self.J("plan")["actions"] if x.get("item") == ref),
                                               ensure_ascii=False).lower()
                self.triage_next = ref
            return True
        if do == "blocked":
            return False
        raise AssertionError(f"ação desconhecida: {a}")

    def cycle(self, max_actions=12):
        self.new_container()
        self.P("balance", "5000")                                   # passo 0: saldo lido nesta sessão
        self.P("tick-start")
        self.apply_panel()
        n = 0
        blocked = []
        while n < max_actions:
            p = self.J("plan")
            if p["paused"]:
                break
            assert not p.get("other_tick")
            acts = [a for a in p["actions"] if a["do"] != "blocked"]
            blocked = [a for a in p["actions"] if a["do"] == "blocked"]
            done = False
            for a in acts:
                if getattr(self, "triage_next", None) == a.get("item") and a["do"] == "video_submit":
                    self.P("video-request", a["item"], "--no-grid")        # triagem: muda UMA variável
                    self.triage_next = None
                if self.execute(a):
                    done = True
                    n += 1
                    break
            if not done:
                break
        self.sync_panel()
        self.P("tick-end")
        assert not (self.root / ".lock").exists()
        return p, blocked

    def next_day(self):
        f = self.root / "data/ledger.jsonl"
        rows = [json.loads(x) for x in f.read_text().splitlines() if x.strip()]
        f.write_text("".join(json.dumps({**r, "at": r["at"] - 86400}) + "\n" for r in rows))


def seed_history(root):
    """3 posts antigos do Gersinho (roteiros próprios): a trend cabe nos 30% da D7 e a estreia foi há 2 dias
    (calibração D3 ligada: o Caio aprova storyboard e frames; a Marlene ainda está antes do D+10)."""
    s = json.loads((root / EXAMPLE).read_text())
    now = time.time()
    for i, place in enumerate(["feira livre", "padaria do bairro", "lotérica da esquina"]):
        iid = f"20260915-00000{i}-antigo-{i}"
        d = {"page": "gersinho", "id": iid, "state": "postado", "created_at": now - 20 * 86400,
             "updated_at": now - 2 * 86400, "idea": {"title": f"Antigo {i}"},
             "script": {**s, "title": f"Antigo {i}", "location": {**s["location"], "place": place}},
             "post": {"posted_at": now - 2 * 86400 + i, "link": f"https://instagram.com/reel/old{i}"}}
        f = root / "data/queue/gersinho" / f"{iid}.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d))


def test_e2e_daily_cycle_as_skill(usina, tmp_path):
    seed_history(usina)
    R = Rehearsal(usina, tmp_path)

    # Marlene (rascunho): nada gera; ativada com ficha, ainda barrada pelo D+10.
    assert "rascunho" in R.P("new", "marlene", "Laquê no banco", "--idea", "x", ok=False).stderr
    m = R.P("new", "marlene", "Laquê no banco", "--idea", "controle remoto no cabelo", "--force").stdout.strip()
    s = json.loads((usina / EXAMPLE).read_text())
    s["page"] = "marlene"
    (usina / "m.json").write_text(json.dumps(s))
    R.P("save-script", m, "m.json")
    assert "rascunho" in R.P("image", m, "storyboard", "--force", ok=False).stderr

    trend_ref = None
    for day in range(30):
        if day == 3:   # o Caio pausa pelo painel; o ciclo seguinte só sincroniza e sai; depois retoma
            R.decide("usina/kill-switch", "usina", "pause", "viagem")
        if day == 4:
            assert (usina / "PAUSE").exists()
            R.decide("usina/kill-switch", "usina", "resume")
        p, blocked = R.cycle()
        if day == 3:
            assert p["paused"] and (usina / "PAUSE").exists()
        trend_ref = trend_ref or next((r for r, k in R.kind.items() if k == "trend"), None)
        if trend_ref and it_of(usina, trend_ref)["state"] == "roteiro":
            src = it_of(usina, trend_ref).get("motion") or {}
            if not src.get("source_path"):     # o Caio (ou a sessão) traz a fonte: com corte é recusada
                assert "cortes" in R.P("motion-source", trend_ref, "--file", str(R.media["cut"]), ok=False).stderr
                out = R.P("motion-source", trend_ref, "--file", str(R.media["source"])).stdout
                assert "media-status" in out       # rodada 4: fora do tick, quem registra a fonte arquiva
                R.sync_panel()
        if any("teto diário" in b["why"] for b in blocked):
            R.next_day()
        R.caio_acts()
        st = {r: it_of(usina, r)["state"] for r in R.kind}
        if all(v in ("postado", "descartado") for v in st.values()) and len(st) == 3:
            break
    else:
        raise AssertionError(f"o ciclo não terminou: {st}\n{R.log[-15:]}")
    R.apply_panel()

    by = {k: r for r, k in R.kind.items()}
    own, veto, trend = it_of(usina, by["own"]), it_of(usina, by["veto"]), it_of(usina, by["trend"])
    assert veto["state"] == "descartado" and "vetado" in veto["history"][-1]["why"]
    # próprio: storyboard reprovado pelo QA e pelo Caio; vídeo com corte reprovado; job falho estornado
    assert own["state"] == "postado" and own["attempts"] == {"storyboard": 3, "frames": 1, "video": 3}
    assert own["video_opts"] == {"no_grid": True}
    assert any(h.get("cuts") for h in own["video"]["history"]) and own["video"]["cuts"] == []
    # trend: 2 rodadas de variações, MC, gag (1 falho estornado), pacote emendado de 15 s, Postei no painel
    assert trend["state"] == "postado" and trend["post"]["link"] == "https://instagram.com/reel/trend"
    assert trend["attempts"]["frames"] == 2 and trend["attempts"]["gag"] == 2 and trend["post"]["with_gag"]
    assert trend["frames"]["start"]["picked"] == 3
    pk = R.downloaded[by["trend"]]
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(pk)],
                             capture_output=True, text=True, check=True).stdout)
    assert abs(d - 15) < 0.3                                     # o Caio baixou o vídeo final (MC + gag)
    rows = ledger(usina)
    assert sum(1 for r in rows if r["action"] == "video_refund") == 2
    assert not any(r["page"] == "marlene" for r in rows)        # Marlene nunca gastou
    assert it_of(usina, m)["state"] == "roteiro"
    fails = (usina / "playbook/falhas.md").read_text()
    assert "(Caio) topete achatado" in fails and "corte seco" in fails and "gag" in fails
    assert not (usina / "PAUSE").exists() and not (usina / ".lock").exists()
    # marlene ativada com ficha: ainda fechada (D+2 do Gersinho), e a mensagem não fala de estoque
    activate_marlene(usina)
    set_page(usina, "gersinho", launched_at=time.strftime("%Y-%m-%d", time.localtime(time.time() - 2 * 86400)))
    err = R.P("image", m, "storyboard", ok=False).stderr
    assert "D+10" in err and "prontos" not in err
    assert any("marlene: portão de estreia fechado" in n for n in R.J("plan")["notes"])
