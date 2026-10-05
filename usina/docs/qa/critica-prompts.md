# Crítica dos prompts emitidos (05/10/2026)

**Método.** Renderizei em modo mock (`USINA_MOCK=1`, numa cópia da usina no scratchpad, sem tocar na fila real nem no livro-caixa, sem chamada ao Higgsfield ou à OpenAI) tudo o que o pipeline manda:
- para os 3 itens de `data/queue/gersinho/`: storyboard, frame A, frame B e o JSON do `video-request`;
- para a trend de exemplo: frame do motion control, prompt de cena e JSON do Genjutsu, e o gag pós-MC.

Depois li cada prompt linha por linha contra o `playbook/seedance-master.md` (regras 1–25), as 8 leis do `prompts/script.md` e os tutoriais (`videos-analisados.md`).

**Pergunta central:** o que sai do código impede a falha do boxe (ele de costas no momento em que o outro soca)? **Antes, não.** A orientação existia só como uma frase global no fim do ACTION. Nenhum estágio dizia o ângulo dele, e nada obrigava a dizer onde está e para onde olha o outro ator. Um roteiro com "um boxeador soca" passava no lint.

---

## Achados e correções

| # | Achado (prompt renderizado) | Regra violada | O que mudou |
|---|---|---|---|
| 1 | Orientação só global ("his chest stays square…"), sem grau por estágio; nenhum "quem encara quem" quando outro ator age | Regra 18; lei 5; falha do boxe | `en.stages[].facing` obrigatório, com grau e lente. `counterpart {who, position, facing}` obrigatório quando um ator (pessoa ou bicho) interage. Os dois entram na linha do estágio, no painel do storyboard e nos frames A e B. Lint barra a falta. |
| 2 | Último estado final = "frozen result, readable as a cover" (não é visível) | Regras 2 e 5 | Sem `end_image`, o último estado final é o `end_change` por extenso. Com `end_image`, vale o `end_state` concreto do roteiro. Lint avisa estado abstrato. |
| 3 | "Exactly two hands in frame, both his" com 5 figurantes no quadro | Regras 13 e 24 (contradição) | "He has exactly two hands: …". Lint: erro com figurantes. |
| 4 | Busão: folhas "dobradas no lado direito" que depois "se encontram no centro"; topete "acima do batente" com ele no degrau; a porta prende o topete "por cima" | Regra 24 (cadeia causal); U1 | Folhas nas duas laterais fechando para o centro; a emenda prende a ponta do topete, que passa 10 cm da linha da porta. |
| 5 | Guarda-chuva: "pushes the runner" com a mão esquerda travada na barriga (precisa de 2 mãos); chuva vertical "caindo no rosto" sob a copa (física ilegível) | Regras 24 e 2 | Guarda-chuva automático (polegar direito). A copa pousa no topete, inclinada 20°, e um fio d'água da borda cai no ombro esquerdo. |
| 6 | PT x EN: premissa "continua dançando enquanto o ônibus sai" e end_frame "ônibus em movimento", mas o `en` não tem ônibus andando (seria uma 3ª ação) | Lei 2; regra 1 | PT reescrito igual ao `en` (o revisor compara os dois). |
| 7 | "a crowded bus", "standing passengers", "crowded office elevator" com contagem exata | Regra 13 | Termos removidos. Lint: "crowded/crowd/packed/lotado" é erro. |
| 8 | Genjutsu recebia só o frame e a fonte, sem ficha | `videos-analisados` §5 (ficha em toda geração) | Rosto e silhueta entram como `image_references` 2 e 3, com papel declarado ("same man, not extra people"). `--no-sheet` faz o A/B se o modelo duplicar o personagem. |
| 9 | Prompt de cena do MC: "Exactly 5 passersby continue their own tasks" **sem as tarefas** e sem câmera | `videos-analisados` §8 (fundo morto) | Tarefa de cada figurante e "follows the source video's camera, no added cuts". |
| 10 | Passante a 4 m e 63°: o rosto fica com ~5% da altura do quadro. O storyboard dizia "MS" com câmera de corpo inteiro a 4 m | `videos-analisados` §8 (rosto pequeno = rosto genérico); regra 6 | 3 m (ainda dentro dos 3–5 m do B2) e "full body fills 80% of the frame height". `shot` igual em todos os painéis. Lint avisa `shot` diferente num plano travado. |
| 11 | Topete "25 cm, as tall as his own head" contra a bíblia "twice the height of his head". "slim" contra "lanky… potbelly". SCENE CONTEXT repetia o figurino inteiro | Regra 8 (texto não contradiz a referência; identidade mínima) | Silhueta alinhada à bíblia. Papel curto + marca. Figurino só via @Image 2. |
| 12 | Storyboard: "props exactly as listed per panel (…folded open…)", ou seja, porta aberta nos 4 painéis, mas os painéis 3–4 têm porta fechada | Consistência painel ↔ estágio | `rules` usa o `props_lock` (estado do clipe inteiro). |
| 13 | `@Image 1` só por número, com `start_image`/`end_image` antes na lista de medias | Regra 10; `sd25` (o 2.5 casa o material pelo conteúdo) | Handle + conteúdo ("@Image 1 (the close-up face photo on grey)") e "the image references never change the start- or end-frame composition". |
| 14 | Gag: a mesma frase 3 vezes (texto, End state, "Final state"); BPM num gag sem dança; sem logline; "does not move or react" | Regras 22 e 7; desperdício de tokens | Sem "Final state". Logline (`gag_sentence`) no SCENE CONTEXT. "keeps the same pose". Câmera "locked off, no zoom" (o FOV é o da fonte, não o da tabela). |
| 15 | `script.md` ensinava `"fov_deg": 47` para passante. O lint só avisava, e o prompt ignorava o campo | Regra 21 | Template com 63°. Lint: `fov_deg` diferente do modo é erro. |
| 16 | Selfie: a mão direita segura o celular, mas nada impedia `hands` com "right index finger raised" | Regra 24 (3ª mão) | Lint: em selfie, `en.hands` tem de citar o celular. |
| 17 | Figurantes: a contagem de tarefas não era conferida | Regra 14 | `task_count` soma "two joggers…, one vendor…". Menos tarefas que `extras_count` é erro. |

Itens 3–7 e 10–11 exigiram reescrever os 3 roteiros da fila e os 2 exemplos (`prompts/examples/`). Todos passam no lint novo. As versões antigas falham: busão com 6 erros, trend com 3.

---

## Antes e depois (trechos renderizados)

**Vídeo, busão, estágio do gag (o ponto da falha do boxe):**
```
ANTES
[Stage 3 — 6.5-8.5s] The two glass door leaves swing closed from the right side of the doorway in front of his
body; the top edge of the closing door meets the base of the pompadour; the pompadour passes over the door edge…
End state: door closed, pompadour sticking out above the door, his face behind the glass.
[Stage 4 — 8.5-10s] … End state: frozen result, readable as a cover.
Throughout: real-time at 95 BPM; his chest stays square to the lens, hips rotate at most 30°, …

DEPOIS
[Stage 3 — 6.5-8.5s] The two glass door leaves swing closed from the left and right sides of the doorway toward
the center, in front of his body; their vertical edges meet in the center and pinch the front tip of the pompadour
that sticks out past the door line; … he keeps the pose. Orientation: chest 0° to the lens, face 0° to the lens,
eyes on the lens through the glass. End state: door closed, the pompadour tip pinched in the seam…
[Stage 4 — 8.5-10s] … End state: door closed, pompadour tip pinched outside the seam, deadpan face behind the glass.
Unless a stage names a turn, his chest stays at 0° to the lens and his hips rotate at most 30°; …
```

**Quem encara quem (gag da trend; o mesmo formato vale para um boxeador):**
```
DEPOIS
[Stage 2 — 2.5-5s] A grey seagull glides in from frame-right and lands on top of his rigid pompadour, folding its
wings; he keeps the same pose and keeps staring into the lens. Orientation: chest 0° to the lens, face 0° to the
lens, eyes on the lens. The grey seagull: standing on the top of his pompadour, centered, in profile facing
frame-left, 90° to the lens. End state: …
```
Sem `counterpart`, o lint para: `gag_followup.en.stages[2]: outro ator interage com ele; declare 'counterpart'…`.

**Genjutsu (`video_request.json`) e prompt de cena:**
```
ANTES  medias: [image_references(frame), video_references(fonte)]
       "Exactly 5 passersby continue their own tasks; none looks at him."
DEPOIS medias: [image_references(frame), image_references(rosto), image_references(silhueta), video_references(fonte)]
       "Image 2 (face close-up) and image 3 (silhouette sheet) are identity references of that same man, not extra
        people… Exactly 5 passersby continue their own tasks — two joggers pass in the background, one vendor…"
```

**Frame A (tamanho do rosto):**
```
ANTES  static phone on a passerby's tripod at chest height, 63° field of view, 4 m away.
DEPOIS static phone on a passerby's tripod at chest height, 63° field of view, 3 m away. … His full body, from his
       shoes to the top of the pompadour, fills 80% of the frame height, so his face stays large and readable.
```

**Storyboard (painel = estágio):**
```
ANTES  "rules": "…props exactly as listed per panel (exactly one bus front door…, folded open…)"
DEPOIS "orientation": "chest 0° to the lens, face 0° to the lens, eyes on the lens through the glass"  (por painel)
       "rules": "…props: exactly one bus door with two glass leaves: open at both sides in the first frame, closed in
                 the center in the last frame, pinching the pompadour tip"
```

## Tamanho (BIBO: estrutura vence comprimento)

Saiu o que era duplicado:
- a descrição inteira do topete no PHYSICS (já estava na marca);
- o figurino no SCENE CONTEXT;
- "real-time" dito 3 vezes;
- o "Final state" do gag;
- a orientação repetida quando não muda (só aparece de novo se mudar ou se houver outro ator).

Entraram a orientação em graus e a geometria do gag. Vídeo do busão: 755 → 848 palavras, em 9 blocos. Gag: 459 → 505. Cena do MC: 95 → 201, por causa das tarefas e dos papéis da ficha. Nenhum estágio ganhou ação nova: o acréscimo é âncora, não beat (`creators-techniques` §4: o que estraga é o beat sobrecarregado).

## Pendências
- **Genjutsu com 3 imagens:** o modelo é "subjects in reference images". Ficha como identidade de um sujeito só ainda não foi testada em campo. Conferir no 1º take; se ele duplicar o personagem, usar `video-request <ref> --no-sheet` e registrar em `falhas.md`.
- **Playbook:** C2/C4 ainda mostram "4 m" e "25 cm". O código agora segue a bíblia (topete com 2× a altura da cabeça) e 3 m (dentro dos 3–5 m do B2). Quem edita o `playbook/` deve alinhar.
- `facing` e `counterpart` valem para os estágios do `en` (o que vira prompt). Os `beats` em PT continuam com `facing` livre.

Código: `pipeline/prompts.py` (`_orient`, `_stage_lines`, `_ref_lines`), `pipeline/lint.py` (`lint_stages`, `lint_crowd`, `task_count`), `pipeline/__main__.py` (`--no-sheet`). Testes: `tests/test_prompts_critic.py`.
