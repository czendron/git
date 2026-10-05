# Técnicas dos melhores criadores de vídeo com IA (out/2026)

Pesquisa feita em 2026-10-05 para a Usina de Virais (Seedance 2.5, Genjutsu e Kling Motion Control via Higgsfield, GPT Image 2.5 para keyframes, formato 9:16).

**Como esta pesquisa foi feita, e os limites dela.**
- O proxy bloqueou quase todo WebFetch e curl (seed.bytedance.com, kling.ai, higgsfield.ai, beehiiv, fal.ai, curiousrefuge.com). Só o guia de Veo 3.1 do Google Cloud abriu inteiro.
- O que veio de criadores e páginas oficiais chegou por **trechos de busca**, sem transcrição dos vídeos.
- O material mais profundo saiu de **repositórios públicos clonados** em `/tmp/research-repos/`. Alguns deles traduzem as regras oficiais da ByteDance e o pipeline aberto do filme *Hell Grind* da Higgsfield:
  - `OSideMedia/higgsfield-ai-prompt-skill`
  - `smixs/visual-skills`
  - `Emily2040/seedance-2.0`
  - `dexhunter/seedance2-skill`
  - `mj2760975907-ux/seedance-2-0-prompting-guide-prompts`
  - `aedev-tools/kling-3-prompting-skill`
  - `maciejdzierzek/kling-ai-prompt-generator`
  - `ZeroLu/awesome-seedance`
  - `seedanceprompts/seedance-prompts`
  - `snubroot/Veo-3-Meta-Framework`

**Legenda de confiança.**
- **[OFICIAL]**: documento do fornecedor, ou tradução fiel dele feita por um repositório que cita a fonte.
- **[CAMPO]**: prática relatada por criador ou estúdio com produção real.
- **[COMUNIDADE]**: guia de terceiro ou blog agregador.
- **⚠ NÃO VERIFICADO**: afirmação sem fonte primária, número sem metodologia, ou conflito entre fontes.

**Siglas das fontes usadas nas tags.**

| Sigla | Fonte |
|---|---|
| BD | ByteDance / Dreamina, guia oficial de prompt do Seedance 2.0/2.5 |
| HG | Higgsfield, *Hell Grind* (pipeline aberto do longa de 95 min) |
| OSM | repo OSideMedia/higgsfield-ai-prompt-skill (FAILURE-MODES, regras de motor) |
| EM | repo Emily2040/seedance-2.0 (directing engine, dicas de campo) |
| VS | repo smixs/visual-skills (referência de Seedance 2.5 tirada dos guias oficiais de 31/07/2026) |
| KL | Kling, guias oficiais (Motion Control, VIDEO 3.0) e resumos deles |
| GV | Google, guia oficial de prompt do Veo 3.1 |
| TM | Theoretically Media (Tim Simmons) |
| CR | Curious Refuge |
| PJ | PJ Ace (Genre.ai) |
| TH | techhalla |
| DC | Dave Clark (Promise) |
| RF | Rory Flynn |
| MV | MattVidPro |
| JP | caso Jean Phil (personagem de IA viral) |
| GJ | Higgsfield Genjutsu |
| MJ | repo comunitário "Seedance 2.0 Master Prompting Guide" (baixa confiança) |

---

## 1. Fontes oficiais

### 1.1 ByteDance: guia de prompt do Seedance 2.0 e 2.5 [OFICIAL]

**URLs**
- https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5
- https://docs.byteplus.com/en/docs/ModelArk/2607689 (guia do 2.5)
- https://docs.byteplus.com/en/docs/modelark/2222480 (guia do 2.0)
- Tradução detalhada em `visual-skills/video/references/seedance-25.md`.

**Fórmula base**

```
<Subject> performs <primary action or event> in <scene and environment>.
The visuals feature <visual style>. Use <shot size, angle, movement or cuts>.
Audio includes <dialogue, ambience, sound effects, or music>.
```

Só o sujeito e o evento são obrigatórios.

**Fórmula macro para prompts longos:** `[declaração de referências] + [resumo de uma linha] + [roteiro por timeline] + [cauda global]`. A cauda global repete o que precisa valer o clipe inteiro e as proibições.

**Referências**
- Cada material recebe um papel. Exemplo: "@Image 1 defines <Character A>'s appearance and clothing. Do not use the image background."
- **Forma proibida pela própria ByteDance:** "@Images 1 through 4 define four characters". Ela nunca diz qual imagem é qual personagem.
- Repetir o @ do mesmo material ao longo do prompt aumenta a precisão.
- Faixas estáveis: 1 a 8 sujeitos em imagens; 1 a 5 sujeitos em vídeo ou áudio de referência, com 5 a 10 s por sujeito.

**Clipe de 30 s: estágios e estados finais**
- Uma mudança principal por estágio, sempre com o **estado final visível**.
- Janelas de tempo de **3 s ou mais**.
- Cada janela leva uma ação central e um movimento de câmera.
- Timestamps distribuem orçamento de tempo. Não são pontos de corte com precisão de frame.

**Sintaxe de áudio do 2.5**

| Marcador | Uso |
|---|---|
| `( )` | música |
| `< >` | efeito sonoro |
| `{ }` | fala |
| `【 】` | legenda ou título |

- Diálogo fora do chinês precisa de uma linha de idioma e sotaque antes.
- "Pure video, no subtitles, no background music" passou a funcionar de forma confiável no 2.5.

**Pessoa realista, fórmula anti "cara de IA"**
- Papel, pele/textura, 3 a 4 detalhes faciais, olhar, cabelo, roupa/tecido, corpo/humor.
- Sufixo obrigatório: **"retaining real fine pores and skin texture"**.
- Para uma transição emocional bastam 2 a 4 sinais observáveis.

**Edição e extensão**
- Na edição, o vídeo fonte é o **"sole editing master"**. O prompt traz o escopo da edição e uma lista longa do que manter.
- Fontes com até 20 s funcionam melhor.
- A extensão aceita de 4 a 30 s por passada, até 60 s no total.

**Primeiro e último frame**
- Uma frase de papel por imagem. Nunca "@Images 1 and 2 are first and last frames".
- As duas imagens precisam ter o mesmo aspect ratio. A saída trava no aspect ratio da primeira.

**Grade de storyboard**
- Até 15 painéis. Declarar a ordem de leitura e excluir o estilo da grade: "Do not use the grid's line-art style, text labels".
- Keyframes em imagens independentes alinham melhor que uma grade única.

**Transições:** incluir "prohibit rigid cutting, prohibit objects appearing out of thin air".

### 1.2 Kling: Motion Control 3.0 e VIDEO 3.0 [OFICIAL, mas lido por resumos de busca]

**URLs**
- https://kling.ai/quickstart/motion-control-user-guide
- https://kling.ai/quickstart/klingai-video-3-model-user-guide
- https://kling.ai/quickstart/klingai-video-3-omni-model-user-guide
- https://kling.ai/blog/ai-motion-transfer-video-tutorial

**Motion Control**
- Entra um vídeo de referência, que dá o movimento, e uma imagem de personagem, que dá a aparência.
- **O prompt não descreve o movimento.** Ele descreve luz, ambiente e fundo.
- "Bind Facial Element" aumenta a consistência do rosto.

**Orientação**
- *Matches Video* segue o corpo e a câmera do vídeo. É a escolha para dança e ação, e é o único modo com element binding.
- *Matches Image* mantém a pose e a orientação da imagem. Serve para planos guiados pela câmera.

**Enquadramento**
- O enquadramento da imagem precisa bater com o do vídeo. Não combinar retrato de busto com dança de corpo inteiro.
- Deixar espaço livre na imagem para o corpo se mover sem ser cortado.

**VIDEO 3.0**
- Multi-shot: até 6 planos em 15 s. O modo *Custom Multi-Shot* define cada plano com sujeito, ação, enquadramento e duração.
- Elements: várias imagens ou um vídeo como âncora de personagem, objeto ou cenário.
- Áudio nativo com plano e contraplano.

**Contexto de out/2026:** o Kling 4.0 foi anunciado em 27/09 (30 s, até 10 keyframes, 15 referências, 4K). A versão Flash já está liberada para assinantes Ultra. https://morphic.com/resources/models/kling-4

### 1.3 Google: guia oficial de prompt do Veo 3.1 [OFICIAL, lido na íntegra]

**URL:** https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1

- **Fórmula:** `[Cinematography] + [Subject] + [Action] + [Context] + [Style & Ambiance]`.
- **Áudio:** a fala vai entre aspas (`A woman says, "..."`). Efeitos levam o prefixo `SFX:` e o ambiente leva `Ambient noise:`.
- **Negativo:** descrever o que se quer ver ("a desolate landscape with no buildings or roads") funciona melhor que "no man-made structures".
- **Fluxos:**
  - First and Last Frame: os dois frames vêm do gerador de imagem e o prompt descreve a transição.
  - Ingredients to Video: imagens de personagem e cenário como referência.
  - Timestamp prompting: `[00:00-00:02] ...`.
- **Limites:** clipes de 4, 6 ou 8 s, 720p ou 1080p, 16:9 ou 9:16.

### 1.4 Higgsfield: *Hell Grind* e Genjutsu [OFICIAL e CAMPO]

**URLs**
- Anúncio da abertura do pipeline: https://x.com/higgsfield/status/2084702370764820572
- Filme: https://www.youtube.com/watch?v=t33k2tn4GpA
- Matéria: https://best.xiaohu.ai/en/article/higgsfield-hell-grind-opensource/
- Resumo técnico em `higgsfield-ai-prompt-skill/skills/higgsfield-seedance/HELL-GRIND.md`

**Números:** longa de 95 min feito em 14 dias por US$ 500 mil. Só os primeiros 25 min exigiram **mais de 16.000 clipes para 253 planos usados**.

**Regras centrais**
1. Primeiro os assets. Um asset é texto descritor mais imagem.
2. Descrever tudo, toda vez. O modelo não tem memória.
3. Mudar uma linha por iteração e registrar no log.
4. Dar menos liberdade ao modelo: um canto em vez da sala inteira, uma âncora, um mapa.
5. Se o plano não sai em 10 a 15 tentativas, simplificar o plano em vez de reescrever o prompt.

**Ficha de personagem em 3 painéis**
- Close do rosto em 3/4, corpo de frente **sem cabeça** e corpo de costas.
- Fundo cinza, luz plana, poros visíveis, sem retoque, sem grain.
- A cabeça sai do corpo de frente porque, nos planos abertos, o modelo pegava o rosto da figura pequena e borrada.

**Nunca rodar a imagem de identidade inteira duas vezes pelo modelo.** Mudanças pontuais (roupa, cicatriz) se fazem com máscara sobre o original. Depois de duas passadas o rosto fica simétrico e plástico.

**Bloco GEO SPATIAL LAYOUT**
- Uma planta da locação, sem personagens, colada igual em todos os planos da cena.
- Lados sempre descritos a partir da câmera (frame-left e frame-right).
- Posições em metros a partir de marcos fixos.
- Declarar o eixo de 180° que a câmera não cruza.

**Primeiro segundo sempre aberto e sem ação.** Isso fixa as posições. O truque do "hm": alguém diz uma palavra curta nesse segundo, o que ajuda o Seedance a tratar o plano aberto como um plano separado.

**Cabeçalho de contagem:** "EXACT 3 CHARACTERS — NO DUPLICATES". O modelo tende a clonar gente e móveis.

**Diálogo**
- Ordem: voz e emoção → fala entre aspas → ação física → reação facial.
- Quem não tem fala fica em silêncio. Riso escrito na ação é expressão facial, sem som.
- A voz de cada personagem fica travada no descritor: registro, ritmo, sotaque, maneira.

**Física, não adjetivo**
- Descrever músculo e respiração em vez de "triste".
- Piscadas faseadas: "one lazy blink → a quick DOUBLE-BLINK → one HARD reset-blink".
- Um micro-evento a cada 1 a 2 s.
- Mãos ocupadas. O ponto mais forte da cena é quando o personagem para o que estava fazendo.

**Música só na pós:** "SFX only. No music."

**Genjutsu**
- URLs: https://higgsfield.ai/genjutsu e https://higgsfield.ai/blog/higgsfield-genjutsu
- Faz transferência de movimento: um clipe de até 30 s mais 1 a 8 imagens do personagem.
- Faz também troca de objeto. Preserva timing, lip-sync e câmera.
- Dicas que circulam [COMUNIDADE]:
  - Tratar o clipe fonte como autoridade de coreografia, timing e câmera, e dizer isso antes de pedir a troca.
  - Trocar um elemento por vez.
  - Usar referências de frente, de corpo inteiro e com rosto nítido.
  - Marcar cada imagem com @nome.
  - Fonte: https://www.tryclout.ai/blog/higgsfield-genjutsu-guide

### 1.5 GPT Image 2.5 (lançado em 08/09/2026) [OFICIAL e COMUNIDADE]

**URLs**
- https://developers.openai.com/api/docs/guides/image-prompting
- https://www.cometapi.com/how-to-prompt-gpt-image-2-5-like-a-pro/

**O que melhorou:** textura de pele e tecido, e fidelidade à referência. Isso facilita séries com o mesmo personagem.

**Regra de ouro para editar:** "Change only X. Preserve [identity, pose, lighting, geometry, text, style]".

**Selfie e UGC [COMUNIDADE]**
- Pedir "a single unedited still frame from a vertical 9:16 iPhone front-camera video… Not a photoshoot, not a portrait".
- Funciona melhor que empilhar adjetivos de realismo.

---

## 2. Criadores

### 2.1 Theoretically Media (Tim Simmons) [CAMPO]

**URLs**
- Canal: https://theoreticallymedia.com/
- Playlist "Seedance 2.0 and 2.5 Masterclass": https://www.youtube.com/playlist?list=PLoknIOnpU4ocGZNW11oBsrfMVyJSUrPID
- Playlist Seedance 2.0: https://www.youtube.com/playlist?list=PLoknIOnpU4oesmnZXHZwQ8xvFYuT0mc05
- Guia escrito: https://theoreticallymedia.beehiiv.com/p/seedance-2-5-prompt-guide (bloqueado aqui, lido por trechos de busca)

**Vídeos**
- "Seedance 2.5 Masterclass & Early Review": https://www.youtube.com/watch?v=b5F81eip5BM
- "Seedance 2.5 Advice with Tim Simmons": https://www.youtube.com/watch?v=deQNOjnDcwY
- "Seedance 2.5 & The New Age of AI Video" (AI For Humans): https://www.youtube.com/watch?v=EA3PGSRotwc
- "The Best AI Short Film You'll See Today (Seedance 2.5)": https://www.youtube.com/watch?v=4wFBA9-KyzY

**O que ensina**
- No 2.5, as tags viraram **atribuições numeradas com papel declarado**.
- **Exclusões declaradas**: dizer o que não tirar de uma referência, como "not the background" ou "not the person's identity".
- **Prompt em sanduíche**:
  - Topo: a intenção.
  - Meio: timeline com um beat por estágio e estado final explícito.
  - Fim: as invariantes repetidas.
- No curta *Death Walks Into A Bar*: disciplina rígida de eixo de 180° e posições preservadas entre os cortes.

### 2.2 Curious Refuge (Caleb e Shelby Ward) [CAMPO e COMUNIDADE]

**URLs**
- Tutoriais: https://curiousrefuge.com/ai-tutorials
- Review do Kling 3.0 (nota 8.1/10): https://curiousrefuge.com/blog/kling-30-review
- Como gerar no Kling 3: https://curiousrefuge.com/blog/how-to-generate-ai-videos-using-kling-3
- Edição com Seedance 2.0 Omni: https://curiousrefuge.com/blog/how-to-edit-videos-using-seedance
- Seedance 2.0 em 4K: https://curiousrefuge.com/blog/how-to-use-seedance-2-4k

**O que ensina:** fluxo de curso que vai de roteiro a shot list, storyboard, geração, som e distribuição. No Seedance Omni, ser explícito sobre o que muda e sobre o que fica ("same scene, same pose, same lighting").

⚠ Não conseguimos o conteúdo dos vídeos em si.

### 2.3 PJ Ace (PJ Accetturo, Genre.ai) [CAMPO]

**URLs**
- Thread do comercial Kalshi: https://x.com/PJaccetturo/status/1932893260399456513 e https://x.com/PJaccetturo/status/1932893267668185525
- Newsletter: https://pjace.beehiiv.com/
- Fluxo descrito por terceiros: https://www.ability.ai/blog/ai-video-production-workflow e https://www.thedaringcreatives.com/creator-stories/pj-ace-nba-finals-ad/

**O que ensina**
- Roteiro escrito com Gemini ou ChatGPT. Depois o LLM converte cada plano num prompt de vídeo, **no máximo 5 prompts por vez** porque a qualidade cai acima disso.
- Cada prompt descreve a cena **como se o modelo não soubesse nada do plano anterior ou do seguinte**: cenário, personagem e tom repetidos sempre.
- Kalshi: cerca de **300 a 400 gerações para 15 clipes usados**, US$ 2 mil, 2 dias.
- Para trabalho profissional, "text-to-video é beco sem saída". O fluxo é:
  - Fotos de referência do local real.
  - Planos montados no Figma.
  - Personagens compostos em frames base com Nano Banana, ao longo de dezenas de iterações.
  - Animação com Veo 3.1, Seedance 2.0 ou Kling.
- Curadoria em grades 2x2 para ver volume. Quando aparece um plano "herói", ele vira mais de 40 variações para dar cobertura.

### 2.4 techhalla [CAMPO]

**URLs**
- Threads: https://threadreaderapp.com/user/techhalla
- Exemplos: https://x.com/techhalla/status/2100526482212712584 e https://x.com/techhalla/status/2078973992740757504

**O que ensina**
- Pares de prompts "GPT Image 2.5 + Seedance 2.5": primeiro o frame em imagem, depois a animação.
- Fluxo Nano Banana Pro → Seedance 2.0 no Magnific, geralmente com 15 s em 720p.
- Fluxo Kling 3.0 + Nano Banana Pro para lutas.
- Grade de storyboard como frame de partida.

⚠ Os prompts exatos ficam nas threads, que não conseguimos abrir.

### 2.5 Dave Clark (Promise Studios) [CAMPO]

**URLs**
- https://nofilmschool.com/dave-clark-interview-adobe-max
- https://www.forbes.com/sites/maureenkerr/2026/07/24/dave-clarks-ai-studio-promise-aims-for-films-hollywood-can-release/

**O que ensina**
- Produção híbrida: atores em fundo azul combinados com vários modelos de IA, escolhidos por plano.
- Fluxo recente: Seedance 2.0 dentro do Runway, edição no DaVinci Resolve, **upscale de vídeo no Magnific** e música no Suno.
- Registro de prompts, configurações e aprovações (o software Muse).

### 2.6 Rory Flynn [CAMPO]

**URLs**
- https://x.com/Ror_Fly
- Diagram-to-video com Veo 3: https://x.com/Ror_Fly/status/1950352402416115788

**O que ensina:** sequenciar o movimento em fases, como "Motion 1: camera pulling back… Motion 2: camera pushes in…". Também desenhar diagramas e setas sobre o frame para guiar o movimento.

**Variante atual [COMUNIDADE]:** pintar o caminho da câmera numa imagem e passar para o Seedance (FLORA). O modelo segue a linha e apaga as marcas. https://mer.vin/2026/06/draw-camera-paths-on-images-flora-seedance-fpv-drone-motion-control/

### 2.7 MattVidPro [COMUNIDADE]

**Vídeo:** "Kling 3.0 vs Seedance 2.0 vs Veo 3.1 vs Sora 2: The Ultimate AI Video Comparison": https://www.youtube.com/watch?v=-MluR9dqt5w

**Valor para nós:** comparação lado a lado dos modelos, não técnica. O consenso dos comparativos:
- Seedance 2.5 vence em produto, texto e controle por referências.
- Kling 3.0 tem realismo de personagem comparável, custa menos e renderiza mais rápido.

### 2.8 Jean Phil (Jean Philanthrope): caso de personagem viral [CAMPO, set/2026]

**URLs**
- https://knowyourmeme.com/memes/jean-philanthrope-jean-phil
- https://www.dexerto.com/tiktok/who-is-jean-phil-ai-character-behind-multimillion-dollar-meme-coin-sparks-fake-persona-trend-3412528/
- Recriação: https://www.getstarrd.app/blog/how-to-make-an-ai-character-like-jean-phil

**A fórmula**
- Um visual reconhecível já na miniatura: terno marrom, chanel loiro, bigode enrolado.
- **Um único bit repetível**: shadowboxing, sem falar, em lugares absurdos.
- Rosto e roupa idênticos em todo vídeo. **Só a locação muda.**
- Primeiro post em 17/09/2026. Cerca de 145 mil seguidores no Instagram em 3 dias. Já tem copiadores, como "Archibald Brown".

**Recriação [COMUNIDADE, ⚠ não confirmado pelo autor]**
- Ficha de personagem feita no ChatGPT.
- Clipe de referência com o movimento.
- Seedance com o prompt "Replace the man in Video 1 with the character in Image 1. Keep the camera move, framing and timing from Video 1. Keep the character identical to Image 1."
- Movimento em velocidade média e sem giros rápidos.

### 2.9 Repositórios que funcionam como "criadores" (destilam produção real)

- **OSideMedia/higgsfield-ai-prompt-skill**: https://github.com/OSideMedia/higgsfield-ai-prompt-skill
  - Catálogo de falhas: action-reversal, multi-motion, walking, fps drift, filler babble.
  - Regras de Motion Control e template de comédia.
  - Separa com rigor o que é [OFICIAL], [CAMPO] e "OPEN" (ainda não medido).
- **Emily2040/seedance-2.0**: https://github.com/Emily2040/seedance-2.0
  - "Directing engine": uma intenção por plano, e toda escolha de câmera, luz e som serve a ela.
  - Configuração por tipo de cena (comédia, UGC, produto).
  - Anti-slop.
- **smixs/visual-skills**: https://github.com/smixs/visual-skills
  - Referência de Seedance 2.5 tirada dos guias oficiais, com exemplos literais.
  - Keyframes de animatic.
- **dexhunter/seedance2-skill**: https://github.com/dexhunter/seedance2-skill
  - Tabela de papéis com @ e padrões por capacidade: extensão, beat-matching, one-take.
- **aedev-tools/kling-3-prompting-skill**: https://github.com/aedev-tools/kling-3-prompting-skill
  - Fórmula do Kling, multi-shot, start e end frame.
  - Start igual ao end gera loop.

---

## 3. Técnicas que vamos adotar

### A. Identidade e consistência

1. **Assets antes de qualquer plano.** Cada personagem é um par: descritor em texto mais imagem aprovada. O par passa por teste de estresse (3 ou 4 gerações em ângulos e luzes diferentes) antes de entrar num roteiro. [HG]
2. **Ficha de 3 painéis "chata de propósito".**
   - Close do rosto em 3/4, corpo de frente sem cabeça e corpo de costas.
   - Fundo cinza, luz plana, poros visíveis.
   - O look cinematográfico vai na locação e no prompt, nunca na ficha. [HG]
   - ⚠ Há conflito interno da Higgsfield sobre pôr grain na ficha. Default: sem grain.
3. **A imagem de identidade nunca passa inteira duas vezes pelo modelo.** Troca de roupa ou detalhe: gerar a edição e aplicar com máscara sobre o original. [HG]
4. **Cada referência leva papel, exclusão e grau de fidelidade, uma linha por sujeito.** [BD][TM][OSM]

   ```
   @Image 1 defines Lia's face, hair and outfit. Do not use the image background.
   ```
5. **Poucas referências, todas consistentes.** Duas ou três imagens da mesma sessão e com a mesma luz rendem mais que seis variadas. [CR, via Medium e Kapwing]
   - ⚠ O número "−60% de drift" não foi verificado.
6. **Com imagem de primeiro frame (I2V), o prompt traz só movimento e câmera.** Redescrever o que já está na imagem cria duas fontes para o mesmo sujeito e gera drift. [OSM][KL]
7. **Prompts autossuficientes.** Nenhum prompt depende de "o plano anterior". Tudo que precisa bater entre dois planos (velocidade de câmera, luz, posição) entra como valor absoluto, igual nos dois prompts. [PJ][OSM]
8. **Fórmula de pessoa realista com sufixo de pele, e sem idade.** [BD][HG]
   - Usar papel, pele, 3 ou 4 detalhes faciais, olhar, cabelo, tecido, corpo.
   - Fechar com "retaining real fine pores and skin texture".
   - **Nunca escrever idade.** O filtro endurece quando lê algo que parece menor de idade.

### B. Keyframes, storyboard e estrutura

9. **Keyframes no GPT Image 2.5 e animação no Seedance 2.5 (`omni_reference`).** [BD][TH][GV]
   - Primeiro e último frame com o mesmo aspect ratio (9:16).
   - Uma frase de papel por frame:

   ```
   @Image 1 is the first frame… @Image 2 is the last frame… The video begins naturally from the first frame and reaches the last frame after one continuous action.
   ```
10. **Corrigir drift no keyframe, não re-rolando o vídeo.** Se a ficha ou o keyframe estão instáveis, o vídeo herda a instabilidade. [COMUNIDADE: oimi.ai, evolink]
11. **Grade de storyboard (2x2 ou 3x3) para planejar.** [BD][TH][VS]
    - Para animar, os painéis vão como **keyframes independentes**: "Use @Image 1 through @Image N as keyframes in this order".
    - Se a grade inteira for usada, declarar a ordem de leitura e excluir o estilo: "Do not use the grid's line-art style or text labels".
12. **Elemento que não está no keyframe precisa ser declarado como ausente.** Sem isso, o modelo inventa onde colocar. [OSM]

    ```
    The phone is not visible in image 1; it enters from below frame when she lifts her hand.
    ```
13. **Prompt em sanduíche para clipes de 10 a 30 s.** [TM][BD]
    - Logline no topo.
    - Estágios com **um evento e um estado final** cada, em janelas de 3 s ou mais.
    - Cauda global com invariantes e proibições.
14. **Abrir já no meio da ação** quando o plano é um evento ("he is ALREADY mid-swing"). Ação complexa no meio da timeline costuma travar. [HG]

### C. Movimento e câmera

15. **Um movimento de câmera dominante por plano, sempre com ponto final.** [OSM][EM][BD]
    - Exemplo: "slow push-in, ending on her hands around the cup".
    - Movimento composto se divide em fases com tempo, ou em dois planos.
16. **Movimento unidirecional.** Encadear 2 ou 3 ações no mesmo sentido para ocupar o clipe. Se a ação acaba cedo, o modelo preenche o resto **revertendo-a**. Ida e volta são dois planos. [OSM]
17. **Física em vez de velocidade e emoção.** [OSM][HG]
    - Trocar "fast" por "feet striking hard, arms pumping". "Fast" é a palavra que mais degrada.
    - Trocar "sad" por músculo e respiração.
    - Andar: "heel lands first, strict left-right alternation, one foot always on the ground".
18. **Micro-vida contra rosto congelado.** [HG]
    - Um micro-evento a cada 1 a 2 s: respiração, narina, sobrancelha.
    - Piscadas faseadas.
    - Imobilidade escrita como "held tension", nunca "nobody moves".
19. **Detalhe proporcional ao tamanho do plano.** Close aceita micro-gesto. Plano aberto pede arcos amplos. Misturar degrada o clipe. [OSM]
20. **Vocabulário de câmera que os modelos obedecem** [BD][KL][GV]:
    - push in / pull out, pan, tilt, tracking / follow, orbit, crane, dolly zoom, whip pan
    - handheld com balanço sutil, locked-off static, POV, low / high angle, macro
    - Para termos raros: termo + alvo + mudança visível + direção ou velocidade.

### D. Dança e motion control (Kling 3.0 MC / Genjutsu)

21. **Checklist do clipe de referência.** [KL][OSM][weshop]
    - Uma pessoa só, corpo inteiro visível na maior parte do tempo.
    - Câmera estável, **sem cortes**, sem oclusão.
    - Velocidade moderada. Borrão no clipe fonte vira falha na saída.
    - Duração de 3 a 10 s (máximo de 30 s).
22. **A imagem do personagem casa com o clipe.** [KL]
    - Mesmo enquadramento: corpo inteiro com corpo inteiro.
    - **Pose inicial igual ao primeiro frame da dança.**
    - Espaço livre para os braços.
    - Orientação *Matches Video* e Bind Facial Element ativado.
23. **O prompt do motion control descreve só o mundo** (luz, cenário, atmosfera), nunca o movimento. [KL][OSM]
24. **Se a saída vier mais curta que a fonte**, o movimento estava rápido ou complexo demais. Desacelerar ou recortar a fonte antes de gastar créditos. [OSM]
25. **Loops para TikTok.** Escolher uma dança que começa e termina na mesma pose e cortar o clipe para o primeiro e o último frame quase coincidirem. No Kling, start igual ao end gera loop. [AE][COMUNIDADE]
26. **Batida da música.** [OSM][COMUNIDADE: opus.pro]
    - Com `@Audio1`, dar um papel ao áudio ("cuts land on the beats of @Audio1") e descrever a sincronia em batidas, não em segundos.
    - Se a música entra só na pós, usar o truque da faixa inaudível: "dancing in time to the unheard 100 BPM beat", e gerar sem música.
27. **Formato Jean Phil para os nossos personagens.** [JP]
    - Um visual de miniatura, um bit repetível, mesma ficha sempre e só a locação muda.
    - Os clipes de referência vêm do Genjutsu, com o prompt "keep camera, framing and timing from Video 1".

### E. Comédia, selfie e realismo

28. **Comédia deadpan.** [EM][OSM]
    - Plano travado e simétrico, geografia limpa.
    - **Segurar o quadro além do confortável.**
    - Um único beat absurdo, um SFX seco.
    - Sem zoom de reação, sem música, sem risada.
    - "A não-reação é a piada": "He doesn't turn around."
    - Diálogo curto, com pausa escrita em parênteses: "(short pause, slow blink)".
29. **Selfie POV realista.** [MJ][EM][COMUNIDADE: X/apob_ai]
    - Abrir com "A selfie video of…".
    - "holds the phone at arm's length, her arm visible in frame".
    - "1x front camera, no fisheye".
    - "slight handheld shake, auto-exposure shift, visible noise and compression".
    - Olhar alterna entre a câmera e a ação.
    - Toda troca de ângulo é motivada pelo personagem mexendo o celular.
    - **Abraçar os artefatos**: limpo demais parece falso.
30. **Trocar palavras vazias por fontes concretas.** "cinematic", "epic", "8k", "hyperrealistic" viram:
    - luz com fonte nomeada ("window light from frame-left, late afternoon")
    - lente e textura ("rain beading on the jacket"). [EM][AE][BD]

### F. Som, iteração e finalização

31. **Áudio do Seedance 2.5 com os marcadores** `( ) < > { } 【 】`. [BD][HG]
    - Proibições na cauda global: "Pure video, no subtitles, no background music".
    - A música vem na pós (trend ou Suno).
    - Diálogo com o idioma declarado antes: "Brazilian Portuguese, São Paulo accent".
32. **Diálogo sem enchimento.** [HG][OSM]
    - Quem não fala tem a boca descrita em repouso ("lips at rest, jaw closed, listening").
    - A fala precisa ocupar o plano. Fala muito curta num plano longo faz o modelo inventar murmúrios.
33. **Iteração cirúrgica com log.** [HG][EM]
    - Rascunho de 3 a 5 s em 480p antes do clipe longo.
    - Muda uma linha por tentativa e registra no log.
    - Depois de 10 a 15 tentativas, simplificar o plano.
    - Esperar volume: de 20 a 60 gerações por clipe bom em produção profissional. ⚠ Proporção inferida de PJ e Hell Grind.
34. **Editar ou estender em vez de regenerar.** [BD][EM]
    - `video_edit` com "sole editing master" e lista longa do que manter.
    - Extensão a partir do último frame.
    - Na continuação de diálogo, abrir a nova geração com a fala que fechou a anterior. [HG]
35. **Ordem de finalização: upscale → leve blur ou suavização → grain → color grade.** [TP][DC][COMUNIDADE: invideo]
    - Upscale com Topaz Starlight Precise 2.5/2.6 (feito para vídeo de IA) ou Magnific.
    - Grain leve, entre 2 e 3% ou overlay em baixa opacidade.
    - Interpolação de frames só para slow motion ou para corrigir frames duplicados.
    - Antes de tudo, checar frame a frame se há frames repetidos (o Seedance às vezes cai para 12–18 fps efetivos). [OSM]
36. **Som em camadas.** [EL]
    - Gerar SFX separados por material ("metal door slam", não "door") no ElevenLabs.
    - Montar ambiente com 2 ou 3 variações sobrepostas e defasadas.
    - Alternativa: Video-to-Sound para foley rápido.
37. **Volume e curadoria.** Ver muitas variações em grade. Quando um plano "herói" aparece, gerar dezenas de variações dele. O LLM escreve no máximo 5 prompts por lote. [PJ]

---

## 4. Mitos e armadilhas

| Mito ou armadilha | Realidade | Fonte |
|---|---|---|
| "Mais referências = mais consistência" | Referências inconsistentes competem entre si. Poucas e coerentes é melhor; acima de 8 sujeitos o resultado fica instável. | BD, CR |
| "@Images 1–4 são os 4 personagens" | Forma explicitamente errada pela ByteDance. Uma linha por sujeito. | BD |
| Escrever "1080p, 24fps, 16:9, 12s, 8K" no prompt | Resolução, duração e proporção são parâmetros do job. No prompt não configuram nada, e "8K" é ruído. | HG, VS |
| "cinematic, epic, hyperrealistic, masterpiece" | Puxam para uma distribuição genérica. Use luz com fonte, lente e textura. | EM, OSM |
| Redescrever a imagem de primeiro frame no prompt | Cria duas fontes para o mesmo sujeito e gera drift. Descreva só movimento e câmera. | OSM, KL |
| Descrever a dança no prompt do Motion Control | Briga com o vídeo de referência. Descreva só o mundo. | KL |
| Combinar movimentos de câmera ("dolly in while orbiting") | Gera tremor ou um meio-termo feio. Use um movimento por plano. | OSM, EM |
| Ação curta num clipe longo | O modelo reverte a ação para preencher o tempo. | OSM |
| "fast" para dar energia | É a palavra que mais degrada. Descreva a física. | OSM |
| Lutas e coreografias geradas em clipes separados e coladas | Cada clipe re-adivinha pose e tempo, e a sequência vira slideshow. Use um take mais longo, extensão ou referência de movimento. | OSM |
| Lista "negative: extra fingers, blur…" no corpo do prompt | No Seedance 2.0 isso foi lido como descrição positiva (empírico). No 2.5 as proibições específicas funcionam ("no subtitles, no BGM"). **Default: travas positivas mais 3 a 5 proibições específicas da cena.** ⚠ Conflito entre fontes. | OSM vs BD |
| "Use dois-pontos antes da fala para não gerar legenda" | Truque comunitário da era Veo 3/Seedance 2.0. ⚠ Não verificado. No 2.5 use `{fala}` com "no subtitles". | MJ |
| "(thats where the camera is)" melhora qualquer prompt | Truque viral do Veo 3 transplantado para o Seedance sem evidência. ⚠ Não verificado. | MJ |
| "Grain de 35mm reduz a detecção em 40%" | Número de blog sem metodologia. ⚠ Não verificado. Grain leve ajuda na percepção, mas não é bala de prata. | COMUNIDADE |
| "Motion intensity 2.0–3.0 para dança no Kling" | Contradiz a faixa 0.1–1.0 da mesma fonte. ⚠ Ignorar. | COMUNIDADE |
| Nome de diretor ("Wes Anderson style") | Funciona às vezes, mas a Higgsfield proíbe e há risco de IP. Descreva o observável: "centered symmetrical framing, pastel palette". | OSM |
| Escrever idade do personagem | Endurece o filtro de conteúdo. Use papel, roupa e ação. | HG |
| Timestamps acertam o frame | Só distribuem orçamento de tempo. Janelas menores que 3 s falham. | BD |
| Texto e logo legíveis gerados pelo vídeo | Sem garantia de precisão. Texto entra na pós. | BD |
| Re-rolar o vídeo indefinidamente | Depois de 10 a 15 tentativas o problema é o plano ou o keyframe, não a sorte. | HG |
| Prompt longo é sempre ruim | Há dois regimes. Plano curto: 50 a 80 palavras. Produção em blocos (Hell Grind): 3.000 a 4.000 palavras estruturadas. O que estraga é o **beat sobrecarregado**, não o tamanho. | OSM, HG |
| Ficha com figura de corpo inteiro pequena e rosto visível | Nos planos abertos o modelo pega o rosto borrado da figura pequena. Remova a cabeça do corpo inteiro. | HG |
| Gerar a trilha junto no Seedance | Atrapalha a edição e o corte na batida. Gere "SFX only" e ponha a música na pós. | HG |
| Ultra Long (180 s), Clay Renderer e edição por marcação no Higgsfield | Só existem no Dreamina. No Higgsfield o 2.5 vai de 4 a 30 s, até 1080p, com start e end só em `omni_reference`. | OSM |

---

## 5. Os 10 tutoriais do YouTube mais úteis (para analisar depois)

⚠ O canal de vários deles não foi confirmado. Os títulos vêm da busca.

| # | Título | URL | Por que analisar |
|---|---|---|---|
| 1 | Seedance 2.5 Masterclass & Early Review (Theoretically Media) | https://www.youtube.com/watch?v=b5F81eip5BM | Prompt sanduíche, exclusões, eixo de 180° num curta inteiro |
| 2 | Seedance 2.5 Crash Course (Global Settings & Storyboard Method) | https://www.youtube.com/watch?v=YgwNVKvgxkk | Configurações globais + storyboard |
| 3 | I Tested Seedance 2.5's 30-Second Mode — Here's the Prompt Structure | https://www.youtube.com/watch?v=i_IdTsGm-Bk | Estrutura de estágios no clipe de 30 s |
| 4 | Seedance 2.5 Advice with Tim Simmons | https://www.youtube.com/watch?v=deQNOjnDcwY | Conselhos práticos e erros comuns |
| 5 | Kling Motion Control 3.0 Full Tutorial — Create ANY Character in ANY Scene | https://www.youtube.com/watch?v=Utono2euM24 | Passo a passo de motion control |
| 6 | Kling 3.0 Motion Control Deep Dive: Better Than 2.6 & Dream Actor M2? | https://www.youtube.com/watch?v=DvXDQfoy7t4 | Testes lado a lado: o que transfere bem |
| 7 | Higgsfield Genjutsu Tutorial: Replace Characters And Swap Objects In Video | https://www.youtube.com/watch?v=cE0GAkSGiUU | O nosso motor de motion control |
| 8 | Consistent Character Sheets in Seedance 2.0 (Prompts Included) | https://www.youtube.com/watch?v=Fx5aNgLlYQ0 | Ficha de personagem para vídeo |
| 9 | Seedance 2.0 Tutorial: Perfect Character + Voice Consistency Workflow in Runway | https://www.youtube.com/watch?v=SWhYbZxRZCA | Consistência de rosto **e voz** |
| 10 | GPT Image 2 Character Sheets: Mastering Layouts & Consistency | https://www.youtube.com/watch?v=d7EOD-rdDNw | Fichas no gerador de imagem que usamos |

**Reserva**
- *Hell Grind* (filme): https://www.youtube.com/watch?v=t33k2tn4GpA
- Genjutsu Motion Transfer & Object Swap: https://www.youtube.com/watch?v=j1tFM5hnxfw
- Insane Seedance Prompts & Tricks: https://www.youtube.com/watch?v=MOkjfFIIb6E
- Complete Kling 3.0 Tutorial for Beginners: https://www.youtube.com/watch?v=hM57LIBamIg
- Comparativo do MattVidPro: https://www.youtube.com/watch?v=-MluR9dqt5w
- Kling Motion Control FREE / Realistic AI Dance: https://www.youtube.com/watch?v=ROCQLKFIHps

**Próximo passo sugerido:** rodar `video_analysis_create` do Higgsfield nos itens 1, 3, 5 e 7 para extrair transcrição e cenas, já que o proxy bloqueou a leitura direta.
