# QA da Usina de Virais: rodada 2 (05/10/2026)

**Escopo:**
- As duas frentes novas desde a rodada 1:
  - **arquivo de mídia** no asset store do painel (`media-status`, `media-restore`, `panel-asset`);
  - **trilha de trend / motion control** (`format: "trend"`, `lint_trend`, `motion-source`, `_video_request_trend`, roteamento no `tick.py`).
- As sugestões 2, 3 e 4 da rodada 1, agora implementadas:
  - erros seguidos e saldo mínimo de créditos;
  - estorno de job falho;
  - Placar com o gatilho de cadência da D5.
- A coerência entre a ata, o `SKILL.md`, a CLI e o painel.

**Ambiente:** `USINA_MOCK=1`, sem API paga, sem publicar o artifact e sem tocar em `vendor/`. Usei ffmpeg local e Chromium headless (Playwright em `/opt/node-tools`) para o painel.

**Resultado:** 28 testes no início e **50 no fim, todos passando** (`.venv/bin/python -m pytest -q tests`). Os 22 testes novos estão em `tests/test_qa_rodada2.py`. Um deles roda o painel de verdade no Chromium (`tests/panel_smoke.js`) e pula sozinho onde não há Playwright.

## Como testei

1. Rodei a suíte existente: 28 de 28 passando.
2. Montei sandboxes descartáveis (cópia de `pipeline/ pages/ prompts/ playbook/ budget.yaml`, refs falsas, `video_enabled: true`) e segui o SKILL passo a passo nas duas trilhas:
   - **trend:** `new` → `save-script` → `motion-source` com fonte boa, com corte, longa (25 s), só com `--hf-id`, e fonte nova com o item já em `frames` → `image frames` (OpenAI e fallback Higgsfield) → `record-image` → `video-request` → `record-video` → falha → estorno;
   - **mídia:** `image` → `media-status` → `panel-asset` → `retry` → apagar `out/` como numa sessão nova → `media-status` → `media-restore` com o arquivo certo, com a versão velha e com um HTML de erro.
3. Estados forçados direto no JSON da fila: mais de 5 prontos com um vídeo em polling; trend sem fonte há 8 dias; ledger com 82% do mês gasto; saldo de créditos desconhecido, velho e baixo.
4. Painel: `node --check` e smoke no Chromium com um `window.claude.use("db")` falso, alimentado pelo `out/panel/batch.json` real da CLI. Conferi os cards da Saúde, o prefill do Placar, o kill switch e o veto na Fila, e quais documentos o painel grava.

## Bugs encontrados e corrigidos

Severidade: **C** crítico (gasta dinheiro ou fura regra da ata), **A** alto (trava a fila ou gera dado errado), **M** médio, **B** baixo.

| # | Sev. | Onde | Bug | Correção | Teste |
|---|---|---|---|---|---|
| 1 | C | `tick.py`, `video-request` | A D5 manda cortar o Genjutsu acima de 80% do mês. O plano só anotava "sem Genjutsu" e mesmo assim mandava `video_submit` de trend, e o `video-request` gerava o pedido. | Trend acima de 80% vira `blocked` no plano e o `video-request` recusa. | `test_trend_blocked_above_80_pct_and_model_recorded` |
| 2 | C | `motion-source` | Aceitava fonte de até 30 s e copiava a duração para `duration_s`, fora dos 3–15 s do próprio `lint_trend`. Com 25 s, a estimativa era de 200 créditos, acima do teto de 160 por ideia: a ideia morria depois de pagar o frame, ou o job saía caro. | Recusa fora de 3–15 s (`--force` para uso consciente). | `test_motion_source_refuses_cuts_and_bad_duration` |
| 3 | C | `motion-source` | Fonte **com corte** gerava só um aviso, mas o C5 exige plano contínuo. O motion control com corte queima créditos. | Recusa (`--force` registra com aviso). | idem |
| 4 | A | `motion-source` | Registrar uma **fonte nova** tinha três problemas. (a) Mantinha o `source_hf_id` da fonte antiga, e o vídeo saía com a fonte velha e o frame novo. (b) Sobrescrevia `source.mp4` e `source-first.jpg` no mesmo caminho, então o arquivo de mídia achava que já estava salvo e a restauração trazia a fonte velha. (c) Com o item já em `frames`, os frames feitos sobre o 1º frame antigo continuavam valendo. | Arquivos versionados (`source-vN.mp4`, `source-vN-first.jpg`), id limpo e histórico guardado. Num item adiantado, só com `--force`: volta para `roteiro`, limpa frames e portões e zera as tentativas de frame. | `test_new_source_invalidates_frames_and_old_upload` |
| 5 | A | `_media_paths` | A fonte e o 1º frame da trend **não entravam no arquivo de mídia**. Na sessão seguinte, `image frames` quebrava ("trend sem o 1º frame") e o `video-request` não tinha a fonte para subir. | Chaves `source` e `source_first` no arquivo. | `test_trend_source_is_archived` |
| 6 | A | `media-status` | Se a sessão morria depois de gerar a v2 e antes de subi-la, o arquivo sumia e o asset guardado era o da v1. O item não aparecia nem em `upload` nem em `restore`: ficava preso com a mídia faltando, **em silêncio**. | Lista nova `lost`, com a versão arquivada e o comando para refazer. | `test_media_status_reports_lost_and_restore_refuses_old_version` |
| 7 | A | `media-restore` | Aceitava qualquer arquivo em qualquer chave. Restaurar o asset da v1 no caminho da v2 trocava a versão em silêncio (o Caio aprovaria uma imagem e o vídeo usaria outra). Também aceitava arquivo vazio ou o HTML de um download que deu erro. | Confere se a versão arquivada é a atual (`--force` para trocar de propósito), se o arquivo não está vazio e se a assinatura bate com PNG, JPG ou MP4. | idem e `test_media_restore_checks_file_type...` |
| 8 | M | `panel-asset` | Se a etapa fosse refeita entre o `media-status` e o upload, gravava o asset de uma versão no caminho de outra. Só reconhecia o id no formato `/_blob/<id>`; com outra URL, a mídia não era arquivada e ninguém avisava. | `--path` (o `media-status` imprime) confere a versão. O id vem de qualquer sequência de 32 hex na URL ou de `--asset-id`. Sem id, avisa que não arquivou. `media-status` avisa arquivo > 15 MB (limite do asset store). | idem |
| 9 | A | `image frames --provider higgsfield` (trend) | O prompt diz "Edit image 1" (o 1º frame da fonte), mas o pedido do fallback não incluía esse frame: a image 1 virava o rosto. | Exige o upload do 1º frame (`record-upload <ref> source_first`) e o coloca como image 1. | `test_trend_higgsfield_fallback_uses_source_first_frame_as_image_1` |
| 10 | A | `record-image` (trend) | Só aceitava `frames` vindo de `storyboard`, mas a trend vem de `roteiro`. O fallback de trend era impossível de registrar. | Trend aceita `roteiro`. | idem |
| 11 | M | `image --provider higgsfield` | O fallback não checava `PAUSE`, tetos nem saldo: imprimia o pedido pronto para gastar. | Passa por `can_spend_higgsfield`. | coberto pelos testes do fallback |
| 12 | M | `record-upload` | Aceitava qualquer chave. `source` criava um `frames["source"]` fantasma (que ia parar na lista da revisão), e `end` num roteiro sem frame B criava um `end_image` do nada. | Só `storyboard`, `start`, `end` (se o frame existe) e `source_first`. | `test_record_upload_rejects_phantom_keys` |
| 13 | M | `lint.py` | `lint()` chamava `lint_trend` **antes** do `try`. Por isso, roteiro de trend com tipo errado (`duration_s: "dez"`) dava traceback, e a docstring tinha virado código morto. Faltava validar `extras_count` e avisar de vento. | Despacho dentro do `try`; validações novas. | `test_trend_lint_malformed_and_zero_extras_prompt` |
| 14 | B | `prompts.motion_frame_prompt` | Com 0 figurantes, o prompt dizia "exactly 0 ordinary passersby". É a regressão do bug 23 da rodada 1: invoca gente. | `crowd()` / "only person". | idem |
| 15 | M | `record-video` | Job de trend era gravado com `model: seedance_2_5`. | `hf_mult_motion_control`. | `test_trend_blocked_above_80...` |
| 16 | M | `record-video --failed` | Rodar de novo (sessão re-executada) dava `ERRO`, que agora contaria como erro seguido. Não conferia o `--job`. | Idempotente ("falha já registrada"); `--job` diferente do atual é recusado. | `test_failed_is_idempotent_and_refund_frees_idea_cap` |
| 17 | C | `video-request` | As travas de 4 tentativas e 160 créditos por ideia só existiam no `plan`. Rodar `video-request` direto furava as duas. | O comando checa as duas. | `test_video_request_enforces_idea_caps` |
| 18 | A | `tick.py` (estoque) | Com 5 ou mais prontos, o `continue` pulava a página **inteira**: um vídeo já pago ficava sem `video_poll`, `fetch-video`, revisão e pacote. Além disso, a ata diz "mais de 5" e o código usava `>=`. | Corta só o gasto novo (`new_ideas`, imagem, `video_submit`); o resto segue. Usa `>`. | `test_unposted_cap_stops_spending_but_keeps_polling` |
| 19 | M | `tick.py` (trend sem fonte) | A trend esperando fonte ocupava para sempre uma vaga do estoque (3 itens) e travava a criação de ideias. | Descarta depois de 7 dias (D7: o radar só pega trend com menos de 7 dias). | `test_trend_without_source_waits_then_discards_after_7_days` |
| 20 | M | `needs_caio` | Sem `launched_at` no `page.yaml` (é o caso do Gersinho), a calibração de 2 semanas da D3 nunca acabava. | Usa o 1º post registrado. | `test_calibration_window_starts_at_first_post...` |
| 21 | M | `panel-apply` | Aplicava as decisões na ordem do arquivo. Com pausar e retomar no mesmo lote, o resultado dependia da ordem do export. | Ordena por `at`. | `test_panel_kill_switch_applies_in_order` |
| 22 | B | `STALE_ASSETS` | O `retry video` não limpava os assets `video` e `last`. | Incluídos. | — |

## Sugestões da rodada 1 implementadas

**2. Erros seguidos e saldo mínimo (D5) no código**
- **Erros seguidos:** `record-error "msg" [--ref]` grava em `data/health.json`. No `max_consecutive_errors` (3), o próprio código cria o `PAUSE`. Comandos de produção que dão certo zeram a sequência, e `resume` também. `panel-apply` e `panel-export` não zeram, porque rodam em todo ciclo.
- **Saldo:** `balance <créditos>` grava o saldo lido pela MCP. O saldo estimado é o último lido menos os créditos lançados depois.
  - Saldo desconhecido ou com mais de 24 h: o plano devolve `check_balance` e o `video-request` recusa.
  - Envio que deixaria o saldo abaixo de `min_higgsfield_credits` (300): `blocked`.
- **Consulta:** `health`.

**3. Estorno**
- `record-video --failed "motivo" --refunded` (ou depois: `record-video <ref> --refunded --job <id>`) lança um `video_refund` com os créditos e dólares negativos do envio. Vale uma vez por job e só para job registrado como falho.
- O teto de 160 por ideia e o teto diário voltam a ter folga. A **tentativa continua contando**: uma moderação que se repete não pode girar para sempre.

**4. Placar e gatilho de cadência (D5)**
- `placar-import out/panel/placar.json` aceita os mesmos formatos do `panel-apply` e grava `data/placar.json` (versionado). Um export velho não sobrescreve número mais novo.
- `cadence-check` avalia por página ativa:
  - estoque aprovado ≥ 4;
  - pelo menos 7 dias desde o `launched_at` ou o 1º post;
  - mediana > 5k ou um Reel > 50k, usando `views7` quando existe e `views` (24 h) quando não.
- Com o gatilho atingido, a sugestão aparece nas `notes` do plano e na aba Saúde. **Nada muda sozinho.**
- No painel, o Placar ganhou "Views 7 dias" e preenche o formulário com os números já lançados, para lançar o 7 d sem apagar o 24 h.

## Coerência ata × SKILL × CLI × painel

| # | Divergência | Situação |
|---|---|---|
| 1 | Ata D1 cita `tick.py plan` / `tick.py record`; a CLI real é `python -m pipeline plan` + `record-*`. | **Corrigida:** nota de implementação no fim da ata, sem mexer nas decisões. |
| 2 | D2: a aba Saúde deveria mostrar erros e ter kill switch. Não tinha nenhum dos dois. | **Corrigida:** os botões Pausar e Retomar viram decisões `stage: "usina"` aplicadas pelo `panel-apply`. O card "Paradas automáticas" mostra os erros, o saldo e a cadência. |
| 3 | D3: o Caio pode vetar ideias no painel. Não havia como. | **Corrigida:** botão "Vetar" na Fila (decisão `stage: "ideia"`). Descarta o item enquanto ele está em ideia, roteiro ou storyboard; depois disso o veto chega tarde e é ignorado. |
| 4 | D3: a calibração de 2 semanas dependia de um `launched_at` que ninguém preenche. | **Corrigida** (bug 20). |
| 5 | D5: avisos de 50% e 80%, corte do Genjutsu, saldo < 300, 3 erros, "mais de 5 prontos". | **Corrigidas** (bugs 1 e 18, sugestão 2). |
| 6 | D5: o gatilho de 2 posts/dia vem do "D7", mas o Placar só tinha views de 24 h. | **Corrigida:** campo `views7`. |
| 7 | SKILL: "3 erros seguidos: `P pause`" dependia do LLM lembrar; "se existir PAUSE, saia" vinha antes de aplicar o "retomar" do painel. | **Corrigida:** `record-error`, e o PAUSE é checado depois do passo 1. Passos novos: `balance`, `placar-import`, `check_balance`, `--refunded`, `lost` e `--path`. |
| 8 | Playbook C5: diz que o Kling MC é "o padrão" e, logo abaixo, que o Genjutsu é o padrão. O código usa o Genjutsu. | **Corrigida:** o Genjutsu é o padrão e o Kling fica como A/B. |
| 9 | Playbook C5: "o gag vem depois", num 2º clipe Seedance a partir do último frame do MC. O pipeline gera só o clipe de MC. | **Aberta** (sugestão 3). Anotado no playbook. |
| 10 | Playbook C5: "faça 4 variações e cure" o frame da trend. O código gera 1. | **Aberta** (sugestão 4). |
| 11 | D7: mix de 25% trend com teto de 30% por página. | **Parcial:** o `new_ideas` mostra a fatia de trend dos últimos 30 dias e avisa no teto. A regra "mesma trend em 2 páginas na mesma semana" continua aberta. |
| 12 | D6: P2 só no D+10, com 10 vídeos em estoque. | **Aberta:** nada impede mudar `status: ativo` antes. |
| 13 | D9.6: o gerador de prompt lê o `falhas.md`. | **Aberta** (sugestão 5 da rodada 1). |
| 14 | A etapa `fonte` da trend não aparecia no painel, só a contagem "esperando você". | **Corrigida:** a Saúde lista o que espera o Caio e marca "trend: falta o vídeo-fonte". |

## Riscos que ficaram

- **Custo do Genjutsu:** a estimativa é de 8 créditos/s (`budget.yaml`) e ainda não foi confirmada num job real. Com isso, um clipe de 10 s custa ~80 e o teto de 160 permite 2 tentativas por trend.
- **Detecção de estorno:** depende da sessão olhar `mcp__Higgsfield__transactions`. Sem o `--refunded`, o comportamento é o antigo (conservador: a falha consome o teto).
- **Saldo estimado:** gasto feito fora da usina (no app, no painel) não entra na estimativa. Por isso a leitura vale só 24 h.
- **Rodar duas vezes ao mesmo tempo:** continua sem lock (sugestão 1).

## Sugestões priorizadas (não implementadas)

| # | Sugestão | Por quê | Esforço |
|---|---|---|---|
| 1 | **Lock de execução** (`data/.lock` com TTL e id da sessão). | Duas Routines no mesmo tick ainda podem submeter o mesmo vídeo duas vezes antes do `record-video`. | P |
| 2 | **Créditos reais do job** no `record-video` (o `generate_video_batch` devolve o custo) e conferência do estorno via `transactions`, em vez de estimativa e flag manual. | Fecha o risco do saldo e do estorno. | P–M |
| 3 | **Gag pós-motion control** (C5): pedir um 2º clipe Seedance de 4–5 s com o último frame do MC como `start_image` (stages 3–4 do C4) e emendar com ffmpeg, num estado próprio (`video_gag`). | Hoje a trend sai só com a dança; a piada física da fórmula da casa (D6) fica de fora. | M |
| 4 | **4 variações do frame da trend** (C5) com escolha pelo revisor (`image ... frames --n 4` + `pick`). | Corrigir pose e enquadramento no frame custa centavos; no vídeo, custa créditos. | P |
| 5 | **Radar com `trend_id`:** a mesma trend nunca em 2 páginas na mesma semana; a D7 checada no `new --format trend`. | Regra de originalidade do Risco. | P |
| 6 | **Portão de estreia da P2/P3** (D6: D+10/D+20 e 10 vídeos em estoque) checado pelo `plan` quando uma página vira `ativo`. | Evita estrear sem estoque. | P |
| 7 | **`falhas.md` no gerador de prompt** (D9.6), continuação da sugestão 5 da rodada 1. | O livro de falhas ainda só serve ao roteirista. | M |
| 8 | **Lembrete do Placar 7 d:** card na Caixa quando um post completa 7 dias sem `views7`. | Sem o número de 7 dias, o gatilho usa o de 24 h, que subestima a tração. | P |
| 9 | **Teto diário no fuso de Brasília** (sugestão 7 da rodada 1). | O dia do Caio é BRT. | P |
| 10 | **Smoke do painel no CI:** `tests/panel_smoke.js` já roda local; falta instalar Playwright no setup da Routine. | Hoje ele pula onde não há Chromium. | P |
