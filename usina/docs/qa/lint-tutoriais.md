# Lint dos tutoriais §11–15 (05/10/2026)

O que os 5 tutoriais da fila (`playbook/videos-analisados.md` §11–15, destilados no `seedance-master.md` B4.10, B4.11, C2, C4 e D) viraram no código. Sem crédito gasto: nada foi gerado, só lint, prompts e testes (`tests/test_lint_tutoriais.py`).

## Regras novas no lint (`pipeline/lint.py`)

| Regra | Fonte | Nível | O que confere |
|---|---|---|---|
| Ator com nome | B4.11; §11 | erro | `counterpart.who` genérico sem descritor (`man`, `person`, `guy`, `woman`, `homem`, `pessoa`, `cara`, `mulher`, `someone`). "the woman in a red apron" e "DONA CIDA" passam. |
| Substantivo do protagonista | B4.11 | erro | `counterpart.who` com o substantivo dele (`man` para Gersinho e Wanderley, `woman` para Marlene, o nome ou o papel). "the bald man" é erro no Gersinho. |
| "the other man" / `@Image N` sujeito | regra 10; B4.11 | erro | No `text` do estágio. `@Image` como objeto ("matches @Image 1") passa. |
| Contraparte humana pelo nome | B4.11 | erro | No estágio com contraparte humana, "a man" ou "the woman" no texto quando o `who` é outro. |
| Substantivos do frame final | §15; C4; D "fim brusco" | aviso | Os núcleos dos sintagmas de `end_change` e `end_props` (sem corpo, lente e borda) têm de aparecer no `text` dos 2 últimos estágios. |
| Contraparte fora do quadro | B4.10 | erro | `position` com a borda de entrada ("off-screen frame-right", "enters from the frame-right edge"). Sem `facing`, mas com vetor de tela do membro (`counterpart.vector` ou no texto: "screen-right to screen-left"). |
| Rosto humano em ≥2 estágios | B4.10 passo 0 | info | Aviso com prefixo `info:` e "considere B4.10 passo 0". Bicho não conta, e contraparte fora do quadro também não. |
| Corte no plano-sequência | regras 6–7; B2 | erro | "cut to", "hard cut" e "shot N" no texto, a menos que o roteiro declare `"cut": {"at": 6.5}`. O `at` é validado. |
| Tempo do gag | B1; regra 5 | erro | Gag (penúltimo estágio) ≥2 s e resultado parado (último) ≥0,5 s. No `gag_followup`, o 2º estágio ≥2,5 s. Substitui o aviso antigo de 1,5 s. |
| Trend: consentimento | §12 | aviso | `trend.consent` (ou `source_hint`) sem nota de autoria ou autorização. |
| Trend: fonte deadpan | §12; C5 | aviso | `en` sem dizer que o dançarino da fonte está deadpan (`en.source_expression`). |

## Prompts (`pipeline/prompts.py`)

- **ACTIVE REFERENCES (B4.11):** "@Image 1 (the close-up face photo on grey) is GERSINHO's face reference…". Com contraparte humana, uma linha diz que ela é outra pessoa e que nada dela vem de @Image 1 ou 2, e outra fixa os nomes ("named only by name: GERSINHO, DONA CIDA").
- **Corpo pelo nome:** o primeiro `he`/`she` de cada estágio vira o nome. O POSITIVE LOCKS usa "GERSINHO's face matches his face reference (@Image 1)". `name()` usa o apelido inteiro ("TIA MARLENE", não "TIA").
- **Dono do beat (C4):** um beat por estágio, com o dono nomeado. É a contraparte quando ela é o sujeito, ou `stage.owner`. Se o dono não aparece no texto, o estágio abre com "<DONO>'s beat:".
- **Fora do quadro (B4.10):** "The boxer in red gloves stays off-screen beyond the frame-right edge; only his right red glove enters the frame; it travels… No face or body of the boxer in red gloves appears in the frame." Usa `limb` e `vector`.
- **Frame B (C2):** "Same light direction, exposure and sharpness as image 1."
- **Corte declarado:** "Exactly one HARD CUT at 6.5s; otherwise the camera holds still" no lugar de "One continuous shot…".

## Roteiros ajustados (a regra estava certa)

- **Busão** (fila e exemplo): o frame final mostra a emenda ("seam"), que não estava no estágio do gag. Agora: "meet in a seam at the center".
- **Elevador:** a cabine do frame final não estava nos últimos estágios. O estágio 4 diz "at the front of the cabin".
- **Guarda-sol:** a haste ("shaft") do frame final. O estágio 3 diz "raises the closed umbrella by its shaft".
- **Trend do calçadão:** ganhou `trend.consent` e `en.source_expression` (fonte deadpan, áudio mudo).

Os 5 passam sem erro e sem os avisos novos.

## Limites

- A extração de substantivos é heurística: pega o núcleo depois de artigo ou possessivo. Por isso é aviso, não erro.
- A contraparte humana ainda não tem ficha própria no `video-request`: o prompt nomeia e separa, mas as medias continuam rosto e silhueta do protagonista. Ligar a ficha dela (B4.11, "ficha própria antes de qualquer vídeo") mexe em `__main__.py` e fica para depois.
