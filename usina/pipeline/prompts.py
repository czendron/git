"""Monta os prompts de ficha, storyboard, frames e vídeo seguindo playbook/seedance-master.md (templates C1–C5).

Fonte da verdade: o roteiro (JSON, bloco `en`) mais a bíblia da página. Regras-chave aplicadas aqui:
- identidade vem das imagens (rosto.png = @Image 1, silhueta.png = @Image 2); texto de identidade mínimo (regra 8)
- 4 estágios B0–B3 com estado final; "moments of ONE continuous shot" (regras 5–7)
- tempo real em BPM, nunca "slow"; câmera lenta proibida pelo nome (regra 19)
- orientação travada em graus a partir da câmera; olhar na lente escrito (regra 18)
- topete/laquê/bigode descrito como material, medida e marco corporal (regra 17)
- cabeçalho de contagem: EXACTLY 1 main character + N passersby (regra 13)
- orientação POR ESTÁGIO (en.stages[].facing, em graus a partir da lente) e, quando outro ator interage com ele,
  posição e orientação desse ator no mesmo estágio (en.stages[].counterpart): quem encara quem no momento-chave
  (falha do boxe: ele de costas quando o outro socou). Ver docs/qa/critica-prompts.md
- ficha (rosto + silhueta) em toda geração, inclusive no motion control (videos-analisados §5)
"""
from __future__ import annotations

import json

from .store import Page

PRONOUN = {"he": ("he", "his", "him", "man"), "she": ("she", "her", "her", "woman")}

CAMERA = {
    "selfie_pov": {
        "fov": 84,
        "frame": "selfie taken by the {noun} with the front camera at arm's length, 84° wide-angle, phone 55 cm from {pos} face, lens slightly below eye level",
        "fill": "{Pos} head, the whole {part} and {pos} shoulders fill the upper two thirds of the frame; {pos} face is the largest element in the photograph.",
        "video": ("Front smartphone camera held at arm's length by {pos} own right hand, 84° field of view, 55 cm from "
                  "{pos} face, lens slightly below eye level. {Pos} right arm extends toward the lens and exits the "
                  "bottom-right frame edge."),
        "storyboard": "84° selfie at arm's length",
    },
    "static_passerby": {
        "fov": 63,
        "frame": "static phone on a passerby's tripod at chest height, 63° field of view, 3 m away",
        "fill": "{Pos} full body, from {pos} shoes to the top of the {part}, fills 80% of the frame height, so {pos} face stays large and readable.",
        "video": "Static smartphone on a tripod at chest height, 63° field of view, 3 m from {obj}, locked off.",
        "storyboard": "63° static from 3 m, full body filling 80% of the panel height",
    },
    "static_low": {
        "fov": 63,
        "frame": "static phone resting 40 cm above the ground, tilted up 10°, 63° field of view, 3 m away",
        "video": "Static smartphone resting 40 cm above the ground, tilted up 10°, 63° field of view, 3 m from {obj}, locked off.",
        "fill": "{Pos} full body, from {pos} shoes to the top of the {part}, fills 80% of the frame height, so {pos} face stays large and readable.",
        "storyboard": "63° static low angle from 3 m",
    },
    # O lint aceita estes dois modos; sem entrada aqui o prompt caía calado na câmera de passante.
    "static_high": {
        "fov": 63,
        "frame": "static phone mounted 2.5 m high, tilted down 20°, 63° field of view, 3 m away",
        "fill": "{Pos} full body fills 75% of the frame height and {pos} face, tilted up toward the lens, stays readable.",
        "video": "Static smartphone mounted 2.5 m high, tilted down 20°, 63° field of view, 3 m from {obj}, locked off.",
        "storyboard": "63° static high angle from 3 m",
    },
    "tracking_side": {
        "fov": 63,
        "frame": "phone held at chest height by a person walking beside {obj}, 63° field of view, 3 m to {pos} side",
        "video": ("Smartphone at chest height moving sideways alongside {obj} at {pos} walking pace, 63° field of view, "
                  "3 m to {pos} side, keeping {obj} in the center third; the camera's only movement is this lateral "
                  "track and it ends when {sub} stops."),
        "fill": "{Pos} full body fills 75% of the frame height, centered.",
        "storyboard": "63° side tracking from 3 m",
    },
}

# Silhueta rígida de cada personagem, como material + medida + marco corporal (regra 17).
SILHOUETTE = {
    "gersinho": ("pompadour", "a giant glossy black pompadour sculpted straight up into a tall wave-shaped block twice "
                 "the height of his own head, rigid like molded resin, every strand fused into one seamless solid shape"),
    "marlene": ("hair dome", "an enormous coppery hairsprayed bouffant shaped into a perfect dome twice as wide as her "
                "shoulders, rigid like a lacquered helmet, every strand fused into one seamless solid shell"),
    "wanderley": ("mustache", "a black waxed horizontal mustache extending straight out to both sides, wider than his "
                  "shoulders, rigid like a carved bar of resin, tips perfectly level"),
}

ROLE = {
    "gersinho": "a lanky brega singer in a shiny tropical-print silk shirt open at the chest, a thick gold chain and white flared trousers",
    "marlene": "a Brazilian auntie in a pastel-pink shoulder-pad blazer suit, huge cat-eye glasses and red nails",
    "wanderley": "a stocky Brazilian uncle in a faded trucker cap, a white tank top, blue tactel shorts and socks with flip-flops",
}

# Identidade mínima no prompt de vídeo (regra 8): papel + a marca da silhueta. O figurino vem da silhueta (@Image 2).
ROLE_SHORT = {
    "gersinho": "a lanky brega singer",
    "marlene": "a Brazilian auntie in cat-eye glasses",
    "wanderley": "a stocky Brazilian uncle",
}
# Primeira frase da silhueta (a marca), para o SCENE CONTEXT e o PHYSICS sem repetir a descrição inteira.
def _mark(sil: str) -> str:
    return sil.split(",")[0]


DEADPAN_FRAME = "Deadpan: lips closed, lip corners level, brows level, eyes looking straight into the lens."
DEADPAN_VIDEO = ("Deadpan throughout: lips closed and relaxed, jaw closed, lip corners level, brows level; one slow "
                 "deliberate blink every 3-4 s; eyes locked on the lens with tiny saccades. Controlled stillness of "
                 "the face while the body moves. Mouth closed throughout — no smile, no speech.")


def _p(page: Page) -> tuple[str, str, str, str]:
    return PRONOUN.get(page.character.get("pronoun", "he"), PRONOUN["he"])


def name(page: Page) -> str:
    return page.character.get("nickname", page.character.get("name", "HIM")).upper().split()[0]


def silhouette(page: Page) -> tuple[str, str]:
    return SILHOUETTE.get(page.slug, ("signature hair", "a rigid signature silhouette, solid like molded resin"))


def cam(script: dict) -> dict:
    return CAMERA.get(script["camera"]["mode"], CAMERA["static_passerby"])


def _sent(text: str) -> str:
    """Frase completa: maiúscula no início e ponto no fim (campos do roteiro chegam soltos)."""
    t = (text or "").strip()
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    return t if t[-1] in ".!?" else t + "."


def _lc(text: str) -> str:
    t = (text or "").strip().rstrip(".")
    return t[:1].lower() + t[1:]


def crowd(n) -> str:
    """'exactly N passersby' ou, com 0, um set só com ele (contagem explícita, regra 13)."""
    n = int(n or 0)
    return f"exactly {n} passerby" if n == 1 else f"exactly {n} passersby"


def _fmt(text: str, page: Page) -> str:
    sub, pos, obj, noun = _p(page)
    return text.format(noun=noun, pos=pos, Pos=pos.capitalize(), obj=obj, sub=sub, part=silhouette(page)[0])


# ---------------- C1 ficha de personagem ----------------

def character_sheet_prompt(page: Page) -> str:
    part, sil = silhouette(page)
    sub, pos, obj, noun = _p(page)
    sheet = {
        "type": "character reference sheet, studio photograph, 4 panels in a 2x2 grid",
        "style": "plain documentary studio photograph, flat even soft light, real skin with visible pores and small "
                 "asymmetries, no retouch, sharp focus throughout",
        "background": "flat solid neutral grey #8a8a8a, seamless, no gradient, no shadows on the backdrop",
        "character": f"{ROLE.get(page.slug, page.character.get('look', ''))}, {sil}, "
                     f"expression: deadpan — lips closed and relaxed, lip corners level, brows level, eyes calm",
        "layout": {
            "top_left": f"large close-up portrait, head turned 3/4 to camera-left, eyes to lens, the full {part} inside "
                        f"the frame with headroom — the ONLY readable face on the sheet",
            "top_right": f"full body true side profile facing frame-left, flat backlight so the body and the {part} read "
                         f"as a crisp outline; face in shadow, unreadable",
            "bottom_left": f"full body from behind, standing straight, full {part} visible from the back",
            "bottom_right": f"full body front, head tilted down 45° so the top of the {part} fills the upper area and "
                            f"the face is hidden",
        },
        "rules": "same person, same outfit, same scale and lighting in all four panels; exactly one person per panel; "
                 "no text, no labels, no numbers, no borders thicker than 8 px white",
    }
    head = ("Image 1 is the approved identity of this character; keep the same face, age, build and outfit. "
            if page.available_refs() else "")
    return head + json.dumps(sheet, ensure_ascii=False, indent=2)


# ---------------- orientação por estágio ----------------

def _orient(st: dict, prev: dict | None = None) -> str:
    """Orientação do personagem no estágio + posição e orientação do outro ator (quem encara quem).

    Com `prev`, a orientação só é repetida quando muda (ou quando há outro ator): o "Unless a stage names a turn"
    segura o resto, e o prompt não incha (BIBO: estrutura vence comprimento)."""
    out = []
    cp = st.get("counterpart")
    has_cp = isinstance(cp, dict) and cp.get("who")
    if st.get("facing") and (prev is None or has_cp or st["facing"] != prev.get("facing")):
        out.append(f"Orientation: {_lc(st['facing'])}.")
    if has_cp:
        out.append(_sent(f"{cp['who']}: {_lc(cp.get('position', ''))}, {_lc(cp.get('facing', ''))}"))
        if str(cp.get("task") or "").strip():  # playbook B4.6: o parceiro tem tarefa enquanto espera
            out.append(_sent(f"Meanwhile {_lc(cp['who'])} {_lc(cp['task'])}"))
    return " ".join(out)


def _stage_lines(stages: list, end_change: str = "", keep_final_match: bool = True) -> list[str]:
    """[Stage n — t] texto + orientação + estado final. Sem frame final como âncora (end_change sem end_image),
    o último estado final é o end_change por extenso; com o end_image, basta o end_state curto do roteiro."""
    lines = []
    for i, st in enumerate(stages, 1):
        text = st["text"] if keep_final_match else st["text"].replace(" The final frame matches the end frame.", "")
        last = i == len(stages)
        end = _lc(end_change) if (last and end_change and not keep_final_match) else _lc(st["end_state"])
        lines.append(" ".join(filter(None, [f"[Stage {i} — {st['t']}] {_sent(text)}",
                                             _orient(st, stages[i - 2] if i > 1 else {}),
                                             f"End state: {end}."])))
    return lines


def _turn_rule(pos: str) -> str:
    return (f"Unless a stage names a turn, {pos} chest stays at 0° to the lens and {pos} hips rotate at most 30°; "
            f"{pos} face is visible in every frame.")


def _ref_lines(nm: str, pos: str, part: str) -> list[str]:
    """Mapa de referências pelo conteúdo + número (o 2.5 casa o material pelo que vê, não só pela ordem)."""
    return [f"@Image 1 (the close-up face photo on grey) defines {nm}'s face — full-preserve, 100% matches the reference.",
            f"@Image 2 (the silhouette sheet on grey) defines only {pos} {part} shape and outfit — full-preserve. Do not "
            f"take the grey backdrop, the panel layout or the extra views."]


# ---------------- C3 storyboard ----------------

def storyboard_prompt(script: dict, page: Page) -> tuple[str, str]:
    en = script["en"]
    sub, pos, obj, noun = _p(page)
    part, _ = silhouette(page)
    panels = en["panels"]
    n = len(panels)
    grid, size = ("2x2", "1024x1536") if n == 4 else ("3x2", "1024x1536") if n == 6 else (f"{n}x1", "1536x1024")
    positions = {4: ["top-left", "top-right", "bottom-left", "bottom-right"],
                 6: ["top-left", "top-center", "top-right", "bottom-left", "bottom-center", "bottom-right"]}
    pos_list = positions.get(n, [f"panel {i + 1}" for i in range(n)])
    stages = en["stages"] if len(en["stages"]) == n else []
    times = [st["t"] for st in stages] if stages else [p.get("t", "") for p in script["storyboard_panels"]]
    per_stage = bool(stages) and all(st.get("facing") for st in stages)
    eyes = "" if per_stage else ", eyes into the lens"
    sb = {
        "type": f"photographic storyboard, {n} panels in a {grid} grid, read left to right, top to bottom, thin white gutters",
        "style": f"vertical smartphone photographs, {_lc(en['lighting'])}, identical camera position and field "
                 f"of view in every panel ({cam(script)['storyboard']})",
        "character": f"the {noun} from image 1 (face) and image 2 ({part}, outfit); exactly one main character in "
                     f"every panel; {pos} face visible in every panel; deadpan in every panel: lips closed, lip "
                     f"corners level{eyes}",
        "location": (f"{en['location']}; {crowd(en['extras_count'])} in every panel, each busy with their "
                     f"own task ({en['extras_tasks']}), none looking at {obj}" if int(en.get('extras_count') or 0)
                     else f"{en['location']}; {sub} is the only person in every panel"),
        "panels": [dict({"position": p, "time": t, "state": s},
                        **({"orientation": _orient(st).replace("Orientation: ", "")} if st and _orient(st) else {}))
                   for p, t, s, st in zip(pos_list, times, panels, stages or [None] * n)],
        "rules": f"same outfit, same {part} shape and size in every panel; props: "
                 f"{_lc(en.get('props_lock') or en.get('props') or 'none')}; no text, no numbers, no speech balloons, "
                 f"no arrows",
    }
    return json.dumps(sb, ensure_ascii=False, indent=2), size


# ---------------- C2 frames ----------------

def frame_a_prompt(script: dict, page: Page, with_storyboard: bool) -> str:
    en = script["en"]
    sub, pos, obj, noun = _p(page)
    part, _ = silhouette(page)
    c = cam(script)
    sb = (" Use panel 1 (top-left) of image 3 as the composition guide; render it as one full-frame photograph."
          if with_storyboard else "")
    first = (en.get("stages") or [{}])[0]
    orient = f" Orientation: {_lc(first['facing'])}." if first.get("facing") else ""
    return "\n".join([
        f"Vertical 9:16 smartphone photograph, {_fmt(c['frame'], page)}.{sb}",
        f"Location: {en['location']}.",
        f"The {noun} from image 1 and image 2 — same face as image 1, same {part} shape and outfit as image 2 — "
        f"stands {en['position']}, already in {pos} signature pose: {en['signature_pose']}.{orient} {DEADPAN_FRAME}",
        f"The {part} is fully inside the frame with 10% headroom above it. {_fmt(c.get('fill', ''), page)} "
        f"{en.get('hands', '')}".replace("  ", " ").strip(),
        (f"Background: {crowd(en['extras_count'])}, ordinary people busy with their own tasks — {en['extras_tasks']} — "
         f"none of them looking at {obj}." if int(en.get("extras_count") or 0) else f"{sub.capitalize()} is the only person in the photograph."),
        f"Props: {en.get('props') or 'none besides the location'}.",
        f"{en['lighting']} Deep depth of field, everything sharp, smartphone HDR look, real skin texture.",
        "Exactly one main character. No text, no captions, no speech balloons, no watermarks.",
    ])


def frame_b_prompt(script: dict, page: Page) -> str:
    en = script["en"]
    sub, pos, obj, noun = _p(page)
    part, _ = silhouette(page)
    last = (en.get("stages") or [{}])[-1]
    lines = [
        f"Edit image 1. Keep the exact same camera position, field of view, location, lighting, passersby layout and "
        f"the {noun}'s identity (face from image 2, {part} and outfit from image 3).",
        f"Change only: {en['end_change']}.",
        _sent(en.get("vacated", "")),
        _sent(en.get("end_props", "")),
        _orient(last),
        DEADPAN_FRAME,
        (f"Exactly one main character, {crowd(en['extras_count'])}, all still busy with their own tasks, "
         f"none looking at {obj}. No text, no balloons." if int(en.get("extras_count") or 0)
         else f"{sub.capitalize()} is the only person in the photograph. No text, no balloons."),
    ]
    return "\n".join(line for line in lines if line and line.strip())


# ---------------- C4 vídeo ----------------

def video_prompt(script: dict, page: Page, *, has_start: bool, has_end: bool, has_storyboard: bool,
                 repair: str = "") -> str:
    en = script["en"]
    sub, pos, obj, noun = _p(page)
    part, sil = silhouette(page)
    nm = name(page)
    extras = int(en.get("extras_count") or 0)
    refs = []
    if has_start or has_end:
        refs.append(" ".join(filter(None, [
            "The start frame defines the opening composition, positions, pose and camera." if has_start else "",
            "The end frame defines the final composition and the gag's end state." if has_end else ""])))
    refs += _ref_lines(nm, pos, part)
    if has_storyboard:
        stg = en["stages"]
        mapping = ", ".join(f"panel {i + 1} is {s['t']}" for i, s in enumerate(stg))
        refs.append(f"@Image 3 (the {len(stg)}-panel storyboard grid) is read left to right, top to bottom: {mapping}. "
                    f"The panels are moments of ONE continuous shot. Do not reorder; do not invent shots; do not use "
                    f"its gutters.")
    if has_start or has_end:
        refs.append("The image references never change the start- or end-frame composition.")
    blocks = []
    if repair:
        blocks += ["REPAIR SCOPE",
                   f"Keep the framing, pacing, location, passersby layout, start and end frames, and {nm}'s identity "
                   f"exactly as specified.",
                   f"Change only: {repair.strip().rstrip('.')}.",
                   f"Protect: the {part} outline, the deadpan mouth, the passersby ignoring {obj}.", ""]
    who = f"{nm}, {ROLE_SHORT.get(page.slug, 'the character')} with {_mark(sil)}"
    blocks += [
        "SCENE CONTEXT",
        (f"EXACTLY 1 main character — {who} — plus {crowd(extras)} in the background. " if extras else
         f"EXACTLY 1 main character — {who} — and no one else in the set. ") + en["gag_sentence"],
        "",
        "ACTIVE REFERENCES",
        *refs,
        "",
        "CAMERA",
        _fmt(cam(script)["video"], page) + " One continuous shot; the camera does not cut on its own; no drift mid-shot.",
        "",
        "LOCATION MAP",
        f"{en['location_map']} The set contains only what the start frame shows.",
        "",
        "ACTION",
        *_stage_lines(en["stages"], en.get("end_change", ""), keep_final_match=has_end),
        _turn_rule(pos),
        "",
        "PERFORMANCE",
        DEADPAN_VIDEO,
        (f"Passersby continue their own tasks — {en['extras_tasks']} — each moving on their own rhythm; none turns toward {obj}."
         if extras else ""),
        "",
        "PHYSICS",
        f"The {part} is one rigid block, hard as molded resin: it moves only with {pos} skull and keeps its exact "
        f"outline in every frame. Still air. Feet keep ground contact, heel lands first, weight visibly transfers. "
        f"{en['hands']} Real-time speed, normal playback — no slow motion.",
        "",
        "LIGHTING",
        f"{en['lighting']} Smartphone video look, deep depth of field, everything sharp.",
        "",
        "POSITIVE LOCKS",
        ((f"Exactly one main character and {crowd(extras)} for the whole clip. " if extras else
          f"Exactly one person, {nm}, for the whole clip. ") + f"{pos.capitalize()} "
         f"face matches @Image 1 and {pos} {part} matches @Image 2 at every distance. "
         f"{en.get('props_lock', '')} No captions, no subtitles, no text on screen.").replace("  ", " "),
    ]
    return "\n".join(b for b in blocks if b is not None).replace("\n\n\n", "\n\n")


# ---------------- C5 motion control (Genjutsu / Kling MC: só cena) ----------------

def motion_scene_prompt(script: dict, page: Page, with_sheet: bool = True) -> str:
    """Prompt de cena do motion control. O movimento vem do vídeo-fonte; o prompt escreve o mundo: papéis das imagens,
    câmera, lugar, luz, rigidez, deadpan e a tarefa de cada figurante (a fonte não traz fundo, videos-analisados §8)."""
    en = script["en"]
    sub, pos, obj, noun = _p(page)
    part, sil = silhouette(page)
    nm = name(page)
    extras = int(en.get("extras_count") or 0)
    roles = (f"Image 1 is the only character, {nm}, already placed in the scene. Image 2 (face close-up) and image 3 "
             f"(silhouette sheet) are identity references of that same {noun}, not extra people: take only {pos} face "
             f"from image 2 and {pos} {part} shape and outfit from image 3." if with_sheet else
             f"Image 1 is the only character, {nm}, already placed in the scene.")
    crowd_line = (f"{crowd(extras).capitalize()} continue their own tasks — {en['extras_tasks']} — each moving on "
                  f"their own rhythm through the whole clip; none looks at {obj}."
                  if extras else f"{sub.capitalize()} is the only person in the set.")
    return " ".join([
        roles,
        "Body motion and timing come from the source video; the camera keeps the framing of image 1 and follows the "
        "source video's camera, with no added cuts.",
        f"{_sent(en['location'])} {en['lighting']} Smartphone video look, everything sharp.",
        f"The {noun}'s {part} is a rigid lacquered solid that moves only as one block with {pos} head and keeps its "
        f"exact outline. {pos.capitalize()} face stays deadpan and visible: lips closed, lip corners level, eyes "
        f"toward the lens.",
        crowd_line,
        "Exactly one main character. Real-time speed.",
    ])


def motion_frame_prompt(script: dict, page: Page) -> str:
    """Frame do personagem para motion control = edição do 1º frame do vídeo-fonte (videos-analisados §2).

    image 1 = primeiro frame da fonte, image 2 = rosto, image 3 = silhueta.
    """
    en = script["en"]
    sub, pos, obj, noun = _p(page)
    part, sil = silhouette(page)
    who = en.get("replace_subject", "the dancer")
    return "\n".join([
        f"Edit image 1. Replace {who} with the {noun} from image 2 and image 3 — same face as image 2, same {part} "
        f"shape and outfit as image 3 ({sil}).",
        f"Keep the exact pose, body position, subject size, framing, camera angle and lens of image 1. Place the "
        f"scene in: {en['location']}. {en['lighting']}",
        f"The {part} is fully inside the frame with 10% headroom above it. {pos.capitalize()} face is unobstructed, "
        f"sharp and evenly lit. {DEADPAN_FRAME}",
        (f"Background: {crowd(en['extras_count'])}, ordinary people busy with their own tasks — {en['extras_tasks']} — "
         f"none of them looking at {obj}, each at least 1.5 m from {obj}, outside {pos} arm reach."
         if int(en.get("extras_count") or 0)
         else f"Remove everyone else: {sub} is the only person in the photograph."),
        "Must look like a real vertical smartphone photo taken in that place: real skin texture, natural exposure, "
        "everything sharp. Exactly one main character. No text, no captions, no watermarks.",
    ])


def gag_prompt(script: dict, page: Page) -> str:
    """Gag pós-motion control (playbook C5): Seedance 2.5, start_image = último frame do clipe de MC, só os stages
    3 e 4 do C4 (aqui, os 2 estágios de gag_followup.en) e o estado final em end_change."""
    en = script["en"]
    g = script["gag_followup"]
    gen = g["en"]
    sub, pos, obj, noun = _p(page)
    part, sil = silhouette(page)
    nm = name(page)
    extras = int(en.get("extras_count") or 0)
    logline = gen.get("gag_sentence") or f"It ends with {_lc(gen['end_change'])}."
    who = f"{nm}, {ROLE_SHORT.get(page.slug, 'the character')} with {_mark(sil)}"
    blocks = [
        "SCENE CONTEXT",
        f"This clip continues a dance video: the start frame is its last frame. EXACTLY 1 main character — {who}"
        + (f" — plus {crowd(extras)} in the background. " if extras else " — and no one else in the set. ")
        + _sent(logline),
        "",
        "ACTIVE REFERENCES",
        "The start frame defines the opening composition, pose, location, lighting, passersby and camera: continue "
        "from it exactly, with no jump.",
        *_ref_lines(nm, pos, part),
        "The image references never change the start-frame composition.",
        "",
        "CAMERA",
        # trend: a câmera é a do vídeo-fonte (o FOV dele, não o da tabela); trava sem zoom para o gag não reenquadrar
        "Same camera position, lens and framing as the start frame, locked off, no zoom. One continuous shot; no cut; "
        "no drift.",
        "",
        "ACTION",
        *_stage_lines(gen["stages"], gen.get("end_change", ""), keep_final_match=False),
        _turn_rule(pos),
        "",
        "PERFORMANCE",
        DEADPAN_VIDEO,
        (f"Passersby continue their own tasks — {en['extras_tasks']} — none turns toward {obj}." if extras else ""),
        "",
        "PHYSICS",
        f"The {part} is one rigid block, hard as molded resin: it moves only with {pos} skull and keeps its exact "
        f"outline in every frame. Still air. Real-time speed, normal playback — no slow motion.",
        "",
        "LIGHTING",
        f"{en['lighting']} Smartphone video look, deep depth of field, everything sharp.",
        "",
        "POSITIVE LOCKS",
        (f"Exactly one main character and {crowd(extras)} for the whole clip. " if extras else
         f"Exactly one person, {nm}, for the whole clip. ")
        + f"{pos.capitalize()} face matches @Image 1 and {pos} {part} matches @Image 2. No captions, no subtitles, "
          f"no text on screen.",
    ]
    return "\n".join(blocks).replace("\n\n\n", "\n\n")


def caption(script: dict) -> str:
    tags = " ".join(t if t.startswith("#") else f"#{t}" for t in script.get("hashtags", []))
    return f"{script['caption'].strip()}\n\n{tags}".strip()
