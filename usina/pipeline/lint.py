"""Validador de roteiro (ata D9). Nada é gerado se o roteiro não passar aqui.

Erros bloqueiam; avisos aparecem mas deixam passar.
"""
from __future__ import annotations

import re

REQUIRED = ["page", "title", "format", "premise", "gag_without_sound", "location", "camera", "beats",
            "character_actions_count", "duration_s", "end_state", "storyboard_panels", "start_frame",
            "caption", "hashtags", "self_score", "en"]
EN_REQUIRED = ["gag_sentence", "location", "location_map", "position", "signature_pose", "extras_count", "extras_tasks",
               "hands", "stages", "end_change", "lighting", "panels"]
SLOW = re.compile(r"\b(slow(?!(?: deliberate)? blink)|slowly|graceful|gracefully|smooth|smoothly|slow-motion|slo-mo)\b", re.I)
WIND = re.compile(r"\b(wind|breeze|flowing|windy)\b", re.I)
FORMATS = {"proprio", "trend", "crossover"}
CAMERA_MODES = {"static_passerby", "selfie_pov", "static_low", "static_high", "tracking_side"}
FOV_STEPS = {8, 12, 18, 29, 47, 63, 84, 107, 180}

# Palavras que denunciam ação abstrata/invisível (lição do vídeo da laje).
ABSTRACT = ["desafia", "desafiando", "responde ao", "ofendid", "orgulh", "decide ", "pensa ", "lembra ",
            "sente ", "percebe", "imagina", "sonha", "vibe", "energia", "épico", "epico", "clima de"]
# Brand safety (ata D8 / fórmula da casa).
UNSAFE = ["camisa de time", "camisa do flamengo", "corinthians", "palmeiras", "igreja", "pastor", "padre",
          "bolsonaro", "lula", "cerveja", "cachaça", "cigarro", "arma", "revólver", "biquíni", "sensual",
          "criança em destaque", "bebê no colo", "jean phil", "jeanphil", "token", "cripto", "pix"]
BACK = re.compile(r"\b(de costas|costas para a c[aâ]mera|back to (the )?camera|turns? (his|her) back)\b", re.I)


def _text(obj) -> str:
    if isinstance(obj, dict):
        return " ".join(_text(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_text(v) for v in obj)
    return str(obj or "")


def _span(t: str) -> tuple[float, float] | None:
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*s?\s*$", str(t))
    return (float(m.group(1)), float(m.group(2))) if m else None


TREND_REQUIRED = ["page", "title", "format", "premise", "gag_without_sound", "camera", "duration_s", "caption",
                  "hashtags", "self_score", "music", "trend", "en"]
TREND_EN = ["location", "lighting", "extras_count", "extras_tasks", "replace_subject"]


def trend_key(name) -> str:
    """Nome da trend normalizado (ata D7: a mesma trend nunca em 2 páginas na mesma semana).

    Sem acento, caixa, pontuação e o que vem entre parênteses (artista/versão): "Gang Gang (Chef Boy)" == "gang-gang".
    """
    import unicodedata
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", str(name or ""))
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", t))


def lint_trend(script: dict, page: dict | None = None) -> tuple[list[str], list[str]]:
    """Roteiro de trend (motion control): o movimento vem do vídeo-fonte; o roteiro define cenário, figurantes e piada."""
    errors: list[str] = []
    warns: list[str] = []
    for k in TREND_REQUIRED:
        if k not in script or script[k] in (None, "", [], {}):
            errors.append(f"falta o campo '{k}'")
    if errors:
        return errors, warns
    for k in TREND_EN:
        if script["en"].get(k) in (None, ""):
            errors.append(f"falta en.{k}")
    try:
        if not 0 <= int(script["en"].get("extras_count", 0)) <= 12:
            errors.append("en.extras_count deve ficar entre 0 e 12")
    except (TypeError, ValueError):
        errors.append("en.extras_count deve ser um número")
    if WIND.search(_text(script["en"])):
        warns.append("vento/brisa no bloco en: faz o cabelo rígido balançar (regra 17)")
    tr = script["trend"]
    if not tr.get("name") or not tr.get("source_hint"):
        errors.append("trend precisa de name e source_hint (de onde vem o vídeo-fonte)")
    dur = float(script["duration_s"])
    if not 3 <= dur <= 15:
        errors.append(f"duração {dur}s fora de 3–15 s para motion control (corte a fonte no trecho da coreografia)")
    if SLOW.search(_text(script["en"])):
        errors.append("bloco en com palavra de câmera lenta (regra 19)")
    scan = {k: v for k, v in script.items() if k not in ("brand_safety", "risks", "originality_note")}
    full = _text(scan).lower()
    for w in UNSAFE:
        if re.search(r"(?<![\wà-ú])" + re.escape(w) + r"(?![\wà-ú])", full):
            errors.append(f"brand safety: '{w}'")
    low = [k for k, v in script["self_score"].items() if isinstance(v, (int, float)) and v < 3]
    if low:
        errors.append(f"self_score abaixo de 3 em: {', '.join(low)}")
    if page and script["page"] != page.get("slug"):
        errors.append(f"page '{script['page']}' não bate com '{page.get('slug')}'")
    if script.get("gag_followup") is not None:
        e, w = lint_gag(script["gag_followup"])
        errors += e
        warns += w
    return errors, warns


def lint_gag(g) -> tuple[list[str], list[str]]:
    """Gag pós-motion control (playbook C5): clipe Seedance de 4–5 s a partir do último frame do MC,
    com os 2 últimos estágios do C4 (en.stages de 2 + en.end_change)."""
    errors: list[str] = []
    warns: list[str] = []
    if not isinstance(g, dict):
        return ["gag_followup precisa ser um objeto {duration_s, en: {stages, end_change}}"], warns
    dur = float(g.get("duration_s") or 0)
    if not 4 <= dur <= 5:
        errors.append(f"gag_followup.duration_s {dur}s fora de 4–5 s")
    en = g.get("en") or {}
    stages = en.get("stages") or []
    if len(stages) != 2:
        errors.append(f"gag_followup.en.stages tem {len(stages)} estágios (use 2: a armação e a piada)")
    end = 0.0
    for i, st in enumerate(stages, 1):
        if not isinstance(st, dict) or not st.get("text") or not st.get("end_state"):
            errors.append(f"gag_followup.en.stages[{i}] precisa de t, text e end_state")
            continue
        sp = _span(st.get("t", ""))
        if not sp:
            errors.append(f"gag_followup.en.stages[{i}]: tempo '{st.get('t')}' inválido")
            continue
        if abs(sp[0] - end) > 0.01:
            errors.append(f"gag_followup.en.stages[{i}] começa em {sp[0]}s; o anterior terminou em {end}s")
        end = sp[1]
    if stages and dur and abs(end - dur) > 0.51:
        errors.append(f"gag_followup.en.stages terminam em {end}s, mas duration_s é {dur}")
    if not en.get("end_change"):
        errors.append("falta gag_followup.en.end_change (o estado final da piada)")
    if SLOW.search(_text(en)):
        errors.append("gag_followup.en com palavra de câmera lenta (regra 19)")
    if WIND.search(_text(en)):
        warns.append("vento/brisa no gag_followup: faz o cabelo rígido balançar (regra 17)")
    return errors, warns


def lint(script: dict, page: dict | None = None) -> tuple[list[str], list[str]]:
    """Valida o roteiro. Roteiro malformado (tipo errado num campo) vira erro de lint, nunca traceback."""
    if not isinstance(script, dict):
        return ["o roteiro precisa ser um objeto JSON"], []
    try:
        if script.get("format") == "trend":
            return lint_trend(script, page)
        return _lint(script, page)
    except (TypeError, ValueError, AttributeError, KeyError) as e:
        return [f"roteiro malformado ({type(e).__name__}: {e}); confira os tipos dos campos"], []


def _lint(script: dict, page: dict | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    for k in REQUIRED:
        if k not in script or script[k] in (None, "", [], {}):
            errors.append(f"falta o campo '{k}'")
    if errors:
        return errors, warns

    en = script["en"]
    for k in EN_REQUIRED:
        if not en.get(k):
            errors.append(f"falta en.{k}")
    stages = en.get("stages") or []
    if not 3 <= len(stages) <= 4:
        errors.append(f"en.stages tem {len(stages)} estágios (use a grade B0–B3: 4, ou 3 em clipes de 8 s)")
    send = 0.0
    for i, st in enumerate(stages, 1):
        if not isinstance(st, dict) or not st.get("text") or not st.get("end_state"):
            errors.append(f"en.stages[{i}] precisa de t, text e end_state")
            continue
        sp = _span(st.get("t", ""))
        if not sp:
            errors.append(f"en.stages[{i}]: tempo '{st.get('t')}' inválido")
            continue
        if abs(sp[0] - send) > 0.01:
            errors.append(f"en.stages[{i}] começa em {sp[0]}s; o anterior terminou em {send}s")
        send = sp[1]
        if i == 2 and sp[1] - sp[0] < 1.5 * 2:
            warns.append("estágio da assinatura curto (<3 s): cada movimento precisa de ≥1,5 s")
        if i == len(stages) - 1 and sp[1] - sp[0] < 1.5:
            warns.append("estágio do gag com menos de 1,5 s")
    if stages and abs(send - float(script.get("duration_s", 0))) > 0.51:
        errors.append(f"en.stages terminam em {send}s, mas duration_s é {script.get('duration_s')}")
    if isinstance(en.get("panels"), list) and stages and len(en["panels"]) != len(stages):
        errors.append("en.panels precisa ter um painel por estágio (mesmo número)")
    if SLOW.search(_text(en)):
        errors.append(f"bloco en usa '{SLOW.search(_text(en)).group(0)}': vira câmera lenta. Escreva o andamento em BPM (regra 19)")
    if WIND.search(_text(en)):
        warns.append("vento/brisa no bloco en: faz o cabelo rígido balançar (regra 17)")
    try:
        if not 0 <= int(en.get("extras_count", 0)) <= 12:
            errors.append("en.extras_count deve ficar entre 0 e 12")
    except (TypeError, ValueError):
        errors.append("en.extras_count deve ser um número")
    if script["format"] not in FORMATS:
        errors.append(f"format inválido: {script['format']}")
    dur = float(script["duration_s"])
    if not 6 <= dur <= 15:
        errors.append(f"duração {dur}s fora de 6–15 s")

    acts = int(script["character_actions_count"])
    limit = 3 if dur >= 12 else 2
    if acts > limit:
        errors.append(f"{acts} ações do personagem em {dur:.0f}s (máximo {limit}); corte para dança/gesto + piada")

    beats = script["beats"]
    if not 1 <= len(beats) <= 3:
        errors.append(f"{len(beats)} beats (use 1–3)")
    end = 0.0
    for i, b in enumerate(beats, 1):
        sp = _span(b.get("t", ""))
        if not sp:
            errors.append(f"beat {i}: tempo '{b.get('t')}' não está no formato '0-6s'")
            continue
        if abs(sp[0] - end) > 0.01:
            errors.append(f"beat {i}: começa em {sp[0]}s, mas o anterior terminou em {end}s")
        end = sp[1]
        if not b.get("facing"):
            errors.append(f"beat {i}: diga para onde o personagem olha ('facing')")
        if BACK.search(_text(b)) and "costas" not in script.get("premise", ""):
            errors.append(f"beat {i}: personagem de costas para a câmera (só se a piada for isso)")
        # uma ação por beat: muitos verbos encadeados = confusão
        action = str(b.get("action", ""))
        chained = len(re.findall(r";| e depois | depois | então | then | and then ", action))
        if chained >= 2:
            warns.append(f"beat {i}: ação com muitas etapas encadeadas ({chained + 1}); simplifique")
    if beats and abs(end - dur) > 0.51:
        errors.append(f"os beats terminam em {end}s, mas a duração é {dur}s")

    cam = script["camera"]
    if cam.get("mode") not in CAMERA_MODES:
        errors.append(f"camera.mode inválido: {cam.get('mode')} (use {sorted(CAMERA_MODES)})")
    fov = cam.get("fov_deg")
    if fov is not None and int(fov) not in FOV_STEPS:
        errors.append(f"camera.fov_deg {fov} fora da tabela {sorted(FOV_STEPS)}")

    panels = script["storyboard_panels"]
    if not 3 <= len(panels) <= 6:
        errors.append(f"{len(panels)} painéis de storyboard (use 3–6 para 8–12 s)")
    if fov is not None and script["camera"].get("mode") == "selfie_pov" and int(fov) != 84:
        warns.append("selfie usa 84° (playbook regra 21)")
    if fov is not None and script["camera"].get("mode") == "static_passerby" and int(fov) != 63:
        warns.append("passante usa 63° (playbook regra 21)")

    scan = {k: v for k, v in script.items() if k not in ("brand_safety", "risks", "originality_note")}
    full = _text(scan).lower()
    for w in ABSTRACT:
        if w in full:
            warns.append(f"palavra abstrata '{w.strip()}': troque por algo visível")
    for w in UNSAFE:
        if re.search(r"(?<![\wà-ú])" + re.escape(w) + r"(?![\wà-ú])", full):
            errors.append(f"brand safety: '{w}'")

    tags = script["hashtags"]
    if not 3 <= len(tags) <= 5:
        warns.append(f"{len(tags)} hashtags (ideal 3–5)")
    if len(script["caption"]) > 220:
        warns.append("legenda longa (>220 caracteres)")

    sc = script["self_score"]
    low = [k for k, v in sc.items() if isinstance(v, (int, float)) and v < 3]
    if low:
        errors.append(f"self_score abaixo de 3 em: {', '.join(low)}")

    if page:
        ch = page.get("character", {})
        if script["page"] != page.get("slug"):
            errors.append(f"page '{script['page']}' não bate com '{page.get('slug')}'")
        if ch.get("bpm") and script.get("music", {}).get("bpm"):
            if abs(int(script["music"]["bpm"]) - int(ch["bpm"])) > 25:
                warns.append(f"BPM {script['music']['bpm']} longe do BPM do personagem ({ch['bpm']})")
    if script.get("props") and not script.get("end_frame"):
        warns.append("há props na piada mas não há end_frame; considere controlar o fim com um frame final")
    return errors, warns
