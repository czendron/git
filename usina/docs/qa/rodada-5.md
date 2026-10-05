# QA rodada 5 (05/10/2026)

Escopo: as fricções abertas da rodada 4 (itens 3, 4, 5 e 6) e as regras checáveis do playbook B4 no lint. Nada foi gerado: zero chamadas à OpenAI ou ao Higgsfield. Testes: **119 passando** (104 antes + 15 em `tests/test_qa_rodada5.py`). O `index.html` não mudou.

## O que mudou

| # | Mudança | Onde |
|---|---|---|
| 1 | **Limite de 12 ações por ciclo** no `plan`. As ações saem ordenadas por prioridade, e o corte começa pelo fim da lista:<br>1. `check_balance`;<br>2. buscar e revisar o que já foi pago (`video_poll`, `fetch-video`, `review_video`);<br>3. o que não gasta (revisão de imagem, retry, descarte, pacote);<br>4. imagem nova;<br>5. `video_submit`;<br>6. `write_script`;<br>7. `new_ideas`.<br>`blocked` é aviso e não ocupa vaga. O que fica de fora vai para `truncated` e para as `notes`. | `pipeline/tick.py` (`cap_actions`, `action_priority`) |
| 2 | **O livro de falhas do pipeline** agora é `data/falhas.jsonl`: append-only, um JSON por linha com `at`, `date`, `page`, `item`, `stage`, `category` (o último `[categoria]` das notas) e `notes`. O `.gitattributes` na raiz usa `merge=union`, então dois containers que acrescentam linhas não entram em conflito. O pipeline não escreve mais em `playbook/falhas.md`, que fica só para a curadoria. | `pipeline/__main__.py` (`_log_failure`), `.gitattributes` |
| 2a | `memory <página>` lê as falhas curadas do playbook (da página e gerais) e as últimas 15 da página no jsonl. Linha corrompida é pulada. | `cmd_memory`, `_failure_log` |
| 2b | Comando novo `falhas-digest [--page] [--since AAAA-MM-DD]`: markdown agrupado por categoria, com páginas, etapas, portões (G*) e as últimas 10 linhas de cada grupo, pronto para curar no playbook. | `cmd_falhas_digest` |
| 3 | **Folha do clipe do gag** (`gag-vN-sheet.jpg`) vira mídia `gag_clip_sheet`:<br>- aparece no `media-status` → `panel-asset` → `media-restore`;<br>- o `retry gag` e o `retry video` a limpam;<br>- o `lost` aponta para `fetch-video --gag`.<br>A folha `video-vN-gag.jpg` (chave `gag`) já era arquivada. | `_media_paths`, `MEDIA_KEYS`, `STALE_ASSETS`, `_lost_fix` |
| 4 | **Lint do B4** (vale para `en.stages` e para `gag_followup.en.stages`). Detalhes abaixo. | `pipeline/lint.py` (`lint_counterpart`) |
| 5 | **Folga de 20% no teto diário para o gag**: quando o MC do item já foi pago (créditos no livro-caixa), o gag pode passar até 20% do teto diário do Higgsfield (US$ 12 → 14,40). O teto do mês nunca estica. O plano marca `day_overflow: true`, e o `video-request --gag` aceita a mesma folga. Nota de implementação na ata (D5), sem mudar a decisão. | `pipeline/budget.py` (`GAG_DAY_OVERFLOW`, `gag_overflow`), `tick._gag_actions`, `_video_request_gag` |

### Regras do B4 no lint

| Regra | Nível | Como detecta |
|---|---|---|
| Contraparte atrás dele (B4.1) | erro | Qualquer um destes:<br>- `counterpart.position` com behind/atrás/in back of;<br>- `counterpart.facing` com "facing his back" ou "behind him";<br>- o `facing` dele com "back to the <contraparte>" ou "away from the <contraparte>".<br>Não conta "behind the counter/stall/glass…" (atrás de um móvel não é atrás dele). A saída é `"gag_requires": "behind"` no roteiro ou no `gag_followup`. |
| Mais de um contato ou golpe num clipe (B4.7) | erro | Verbos de contato (punch, jab, slap, push, grab, tap, lands on, stops against…) nos estágios com `counterpart`. "twice", "again" e "N times" contam em dobro. "On contact" (a reação) não conta. |
| Ele e a contraparte agem no mesmo estágio (B4.5) | erro | A contraparte é sujeito de uma oração com verbo de movimento ou contato, e ele é sujeito de outra oração com verbo que não é de pose (keeps, holds, stares, does not… são pose). |
| Contraparte sem tarefa no estágio em que não age (B4.6) | aviso | Estágio com `counterpart` em que ela não age e sem `counterpart.task`. Também avisa quando a contraparte some num estágio entre dois estágios em que aparece. |

O `counterpart.task` entra no prompt ("Meanwhile the boxer bounces on his toes…").

**Roteiros conferidos:** os 3 da fila (`data/queue/gersinho/`) e os 2 exemplos (`prompts/examples/`) passam sem erro nem aviso. O exemplo de contraparte do `prompts/script.md` (vendedor entrega e ele pega no mesmo estágio) violava o B4.5. Foi reescrito em dois tempos, e as regras novas foram listadas ali.

## Testes alterados
O destino das falhas mudou. `test_pipeline`, `test_qa_rodada1`, `test_qa_rodada3` e `test_qa_rodada4` agora leem `data/falhas.jsonl`. As contagens são feitas por linha, porque a categoria repete o texto das notas.

## Fricções que ficaram (sugestões)

| # | Fricção | Sugestão | Esforço |
|---|---|---|---|
| 1 | O painel ainda não mostra a folha do gag no card de vídeo. O asset existe (`assets.gag_clip_sheet` no export), mas o `index.html` não foi tocado. | Uma linha no `renderCaixa`: `img(a.gag_clip_sheet, "folha do gag")`. Depois, rodar `node --check` e o smoke. | P |
| 2 | O `new_ideas` ainda pede até 10 ideias de uma vez na estreia. Pelo limite, isso é uma ação só. | Limitar o `count` a 3 por ciclo (rodada 4, item 4). | P |
| 3 | O `data/ledger.jsonl` também é append-only e tem o mesmo risco de conflito no git entre containers. | `usina/data/ledger.jsonl merge=union` no `.gitattributes`. | P |
| 4 | O lint do B4 é heurístico, feito de verbos e sujeito da oração. Escrita fora do padrão da casa ("his glove is hit by…") escapa. | Manter o G13 do revisor de vídeo como rede. Ampliar as listas quando o digest mostrar um caso. | — |
| 5 | O teto diário segue em UTC (rodada 4, item 3). A folga resolve o gag, mas não o item próprio. | Teto no fuso de Brasília, se o Caio quiser. Isso é decisão da ata. | P |
| 6 | Os passos de git do SKILL seguem sem ensaio (rodada 4, item 8). | Clone descartável com um remoto `--bare`. | M |
