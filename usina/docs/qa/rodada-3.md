# QA da Usina de Virais: rodada 3 (05/10/2026)

**Escopo:** fechar as divergências com a ata que a rodada 2 deixou abertas (tabela "Coerência", linhas 9 a 13) e a sugestão nº 1 (lock de execução).
- Lock de ciclo.
- Livro de falhas no roteirista (D9.6).
- Portão de estreia da P2/P3 (D6).
- Trend única por semana e teto de 30% (D7).
- Gag depois do motion control (playbook C5).
- 4 variações do frame da trend (C5).

**Ambiente:** `USINA_MOCK=1`, sem API paga, sem publicar o artifact. Não toquei em `vendor/` nem em `playbook/`, que outro agente edita.

**Resultado:** a suíte tinha 50 testes no início e terminou com **64, todos passando** (`.venv/bin/python -m pytest -q tests`).
- Os 14 testes novos estão em `tests/test_qa_rodada3.py`.
- Ajustei 1 teste antigo (`test_trend_motion_flow`): o plano agora pede `frames --variants 4`.

Houve um commit intermediário por item, já no `origin/usina-de-virais`.

## O que foi implementado

| # | Item | Como ficou | Testes |
|---|---|---|---|
| 1 | **Lock de ciclo** (sugestão 1 da rodada 2) | `tick-start [--owner]` grava `usina/.lock` (dono, pid, host, hora, TTL de 2 h) e `tick-end` libera. Lock de outro dono vivo: o `tick-start` recusa, o `plan` volta sem ações (`other_tick` e uma nota) e o `video-request` recusa. Lock com mais de 2 h é ignorado, com nota. O dono local fica em `out/.tick-owner`. O SKILL ganhou o passo 0.2: `git pull`, `tick-start` e push do lock (assim containers diferentes se enxergam), e `tick-end` no fechamento e na saída por PAUSE. | `test_tick_lock_blocks_second_cycle_and_expires`, `test_video_request_refuses_while_other_cycle_runs` |
| 2 | **D9.6, falhas no roteirista** | `memory <página>` imprime, além dos 20 roteiros, as últimas 15 falhas da página e as 15 gerais do `playbook/falhas.md`. Lê a tabela do `_log_failure` e também bullets livres: bullet que cita a página entra nela; que cita outra página fica de fora; o resto é geral. O `save-script` avisa `cenário repete` quando o lugar coincide com um dos últimos 20 itens da página. Compara o `location.place` em pt (ou o `en.location`, na trend) por sobreposição de palavras ≥ 60%. | `test_memory_shows_failure_book_for_page_and_general`, `test_save_script_warns_repeated_place` |
| 3 | **D6, portão de estreia** | Módulo `launch.py` e comando `launch-check <página>`, com os checks status, ficha, dias e estoque. Regras: (a) `rascunho` nunca gera; `image` e `video-request` recusam até com `--force`. (b) Página ativa só gera com face e silhouette com `higgsfield_id`. (c) P2 só no D+10 e P3 só no D+20 do Gersinho, contados do `launched_at` ou, sem ele, do 1º post; dá para sobrepor com `launch:` no page.yaml. (d) Antes do 1º post, exige 10 prontos. O `plan` põe tudo nas `notes` e não gera com o portão fechado. O `new` recusa, e o `posted` registra mas avisa (o post já aconteceu no app). O painel recebe `launch` em `paginas`. O código **nunca muda `status`**. | `test_draft_page_never_generates`, `test_launch_gate_ficha_days_and_stock` |
| 4 | **D7, trend** | O `save-script` dá **erro** quando o `trend.name` normalizado já está num item de outra página criado (ou postado) nos últimos 7 dias. A normalização tira acento, caixa, pontuação e parênteses: "Gang Gang (Chef Boy)" = "GANG gang!". Teto de 30% em 30 dias: o `new_ideas` traz `allow_trend` (falso se mais uma trend passaria do teto), o `plan` avisa quando a página já está acima e o `save-script` avisa. | `test_same_trend_never_on_two_pages_same_week`, `test_trend_cap_30pct_plan_warns_and_stops_suggesting` |
| 5 | **C5, gag depois do MC** | Campo opcional `gag_followup` no roteiro de trend: `{duration_s: 4–5, en: {stages: [2], end_change}}`, validado por `lint_gag`. Fluxo em `revisao`, depois do QA do clipe de dança: `video-request --gag` pede o upload do último frame (`record-upload <ref> last`) e devolve o pedido Seedance 2.5 (`start_image` = último frame do MC, rosto e silhueta, prompt `gag_prompt`). Depois: `record-video --gag --job/--url/--failed`, `fetch-video --gag`, `review <ref> gag`, `retry <ref> gag` e `skip-gag`. O plano encadeia tudo com as mesmas travas de gasto (saldo, teto do dia e do mês, 160 créditos por ideia). Reprovado 2 vezes, o gag cai sozinho. O `package` emenda MC + gag (`media.concat`): concat demuxer **sem reencode** quando codec, tamanho, fps e áudio batem; senão, reencoda no tamanho do MC. O pacote só sai com o gag aprovado, descartado ou com `--no-gag`. O exemplo `gersinho-trend-calcadao.json` ganhou um gag (gaivota pousando no topete) e o `prompts/script.md` documenta o campo. | `test_gag_lint`, `test_gag_followup_flow_and_concat`, `test_gag_dropped_after_two_fails_packages_mc_only`, `test_gag_mismatched_clip_is_reencoded` |
| 6 | **C5, 4 variações** | `image <ref> frames --variants 4` (só na trend). Pela OpenAI, é 1 chamada com `n=4`; se vierem menos, completa com chamadas avulsas. No mock, são 4 placeholders. No fallback Higgsfield, saem 4 requests e cada resultado se registra com `record-image <ref> frames var<n>`. As opções ficam em `item.variants`, e o revisor escolhe com `pick <ref> frames <n>`. `review frames pass` sem `pick` é recusado. As 4 contam como **uma** tentativa (3 por ideia) e entram no livro-caixa como 4 imagens. O plano já pede `--variants 4` para trend e manda `review_image` com `pick: true`. | `test_trend_frame_variants_and_pick`, `test_trend_variants_higgsfield_fallback` |

## Achados no caminho

| Sev. | Achado | Decisão |
|---|---|---|
| A | A D5 ("mais de 5 prontos param de gerar") e a D6 ("10 em estoque antes de estrear") se contradiziam: a P2 nunca chegaria a 10. | Antes do 1º post, o teto e o estoque-alvo da página passam a ser 10 (`min_stock`); ao chegar a 10, o gasto novo para até a estreia. Depois do 1º post, volta o teto de 5. |
| M | Ativar a página não bastava: sem trava, `image` e `video-request` geravam numa página com a ficha incompleta. | `_gen_gate` nos dois comandos. |
| M | Emendar MC + gag remuxa o arquivo, e o C2PA do provedor não sobrevive. A ata D8 proíbe remover metadados de IA. | A linha do CHECKLIST do pacote emendado torna **obrigatório** o rótulo "AI info". Vídeo sem gag continua byte a byte (`normalize_reels`). |
| B | O `playbook/seedance-master.md` (C5) ainda diz "Ainda manual: o pipeline gera só o clipe de motion control". | Não toquei no playbook (fica com o outro agente). A nota pode ser trocada por "`gag_followup` + `video-request --gag`". |

## Coerência ata × SKILL × CLI (atualização da tabela da rodada 2)

| # (rodada 2) | Divergência | Situação agora |
|---|---|---|
| 9 | C5: gag em 2º clipe Seedance | **Fechada** (item 5). |
| 10 | C5: 4 variações do frame da trend | **Fechada** (item 6). |
| 11 | D7: mesma trend em 2 páginas na semana | **Fechada** (item 4); o teto de 30% agora também corta a trend nova. |
| 12 | D6: P2 no D+10 com 10 em estoque | **Fechada** (item 3). |
| 13 | D9.6: o roteirista lê o `falhas.md` | **Fechada** para o roteirista (item 2). O gerador de prompt de imagem e vídeo ainda não lê o livro. |
| — | Rodar dois ciclos ao mesmo tempo | **Fechada** (item 1). |

A ata ganhou "Notas de implementação (QA rodada 3)", sem mudar decisões. O SKILL ganhou o passo 0.2 (lock) e foi atualizado em `write_script`, `new_ideas`, na trilha de trend (variações e gag) e na regra de páginas.

## Riscos que ficaram

- **Lock entre containers:** depende do `git push` logo depois do `tick-start`. Se duas sessões derem push no mesmo segundo, uma é recusada e segue o roteiro do SKILL (desfaz e tenta de novo). Se a sessão morre sem `tick-end`, o lock segura o próximo ciclo por até 2 h.
- **`n=4` na OpenAI:** o `images.edit` com `n` não foi exercitado contra a API real. A queda para chamadas avulsas está coberta pelo código, mas não por teste.
- **Variações fora do arquivo de mídia:** se a sessão cai entre o `image --variants` e o `pick`, as 4 opções se perdem e é preciso gerar de novo (custa centavos). Só a escolhida entra no arquivo de mídia.
- **Painel:** o `panel-export` já manda `gagUrl` (fila) e `launch` (páginas), mas o `index.html` ainda não mostra os dois. O Caio aprova o vídeo vendo só o clipe de MC.
- **Custo do gag:** a estimativa é de 6,5 créditos/s (Seedance 720p), cerca de 33 por gag de 5 s. Com o MC a 8 créditos/s, uma trend de 10 s com gag fica em ~113 dos 160. Cabe 1 retry do gag (~145). Um retry do MC (80 + 80 = 160) esgota o teto, e o plano então descarta o gag sozinho (`skip-gag`, teto da ideia).

## Sugestões (não implementadas)

| # | Sugestão | Esforço |
|---|---|---|
| 1 | Mostrar `gagUrl` e o `launch-check` no painel (Fila e Páginas). | P |
| 2 | `falhas.md` no gerador de prompt de vídeo: injetar as falhas da página como "Avoid:" no `video_prompt`/`gag_prompt`. | M |
| 3 | Créditos reais do job no `record-video` (sugestão 2 da rodada 2, ainda aberta). | P–M |
| 4 | Guardar as variações no arquivo de mídia até o `pick`, para sobreviver a uma sessão que cai. | P |
| 5 | Teto diário no fuso de Brasília e lembrete do Placar de 7 dias (sugestões 8 e 9 da rodada 2). | P |
