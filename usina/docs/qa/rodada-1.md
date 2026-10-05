# QA da Usina de Virais: rodada 1 (05/10/2026)

**Escopo:** pipeline Python (`pipeline/*.py`), prompts gerados contra o `playbook/seedance-master.md` (seções A, B, C e E), painel `index.html` e o fluxo diário do `SKILL.md`.
**Ambiente:** `USINA_MOCK=1`, sem rede paga, ffmpeg local e Playwright/Chromium para o painel. Não houve chamada a API paga nem publicação do artifact.
**Resultado:** 7 testes no início e **26 no fim, todos passando** (`.venv/bin/python -m pytest -q tests`). Os 19 testes novos estão em `tests/test_qa_rodada1.py`, um por bug corrigido.

## Como testei

1. Rodei a suíte existente: 7 de 7 passando.
2. Simulei a automação em sandboxes descartáveis (cópia de `pipeline/ pages/ prompts/ playbook/ budget.yaml`, refs falsas e `video_enabled: true`). Segui o SKILL passo a passo:
   - `new`, `save-script`, `image`, `review`, `approve` e `retry`;
   - `video-request`, `record-upload`, `record-video`, `fetch-video`, `package` e `posted`;
   - `panel-export` e `panel-apply`;
   - `pause` e `discard`.
   Em cada passo procurei estados que travam, re-execução, contagem dupla, caminhos e dados malformados.
3. Gerei os prompts de storyboard, frame A/B, vídeo e motion para os 3 roteiros da fila e para variações: 0 figurantes, câmera `tracking_side`, luz interna, sem `end_image` e com `--repair`. Comparei cada um com os templates C1–C6 e as regras 8, 10, 12, 13, 17, 19, 21 e 22.
4. No painel:
   - `node --check` no script;
   - smoke test no Chromium (Playwright), com um `window.claude.use("db")` falso alimentado pelo `out/panel/batch.json` real da CLI: Caixa, Fila, Saúde, Páginas, aprovar/recusar e teclado nas abas;
   - conferi a API contra `db.d.ts` (contrato 0.2.67): `onSnapshot`, `snap.exists` e `data()` estão corretos.

## Bugs encontrados e corrigidos

Severidade: **C** crítico (gasta dinheiro ou fura uma regra da ata), **A** alto (trava a fila ou gera dado errado), **M** médio, **B** baixo. As linhas citadas são do commit anterior (`110ed6b`).

| # | Sev. | Onde | Bug | Correção | Teste |
|---|---|---|---|---|---|
| 1 | C | `tick.py:93-95` | Com os frames **recusados pelo Caio**, o plano caía no `else` e mandava `video_submit`: o vídeo era pago em cima de frames reprovados (fura a D3). | Novo ramo `caio == "rejected"`: `retry frames` ou, na 3ª tentativa, `discard`. | `test_frames_rejected_by_caio_never_submits_video` |
| 2 | C | `__main__.py:337-351` | `record-video --job X` repetido somava tentativa e lançava o custo de novo. Com uma sessão re-executada, o livro-caixa dobrava e a ideia era descartada antes da hora. | Job já conhecido (atual ou no histórico) é ignorado. `--job` só vale no estado `frames`. | `test_record_video_same_job_counts_once` |
| 3 | C | `tick.py:103` | O teto de **160 créditos por ideia** (D5) não existia no código; só o de 4 tentativas. Detalhe: `item.cost` nunca era preenchido. | `budget.item_spend()` soma o livro-caixa da ideia. O plano descarta quando o gasto mais a próxima tentativa passa de 160. | `test_per_idea_credit_cap_discards` |
| 4 | C | `__main__.py:287` | `video-request` não checava `PAUSE`, `video_enabled` nem o teto. Quem rodasse fora do plano recebia o JSON pronto para gastar. | O comando agora checa as três travas e o estado `frames`. | `test_pause_blocks_video_request` |
| 5 | C | `media.py:131-136` | O pacote fazia remux com ffmpeg em todo vídeo compatível. Isso **descarta as caixas C2PA/JUMBF**, e a D8 proíbe remover C2PA. | Vídeo compatível é copiado byte a byte; só o incompatível é transcodificado. O CHECKLIST manda postar o MP4 como está. | `test_normalize_without_audio_and_c2pa_safe_copy` |
| 6 | A | `media.py:138` | Vídeo **sem áudio e fora do padrão** gerava `ffmpeg ... -i -f lavfi ...` (o `-i` ficava sem arquivo) e o `package` quebrava. É exatamente o caso do Seedance com `generate_audio: false` quando a resolução não é 9:16/h264. | Comando remontado com `-map 0:v:0 -map 1:a:0` para o silêncio. | idem |
| 7 | A | `tick.py:112` | Job do Higgsfield com falha (`failed`/`nsfw`) **travava o item para sempre** em `video_poll`, porque não havia comando para registrar a falha. | `record-video --failed "motivo"`: guarda o histórico, volta para `frames`, conta a tentativa, anota no livro de falhas e no livro-caixa. | `test_failed_job_does_not_get_stuck` |
| 8 | A | `__main__.py:186,383,422` | A fila guardava **caminhos absolutos** (`/home/user/...`). No repo clonado em outra máquina, o `frames` perdia o storyboard **em silêncio** (gerava sem o painel 1) e o `package` falhava. | `store.rel()` grava caminho relativo; `store.local()` resolve o relativo e remapeia o absoluto legado. Sem storyboard local, o frame A agora **recusa** com instrução (`--sem-storyboard` para seguir conscientemente). | `test_queue_paths_are_relative...`, `test_frames_refuse_when_storyboard_file_missing` |
| 9 | A | `__main__.py:553-578` | `panel-apply` com dados malformados dava traceback: `{"documents": [...]}`, item que não é objeto e `ref` nulo (`TypeError` em `"/" in None`). Faltava também idempotência: sem o `applied` marcado no painel, cada ciclo reaplicava a decisão. Pior: uma recusa **velha** reprovava a versão nova da etapa sem o Caio ver. | Aceita lista, `{documents/docs/items/rows/results}` e `{id: doc}`. Ids aplicados ficam em `item.decisions`. Decisão com `at` anterior ao `qa_at` atual é obsoleta. Devolve `applied_ids`, `obsolete_ids` e `invalid_ids`. | `test_panel_apply_is_robust_idempotent_and_skips_stale` |
| 10 | A | `__main__.py:209-228` | Fallback Higgsfield nos frames: (a) o pedido do frame B ia no **mesmo batch** do A, com o placeholder `"<job_id do frame start>"` como media; (b) cada `record-image` somava 1 tentativa, então start e end contavam 2 e a ideia era descartada na 2ª rodada; (c) o frame `end` de uma rodada antiga sobrevivia. | Dois passos: o 1º pede só o A; o plano pede o 2º (`image ... frames --provider higgsfield`) já com o id do A como image 1. A rodada conta uma vez, `record-image` é idempotente por job e os frames velhos são limpos. | `test_higgsfield_fallback_respects_switch_and_two_steps` |
| 11 | A | `__main__.py:159`, `budget.yaml` | `--provider higgsfield` funcionava com `image_fallback_allowed: false`, contra o interruptor do Caio ("use a API do ChatGPT pra imagens"). O SKILL mandava usar o fallback sem condição. | O provedor padrão vem de `switches.image_provider`; o fallback é recusado se não estiver liberado. SKILL ajustado. | idem |
| 12 | A | `__main__.py:521`, `index.html:690` | `panel-export` pulava os itens **descartados**: o painel guardava o estado antigo, e a Caixa podia mostrar para sempre um card de algo já descartado. | Exporta tudo (o painel já filtra por estado). Escreve também os lotes `batch-NN.json` de até 50. | `test_panel_export_keeps_discarded...` |
| 13 | A | `__main__.py` (assets) | Num `retry`, o asset da Caixa continuava apontando para a **imagem da versão anterior**: o Caio aprovaria a v1 achando que era a v2. | `_clear_assets` limpa as chaves da etapa ao gerar, refazer ou reescrever. | idem |
| 14 | A | `index.html:690` | Na Caixa, depois que a decisão era marcada `applied` e até o próximo `panel-export`, o card **voltava** (a fila ainda dizia `caio: pending`), e um 2º clique gerava decisão duplicada. | "Decidido" passou a ser: há decisão não aplicada, **ou** aplicada com `at ≥ qa_at` da revisão atual. | smoke test do painel |
| 15 | M | `review`, `image`, `retry`, `save-script`, `package`, `posted`, `fetch-video` | Nenhum comando checava o estado do item. Re-rodar `image storyboard` gerava e cobrava de novo; `review` era aceito num item sem imagem; `save-script` repetido regredia um item `pronto`; `package` reabria um `postado`; `package` saía sem a aprovação do Caio no vídeo (D3). | `_need_state()` por comando, com `--force` para o uso intencional. `package` exige `caio: approved`. A reescrita de roteiro zera portões, frames e vídeo. | `test_state_guards...`, `test_video_review_rerun...` |
| 16 | M | `__main__.py:242-255` | Re-rodar `review video` lançava `video_review` de novo no livro-caixa, distorcendo o aproveitamento das últimas 10, e duplicava a linha no `falhas.md`. | Só a 1ª revisão da versão conta. | `test_video_review_rerun_counts_once...` |
| 17 | M | `__main__.py:84` | `new` criava itens em página `rascunho` (D6) e duplicava ideias com o mesmo título. | Recusa os dois casos (com `--force` para quem precisar). | `test_new_refuses_draft_page_and_duplicate` |
| 18 | M | `lint.py` | Roteiro com tipo errado (`character_actions_count: "duas"`, beat como string) dava **traceback** em vez de erro de lint. JSON inválido no `save-script`/`lint` também. | `lint()` captura e devolve `roteiro malformado`; a CLI trata `JSONDecodeError`/`OSError`. | `test_lint_malformed...` |
| 19 | M | `prompts.py:77` | O lint aceita `static_high` e `tracking_side`, mas o prompt caía **calado** na câmera de passante. | Entradas novas em `CAMERA` (com ponto final do movimento, regra 21). | `test_camera_modes_accepted_by_lint_have_prompts` |
| 20 | M | `prompts.py:45,47` | A silhueta usada no PHYSICS do vídeo dizia "one **smooth** solid shape". A tabela D lista "smooth" entre as palavras lidas como velocidade (câmera lenta). | Trocado por "seamless". | `test_video_prompt_has_no_speed_words...` |
| 21 | M | `prompts.py:129` | O storyboard forçava "natural daylight", mesmo em cena interna (elevador). Isso briga com a luz do frame A. | Usa `en.lighting` do roteiro. | `test_prompts_with_zero_extras...` |
| 22 | M | `prompts.py:208` | `--repair` jogava o texto cru no topo, sem o esqueleto C6a (Keep / Change only / Protect). | Esqueleto C6a completo. | `test_video_prompt_has_no_speed_words_and_repair_skeleton` |
| 23 | B | `prompts.py` | Com `extras_count: 0`, os prompts diziam "exactly 0 passersby" e "Passersby continue..." (invoca gente, regra 22). Sem `end_image`, o Stage 4 citava "matches the end frame". O frame B deixava linha em branco e frases sem maiúscula ou ponto. | `crowd()` / "only person in the set"; frase do end frame removida quando não há `end_image`; `_sent()`. | idem |
| 24 | B | `prompts.py` frame A | O frame A não contava as mãos (tabela D, "membros extras"). | Inclui `en.hands`. | — |
| 25 | B | `index.html:776` | O seletor do Placar era recriado a cada snapshot da fila e **perdia a escolha** no meio do preenchimento. Os números aceitavam negativos, e retenção vazia aparecia como `undefined%`. | Preserva a seleção, valida (≥0; retenção ≤100) e mostra "—". | smoke |
| 26 | B | `index.html:742` | `esc(premise).slice(0,120)` cortava entidade HTML ao meio (`&am`). | Corta antes de escapar. | smoke |
| 27 | B | `index.html:345` | Erro de assinatura do banco ia só para o console: o painel ficava vazio, sem explicação. | Aviso `role="alert"` e bolinha do banco em vermelho. | smoke |
| 28 | B | `index.html` a11y | As abas não tinham `aria-controls`, `tabpanel` nem navegação por setas. "Refazer" sem motivo deixava o botão preso em "Escreva o motivo". | ARIA completo, setas/Home/End, foco e `aria-invalid` no campo do motivo. | smoke (`ArrowDown` → `t-fila`) |
| 29 | B | `__main__.py` CHECKLIST | Imprimia `None` sem `music`. Trazia só 1 sugestão de som (a D4 pede 3) e não lembrava do rótulo "AI-generated profile". | Até 3 sugestões (`trend_sound_hints`), padrões sem `None`, item do rótulo e "não reexportar". | parcial |
| 30 | B | `memory` | Quebrava se `location` fosse string. | Tratado. | — |

**SKILL.md** (`/.claude/skills/usina/SKILL.md`), quatro ajustes para acompanhar a CLI:
- `record-video --failed`;
- fallback condicionado ao interruptor;
- frames do fallback em 2 passos;
- lotes `batch-NN.json`.

## Revisão dos prompts contra o playbook (o que já estava certo)

- **C4, estrutura dos blocos:** a ordem é SCENE CONTEXT → ACTIVE REFERENCES → CAMERA (3º bloco, regra 21) → LOCATION MAP → ACTION → PERFORMANCE → PHYSICS → LIGHTING → POSITIVE LOCKS.
- **C4, references e ações:** `@Image 1` é o rosto, `@Image 2` a silhueta e `@Image 3` a grade, igual à ordem de `medias` no `video-request` (start, end, rosto, silhueta, grade). As ações usam `[Stage]` com estado final e "moments of ONE continuous shot" (regras 7 e 12).
- **Negações** só onde o padrão do modelo já é a falha (regra 22): sorriso, câmera lenta, corte, figurante olhando, texto.
- **Frame B** é edição do frame A, com image 1 = A, 2 = rosto e 3 = silhueta (C2). A ordem bate com `img_refs` no `cmd_image`.
- **Slow:** os únicos "slow" que sobram são "slow blink" e "no slow motion", ambos previstos pelo playbook.
- **Pendências** (não corrigidas, ver sugestões):
  - o `fov_deg` do roteiro é ignorado (o FOV vem do modo);
  - não existe `@Image 4` para a ficha de prop (B3);
  - o template C1 do playbook ainda diz "smooth" (inofensivo em imagem parada, mas convém alinhar).

## Riscos que ficaram (não são bug de código)

- **A mídia não sobrevive entre sessões.** `out/` está no `.gitignore`, e cada Routine pode rodar num container novo. Storyboard e frames gerados num ciclo não existem no seguinte. Agora o pipeline **falha alto** em vez de degradar calado, mas o fluxo diário vai tropeçar nisso (ver sugestão 1).
- **Teto de 160 créditos.** Com a estimativa de 6,5 créditos/s, um clipe de 10 s custa 65. O teto de 160 permite **só 2 vídeos por ideia**, não 4. O Caio precisa decidir se quer assim.
- **Fuso do dia.** O "dia" do teto diário é UTC (vira às 21h em Brasília).

## Sugestões priorizadas (não implementadas)

| # | Sugestão | Por quê | Esforço |
|---|---|---|---|
| 1 | **Persistir a mídia entre sessões.** Subir cada imagem ao Higgsfield (`media_upload`) logo depois de gerar e gravar o `higgsfield_id`; baixar de volta pela URL do CDN quando faltar o arquivo local. Alternativa: versionar só os PNGs aprovados (Git LFS). | Hoje o ciclo de amanhã não acha o storyboard de hoje; vídeo e frames dependem disso. | M (1 dia) |
| 2 | **Contador de erros seguidos e saldo mínimo no código** (`max_consecutive_errors: 3`, `min_higgsfield_credits: 300`). Comando `P error "<msg>"` e `P balance <n>`, com o plano pausando sozinho. | São regras da D5 que hoje dependem do LLM lembrar. | P (2–4 h) |
| 3 | **Estorno de job falho.** `record-video --failed --refunded` lança créditos negativos quando o Higgsfield devolve. | Sem isso, falha do provedor consome o teto da ideia e o diário. | P (1 h) |
| 4 | **Ler o Placar na CLI** (coleção `placar` → `data/placar.json`) e calcular o gatilho da D5: ≥4 aprovados no estoque e mediana >5k ou um Reel >50k, para subir o Gersinho a 2/dia. | O painel coleta os números, mas nada os usa. | M (meio dia) |
| 5 | **Usar `playbook/falhas.md` no gerador de prompt** (D9.6): mapear categoria → trecho de reforço (ex.: `blocking-broken` → reforço de orientação no Stage 2). | Hoje só o roteirista lê o livro de falhas. | M |
| 6 | **`fov_deg` do roteiro no prompt** (ou o lint exigir que bata com o modo) e **ficha de prop como `@Image 4`** (B3). | Fecha as duas lacunas do C4. | P |
| 7 | **Teto diário no fuso de Brasília** (`budget.yaml: tz: America/Sao_Paulo`). | O dia do Caio é BRT. | P |
| 8 | **`panel-export` incremental:** exportar só os docs alterados desde o último export (hash por doc) e gerar `if_version` a partir de uma leitura salva. | Menos escrita e menos conflito de versão no `ArtifactData batch`. | M |
| 9 | **Concordância Caio × revisor de IA por categoria** (E4), calculada pelas decisões aplicadas. Mostrar na aba Saúde e liberar o fim da calibração quando passar de 85% em ≥20 casos. | Hoje a calibração acaba por data (14 dias), não por dado. | M |
| 10 | **Radar:** a mesma trend nunca em 2 páginas na mesma semana, e o teto de 30% de trend por página (D7) checado no `new` (`--format trend --trend-id`). | Regra de originalidade do Risco. | P–M |
| 11 | **Painel:** paginar `decisoes` (o `limit(300)` corta o histórico com o tempo); botão "Desfazer decisão" enquanto `applied: false`; filtro por estado na Fila e ocultar descartados por padrão. | UX do Caio. | P |
| 12 | **Lock de execução** (`data/.lock` com TTL) para duas Routines não rodarem o mesmo tick ao mesmo tempo. | Re-run concorrente é a próxima fonte de gasto duplo. | P |
| 13 | **Teste ponta a ponta do painel no CI** (o smoke com Playwright desta rodada virando teste). | Hoje o painel só tem `node --check` nos testes. | P |
| 14 | **Alinhar o template C1 do playbook** ("smooth" → "seamless") e documentar no README da CLI os comandos novos (`--force`, `--failed`, `--sem-storyboard`). | Consistência. | P |
