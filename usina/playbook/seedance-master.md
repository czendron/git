# Seedance Master Playbook — Usina de Virais

Destilado de `vendor/higgsfield-ai-prompt-skill` (OSideMedia, MIT) e `vendor/higgsfield-official-skills`, filtrado para o nosso formato: Reels 9:16 fotorreal, 8–12 s, personagem de silhueta rígida e absurda (topete gigante, laquê, bigode), **deadpan sempre**, dança lenta de assinatura ou ação banal em lugar comum do Brasil, figurantes ignorando, piada física no fim, câmera selfie grande-angular ou câmera parada de passante.

**Prioridade:** as lições validadas do Caio (ata D9) ganham de qualquer regra do vendor quando houver conflito.

**Siglas das fontes:**
- `OS/` = `vendor/higgsfield-ai-prompt-skill/`
- `sd20/` = `OS/skills/higgsfield-seedance/`
- `sd25/` = `OS/skills/higgsfield-seedance-2-5/`
- `OF/` = `vendor/higgsfield-official-skills/higgsfield-generate/references/`
- `U1`–`U4` = lições do Caio (escrever o visível; storyboard primeiro; referência com pouco texto; falha da laje)

Status de evidência: quase tudo no vendor é `[EMPIRICAL]`/`[FIELD]`. São heurísticas fortes, não garantias. O que valer ou falhar no nosso material vai para `playbook/falhas.md`.

---

## Por que o vídeo da laje falhou (o caso que motiva este arquivo)

| Pedido | O que o modelo fez | Mecanismo (fonte) |
|---|---|---|
| 8 s com 4 ações: olhar o celular com desdém → guardar → encarar → dançar | Virou de costas no momento-chave; apareceu um soco | Densidade de ações: o modelo resolve 1–2 beats a cada 5 s (`OS/skills/higgsfield-motion` § Beat Density). Uma cadeia que muda de direção (pega, guarda, olha, dança) é "processo", e o modelo erra processo e acerta estado (`higgsfield-acting` § States, not transitions). |
| "O brega desafia o boxe" | Inventou um confronto físico | Conceito abstrato sem contraparte visível. O modelo precisa renderizar a relação e escolhe o clichê visual mais próximo, que aqui é a luta. Só se descreve o que pode ser visto (`sd20/ENGINE-RULES.md` regra 9). |
| Nenhum quadro intermediário | Ordem e pose livres | Sem âncora de estado final, qualquer frame serve de parada (`sd20/FAILURE-MODES.md` § Truncated action). |

---

## A) As 25 regras

| # | Regra | Por quê | Fonte |
|---|---|---|---|
| 1 | **Uma ideia = 1 gag que se entende sem som. No máximo 2 ações por clipe de 10 s: a assinatura e a piada, nessa ordem.** | O modelo gasta a atenção uma vez só. Com várias ações, ele fica pela metade em cada uma, borra ou inventa. | U4; `higgsfield-motion` § Beat Density; `sd25/SKILL.md` § Split by JOB |
| 2 | **Escreva o visível.** Toda abstração vira algo que se vê no quadro ("desafia o boxe" vira "um saco de pancada vermelho pendurado a 1 m, imóvel"). Se não dá para mostrar, não entra. | Uma relação abstrata sem objeto vira um clichê inventado (o soco). | U1; `sd20/ENGINE-RULES.md` 9; `sd20/SKILL.md` § Name the thing |
| 3 | **Estados, não transições.** O start frame já mostra o personagem na pose de assinatura. Nada de "tira o celular, guarda, aí...". | Modelos erram o processo e acertam o estado. Ação complexa abre o prompt, e a aproximação vira outro clipe. | `higgsfield-acting` § States; `sd20/HELL-GRIND.md` § Solutions born under deadline |
| 4 | **Duração = conteúdo.** Cada segundo do clipe tem ação escrita, num só sentido. Todo movimento de câmera tem ponto final ("termina com o topete no terço superior"). | Uma ação curta num clipe longo é "preenchida" de trás para frente (vai e volta). O mesmo vale para a câmera sem destino. | `sd20/FAILURE-MODES.md` § Action-reversal fill; `sd20/SKILL.md` § Motion-prompt laws |
| 5 | **Cada estágio tem 1 mudança e um estado final visível.** O resultado do gag fica parado ≥0,5 s antes do fim. | Sem estado final declarado, o corte cai antes do resultado: a tampa ainda está fechando. | `sd25/SKILL.md` § Long Video; `sd20/FAILURE-MODES.md` § Truncated action |
| 6 | **Plano-sequência por padrão:** `one continuous shot, the camera does not cut on its own`. Se o gag precisa de outro enquadramento, faça outra geração e emende na edição. | O modelo insere cortes por conta própria. Física e performance num prompt só pioram as duas. | `sd20/SKILL.md` § Cut-format ladder; `sd25/SKILL.md` § Split by JOB |
| 7 | **Sem rótulo por segundo nem "Shot 1/2" dentro de um plano-sequência.** No 2.5, use `[Stage]` com estado final e diga que os estágios são "momentos de um mesmo plano contínuo". | O Seedance lê blocos com tempo como instrução de corte. | `sd20/SKILL.md` § Single-vs-multi-shot |
| 8 | **A identidade vem da imagem.** O texto de identidade é mínimo: papel, 2–3 marcas visíveis e "100% matches the reference". Nunca contradiz a referência. Com `start_image`, o prompt fala só de movimento e câmera. | Texto longo de aparência briga com a imagem e degrada a identidade. Redescrever o frame inicial cria duas entradas concorrentes. | U3; `sd20/SKILL.md` § Tag naming + minimal reference text; `OF/prompt-engineering.md` § Image-to-video |
| 9 | **Ficha de personagem chata de propósito:** cinza liso (um único hex por projeto, `#8a8a8a`), luz plana, pele com poros, **um só rosto legível** (close 3/4) e corpo inteiro sem rosto legível. Junte uma vista de perfil e uma de costas para a silhueta. | Vários rostos pequenos são "medidos" juntos e a identidade fica genérica. Fundo com cenário vaza para o set. | `sd25/VFX-PIPELINE.md` § Stage 1 / face-lock crop; `sd20/HELL-GRIND.md` § character sheet; `OS/templates/ad-asset-prep.md` |
| 10 | **Cada material tem papel, grau de fidelidade e exclusão, uma linha por material.** Nas frases de ação, o personagem aparece pelo nome e uma marca visível, nunca por `@Image`. | O modelo não deduz o mapeamento. A ficha vaza o fundo cinza e o layout. Um handle usado como sujeito faz o personagem voltar como duas pessoas. | `sd25/SKILL.md` § Reference Roles, § Fidelity |
| 11 | **Uma imagem, um papel.** Primeiro e último frame vão nos papéis `start_image`/`end_image` do omni_reference, com uma frase curta confirmando o papel. Não declare a mesma imagem de novo como frame em prosa. Os dois frames têm a mesma proporção (9:16). | Âncoras fundidas ou com proporções diferentes esticam o último frame. | `sd25/SKILL.md` § First-Last Frame |
| 12 | **O storyboard dá ordem e composição aproximada, não reprodução literal.** Inclua o mapa painel→tempo e `Do not reorder; do not invent shots`, e exclua bordas, numeração e estilo do desenho. | O mapeamento por tempo segurou cada painel no seu trecho e evitou vazamento de props entre painéis no A/B. Sem o mapa, o modelo escolheu o próprio ritmo. | `sd25/MODE-PLAYBOOKS.md` § Storyboard grids / panel-to-timestamp |
| 13 | **Cabeçalho de contagem:** `EXACTLY 1 main character` mais a contagem de cada prop. Os figurantes são uma massa com número ("5–7 passersby"). | O modelo adora acrescentar gente e clonar objetos. Ele acompanha no máximo 3 personagens. | `sd20/HELL-GRIND.md` § character-count header; `sd20/ENGINE-RULES.md` 5 |
| 14 | **Figurantes são ambiente.** Cada um tem uma tarefa própria (celular, sacola, banca) e movimentos defasados, e o prompt diz explicitamente que nenhum olha para ele. | Reação em grupo é o padrão do modelo diante de um espetáculo. Quando o padrão já é a falha, a proibição curta se justifica. | `higgsfield-acting` § Ensemble; `OS/skills/shared/negative-constraints.md` § Where a ban is still correct |
| 15 | **Deadpan descrito como anatomia:** lábios fechados e relaxados, mandíbula fechada, cantos da boca nivelados, sobrancelhas niveladas, piscadas lentas a cada 3–4 s, olhar fixo na lente com microssacadas. É uma imobilidade escolhida, não um olhar morto. | Nome de emoção vira algo raso. Olho parado é o sinal nº 1 de IA. Comédia se faz com seriedade total. | U3; `higgsfield-facs` § Emotion→AU (AU12 = sorriso); `higgsfield-acting` § Eye life, atlas nº 13 |
| 16 | **Ninguém fala.** Use `generate_audio: false` (a música entra na pós). Se precisar de som ambiente, liste só os sons diegéticos e escreva o estado da boca de todo rosto visível. | Silêncio deixado em aberto vira balbucio, e a boca sem instrução "fala". | `sd20/FAILURE-MODES.md` § Filler-babble; ata D4 (MP4 sem música) |
| 17 | **Silhueta rígida descrita como material, física e medida:** "lacquered solid like molded resin, moves only as one block with the skull, 25 cm tall, the height of his own head", "still air". A forma fica gravada no asset (perfil, costas e topo). | Cabelo é, por padrão, um material que balança. Palavras vagas de escala não seguram, e marco corporal com unidade segura. | `sd20/SKILL.md` § Measurable-language, § Bake it into the asset; `sd25/VFX-PIPELINE.md` § Stage 2 |
| 18 | **Orientação travada em graus e a partir da câmera:** "chest square to the lens, hips rotate at most 30°, face visible in every frame". Giro só com nome, duração e direção final ("completes one 360° turn in 1.5 s and ends facing the lens"). | Direita/esquerda só existem a partir da câmera. Um movimento sem vetor é reinventado a cada take, e é daí que vem o "virou de costas". | `sd20/SKILL.md` § Measurable-language, § Spatial Layout Block; `sd20/FAILURE-MODES.md` § fight vectors |
| 19 | **Tempo real.** Nunca use "slow" como velocidade. Escreva o andamento em BPM, com passos no tempo, transferência de peso e calcanhar primeiro. Proíba câmera lenta pelo nome. | Os modelos puxam câmera lenta sozinhos, e "slow dance" vira slow motion flutuante. "Fast" é a palavra que mais degrada. | `sd20/FAILURE-MODES.md` § fight (slow-mo ban), § Walking; `sd20/SKILL.md` § "fast" |
| 20 | **Dança no prompt = 3–4 movimentos em termos corporais simples** (qual pé, qual direção, o que as mãos fazem). Coreografia de trend vai para motion control, não para o prompt. | Nome de passo não é renderizado, "dança" sozinha não significa nada, e a descrição corporal funciona. | `OS/templates/10-dance-music-performance.md` § Beat-by-beat; `higgsfield-motion` § Kling MC |
| 21 | **FOV em graus, só da tabela, e bloco CAMERA em 3º.** No máximo 1 movimento de câmera (parada é o melhor). Micro-movimento leva distância e tempo. Selfie = 84°, passante = 63°. | Em milímetros ou em valor intermediário, o FOV é ignorado. Movimento composto treme. | U1; `sd20/SKILL.md` § FOV anchors; `higgsfield-camera` § One-Move, § Micro-moves |
| 22 | **Frase positiva.** Proibição só onde o padrão do modelo já é a falha (sorriso, câmera lenta, gente extra, figurante olhando, legenda, música), curta e depois da frase positiva. | Toda palavra é lida como algo a renderizar: o que você escreve é o que você invoca, inclusive dentro de um "não". | `negative-constraints.md` § The words you write…; `sd20/SKILL.md` § No negative prompts |
| 23 | **Isolamento de contexto.** Cada prompt é um documento lacrado. Valores que precisam bater entre clipes (FOV, mapa do lugar, velocidade) são repetidos por extenso, nunca com "como antes" ou número de cena. Trave o cenário: `the set contains only what the reference shows`. | O modelo não tem memória, e inventar ambiente é a deriva nº 1. | U1; `sd20/SKILL.md` § Context isolation, § POSITIVE LOCKS; `sd20/FAILURE-MODES.md` § Walking (shared absolute) |
| 24 | **Prop:** cadeia causal (estrutura → apoio → força → resposta do material → estado final), orientação em termos de câmera ("screen faces the lens"), mãos contadas e com dono, seta vermelha na ficha do prop. Lugares que ficaram vagos aparecem vazios. | Sem mecanismo, a mão mima e o objeto não muda. Em close sem contagem, aparece uma terceira mão. | `sd20/FAILURE-MODES.md` § Mimed manipulation, § Orphan limbs; `sd20/PRODUCTION-PATTERNS.md` § Red-Arrow; U2 |
| 25 | **Iteração disciplinada:** uma variável por take. A mesma falha em 2 takes obriga a reescrever. Teto de 4 tentativas ou 160 créditos por ideia. O 480p valida a estrutura, não o take. Antes de descartar, aproveite os segundos bons. | Sem seed, cada render é um novo sorteio. Mudar várias coisas impede o diagnóstico. | `higgsfield-troubleshoot` § Take Triage, § Stop-Rule Ladder; `sd20/SKILL.md` § Drafts Validate the Prompt; ata D5 |

---

## B) Método de planejamento para clipes deadpan de 8–12 s

### B1. A grade de beats (fixa)

Quatro beats, duas ações. O beat 0 e o beat 3 não são ações: são estados.

| Beat | Função | 8 s | **10 s (padrão)** | 12 s |
|---|---|---|---|---|
| B0 Fixar | Personagem já na pose, no lugar, figurantes já em movimento. Sem movimento de câmera e sem ação roteirizada (só respiração e piscada). O modelo "fotografa" as posições. | 0–0,8 | 0–1,0 | 0–1,0 |
| B1 Assinatura (ação 1) | Dança lenta de assinatura ou ação banal: 3–4 movimentos simples, num sentido só | 0,8–5,0 | 1,0–6,5 | 1,0–8,0 |
| B2 Gag (ação 2) | Um único evento físico causal (o topete enrosca no varal, a lata sai de dentro do laquê) | 5,0–6,8 | 6,5–8,5 | 8,0–10,5 |
| B3 Resultado/loop | Resultado parado, deadpan na lente. O último frame lembra o primeiro, para fechar o loop. | 6,8–8,0 | 8,5–10,0 | 10,5–12,0 |

Regras de duração:
- A `duration` é a soma dos beats e o valor declarado no job. Os tempos no prompt são orçamento, não corte exato (`sd25` § Timestamps).
- Cada movimento de dança precisa de ≥1,5 s. O gag precisa de ≥2 s, contando o assentamento.
- Se a assinatura não cabe, a solução é **12 s, não mais movimentos**.
- No motion control e no v2v, a duração é a do vídeo-fonte. Corte o vídeo antes, nunca peça mais do que ele tem (`sd25/VFX-PIPELINE.md` § Stage 4). O mínimo do Seedance é 4 s.

### B2. Plano-sequência ou corte

| Situação | Decisão |
|---|---|
| Câmera selfie | **Sempre plano-sequência.** O braço do personagem sai pela borda do quadro. A dança fica do peito para cima (topete, ombros, cabeça). |
| Câmera parada de passante | Plano-sequência, corpo inteiro, de 3 a 5 m de distância |
| O gag pede outro tamanho de quadro (inserto do prop, detalhe do topete) | **Duas gerações, emendadas na edição.** O último frame do clipe A vira o `start_image` do clipe B, com a ação cruzando o corte no meio do movimento. A troca muda o tamanho do quadro **e** o tipo de câmera (`ENGINE-RULES` 11). |
| Precisa mesmo de um corte num clipe só | `Exactly one HARD CUT at 6.5s; otherwise the camera holds still.` Use pouco e valide no 480p. |
| O 2º clipe começa onde o 1º terminou, mas o personagem sai do quadro | Saiu do quadro = corte implícito (`ENGINE-RULES` 6). Nunca saída e reentrada no mesmo plano. Planeje uma pausa de quadro vazio de 1–1,5 s como ponto de emenda. |

### B3. Qual material usar: start/end frame, grade de storyboard ou referência de imagem

| Material | Papel no `omni_reference` | Use quando | Não use quando |
|---|---|---|---|
| Recorte do rosto 3/4 (da ficha) | `image_references` → identidade, preservação total | **Sempre** | — |
| Ficha de silhueta (perfil, costas e topo, sem rosto legível) | `image_references` → só a forma do cabelo/bigode e o figurino | Sempre que a silhueta rígida aparece | — |
| Frame A (GPT Image) | `start_image` | **Sempre.** Trava o lugar, a câmera, a pose de assinatura e a posição dos figurantes. | — |
| Frame B (GPT Image) | `end_image` | O gag tem estado final preciso: orientação do prop, lugar vago, topete deformado de propósito. É o caso mais comum. | Quando o fim é livre (dança pura de trend) |
| Grade de storyboard (4–6 painéis) | `image_references` → só ordem e composição | ≥3 momentos que o modelo precisa ordenar (assinatura → gatilho → resultado), ou para curar a ideia antes de gastar com vídeo | Clipe de 1 ação só, porque a grade aumenta o risco de corte |
| Keyframes separados (3+ imagens em ordem) | `image_references` + `Use @Image 3 through @Image 5 as keyframes in this order` | Quando a grade não segura a pose de cada painel | — |
| Ficha do prop (com seta vermelha se precisar) | `image_references` → estrutura, material e lado de contato | O prop aparece no gag | — |

**Pacote padrão de um clipe de 10 s:** rosto + silhueta + `start_image` + `end_image` + (grade, se houver ≥3 momentos). São 4 ou 5 imagens, dentro da faixa estável de 1–8 sujeitos (`sd25` § Material budget). Cada material extra é mais uma fonte possível de vazamento.

**Ordem de produção (storyboard primeiro, U2):**
1. Ficha do personagem (uma vez, aprovada).
2. Grade do storyboard. É barata, o revisor de IA e o Caio curam.
3. Frame A, feito a partir do painel 1.
4. Frame B, feito **como edição do frame A**, para manter câmera e geometria.
5. Draft do Seedance em 480p, só quando o template for novo.
6. Versão final em 720p.
7. Revisor de vídeo.

O storyboard de cada clipe começa no estado final do clipe anterior.

### B4. Cena com contraparte (dois atores: soco, empurrão, entrega, encarada)

Motivo: no clipe de boxe do Caio, o personagem ficou **de costas para quem dava o soco**. Sem bloco espacial, o Seedance escolhe as posições sozinho, e os atores trocam de lado ou desviam o olhar (`templates/seedance/multi-character-anchor.md` § BAD; `sd20/SKILL.md` § Spatial Layout Block).

1. **Prefira uma contraparte que não seja gente.** O saco de pancada, o poste e o varal não viram de costas. Um segundo ator só entra se o gag precisa dele.
2. **Cabeçalho `EXACTLY 2 characters`** e um bloco `SPATIAL LAYOUT` (modelo no C4) com uma linha por ator: terço da tela, distância da câmera, orientação do corpo **em relação ao outro ator e à lente**, para onde olha e o que toca. Feche com as relações: distância entre os dois em metros, eyeline (`A → B`, `B → lens`), regra de cruzamento (`neither crosses the central vertical axis`) e quem fica mais perto da câmera (`multi-character-anchor.md`; `vocab.md` § Crossing rule).
3. **O compromisso deadpan:** o protagonista fica com **o peito a 45° virado para o parceiro e o rosto na lente** (`chest turned 45° toward the boxer at frame-right, face turned to the lens`). O parceiro fica de perfil ou 3/4 para o protagonista e **nunca olha para a lente**. Assim a regra 18 (rosto visível) e a interação convivem.
4. **A orientação vem do frame A.** O start frame já mostra os dois na posição e orientação certas, e o end frame mostra o resultado. A referência manda mais que o texto (D, linha "figurantes reagem").
5. **Um ator age por estágio. A reação tem hora marcada** e começa no contato, não antes. Exemplo: `[Stage 3 — 6.5-7.5s] The boxer's right glove travels screen-right to screen-left and stops against Gerson's pompadour. [Stage 4 — 7.5-8.5s] On contact, the pompadour tilts 10° and springs back as one block; Gerson does not move his face.` Todo golpe tem nome **e vetor** (direção em termos de tela e onde termina), senão é reinventado a cada take (`sd20/FAILURE-MODES.md` § A fight generated as separate clips).
6. **O parceiro tem uma tarefa enquanto espera** ("bounces on his toes, guard up, eyes on Gerson"), nunca um rosto parado (`higgsfield-acting` § Listening and reaction).
7. **Mais de um contato = mais de um clipe.** Uma troca (A ataca, B reage, A responde) vira clipes encadeados, com o último frame de um como `start_image` do outro e o movimento cruzando o corte no meio. A edição faz a troca, não o modelo (`sd20/FAILURE-MODES.md` § fight; `videos-analisados.md` §9–§10).
8. **Planeje de cima, mostre de frente.** O mapa de planta baixa (`templates/seedance/top-down-map.md`) serve para o Claude raciocinar; o que vai ao modelo é a prosa do bloco e o frame A, nunca a planta.

---

## C) Templates

Convenção: `{{...}}` é campo a preencher. O texto em inglês vai ao modelo como está.

### C1. Ficha de personagem (GPT Image 2.5)

Use o Formato A (JSON), porque o GPT Image respeita layout por regiões (`higgsfield-gpt-image-2` § 3). Gere em `quality: high`, na **maior resolução disponível** (o `rosto.png` é um recorte de 1/4 da ficha), e 2:3 ou outra proporção vertical disponível. Uma ficha por figurino (`videos-analisados.md` §5–6). Evite "photorealistic" com rosto (deixa a pele plástica) e use linguagem de fotografia (`gpt-image-2` § 1, § 4).

```json
{
  "type": "character reference sheet, studio photograph, 4 panels in a 2x2 grid",
  "style": "plain documentary studio photograph, flat even soft light, real skin with visible pores and small asymmetries, no retouch, sharp focus throughout",
  "background": "flat solid neutral grey #8a8a8a, seamless, no gradient, no shadows on the backdrop",
  "character": "{{role, e.g. 'a slim brega singer in a shiny wine-red shirt and white flared trousers'}}, {{signature silhouette, e.g. 'a giant black lacquered pompadour rising 25 cm above the forehead, as tall as his own head, glossy, rigid like molded resin, every strand fused into one smooth solid shape'}}, expression: deadpan — lips closed and relaxed, lip corners level, brows level, eyes calm",
  "layout": {
    "top_left":  "large close-up portrait, head turned 3/4 to camera-left, eyes to lens, the full pompadour inside the frame with headroom — the ONLY readable face on the sheet",
    "top_right": "full body true side profile facing frame-left, flat backlight so the body and the pompadour read as a crisp outline; face in shadow, unreadable",
    "bottom_left": "full body from behind, standing straight, full pompadour visible from the back",
    "bottom_right": "full body front, head tilted down 45° so the top of the pompadour fills the upper area and the face is hidden"
  },
  "rules": "same person, same outfit, same scale and lighting in all four panels; exactly one person per panel; no text, no labels, no numbers, no borders thicker than 8 px white"
}
```

> Por que os painéis de corpo inteiro escondem o rosto: o rosto pequeno não pode ser legível (face-lock crop), mas a silhueta precisa do cabelo inteiro. Por isso a ficha usa contraluz no perfil, vista de costas e cabeça inclinada na frente, em vez de cortar a cabeça. Depois de aprovada, **recorte a ficha em 2 arquivos**: `rosto.png` (o painel top_left) e `silhueta.png` (os outros 3). Correções pontuais (cor da camisa, uma mecha) se fazem com edição e máscara sobre o original, nunca com uma segunda passada completa (`HELL-GRIND` § masks). Esse painel em contraluz também serve de teste da "silhueta preta na miniatura" (ata D6).

### C2. Frame inicial e frame final (GPT Image 2.5 `images.edit` com referências)

Entradas: `[rosto.png, silhueta.png, painel do storyboard (opcional), foto do lugar (opcional)]`. Use variant `sunburst` se estiver disponível (precisão de edição), `quality: high`, 9:16 ou o retrato mais próximo que a API aceitar. Confira a proporção final antes de mandar ao Seedance.

**Frame A (início):**
```
Vertical 9:16 smartphone photograph, {{CAMERA: "selfie taken by the man himself with the front camera at arm's length, 84° wide-angle, phone 55 cm from his face, slight upward angle" | "static phone on a passerby's tripod at chest height, 63° field of view, 4 m away"}}.
Location: {{concrete Brazilian place, e.g. "a covered bus stop on a busy avenue in São Paulo outskirts, yellow-and-black curb, a pastel stall behind, overcast midday light"}}.
The man from image 1 and image 2 — same face as image 1, same pompadour shape and outfit as image 2 — stands {{position, e.g. "in the center third, chest square to the lens, feet on the yellow curb line"}}, already in his signature pose: {{e.g. "right index finger raised beside his temple, left hand on his belt buckle"}}. Deadpan: lips closed, lip corners level, eyes looking straight into the lens.
The pompadour is fully inside the frame with 10% headroom above it.
Background: exactly {{5}} ordinary passersby busy with their own tasks — {{e.g. "one reads a phone, one carries grocery bags, one buys pastel"}} — none of them looking at him.
Props: {{exact count and orientation, e.g. "exactly one phone, held in his left hand, screen facing his chest"}}.
Natural daylight, deep depth of field, everything sharp, smartphone HDR look.
Exactly one main character. No text, no captions, no speech balloons, no watermarks.
```

**Frame B (fim):** use o **frame A como imagem 1** e o rosto e a silhueta como 2 e 3.
```
Edit image 1. Keep the exact same camera position, field of view, location, lighting, passersby layout and the man's identity (face from image 2, pompadour and outfit from image 3).
Change only: {{the gag's end state, e.g. "the pompadour is now hooked on the bus-stop timetable sign above him, the sign tilted 20° to frame-right; he stands still under it, chest square to the lens"}}.
{{Vacated places stated empty, e.g. "the spot on the bench where the bag was is now empty bare metal."}}
{{Prop orientation, e.g. "the phone is in his right trouser pocket, only its top 2 cm visible."}}
Deadpan: lips closed, lip corners level, eyes into the lens.
Exactly one main character, exactly {{5}} passersby, all still busy with their own tasks, none looking at him. No text, no balloons.
```

### C3. Grade de storyboard para clipe de 10 s (GPT Image 2.5)

Para 4 painéis, use uma grade 2×2 numa tela 9:16 (cada painel fica 9:16). Para 6 painéis, use 3×2 numa tela 4:5 (cada painel fica perto de 9:16). Painéis fotorreais com o mesmo personagem: assim o "estilo do desenho" não vaza. Entradas: rosto, silhueta e, se houver, o último frame do clipe anterior.

```json
{
  "type": "photographic storyboard, {{4}} panels in a {{2x2}} grid, read left to right, top to bottom, thin white gutters",
  "style": "vertical smartphone photographs, natural daylight, identical camera position and field of view in every panel ({{84° selfie at arm's length | 63° static from 4 m}})",
  "character": "the man from image 1 (face) and image 2 (pompadour, outfit); exactly one main character in every panel; deadpan in every panel: lips closed, lip corners level, eyes into the lens",
  "location": "{{same concrete location text as frame A}}; exactly {{5}} passersby in every panel, each busy with their own task, none looking at him",
  "panels": [
    {"position": "top-left",     "time": "0-1s",   "state": "{{= end state of the previous clip / start pose}}"},
    {"position": "top-right",    "time": "1-6.5s", "state": "{{signature move at its peak, e.g. 'hips shifted to frame-left, right finger by temple'}}"},
    {"position": "bottom-left",  "time": "6.5-8.5s","state": "{{gag trigger, physical cause visible, e.g. 'pompadour tip touching the timetable sign edge'}}"},
    {"position": "bottom-right", "time": "8.5-10s","state": "{{gag result, settled, prop orientation + vacated places explicit}}"}
  ],
  "rules": "same outfit, same pompadour shape and size in every panel; props exactly as listed per panel; no text, no numbers, no speech balloons, no arrows"
}
```

Antes de aprovar, confira: contagem de pessoas por painel, topete idêntico, orientação dos props, lugar vago vazio e painel 1 igual ao fim do clipe anterior.

### C4. Prompt do Seedance 2.5 (`omni_reference`, blocos)

Parâmetros: `model: seedance_2_5`, `mode: omni_reference`, `aspect_ratio: 9:16`, `duration: {{10}}`, `resolution: 720p` (480p no draft), `generate_audio: false`. Medias: `start_image` = frame A, `end_image` = frame B e `image_references` = [rosto, silhueta, grade?, prop?], nesta ordem.

```
SCENE CONTEXT
EXACTLY 1 main character — {{GERSON}}, a slim brega singer with a giant black lacquered pompadour — plus exactly {{5}} background passersby. {{One-sentence visible gag, e.g. "At a São Paulo bus stop he performs his slow signature move until his rigid pompadour hooks the timetable sign."}}

ACTIVE REFERENCES
The start frame defines the opening composition, positions, pose and camera. The end frame defines the final composition and the gag's end state.
@Image 1 defines {{GERSON}}'s face — full-preserve, 100% matches the reference.
@Image 2 defines only his pompadour shape and outfit — full-preserve. Do not take the grey backdrop, the panel layout or the extra views.
{{@Image 3 provides a 4-panel storyboard read left to right, top to bottom: panel 1 is 0-1s, panel 2 is 1-6.5s, panel 3 is 6.5-8.5s, panel 4 is 8.5-10s. The panels are moments of ONE continuous shot. Do not reorder; do not invent shots; do not use its gutters.}}
{{@Image 4 defines the {{prop}}'s structure and material only.}}

CAMERA
{{Selfie: "Front smartphone camera held at arm's length by his own right hand, 84° field of view, 55 cm from his face, lens slightly below eye level. His right arm extends toward the lens and exits the bottom-right frame edge." | Passerby: "Static smartphone on a tripod at chest height, 63° field of view, 4 m from him, locked off."}} One continuous shot; the camera does not cut on its own; no drift mid-shot.

{{SPATIAL LAYOUT — só com contraparte humana (B4):
GERSON: frame-left third, 3 m from the lens, chest turned 45° toward the boxer, face turned to the lens, eyes on the lens, feet planted on the gym mat.
BOXER: frame-right third, 3.5 m from the lens, body in three-quarter profile facing Gerson (screen-left), guard up, eyes on Gerson, never on the lens.
Relationships: 1.2 m between them; eyeline boxer → Gerson, Gerson → lens; neither crosses the central vertical axis; Gerson's back never turns to the boxer or to the lens.}}

LOCATION MAP
{{Frame-left: pastel stall. Center: bus-stop bench and timetable sign 2.1 m high. Frame-right: avenue curb.}} The set contains only what the start frame shows.

ACTION
[Stage 1 — 0-1s] He holds the signature pose from the start frame; breathing lifts the chest, one slow blink. End state: same pose, eyes into the lens.
[Stage 2 — 1-6.5s] Real-time, at 90 BPM: {{3-4 plain moves, e.g. "he shifts his weight onto his left foot, heel first; his hips sway once to frame-left and once to frame-right on the beat; his right index finger taps his temple twice"}}. His chest stays square to the lens; hips rotate at most 30°; his face is visible in every frame. End state: {{pose}}.
[Stage 3 — 6.5-8.5s] {{Gag as a causal chain: initial structure → anchor → force → material response, e.g. "he straightens to full height; the tip of the pompadour meets the lower edge of the timetable sign; the sign tilts 20° to frame-right and stays hooked on the pompadour"}}. End state: {{= end frame}}.
[Stage 4 — 8.5-10s] Everything settles and holds; he stares into the lens. The final frame matches the end frame.

PERFORMANCE
Deadpan throughout: lips closed and relaxed, jaw closed, lip corners level, brows level; one slow deliberate blink every 3-4 s; eyes locked on the lens with tiny saccades. Controlled stillness of the face while the body moves. Mouth closed throughout — no smile, no speech.
Passersby continue their own tasks — {{tasks}} — each moving on their own rhythm; none turns toward him.

PHYSICS
The pompadour is a single rigid lacquered mass, 25 cm tall, as hard as molded resin: it moves only as one solid block with his skull and keeps its exact outline in every frame. Still air. Feet keep ground contact, heel lands first, weight visibly transfers. Exactly two hands in frame, both his, {{entry points}}. Real-time speed, normal playback — no slow motion.

LIGHTING
{{Overcast midday daylight, soft shadows under the bus-stop roof, 5600K.}} Smartphone video look, deep depth of field, everything sharp.

POSITIVE LOCKS
Exactly one main character and exactly {{5}} passersby for the whole clip. His face matches @Image 1 and his pompadour matches @Image 2 at every distance. {{Prop count + orientation.}} No captions, no subtitles, no text on screen.
```

Notas:
- O ACTION usa `[Stage]` com estado final, sem "Shot 1/2".
- Se o draft em 480p mostrar cortes, tire primeiro a grade (uma variável só).
- Não prenda a regra "never looks into the camera" do HELL-GRIND: nós **queremos** o olhar na lente, então ele precisa estar escrito.

### C5. Motion control para trend (Kling 3.0 MC / Genjutsu)

**Escolha:**
- **Kling 3.0 Motion Control:** MCP `motion_control` (`image_id`, `motion_video_id`, `scene_control`) ou CLI workflow `kling3_0_motion_control` (`mode std|pro`, `background_source input_image|input_video`). Tem prompt de cena e **permite usar o cenário da imagem**. Nós sempre usamos o nosso cenário (ata D7): no Kling, isso é `background_source = input_image`. Desde 05/10 fica como A/B do Genjutsu, que é o padrão do pipeline (`video-request` de trend).
- **Genjutsu (`hf_mult_motion_control`, via `generate_video`):** usa `image_references` + `video_references` + **prompt de cena**. Corrigido em 05/10 pelo tutorial assistido (`videos-analisados.md` §3): ele aceita a descrição de ambiente, câmera e visual, sai em até 1080p, preserva caminhada, tremor e timing da fonte, e aceita 2 personagens. A fonte pode vir da **motion library** do Higgsfield. Use como padrão para trend quando quiser manter tudo dentro do Higgsfield; o Kling MC fica como A/B. Nunca use a ferramenta legada `motion_control` para o Genjutsu.

**Requisitos do vídeo-fonte** (`higgsfield-motion` § Motion Reference Input Checklist; `higgsfield-troubleshoot` § MC Failures):
- [ ] Um único dançarino, da cabeça aos pés no quadro o tempo todo, sem oclusão.
- [ ] Um plano contínuo, sem corte, dissolve ou zoom. Câmera parada de preferência.
- [ ] 8–10 s, cortado no trecho da coreografia (≤10 s, critério do radar). O limite é de 3–30 s.
- [ ] Velocidade lenta a moderada. Se o output sair **mais curto que a fonte**, o movimento era rápido demais: desacelere a fonte para 50–75% e corte de novo.
- [ ] 9:16, bom contraste entre corpo e fundo, pessoa real (não animação).
- [ ] Mãos visíveis a fonte inteira (o Kling inventa e borra as mãos que não vê) e corpo suficiente no quadro (perto demais, o Kling recusa com "not enough upper body"). Ver `videos-analisados.md` §8.
- [ ] Assinatura recorrente: prefira uma fonte gravada pelo Caio (corpo inteiro, câmera parada, deadpan), reusada em todos os vídeos do personagem (§8).
- [ ] O baixar e subir no Higgsfield é feito antes, com o arquivo .mp4 (README).

**Imagem do personagem = edição do 1º frame da fonte** (`videos-analisados.md` §2). Pegue o primeiro frame do vídeo-fonte (`python -m pipeline` usa ffmpeg) e edite no GPT Image 2.5 com o rosto e a silhueta como referências: `Replace the dancer with the man from image 2 and image 3 — same face, same pompadour and outfit. Keep the exact pose, framing, location and light of image 1. Must look like a real smartphone photo inside the original scene. Deadpan: lips closed, lip corners level.` Faça 4 variações e cure. Assim pose, enquadramento e cenário batem com a fonte.

**Requisitos da imagem do personagem:** frame A do C2 em modo passante (63°, corpo inteiro e pés visíveis), com **a mesma pose, o mesmo enquadramento e o mesmo tamanho de sujeito do primeiro frame da fonte** (marcas de chão e props que a dança toca na mesma linha e ângulo; senão sai física quebrada, `videos-analisados.md` §8), rosto legível, topete inteiro com 10% de folga acima, braços sem cobrir o rosto e figurantes posicionados longe da trajetória da dança.

**Prompt do Kling MC (só cena: o movimento vem do vídeo):**
```
Keep the scene, lighting and passersby from the character image. Overcast midday daylight at a São Paulo bus stop, smartphone video look, everything sharp. The man's giant black pompadour is a rigid lacquered solid that moves only as one block with his head and keeps its exact outline. His face stays deadpan: lips closed, lip corners level, eyes toward the lens. Exactly 5 passersby continue their own tasks — {{one task each, e.g. 'one walks past frame-left to frame-right, one checks a phone, one buys pastel'}} — moving throughout the clip; none looks at him. Real-time speed.
```
Os figurantes e a câmera **precisam estar escritos**: a fonte não traz movimento de fundo e o Kling 3.0 tende a deixar o fundo parado (`videos-analisados.md` §8). Orientação: `Video Orientation` / `Matches Video` (no Kling/OpenArt, *Exact*, até 30 s). *Partial* (outra posição, câmera livre) só vai até 10 s. O Kling MC 2.6 é um A/B mais barato; o 3.0 exagera a nitidez de pele e barba. **O gag vem depois:** pegue o último frame do clipe de MC como `start_image` de um clipe de 4–5 s no Seedance 2.5 (C4, só os stages 3 e 4) e emende os dois. No pipeline: campo `gag_followup` no roteiro de trend → `video-request <ref> --gag` (último frame do MC como `start_image`) → `review gag` → o `package` emenda MC + gag (sem reencode quando os clipes batem). A emenda perde o C2PA do provedor: o rótulo "AI info" no post é obrigatório.

### C6. Prompt de reparo

Antes de tudo, dê um veredito (`higgsfield-troubleshoot` § Take Triage):
- **manter**;
- **corrigir na pós** (trim, cor, frames instáveis nas pontas);
- **editar** (uma camada errada);
- **re-roll** (prompt certo, azar);
- **reescrever** (a mesma falha em 2 takes).

Mude **uma** variável por vez.

**(a) Regerar com escopo travado** (Repair Skeleton, `sd20/SKILL.md`): repita o prompt C4 inteiro, palavra por palavra, e troque **só** o bloco que falhou. No topo, acrescente:
```
REPAIR SCOPE
Keep the framing, pacing, location, passersby layout, start and end frames, and {{GERSON}}'s identity exactly as specified.
Change only: {{one element, e.g. "in Stage 2 his chest stays square to the lens; the hip sway is limited to 30°; his face is visible in every frame"}}.
Protect: the pompadour outline, the deadpan mouth, the passersby ignoring him.
```

**(b) `video_edit` em escopo** (quando composição e timing estão certos e só uma camada falhou). É cobrado pela duração total do vídeo-fonte (`sd25/MODE-PLAYBOOKS.md` § Video editing):
```
[Edit Goal] Edit @Video 1. Only from {{6.0-7.5}} seconds, {{change the man's mouth to closed and relaxed with level lip corners}}.
[Source Video Role] @Video 1 is the sole editing master. It defines the character, location, passersby, actions, composition, camera and event order.
[Edit Scope] Modify only {{his mouth and lower face}} within that time range.
[Content to Preserve] Keep his identity, pompadour shape, outfit, body motion, the passersby, the camera and all timing from @Video 1.
```

**(d) Object swap do Genjutsu** (`videos-analisados.md` §3): troca só o figurino ou o prop errado num vídeo que ficou bom. O resto da cena fica intacto.

**(c) Aproveitamento:** antes de descartar, marque entrada e saída do trecho bom. Um clipe "ruim" muitas vezes tem 2–3 s utilizáveis (`sd20/FAILURE-MODES.md` § Failed-generation salvage). Registre tudo em `playbook/falhas.md`.

---

**Teste de moderação de rosto (personagem novo):** antes do primeiro vídeo, rode 4 s em 480p. Se o Seedance 2.5 bloquear o rosto, gere uma ficha nova e neutra (C1) e teste de novo (`videos-analisados.md` §1).

## D) Tabela de diagnóstico de falhas

| Sintoma | Causa provável | Correção (uma variável) |
|---|---|---|
| **Deriva de identidade** (rosto muda ao longo do clipe ou entre clipes) | Texto longo de aparência brigando com a ref; vários rostos legíveis na ficha; encadeamento de clipes a partir de frame derivado | Corte o texto para papel + 2 marcas. Ficha com um rosto só. Reancore sempre na ficha **original**, nunca num frame da cauda (`higgsfield-troubleshoot` § Atlas). No MC, use imagem com rosto maior e luz uniforme. |
| **Cabelo rígido deforma** (o topete balança, achata ou muda de altura) | Cabelo é material que se mexe por padrão; palavras de vento ou "dança" contaminam; ref sem perfil ou topo; escala vaga | Bloco PHYSICS com material, medida e marco corporal mais "still air". Silhueta de perfil e costas no asset. Remova "wind", "breeze" e "flowing". No MC, frase de rigidez no prompt. Se persistir, o gag não pode exigir contato violento com o cabelo. |
| **Personagem vira de costas ou para longe da câmera** | Ação sem vetor; dança com giros implícitos; leitura abstrata ("desafia", "confronta"); tempo sobrando (preenchimento reverso) | Trava de orientação em graus, "face visible in every frame" e olhar na lente escrito. Giro só nomeado com duração e direção final. Duração igual ao conteúdo. Corte a ideia abstrata. |
| **Personagem de frente para o lado errado durante a interação** (de costas para quem soca, encara o vazio, parceiro olha para a lente) | Nenhum bloco espacial: o modelo escolhe as posições; orientação escrita só em relação à câmera; frame A com os dois mal orientados; a reação descrita como relação abstrata ("enfrenta") | Bloco `SPATIAL LAYOUT` (C4) com a orientação de cada um **em relação ao outro e à lente**, eyeline `A → B`, regra de cruzamento e o compromisso deadpan (peito 45° para o parceiro, rosto na lente). Refaça o frame A com os dois já orientados; é a primeira variável a trocar, porque a referência manda mais que o texto (B4). |
| **Reação fora de hora** (o protagonista reage antes do golpe, o golpe não chega, os dois agem juntos) | Ação e reação no mesmo estágio; golpe sem vetor nem ponto de parada; mais de um contato num clipe | Um ator por estágio; a reação começa "on contact" no estágio seguinte; golpe com nome, vetor de tela e ponto final. Mais de um contato vira clipes encadeados com o movimento cruzando o corte (B4; `sd20/FAILURE-MODES.md` § fight). |
| **Os dois trocam de lado ou viram espelho entre clipes** | Eixo não travado; cada prompt reinventa o layout | Repita o mesmo `SPATIAL LAYOUT` por extenso em todos os clipes da cena (regra 23) e diga a direção de tela ("the boxer stays frame-right") (`higgsfield-troubleshoot` § Screen direction flips). |
| **Membros extras** (terceira mão, braço sem dono) | Nenhuma contagem de mãos; selfie com braço de origem ambígua; mãos perto de outras pessoas | `Exactly two hands in frame, both his: right arm exits bottom-right edge holding the phone, left hand…`. Mantenha figurantes a mais de 1 m. |
| **Figurantes reagem** (olham, riem, filmam) | Reação em grupo é o padrão diante de um espetáculo; figurantes sem tarefa | Uma tarefa para cada, movimento defasado e a proibição curta `none turns toward him`. Figurantes no plano de fundo. Coloque a proibição também no frame A e no B (a referência manda mais que o texto). |
| **Número errado de pessoas** (clone, gente surgindo) | Sem cabeçalho de contagem; ref de personagem usada como "multidão" | `EXACTLY 1 main character… exactly 5 passersby` no SCENE CONTEXT e nos LOCKS. Figurantes nunca usam a ref do protagonista. Para figurantes variados, use uma ficha "VARIETY reference" (`PRODUCTION-PATTERNS` § Reference-Role Vocabulary). |
| **Orientação do prop errada** (tela virada, objeto girado) | A orientação não foi dita em termos de câmera; o prop não está no end frame; não há ficha do lado certo | Orientação relativa à lente ("screen faces the lens"). End frame com o prop no estado final. Ficha do prop com a face exposta e a seta vermelha lida no texto. |
| **Câmera inventa cortes** | Grade de storyboard lida como lista de planos; rótulos por segundo; muito conteúdo num trecho | `One continuous shot, the camera does not cut on its own`. "The panels are moments of ONE continuous shot". Se continuar, tire a grade e fique com start e end frame. |
| **Câmera lenta ou movimento flutuante** | "slow", "graceful", "smooth" lidos como velocidade; sem contato com o chão; modelo puxa slow-mo sozinho | Andamento em BPM, "real-time speed, normal playback — no slow motion", calcanhar primeiro e peso transferido. Troque "slow dance" por "small moves on a 90 BPM count". |
| **Dança parece falsa** (deslizando, sem peso, genérica) | Passo citado por nome ou "dances" vago; movimento demais; sem física de passada | 3–4 movimentos em termos corporais (pé, direção, mão) com peso. Se for trend, use MC com fonte limpa. No MC: mude Matches Video/Image ou desacelere a fonte. |
| **Boca se mexe ou sorri** | Áudio gerado preenchendo silêncio; nenhum estado de boca escrito; dançar puxa sorriso por padrão | `generate_audio: false`. Anatomia do deadpan no PERFORMANCE mais o tail `mouth closed throughout — no smile, no speech`. Frames A e B com a boca fechada. Correção pontual: `video_edit` com escopo no rosto, na janela de tempo. |

---

## E) Rubrica de QA para revisor automático de visão

### E1. Amostragem

| Material | Amostrar |
|---|---|
| Frame ou storyboard (imagem) | A imagem inteira e cada painel recortado |
| Vídeo | 2 fps no clipe todo (cerca de 20 frames em 10 s), mais 6 fps na janela do gag (B2), mais o primeiro e o último frame |
| Detecção de corte | Diferença de histograma entre frames consecutivos a 6 fps em todo o clipe (cálculo, não visão). Salto acima de um limiar com mudança de enquadramento conta como corte. |

Referências passadas ao revisor: `rosto.png`, `silhueta.png`, frame A, frame B e a planilha de beats (contagens e props).

### E2. Portões eliminatórios (sim/não; um "não" reprova)

| ID | Pergunta | Aplica a | Passa se |
|---|---|---|---|
| G1 | Número de protagonistas = 1 e de figurantes = N±1? | todos | 100% dos frames |
| G2 | O rosto do protagonista é a mesma pessoa de `rosto.png`? | todos | ≥95% dos frames com rosto visível |
| G3 | A silhueta (altura, contorno e volume do topete) bate com `silhueta.png`? | todos | 100% dos frames. Altura do topete / altura da cabeça dentro de ±15% da ficha. |
| G4 | O rosto está visível (frontal até 3/4, ≤45°)? | vídeo | ≥85% dos frames de B1; 100% dos de B3 |
| G5 | Mãos ≤2, cada uma ligada a um braço e um ombro? | todos | 100% |
| G6 | Boca fechada e sem sorriso (cantos da boca nivelados, sem dentes)? | todos | ≥95% dos frames e nenhum sorriso |
| G7 | Algum figurante olha ou se vira para o protagonista? | todos | no máximo 1 frame isolado |
| G8 | Corte detectado? | vídeo | 0 cortes (ou exatamente os cortes declarados) |
| G9 | Texto, legenda, balão ou marca d'água? | todos | nenhum (letreiros diegéticos do lugar são ok) |
| G10 | Props com a contagem e a orientação da planilha, e lugares vagos vazios? | frames, painéis e último frame | 100% |
| G11 | O evento do gag acontece e o resultado fica parado ≥0,5 s antes do fim? | vídeo | sim |
| G12 | O último frame corresponde ao frame B (composição, estado do gag)? | vídeo | sim |
| G13 | Com contraparte humana: cada ator mantém o lado de tela e a orientação do frame A (ninguém de costas para o parceiro, parceiro sem olhar para a lente)? | vídeo com 2 atores | ≥95% dos frames (B4) |

### E3. Notas (0–5)

| ID | Critério | 5 = |
|---|---|---|
| S1 | Fidelidade de identidade | indistinguível da ficha |
| S2 | Rigidez da silhueta | contorno idêntico em todos os frames, move-se como bloco |
| S3 | Deadpan | rosto imóvel e vivo: piscadas lentas, microssacadas, olhar na lente |
| S4 | Física do movimento | tempo real, peso, contato com o chão, sem deslizar nem flutuar |
| S5 | Leitura da dança/assinatura | movimentos claros, no tempo, sem membros borrados |
| S6 | Autenticidade do lugar | Brasil popular reconhecível, sem lugar genérico de banco de imagem |
| S7 | Visual de celular fotorreal | parece filmado por um telefone, pele real, sem plástico |
| S8 | Legibilidade do gag sem som | entende-se em 1 visualização sem áudio |
| S9 | Loop | o último frame emenda no primeiro sem salto visível |
| S10 (só storyboard) | Fidelidade ao roteiro de beats | cada painel = o estado pedido |

### E4. Limiares e ações

- **Aprova para o Caio:** todos os portões passam, média de S1–S9 ≥3,8, nenhuma nota <3, e S1, S2 e S3 ≥4.
- **Refaz automático:** um portão falha ou a média fica <3,8. O revisor devolve `{gate|score, frame_ts, evidência em 1 linha, categoria}`, com categoria do enum `identity-drift | wardrobe-contamination | extra-cuts | blocking-broken | performance | camera-wrong | physics | text-render | composition | other` (`higgsfield-troubleshoot` § Vision-Grounded Diagnosis).
- **Escala o diagnóstico:** a mesma categoria em 2 takes significa reescrever o prompt (regra 25). Na 3ª reprovação de frame, descarta (ata D3). Com 4 tentativas ou 160 créditos na ideia, a ideia é descartada.
- **Calibração:** nas 2 primeiras semanas de cada personagem, o Caio confirma o veredito. Registre a concordância por categoria e só confie no revisor sem confirmação quando a categoria passar de 85% de concordância em ≥20 casos.

---

## F) Roteamento de modelos

| Trabalho | Modelo | Configuração | Por quê |
|---|---|---|---|
| Ficha, storyboard, frames A e B | **GPT Image 2.5** (API OpenAI `images.edit` com refs; ou `gpt_image_2_5` no Higgsfield) | storyboard `medium`; ficha e frames `high`; variant `sunburst` em edição | Layout por regiões e edição com refs. Rosto realista tende a plástico, por isso use linguagem de foto de celular e não "photorealistic". |
| Clipe próprio (assinatura + gag), 8–12 s | **Seedance 2.5** `omni_reference` | 720p, 9:16, `generate_audio: false`, start e end frame | Padrão oficial para vídeo sério. Único com start e end frame mais refs múltiplas até 30 s. O 1080p ainda não foi avaliado em campo. |
| Draft de estrutura (template novo) | Seedance 2.5 em 480p (ou Seedance 2.0 `fast` 480p) | mesmo prompt | Valida cortes, bloqueio, contagem e figurantes. **Não** valida a performance: sem seed, o 720p é outro sorteio. |
| Entrega que precisa de 4K ou do parâmetro `genre` | Seedance 2.0 `std` | 4–15 s | O 2.5 para em 1080p. No nosso caso, raramente: o upscale só entra nos vídeos que performaram (Topaz / `bytedance_video_upscale`). |
| Plano simples, um só plano de profundidade, câmera parada, custo baixo | **Kling 3.0** | `std`, 9:16, start e end frame, 3–15 s | Opção mais barata para cena simples sem movimento pesado. Bom fallback quando o Seedance insiste num defeito (troca de motor no 3º degrau do Retry Ladder). |
| Trend de dança com o nosso cenário | **Kling 3.0 Motion Control** | `background_source: input_image`, `std` para iterar, `pro` para entregar; 720p | Tem o seletor de cenário e prompt de cena. A duração é a da fonte. |
| Trend (padrão do pipeline; Kling MC fica como A/B) | **Genjutsu** `hf_mult_motion_control` | `image_references` + `video_references`, 720p | Transferência nativa do Higgsfield. Aceita prompt de cena (ambiente, câmera, visual) e sai em até 1080p (C5 e `videos-analisados.md` §3); padrão do pipeline para trend. Ainda não avaliado em campo. |
| Correção em uma camada | Seedance 2.5 `video_edit` | cobra a duração do vídeo-fonte | Mais barato que regerar quando a composição e o timing já estão bons |
| Emenda do gag depois do MC | Seedance 2.5 `omni_reference`, 4–5 s | `start_image` = último frame do MC | O MC não faz o gag. A emenda cruza o corte no meio do movimento. |

**Notas de custo** (são estimativas. Antes de gerar, confirme com `higgsfield generate cost <modelo> ...` ou com o estimate da API, `OF/troubleshooting.md` § Cost):
- **Seedance 2.5:** cerca de US$0,074/s, ou seja, ≈US$0,74 por clipe de 10 s (`research/apis-e-limites.md`, terceiros).
- **Kling 3.0:** cerca de US$0,112/s. **Kling MC:** std ≈US$0,063/s, pro ≈US$0,084/s (terceiros, citam desconto temporário).
- **`video_edit`:** cobra a duração inteira do vídeo-fonte.
- **GPT Image 2.5 em retrato:** centavos por imagem (≈US$0,01–0,05 entre medium e high, conforme o blog consultado).
- **Imagens de referência no edit:** somam tokens de entrada.
- **Regra de bolso:** um storyboard rejeitado custa menos de 1% de um take de vídeo. Por isso o storyboard vem primeiro e o revisor reprova frame antes de chegar ao vídeo.
- **Orçamento da ata:** teto de US$12/dia no Higgsfield; 4 tentativas ou 160 créditos por ideia; gerar em 720p; com 80% do orçamento do mês, corta 1080p e Genjutsu.

**Resolução e duração (resumo):**
- 480p só para validar a estrutura de um template novo; 720p para produção; upscale só nos vencedores.
- 10 s é o padrão, 8 s para gag de uma ação e 12 s quando a assinatura precisa de mais tempo.
- No MC e no v2v, a duração é a da fonte cortada. O mínimo do Seedance é 4 s.
