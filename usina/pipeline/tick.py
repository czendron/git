"""O cérebro determinístico (ata D1): olha a fila e diz exatamente o que a sessão deve fazer agora.

`plan` devolve uma lista de ações em JSON. A sessão do Claude executa cada uma (comandos do pipeline,
chamadas MCP do Higgsfield, revisão visual) e registra o resultado com os comandos `record-*`/`review`/`approve`.
O LLM nunca decide o fluxo: só executa o que o plano manda.
"""
from __future__ import annotations

import time

from . import budget
from .store import Item, Page, list_items, load_pages

ACTIVE = ["ideia", "roteiro", "storyboard", "frames", "video", "revisao", "pronto"]
CALIBRATION_DAYS = 14
BUFFER_DAYS = 3  # quantos dias de posts manter no estoque (ideias em produção + prontos)


def needs_caio(page: Page, stage: str, now: float | None = None) -> bool:
    """Ata D3: o Caio aprova storyboard/frames nas 2 primeiras semanas de cada personagem."""
    if stage == "video":
        return True
    launched = page.data.get("launched_at")
    if not launched:
        return True
    now = now or time.time()
    try:
        ts = time.mktime(time.strptime(str(launched), "%Y-%m-%d"))
    except ValueError:
        return True
    return (now - ts) < CALIBRATION_DAYS * 86400


def _gate(item: Item, stage: str) -> dict:
    return item.gates.setdefault(stage, {"qa": "pending", "caio": "pending"})


def _est_video_credits(item: Item, b: dict) -> float:
    d = float(item.script.get("duration_s", 10))
    key = "hf_mult_motion_control_per_s" if item.script.get("format") == "trend" else "seedance_2_5_720p_per_s"
    per = b["cost_estimates"]["higgsfield_credits"][key]
    return d * per


def plan_item(item: Item, page: Page, b: dict, now: float) -> list[dict]:
    st = item.state
    pid = f"{item.page}/{item.id}"
    cmd = f"python -m pipeline"
    acts: list[dict] = []
    att = item.attempts
    max_img = b["per_idea"]["max_image_attempts"]

    if st == "ideia":
        acts.append({"do": "write_script", "item": pid,
                     "how": f"Leia prompts/script.md, pages/{item.page}/page.yaml, `{cmd} memory {item.page}` e "
                            f"playbook/falhas.md. Escreva o roteiro JSON para a ideia {item.idea!r} em "
                            f"out/scripts/{item.id}.json e rode `{cmd} save-script {pid} out/scripts/{item.id}.json`."})
    elif st == "roteiro" and item.script.get("format") == "trend":
        mo = item.motion or {}
        if not mo.get("first_frame"):
            acts.append({"do": "await_caio", "item": pid, "stage": "fonte",
                         "how": f"Trend precisa do vídeo-fonte (.mp4, 1 pessoa, corpo inteiro, câmera parada, 8-10 s): "
                                f"motion library do Higgsfield ou trend recortada. `{cmd} motion-source {pid} --file fonte.mp4`"})
        elif att.get("frames", 0) >= max_img:
            acts.append({"do": "discard", "item": pid, "how": f"{cmd} discard {pid} --why 'frame de trend reprovado 3x'"})
        else:
            acts.append({"do": "run", "item": pid, "cmd": f"{cmd} image {pid} frames",
                         "cost_usd": b["cost_estimates"]["openai_image"]["high"], "provider": "openai"})
    elif st == "roteiro":
        if att.get("storyboard", 0) >= max_img:
            acts.append({"do": "discard", "item": pid, "why": "storyboard reprovado 3x",
                         "how": f"{cmd} discard {pid} --why 'storyboard reprovado 3x'"})
        else:
            acts.append({"do": "run", "item": pid, "cmd": f"{cmd} image {pid} storyboard",
                         "cost_usd": b["cost_estimates"]["openai_image"]["high"], "provider": "openai"})
    elif st == "storyboard":
        g = _gate(item, "storyboard")
        if g["qa"] == "pending":
            acts.append({"do": "review_image", "item": pid, "stage": "storyboard", "file": item.storyboard.get("path"),
                         "rubric": "prompts/review_storyboard.md",
                         "how": f"Abra a imagem com Read, aplique a rubrica e registre: "
                                f"`{cmd} review {pid} storyboard pass|fail --notes '...'`"})
        elif g["qa"] == "fail":
            acts.append({"do": "run", "item": pid, "cmd": f"{cmd} retry {pid} storyboard"})
        elif needs_caio(page, "storyboard", now) and g["caio"] == "pending":
            acts.append({"do": "await_caio", "item": pid, "stage": "storyboard"})
        elif g["caio"] == "rejected":
            acts.append({"do": "run", "item": pid, "cmd": f"{cmd} retry {pid} storyboard"})
        else:
            acts.append({"do": "run", "item": pid, "cmd": f"{cmd} image {pid} frames",
                         "cost_usd": 2 * b["cost_estimates"]["openai_image"]["high"], "provider": "openai"})
    elif st == "frames":
        g = _gate(item, "frames")
        if g["qa"] == "pending" and item.script.get("en", {}).get("end_change") and "end" not in item.frames:
            # fallback Higgsfield em dois passos: falta o frame B (edição do A)
            acts.append({"do": "run", "item": pid, "cmd": f"{cmd} image {pid} frames --provider higgsfield"})
        elif g["qa"] == "pending":
            acts.append({"do": "review_image", "item": pid, "stage": "frames",
                         "file": [f.get("path") for f in item.frames.values()],
                         "rubric": "prompts/review_frames.md",
                         "how": f"`{cmd} review {pid} frames pass|fail --notes '...'`"})
        elif g["qa"] == "fail":
            if att.get("frames", 0) >= max_img:
                acts.append({"do": "discard", "item": pid, "how": f"{cmd} discard {pid} --why 'frames reprovados 3x'"})
            else:
                acts.append({"do": "run", "item": pid, "cmd": f"{cmd} retry {pid} frames"})
        elif needs_caio(page, "frames", now) and g["caio"] == "pending":
            acts.append({"do": "await_caio", "item": pid, "stage": "frames"})
        elif g["caio"] == "rejected":
            # Caio recusou os frames: refaz (ou descarta na 3ª), nunca segue para o vídeo.
            if att.get("frames", 0) >= max_img:
                acts.append({"do": "discard", "item": pid, "how": f"{cmd} discard {pid} --why 'frames reprovados 3x'"})
            else:
                acts.append({"do": "run", "item": pid, "cmd": f"{cmd} retry {pid} frames"})
        else:
            if not b.get("switches", {}).get("video_enabled", False):
                acts.append({"do": "blocked", "item": pid, "why": "vídeo desligado em budget.yaml (switches.video_enabled)"})
                return acts
            credits = _est_video_credits(item, b)
            usd = credits * float(b.get("higgsfield_credit_usd", 0.05))
            ok, why = budget.can_spend("higgsfield", usd, now)
            if not ok:
                acts.append({"do": "blocked", "item": pid, "why": why})
            elif att.get("video", 0) >= b["per_idea"]["max_video_attempts"]:
                acts.append({"do": "discard", "item": pid, "how": f"{cmd} discard {pid} --why 'limite de tentativas de vídeo'"})
            elif budget.item_spend(item.page, item.id)["credits"] + credits > float(b["per_idea"].get("max_credits", 1e9)):
                acts.append({"do": "discard", "item": pid,
                             "how": f"{cmd} discard {pid} --why 'teto de {b['per_idea']['max_credits']} créditos por ideia'"})
            else:
                acts.append({"do": "video_submit", "item": pid, "est_credits": credits, "provider": "higgsfield",
                             "how": f"Rode `{cmd} video-request {pid}`: ele imprime as imagens a subir e o JSON exato "
                                    f"para mcp__Higgsfield__generate_video_batch. Suba as imagens (media_upload + PUT, "
                                    f"ou o fallback descrito na saída), envie, e registre com "
                                    f"`{cmd} record-video {pid} --job <job_id> --credits <créditos>`."})
    elif st == "video":
        if not item.video.get("url"):
            acts.append({"do": "video_poll", "item": pid, "job_id": item.video.get("job_id"),
                         "how": f"mcp__Higgsfield__jobs_wait; quando completar: `{cmd} record-video {pid} --url <result_url>`"})
        elif not item.video.get("path"):
            acts.append({"do": "run", "item": pid, "cmd": f"{cmd} fetch-video {pid}"})
        else:
            g = _gate(item, "video")
            if g["qa"] == "pending":
                acts.append({"do": "review_video", "item": pid, "rubric": "prompts/review_video.md",
                             "file": item.video.get("sheet"),
                             "how": f"Abra a folha de contato (e o último frame) com Read, aplique a rubrica e registre "
                                    f"`{cmd} review {pid} video pass|fail --notes '...'`"})
            elif g["qa"] == "fail":
                acts.append({"do": "run", "item": pid, "cmd": f"{cmd} retry {pid} video"})
    elif st == "revisao":
        g = _gate(item, "video")
        if g["caio"] == "pending":
            acts.append({"do": "await_caio", "item": pid, "stage": "video"})
        elif g["caio"] == "rejected":
            acts.append({"do": "run", "item": pid, "cmd": f"{cmd} retry {pid} video"})
        else:
            acts.append({"do": "run", "item": pid, "cmd": f"{cmd} package {pid}"})
    return acts


def plan(now: float | None = None) -> dict:
    now = now or time.time()
    b = budget.load_budget()
    out = {"at": now, "paused": budget.paused(), "spend": None, "actions": [], "waiting_caio": [], "notes": []}
    s = budget.spend(now)
    out["spend"] = {"today": s.today, "month_usd": s.month_usd, "month_cap": s.month_cap,
                    "month_pct": round(s.month_pct, 1)}
    if out["paused"]:
        out["notes"].append(f"PAUSADO: {out['paused']}. Nenhuma ação.")
        return out
    y = budget.yield_last(10)
    if y is not None and y < b["quality"]["min_yield_last10"]:
        out["notes"].append(f"Aproveitamento {y:.0%} < {b['quality']['min_yield_last10']:.0%} nas últimas 10. "
                            f"Parando geração de vídeo; revise playbook/falhas.md.")
    if budget.degraded_mode(now):
        out["notes"].append("Acima de 80% do teto mensal: só 720p, sem Genjutsu.")

    import os
    sw = b.get("switches", {})
    if sw.get("image_provider", "openai") == "openai" and not os.getenv("OPENAI_API_KEY") \
            and os.getenv("USINA_MOCK") != "1":
        out["notes"].append("OPENAI_API_KEY ausente: etapas de imagem bloqueadas (libere api.openai.com e a chave no ambiente)."
                            + (" Fallback Higgsfield permitido." if sw.get("image_fallback_allowed") else ""))
        out["images_blocked"] = not sw.get("image_fallback_allowed", False)
    for page in load_pages(include_drafts=False):
        items = [i for i in list_items(page.slug) if i.state in ACTIVE]
        ready = [i for i in items if i.state == "pronto"]
        if len(ready) >= b["max_unposted_per_page"]:
            out["notes"].append(f"{page.slug}: {len(ready)} prontos sem postar; não gero mais.")
            continue
        target = int(page.data.get("cadence", {}).get("posts_per_day", 1)) * BUFFER_DAYS
        missing = target - len(items)
        if missing > 0:
            out["actions"].append({"do": "new_ideas", "page": page.slug, "count": missing,
                                   "how": f"Escolha {missing} ideia(s) (radar, pauta ou roteiros de crossover) e crie com "
                                          f"`python -m pipeline new {page.slug} 'título' --idea '...'`"})
        for it in sorted(items, key=lambda i: ACTIVE.index(i.state), reverse=True):
            for a in plan_item(it, page, b, now):
                if a["do"] == "await_caio":
                    out["waiting_caio"].append(a)
                elif out.get("images_blocked") and a.get("provider") == "openai":
                    out["notes"].append(f"{a['item']}: imagem esperando a OPENAI_API_KEY.")
                elif a["do"] == "video_submit" and y is not None and y < b["quality"]["min_yield_last10"]:
                    out["notes"].append(f"{a['item']}: vídeo segurado pelo aproveitamento baixo.")
                else:
                    out["actions"].append(a)
    return out
