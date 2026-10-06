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
- tutoriais §11–15 (docs/qa/lint-tutoriais.md): cada referência ligada a um papel e a um nome uma vez; no corpo do
  prompt só o nome, nunca "the man" (B4.11); um beat de piada por estágio, com o dono nomeado (C4); contraparte fora
  do quadro, só o membro entrando pela borda (B4.10); frame B com a luz e a nitidez do A (C2); corte só declarado (B2)
"""
from __future__ import annotations

import json
import re

from . import lint as _lint
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
    """Nome do personagem no prompt (B4.11): o apelido inteiro ('TIA MARLENE', não 'TIA')."""
    return " ".join(str(page.character.get("nickname", page.character.get("name", "HIM"))).upper().split())


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
    """Primeira letra minúscula para emendar no meio da frase; nome em caixa alta ('DONA CIDA', 'GERSINHO') fica."""
    t = (text or "").strip().rstrip(".")
    first = t.split(" ", 1)[0]
    if len(first) > 1 and first.isupper():
        return t
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


# ---------------- C1 ficha da contraparte humana (rodada 7) ----------------

def counterpart_sheet_prompt(script: dict, page: Page, cp: dict) -> str:
    """Ficha C1 da contraparte humana que aparece no quadro (B4.11: "ator humano ganha ficha própria antes de
    qualquer vídeo"). Pessoa fictícia, comum, não reconhecível, e de propósito diferente do protagonista: a ficha
    vira uma imagem a mais nos frames e no vídeo, ligada ao nome dela no ACTIVE REFERENCES."""
    part, _ = silhouette(page)
    who = str(cp["who"]).strip()
    look = str(cp.get("look") or "").strip() or (
        f"an ordinary Brazilian adult who plausibly is {who}, in everyday clothes that fit that role")
    sheet = {
        "type": "character reference sheet, studio photograph, 4 panels in a 2x2 grid",
        "style": "plain documentary studio photograph, flat even soft light, real skin with visible pores and small "
                 "asymmetries, no retouch, sharp focus throughout",
        "background": "flat solid neutral grey #8a8a8a, seamless, no gradient, no shadows on the backdrop",
        "character": f"{who}: {_lc(look)}. An invented, fictional person with an ordinary, non-recognizable face — not "
                     f"a real or famous person and not a lookalike of anyone. Clearly a different person from "
                     f"{name(page)} ({ROLE_SHORT.get(page.slug, 'the main character')}): different face, age, hair and "
                     f"build, no {part}, nothing of {name(page)}'s outfit. Expression: neutral, lips closed, brows level",
        "layout": {
            "top_left": "large close-up portrait, head turned 3/4 to camera-left, eyes to lens, full head with headroom",
            "top_right": "full body front, standing straight, arms relaxed, face readable",
            "bottom_left": "full body true side profile facing frame-left",
            "bottom_right": "full body from behind, standing straight",
        },
        "rules": "same person, same outfit, same scale and lighting in all four panels; exactly one person per panel; "
                 "no text, no labels, no numbers, no logos, no borders thicker than 8 px white",
    }
    return json.dumps(sheet, ensure_ascii=False, indent=2)


def _cps(counterpart) -> list[tuple[str, int]]:
    """Ficha(s) de outras pessoas: (nome, nº da imagem). Aceita uma tupla (rodada 7) ou uma lista (elenco)."""
    if not counterpart:
        return []
    if isinstance(counterpart, tuple) and len(counterpart) == 2 and isinstance(counterpart[1], int):
        return [counterpart]
    return [c for c in counterpart if c]


def _and(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def counterpart_lines(counterpart, noun: str) -> str:
    return " ".join(counterpart_frame_line(w, n, noun) for w, n in _cps(counterpart))


def counterpart_frame_line(cp_who: str, n: int, noun: str) -> str:
    """Linha dos frames A/B: a ficha da contraparte é a imagem n e só ela define essa pessoa."""
    w = cp_who[:1].upper() + cp_who[1:]
    return (f"{w} is defined only by image {n} (a reference sheet on grey): whenever {cp_who} is in the photograph, "
            f"{cp_who}'s face, hair, build and clothes match image {n} exactly. {w} is a different person from the "
            f"{noun}; nothing of the {noun} comes from image {n}, and nothing of {cp_who} comes from the {noun}'s "
            f"images. Do not copy the grey backdrop or the panel layout of image {n}.")


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
    if has_cp and _lint.is_offscreen(cp):
        out.append(_offscreen(cp))
    elif has_cp:
        out.append(_sent(f"{cp['who']}: {_lc(cp.get('position', ''))}, {_lc(cp.get('facing', ''))}"))
    if has_cp:
        if str(cp.get("task") or "").strip():  # playbook B4.6: o parceiro tem tarefa enquanto espera
            out.append(_sent(f"Meanwhile {_lc(cp['who'])} {_lc(cp['task'])}"))
    return " ".join(out)


def _offscreen(cp: dict) -> str:
    """B4.10 (degrau 0): a contraparte fica fora do quadro; só o membro entra pela borda, com vetor de tela.
    Sem segundo rosto no quadro, não há segunda orientação para errar."""
    who = str(cp["who"]).strip()
    m = _lint.EDGE.search(str(cp.get("position") or ""))
    edge = f"the {m.group(1).lower()} edge" if m else "the frame edge"
    limb = _lc(cp.get("limb") or "one arm")
    vector = _lc(cp.get("vector") or "")
    if vector and not re.match(r"(the|his|her|its|their|a|an)\b", vector):
        vector = "it " + vector
    return " ".join(filter(None, [
        _sent(f"{who} stays off-screen beyond {edge}; only {limb} enters the frame" + (f"; {vector}" if vector else "")),
        _sent(f"No face or body of {re.sub(r'^The ', 'the ', who)} appears in the frame")]))


def _possessive(who: str) -> str:
    w = str(who).strip()
    return w + ("'" if w.endswith("s") else "'s")


def _owner(st: dict, nm: str) -> tuple[str, bool]:
    """Dono do beat (C4, videos-analisados §13): `owner` explícito, a contraparte quando é ela quem age no estágio,
    senão o protagonista. Devolve (nome, é_o_protagonista)."""
    if str(st.get("owner") or "").strip():
        o = str(st["owner"]).strip()
        return o, o.upper() == nm.upper()
    cp = st.get("counterpart")
    if isinstance(cp, dict) and cp.get("who"):
        nre = _lint._noun_re(_lint._cp_noun(cp["who"]))
        clauses = [c for c in _lint.CLAUSES.split(str(st.get("text") or "")) if c and c.strip()]
        first = nre.search(clauses[0]) if nre and clauses else None
        me = _lint.PROTAG_REF.search(clauses[0]) if clauses else None
        if any(_lint._cp_acts(c, nre) for c in clauses) or (first and (me is None or first.start() < me.start())):
            return str(cp["who"]).strip(), False
    return nm, True


def _named(text: str, st: dict, nm: str) -> str:
    """Um beat por estágio com o dono nomeado: o primeiro 'he'/'she' sujeito vira o nome (B4.11: o corpo do prompt
    chama o personagem pelo nome); se o dono não aparece no texto, o estágio abre com '<DONO>'s beat:'."""
    owner, mine = _owner(st, nm)
    if mine:
        if re.search(rf"\b{re.escape(nm)}\b", text, re.I):
            return text
        new, n = re.subn(r"(^|[.;:]\s*|,\s*(?:and|then)\s+|\b(?:and|then|while|until)\s+)(he|she)\b",
                         lambda m: m.group(1) + nm, text, count=1, flags=re.I)
        return new if n else f"{_possessive(nm)} beat: {_lc(text)}"
    noun = _lint._cp_noun(owner)
    if noun and re.search(rf"\b{re.escape(noun)}", text, re.I):
        return text
    return f"{_possessive(owner[:1].upper() + owner[1:])} beat: {_lc(text)}"


def _stage_lines(stages: list, end_change: str = "", keep_final_match: bool = True, nm: str = "") -> list[str]:
    """[Stage n — t] texto + orientação + estado final. Sem frame final como âncora (end_change sem end_image),
    o último estado final é o end_change por extenso; com o end_image, basta o end_state curto do roteiro.
    Com `nm`, cada estágio nomeia o dono do beat (C4)."""
    lines = []
    for i, st in enumerate(stages, 1):
        text = st["text"] if keep_final_match else st["text"].replace(" The final frame matches the end frame.", "")
        if nm:
            text = _named(text, st, nm)
        last = i == len(stages)
        end = _lc(end_change) if (last and end_change and not keep_final_match) else _lc(st["end_state"])
        lines.append(" ".join(filter(None, [f"[Stage {i} — {st['t']}] {_sent(text)}",
                                             _orient(st, stages[i - 2] if i > 1 else {}),
                                             f"End state: {end}."])))
    return lines


def _turn_rule(pos: str) -> str:
    return (f"Unless a stage names a turn, {pos} chest stays at 0° to the lens and {pos} hips rotate at most 30°; "
            f"{pos} face is visible in every frame.")


def _ref_lines(nm: str, pos: str, part: str, cast: list | None = None, sheets: dict | None = None) -> list[str]:
    """Mapa de referências pelo conteúdo + papel + nome (o 2.5 casa o material pelo que vê, não só pela ordem).
    B4.11: cada imagem é ligada a um nome uma vez aqui; daí em diante o prompt usa só o nome. Com `cp_image`
    (rodada 7), a ficha da contraparte humana ganha a sua linha de papel."""
    lines = [f"@Image 1 (the close-up face photo on grey) is {nm}'s face reference: it defines {nm}'s face — "
             f"full-preserve, 100% matches the reference.",
             f"@Image 2 (the silhouette sheet on grey) is {nm}'s silhouette reference: it defines only {pos} {part} "
             f"shape and outfit — full-preserve. Do not take the grey backdrop, the panel layout or the extra views."]
    sheets = {str(k).strip().lower(): v for k, v in (sheets or {}).items()}
    for who in cast or []:
        cp_image = sheets.get(who.strip().lower())
        if cp_image:
            lines.append(f"@Image {cp_image} (the 4-panel reference sheet of another person on grey) is "
                         f"{_possessive(who)} reference: it defines {_possessive(who)} face, hair, build and clothes — "
                         f"full-preserve. {who[:1].upper() + who[1:]} is a different person from {nm}; nothing of "
                         f"{who} comes from @Image 1 or @Image 2, and nothing of {nm} comes from @Image {cp_image}. "
                         f"Do not take its grey backdrop or panel layout.")
            continue
        lines.append(f"{who[:1].upper() + who[1:]} is a different person from {nm}, with a face, hair and clothes "
                     f"of their own; nothing of {who} comes from @Image 1 or @Image 2.")
    if cast:
        lines.append(f"From here on each actor is named only by name: {nm}"
                     + "".join(f", {w}" for w in cast) + ".")
    return lines


def _human_cast(stages: list) -> list[str]:
    """Contrapartes humanas do clipe (B4.11), na ordem em que aparecem, sem repetir."""
    out: list[str] = []
    for st in stages or []:
        cp = st.get("counterpart") if isinstance(st, dict) else None
        if _lint.is_human(cp) and str(cp["who"]).strip() not in out:
            out.append(str(cp["who"]).strip())
    return out


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

def _alone(sub: str, counterpart) -> str:
    cps = _cps(counterpart)
    if cps:  # rodada 7: a contraparte com ficha pode estar no quadro; o "only person" a apagaria
        return f"Besides {_and([w for w, _ in cps])}, {sub} is the only person in the photograph."
    return f"{sub.capitalize()} is the only person in the photograph."


def frame_a_prompt(script: dict, page: Page, with_storyboard: bool, counterpart=None) -> str:
    en = script["en"]
    sub, pos, obj, noun = _p(page)
    part, _ = silhouette(page)
    c = cam(script)
    sb = (" Use panel 1 (top-left) of image 3 as the composition guide; render it as one full-frame photograph."
          if with_storyboard else "")
    first = (en.get("stages") or [{}])[0]
    orient = f" Orientation: {_lc(first['facing'])}." if first.get("facing") else ""
    return "\n".join(x for x in [
        f"Vertical 9:16 smartphone photograph, {_fmt(c['frame'], page)}.{sb}",
        f"Location: {en['location']}.",
        f"The {noun} from image 1 and image 2 — same face as image 1, same {part} shape and outfit as image 2 — "
        f"stands {en['position']}, already in {pos} signature pose: {en['signature_pose']}.{orient} {DEADPAN_FRAME}",
        f"The {part} is fully inside the frame with 10% headroom above it. {_fmt(c.get('fill', ''), page)} "
        f"{en.get('hands', '')}".replace("  ", " ").strip(),
        (f"Background: {crowd(en['extras_count'])}, ordinary people busy with their own tasks — {en['extras_tasks']} — "
         f"none of them looking at {obj}." if int(en.get("extras_count") or 0) else _alone(sub, counterpart)),
        f"Props: {en.get('props') or 'none besides the location'}.",
        _featured_line(en),
        counterpart_lines(counterpart, noun),
        f"{en['lighting']} Deep depth of field, everything sharp, smartphone HDR look, real skin texture.",
        "Exactly one main character. No text, no captions, no speech balloons, no watermarks.",
    ] if x)


def frame_b_prompt(script: dict, page: Page, counterpart=None) -> str:
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
        "Same light direction, exposure and sharpness as image 1.",
        counterpart_lines(counterpart, noun),
        DEADPAN_FRAME,
        (f"Exactly one main character, {crowd(en['extras_count'])}, all still busy with their own tasks, "
         f"none looking at {obj}. No text, no balloons." if int(en.get("extras_count") or 0)
         else f"{_alone(sub, counterpart)} No text, no balloons."),
    ]
    return "\n".join(line for line in lines if line and line.strip())


# ---------------- C4 vídeo ----------------

def _cut_line(script: dict) -> str:
    """Plano-sequência por padrão (regra 6); corte só quando o roteiro declara `cut: {at}` (playbook B2)."""
    cut = script.get("cut") or (script.get("en") or {}).get("cut")
    at = cut.get("at") if isinstance(cut, dict) else None
    if at is not None:
        return f"Exactly one HARD CUT at {float(at):g}s; otherwise the camera holds still; no drift mid-shot."
    return "One continuous shot; the camera does not cut on its own; no drift mid-shot."


def video_prompt(script: dict, page: Page, *, has_start: bool, has_end: bool, has_storyboard: bool,
                 repair: str = "", counterpart=None) -> str:
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
    refs += _ref_lines(nm, pos, part, _human_cast(en["stages"]) + _extra_cast(en, counterpart), _sheet_map(counterpart))
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
         f"EXACTLY 1 main character — {who} — and no one else in the set. ") + en["gag_sentence"]
        + (" " + _featured_line(en) if _featured_line(en) else ""),
        "",
        "ACTIVE REFERENCES",
        *refs,
        "",
        "CAMERA",
        _fmt(cam(script)["video"], page) + " " + _cut_line(script),
        "",
        "LOCATION MAP",
        f"{en['location_map']} The set contains only what the start frame shows.",
        "",
        "ACTION",
        *_stage_lines(en["stages"], en.get("end_change", ""), keep_final_match=has_end, nm=nm),
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
          f"Exactly one person, {nm}, for the whole clip. ") + f"{nm}'s "
         f"face matches {pos} face reference (@Image 1) and {pos} {part} matches {pos} silhouette reference "
         f"(@Image 2) at every distance. "
         f"{en.get('props_lock', '')} No captions, no subtitles, no text on screen.").replace("  ", " "),
    ]
    return "\n".join(b for b in blocks if b is not None).replace("\n\n\n", "\n\n")


# ---------------- C5 motion control (Genjutsu / Kling MC: só cena) ----------------

def _intake_text(intake: dict | None, key: str) -> str:
    """Prompt escrito na aba Motion control do painel (motion-intake), limpo e com teto de tamanho."""
    v = (intake or {}).get(key)
    return re.sub(r"\s+\n", "\n", str(v)).strip()[:4000] if isinstance(v, str) and v.strip() else ""


NO_LIKENESS = ("He is a fictional character: do not give him the likeness of any real person, and keep nothing of the "
               "replaced person's face.")


SWAP_KINDS = ("protagonist", "cast", "object", "new_character")


def swaps(intake: dict | None) -> list[dict]:
    """Trocas pedidas na aba Motion control (intake.swaps), limpas: [{target, kind, cast_id, description}].
    Sem swaps, o replace_subject antigo vira uma troca pelo protagonista (compatível com pedidos de antes)."""
    out = []
    for sw in (intake or {}).get("swaps") or []:
        if not isinstance(sw, dict) or not str(sw.get("target") or "").strip():
            continue
        rw = sw.get("replace_with") if isinstance(sw.get("replace_with"), dict) else {}
        kind = str(rw.get("kind") or sw.get("kind") or "protagonist").strip()
        out.append({"target": str(sw["target"]).strip()[:200], "kind": kind if kind in SWAP_KINDS else "object",
                    "cast_id": str(rw.get("cast_id") or "").strip(),
                    "description": str(rw.get("description") or "").strip()[:300]})
    if not out and str((intake or {}).get("replace_subject") or "").strip():
        out.append({"target": str(intake["replace_subject"]).strip(), "kind": "protagonist", "cast_id": "",
                    "description": ""})
    return out


def swap_cast_order(intake: dict | None) -> list[str]:
    """cast_ids das trocas por gente do elenco, na ordem das imagens (image 4, 5, … no frame; depois da ficha no
    Genjutsu). Uma imagem por pessoa."""
    out: list[str] = []
    for sw in swaps(intake):
        if sw["kind"] == "cast" and sw["cast_id"] and sw["cast_id"] not in out:
            out.append(sw["cast_id"])
    return out


def _cast_sheet_role(who: str, n: int, nm: str) -> str:
    return (f"Image {n} (the 4-panel reference sheet of another person on grey) is {_possessive(who)} identity "
            f"reference: {_possessive(who)} face, hair, build and clothes match image {n} exactly. {who} is a "
            f"different person from {nm}; nothing of {nm} comes from image {n}. Do not copy its grey backdrop or "
            f"panel layout.")


def motion_scene_prompt(script: dict, page: Page, with_sheet: bool = True, intake: dict | None = None,
                        cast: list[tuple[str, str]] | None = None) -> str:
    """Prompt de cena do motion control. O movimento vem do vídeo-fonte; o prompt escreve o mundo: papéis das imagens,
    câmera, lugar, luz, rigidez, deadpan e a tarefa de cada figurante (a fonte não traz fundo, videos-analisados §8).

    Com `intake.scene_prompt` (pedido do painel), ele vira o corpo do prompt; os papéis das imagens (dependem da ordem
    em que o pipeline manda as mídias) e as travas inegociáveis (rigidez da silhueta, deadpan, sem rosto real) entram
    sempre."""
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
    first_cast = 4 if with_sheet else 2
    for i, (_cid, who) in enumerate(cast or []):  # elenco trocado na fonte: a ficha dele vem depois da do personagem
        roles += " " + _cast_sheet_role(who, first_cast + i, nm)
    custom = _intake_text(intake, "scene_prompt")
    if custom:
        return "\n\n".join([
            roles,
            custom,
            "LOCKS: " + " ".join([
                f"The {noun}'s {part} is a rigid lacquered solid that moves only as one block with {pos} head and keeps "
                f"its exact outline. Still air.",
                f"{pos.capitalize()} face stays deadpan and visible: lips closed, lip corners level, eyes toward the lens.",
                NO_LIKENESS.replace("He is", f"{sub.capitalize()} is").replace(" him ", f" {obj} "),
                "Body motion and timing come from the source video, with no added cuts. Exactly one main character. "
                "Real-time speed. No captions, no subtitles, no text on screen.",
            ]),
        ])
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


def _swap_lines(sws: list[dict], page: Page, cast: dict[str, tuple[str, int]]) -> list[str]:
    """Uma linha por troca (pessoa ou objeto), cada uma com a sua imagem de referência quando houver."""
    sub, pos, obj, noun = _p(page)
    part, sil = silhouette(page)
    nm = name(page)
    lines = []
    for i, sw in enumerate(sws, 1):
        t = sw["target"]
        if sw["kind"] == "protagonist":
            lines.append(f"{i}. Replace {t} with {nm}, the {noun} from image 2 and image 3 — same face as image 2, "
                         f"same {part} shape and outfit as image 3 ({sil}).")
        elif sw["kind"] == "cast" and sw["cast_id"] in cast:
            who, n = cast[sw["cast_id"]]
            lines.append(f"{i}. Replace {t} with {who}, the person on the reference sheet in image {n} — same face, "
                         f"hair, build and clothes as image {n}; a different person from {nm}. Do not copy the grey "
                         f"backdrop or the panel layout of image {n}.")
        elif sw["kind"] == "object":
            lines.append(f"{i}. Replace {t} with {sw['description'] or 'the object the producer asked for'}, same "
                         f"size, position and hold as the original, real and physically plausible.")
        else:  # new_character ou cast sem ficha: só texto, gente fictícia
            lines.append(f"{i}. Replace {t} with {sw['description'] or 'an ordinary person'}: an invented, fictional "
                         f"person with an ordinary, non-recognizable face, not a lookalike of anyone.")
    return lines


def motion_frame_prompt(script: dict, page: Page, intake: dict | None = None,
                        cast: list[tuple[str, str]] | None = None) -> str:
    """Frame do personagem para motion control = edição do 1º frame do vídeo-fonte (videos-analisados §2).

    image 1 = primeiro frame da fonte, image 2 = rosto, image 3 = silhueta. Com `intake.frame_prompt` (painel), ele é o
    corpo do pedido e as travas (silhueta inteira e rígida, deadpan, sem rosto real, um personagem) vão no fim.
    """
    en = script["en"]
    sub, pos, obj, noun = _p(page)
    part, sil = silhouette(page)
    who = en.get("replace_subject") or (intake or {}).get("replace_subject") or "the dancer"
    custom = _intake_text(intake, "frame_prompt")
    sws = swaps(intake)
    cast_map = {cid: (w, 4 + i) for i, (cid, w) in enumerate(cast or [])}
    multi = len(sws) > 1 or any(sw["kind"] != "protagonist" for sw in sws)
    if multi:  # várias trocas (painel, aba Motion control): uma linha por pessoa ou objeto, cada uma com a sua imagem
        roles = [f"Image 1 is the first frame of the source video. Image 2 (face close-up) and image 3 (silhouette "
                 f"sheet) are {name(page)}'s identity references."]
        roles += [f"Image {n} (a 4-panel reference sheet on grey) defines {w}." for w, n in cast_map.values()]
        body = custom if custom else "\n".join([
            "Edit image 1. Make exactly these replacements, one per person or object, and nothing else:",
            *_swap_lines(sws, page, cast_map),
            "Everyone and everything not listed stays exactly as in image 1.",
            f"Keep the exact pose, body position, subject size, framing, camera angle and lens of image 1. Place the "
            f"scene in: {en['location']}. {en['lighting']}"])
        if not body.lower().startswith("edit image 1"):
            body = "Edit image 1.\n" + body
        if custom:  # o texto do painel venceu, mas toda troca pedida tem de estar nele (com a sua imagem)
            miss = [ln for sw, ln in zip(sws, _swap_lines(sws, page, cast_map)) if sw["target"].lower() not in body.lower()
                    or (sw["kind"] == "cast" and sw["cast_id"] in cast_map
                        and f"image {cast_map[sw['cast_id']][1]}" not in body.lower())]
            if miss:
                body += "\nAlso make these replacements:\n" + "\n".join(miss)
        return "\n".join([
            body,
            " ".join(roles),
            f"Locks: {name(page)}'s {part} is fully inside the frame with 10% headroom above it, one rigid solid with "
            f"its exact outline. {DEADPAN_FRAME} Every replaced person is a fictional character: no likeness of any real "
            f"person, nothing of the replaced people's faces.",
            "Must look like a real vertical smartphone photo: real skin texture, natural exposure, everything sharp. "
            f"Exactly one main character, {name(page)}. No text, no captions, no watermarks.",
        ])
    if custom:
        if not custom.lower().startswith("edit image 1"):
            custom = (f"Edit image 1. Replace {who} with the {noun} from image 2 and image 3 — same face as image 2, "
                      f"same {part} shape and outfit as image 3 ({sil}).\n" + custom)
        return "\n".join([
            custom,
            f"Locks: the {part} is fully inside the frame with 10% headroom above it, one rigid solid with its exact "
            f"outline. {DEADPAN_FRAME} " + NO_LIKENESS.replace("He is", f"{sub.capitalize()} is").replace(" him ", f" {obj} "),
            "Must look like a real vertical smartphone photo: real skin texture, natural exposure, everything sharp. "
            "Exactly one main character. No text, no captions, no watermarks.",
        ])
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


def _sheet_map(counterpart) -> dict:
    """{nome: nº da imagem} das fichas de outras pessoas (contraparte avulsa e elenco)."""
    return {w: n for w, n in _cps(counterpart)}


def _extra_cast(en: dict, counterpart=None) -> list[str]:
    """Figurantes em destaque (en.featured_extras) e quem tem ficha mas não é contraparte: entram no ACTIVE
    REFERENCES com a linha de papel (ficha) ou de exclusão (sem ficha)."""
    have = {w.lower() for w in _human_cast(en.get("stages") or [])}
    out: list[str] = []
    for ex in _lint.featured_extras({"en": en}):
        w = ex.get("who") or ""
        if w and w.lower() not in have and w not in out:
            out.append(w)
    for w, _ in _cps(counterpart):
        if w.lower() not in have and w not in out:
            out.append(w)
    return out


def _featured_line(en: dict) -> str:
    """Figurantes em destaque: nome, posição e tarefa (B4.6), fora da contagem de passantes."""
    parts = []
    for ex in _lint.featured_extras({"en": en}):
        if not ex.get("who"):
            continue
        bits = ", ".join(x for x in (_lc(ex.get("position", "")), _lc(ex.get("task", ""))) if x)
        parts.append(f"{ex['who']}" + (f" ({bits})" if bits else ""))
    if not parts:
        return ""
    return _sent("Featured extras, besides the passersby: " + "; ".join(parts) + "; none of them looks at the lens")


def gag_prompt(script: dict, page: Page, counterpart=None) -> str:
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
        *_ref_lines(nm, pos, part, _human_cast(gen["stages"]) + [w for w, _ in _cps(counterpart)
                                                                   if w.lower() not in {x.lower() for x in _human_cast(gen["stages"])}],
                    _sheet_map(counterpart)),
        "The image references never change the start-frame composition.",
        "",
        "CAMERA",
        # trend: a câmera é a do vídeo-fonte (o FOV dele, não o da tabela); trava sem zoom para o gag não reenquadrar
        "Same camera position, lens and framing as the start frame, locked off, no zoom. "
        + (_cut_line(g) if g.get("cut") or gen.get("cut") else "One continuous shot; no cut; no drift."),
        "",
        "ACTION",
        *_stage_lines(gen["stages"], gen.get("end_change", ""), keep_final_match=False, nm=nm),
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
        + f"{nm}'s face matches {pos} face reference (@Image 1) and {pos} {part} matches {pos} silhouette reference "
          f"(@Image 2). No captions, no subtitles, no text on screen.",
    ]
    return "\n".join(blocks).replace("\n\n\n", "\n\n")


def caption(script: dict) -> str:
    tags = " ".join(t if t.startswith("#") else f"#{t}" for t in script.get("hashtags", []))
    return f"{script['caption'].strip()}\n\n{tags}".strip()
