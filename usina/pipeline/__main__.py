"""CLI da Usina. Uso: python -m pipeline <comando> ...  (rodar dentro de usina/)

Comandos principais:
  pages | status | plan | memory <page>
  new <page> "título" --idea "..."          cria item (estado ideia)
  save-script <page/id> arquivo.json         valida (lint) e salva o roteiro
  lint arquivo.json [--page slug]
  image <page/id> storyboard|frames [--provider openai|higgsfield] [--mock]
  record-image <page/id> <stage> <key> --hf-job <id> [--url ...]   (quando a imagem veio do Higgsfield)
  record-upload <page/id> <key> --hf-id <media_id>                  (imagem local subida pro Higgsfield)
  review <page/id> storyboard|frames|video pass|fail --notes "..."
  approve <page/id> storyboard|frames|video [--reject] [--notes]
  retry <page/id> storyboard|frames|video | discard <page/id> --why "..."
  video-request <page/id> | record-video <page/id> [--job ...] [--url ...] [--credits n]
  fetch-video <page/id> [--file local.mp4] | package <page/id> | posted <page/id> [--link]
  pause "motivo" | resume | ledger
"""
from __future__ import annotations

import argparse
import json
import re
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import budget, images, lint as lintmod, media, prompts
from .store import OUT, ROOT, StoreError, get_page, list_items, load_item, load_pages, local, new_item, rel, slugify

FAILS = ROOT / "playbook" / "falhas.md"


def _item(ref: str):
    if not isinstance(ref, str) or "/" not in ref:
        raise StoreError(f"referência inválida {ref!r}: use <page>/<id>")
    page, iid = ref.split("/", 1)
    return get_page(page), load_item(page, iid)


def _workdir(item) -> Path:
    d = OUT / item.page / item.id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _need_state(it, allowed, what: str, force: bool = False) -> None:
    """Trava de estado: impede que um comando repetido (ou fora de ordem) regrida o item ou gaste de novo."""
    if it.state not in allowed and not force:
        raise StoreError(f"{it.page}/{it.id} está em '{it.state}'; '{what}' só vale em {', '.join(allowed)} "
                         f"(use --force se for intencional)")


# Assets do painel que ficam velhos quando a etapa é refeita (senão a Caixa mostra a imagem da versão anterior).
STALE_ASSETS = {"storyboard": ["storyboard"], "frames": ["start", "end"], "video": ["sheet", "gag", "cover"]}


def _clear_assets(it, *stages: str) -> None:
    assets = it.post.get("assets") or {}
    for st in stages:
        for k in STALE_ASSETS.get(st, []):
            assets.pop(k, None)


def _switches() -> dict:
    return budget.load_budget().get("switches", {}) or {}


def _check_image_provider(provider: str) -> None:
    sw = _switches()
    if provider == "higgsfield" and sw.get("image_provider", "openai") != "higgsfield" \
            and not sw.get("image_fallback_allowed", False):
        raise StoreError("fallback de imagem pelo Higgsfield desligado em budget.yaml "
                         "(switches.image_fallback_allowed: false). Peça ao Caio para liberar.")


# ---------- comandos ----------

def cmd_pages(a):
    for p in load_pages():
        refs = [f"{r.name}{'' if r.exists() else ' (FALTA)'}" for r in p.ref_paths()]
        print(f"{p.slug:10} {p.data.get('status'):9} {p.character.get('name')}  refs: {', '.join(refs) or '—'}")


def cmd_status(a):
    s = budget.spend()
    print(f"Gasto hoje: {s.today}  mês: US$ {s.month_usd} / {s.month_cap} ({s.month_pct:.0f}%)")
    if budget.paused():
        print(f"PAUSADO: {budget.paused()}")
    for it in list_items():
        g = ", ".join(f"{k}:{v.get('qa')}/{v.get('caio')}" for k, v in it.gates.items())
        print(f"{it.page}/{it.id:48} {it.state:11} {g}")


def cmd_plan(a):
    from .tick import plan
    _print(plan())


def cmd_memory(a):
    items = [i for i in list_items(a.page) if i.script][-20:]
    for i in items:
        s = i.script
        loc = s.get("location")
        place = loc.get("place") if isinstance(loc, dict) else loc
        print(f"- [{i.state}] {s.get('title')} | {place} | {s.get('premise')}")
    if not items:
        print("(sem histórico)")


def cmd_new(a):
    page = get_page(a.page)
    if not page.active and not a.force:
        raise StoreError(f"página '{a.page}' está em '{page.data.get('status')}': não gera nada (ata D6). Use --force para testar.")
    slug = slugify(a.title)
    dup = [i for i in list_items(a.page) if i.state != "descartado" and slugify(i.idea.get("title", "")) == slug]
    if dup and not a.force:
        raise StoreError(f"já existe ideia com esse título: {a.page}/{dup[0].id} (use --force para criar outra)")
    it = new_item(a.page, a.title, {"title": a.title, "text": a.idea or a.title, "source": a.source})
    it.save()
    print(f"{it.page}/{it.id}")


def cmd_lint(a):
    script = json.loads(Path(a.file).read_text(encoding="utf-8"))
    page = get_page(a.page or script.get("page")).data if (a.page or script.get("page")) else None
    errors, warns = lintmod.lint(script, page)
    for w in warns:
        print(f"aviso: {w}")
    for e in errors:
        print(f"ERRO: {e}")
    print("OK" if not errors else f"{len(errors)} erro(s)")
    sys.exit(1 if errors else 0)


def cmd_save_script(a):
    page, it = _item(a.ref)
    script = json.loads(Path(a.file).read_text(encoding="utf-8"))
    errors, warns = lintmod.lint(script, page.data)
    for w in warns:
        print(f"aviso: {w}")
    if errors:
        for e in errors:
            print(f"ERRO: {e}")
        sys.exit(1)
    _need_state(it, ["ideia", "roteiro"], "save-script", a.force)
    if it.state not in ("ideia", "roteiro"):  # reescrita (triagem C6): tudo que veio do roteiro antigo perde a validade
        for st in ("storyboard", "frames", "video"):
            it.gates.pop(st, None)
        it.storyboard, it.frames = {}, {}
        if any(k != "history" for k in it.video):
            it.video = {"history": it.video.get("history", []) + [{k: v for k, v in it.video.items() if k != "history"}]}
        _clear_assets(it, "storyboard", "frames", "video")
    it.script = script
    it.post["caption"] = prompts.caption(script)
    it.set_state("roteiro", "lint ok")
    it.save()
    print(f"roteiro salvo: {a.ref}")


def _refs(page) -> list[Path]:
    """[rosto, silhueta] na ordem do playbook (@Image 1 = rosto, @Image 2 = silhueta)."""
    by_role = {r.get("role"): page.dir / r["file"] for r in page.data.get("refs", []) if r.get("file")}
    out = [by_role.get("face"), by_role.get("silhouette")]
    missing = [str(p) for p in out if p is None or not p.exists()]
    if missing:
        raise StoreError(f"{page.slug}: faltam referências locais ({', '.join(missing) or 'role face/silhouette'}). "
                         f"Rode `python -m pipeline fetch-refs {page.slug}` ou gere a ficha com `sheet {page.slug}` + `split-sheet`.")
    return out


def _hf_ref_ids(page) -> list[str]:
    by_role = {r.get("role"): r.get("higgsfield_id") for r in page.data.get("refs", [])}
    return [i for i in (by_role.get("face"), by_role.get("silhouette")) if i]


def cmd_image(a):
    page, it = _item(a.ref)
    stage = a.stage
    if not it.script:
        raise StoreError("item sem roteiro")
    provider = a.provider or _switches().get("image_provider", "openai")
    _check_image_provider(provider)
    b = budget.load_budget()
    quality = a.quality
    unit = b["cost_estimates"]["openai_image"].get(quality, 0.17)
    wd = _workdir(it)
    # Fallback Higgsfield, 2º passo: o frame B é edição do frame A, então só sai depois que o A foi registrado.
    hf_second = (provider == "higgsfield" and stage == "frames" and it.state == "frames"
                 and it.gates.get("frames", {}).get("qa") == "pending"
                 and it.frames.get("start", {}).get("higgsfield_id") and not it.frames.get("end"))
    if not hf_second:
        _need_state(it, ["roteiro"] if stage == "storyboard" else ["storyboard"], f"image {stage}", a.force)
    n = it.attempts.get(stage, 0) + (0 if hf_second else 1)
    jobs = []
    if stage == "storyboard":
        prompt, size = prompts.storyboard_prompt(it.script, page)
        jobs.append(("storyboard", prompt, size, []))
    elif stage == "frames":
        sb = local(it.storyboard.get("path"))
        with_sb = bool(sb and sb.exists())
        if it.storyboard.get("path") and not with_sb and not a.sem_storyboard and provider == "openai":
            raise StoreError(f"o storyboard aprovado não está nesta máquina ({it.storyboard.get('path')}). "
                             f"O frame A precisa do painel 1 (playbook C2). Restaure o arquivo (out/ não vai para o git), "
                             f"rode com --sem-storyboard (o revisor confere a composição) ou refaça o storyboard "
                             f"com `retry {a.ref} storyboard --force`.")
        sb_in_prompt = bool(it.storyboard.get("higgsfield_id")) if provider == "higgsfield" else with_sb
        jobs.append(("start", prompts.frame_a_prompt(it.script, page, sb_in_prompt),
                     "1024x1536", [sb] if with_sb else []))
        if it.script.get("en", {}).get("end_change"):
            jobs.append(("end", prompts.frame_b_prompt(it.script, page), "1024x1536", ["__FRAME_A__"]))
    else:
        raise StoreError("stage deve ser storyboard ou frames")

    if provider == "higgsfield":
        # Fallback: mesmo modelo (GPT Image 2.5) via MCP do Higgsfield; a sessão executa e registra.
        ids = _hf_ref_ids(page)
        reqs = []
        for key, prompt, size, extra in jobs:
            if hf_second and key != "end":
                continue
            if not hf_second and key == "end":
                continue  # o frame B sai no 2º passo, com o id do frame A
            medias = [{"role": "image_references", "value": i} for i in ids]
            if key == "end":  # image 1 = frame A, image 2 = rosto, image 3 = silhueta (playbook C2)
                medias = [{"role": "image_references", "value": it.frames["start"]["higgsfield_id"]}] + medias
            elif stage == "frames" and it.storyboard.get("higgsfield_id"):
                medias.append({"role": "image_references", "value": it.storyboard["higgsfield_id"]})
            reqs.append({"key": key, "params": {
                "model": "gpt_image_2_5", "aspect_ratio": "16:9" if size == "1536x1024" else "9:16",
                "quality": "high", "medias": medias, "prompt": prompt}})
        out = {"mcp_tool": "mcp__Higgsfield__generate_image_batch",
               "requests": [{"index": i, "params": r["params"]} for i, r in enumerate(reqs)],
               "then": [f"python -m pipeline record-image {a.ref} {stage} {r['key']} --hf-job <job_id> --url <result_url>"
                        for r in reqs]}
        if stage == "frames" and not hf_second and len(jobs) > 1:
            out["depois"] = (f"Frame B é edição do frame A: depois do record-image do start, rode de novo "
                             f"`python -m pipeline image {a.ref} frames --provider higgsfield` para o pedido do end.")
        _print(out)
        return

    ok, why = budget.can_spend("openai", unit * len(jobs))
    if not ok:
        raise StoreError(why)
    mock = bool(a.mock) or os.getenv("USINA_MOCK") == "1"
    refs = _refs(page)
    target = {}
    for key, prompt, size, extra in jobs:
        name = key if key == stage else f"{stage}-{key}"
        out = wd / f"{name}-v{n}.png"
        (wd / f"{name}-v{n}.prompt.txt").write_text(prompt, encoding="utf-8")
        if extra == ["__FRAME_A__"]:
            img_refs = [local(target["start"]["path"])] + refs   # Frame B = edição do Frame A (playbook C2)
        else:
            img_refs = refs + extra
        images.generate(prompt, out, img_refs, aspect=size, quality=quality, mock=mock)
        budget.record(it.page, it.id, "openai", f"image_{stage}", usd=0 if mock else unit,
                      note=f"{key}{' (mock)' if mock else ''}")
        target[key] = {"path": rel(out), "prompt": prompt, "v": n}
        print(f"ok: {out.relative_to(ROOT)}")
    it.attempts[stage] = n
    _clear_assets(it, stage)
    if stage == "storyboard":
        it.storyboard = target["storyboard"]
        it.gates["storyboard"] = {"qa": "pending", "caio": "pending"}
        it.set_state("storyboard", f"storyboard v{n}")
    else:
        it.frames = target
        it.gates["frames"] = {"qa": "pending", "caio": "pending"}
        it.set_state("frames", f"frames v{n}")
    it.save()


def cmd_record_image(a):
    page, it = _item(a.ref)
    if a.stage not in ("storyboard", "frames") or (a.stage == "frames" and a.key not in ("start", "end")) \
            or (a.stage == "storyboard" and a.key != "storyboard"):
        raise StoreError("use: record-image <ref> storyboard storyboard | frames start|end")
    seen = [it.storyboard] + list(it.frames.values())
    if any(e.get("higgsfield_job") == a.hf_job for e in seen):
        print(f"já registrado: {a.hf_job}")
        return
    # Mesma rodada? (frames: start e end chegam em dois record-image; a tentativa só conta uma vez)
    same_round = it.state == a.stage and it.gates.get(a.stage, {}).get("qa") == "pending"
    if a.stage == "storyboard":
        same_round = False
    elif not same_round:
        _need_state(it, ["storyboard"], "record-image frames")
    if a.stage == "storyboard":
        _need_state(it, ["roteiro"], "record-image storyboard")
    v = it.attempts.get(a.stage, 0) + (0 if same_round else 1)
    entry = {"higgsfield_job": a.hf_job, "higgsfield_id": a.hf_job, "url": a.url or "", "v": v}
    if a.url:
        name = "storyboard" if a.stage == "storyboard" else f"frames-{a.key}"
        dst = _workdir(it) / f"{name}-v{v}.png"
        if _download(a.url, dst):
            entry["path"] = rel(dst)
    it.attempts[a.stage] = v
    if a.stage == "storyboard":
        it.storyboard = entry
        it.gates["storyboard"] = {"qa": "pending", "caio": "pending"}
        _clear_assets(it, "storyboard")
        it.set_state("storyboard", "storyboard via Higgsfield")
    else:
        if not same_round:
            it.frames = {}
            _clear_assets(it, "frames")
            it.gates["frames"] = {"qa": "pending", "caio": "pending"}
            it.set_state("frames", "frames via Higgsfield")
        it.frames[a.key] = entry
    budget.record(it.page, it.id, "higgsfield", f"image_{a.stage}", credits=2, job_id=a.hf_job, note=a.key)
    it.save()
    print("registrado")


def cmd_record_upload(a):
    page, it = _item(a.ref)
    if a.key == "storyboard":
        it.storyboard["higgsfield_id"] = a.hf_id
    else:
        it.frames.setdefault(a.key, {})["higgsfield_id"] = a.hf_id
    it.save()
    print("registrado")


def cmd_review(a):
    page, it = _item(a.ref)
    _need_state(it, [a.stage], f"review {a.stage}")
    if a.stage == "video" and not it.video.get("path"):
        raise StoreError("vídeo ainda não baixado: rode fetch-video antes de revisar")
    g = it.gates.setdefault(a.stage, {"qa": "pending", "caio": "pending"})
    first = g.get("qa") == "pending"   # re-rodar o mesmo review não conta duas vezes no aproveitamento nem no livro de falhas
    g["qa"] = a.verdict
    g["qa_notes"] = a.notes
    g["qa_at"] = time.time()
    if a.stage == "video":
        if first:
            budget.record(it.page, it.id, "review", "video_review", ok=a.verdict == "pass", note=a.notes[:200])
        if a.verdict == "pass":
            it.set_state("revisao", "QA de vídeo ok")
    if a.verdict == "fail" and a.notes and first:
        _log_failure(it, a.stage, a.notes)
    it.save()
    print(f"{a.stage}: {a.verdict}")


def cmd_approve(a):
    page, it = _item(a.ref)
    g = it.gates.setdefault(a.stage, {"qa": "pending", "caio": "pending"})
    g["caio"] = "rejected" if a.reject else "approved"
    g["caio_notes"] = a.notes
    if a.reject and a.notes:
        _log_failure(it, a.stage, f"(Caio) {a.notes}")
    it.save()
    print(f"{a.stage}: {g['caio']}")


def cmd_retry(a):
    page, it = _item(a.ref)
    prev = {"storyboard": "roteiro", "frames": "storyboard", "video": "frames"}[a.stage]
    _need_state(it, {"storyboard": ["storyboard"], "frames": ["frames"], "video": ["video", "revisao"]}[a.stage],
                f"retry {a.stage}", a.force)
    it.gates[a.stage] = {"qa": "pending", "caio": "pending"}
    _clear_assets(it, a.stage)
    if a.stage == "video":
        it.video = {"history": it.video.get("history", []) + [{k: v for k, v in it.video.items() if k != "history"}]}
    it.set_state(prev, f"refazer {a.stage}")
    it.save()
    print(f"voltou para {prev}")


def cmd_discard(a):
    page, it = _item(a.ref)
    if it.state == "descartado":
        print("já descartado")
        return
    if it.state == "postado":
        raise StoreError("item já postado: não se descarta (a automação nunca apaga posts, ata D8)")
    it.set_state("descartado", a.why)
    it.save()
    print("descartado")


def cmd_video_request(a):
    page, it = _item(a.ref)
    _need_state(it, ["frames"], "video-request")
    if not _switches().get("video_enabled", False):
        raise StoreError("vídeo desligado em budget.yaml (switches.video_enabled)")
    s = it.script
    b = budget.load_budget()
    est = float(s.get("duration_s", 10)) * b["cost_estimates"]["higgsfield_credits"]["seedance_2_5_720p_per_s"]
    ok, why = budget.can_spend("higgsfield", est * float(b.get("higgsfield_credit_usd", 0.05)))
    if not ok:
        raise StoreError(why)
    need_upload, medias = [], []
    for key, role in (("start", "start_image"), ("end", "end_image")):
        f = it.frames.get(key)
        if not f:
            continue
        if f.get("higgsfield_id"):
            medias.append({"role": role, "value": f["higgsfield_id"]})
        else:
            need_upload.append({"key": key, "path": f.get("path")})
    ref_ids = _hf_ref_ids(page)
    if len(ref_ids) < 2:
        raise StoreError(f"{page.slug}: precisa de higgsfield_id para face e silhouette no page.yaml")
    medias += [{"role": "image_references", "value": i} for i in ref_ids]  # @Image 1 rosto, @Image 2 silhueta
    has_sb = False
    use_grid = not a.no_grid
    if it.storyboard and use_grid:
        if it.storyboard.get("higgsfield_id"):
            medias.append({"role": "image_references", "value": it.storyboard["higgsfield_id"]})  # @Image 3
            has_sb = True
        else:
            need_upload.append({"key": "storyboard", "path": it.storyboard.get("path")})
    if need_upload:
        _print({"ready": False, "upload_first": need_upload,
                "how": ("Para cada arquivo: mcp__Higgsfield__media_upload(filename=<nome.png>) -> "
                        "curl -X PUT -H 'Content-Type: image/png' --data-binary @<arquivo> '<upload_url>' -> "
                        "mcp__Higgsfield__media_confirm(media_id=..., type='image') -> "
                        f"`python -m pipeline record-upload {a.ref} <key> --hf-id <media_id>`. Depois rode video-request de novo. "
                        "Se o PUT for bloqueado pela rede, refaça a etapa com `image ... --provider higgsfield` "
                        "(o mesmo modelo GPT Image, já hospedado no Higgsfield).")})
        return
    has_start = any(m["role"] == "start_image" for m in medias)
    has_end = any(m["role"] == "end_image" for m in medias)
    prompt = prompts.video_prompt(s, page, has_start=has_start, has_end=has_end, has_storyboard=has_sb, repair=a.repair)
    (_workdir(it) / f"video-v{it.attempts.get('video', 0) + 1}.prompt.txt").write_text(prompt, encoding="utf-8")
    res = "720p" if budget.degraded_mode() else str(page.data.get("video_resolution", "720p"))
    _print({
        "ready": True,
        "mcp_tool": "mcp__Higgsfield__generate_video_batch",
        "requests": [{"index": 0, "params": {
            "model": "seedance_2_5", "mode": "omni_reference", "aspect_ratio": "9:16",
            "duration": int(s.get("duration_s", 10)), "resolution": a.resolution or res, "generate_audio": False,
            "medias": medias, "prompt": prompt}}],
        "note": "Se a resposta recomendar um preset, reenvie com declined_preset_id.",
        "then": f"python -m pipeline record-video {a.ref} --job <job_id> --credits <créditos>",
    })


def cmd_record_video(a):
    page, it = _item(a.ref)
    if a.failed is not None:
        # job do Higgsfield falhou (failed/nsfw/cancelado): sem isso o item ficaria preso em video_poll para sempre
        _need_state(it, ["video"], "record-video --failed")
        it.video = {"history": it.video.get("history", []) + [{**{k: v for k, v in it.video.items() if k != "history"},
                                                                 "failed": a.failed or "falhou"}]}
        it.gates["video"] = {"qa": "pending", "caio": "pending"}
        budget.record(it.page, it.id, "higgsfield", "video_failed", ok=False, note=(a.failed or "")[:200],
                      job_id=(it.video["history"][-1].get("job_id") or ""))
        _log_failure(it, "video", f"job falhou: {a.failed or 'sem motivo'}")
        it.set_state("frames", "job de vídeo falhou")
        it.save()
        print("falha registrada; volta para frames (conta como tentativa)")
        return
    if a.job:
        known = [it.video.get("job_id")] + [h.get("job_id") for h in it.video.get("history", [])]
        if a.job in known:
            print(f"job {a.job} já registrado (não conta de novo)")
            a.job = None
    if a.job:
        _need_state(it, ["frames"], "record-video --job")
        it.attempts["video"] = it.attempts.get("video", 0) + 1
        it.video.update({"job_id": a.job, "provider": "higgsfield", "model": "seedance_2_5", "submitted_at": time.time()})
        it.gates["video"] = {"qa": "pending", "caio": "pending"}
        if it.state != "video":
            it.set_state("video", f"vídeo v{it.attempts['video']} enviado")
        credits = a.credits if a.credits is not None else \
            float(it.script.get("duration_s", 10)) * budget.load_budget()["cost_estimates"]["higgsfield_credits"]["seedance_2_5_720p_per_s"]
        budget.record(it.page, it.id, "higgsfield", "video_submit", credits=credits, job_id=a.job)
    if a.url:
        if not it.video.get("job_id"):
            raise StoreError("registre o job antes (--job)")
        it.video["url"] = a.url
    it.save()
    print("registrado")


def _download(url: str, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["curl", "-sSfL", "--max-time", "180", "-o", str(dst), url], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"download falhou ({r.stderr.strip()[:200]}). Libere o domínio na rede do ambiente "
              f"ou baixe à mão e use --file.", file=sys.stderr)
        return False
    return True


def cmd_fetch_video(a):
    page, it = _item(a.ref)
    _need_state(it, ["video"], "fetch-video")
    wd = _workdir(it)
    v = it.attempts.get("video", 1)
    dst = wd / f"video-v{v}.mp4"
    if a.file:
        shutil.copy(a.file, dst)
    elif not _download(it.video.get("url", ""), dst):
        sys.exit(2)
    info = media.probe(dst)
    sheet = media.sheet_window(dst, wd / f"video-v{v}-sheet.jpg", 0, info["duration"], fps=2)
    stages = it.script.get("en", {}).get("stages", [])
    gag = None
    if len(stages) >= 3:
        sp = lintmod._span(stages[-2]["t"])
        if sp:
            gag = media.sheet_window(dst, wd / f"video-v{v}-gag.jpg", sp[0], min(sp[1] + 0.5, info["duration"]), fps=6)
    last = media.last_frame(dst, wd / f"video-v{v}-last.jpg")
    cuts = media.detect_cuts(dst)
    it.video.update({"path": rel(dst), "sheet": rel(sheet), "gag_sheet": rel(gag) if gag else "",
                     "last": rel(last), "info": info, "cuts": cuts})
    if not info.get("acodec"):
        print("sem trilha de áudio (esperado: generate_audio false; a música entra no app)")
    it.save()
    print(f"ok: {dst.relative_to(ROOT)}  {info}")
    print(f"cortes detectados: {cuts or 'nenhum'}")
    print(f"revisar: {sheet.relative_to(ROOT)}, {gag.relative_to(ROOT) if gag else '-'} e {last.relative_to(ROOT)}")


def cmd_package(a):
    page, it = _item(a.ref)
    _need_state(it, ["revisao", "pronto"], "package")
    if it.gates.get("video", {}).get("caio") != "approved":
        raise StoreError("o Caio ainda não aprovou o vídeo (portão obrigatório, ata D3)")
    src = local(it.video.get("path"))
    if not src or not src.exists():
        raise StoreError("vídeo local não encontrado; rode fetch-video")
    pk = OUT / "packages" / it.page / it.id
    pk.mkdir(parents=True, exist_ok=True)
    mp4 = media.normalize_reels(src, pk / f"{it.page}-{it.id}.mp4")
    cover = local(it.video.get("last"))
    if not cover or not cover.exists():
        cover = media.last_frame(mp4, pk / "_last.jpg")
    shutil.copy(cover, pk / "capa.jpg")
    h = media.video_hash(mp4, pk)
    for f in pk.glob("_h*.jpg"):
        f.unlink()
    dup = _find_duplicate(h, it)
    (pk / "legenda.txt").write_text(it.post.get("caption") or prompts.caption(it.script), encoding="utf-8")
    music = it.script.get("music") or {}
    handle = page.character.get("handle") or page.slug
    bpm = music.get("bpm") or page.character.get("bpm") or "?"
    hints = music.get("trend_sound_hints") or [music.get("trend_sound_hint")]
    hints = [h for h in hints if h][:3] or ["procure no app um som em alta do estilo acima"]
    (pk / "CHECKLIST.md").write_text("\n".join([
        f"# Postar: {it.script.get('title')} ({handle})",
        "",
        f"- [ ] Conta certa: {handle} (nunca postar este arquivo em outra página)",
        f"- [ ] Som em alta: estilo {music.get('genre') or page.character.get('dance_style', '')} ~{bpm} BPM. Sugestões:",
        *[f"      {i}. {h}" for i, h in enumerate(hints, 1)],
        f"      Sem som em alta? Use: {music.get('fallback') or 'instrumental royalty-free no mesmo BPM'}",
        "- [ ] Ativar 'AI info' (rótulo de IA) no post e conferir 'AI-generated profile' na conta",
        "- [ ] Postar o MP4 deste pacote como está (não reexportar: preserva os metadados de IA/C2PA)",
        f"- [ ] Capa: capa.jpg; texto: \"{it.script.get('cover', {}).get('text_max4', '')}\"",
        "- [ ] Legenda: copiar de legenda.txt",
        f"- [ ] Horário sugerido (BRT): {', '.join(page.data.get('cadence', {}).get('post_times_brt', []))}",
        f"- [ ] Depois de postar: `python -m pipeline posted {it.page}/{it.id} --link <url>`",
        "",
        f"Duplicado? {'SIM, NÃO POSTE: ' + dup if dup else 'não'}",
    ]), encoding="utf-8")
    it.post.update({"package": rel(pk), "hash": h, "duplicate_of": dup})
    if it.state != "pronto":
        it.set_state("pronto", "pacote montado")
    it.save()
    print(f"pacote: {pk.relative_to(ROOT)}{'  ATENÇÃO duplicado de ' + dup if dup else ''}")


def _find_duplicate(h: str, me) -> str:
    for other in list_items():
        oh = other.post.get("hash")
        if other.id != me.id and oh and media.hamming(h, oh) <= 12:
            return f"{other.page}/{other.id}"
    return ""


def cmd_posted(a):
    page, it = _item(a.ref)
    _need_state(it, ["pronto"], "posted")
    if it.post.get("duplicate_of"):
        print(f"ATENÇÃO: o pacote estava marcado como duplicado de {it.post['duplicate_of']} (ata D8)", file=sys.stderr)
    it.post.update({"posted_at": time.time(), "link": a.link or ""})
    it.set_state("postado", "postado pelo Caio")
    it.save()
    print("postado")


def cmd_fetch_refs(a):
    page = get_page(a.page)
    for r in page.data.get("refs", []):
        dst = page.dir / r["file"]
        if dst.exists():
            print(f"já existe: {dst.name}")
            continue
        if r.get("url") and _download(r["url"], dst):
            print(f"baixado: {dst.name}")


def cmd_sheet(a):
    """Ficha do personagem (playbook C1): 2x2 com UM rosto legível. Depois: split-sheet."""
    page = get_page(a.page)
    prompt = prompts.character_sheet_prompt(page)
    wd = page.dir / "refs"
    wd.mkdir(parents=True, exist_ok=True)
    n = len(list(wd.glob("ficha-v*.png"))) + 1
    out = wd / f"ficha-v{n}.png"
    (wd / f"ficha-v{n}.prompt.txt").write_text(prompt, encoding="utf-8")
    provider = a.provider or _switches().get("image_provider", "openai")
    _check_image_provider(provider)
    if provider == "higgsfield":
        ids = _hf_ref_ids(page)[:1]
        _print({"mcp_tool": "mcp__Higgsfield__generate_image", "params": {
            "model": "gpt_image_2_5", "aspect_ratio": "2:3", "quality": "high",
            "medias": [{"role": "image_references", "value": i} for i in ids], "prompt": prompt},
            "then": f"baixe o resultado para {out.relative_to(ROOT)} e rode split-sheet"})
        return
    mock = bool(a.mock) or os.getenv("USINA_MOCK") == "1"
    existing = [p for p in page.available_refs() if "rosto" in p.name or "close" in p.name][:1]
    unit = budget.load_budget()["cost_estimates"]["openai_image"]["high"]
    ok, why = budget.can_spend("openai", unit)
    if not ok and not mock:
        raise StoreError(why)
    images.generate(prompt, out, existing, aspect="1024x1536", quality="high", mock=mock)
    budget.record(page.slug, "ficha", "openai", "image_sheet", usd=0 if mock else unit)
    print(f"ficha: {out.relative_to(ROOT)} — aprove e rode `python -m pipeline split-sheet {page.slug} {out.relative_to(ROOT)}`")


def cmd_split_sheet(a):
    """Recorta a ficha 2x2 em rosto.png (painel superior esquerdo) e silhueta.png (os outros 3 lado a lado)."""
    from PIL import Image
    page = get_page(a.page)
    im = Image.open(ROOT / a.file if not Path(a.file).is_absolute() else a.file).convert("RGB")
    w, h = im.size
    q = [im.crop((0, 0, w // 2, h // 2)), im.crop((w // 2, 0, w, h // 2)),
         im.crop((0, h // 2, w // 2, h)), im.crop((w // 2, h // 2, w, h))]
    refs = page.dir / "refs"
    q[0].save(refs / "rosto.png")
    pw, ph = q[1].size
    sil = Image.new("RGB", (pw * 3 + 16, ph), (138, 138, 138))
    for i, panel in enumerate(q[1:]):
        sil.paste(panel, (i * (pw + 8), 0))
    sil.save(refs / "silhueta.png")
    print(f"ok: {refs.relative_to(ROOT)}/rosto.png e silhueta.png. Atualize refs no page.yaml (role face/silhouette), "
          f"suba as duas no Higgsfield e grave os higgsfield_id.")


def _panel_doc(it, page) -> dict:
    s = it.script or {}
    return {
        "page": it.page, "itemId": it.id, "ref": f"{it.page}/{it.id}", "state": it.state,
        "title": s.get("title") or it.idea.get("title", it.id), "premise": s.get("premise") or it.idea.get("text", ""),
        "gag": s.get("gag_without_sound", ""), "duration": s.get("duration_s"), "format": s.get("format", ""),
        "gates": it.gates, "attempts": it.attempts, "assets": it.post.get("assets", {}),
        "caption": it.post.get("caption", ""), "cover_text": s.get("cover", {}).get("text_max4", ""),
        "music": s.get("music", {}), "videoUrl": it.video.get("url", ""), "cuts": it.video.get("cuts", []),
        "package": it.post.get("package", ""), "handle": page.character.get("handle", ""),
        "updatedAt": int(it.updated_at * 1000), "createdAt": int(it.created_at * 1000),
    }


def cmd_panel_export(a):
    """Gera os documentos do painel (coleções fila, paginas, saude) para a sessão gravar com ArtifactData batch.

    Itens descartados também vão (com o estado novo): se ficassem de fora, o painel guardaria o estado antigo e a
    Caixa mostraria para sempre um card de aprovação de um item que já morreu.
    """
    from .tick import plan as mkplan
    writes = []
    pages = {p.slug: p for p in load_pages()}
    for it in list_items():
        page = pages.get(it.page)
        if page is None:
            print(f"aviso: item {it.page}/{it.id} sem pages/{it.page}/page.yaml; ignorado", file=sys.stderr)
            continue
        writes.append({"op": "set", "collection": "fila", "doc_id": f"{it.page}--{it.id}",
                       "data": _panel_doc(it, page)})
    for slug, p in pages.items():
        ch = p.character
        writes.append({"op": "set", "collection": "paginas", "doc_id": slug, "data": {
            "slug": slug, "status": p.data.get("status"), "name": ch.get("name"), "handle": ch.get("handle"),
            "silhouette": ch.get("silhouette_letter"), "bpm": ch.get("bpm"), "dance": ch.get("dance_style"),
            "world": ch.get("world"), "gag": ch.get("recurring_gag"), "relationship": ch.get("relationship"),
            "signature": ch.get("signature_move"), "cadence": p.data.get("cadence", {}),
            "refsReady": len(p.available_refs()) >= 2, "launchedAt": str(p.data.get("launched_at", "") or "")}})
    pl = mkplan()
    writes.append({"op": "set", "collection": "saude", "doc_id": "atual", "data": {
        "at": int(time.time() * 1000), "paused": pl["paused"] or "", "spend": pl["spend"], "notes": pl["notes"],
        "actions": len(pl["actions"]), "waiting": [w["item"] + " · " + w["stage"] for w in pl["waiting_caio"]],
        "ledger": budget.rows()[-15:]}})
    out = OUT / "panel" / "batch.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    for old in out.parent.glob("batch-*.json"):
        old.unlink()
    out.write_text(json.dumps(writes, ensure_ascii=False, indent=2), encoding="utf-8")
    chunks = [writes[i:i + 50] for i in range(0, len(writes), 50)]
    for n, ch in enumerate(chunks, 1):  # ArtifactData batch aceita até 50 escritas por chamada
        (out.parent / f"batch-{n:02d}.json").write_text(json.dumps(ch, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(writes)} documentos em {out.relative_to(ROOT)} ({len(chunks)} lote(s) de até 50: "
          f"out/panel/batch-NN.json; documentos já existentes precisam do if_version lido antes)")


MEDIA_KEYS = ("storyboard", "start", "end", "video", "sheet", "gag", "last")


def _media_paths(it) -> dict:
    """Arquivos de mídia que o item usa hoje (chave -> caminho relativo)."""
    out = {}
    if it.storyboard.get("path"):
        out["storyboard"] = it.storyboard["path"]
    for k in ("start", "end"):
        if (it.frames.get(k) or {}).get("path"):
            out[k] = it.frames[k]["path"]
    v = it.video or {}
    for k, f in (("video", "path"), ("sheet", "sheet"), ("gag", "gag_sheet"), ("last", "last")):
        if v.get(f):
            out[k] = v[f]
    return {k: rel(p) for k, p in out.items()}


def cmd_panel_asset(a):
    """Grava o asset do painel (subido com Artifact asset:true) no item: serve à Caixa E de arquivo permanente.

    O id em /_blob/<id> fica em item.post.media[key] junto do caminho local, para `media-status` restaurar
    o arquivo numa sessão nova (out/ não vai para o git).
    """
    page, it = _item(a.ref)
    it.post.setdefault("assets", {})[a.key] = a.url
    m = re.search(r"/_blob/([0-9a-f]{32})", a.url or "")
    if m:
        path = _media_paths(it).get(a.key, "")
        it.post.setdefault("media", {})[a.key] = {"asset": m.group(1), "path": path}
    it.save()
    print("ok")


def cmd_media_status(a):
    """O que subir (existe local, sem asset) e o que restaurar (sumiu do disco, tem asset) para os itens ativos."""
    upload, restore = [], []
    for it in list_items():
        if a.ref and f"{it.page}/{it.id}" != a.ref:
            continue
        if it.state in ("descartado", "postado") and not a.ref:
            continue
        media = it.post.get("media", {})
        for key, path in _media_paths(it).items():
            rec = media.get(key) or {}
            exists = local(path).exists()
            if exists and rec.get("path") != path:
                upload.append({"ref": f"{it.page}/{it.id}", "key": key, "file": str(local(path))})
            elif not exists and rec.get("asset") and rec.get("path") == path:
                restore.append({"ref": f"{it.page}/{it.id}", "key": key, "asset_id": rec["asset"], "to": path})
    _print({"upload": upload, "restore": restore,
            "how_upload": "Artifact(url=<painel>, asset=true, file_paths=[...]) e depois "
                          "`python -m pipeline panel-asset <ref> <key> /_blob/<id>` para cada arquivo",
            "how_restore": "Artifact(action='read', url=<painel>, path=<asset_id>) e depois "
                           "`python -m pipeline media-restore <ref> <key> --file <arquivo salvo>`"})


def cmd_media_restore(a):
    page, it = _item(a.ref)
    path = _media_paths(it).get(a.key)
    if not path:
        raise StoreError(f"{a.ref} não usa mídia '{a.key}'")
    dst = local(path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(a.file, dst)
    print(f"restaurado: {path}")


def _decision_rows(raw) -> list:
    """Aceita a saída do ArtifactData list em vários formatos: lista, {documents|docs|items|rows|results: [...]}."""
    if isinstance(raw, dict):
        for k in ("documents", "docs", "items", "rows", "results", "data"):
            if isinstance(raw.get(k), list):
                return raw[k]
        return [dict(v, id=k) if isinstance(v, dict) else v for k, v in raw.items()]  # {doc_id: {...}}
    return raw if isinstance(raw, list) else []


def cmd_panel_apply(a):
    """Aplica as decisões do Caio vindas do painel (coleção decisoes, exportada para JSON).

    Idempotente: o id de cada decisão aplicada fica no item, então rodar de novo (ou esquecer de marcar
    applied no painel) não aplica duas vezes. Decisão mais antiga que a revisão atual da etapa (o item já
    foi refeito) é obsoleta: não mexe no portão novo.
    """
    try:
        raw = json.loads(Path(a.file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise StoreError(f"não consegui ler {a.file}: {e}")
    done, stale, invalid = [], [], []
    for r in _decision_rows(raw):
        if not isinstance(r, dict):
            print(f"ignorado (não é documento): {r!r}"[:200])
            continue
        d = r.get("data") if isinstance(r.get("data"), dict) else r
        did = r.get("doc_id") or r.get("id") or r.get("_id") or d.get("id")
        if d.get("applied"):
            continue
        ref, stage, verdict = d.get("ref"), d.get("stage"), d.get("verdict")
        if stage not in ("storyboard", "frames", "video") or verdict not in ("approve", "reject"):
            print(f"inválido: {json.dumps(d, ensure_ascii=False)[:200]}")
            if did:
                invalid.append(did)
            continue
        try:
            page, it = _item(ref)
        except StoreError as e:
            print(f"inválido ({e})")
            if did:
                invalid.append(did)
            continue
        if did and did in it.decisions:
            print(f"{ref} {stage}: decisão {did} já aplicada")
            done.append(did)
            continue
        g = it.gates.setdefault(stage, {"qa": "pending", "caio": "pending"})
        try:
            at = float(d.get("at") or 0) / 1000.0  # o painel grava em ms
        except (TypeError, ValueError):
            at = 0.0
        if at and g.get("qa_at") and at < float(g["qa_at"]):
            print(f"{ref} {stage}: decisão obsoleta (a etapa foi refeita depois); ignorada")
            stale.append(did)
            continue
        g["caio"] = "approved" if verdict == "approve" else "rejected"
        g["caio_notes"] = str(d.get("notes") or "")
        if verdict == "reject" and d.get("notes"):
            _log_failure(it, stage, f"(Caio) {d['notes']}")
        if did:
            it.decisions.append(did)
        it.save()
        done.append(did)
        print(f"{ref} {stage}: {g['caio']}")
    # applied_ids = tudo que pode ser marcado applied no painel (aplicadas, obsoletas e inválidas)
    print(json.dumps({"applied_ids": [i for i in done + stale + invalid if i], "obsolete_ids": [i for i in stale if i],
                      "invalid_ids": invalid}))


def cmd_pause(a):
    budget.PAUSE_FILE.write_text(a.reason or "pausado pelo Caio", encoding="utf-8")
    print("PAUSADO")


def cmd_resume(a):
    if budget.PAUSE_FILE.exists():
        budget.PAUSE_FILE.unlink()
    print("retomado")


def cmd_ledger(a):
    for r in budget.rows()[-30:]:
        print(f"{time.strftime('%m-%d %H:%M', time.gmtime(r['at']))} {r['page']:9} {r['provider']:10} {r['action']:16} "
              f"US$ {r['usd']:.3f} {r['credits'] or '':>6} {r['note']}")


def _log_failure(it, stage: str, notes: str) -> None:
    FAILS.parent.mkdir(parents=True, exist_ok=True)
    if not FAILS.exists():
        FAILS.write_text("# Livro de falhas\n\nCada reprovação vira uma linha. O roteirista lê antes de escrever.\n\n"
                         "| data | página | etapa | item | o que falhou |\n|---|---|---|---|---|\n", encoding="utf-8")
    with FAILS.open("a", encoding="utf-8") as f:
        f.write(f"| {time.strftime('%Y-%m-%d')} | {it.page} | {stage} | {it.id} | {notes.replace('|', '/')} |\n")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m pipeline")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("pages").set_defaults(f=cmd_pages)
    sp.add_parser("status").set_defaults(f=cmd_status)
    sp.add_parser("plan").set_defaults(f=cmd_plan)
    p = sp.add_parser("memory"); p.add_argument("page"); p.set_defaults(f=cmd_memory)
    p = sp.add_parser("new"); p.add_argument("page"); p.add_argument("title"); p.add_argument("--idea", default="")
    p.add_argument("--source", default="pauta"); p.add_argument("--force", action="store_true")
    p.set_defaults(f=cmd_new)
    p = sp.add_parser("lint"); p.add_argument("file"); p.add_argument("--page"); p.set_defaults(f=cmd_lint)
    p = sp.add_parser("save-script"); p.add_argument("ref"); p.add_argument("file")
    p.add_argument("--force", action="store_true", help="reescrever o roteiro de um item já em produção")
    p.set_defaults(f=cmd_save_script)
    p = sp.add_parser("image"); p.add_argument("ref"); p.add_argument("stage", choices=["storyboard", "frames"])
    p.add_argument("--provider", choices=["openai", "higgsfield"], default=os.getenv("USINA_IMAGE_PROVIDER"),
                   help="padrão: switches.image_provider do budget.yaml")
    p.add_argument("--quality", default="high", choices=["low", "medium", "high", "xhigh"])
    p.add_argument("--mock", action="store_true", default=None)
    p.add_argument("--force", action="store_true"); p.add_argument("--sem-storyboard", action="store_true")
    p.set_defaults(f=cmd_image)
    p = sp.add_parser("record-image"); p.add_argument("ref"); p.add_argument("stage"); p.add_argument("key")
    p.add_argument("--hf-job", required=True); p.add_argument("--url"); p.set_defaults(f=cmd_record_image)
    p = sp.add_parser("record-upload"); p.add_argument("ref"); p.add_argument("key")
    p.add_argument("--hf-id", required=True); p.set_defaults(f=cmd_record_upload)
    p = sp.add_parser("review"); p.add_argument("ref"); p.add_argument("stage", choices=["storyboard", "frames", "video"])
    p.add_argument("verdict", choices=["pass", "fail"]); p.add_argument("--notes", default=""); p.set_defaults(f=cmd_review)
    p = sp.add_parser("approve"); p.add_argument("ref"); p.add_argument("stage", choices=["storyboard", "frames", "video"])
    p.add_argument("--reject", action="store_true"); p.add_argument("--notes", default=""); p.set_defaults(f=cmd_approve)
    p = sp.add_parser("retry"); p.add_argument("ref"); p.add_argument("stage", choices=["storyboard", "frames", "video"])
    p.add_argument("--force", action="store_true"); p.set_defaults(f=cmd_retry)
    p = sp.add_parser("discard"); p.add_argument("ref"); p.add_argument("--why", default=""); p.set_defaults(f=cmd_discard)
    p = sp.add_parser("video-request"); p.add_argument("ref")
    p.add_argument("--no-grid", action="store_true", help="sem a grade de storyboard (se o take inventou cortes)")
    p.add_argument("--resolution", choices=["480p", "720p", "1080p"], help="480p = draft de estrutura")
    p.add_argument("--repair", default="", help="REPAIR SCOPE (playbook C6a): o que mudar, uma variável")
    p.set_defaults(f=cmd_video_request)
    p = sp.add_parser("sheet"); p.add_argument("page"); p.add_argument("--mock", action="store_true", default=None)
    p.add_argument("--provider", choices=["openai", "higgsfield"], default=os.getenv("USINA_IMAGE_PROVIDER"))
    p.set_defaults(f=cmd_sheet)
    p = sp.add_parser("split-sheet"); p.add_argument("page"); p.add_argument("file"); p.set_defaults(f=cmd_split_sheet)
    p = sp.add_parser("record-video"); p.add_argument("ref"); p.add_argument("--job"); p.add_argument("--url")
    p.add_argument("--credits", type=float)
    p.add_argument("--failed", nargs="?", const="", default=None, help="o job falhou (motivo opcional)")
    p.set_defaults(f=cmd_record_video)
    p = sp.add_parser("fetch-video"); p.add_argument("ref"); p.add_argument("--file"); p.set_defaults(f=cmd_fetch_video)
    p = sp.add_parser("package"); p.add_argument("ref"); p.set_defaults(f=cmd_package)
    p = sp.add_parser("posted"); p.add_argument("ref"); p.add_argument("--link"); p.set_defaults(f=cmd_posted)
    p = sp.add_parser("fetch-refs"); p.add_argument("page"); p.set_defaults(f=cmd_fetch_refs)
    p = sp.add_parser("panel-export"); p.add_argument("--all", action="store_true", help="(sem efeito: tudo é exportado)"); p.set_defaults(f=cmd_panel_export)
    p = sp.add_parser("panel-asset"); p.add_argument("ref"); p.add_argument("key"); p.add_argument("url")
    p.set_defaults(f=cmd_panel_asset)
    p = sp.add_parser("media-status"); p.add_argument("--ref"); p.set_defaults(f=cmd_media_status)
    p = sp.add_parser("media-restore"); p.add_argument("ref"); p.add_argument("key"); p.add_argument("--file", required=True)
    p.set_defaults(f=cmd_media_restore)
    p = sp.add_parser("panel-apply"); p.add_argument("file"); p.set_defaults(f=cmd_panel_apply)
    p = sp.add_parser("pause"); p.add_argument("reason", nargs="?"); p.set_defaults(f=cmd_pause)
    sp.add_parser("resume").set_defaults(f=cmd_resume)
    sp.add_parser("ledger").set_defaults(f=cmd_ledger)
    a = ap.parse_args(argv)
    try:
        a.f(a)
    except (StoreError, images.ImageError, media.MediaError, json.JSONDecodeError, OSError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
