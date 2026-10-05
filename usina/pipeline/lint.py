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


# ---- crítica de prompt (docs/qa/critica-prompts.md): falhas mecanicamente detectáveis ----
DEG = re.compile(r"\d+(?:\.\d+)?\s*(?:°|deg\b|degrees?\b)", re.I)
LENS = re.compile(r"\b(lens|camera)\b", re.I)
BACK_EN = re.compile(r"\b(180\s*°|back (is )?(turned )?to(ward)? the (lens|camera)|turns? (his|her) back|faces? away)", re.I)
# Outro ator (gente ou bicho) + verbo de interação na mesma oração = precisa dizer quem encara quem.
ACTOR = re.compile(r"\b(man|woman|men|women|boy|girl|guy|lady|person|someone|stranger|another|passerby|passersby|"
                   r"passenger|pedestrian|vendor|driver|worker|boxer|opponent|fighter|partner|referee|"
                   r"dog|cat|seagull|pigeon|bird|horse|chicken|monkey)\b", re.I)
INTERACT = re.compile(r"\b(punch\w*|hit|hits|hitting|strik\w*|slap\w*|kick\w*|push\w*|shov\w*|grab\w*|pull\w*|"
                      r"hug\w*|kiss\w*|hands? (him|her)|giv\w*|offer\w*|throw\w*|toss\w*|catch\w*|touch\w*|"
                      r"tap\w*|bump\w*|lands?|landing|perch\w*|approach\w*|walks? up to|faces?|facing|"
                      r"confront\w*|swing\w* at|block\w*|dodg\w*|steps? toward)\b", re.I)
# Verbos vagos: o modelo escolhe sozinho o que fazer (regra 20; o "desafia o boxe" virou soco).
VAGUE = re.compile(r"\b(dances|dancing|does a dance|fights?|fighting|spars?|sparring|reacts?|reacting|interacts?|"
                   r"interacting|confronts?|plays? with|messes with|moves around|grooves?|vibes?)\b", re.I)
ABSTRACT_END = re.compile(r"readable as a cover|frozen result|as before|same as above|the gag lands|it works", re.I)
CROWD = re.compile(r"\b(crowded|crowd|packed|full of people|throngs?|lotad[oa])\b", re.I)
NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
       "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
CAMERA_FOV = {"selfie_pov": 84, "static_passerby": 63, "static_low": 63, "static_high": 63, "tracking_side": 63}


def task_count(tasks: str) -> int | None:
    """Soma das pessoas com tarefa em en.extras_tasks ("two joggers ..., one vendor ...") ou None se ilegível."""
    total, found = 0, False
    for clause in re.split(r"[,;]|\band (?=(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b)",
                           str(tasks or "")):
        m = re.match(r"\s*(?:and\s+)?(\d+|[a-z]+)\b", clause.lower())
        if m and (m.group(1).isdigit() or m.group(1) in NUM):
            total += int(m.group(1)) if m.group(1).isdigit() else NUM[m.group(1)]
            found = True
    return total if found else None


# ---- playbook B4 (cena com contraparte), as partes mecanicamente checáveis (rodada 5) ----
# 1. contraparte atrás dele: o modelo gira o corpo inteiro para encará-la ("nunca atrás"). Atrás de um móvel
#    (balcão, banca, vidro) não é atrás dele.
BEHIND = re.compile(r"\b(behind|atr[aá]s|in back of|at (his|her) back)\b(?!\s+(?:(?:the|a|an|his|her)\s+)?(?:\w+\s+)?"
                    r"(counter|stall|stand|kiosk|desk|table|bar|window|glass|fence|railing|wall|cart|register|"
                    r"turnstile|car|bus|door|gate|balc[aã]o|banca|vidro|mesa|grade)\b)", re.I)
BEHIND_CP_FACING = re.compile(r"\b((at|toward|towards|on|facing|faces) (his|her) back|behind (him|her)|nas costas del[ea]|atr[aá]s del[ea])\b",
                              re.I)
# 7. contato/golpe: mais de um num clipe = mais de um clipe
CONTACT = re.compile(r"\b(punch(es|ed|ing)?|hits?|hitting|strik(es?|ing)|struck|slap\w*|kick\w*|push(es|ed|ing)?|shov\w*|"
                     r"jab\w*|smack\w*|headbutt\w*|tackl\w*|grab\w*|pok(e|es|ing)|taps?|tapping|pecks?|pecking|"
                     r"bumps?|knocks?|collid\w*|lands? (on|against)|landing on|stops? against|slams?)\b", re.I)
REPEAT = re.compile(r"\b(twice|two times|three times|\d+ times|again|repeatedly|several times|a few times|"
                    r"one after another|combo|flurry)\b", re.I)
ON_CONTACT = re.compile(r"\b(on|after|at the) contact\b", re.I)
# 5. um ator age por estágio: o que conta como ação da contraparte (gesto de espera não conta)
CP_ACT = re.compile(CONTACT.pattern[:-3] + r"|glid\w*|fl(y|ies|ew)|flaps?|swoops?|walks?|runs?|jumps?|swings?|throws?|"
                    r"toss\w*|travels?|lunges?|steps? (in|toward|towards|forward)|reach(es)?|approach\w*|gives?|"
                    r"offers?|hands? (him|her)|pulls?|drops?|charges?|dives?|enters?|comes? in)\b", re.I)
PROTAG_SUBJ = re.compile(r"^\s*(?:(?:on contact|then|meanwhile|now|still|and|but|at the same time)[\s,]+)*"
                         r"(he|she|gerson|gersinho|marlene|wanderley)\s+(\w+)", re.I)
STATIC = {"keeps", "keep", "holds", "hold", "stays", "stay", "stares", "stare", "remains", "does", "doesn't", "did",
          "is", "stands", "watches", "looks", "blinks", "breathes", "waits", "freezes", "never", "only", "still",
          "just", "barely", "continues", "doesnt", "has", "seems", "not", "already", "simply", "sits", "lies"}
PROTAG_REF = re.compile(r"\b(he|she|him|his|her|gerson|gersinho|marlene|wanderley)\b", re.I)
CLAUSES = re.compile(r"[;.]|,\s*(?:and|then|while)\s+|\s+(?:and|while|as)\s+(?=(?:he|she|the|a|an|his|her)\b)", re.I)
_DET = {"the", "a", "an", "one", "his", "her", "its", "their", "grey", "gray", "small", "big", "large", "old", "young"}


def _cp_noun(who) -> str:
    """'the grey seagull' -> 'seagull'; 'the boxer at frame-right' -> 'boxer'."""
    head = re.split(r"\b(?:at|in|on|with|from|near|by|of|who|that)\b|[,(]", str(who or ""), maxsplit=1)[0]
    words = [w for w in re.findall(r"[a-zà-ú'-]+", head.lower()) if w not in _DET]
    return words[-1].removesuffix("'s") if words else ""


def _noun_re(noun: str):
    return re.compile(rf"\b{re.escape(noun)}(?:'s|s|es)?\b", re.I) if noun else None


def _cp_acts(clause: str, noun_re) -> bool:
    """A contraparte é o sujeito da oração (aparece antes de qualquer referência a ele) e faz um movimento."""
    if not noun_re:
        return False
    m = noun_re.search(clause)
    if not m:
        return False
    p = PROTAG_REF.search(clause)
    return (p is None or m.start() < p.start()) and bool(CP_ACT.search(clause[m.end():]))


def _protag_acts(clause: str) -> bool:
    m = PROTAG_SUBJ.match(clause)
    return bool(m) and m.group(2).lower() not in STATIC


# ---- tutoriais §11–15 (docs/qa/lint-tutoriais.md) ----
# B4.11: cada ator com nome próprio. "the man" / "a person" sem descritor vira "the man" e "the other man" no prompt.
GENERIC_WHO = {"man", "men", "person", "people", "guy", "guys", "woman", "women", "homem", "pessoa", "cara",
               "mulher", "someone", "somebody", "alguém", "alguem", "other", "one", "sujeito", "moço", "moça"}
WHO_FILLER = {"the", "a", "an", "one", "other", "another", "second", "o", "um", "uma", "outro", "outra", "that",
              "this", "some", "segundo", "segunda", "de", "da", "do", "in", "on", "at", "with", "from", "of", "by",
              "near", "who", "that", "is", "standing", "frame-left", "frame-right", "left", "right", "center"}
ANIMALS = {"dog", "cat", "seagull", "gull", "pigeon", "bird", "horse", "chicken", "rooster", "monkey", "parrot",
           "goat", "cow", "duck", "pig", "donkey", "lizard", "capybara", "squirrel", "crab", "fly", "bee",
           "cachorro", "gato", "gaivota", "pombo", "galinha", "galo", "macaco", "papagaio", "capivara", "vira-lata"}
# O substantivo do protagonista (o que o prompt e os frames usam para ele) não pode nomear a contraparte.
PROTAG_NOUNS = {"gersinho": {"man", "gerson", "gersinho", "singer"},
                "marlene": {"woman", "marlene", "auntie", "tia"},
                "wanderley": {"man", "wanderley", "uncle"}}
OTHER_ONE = re.compile(r"\bthe other (?:man|men|one|ones|guy|woman|person)\b", re.I)
IMAGE_SUBJ = re.compile(r"(?:^|[.;:!?]\s*|,\s*|\b(?:and|then|while|as|when|until|but)\s+)(@\s?Image\s*\d+)(?:'s)?\s+"
                        r"(?!\()", re.I)
GENERIC_IN_TEXT = re.compile(r"\b(?:the|a|an|another)\s+(man|woman|guy|person)\b", re.I)
# B4.10: contraparte fora do quadro (só o membro entra pela borda)
OFFSCREEN = re.compile(r"\boff[- ]?screen\b|\bout of (?:the )?frame\b|\boutside the frame\b|\benter\w*\b[^.;]*\bedge\b|"
                       r"\bfrom (?:the )?[\w-]+ (?:frame )?edge\b", re.I)
EDGE = re.compile(r"\b(frame-(?:left|right|top|bottom)|(?:bottom|top)-(?:left|right)|left|right|top|bottom)\b", re.I)
SCREEN_VEC = re.compile(r"\b(?:screen|frame)-(?:left|right|top|bottom)\b[^.;]{0,30}?\b(?:to|toward|towards|into)\s+"
                        r"(?:the\s+)?(?:screen|frame)-(?:left|right|top|bottom|center)\b", re.I)
# Corte num plano-sequência (regras 6–7; B2): só com corte declarado no roteiro.
CUT = re.compile(r"\bcut to\b|\bhard cut\b|\bshot\s+(?:\d+|one|two|three|four)\b", re.I)
# §15: o que o frame final mostra tem de estar escrito nos últimos estágios.
_END_DETS = {"the", "a", "an", "his", "her", "its", "their", "both", "each", "one", "two", "three", "four", "five",
             "this", "that", "these", "those", "another"}
_END_STOP = {"of", "in", "on", "at", "to", "into", "onto", "from", "with", "by", "for", "toward", "towards", "through",
             "between", "above", "below", "under", "over", "behind", "beside", "near", "around", "against", "past",
             "and", "or", "but", "while", "as", "so", "that", "which", "who", "where", "when", "is", "are", "was",
             "were", "be", "been", "has", "have", "still", "now", "again", "fully", "only", "just", "also", "out",
             "up", "down", "off", "away", "back", "same", "all", "no", "not", "than",
             "sticks", "rests", "pours", "holds", "stands", "keeps", "stays", "hangs", "lies", "sits", "meets",
             "swings", "slides", "falls", "drops", "tilts", "leans", "covers", "points", "faces", "remains", "shows",
             "touches", "springs", "comes", "goes", "runs", "flows", "drips", "looks", "stares", "keep", "hold",
             "stand", "stay", "seen", "tilted", "raised"}
_END_SKIP = {"lens", "camera", "frame", "frame-left", "frame-right", "edge", "edges", "center", "centre", "front",
             "side", "sides", "top", "bottom", "middle", "left", "right", "face", "head", "hand", "hands", "finger",
             "fingers", "shoulder", "shoulders", "chest", "eye", "eyes", "arm", "arms", "foot", "feet", "leg", "legs",
             "hip", "hips", "body", "mouth", "lips", "brows", "pose", "expression", "task", "tasks", "passenger",
             "passengers", "passersby", "passerby", "people", "person", "man", "woman", "deadpan", "way", "place",
             "shot", "clip", "scene", "moment", "result", "end", "start", "state", "outline", "beat", "time", "cm",
             "m", "line", "position", "spot", "level", "height", "half", "rest"}


def _stem(w: str) -> str:
    w = w.lower().removesuffix("'s")
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("ches", "shes", "sses", "xes")):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def end_nouns(text: str) -> list[str]:
    """Núcleos dos sintagmas nominais ('the two glass door leaves are closed' -> 'leaves'), sem corpo nem cenário
    genérico: os props e lugares que o frame final mostra (videos-analisados §15)."""
    toks = re.findall(r"[a-z][a-z'-]*|[,.;:()]|\d+(?:\.\d+)?", str(text or "").lower())
    out: list[str] = []
    i = 0
    while i < len(toks):
        if toks[i] not in _END_DETS:
            i += 1
            continue
        j, phrase = i + 1, []
        while j < len(toks) and len(phrase) < 5:
            t = toks[j]
            if (t in _END_DETS or t in _END_STOP or not t[0].isalpha() or t.endswith(("ed", "ing", "ly"))
                    or t.endswith("°")):
                break
            phrase.append(t)
            j += 1
        if phrase:
            head = phrase[-1].removesuffix("'s")
            if head not in _END_SKIP and len(head) > 2 and head not in out:
                out.append(head)
        i = j if j > i + 1 else i + 1
    return out


def lint_end_nouns(stages, end_text: str, where: str = "en.stages") -> list[str]:
    """§15 (Kling end frame): os substantivos do estado final têm de aparecer no texto dos 2 últimos estágios,
    senão o modelo salta para o end frame no último segundo (fim brusco)."""
    stages = [st for st in (stages or []) if isinstance(st, dict)]
    if not stages or not str(end_text or "").strip():
        return []
    said = {_stem(w) for st in stages[-2:] for w in re.findall(r"[a-z][a-z'-]*", str(st.get("text") or "").lower())}
    missing = [n for n in end_nouns(end_text) if _stem(n) not in said]
    if not missing:
        return []
    return [f"{where}: o frame final mostra {', '.join(repr(m) for m in missing)}, mas o texto dos 2 últimos "
            f"estágios não cita; escreva no estágio do gag, senão a transição sai brusca (videos-analisados §15; "
            f"playbook C4)"]


def protagonist_nouns(slug: str = "", page: dict | None = None) -> set[str]:
    """Como o prompt chama o protagonista: 'man'/'woman' (frames), o nome e o papel. A contraparte não pode usar."""
    out = set(PROTAG_NOUNS.get(str(slug or ""), set()))
    ch = (page or {}).get("character") or {}
    if ch:
        out.add("woman" if ch.get("pronoun") == "she" else "man")
        for k in ("name", "nickname"):
            out |= {w.lower() for w in re.findall(r"[A-Za-zÀ-ú]+", str(ch.get(k) or "")) if len(w) > 2}
    return out


def is_offscreen(cp) -> bool:
    """B4.10: `position` nomeia a borda de entrada ('enters from frame-right edge', 'off-screen frame-right')."""
    return isinstance(cp, dict) and bool(OFFSCREEN.search(str(cp.get("position") or "")))


def is_human(cp) -> bool:
    return isinstance(cp, dict) and bool(cp.get("who")) and _cp_noun(cp.get("who")) not in ANIMALS


def _who_error(who: str, protag: set[str]) -> str:
    """B4.11: 'the man' sem descritor, ou o mesmo substantivo do protagonista, vira 'the man / the other man'."""
    noun = _cp_noun(who)
    words = re.findall(r"[a-zà-ú'-]+", str(who).lower())
    if noun and noun in protag:
        return (f"'{who}' usa '{noun}', o mesmo substantivo do protagonista: o modelo troca os dois (rosto, roupa). "
                f"Dê um nome próprio ou um papel (ex.: 'the boxer', 'DONA CIDA'; playbook B4.11)")
    generic = noun in GENERIC_WHO or not noun
    content = [w for w in words if w not in WHO_FILLER and w not in GENERIC_WHO]
    if generic and not content:
        return (f"'{who}' é genérico: vira 'the man' e 'the other man' no prompt. Dê um nome próprio, um papel ou "
                f"um descritor visível (ex.: 'the boxer in red gloves', 'DONA CIDA'; playbook B4.11)")
    return ""


def lint_counterpart(stages, where: str = "en.stages", allow_behind: bool = False,
                     protagonist: set[str] | frozenset = frozenset()) -> tuple[list[str], list[str]]:
    """Playbook B4 no que dá para checar no texto: contraparte nunca atrás dele (salvo gag_requires: behind),
    um contato por clipe, um ator age por estágio e tarefa para a contraparte nos estágios em que não age.
    B4.11: `counterpart.who` com nome próprio (nunca genérico nem o substantivo do protagonista)."""
    errors: list[str] = []
    warns: list[str] = []
    named: set[str] = set()
    for i, st in enumerate(stages or [], 1):
        cp = st.get("counterpart") if isinstance(st, dict) else None
        if isinstance(cp, dict) and cp.get("who") and str(cp["who"]) not in named:
            named.add(str(cp["who"]))
            msg = _who_error(str(cp["who"]), set(protagonist))
            if msg:
                errors.append(f"{where}[{i}].counterpart.who: {msg}")
    idx = [i for i, st in enumerate(stages or [], 1) if isinstance(st, dict) and isinstance(st.get("counterpart"), dict)
           and st["counterpart"].get("who")]
    if not idx:
        return errors, warns
    contacts: list[str] = []
    for i in idx:
        st = stages[i - 1]
        cp = st["counterpart"]
        who = str(cp.get("who"))
        nre = _noun_re(_cp_noun(who))
        pos, cpf, myf = str(cp.get("position") or ""), str(cp.get("facing") or ""), str(st.get("facing") or "")
        behind = BEHIND.search(pos) or BEHIND_CP_FACING.search(cpf)
        if not behind and nre:  # a orientação dele já diz que está de costas para ela
            n = re.escape(_cp_noun(who))
            behind = re.search(rf"\bback (is )?(turned )?to(ward)? (the )?{n}|\b(turned )?away from (the )?{n}", myf, re.I)
        if behind and not allow_behind:
            errors.append(f"{where}[{i}].counterpart: '{who}' fica atrás dele ('{behind.group(0)}'): o modelo gira o "
                          f"corpo inteiro para encará-la. Ponha ao lado ou à frente (playbook B4.1) ou, se a piada é "
                          f"essa, declare \"gag_requires\": \"behind\"")
        clauses = [c for c in CLAUSES.split(str(st.get("text") or "")) if c and c.strip()]
        cp_acts = any(_cp_acts(c, nre) for c in clauses)
        me_acts = any(_protag_acts(c) for c in clauses)
        if cp_acts and me_acts:
            errors.append(f"{where}[{i}]: '{who}' e ele agem no mesmo estágio; um ator age por estágio e a reação "
                          f"começa no contato, no estágio seguinte (playbook B4.5)")
        if not cp_acts and not str(cp.get("task") or "").strip():
            warns.append(f"{where}[{i}].counterpart: '{who}' não age neste estágio e está sem tarefa; dê uma em "
                         f"counterpart.task (ex.: 'bounces on his toes, guard up, eyes on him'; playbook B4.6)")
        for c in clauses:
            if ON_CONTACT.search(c):
                c = ON_CONTACT.sub(" ", c)
            for m in CONTACT.finditer(c):
                contacts.append(f"[{i}] {m.group(0)}")
                if REPEAT.search(c):
                    contacts.append(f"[{i}] {m.group(0)} ({REPEAT.search(c).group(0)})")
    if len(contacts) > 1:
        errors.append(f"{where}: {len(contacts)} contatos/golpes no mesmo clipe ({'; '.join(contacts)}); mais de um "
                      f"contato = mais de um clipe, encadeados pelo último frame (playbook B4.7)")
    for i in range(idx[0] + 1, idx[-1]):
        if i not in idx:
            warns.append(f"{where}[{i}]: a contraparte some entre os estágios {idx[0]} e {idx[-1]}; repita "
                         f"counterpart com a mesma posição e uma tarefa (playbook B4.2 e B4.6)")
    return errors, warns


def lint_stages(stages, premise: str = "", where: str = "en.stages", allow_behind: bool = False,
                protagonist: set[str] | frozenset = frozenset(), allow_cut: bool = False) -> tuple[list[str], list[str]]:
    """Orientação por estágio (regra 18) e quem encara quem quando outro ator interage com ele (falha do boxe).
    Mais (tutoriais §11–15): ator pelo nome (B4.11), contraparte fora do quadro (B4.10), sem corte no plano-sequência."""
    errors: list[str] = []
    warns: list[str] = []
    e, w = lint_counterpart(stages, where, allow_behind, protagonist)
    errors += e
    warns += w
    back_ok = "costas" in str(premise or "")
    on_screen_human: list[int] = []
    for i, st in enumerate(stages or [], 1):
        if not isinstance(st, dict):
            continue
        text = str(st.get("text") or "")
        cp = st.get("counterpart")
        has_cp = isinstance(cp, dict) and bool(cp.get("who"))
        off = has_cp and is_offscreen(cp)
        facing = str(st.get("facing") or "")
        if not facing:
            errors.append(f"{where}[{i}]: falta 'facing' (orientação dele neste estágio, em graus a partir da lente, "
                          f"ex.: 'chest 0° to the lens, eyes on the lens')")
        elif not (DEG.search(facing) and LENS.search(facing)):
            errors.append(f"{where}[{i}].facing '{facing}': diga o ângulo em graus em relação à lente (regra 18)")
        if BACK_EN.search(facing + " " + text) and not back_ok:
            errors.append(f"{where}[{i}]: ele fica de costas para a câmera (só se a piada for isso, regra 5 do roteirista)")
        clauses = re.split(r"[;.]", text)
        if any(ACTOR.search(c) and INTERACT.search(c) for c in clauses):
            if not has_cp or not cp.get("position") or (not off and not cp.get("facing")):
                errors.append(f"{where}[{i}]: outro ator interage com ele; declare 'counterpart' {{who, position, "
                              f"facing}} (onde está e para onde olha no momento-chave)")
            elif not off and not DEG.search(str(cp.get("facing"))):
                errors.append(f"{where}[{i}].counterpart.facing: diga o ângulo em graus (ex.: 'in profile facing "
                              f"frame-left toward him, 90° to the lens')")
        if off and not SCREEN_VEC.search(str(cp.get("vector") or "") + " " + text):
            errors.append(f"{where}[{i}].counterpart: '{cp['who']}' fica fora do quadro (B4.10), então rosto e olhar "
                          f"não são exigidos, mas o membro que entra precisa de vetor de tela em counterpart.vector "
                          f"(ex.: 'the right glove travels screen-right to screen-left and stops against his "
                          f"pompadour')")
        if has_cp and not off and is_human(cp):
            on_screen_human.append(i)
        # B4.11: ninguém é "the other man" nem "@Image N" fazendo a ação (regra 10)
        m = OTHER_ONE.search(text)
        if m:
            errors.append(f"{where}[{i}]: '{m.group(0)}' no texto; cada ator tem nome próprio (counterpart.who), "
                          f"nunca 'the man' e 'the other man' (playbook B4.11)")
        m = IMAGE_SUBJ.search(text)
        if m:
            errors.append(f"{where}[{i}]: '{m.group(1)}' como sujeito da frase; o handle fica no ACTIVE REFERENCES "
                          f"e a ação usa o nome (regra 10; B4.11)")
        if has_cp and is_human(cp):
            noun = _cp_noun(cp["who"])
            g = [x for x in GENERIC_IN_TEXT.finditer(text) if x.group(1).lower() != noun]
            if g:
                errors.append(f"{where}[{i}]: '{g[0].group(0)}' no texto com contraparte humana; chame pelo nome de "
                              f"counterpart.who ('{cp['who']}'), nunca por 'the man' (playbook B4.11)")
        m = CUT.search(text)
        if m and not allow_cut:
            errors.append(f"{where}[{i}]: '{m.group(0)}' num clipe de plano-sequência; o Seedance obedece e corta. "
                          f"Outro enquadramento = outra geração (B2), ou declare o corte no roteiro com "
                          f"\"cut\": {{\"at\": 6.5}} (regras 6–7)")
        if ABSTRACT_END.search(str(st.get("end_state", ""))):
            warns.append(f"{where}[{i}].end_state abstrato ('{ABSTRACT_END.search(str(st.get('end_state'))).group(0)}'): "
                         f"descreva o que se vê no quadro (regra 5)")
        m = VAGUE.search(text)
        if m:
            warns.append(f"{where}[{i}]: verbo vago '{m.group(0)}': escreva o movimento do corpo (pé, direção, mão)")
    if len(on_screen_human) >= 2:
        warns.append(f"info: {where}{on_screen_human}: contraparte humana com rosto no quadro em "
                     f"{len(on_screen_human)} estágios; considere B4.10 passo 0 (só o membro entrando pela borda, "
                     f"'position': 'enters from the frame-right edge', ou um clipe separado com corte de olhar)")
    return errors, warns


def _cut_declared(*objs) -> bool:
    """Corte explícito no roteiro (`"cut": {"at": 6.5}` no topo, no `en` ou no gag_followup; playbook B2)."""
    return any(isinstance(o, dict) and bool(o.get("cut")) for o in objs)


def lint_cut(cut, dur: float, where: str = "cut") -> list[str]:
    if not cut:
        return []
    at = cut.get("at") if isinstance(cut, dict) else None
    try:
        at = float(at)
    except (TypeError, ValueError):
        return [f"{where}: diga quando é o corte ({{\"at\": 6.5}}); o prompt vira 'Exactly one HARD CUT at 6.5s'"]
    if not 0 < at < dur:
        return [f"{where}.at {at}s fora do clipe (0–{dur}s)"]
    return []


def _gag_timing(stages, where: str, gag_idx: int, hold_idx: int | None, gag_min: float = 2.0) -> list[str]:
    """Playbook B1: o gag precisa de ≥2 s (contando o assentamento) e o resultado fica parado ≥0,5 s."""
    errors: list[str] = []
    n = len(stages)
    for idx, minimum, what in ((gag_idx, gag_min, "o gag"), (hold_idx, 0.5, "o resultado parado (hold final)")):
        if idx is None or not -n <= idx < n or not isinstance(stages[idx], dict):
            continue
        sp = _span(stages[idx].get("t", ""))
        if sp and sp[1] - sp[0] < minimum - 1e-6:
            errors.append(f"{where}[{idx % n + 1}] ({stages[idx].get('t')}) tem {sp[1] - sp[0]:.1f} s; {what} precisa "
                          f"de ≥{minimum:g} s (playbook B1, regra 5)")
    return errors


def lint_crowd(en: dict, where: str = "en") -> tuple[list[str], list[str]]:
    """Figurantes: tarefa para cada um (regra 14) e nenhuma multidão que contradiga a contagem exata (regra 13)."""
    errors: list[str] = []
    warns: list[str] = []
    try:
        n = int(en.get("extras_count") or 0)
    except (TypeError, ValueError):
        return errors, warns
    if n:
        k = task_count(en.get("extras_tasks", ""))
        if k is None:
            warns.append(f"{where}.extras_tasks: não deu para contar as tarefas; escreva 'two joggers ..., one vendor ...'")
        elif k < n:
            errors.append(f"{where}.extras_tasks dá tarefa a {k} de {n} figurantes: os outros {n - k} ficam sem "
                          f"tarefa e reagem a ele (regra 14)")
        elif k > n:
            errors.append(f"{where}.extras_tasks descreve {k} pessoas, mas extras_count é {n} (regra 13)")
    m = CROWD.search(" ".join(str(en.get(k, "")) for k in ("gag_sentence", "location", "location_map", "position")))
    if m:
        errors.append(f"{where}: '{m.group(0)}' contradiz a contagem exata de figurantes ({n}); descreva só as "
                      f"pessoas contadas (regra 13)")
    hands = str(en.get("hands", ""))
    if n and re.search(r"hands in (the )?frame", hands, re.I) and not re.search(r"\bfor (him|her)\b", hands, re.I):
        errors.append(f"{where}.hands diz 'hands in frame, both his' com {n} figurantes no quadro: escreva "
                      f"'He has exactly two hands: ...' (as mãos dos figurantes também aparecem)")
    return errors, warns


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
    e, w = lint_crowd(script["en"])
    errors += e
    warns += w
    tr = script["trend"]
    if not tr.get("name") or not tr.get("source_hint"):
        errors.append("trend precisa de name e source_hint (de onde vem o vídeo-fonte)")
    if not CONSENT.search(" ".join(str(tr.get(k) or "") for k in ("consent", "source_note", "source_hint"))):
        warns.append("trend sem nota de consentimento/autoria da fonte: diga em trend.consent quem gravou e quem "
                     "autorizou (fonte gravada pelo Caio, motion library licenciada; dança de terceiro só com "
                     "autorização; videos-analisados §12)")
    if not _source_deadpan(script["en"]):
        warns.append("en não diz que o dançarino da fonte está deadpan: a expressão da fonte passa para o "
                     "personagem. Escreva en.source_expression, ex.: 'the source dancer is deadpan: lips closed, "
                     "lip corners level' (videos-analisados §12; playbook C5)")
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
        e, w = lint_gag(script["gag_followup"], script.get("premise", ""), _behind_ok(script),
                        protagonist_nouns(script.get("page"), page))
        errors += e
        warns += w
    return errors, warns


CONSENT = re.compile(r"consent|autoriz|autoria|authori[sz]|licen[cs]|gravad[oa] pel[oa]|recorded by|own recording|"
                     r"fonte pr[oó]pria|direitos", re.I)


def _source_deadpan(en: dict) -> bool:
    """§12: a fonte de dança é gravada deadpan (en.source_expression, ou uma frase do en ligando fonte e deadpan)."""
    if re.search(r"\bdeadpan\b", str(en.get("source_expression") or ""), re.I):
        return True
    return bool(re.search(r"\b(source|fonte|dancer)\b[^.;]*\bdeadpan\b|\bdeadpan\b[^.;]*\b(source|fonte)\b",
                          _text(en), re.I))


def _behind_ok(script: dict, *more) -> bool:
    """`"gag_requires": "behind"` no roteiro (ou no gag_followup): a contraparte atrás dele é a piada."""
    return any(isinstance(x, dict) and str(x.get("gag_requires") or "").lower() == "behind" for x in (script, *more))


def lint_gag(g, premise: str = "", allow_behind: bool = False,
             protagonist: set[str] | frozenset = frozenset()) -> tuple[list[str], list[str]]:
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
    # 2 estágios (armação e piada): a piada e o resultado parado dividem o último, então ≥2 s + 0,5 s
    if len(stages) == 2:
        errors += _gag_timing(stages, "gag_followup.en.stages", -1, None, gag_min=2.5)
    errors += lint_cut(g.get("cut") or en.get("cut"), dur, "gag_followup.cut")
    e, w = lint_stages(stages, premise, "gag_followup.en.stages", allow_behind or _behind_ok(g), protagonist,
                       _cut_declared(g, en))
    errors += e
    warns += w
    warns += lint_end_nouns(stages, " ".join(str(en.get(k) or "") for k in ("end_change", "end_props")),
                            "gag_followup.en.stages")
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
    if stages and abs(send - float(script.get("duration_s", 0))) > 0.51:
        errors.append(f"en.stages terminam em {send}s, mas duration_s é {script.get('duration_s')}")
    if len(stages) >= 3:
        errors += _gag_timing(stages, "en.stages", -2, -1)
    errors += lint_cut(script.get("cut") or en.get("cut"), float(script.get("duration_s") or 0))
    e, w = lint_stages(stages, script.get("premise", ""), allow_behind=_behind_ok(script),
                       protagonist=protagonist_nouns(script.get("page"), page), allow_cut=_cut_declared(script, en))
    errors += e
    warns += w
    if script.get("end_frame") or en.get("end_change"):
        warns += lint_end_nouns(stages, " ".join(str(en.get(k) or "") for k in ("end_change", "end_props")))
    e, w = lint_crowd(en)
    errors += e
    warns += w
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
    want = CAMERA_FOV.get(cam.get("mode"))
    if fov is not None and want and int(fov) != want:
        # o prompt usa o FOV do modo; um fov_deg diferente no roteiro é uma contradição calada (regra 21)
        errors.append(f"camera.fov_deg {fov} não bate com o modo {cam.get('mode')} ({want}°, playbook regra 21)")
    if cam.get("mode") == "selfie_pov" and not re.search(r"\bphone\b", str(en.get("hands", "")), re.I):
        errors.append("selfie: a mão direita segura o celular; diga isso em en.hands (senão aparece uma 3ª mão)")
    shots = {str(p.get("shot", "")).strip() for p in panels if isinstance(p, dict)}
    if cam.get("mode") != "tracking_side" and len(shots) > 1:
        warns.append(f"storyboard_panels com enquadramentos diferentes ({sorted(shots)}) num plano travado: "
                     f"vira corte (regra 6)")

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
