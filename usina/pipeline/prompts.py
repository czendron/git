"""Monta os prompts de ficha, storyboard, frames e vídeo seguindo playbook/seedance-master.md (templates C1–C5).

Fonte da verdade: o roteiro (JSON, bloco `en`) mais a bíblia da página. Regras-chave aplicadas aqui:
- identidade vem das imagens (rosto.png = @Image 1, silhueta.png = @Image 2); texto de identidade mínimo (regra 8)
- 4 estágios B0–B3 com estado final; "moments of ONE continuous shot" (regras 5–7)
- tempo real em BPM, nunca "slow"; câmera lenta proibida pelo nome (regra 19)
- orientação travada em graus a partir da câmera; olhar na lente escrito (regra 18)
- topete/laquê/bigode descrito como material, medida e marco corporal (regra 17)
- cabeçalho de contagem: EXACTLY 1 main character + N passersby (regra 13)
"""
from __future__ import annotations

import json

from .store import Page

PRONOUN = {"he": ("he", "his", "him", "man"), "she": ("she", "her", "her", "woman")}

CAMERA = {
    "selfie_pov": {
        "fov": 84,
        "frame": "selfie taken by the {noun} with the front camera at arm's length, 84° wide-angle, phone 55 cm from {pos} face, lens slightly below eye level",
        "video": ("Front smartphone camera held at arm's length by {pos} own right hand, 84° field of view, 55 cm from "
                  "{pos} face, lens slightly below eye level. {Pos} right arm extends toward the lens and exits the "
                  "bottom-right frame edge."),
        "storyboard": "84° selfie at arm's length",
    },
    "static_passerby": {
        "fov": 63,
        "frame": "static phone on a passerby's tripod at chest height, 63° field of view, 4 m away",
        "video": "Static smartphone on a tripod at chest height, 63° field of view, 4 m from {obj}, locked off.",
        "storyboard": "63° static from 4 m",
    },
    "static_low": {
        "fov": 63,
        "frame": "static phone resting 40 cm above the ground, tilted up 10°, 63° field of view, 3 m away",
        "video": "Static smartphone resting 40 cm above the ground, tilted up 10°, 63° field of view, 3 m from {obj}, locked off.",
        "storyboard": "63° static low angle from 3 m",
    },
}

# Silhueta rígida de cada personagem, como material + medida + marco corporal (regra 17).
SILHOUETTE = {
    "gersinho": ("pompadour", "a giant black lacquered pompadour rising 25 cm above the forehead, as tall as his own "
                 "head, glossy, rigid like molded resin, every strand fused into one smooth solid shape"),
    "marlene": ("hair dome", "an enormous coppery hairsprayed bouffant shaped into a perfect dome twice as wide as her "
                "shoulders, rigid like a lacquered helmet, every strand fused into one smooth solid shell"),
    "wanderley": ("mustache", "a black waxed horizontal mustache extending straight out to both sides, wider than his "
                  "shoulders, rigid like a carved bar of resin, tips perfectly level"),
}

ROLE = {
    "gersinho": "a slim brega singer in a shiny tropical-print silk shirt open at the chest, a thick gold chain and white flared trousers",
    "marlene": "a Brazilian auntie in a pastel-pink shoulder-pad blazer suit, huge cat-eye glasses and red nails",
    "wanderley": "a stocky Brazilian uncle in a faded trucker cap, a white tank top, blue tactel shorts and socks with flip-flops",
}

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


def _fmt(text: str, page: Page) -> str:
    sub, pos, obj, noun = _p(page)
    return text.format(noun=noun, pos=pos, Pos=pos.capitalize(), obj=obj, sub=sub)


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
    times = [st["t"] for st in en["stages"]] if len(en["stages"]) == n else [p.get("t", "") for p in script["storyboard_panels"]]
    sb = {
        "type": f"photographic storyboard, {n} panels in a {grid} grid, read left to right, top to bottom, thin white gutters",
        "style": f"vertical smartphone photographs, natural daylight, identical camera position and field of view in "
                 f"every panel ({cam(script)['storyboard']})",
        "character": f"the {noun} from image 1 (face) and image 2 ({part}, outfit); exactly one main character in "
                     f"every panel; deadpan in every panel: lips closed, lip corners level, eyes into the lens",
        "location": f"{en['location']}; exactly {en['extras_count']} passersby in every panel, each busy with their "
                    f"own task ({en['extras_tasks']}), none looking at {obj}",
        "panels": [{"position": p, "time": t, "state": s} for p, t, s in zip(pos_list, times, panels)],
        "rules": f"same outfit, same {part} shape and size in every panel; props exactly as listed per panel "
                 f"({en.get('props', 'none')}); no text, no numbers, no speech balloons, no arrows",
    }
    return json.dumps(sb, ensure_ascii=False, indent=2), size


# ---------------- C2 frames ----------------

def frame_a_prompt(script: dict, page: Page, with_storyboard: bool) -> str:
    en = script["en"]
    sub, pos, obj, noun = _p(page)
    part, _ = silhouette(page)
    sb = (" Use panel 1 (top-left) of image 3 as the composition guide; render it as one full-frame photograph."
          if with_storyboard else "")
    return "\n".join([
        f"Vertical 9:16 smartphone photograph, {_fmt(cam(script)['frame'], page)}.{sb}",
        f"Location: {en['location']}.",
        f"The {noun} from image 1 and image 2 — same face as image 1, same {part} shape and outfit as image 2 — "
        f"stands {en['position']}, already in {pos} signature pose: {en['signature_pose']}. {DEADPAN_FRAME}",
        f"The {part} is fully inside the frame with 10% headroom above it.",
        f"Background: exactly {en['extras_count']} ordinary passersby busy with their own tasks — {en['extras_tasks']} — "
        f"none of them looking at {obj}.",
        f"Props: {en.get('props') or 'none besides the location'}.",
        f"{en['lighting']} Deep depth of field, everything sharp, smartphone HDR look, real skin texture.",
        "Exactly one main character. No text, no captions, no speech balloons, no watermarks.",
    ])


def frame_b_prompt(script: dict, page: Page) -> str:
    en = script["en"]
    sub, pos, obj, noun = _p(page)
    part, _ = silhouette(page)
    return "\n".join([
        f"Edit image 1. Keep the exact same camera position, field of view, location, lighting, passersby layout and "
        f"the {noun}'s identity (face from image 2, {part} and outfit from image 3).",
        f"Change only: {en['end_change']}.",
        en.get("vacated", "") or "",
        en.get("end_props", "") or "",
        DEADPAN_FRAME,
        f"Exactly one main character, exactly {en['extras_count']} passersby, all still busy with their own tasks, "
        f"none looking at {obj}. No text, no balloons.",
    ]).replace("\n\n", "\n")


# ---------------- C4 vídeo ----------------

def video_prompt(script: dict, page: Page, *, has_start: bool, has_end: bool, has_storyboard: bool,
                 repair: str = "") -> str:
    en = script["en"]
    sub, pos, obj, noun = _p(page)
    part, sil = silhouette(page)
    nm = name(page)
    bpm = script.get("music", {}).get("bpm") or page.character.get("bpm", 95)
    refs = []
    if has_start or has_end:
        refs.append(" ".join(filter(None, [
            "The start frame defines the opening composition, positions, pose and camera." if has_start else "",
            "The end frame defines the final composition and the gag's end state." if has_end else ""])))
    refs.append(f"@Image 1 defines {nm}'s face — full-preserve, 100% matches the reference.")
    refs.append(f"@Image 2 defines only {pos} {part} shape and outfit — full-preserve. Do not take the grey backdrop, "
                f"the panel layout or the extra views.")
    if has_storyboard:
        stg = en["stages"]
        mapping = ", ".join(f"panel {i + 1} is {s['t']}" for i, s in enumerate(stg))
        refs.append(f"@Image 3 provides a {len(stg)}-panel storyboard read left to right, top to bottom: {mapping}. "
                    f"The panels are moments of ONE continuous shot. Do not reorder; do not invent shots; do not use "
                    f"its gutters.")
    action = []
    for i, st in enumerate(en["stages"], 1):
        action.append(f"[Stage {i} — {st['t']}] {st['text']} End state: {st['end_state']}")
    blocks = []
    if repair:
        blocks += ["REPAIR SCOPE", repair, ""]
    blocks += [
        "SCENE CONTEXT",
        f"EXACTLY 1 main character — {nm}, {ROLE.get(page.slug, 'the character')}, with {sil.split(',')[0]} — plus "
        f"exactly {en['extras_count']} background passersby. {en['gag_sentence']}",
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
        *action,
        f"Throughout: real-time at {bpm} BPM; {pos} chest stays square to the lens, hips rotate at most 30°, {pos} face "
        f"is visible in every frame.",
        "",
        "PERFORMANCE",
        DEADPAN_VIDEO,
        f"Passersby continue their own tasks — {en['extras_tasks']} — each moving on their own rhythm; none turns toward {obj}.",
        "",
        "PHYSICS",
        f"The {part} is a single rigid mass — {sil}: it moves only as one solid block with {pos} skull and keeps its "
        f"exact outline in every frame. Still air. Feet keep ground contact, heel lands first, weight visibly "
        f"transfers. {en['hands']} Real-time speed, normal playback — no slow motion.",
        "",
        "LIGHTING",
        f"{en['lighting']} Smartphone video look, deep depth of field, everything sharp.",
        "",
        "POSITIVE LOCKS",
        f"Exactly one main character and exactly {en['extras_count']} passersby for the whole clip. {pos.capitalize()} "
        f"face matches @Image 1 and {pos} {part} matches @Image 2 at every distance. "
        f"{en.get('props_lock', '')} No captions, no subtitles, no text on screen.".replace("  ", " "),
    ]
    return "\n".join(blocks)


# ---------------- C5 motion control (Kling MC: só cena) ----------------

def motion_scene_prompt(script: dict, page: Page) -> str:
    en = script["en"]
    sub, pos, obj, noun = _p(page)
    part, sil = silhouette(page)
    return (f"Keep the scene, lighting and passersby from the character image. {en['lighting']} "
            f"{en['location']}, smartphone video look, everything sharp. The {noun}'s {part} is a rigid lacquered "
            f"solid that moves only as one block with {pos} head and keeps its exact outline. {pos.capitalize()} face stays "
            f"deadpan: lips closed, lip corners level, eyes toward the lens. Exactly {en['extras_count']} passersby "
            f"continue their own tasks; none looks at {obj}. Real-time speed.")


def caption(script: dict) -> str:
    tags = " ".join(t if t.startswith("#") else f"#{t}" for t in script.get("hashtags", []))
    return f"{script['caption'].strip()}\n\n{tags}".strip()
