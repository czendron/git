# QA rodada 6 (05/10/2026)

Escopo:
- ensaio dos passos de git do SKILL com um remoto `--bare` e dois clones (dois containers);
- tetos no fuso do Caio;
- limite de ideias novas por ciclo;
- comando `status --morning`.

Nada foi gerado: zero chamadas à OpenAI ou ao Higgsfield. Testes: **134 passando** (119 antes + 15 em `tests/test_qa_rodada6.py`). Os testes de git usam só repositórios locais. O `index.html` e o `playbook/` não mudaram.

## 1. Ensaio de git (remoto bare + clones A e B)

| Cenário | Resultado com o SKILL antigo | Agora |
|---|---|---|
| Lock no início (pull, `tick-start`, push) | **Falhou.** O passo 0 faz `cd usina`, e daí `git add usina/.lock` aponta para `usina/usina/.lock`. O lock nunca subia, e o outro container não o via. | `P tick-start --git` puxa, pega o lock, commita só o `.lock` e empurra. |
| 2º ciclo concorrente | Funcionou (com o caminho corrigido à mão): B puxou o lock de A e o `tick-start` recusou. | Igual, e B não empurra nada. |
| Corrida: alguém empurra entre o pull e o push do lock | A receita do SKILL funcionou com o caminho corrigido, mas eram 5 comandos à mão. | O comando desfaz só o commit do lock (`reset --keep`), puxa e tenta uma vez. Se quem empurrou foi outro ciclo, ele recusa. |
| Lock vencido (> 2 h) | Funcionou: B ignora e assume. | Igual, com aviso. |
| Push no fim do ciclo | **Falhou.** Não havia plano B: qualquer push no meio (outro agente, o Caio, um ciclo que assumiu o lock) deixava o commit preso no container. | `P tick-end --git` solta o lock, commita `usina/` e empurra. Se o push for recusado: `pull --no-rebase`, resolve e empurra de novo (até 3 vezes). |
| `ledger.jsonl` e `falhas.jsonl` com linhas nos dois clones | Funcionou: `merge=union` junta as linhas, em merge e em rebase. | Igual. O resolvedor também faz a união se o `.gitattributes` faltar. |
| Mesmo item da fila editado nos dois clones | **Parou** num rebase pela metade, com marcadores `<<<<<<<` no JSON. | Resolvido por regra (abaixo). A versão perdedora vai para `data/conflicts/`. |
| `.lock` apagado por A e renovado por B (A acabou depois que B assumiu) | Conflito modify/delete. | Fica o lock vivo de B, e A recebe o aviso "assumiu": não gaste mais. |

**Regras do resolvedor** (`pipeline/gitsync.py`; à mão: `git pull --no-rebase` + `P git-resolve`):
- **Item da fila:** vence a versão com mais `job_id`/`hf_job`. No empate, a mais avançada na esteira; depois, a de `updated_at` mais recente. Se a perdedora tiver um job que a vencedora não tem, o aviso manda conferir no Higgsfield antes de pagar de novo.
- **`data/health.json`:** fica o saldo mais recente, os erros dos dois lados são unidos e vale a maior sequência de erros.
- **Qualquer outro arquivo** (página, prompt, código): sem regra. O merge é abortado, e o commit do ciclo sobe para o ramo `usina-conflito-<data>` do remoto. Nada vai para `usina-de-virais`. O operador reporta e não resolve à mão.

**Outro achado:** `pages/*/refs/*.png` não estava no `.gitignore`. O `git add -A usina` do fim do ciclo subiria o rosto e a silhueta, que o SKILL diz que ficam fora do git. Agora `pages/*/refs/` e `*.tmp` estão no `.gitignore` da usina.

## 2. Tetos no fuso do Caio
- `budget.yaml`: `timezone: Australia/Sydney` (padrão, via `zoneinfo`; o SKILL instala `tzdata` como rede).
- O teto diário (US$ 12 e US$ 2) e o do mês viram à meia-noite local. Exemplo: 00:10 do dia 7 em Sydney ainda é dia 6 em UTC, e o teto já zerou.
- Um fuso inválido cai em Sydney, nunca em UTC calado.
- A data das falhas no jsonl, o `ledger` e o "1º post em" do `launch-check` também passaram para o fuso local.

## 3. Ideias novas por ciclo
- O `new_ideas` pede no máximo **3 por página por ciclo**.
- O limite é configurável: `new_ideas_per_cycle` no `budget.yaml`, e o do `page.yaml` vale por cima.
- A ação traz `stock_missing` (quanto falta para o estoque) e as `notes` avisam quando o resto fica para os próximos ciclos.
- A estreia da P2/P3, que pedia 10 de uma vez, agora leva 4 ciclos.

## 4. `status --morning`
Resumo em PT-BR, com até 25 linhas, em quatro blocos:
- **Esperando você:** com o nome do painel. Caixa › Storyboard / Primeiro e último frame / Vídeo final; Fila › Baixar MP4 e Postei; Saúde › vídeo-fonte da trend.
- **Últimas 24 h:** o que andou na esteira, o gasto por provedor e o teto do dia local e do mês.
- **Bloqueios:** PAUSE, OPENAI_API_KEY, `video_enabled: false`, refs locais faltando, saldo baixo, erros seguidos, outro ciclo.
- **Portão de estreia por página:** para página em rascunho, o que ainda faltaria ao ativar.

A espera aparece mesmo com PAUSE (o `plan` sai cedo e não listava nada). O `panel-export` passou a usar a mesma lista, e a Saúde não mostra mais "nada esperando" durante a pausa. O relatório final do SKILL parte desse texto.

## Fricções que ficaram

| # | Fricção | Sugestão |
|---|---|---|
| 1 | Clock do container: o lock compara horários de máquinas diferentes. Uma diferença de minutos não importa com o TTL de 2 h, mas uma de horas importaria. | Se aparecer, gravar a hora do commit do lock (`git log`) em vez de `time.time()`. |
| 2 | O ramo `usina-conflito-*` não aparece no painel. | Uma linha na Saúde quando existir (exige mexer no `index.html`). |
| 3 | O `tick-end --git` commita tudo de `usina/`, inclusive edições de outro agente na mesma árvore. Containers de Routine são isolados, mas uma sessão compartilhada não é. | Rodar o ciclo sempre num container próprio, como já fazem as Routines. |
| 4 | O `new_ideas` limita o plano, não o comando `new`. | Basta o plano; o `new` à mão é do Caio. |
