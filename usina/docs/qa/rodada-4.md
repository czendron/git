# QA da Usina de Virais: rodada 4 (05/10/2026)

**Escopo:** ensaiar o ciclo diário **inteiro**, exatamente como o `SKILL.md` manda, com um item de cada tipo:
- item próprio do Gersinho: ideia → roteiro → storyboard → frames → vídeo → revisão → pronto → pacote → postado;
- trend: roteiro → fonte (`motion-source`) → 4 opções do frame e `pick` → vídeo de motion control → gag → pacote;
- item da Marlene, que o portão de estreia (D6) tem de barrar.

**Ambiente:**
- Cópia isolada da `usina/` no scratchpad, com `USINA_MOCK=1`. A fila, o livro-caixa e o banco do painel reais não foram tocados.
- Higgsfield simulado: job ids, URLs `file://` e ids de upload falsos.
- Painel simulado: `decisoes` e `placar` no formato que o `index.html` grava, e um "asset store" numa pasta com ids de 32 hex.
- Vídeos sintéticos com ffmpeg (720x1280, 9:16): MC de 10 s, gag de 5 s, fonte de 9–10 s e um clipe com corte seco aos 5 s.
- Cada ciclo é um container novo: `out/` é apagado e a mídia volta pelo `media-restore`.

**Resultado:** a suíte passou de 90 para **104 testes, todos passando** (`.venv/bin/python -m pytest -q tests`, cerca de 3 min).
- Os 14 testes novos estão em `tests/test_qa_rodada4.py`.
- Um deles é o próprio ensaio automatizado (`test_e2e_daily_cycle_as_skill`, ~45 s): ciclos com container novo, painel, asset store e Higgsfield simulados. Os comandos rodam como o `plan` os emite.
- Ajustei 1 teste da rodada 3 (`test_gag_followup_flow_and_concat`): ele aprovava o vídeo antes do gag, que era o próprio bug E.

O `index.html` mudou (bug G e parte do E); o JS passa no `node --check` e no smoke do Chromium.

## Bugs (sintoma → causa → correção)

| # | Sintoma | Causa | Correção | Teste |
|---|---|---|---|---|
| A | O 2º `tick-start` da **mesma** sessão dizia "outro ciclo rodando", com o próprio dono, enquanto o `plan` dizia que o lock era meu. Uma Routine que dispara de novo na mesma conversa ficava presa por 2 h. | `lock.acquire` sem `--owner` inventava um dono novo em vez de ler `out/.tick-owner`. | O lock virou reentrante: reusa o dono da sessão e responde "renovado". | `test_tick_start_reentrant_same_session` |
| B | A triagem C6 se perdia. Exemplo: o take saiu com corte, a sessão tentou `--no-grid` e o job falhou no provedor; o plano voltou a pedir `video-request` puro e a grade voltou em silêncio. | `--no-grid`, `--repair` e `--no-sheet` só existiam na linha de comando. | Campo `video_opts` no item. O `video-request` grava as opções e o `video_submit` do plano mostra `triage`. `--grid` e `--reset-opts` desfazem; reescrever o roteiro zera. | `test_triage_opts_persist_after_failed_job` |
| C | Um "pausar" do painel ainda não marcado `applied` pausava de novo a cada `panel-apply`, mesmo depois de um `P resume`. O SKILL promete "rodar de novo não reaplica". O veto reaplicado dizia "chegou tarde (já em descartado)". | O kill switch não guardava os ids aplicados, e o veto não ia para `item.decisions`. | Ids do kill switch guardados em `health.json` (`applied_switches`) e o veto gravado no item. A mensagem agora é "já aplicado". | `test_killswitch_and_veto_idempotent` |
| D | `record-video --gag --refunded` respondia "registrado (gag)" e não lançava estorno. O crédito devolvido continuava comendo o teto de 160 da ideia e o teto do dia. | `_record_gag` ignorava `--refunded`. | Estorno também para o gag (`gag_history`), uma vez por job. O erro indica `--gag --failed` quando o job não está como falho. | `test_gag_refund` |
| E | **Ata D3:** na trend, o card "Vídeo final" aparecia na Caixa logo depois do QA do MC, antes de o gag existir. O Caio aprovava o MC, e o `package` emendava um gag que nenhum humano viu. | O `plan` punha `await_caio video` junto com as ações do gag, e o painel não sabia do gag. | Sem `await_caio` nem card enquanto o gag não se resolve (`gagPending` no export; o `index.html` esconde o card). `approve video` recusa, e aprovação do painel nesse intervalo vira obsoleta. Quando o gag passa ou é descartado, `qa_at` é renovado e o card volta: decisão anterior não vale. | `test_caio_approves_trend_only_after_gag`, smoke do painel |
| F | O MP4 do pacote só existia no container que o montou (`out/` não vai para o git). Com gag, a emenda MC + gag não existia em lugar nenhum, e o Caio não tinha de onde baixar o que vai postar. As 4 opções do frame da trend também se perdiam se a sessão caísse antes do `pick` (risco da rodada 3). | `_media_paths` não incluía o pacote nem as variações. | `media-status` passou a listar `package` (item `pronto`) e `var1`–`var4` (antes do pick). O `pick` reaproveita o asset da opção como `start`, sem subir de novo. | `test_media_status_archives_package_and_variants`, `test_package_archived_and_cover_is_gag_end` |
| F2 | Em `lost`, a fonte da trend sugeria `retry … frames --force`, que não traz a fonte de volta. | Um `fix` genérico por etapa. | `fix` por chave: fonte → `motion-source --file`; opções → `retry frames`; pacote → `package`; gag → `retry gag`. | idem |
| G | Não havia caminho `pronto → postado` fora do terminal: o painel não tinha "Postei" e o Placar não mudava o estado. A página parava sozinha no teto de 5 prontos (D5), e o D+10 da P2 nunca contava. | Faltava a ação no painel e no `panel-apply`. | Decisão `stage: "post", verdict: "posted"` (botão **Postei** na Fila, com link opcional). Número lançado no Placar para item `pronto` também marca `postado`. A Fila mostra **Baixar MP4** e a legenda. O plano lista `postar` em `waiting_caio`. | `test_posted_via_panel_and_via_placar`, smoke do painel |
| H | Na trend com gag, a `capa.jpg` era o último frame do MC, não o fim do gag (a piada). | A capa vinha de `video.last`. | Com emenda, a capa sai do último frame do MP4 final. | `test_package_archived_and_cover_is_gag_end` |
| I | `fetch-refs` falhava (403 no CDN) e saía com código 0. A dica mandava usar `--file`, que o comando não tinha. | Falta de tratamento de erro. | Sai com ERRO e aceita `--face`/`--silhouette` com arquivos locais. | `test_fetch_refs_fails_loudly_and_accepts_local_files` |
| J | A mensagem "não gera (…; 0/10 prontos antes do 1º post)" punha o estoque como motivo, mas o estoque só trava o 1º post. Parecia que faltava estoque para gerar o próprio estoque. | O `summary` misturava os checks de geração e de post. | `gen_summary` só com status, ficha e dias. | `test_launch_gate_message_lists_only_generation_blockers` |
| K | Vídeo reprovado com a ideia no teto: o plano mandava `retry` e só no plano seguinte dizia `discard`, gastando um passo. | O teto era checado só no estado `frames`. | `_redo_video` decide entre `retry` e `discard` na hora (4 tentativas ou 160 créditos). | `test_redo_video_at_credit_cap_goes_straight_to_discard` |
| L | Fonte registrada com `motion-source` fora do ciclo (pelo Caio, numa sessão avulsa) sumia com o container. O ciclo seguinte achava `lost`. | Ninguém arquivava a fonte nessa sessão. | `motion-source --file` imprime o passo de arquivar, e o SKILL diz o mesmo. O ensaio automatizado pegou isso. | `test_e2e_daily_cycle_as_skill` |

## Fricções (corrigidas no texto ou na saída)
- **`review_video` sem os cortes:** o SKILL dizia "veja os `cuts` no item" e a ação só trazia a folha. Agora `file` lista folha, folha do gag e último frame, a ação traz `cuts`, e o `how` avisa quando há corte. No ensaio, o clipe com corte aos 5 s foi detectado e reprovado.
- **SKILL × CLI:** o texto foi alinhado nos pontos abaixo. Preservei a edição do G13 feita por outro agente.
  - refs locais e `fetch-refs --face/--silhouette` (o fallback Higgsfield só com o interruptor ligado);
  - lock reentrante;
  - `fix` do `lost` por chave;
  - Postei e Placar no passo 1;
  - triagem gravada, estorno do gag e D3 com gag na trilha de trend;
  - pacote e opções no passo 3.1;
  - `postar` em `waiting_caio`.
- **Retry após reprovação:** o `retry` do vídeo agora traz `next` com a lembrança da triagem C6.

## Fricções que ficaram (sugestões)

| # | Fricção | Sugestão | Esforço |
|---|---|---|---|
| 1 | `rosto.png`/`silhueta.png` não estão no git e o CDN do Higgsfield dá 403 pelo proxy. Toda sessão nova começa sem refs, e o `image` pela OpenAI não roda. | Versionar as duas refs (são pequenas) ou arquivá-las como asset do painel e restaurar no passo 0.5. | P |
| 2 | Página nova: `allow_trend` é `false` até haver 3 roteiros próprios (com 0 roteiros, 1 trend dá 100%). E o `new_ideas` com `count: 3` só checa +1. | Aceitável pela D7. Se o Caio quiser uma trend na 1ª semana, avaliar o teto só a partir de N≥5. | P |
| 3 | O teto diário de US$ 12 (em UTC) não comporta, no mesmo dia, um item próprio com 3 tentativas mais uma trend com gag. No ensaio, o gag ficou `blocked` até o dia seguinte. | Correto pela ata. Vale mostrar no relatório "gag adiado por teto diário" e fazer o teto no fuso de Brasília (sugestão antiga). | P |
| 4 | O plano não limita as 12 ações por ciclo. Com a P2 aberta, o `new_ideas` pede 9 ideias de uma vez (estoque de estreia 10). | Pôr `count` no máximo 3 por ciclo no `new_ideas`. | P |
| 5 | O `_log_failure` escreve em `playbook/falhas.md`, pasta que outro agente edita à mão. Há risco de conflito de merge a cada ciclo. | Mover o livro gerado para `data/falhas.md` e fazer o `memory` ler os dois. | P |
| 6 | A folha do gag (`gag-vN-sheet.jpg`) não é asset: no card, o Caio vê o gag só pelo link `gagUrl`. | Arquivar a folha do gag e mostrá-la no card de vídeo da trend. | P |
| 7 | `save-script` e `package` não dizem o próximo passo ("rode `plan`"). | Imprimir a próxima ação, como `image` e `fetch-video` já fazem. | P |
| 8 | Os passos de git do SKILL (pull, push do lock, commit) não foram ensaiados: a cópia isolada não é um repositório. | Ensaiar num clone descartável com um remoto local (`git init --bare`). | M |

## Como o ensaio automatizado funciona
`Rehearsal` em `tests/test_qa_rodada4.py`. Antes do 1º ciclo, a fila recebe 3 posts antigos: com eles, a D7 permite a trend e a calibração D3 fica ligada. Cada ciclo segue o SKILL:
1. Container novo: `media-status` → `media-restore`, exigindo `lost` vazio.
2. `balance`, `tick-start` e `panel-apply` + `placar-import`.
3. `plan`, executando até 12 ações do jeito que vêm (`cmd`, `how`, `video-request` → uploads → `record-video`).
4. `media-status` → `panel-asset` (exigindo `upload` vazio), `panel-export` e `tick-end`.

Entre os ciclos, o "Caio" lê o export do painel:
- reprova o storyboard com motivo e aprova o resto;
- veta uma ideia;
- pausa e retoma pela aba Saúde;
- baixa o MP4 do pacote do asset store (o da trend tem 15 s: MC + gag);
- clica Postei na trend e lança números no Placar do item próprio.

O teste confere:
- as tentativas: storyboard 3, vídeo 3 (corte reprovado e job estornado) e gag 2;
- a triagem gravada;
- os 2 estornos (vídeo e gag);
- as falhas no livro;
- que a Marlene nunca gastou e segue barrada no D+2;
- lock e PAUSE limpos no fim.
