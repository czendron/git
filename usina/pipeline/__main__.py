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
  image <page/id> frames --variants 4 | pick <page/id> frames <n>     (trend: 4 opções do frame, o revisor escolhe)
  approve <page/id> storyboard|frames|video [--reject] [--notes]
  retry <page/id> storyboard|frames|video | discard <page/id> --why "..."
  video-request <page/id> | record-video <page/id> [--job ...] [--url ...] [--credits n]
  fetch-video <page/id> [--file local.mp4] | package <page/id> | posted <page/id> [--link]
  video-request <ref> --gag | record-video <ref> --gag ... | fetch-video <ref> --gag | review <ref> gag | skip-gag
  motion-source <page/id> --file fonte.mp4 | --hf-id <id>               (trend: vídeo-fonte do motion control)
  media-status [--ref] | media-restore <page/id> <key> --file f | panel-asset <page/id> <key> /_blob/<id> [--path]
  panel-export | panel-apply decisoes.json | placar-import placar.json | cadence-check
  record-error "msg" [--ref] | balance <créditos> | health
  pause "motivo" | resume | ledger
  tick-start [--owner id] | tick-end [--owner id] [--force]      lock do ciclo (TTL 2 h)
  launch-check <page>                                          portão de estreia (ata D6)
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

from . import budget, images, launch, lint as lintmod, lock, media, placar, prompts
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
STALE_ASSETS = {"storyboard": ["storyboard"], "frames": ["start", "end"],
                "video": ["sheet", "gag", "cover", "video", "last", "gag_clip"]}


def _clear_assets(it, *stages: str) -> None:
    assets = it.post.get("assets") or {}
    for st in stages:
        for k in STALE_ASSETS.get(st, []):
            assets.pop(k, None)


def _switches() -> dict:
    return budget.load_budget().get("switches", {}) or {}


def _gen_gate(page) -> None:
    """Ata D6: rascunho nunca gera (nem com --force); ativo só com ficha aprovada e no D+N da estreia."""
    gate = launch.check(page)
    if not gate["can_generate"]:
        raise StoreError(f"{page.slug}: não gera ({gate['summary']}). Veja `launch-check {page.slug}` (ata D6)")


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
        print(f"- [{i.state}] {s.get('title')} | {_place(s)[0] or _place(s)[1][:60]} | {s.get('premise')}")
    if not items:
        print("(sem histórico)")
    page_rows, general = _failures(a.page)
    print(f"\nLivro de falhas (playbook/falhas.md), {a.page}: últimas {len(page_rows[-15:])}")
    for r in page_rows[-15:]:
        print(f"  {r}")
    if not page_rows:
        print("  (nenhuma)")
    print(f"Livro de falhas, gerais: últimas {len(general[-15:])}")
    for r in general[-15:]:
        print(f"  {r}")
    if not general:
        print("  (nenhuma)")


GENERAL = {"geral", "gerais", "todas", "todos", "*", "-", "all", ""}


def _failures(slug: str) -> tuple[list[str], list[str]]:
    """Linhas do livro de falhas da página e as gerais (ata D9.6: o roteirista lê antes de escrever).

    Tabela `| data | página | etapa | item | o que falhou |` (o formato do _log_failure) ou bullets livres
    (o playbook é editado à mão): bullet que cita a página é dela; que cita outra página, não entra; senão é geral.
    """
    if not FAILS.exists():
        return [], []
    slugs = {p.slug for p in load_pages()}
    mine, general = [], []
    for line in FAILS.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if t.startswith("|"):
            cols = [c.strip() for c in t.strip("|").split("|")]
            if len(cols) < 3 or set(cols[0]) <= set("-: ") or cols[0].lower() == "data":
                continue
            who = cols[1].lower()
            row = " | ".join(cols)
            if who == slug:
                mine.append(row)
            elif who in GENERAL or who not in slugs:
                general.append(row)
        elif t.startswith(("- ", "* ")):
            low = t.lower()
            if slug in low:
                mine.append(t[2:])
            elif not any(s in low for s in slugs):
                general.append(t[2:])
    return mine, general


STOP = set("a o as os de da do das dos e em no na nos nas um uma com sem para por ao à the of and in on at to with "
           "an by from its his her their near".split())


def _place(script: dict) -> tuple[str, str]:
    """(lugar em pt, location em en) do roteiro; trend só tem o en."""
    loc = script.get("location")
    pt = loc.get("place") if isinstance(loc, dict) else (loc if isinstance(loc, str) else "")
    en = (script.get("en") or {}).get("location") or ""
    return str(pt or ""), str(en or "")


def _tokens(text: str) -> set:
    return {w for w in slugify(text).split("-") if len(w) > 2 and w not in STOP}


def _same_place(a: str, b: str) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / min(len(ta), len(tb)) >= 0.6


TREND_WEEK_S = 7 * 86400


def _trend_rules(it, script: dict, now: float | None = None) -> tuple[list[str], list[str]]:
    """Ata D7: a mesma trend nunca vai para duas páginas na mesma semana (erro) e no máximo 30% de trend por
    página em 30 dias (aviso; o plan já não sugere trend acima do teto)."""
    from .tick import TREND_CAP, trend_share
    now = now or time.time()
    key = lintmod.trend_key((script.get("trend") or {}).get("name"))
    errors, warns = [], []
    for o in list_items():
        if o.page == it.page or o.state == "descartado" or (o.script or {}).get("format") != "trend":
            continue
        if lintmod.trend_key((o.script.get("trend") or {}).get("name")) != key or not key:
            continue
        recent = now - o.created_at < TREND_WEEK_S or now - float(o.post.get("posted_at") or 0) < TREND_WEEK_S
        if recent:
            errors.append(f"a trend '{script['trend']['name']}' já está em {o.page}/{o.id} nos últimos 7 dias: "
                          f"a mesma trend nunca vai para duas páginas na mesma semana (ata D7)")
    n, t = trend_share(it.page, now, exclude=it.id)
    if (t + 1) / (n + 1) > TREND_CAP:
        warns.append(f"{it.page}: com este, {t + 1} de {n + 1} roteiros em 30 dias são trend "
                     f"({(t + 1) / (n + 1):.0%}), acima do teto de {TREND_CAP:.0%} (ata D7)")
    return errors, warns


def _repeated_place(it, script: dict) -> list[str]:
    """Avisos de cenário repetido contra os últimos 20 itens da página (D9.6: não repetir cenário/lugar)."""
    pt, en = _place(script)
    out = []
    for o in [i for i in list_items(it.page) if i.script and i.id != it.id and i.state != "descartado"][-20:]:
        opt, oen = _place(o.script)
        if (pt and opt and _same_place(pt, opt)) or (not (pt and opt) and en and oen and _same_place(en, oen)):
            out.append(f"cenário repete '{o.script.get('title')}' ({it.page}/{o.id}): {opt or oen[:80]}. "
                       f"Troque o lugar (ata D9.6), salvo se for série de propósito")
    return out


def cmd_new(a):
    page = get_page(a.page)
    if not page.active and not a.force:
        raise StoreError(f"página '{a.page}' está em '{page.data.get('status')}': não gera nada (ata D6). Use --force para testar.")
    gate = launch.check(page)
    if page.active and not gate["can_generate"] and not a.force:
        raise StoreError(f"portão de estreia fechado ({gate['summary']}): `launch-check {a.page}` (ata D6)")
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
    if not errors:
        warns += _repeated_place(it, script)
        if script.get("format") == "trend":
            e, w = _trend_rules(it, script)
            errors += e
            warns += w
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
        it.storyboard, it.frames, it.variants = {}, {}, []
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
    _gen_gate(page)
    nvar = int(getattr(a, "variants", 1) or 1)
    if nvar > 1 and not (stage == "frames" and it.script.get("format") == "trend"):
        raise StoreError("--variants só vale para o frame da trend (playbook C5)")
    if not 1 <= nvar <= 4:
        raise StoreError("--variants vai de 1 a 4")
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
        trend_frames = stage == "frames" and it.script.get("format") == "trend"
        _need_state(it, ["roteiro"] if stage == "storyboard" or trend_frames else ["storyboard"], f"image {stage}", a.force)
    n = it.attempts.get(stage, 0) + (0 if hf_second else 1)
    jobs = []
    if stage == "storyboard":
        prompt, size = prompts.storyboard_prompt(it.script, page)
        jobs.append(("storyboard", prompt, size, []))
    elif stage == "frames" and it.script.get("format") == "trend":
        first = local((it.motion or {}).get("first_frame"))
        if not first or not first.exists():
            raise StoreError("trend sem o 1º frame da fonte: rode `motion-source <ref> --file fonte.mp4` antes")
        jobs.append(("start", prompts.motion_frame_prompt(it.script, page), "1024x1536", ["__SOURCE_FIRST__"]))
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
        n_req = nvar if stage == "frames" else len(jobs)
        ok, why = budget.can_spend_higgsfield(
            n_req * b["cost_estimates"]["higgsfield_credits"].get("gpt_image_2_5", 2))
        if not ok:
            raise StoreError(why)
        trend_first = None
        if stage == "frames" and it.script.get("format") == "trend":
            trend_first = (it.motion or {}).get("first_frame_hf_id")
            if not trend_first:  # o prompt edita o 1º frame da fonte: sem ele como image 1, o rosto vira a "fonte"
                _print({"ready": False, "upload_first": [{"key": "source_first", "path": it.motion.get("first_frame"),
                                                           "type": "image"}],
                        "how": "media_upload + PUT + media_confirm(type='image') e depois "
                               f"`python -m pipeline record-upload {a.ref} source_first --hf-id <id>`; rode de novo."})
                return
        reqs = []
        for key, prompt, size, extra in jobs:
            if hf_second and key != "end":
                continue
            if not hf_second and key == "end":
                continue  # o frame B sai no 2º passo, com o id do frame A
            medias = [{"role": "image_references", "value": i} for i in ids]
            if key == "end":  # image 1 = frame A, image 2 = rosto, image 3 = silhueta (playbook C2)
                medias = [{"role": "image_references", "value": it.frames["start"]["higgsfield_id"]}] + medias
            elif trend_first:  # image 1 = 1º frame da fonte, depois rosto e silhueta (videos-analisados §2)
                medias = [{"role": "image_references", "value": trend_first}] + medias
            elif stage == "frames" and it.storyboard.get("higgsfield_id"):
                medias.append({"role": "image_references", "value": it.storyboard["higgsfield_id"]})
            params = {"model": "gpt_image_2_5", "aspect_ratio": "16:9" if size == "1536x1024" else "9:16",
                      "quality": "high", "medias": medias, "prompt": prompt}
            if nvar > 1:  # trend: N opções do frame, o revisor escolhe com `pick`
                reqs += [{"key": f"var{k}", "params": params} for k in range(1, nvar + 1)]
            else:
                reqs.append({"key": key, "params": params})
        out = {"mcp_tool": "mcp__Higgsfield__generate_image_batch",
               "requests": [{"index": i, "params": r["params"]} for i, r in enumerate(reqs)],
               "then": [f"python -m pipeline record-image {a.ref} {stage} {r['key']} --hf-job <job_id> --url <result_url>"
                        for r in reqs]}
        if nvar > 1:
            out["depois"] = f"Depois dos record-image, escolha a melhor com `python -m pipeline pick {a.ref} frames <n>`."
        if stage == "frames" and not hf_second and len(jobs) > 1:
            out["depois"] = (f"Frame B é edição do frame A: depois do record-image do start, rode de novo "
                             f"`python -m pipeline image {a.ref} frames --provider higgsfield` para o pedido do end.")
        _print(out)
        return

    ok, why = budget.can_spend("openai", unit * len(jobs) * nvar)
    if not ok:
        raise StoreError(why)
    mock = bool(a.mock) or os.getenv("USINA_MOCK") == "1"
    refs = _refs(page)
    target = {}
    variants = []
    for key, prompt, size, extra in jobs:
        name = key if key == stage else f"{stage}-{key}"
        out = wd / f"{name}-v{n}.png"
        (wd / f"{name}-v{n}.prompt.txt").write_text(prompt, encoding="utf-8")
        if extra == ["__SOURCE_FIRST__"]:  # image 1 = 1º frame da fonte, depois rosto e silhueta
            img_refs = [local(it.motion["first_frame"])] + refs
        elif extra == ["__FRAME_A__"]:
            img_refs = [local(target["start"]["path"])] + refs   # Frame B = edição do Frame A (playbook C2)
        else:
            img_refs = refs + extra
        if nvar > 1:
            outs = [wd / f"{name}-v{n}-o{k}.png" for k in range(1, nvar + 1)]
            images.generate_variants(prompt, outs, img_refs, aspect=size, quality=quality, mock=mock)
            for k, o in enumerate(outs, 1):
                budget.record(it.page, it.id, "openai", f"image_{stage}", usd=0 if mock else unit,
                              note=f"{key} opção {k}{' (mock)' if mock else ''}")
                variants.append({"n": k, "path": rel(o), "prompt": prompt, "v": n})
                print(f"ok: {o.relative_to(ROOT)}")
            continue
        images.generate(prompt, out, img_refs, aspect=size, quality=quality, mock=mock)
        budget.record(it.page, it.id, "openai", f"image_{stage}", usd=0 if mock else unit,
                      note=f"{key}{' (mock)' if mock else ''}")
        target[key] = {"path": rel(out), "prompt": prompt, "v": n}
        print(f"ok: {out.relative_to(ROOT)}")
    if variants:
        print(f"{len(variants)} opções: abra todas com Read e escolha com `python -m pipeline pick {a.ref} frames <n>`")
    it.variants = variants if stage == "frames" else it.variants
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
    var = re.fullmatch(r"var([1-4])", a.key or "")
    if a.stage not in ("storyboard", "frames") or (a.stage == "frames" and a.key not in ("start", "end") and not var) \
            or (a.stage == "storyboard" and a.key != "storyboard"):
        raise StoreError("use: record-image <ref> storyboard storyboard | frames start|end|var1..var4")
    if var and it.script.get("format") != "trend":
        raise StoreError("variações (varN) só no frame da trend")
    seen = [it.storyboard] + list(it.frames.values()) + list(it.variants)
    if any(e.get("higgsfield_job") == a.hf_job for e in seen):
        print(f"já registrado: {a.hf_job}")
        return
    # Mesma rodada? (frames: start e end chegam em dois record-image; a tentativa só conta uma vez)
    same_round = it.state == a.stage and it.gates.get(a.stage, {}).get("qa") == "pending"
    if a.stage == "storyboard":
        same_round = False
    elif not same_round:  # trend não tem storyboard: o frame sai direto do roteiro (edição do 1º frame da fonte)
        _need_state(it, ["roteiro"] if it.script.get("format") == "trend" else ["storyboard"], "record-image frames")
    if a.stage == "storyboard":
        _need_state(it, ["roteiro"], "record-image storyboard")
    v = it.attempts.get(a.stage, 0) + (0 if same_round else 1)
    entry = {"higgsfield_job": a.hf_job, "higgsfield_id": a.hf_job, "url": a.url or "", "v": v}
    if a.url:
        name = "storyboard" if a.stage == "storyboard" else f"frames-{a.key}"
        dst = _workdir(it) / (f"frames-start-v{v}-o{var.group(1)}.png" if var else f"{name}-v{v}.png")
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
            it.variants = []
            _clear_assets(it, "frames")
            it.gates["frames"] = {"qa": "pending", "caio": "pending"}
            it.set_state("frames", "frames via Higgsfield")
        if var:
            it.variants = [x for x in it.variants if x.get("n") != int(var.group(1))] + [
                {**entry, "n": int(var.group(1))}]
        else:
            it.frames[a.key] = entry
    budget.record(it.page, it.id, "higgsfield", f"image_{a.stage}", credits=2, job_id=a.hf_job, note=a.key)
    it.save()
    print("registrado")


def cmd_record_upload(a):
    page, it = _item(a.ref)
    if a.key == "source_first":
        if not (it.motion or {}).get("first_frame"):
            raise StoreError("trend sem fonte registrada: rode motion-source --file antes")
        it.motion["first_frame_hf_id"] = a.hf_id
    elif a.key == "source":
        raise StoreError("o vídeo-fonte se registra com `motion-source <ref> --hf-id <id>`")
    elif a.key == "last":
        if not it.video.get("last"):
            raise StoreError("item sem último frame de vídeo (rode fetch-video antes)")
        it.video["last_hf_id"] = a.hf_id
    elif a.key == "storyboard":
        if not it.storyboard:
            raise StoreError("item sem storyboard para associar ao upload")
        it.storyboard["higgsfield_id"] = a.hf_id
    elif a.key in ("start", "end"):
        if not it.frames.get(a.key):  # senão nasceria um frame "fantasma" só com id (ex.: end num roteiro sem end)
            raise StoreError(f"item sem frame '{a.key}' gerado; nada para associar ao upload")
        it.frames[a.key]["higgsfield_id"] = a.hf_id
    else:
        raise StoreError("key deve ser storyboard, start, end, source_first ou last")
    it.save()
    print("registrado")


def cmd_review(a):
    page, it = _item(a.ref)
    if a.stage == "gag":
        return _review_gag(a, it)
    _need_state(it, [a.stage], f"review {a.stage}")
    if a.stage == "video" and not it.video.get("path"):
        raise StoreError("vídeo ainda não baixado: rode fetch-video antes de revisar")
    if a.stage == "frames" and a.verdict == "pass" and it.variants and not it.frames.get("start"):
        raise StoreError(f"escolha a opção antes: `pick {a.ref} frames <n>` (ou reprove todas com fail)")
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


def _review_gag(a, it):
    _need_state(it, ["revisao"], "review gag")
    gag = it.video.get("gag") or {}
    if not gag.get("path"):
        raise StoreError("gag ainda não baixado: `fetch-video <ref> --gag`")
    g = it.gates.setdefault("gag", {"qa": "pending", "caio": "skip"})
    first = g.get("qa") == "pending"
    g.update({"qa": a.verdict, "qa_notes": a.notes, "qa_at": time.time()})
    if a.verdict == "fail" and first:
        _log_failure(it, "gag", a.notes or "gag reprovado")
        if it.attempts.get("gag", 0) >= GAG_MAX_ATTEMPTS:
            it.video["gag"] = {**gag, "dropped": f"reprovado {GAG_MAX_ATTEMPTS}x"}
            print(f"gag reprovado {GAG_MAX_ATTEMPTS}x: descartado, o pacote sai só com o motion control")
    it.save()
    print(f"gag: {a.verdict}")


def cmd_pick(a):
    """Escolhe uma das opções do frame da trend (playbook C5: 4 variações, o revisor cura)."""
    page, it = _item(a.ref)
    _need_state(it, ["frames"], "pick")
    if it.gates.get("frames", {}).get("qa") != "pending":
        raise StoreError("o frame já foi revisado; para trocar a opção, `retry` e gere de novo")
    opt = next((x for x in it.variants if int(x.get("n", 0)) == a.n), None)
    if not opt:
        raise StoreError(f"opção {a.n} não existe (há {sorted(x.get('n') for x in it.variants) or 'nenhuma'})")
    if opt.get("path") and not local(opt["path"]).exists() and not opt.get("higgsfield_id"):
        raise StoreError(f"arquivo da opção {a.n} sumiu ({opt['path']}); gere de novo")
    it.frames = {"start": {**{k: v for k, v in opt.items() if k != "n"}, "picked": a.n}}
    _clear_assets(it, "frames")
    it.history.append({"at": time.time(), "from": it.state, "to": it.state, "why": f"opção {a.n} do frame escolhida"})
    it.save()
    print(f"frame: opção {a.n} ({opt.get('path') or opt.get('higgsfield_id')})")


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
    if a.stage == "gag":
        _need_state(it, ["revisao"], "retry gag")
        gag = it.video.get("gag") or {}
        if gag:
            it.video.setdefault("gag_history", []).append(gag)
        it.video["gag"] = {}
        it.gates.pop("gag", None)
        it.post.get("assets", {}).pop("gag_clip", None)
        it.save()
        print("gag limpo: peça de novo com video-request --gag")
        return
    prev = {"storyboard": "roteiro", "frames": "storyboard", "video": "frames"}[a.stage]
    if a.stage == "frames" and it.script.get("format") == "trend":
        prev = "roteiro"  # trend não tem storyboard: o vídeo-fonte faz esse papel
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
    _other_tick()
    _gen_gate(page)
    if a.gag:
        return _video_request_gag(a, page, it)
    _need_state(it, ["frames"], "video-request")
    if not _switches().get("video_enabled", False):
        raise StoreError("vídeo desligado em budget.yaml (switches.video_enabled)")
    s = it.script
    b = budget.load_budget()
    rate_key = "hf_mult_motion_control_per_s" if s.get("format") == "trend" else "seedance_2_5_720p_per_s"
    est = float(s.get("duration_s", 10)) * b["cost_estimates"]["higgsfield_credits"][rate_key]
    if s.get("format") == "trend" and budget.degraded_mode():
        raise StoreError("acima de 80% do teto do mês: Genjutsu/motion control cortado (ata D5)")
    ok, why = budget.can_spend_higgsfield(est)
    if not ok:
        raise StoreError(why)
    cap = b["per_idea"]
    if it.attempts.get("video", 0) >= cap["max_video_attempts"]:
        raise StoreError(f"ideia já usou {cap['max_video_attempts']} tentativas de vídeo (ata D5): descarte")
    spent = budget.item_spend(it.page, it.id)["credits"]
    if spent + est > float(cap.get("max_credits", 1e9)):
        raise StoreError(f"ideia já gastou {spent:.0f} créditos; +{est:.0f} passaria do teto de {cap['max_credits']} (ata D5)")
    if s.get("format") == "trend":
        return _video_request_trend(a, page, it, b)
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


GAG_MAX_ATTEMPTS = 2


def _gag_est(it, b) -> float:
    g = it.script.get("gag_followup") or {}
    return float(g.get("duration_s", 5)) * b["cost_estimates"]["higgsfield_credits"]["seedance_2_5_720p_per_s"]


def _video_request_gag(a, page, it):
    """Gag pós-motion control (playbook C5): Seedance 2.5 de 4–5 s com o último frame do MC como start_image."""
    s = it.script
    if s.get("format") != "trend" or not s.get("gag_followup"):
        raise StoreError("--gag só vale para trend com gag_followup no roteiro")
    _need_state(it, ["revisao"], "video-request --gag (depois do QA do motion control)")
    if it.gates.get("video", {}).get("qa") != "pass":
        raise StoreError("o clipe de motion control ainda não passou no QA")
    if not _switches().get("video_enabled", False):
        raise StoreError("vídeo desligado em budget.yaml (switches.video_enabled)")
    gag = it.video.get("gag") or {}
    if gag.get("dropped"):
        raise StoreError(f"gag descartado ({gag['dropped']})")
    if gag.get("job_id"):
        raise StoreError(f"gag já enviado (job {gag['job_id']}); falhou? `record-video {a.ref} --gag --failed`")
    if it.attempts.get("gag", 0) >= GAG_MAX_ATTEMPTS:
        raise StoreError(f"gag já usou {GAG_MAX_ATTEMPTS} tentativas: `skip-gag {a.ref}` e empacote só o motion control")
    b = budget.load_budget()
    est = _gag_est(it, b)
    ok, why = budget.can_spend_higgsfield(est)
    if not ok:
        raise StoreError(why)
    cap = b["per_idea"]
    spent = budget.item_spend(it.page, it.id)["credits"]
    if spent + est > float(cap.get("max_credits", 1e9)):
        raise StoreError(f"ideia já gastou {spent:.0f} créditos; o gag (+{est:.0f}) passaria do teto de "
                         f"{cap['max_credits']} (ata D5): `skip-gag {a.ref}`")
    ref_ids = _hf_ref_ids(page)
    if len(ref_ids) < 2:
        raise StoreError(f"{page.slug}: precisa de higgsfield_id para face e silhouette no page.yaml")
    if not it.video.get("last_hf_id"):
        _print({"ready": False, "upload_first": [{"key": "last", "path": it.video.get("last"), "type": "image"}],
                "how": "media_upload + PUT + media_confirm(type='image') do último frame do motion control e depois "
                       f"`python -m pipeline record-upload {a.ref} last --hf-id <id>`; rode `video-request --gag` de novo."})
        return
    g = s["gag_followup"]
    prompt = prompts.gag_prompt(s, page)
    (_workdir(it) / f"gag-v{it.attempts.get('gag', 0) + 1}.prompt.txt").write_text(prompt, encoding="utf-8")
    _print({
        "ready": True,
        "mcp_tool": "mcp__Higgsfield__generate_video_batch",
        "requests": [{"index": 0, "params": {
            "model": "seedance_2_5", "mode": "omni_reference", "aspect_ratio": "9:16",
            "duration": int(round(float(g.get("duration_s", 5)))), "resolution": "720p", "generate_audio": False,
            "medias": [{"role": "start_image", "value": it.video["last_hf_id"]}]
                      + [{"role": "image_references", "value": i} for i in ref_ids],
            "prompt": prompt}}],
        "est_credits": est,
        "note": "Se a resposta recomendar um preset, reenvie com declined_preset_id.",
        "then": f"python -m pipeline record-video {a.ref} --gag --job <job_id> --credits <créditos>",
    })


def _record_gag(a, it):
    gag = dict(it.video.get("gag") or {})
    hist = it.video.setdefault("gag_history", [])
    if a.failed is not None:
        if not gag.get("job_id"):
            if hist and hist[-1].get("failed") is not None:
                print("falha do gag já registrada")
                return
            raise StoreError("nenhum gag em andamento")
        hist.append({**gag, "failed": a.failed or "falhou"})
        it.video["gag"] = {}
        it.gates.pop("gag", None)
        budget.record(it.page, it.id, "higgsfield", "video_failed", ok=False, note=f"gag: {a.failed}"[:200],
                      job_id=gag.get("job_id", ""))
        _log_failure(it, "gag", f"job do gag falhou: {a.failed or 'sem motivo'}")
        it.save()
        print("falha do gag registrada")
        return
    if a.job:
        if a.job == gag.get("job_id") or any(h.get("job_id") == a.job for h in hist):
            print(f"job {a.job} já registrado (não conta de novo)")
        else:
            _need_state(it, ["revisao"], "record-video --gag")
            if gag.get("job_id"):
                raise StoreError(f"já há um gag em andamento (job {gag['job_id']})")
            it.attempts["gag"] = it.attempts.get("gag", 0) + 1
            gag = {"job_id": a.job, "model": "seedance_2_5", "submitted_at": time.time()}
            it.gates["gag"] = {"qa": "pending", "caio": "skip"}
            credits = a.credits if a.credits is not None else _gag_est(it, budget.load_budget())
            budget.record(it.page, it.id, "higgsfield", "video_submit", credits=credits, job_id=a.job, note="gag")
    if a.url:
        if not gag.get("job_id"):
            raise StoreError("registre o job do gag antes (--gag --job)")
        gag["url"] = a.url
    it.video["gag"] = gag
    it.save()
    print("registrado (gag)")


def cmd_skip_gag(a):
    page, it = _item(a.ref)
    gag = dict(it.video.get("gag") or {})
    if gag.get("job_id") and not gag.get("path") and not a.force:
        raise StoreError("há um job de gag em andamento; espere o resultado ou use --force")
    it.video["gag"] = {**gag, "dropped": a.why or "sem gag"}
    it.save()
    print("gag descartado: o pacote sai só com o motion control")


def _video_request_trend(a, page, it, b):
    """Motion control (Genjutsu): frame do personagem (edição do 1º frame da fonte) + vídeo-fonte + prompt de cena."""
    s = it.script
    mo = it.motion or {}
    need = []
    f = it.frames.get("start") or {}
    if not f.get("higgsfield_id"):
        need.append({"key": "start", "path": f.get("path"), "type": "image"})
    if not mo.get("source_hf_id"):
        need.append({"key": "source", "path": mo.get("source_path"), "type": "video"})
    if need:
        _print({"ready": False, "upload_first": need,
                "how": ("Imagem: media_upload + PUT + media_confirm(type='image') -> "
                        f"`python -m pipeline record-upload {a.ref} start --hf-id <id>`. Vídeo-fonte: o mesmo com "
                        f"type='video' -> `python -m pipeline motion-source {a.ref} --hf-id <id>`.")})
        return
    # Ficha em toda geração (videos-analisados §5): rosto e silhueta entram depois do frame do personagem, com o papel
    # declarado no prompt (o Genjutsu trata cada imagem como um sujeito; o prompt diz que são o mesmo homem).
    # --no-sheet volta ao pedido só com o frame, para A/B se o modelo duplicar o personagem.
    sheet_ids = [] if getattr(a, "no_sheet", False) else _hf_ref_ids(page)
    if not getattr(a, "no_sheet", False) and len(sheet_ids) < 2:
        raise StoreError(f"{page.slug}: precisa de higgsfield_id para face e silhouette no page.yaml "
                         f"(ou rode com --no-sheet)")
    prompt = prompts.motion_scene_prompt(s, page, with_sheet=bool(sheet_ids))
    (_workdir(it) / f"video-v{it.attempts.get('video', 0) + 1}.prompt.txt").write_text(prompt, encoding="utf-8")
    res = "720p" if budget.degraded_mode() else (a.resolution or str(page.data.get("video_resolution", "720p")))
    _print({
        "ready": True,
        "mcp_tool": "mcp__Higgsfield__generate_video_batch",
        "requests": [{"index": 0, "params": {
            "model": "hf_mult_motion_control", "resolution": res, "prompt": prompt,
            "medias": [{"role": "image_references", "value": f["higgsfield_id"]}]
                      + [{"role": "image_references", "value": i} for i in sheet_ids]
                      + [{"role": "video_references", "value": mo["source_hf_id"]}]}}],
        "note": "Genjutsu: a duração é a da fonte. Se a saída vier mais curta que a fonte, o movimento era rápido demais: "
                "desacelere a fonte para 50-75% e corte de novo (playbook C5).",
        "then": f"python -m pipeline record-video {a.ref} --job <job_id> --credits <créditos>",
    })


def cmd_motion_source(a):
    """Registra o vídeo-fonte de uma trend: arquivo local (extrai o 1º frame) e/ou id no Higgsfield.

    Fonte nova = frames velhos inválidos (o frame do personagem é edição do 1º frame da fonte) e upload velho
    inválido (o id apontaria para a fonte anterior). Por isso: arquivo versionado, id limpo e volta para roteiro.
    """
    page, it = _item(a.ref)
    if it.script.get("format") != "trend":
        raise StoreError("motion-source só vale para roteiro com format 'trend'")
    mo = dict(it.motion or {})
    if a.file:
        if it.state != "roteiro":
            _need_state(it, ["roteiro"], "motion-source --file (fonte nova invalida os frames)", a.force)
        src = Path(a.file)
        info = media.probe(src)
        cuts = media.detect_cuts(src)
        problems = []
        if not 3 <= info["duration"] <= 15:
            problems.append(f"fonte com {info['duration']:.1f}s: corte no trecho da coreografia (3-15 s, ideal 8-10 s)")
        if cuts:
            problems.append(f"a fonte tem cortes em {cuts}: o motion control quer um plano contínuo (playbook C5)")
        if problems and not a.force:
            raise StoreError("; ".join(problems) + " (use --force se for intencional)")
        n = int(mo.get("v", 0)) + 1
        wd = _workdir(it)
        dst = wd / f"source-v{n}{src.suffix or '.mp4'}"
        shutil.copy(src, dst)
        first = media.frame_at(dst, 0.05, wd / f"source-v{n}-first.jpg")
        mo = {"v": n, "source_path": rel(dst), "first_frame": rel(first), "duration": info["duration"],
              "cuts": cuts, "size": [info["width"], info["height"]],
              "history": (mo.get("history") or []) + ([{k: v for k, v in mo.items() if k != "history"}]
                                                     if mo.get("source_path") else [])}
        warns = problems[:] if a.force else []
        if info["duration"] > 12:
            warns.append("fonte longa: o ideal é 8-10 s")
        if info["width"] > info["height"]:
            warns.append("fonte horizontal: prefira 9:16")
        for w in warns:
            print(f"aviso: {w}")
        if it.state != "roteiro":
            it.frames, it.variants = {}, []
            it.gates.pop("frames", None)
            it.gates.pop("video", None)
            _clear_assets(it, "frames", "video")
            it.attempts["frames"] = 0  # frame novo sobre fonte nova: as reprovações da fonte velha não contam
            it.set_state("roteiro", "fonte nova da trend")
        it.script["duration_s"] = round(float(info["duration"]), 1)
    if a.hf_id:
        if not mo.get("source_path") and not a.file and not a.force:
            raise StoreError("registre o arquivo da fonte antes (--file), ou use --force para só o id")
        mo["source_hf_id"] = a.hf_id
    it.motion = mo
    it.save()
    print(f"fonte registrada: {mo.get('source_path', '')} {mo.get('source_hf_id', '')}".strip())


def cmd_record_video(a):
    page, it = _item(a.ref)
    if a.gag:
        return _record_gag(a, it)
    if a.refunded and a.failed is None:
        return _refund(it, a.job or (it.video.get("history") or [{}])[-1].get("job_id"))
    if a.failed is not None:
        # job do Higgsfield falhou (failed/nsfw/cancelado): sem isso o item ficaria preso em video_poll para sempre
        last = (it.video.get("history") or [{}])[-1]
        if it.state != "video" and last.get("failed") is not None and (not a.job or last.get("job_id") == a.job):
            print(f"falha do job {last.get('job_id')} já registrada (não conta de novo)")
            if a.refunded:
                _refund(it, last.get("job_id"))
            return
        _need_state(it, ["video"], "record-video --failed")
        if a.job and it.video.get("job_id") and a.job != it.video.get("job_id"):
            raise StoreError(f"o job atual é {it.video.get('job_id')}, não {a.job}")
        it.video = {"history": it.video.get("history", []) + [{**{k: v for k, v in it.video.items() if k != "history"},
                                                                 "failed": a.failed or "falhou"}]}
        it.gates["video"] = {"qa": "pending", "caio": "pending"}
        budget.record(it.page, it.id, "higgsfield", "video_failed", ok=False, note=(a.failed or "")[:200],
                      job_id=(it.video["history"][-1].get("job_id") or ""))
        _log_failure(it, "video", f"job falhou: {a.failed or 'sem motivo'}")
        it.set_state("frames", "job de vídeo falhou")
        it.save()
        print("falha registrada; volta para frames (conta como tentativa)")
        if a.refunded:
            _refund(it, it.video["history"][-1].get("job_id"))
        return
    if a.job:
        known = [it.video.get("job_id")] + [h.get("job_id") for h in it.video.get("history", [])]
        if a.job in known:
            print(f"job {a.job} já registrado (não conta de novo)")
            a.job = None
    if a.job:
        _need_state(it, ["frames"], "record-video --job")
        it.attempts["video"] = it.attempts.get("video", 0) + 1
        model = "hf_mult_motion_control" if it.script.get("format") == "trend" else "seedance_2_5"
        it.video.update({"job_id": a.job, "provider": "higgsfield", "model": model, "submitted_at": time.time()})
        it.gates["video"] = {"qa": "pending", "caio": "pending"}
        if it.state != "video":
            it.set_state("video", f"vídeo v{it.attempts['video']} enviado")
        credits = a.credits if a.credits is not None else \
            float(it.script.get("duration_s", 10)) * budget.load_budget()["cost_estimates"]["higgsfield_credits"]["hf_mult_motion_control_per_s" if it.script.get("format") == "trend" else "seedance_2_5_720p_per_s"]
        budget.record(it.page, it.id, "higgsfield", "video_submit", credits=credits, job_id=a.job)
    if a.url:
        if not it.video.get("job_id"):
            raise StoreError("registre o job antes (--job)")
        it.video["url"] = a.url
    it.save()
    print("registrado")


def _refund(it, job: str | None) -> None:
    """Estorno: o Higgsfield devolveu os créditos do job falho. Lança o negativo do que foi lançado no envio,
    para a falha do provedor não comer o teto da ideia (160) nem o diário. Uma vez por job."""
    if not job:
        raise StoreError("qual job? use --job <id>")
    hist = [h.get("job_id") for h in it.video.get("history", []) if h.get("failed") is not None]
    if job not in hist:
        raise StoreError(f"o job {job} não está registrado como falho neste item (rode --failed antes)")
    rows = [r for r in budget.rows() if r.get("job_id") == job and r.get("item") == it.id]
    if any(r["action"] == "video_refund" for r in rows):
        print(f"estorno do job {job} já lançado")
        return
    cr = sum(float(r.get("credits") or 0) for r in rows if r["action"] == "video_submit")
    usd = sum(float(r.get("usd") or 0) for r in rows if r["action"] == "video_submit")
    if not cr and not usd:
        print(f"nada a estornar para {job}")
        return
    budget.record(it.page, it.id, "higgsfield", "video_refund", credits=-cr, usd=-usd, job_id=job, note="estorno")
    print(f"estorno lançado: -{cr:g} créditos (job {job})")


def _download(url: str, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["curl", "-sSfL", "--max-time", "180", "-o", str(dst), url], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"download falhou ({r.stderr.strip()[:200]}). Libere o domínio na rede do ambiente "
              f"ou baixe à mão e use --file.", file=sys.stderr)
        return False
    return True


def _fetch_gag(a, it):
    _need_state(it, ["revisao"], "fetch-video --gag")
    gag = it.video.get("gag") or {}
    if not gag.get("job_id"):
        raise StoreError("nenhum gag enviado")
    wd = _workdir(it)
    n = it.attempts.get("gag", 1)
    dst = wd / f"gag-v{n}.mp4"
    if a.file:
        shutil.copy(a.file, dst)
    elif not _download(gag.get("url", ""), dst):
        sys.exit(2)
    info = media.probe(dst)
    sheet = media.sheet_window(dst, wd / f"gag-v{n}-sheet.jpg", 0, info["duration"], fps=4)
    gag.update({"path": rel(dst), "sheet": rel(sheet), "info": info, "cuts": media.detect_cuts(dst)})
    it.video["gag"] = gag
    it.save()
    print(f"ok: {dst.relative_to(ROOT)}  {info}")
    print(f"revisar o gag: {sheet.relative_to(ROOT)} (emenda com o último frame do motion control: "
          f"{it.video.get('last')})")


def cmd_fetch_video(a):
    page, it = _item(a.ref)
    if a.gag:
        return _fetch_gag(a, it)
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
    joined = None
    gag = it.video.get("gag") or {}
    if it.script.get("gag_followup") and not gag.get("dropped") and not a.no_gag:
        if it.gates.get("gag", {}).get("qa") != "pass":
            raise StoreError("o gag (C5) ainda não passou no QA: termine (video-request --gag → fetch-video --gag → "
                             "review gag), descarte com `skip-gag` ou empacote sem ele com --no-gag")
        gsrc = local(gag.get("path"))
        if not gsrc or not gsrc.exists():
            raise StoreError("clipe do gag não encontrado; rode fetch-video --gag")
        joined, reenc = media.concat(src, gsrc, pk / "_mc+gag.mp4")
        print(f"emendado: motion control + gag ({'reencodado' if reenc else 'sem reencode'})")
        src = joined
    mp4 = media.normalize_reels(src, pk / f"{it.page}-{it.id}.mp4")
    if joined and joined.exists() and joined != mp4:
        joined.unlink()
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
        *(["- [ ] Vídeo emendado (motion control + gag): a emenda não carrega o C2PA do provedor; "
           "o rótulo 'AI info' no post é OBRIGATÓRIO (ata D8)"] if joined else []),
        f"- [ ] Capa: capa.jpg; texto: \"{it.script.get('cover', {}).get('text_max4', '')}\"",
        "- [ ] Legenda: copiar de legenda.txt",
        f"- [ ] Horário sugerido (BRT): {', '.join(page.data.get('cadence', {}).get('post_times_brt', []))}",
        f"- [ ] Depois de postar: `python -m pipeline posted {it.page}/{it.id} --link <url>`",
        "",
        f"Duplicado? {'SIM, NÃO POSTE: ' + dup if dup else 'não'}",
    ]), encoding="utf-8")
    it.post.update({"package": rel(pk), "hash": h, "duplicate_of": dup, "with_gag": bool(joined)})
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
    gate = launch.check(page)
    if not gate["can_post"]:  # o post já aconteceu no app: registra, mas avisa (ata D6)
        print(f"ATENÇÃO: estreia de {page.slug} antes do portão ({gate['summary']}; ata D6)", file=sys.stderr)
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
        "music": s.get("music", {}), "videoUrl": it.video.get("url", ""), "gagUrl": (it.video.get("gag") or {}).get("url", ""), "cuts": it.video.get("cuts", []),
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
            "refsReady": len(p.available_refs()) >= 2, "launchedAt": str(p.data.get("launched_at", "") or ""),
            "launch": launch.check(p)["summary"]}})
    pl = mkplan()
    writes.append({"op": "set", "collection": "saude", "doc_id": "atual", "data": {
        "at": int(time.time() * 1000), "paused": pl["paused"] or "", "spend": pl["spend"], "notes": pl["notes"],
        "actions": len(pl["actions"]), "waiting": [w["item"] + " · " + w["stage"] for w in pl["waiting_caio"]],
        "ledger": budget.rows()[-15:], "balance": pl.get("balance"),
        "errors": {"consecutive": budget.health().get("consecutive_errors", 0),
                   "max": budget.load_budget().get("max_consecutive_errors", 3),
                   "last": budget.health().get("errors", [])[-5:]},
        "cadence": placar.cadence_check()}})
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


MEDIA_KEYS = ("storyboard", "start", "end", "video", "sheet", "gag", "last", "source", "source_first", "gag_clip")
MAGIC = {".png": [b"\x89PNG"], ".jpg": [b"\xff\xd8\xff"], ".jpeg": [b"\xff\xd8\xff"],
         ".mp4": [b"ftyp"], ".mov": [b"ftyp"], ".m4v": [b"ftyp"]}


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
    g = v.get("gag") or {}
    if g.get("path") and not g.get("dropped"):
        out["gag_clip"] = g["path"]
    mo = it.motion or {}  # trend: sem a fonte e o 1º frame, a sessão seguinte não gera o frame nem sobe a fonte
    for k, f in (("source", "source_path"), ("source_first", "first_frame")):
        if mo.get(f):
            out[k] = mo[f]
    return {k: rel(p) for k, p in out.items()}


def cmd_panel_asset(a):
    """Grava o asset do painel (subido com Artifact asset:true) no item: serve à Caixa E de arquivo permanente.

    O id em /_blob/<id> fica em item.post.media[key] junto do caminho local, para `media-status` restaurar
    o arquivo numa sessão nova (out/ não vai para o git).
    """
    page, it = _item(a.ref)
    path = _media_paths(it).get(a.key, "")
    if a.path and rel(a.path) != path:
        # o arquivo subido é de outra versão (a etapa foi refeita entre o media-status e o upload)
        raise StoreError(f"{a.ref} {a.key}: o arquivo subido ({rel(a.path)}) não é mais o atual ({path or 'nenhum'}); "
                         f"rode media-status de novo")
    # O id do asset (32 hex) vem em --asset-id ou dentro da url devolvida pelo Artifact (ex.: /_blob/<id>).
    m = re.fullmatch(r"[0-9a-fA-F]{32}", a.asset_id or "") or re.search(r"(?<![0-9a-fA-F])([0-9a-fA-F]{32})(?![0-9a-fA-F])",
                                                                          a.url or "")
    asset = m.group(1 if m.re.groups else 0).lower() if m else ""
    if a.key in MEDIA_KEYS and not path:
        raise StoreError(f"{a.ref} não usa mídia '{a.key}' agora")
    it.post.setdefault("assets", {})[a.key] = a.url
    if asset:
        it.post.setdefault("media", {})[a.key] = {"asset": asset, "path": path}
    elif a.key in MEDIA_KEYS:
        print("aviso: sem id de asset (32 hex) na url nem em --asset-id: a mídia NÃO fica arquivada", file=sys.stderr)
    it.save()
    print("ok")


def cmd_media_status(a):
    """O que subir (existe local, sem asset) e o que restaurar (sumiu do disco, tem asset) para os itens ativos."""
    upload, restore, lost = [], [], []
    for it in list_items():
        if a.ref and f"{it.page}/{it.id}" != a.ref:
            continue
        if it.state in ("descartado", "postado") and not a.ref:
            continue
        media = it.post.get("media", {})
        for key, path in _media_paths(it).items():
            rec = media.get(key) or {}
            exists = local(path).exists()
            ref = f"{it.page}/{it.id}"
            if exists and rec.get("path") != path:
                up = {"ref": ref, "key": key, "file": str(local(path)), "path": path}
                if local(path).stat().st_size > 15 * 1024 * 1024:  # limite de arquivo binário do asset store
                    up["warn"] = "maior que 15 MB: o asset store recusa; comprima uma cópia só para o arquivo"
                upload.append(up)
            elif not exists and rec.get("asset") and rec.get("path") == path:
                restore.append({"ref": ref, "key": key, "asset_id": rec["asset"], "to": path})
            elif not exists:
                # sumiu e o arquivo guardado (se houver) é de outra versão: não restaurar o velho no lugar do novo
                lost.append({"ref": ref, "key": key, "path": path, "archived_version": rec.get("path") or None,
                             "fix": f"refaça a etapa (retry {ref} {_stage_of(key)} --force) ou restaure à mão"})
    _print({"upload": upload, "restore": restore, "lost": lost,
            "how_upload": "Artifact(url=<painel>, asset=true, file_paths=[...]) e depois "
                          "`python -m pipeline panel-asset <ref> <key> /_blob/<id> --path <path>` para cada arquivo",
            "how_restore": "Artifact(action='read', url=<painel>, path=<asset_id>) e depois "
                           "`python -m pipeline media-restore <ref> <key> --file <arquivo salvo>`"})


def _stage_of(key: str) -> str:
    return {"storyboard": "storyboard", "start": "frames", "end": "frames", "source": "frames",
            "source_first": "frames", "gag_clip": "gag"}.get(key, "video")


def cmd_media_restore(a):
    page, it = _item(a.ref)
    path = _media_paths(it).get(a.key)
    if not path:
        raise StoreError(f"{a.ref} não usa mídia '{a.key}'")
    rec = (it.post.get("media") or {}).get(a.key) or {}
    if rec.get("path") != path and not a.force:
        # o asset guardado é de uma versão anterior (ex.: storyboard v1 com o item já no v2)
        raise StoreError(f"o arquivo guardado de '{a.key}' é {rec.get('path') or 'nenhum'}, mas o item usa {path}: "
                         f"restaurar trocaria a versão em silêncio (use --force se for isso mesmo)")
    src = Path(a.file)
    if not src.is_file() or src.stat().st_size == 0:
        raise StoreError(f"{a.file} vazio ou inexistente (o download do asset falhou?)")
    head = src.read_bytes()[:16]
    sigs = MAGIC.get(Path(path).suffix.lower())
    if sigs and not any(head.startswith(sg) or sg in head for sg in sigs):
        raise StoreError(f"{a.file} não parece um {Path(path).suffix} (cabeçalho {head[:8]!r}): asset errado?")
    dst = local(path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
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

    def _at(r):
        d = r.get("data") if isinstance(r, dict) and isinstance(r.get("data"), dict) else r
        try:
            return float(d.get("at") or 0) if isinstance(d, dict) else 0.0
        except (TypeError, ValueError):
            return 0.0
    for r in sorted(_decision_rows(raw), key=_at):  # em ordem: pausar e depois retomar termina retomado
        if not isinstance(r, dict):
            print(f"ignorado (não é documento): {r!r}"[:200])
            continue
        d = r.get("data") if isinstance(r.get("data"), dict) else r
        did = r.get("doc_id") or r.get("id") or r.get("_id") or d.get("id")
        if d.get("applied"):
            continue
        ref, stage, verdict = d.get("ref"), d.get("stage"), d.get("verdict")
        if stage == "usina" and verdict in ("pause", "resume"):  # kill switch da aba Saúde (ata D2/D8)
            if verdict == "pause":
                budget.PAUSE_FILE.write_text(f"pausado pelo Caio no painel: {d.get('notes') or 'sem motivo'}",
                                             encoding="utf-8")
            else:
                if budget.PAUSE_FILE.exists():
                    budget.PAUSE_FILE.unlink()
                budget.reset_errors()
            print(f"usina: {verdict}")
            if did:
                done.append(did)
            continue
        if stage == "ideia" and verdict == "reject":  # veto de pauta (ata D3): descarta antes de gastar
            try:
                page, it = _item(ref)
            except StoreError as e:
                print(f"inválido ({e})")
                if did:
                    invalid.append(did)
                continue
            if it.state in ("ideia", "roteiro", "storyboard"):
                it.set_state("descartado", f"vetado pelo Caio: {d.get('notes') or 'sem motivo'}")
                it.save()
                print(f"{ref}: vetado")
                done.append(did)
            else:
                print(f"{ref}: veto chegou tarde (já em {it.state}); ignorado")
                stale.append(did)
            continue
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


def cmd_record_error(a):
    h = budget.record_error(a.msg, a.ref or "")
    lim = budget.load_budget().get("max_consecutive_errors", 3)
    print(f"erro registrado ({h['consecutive_errors']}/{lim} seguidos)")
    if budget.paused():
        print(f"PAUSADO: {budget.paused()}")


def cmd_balance(a):
    if a.credits < 0:
        raise StoreError("saldo negativo?")
    budget.record_balance(a.credits)
    st, est = budget.balance_status()
    print(f"saldo registrado: {a.credits:g} créditos ({st}; mínimo {budget.load_budget().get('min_higgsfield_credits')})")


def cmd_health(a):
    h = budget.health()
    st, est = budget.balance_status()
    _print({"paused": budget.paused(), "consecutive_errors": h["consecutive_errors"],
            "last_errors": h["errors"][-5:], "balance": {"status": st, "credits_est": est, "read": h["balance"]}})


def cmd_placar_import(a):
    try:
        raw = json.loads(Path(a.file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise StoreError(f"não consegui ler {a.file}: {e}")
    _print(placar.import_rows(raw))


def cmd_cadence_check(a):
    _print(placar.cadence_check())


def cmd_pause(a):
    budget.PAUSE_FILE.write_text(a.reason or "pausado pelo Caio", encoding="utf-8")
    print("PAUSADO")


def cmd_resume(a):
    if budget.PAUSE_FILE.exists():
        budget.PAUSE_FILE.unlink()
    budget.reset_errors()  # senão o próximo erro pausaria de novo na hora
    print("retomado")


def cmd_launch_check(a):
    _print(launch.check(get_page(a.page)))


def cmd_tick_start(a):
    ok, msg, d = lock.acquire(a.owner)
    if not ok:
        raise StoreError(msg + ". Saia sem fazer nada (o outro ciclo termina e libera).")
    if msg:
        print(f"aviso: {msg}")
    _print({"owner": d["owner"], "lock": "usina/.lock", "expires_in_min": int(lock.TTL_S / 60)})


def cmd_tick_end(a):
    ok, msg = lock.release(a.owner, a.force)
    if not ok:
        raise StoreError(msg)
    print(msg)


def _other_tick() -> None:
    d = lock.held_by_other()
    if d:
        raise StoreError(f"outro ciclo está rodando ({lock.describe(d)}): não submeto vídeo em paralelo")


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


# Comandos cujo sucesso quebra a sequência de erros (ata D5: "3 erros SEGUIDOS").
PROGRESS = {"save-script", "image", "pick", "skip-gag", "record-image", "record-upload", "review", "approve", "retry", "discard",
            "video-request", "record-video", "fetch-video", "package", "posted", "motion-source", "media-restore"}
# (panel-apply/panel-export rodam todo ciclo, com ou sem erro: não podem zerar a contagem)


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
    p.add_argument("--variants", type=int, default=1, help="trend: N opções do frame (1-4); escolha com pick")
    p.set_defaults(f=cmd_image)
    p = sp.add_parser("pick"); p.add_argument("ref"); p.add_argument("stage", choices=["frames"])
    p.add_argument("n", type=int); p.set_defaults(f=cmd_pick)
    p = sp.add_parser("record-image"); p.add_argument("ref"); p.add_argument("stage"); p.add_argument("key")
    p.add_argument("--hf-job", required=True); p.add_argument("--url"); p.set_defaults(f=cmd_record_image)
    p = sp.add_parser("record-upload"); p.add_argument("ref"); p.add_argument("key")
    p.add_argument("--hf-id", required=True); p.set_defaults(f=cmd_record_upload)
    p = sp.add_parser("review"); p.add_argument("ref"); p.add_argument("stage", choices=["storyboard", "frames", "video", "gag"])
    p.add_argument("verdict", choices=["pass", "fail"]); p.add_argument("--notes", default=""); p.set_defaults(f=cmd_review)
    p = sp.add_parser("approve"); p.add_argument("ref"); p.add_argument("stage", choices=["storyboard", "frames", "video"])
    p.add_argument("--reject", action="store_true"); p.add_argument("--notes", default=""); p.set_defaults(f=cmd_approve)
    p = sp.add_parser("retry"); p.add_argument("ref"); p.add_argument("stage", choices=["storyboard", "frames", "video", "gag"])
    p.add_argument("--force", action="store_true"); p.set_defaults(f=cmd_retry)
    p = sp.add_parser("discard"); p.add_argument("ref"); p.add_argument("--why", default=""); p.set_defaults(f=cmd_discard)
    p = sp.add_parser("video-request"); p.add_argument("ref")
    p.add_argument("--no-grid", action="store_true", help="sem a grade de storyboard (se o take inventou cortes)")
    p.add_argument("--resolution", choices=["480p", "720p", "1080p"], help="480p = draft de estrutura")
    p.add_argument("--repair", default="", help="REPAIR SCOPE (playbook C6a): o que mudar, uma variável")
    p.add_argument("--gag", action="store_true", help="trend: 2º clipe (gag, Seedance 4-5 s) a partir do último frame do MC")
    p.add_argument("--no-sheet", action="store_true",
                   help="trend: Genjutsu só com o frame do personagem, sem rosto e silhueta (A/B se duplicar o personagem)")
    p.set_defaults(f=cmd_video_request)
    p = sp.add_parser("skip-gag"); p.add_argument("ref"); p.add_argument("--why", default="")
    p.add_argument("--force", action="store_true"); p.set_defaults(f=cmd_skip_gag)
    p = sp.add_parser("sheet"); p.add_argument("page"); p.add_argument("--mock", action="store_true", default=None)
    p.add_argument("--provider", choices=["openai", "higgsfield"], default=os.getenv("USINA_IMAGE_PROVIDER"))
    p.set_defaults(f=cmd_sheet)
    p = sp.add_parser("split-sheet"); p.add_argument("page"); p.add_argument("file"); p.set_defaults(f=cmd_split_sheet)
    p = sp.add_parser("record-video"); p.add_argument("ref"); p.add_argument("--job"); p.add_argument("--url")
    p.add_argument("--credits", type=float)
    p.add_argument("--failed", nargs="?", const="", default=None, help="o job falhou (motivo opcional)")
    p.add_argument("--refunded", action="store_true",
                   help="o Higgsfield devolveu os créditos do job falho: estorna no livro-caixa (uma vez por job)")
    p.add_argument("--gag", action="store_true", help="o job é o clipe de gag (C5)")
    p.set_defaults(f=cmd_record_video)
    p = sp.add_parser("fetch-video"); p.add_argument("ref"); p.add_argument("--file"); p.add_argument("--gag", action="store_true")
    p.set_defaults(f=cmd_fetch_video)
    p = sp.add_parser("package"); p.add_argument("ref"); p.add_argument("--no-gag", action="store_true")
    p.set_defaults(f=cmd_package)
    p = sp.add_parser("posted"); p.add_argument("ref"); p.add_argument("--link"); p.set_defaults(f=cmd_posted)
    p = sp.add_parser("fetch-refs"); p.add_argument("page"); p.set_defaults(f=cmd_fetch_refs)
    p = sp.add_parser("panel-export"); p.add_argument("--all", action="store_true", help="(sem efeito: tudo é exportado)"); p.set_defaults(f=cmd_panel_export)
    p = sp.add_parser("panel-asset"); p.add_argument("ref"); p.add_argument("key"); p.add_argument("url")
    p.add_argument("--path", help="caminho que o media-status listou (confere que é a versão atual)")
    p.add_argument("--asset-id", help="id do asset (32 hex), se a url não trouxer")
    p.set_defaults(f=cmd_panel_asset)
    p = sp.add_parser("motion-source"); p.add_argument("ref"); p.add_argument("--file"); p.add_argument("--hf-id")
    p.add_argument("--force", action="store_true"); p.set_defaults(f=cmd_motion_source)
    p = sp.add_parser("media-status"); p.add_argument("--ref"); p.set_defaults(f=cmd_media_status)
    p = sp.add_parser("media-restore"); p.add_argument("ref"); p.add_argument("key"); p.add_argument("--file", required=True)
    p.add_argument("--force", action="store_true"); p.set_defaults(f=cmd_media_restore)
    p = sp.add_parser("record-error"); p.add_argument("msg"); p.add_argument("--ref"); p.set_defaults(f=cmd_record_error)
    p = sp.add_parser("balance"); p.add_argument("credits", type=float); p.set_defaults(f=cmd_balance)
    sp.add_parser("health").set_defaults(f=cmd_health)
    p = sp.add_parser("placar-import"); p.add_argument("file"); p.set_defaults(f=cmd_placar_import)
    sp.add_parser("cadence-check").set_defaults(f=cmd_cadence_check)
    p = sp.add_parser("panel-apply"); p.add_argument("file"); p.set_defaults(f=cmd_panel_apply)
    p = sp.add_parser("pause"); p.add_argument("reason", nargs="?"); p.set_defaults(f=cmd_pause)
    sp.add_parser("resume").set_defaults(f=cmd_resume)
    sp.add_parser("ledger").set_defaults(f=cmd_ledger)
    p = sp.add_parser("launch-check"); p.add_argument("page"); p.set_defaults(f=cmd_launch_check)
    p = sp.add_parser("tick-start"); p.add_argument("--owner"); p.set_defaults(f=cmd_tick_start)
    p = sp.add_parser("tick-end"); p.add_argument("--owner"); p.add_argument("--force", action="store_true")
    p.set_defaults(f=cmd_tick_end)
    a = ap.parse_args(argv)
    try:
        a.f(a)
        if a.cmd in PROGRESS:
            budget.reset_errors()
    except (StoreError, images.ImageError, media.MediaError, json.JSONDecodeError, OSError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
