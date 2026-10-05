# Conselho, voto 02: Arquitetura de automação e pipelines

*Papel: orquestração, confiabilidade, observabilidade, idempotência e custo de manutenção para uma pessoa só. 05/10/2026.*

Princípio que guia tudo: **o Caio é o único operador.** Cada peça a mais é algo que quebra às 3h da manhã sem ninguém olhando. Então quero poucas peças, cada uma com um dono só, estado que dá para auditar e falhas que fazem barulho.

## 1. Onde a automação roda

**Recomendo Routines do Claude Code como relógio, com um núcleo Python determinístico que decide o que fazer.** O Claude só executa e registra.

```
Routine (cron, sessão nova)
  └─ python -m pipeline.tick plan        → lê fila (git) + decisões (banco do painel)
       devolve lista de AÇÕES idempotentes: [{key, tipo, página, item, params}]
  └─ Claude executa cada ação:
       - imagem: pipeline/images.py (OpenAI direto)  | fallback: Higgsfield gpt_image_2_5 (MCP)
       - vídeo:  Higgsfield generate_video (MCP), seedance_2_5 start+end frame
       - pacote: Google Drive (MCP)
  └─ python -m pipeline.tick record <key> <resultado.json>   → muda estado, grava job_id
  └─ git commit + push (branch usina-de-virais) + espelha resumo no banco do painel
```

- **Quem decide:** o `tick plan`, em código e com testes. O Claude não escolhe o próximo passo, só segue a lista. Isso tira o não-determinismo do LLM do caminho crítico.
- **Idempotência:** cada ação tem `key = item:etapa:tentativa`. O `job_id` do Higgsfield é gravado *antes* do polling. Se a sessão morrer, o próximo tick acha o `job_id` e só consulta o status, sem gerar de novo nem pagar duas vezes.
- **Estado:** a fonte da verdade é `data/queue/<página>/<id>.json` no git (já existe em `store.py`), que é versionado, tem diff e permite reverter. O banco do painel é **espelho + caixa de entrada**. Cada campo tem um escritor só: o painel escreve apenas a coleção `decisoes` (aprovar/rejeitar/nota), e a Routine escreve todo o resto. Sem escrita concorrente, não tem conflito.
- **Mídia:** as refs ficam no repo (PNGs pequenos). Frames e vídeos ficam no Higgsfield (ID + URL do CDN no JSON). O pacote final (MP4 + legenda + capa) vai para o **Drive**, numa pasta `Usina/<página>/<data>-<id>/`, porque URL de CDN pode expirar. MP4 nunca vai para o git.
- **Falhas:** no máximo 2 tentativas por etapa, com backoff. Moderação não ganha retry (o `images.py` já faz isso). Depois disso o item vai para `erro` com o motivo e aparece em vermelho no painel. **Trava de orçamento**: o `plan` não emite ação de vídeo se o gasto do dia passar do teto em `config/budget.yaml` ou se o `balance` do Higgsfield estiver abaixo do mínimo. **Lock**: um arquivo `data/lock.json` com validade de 90 min evita que duas Routines rodem ao mesmo tempo. **Dead-man switch**: cada run grava `data/runs/<ts>.json` e o painel fica vermelho se a última run tiver mais de 26 h.
- **Agenda:** 3 disparos por dia (horário de Brasília): 06:40 (gera frames do dia), 13:10 (gera vídeos aprovados e monta pacotes) e 22:50 (reconcilia, faz polling e cria o relatório). Cada run tem que ser curta, com teto de 15 ações.

**Alternativas:**

| | A. Routines + núcleo Python (recomendo) | B. GitHub Actions + APIs REST | C. n8n/Make |
|---|---|---|---|
| Chaves novas | só OPENAI (opcional) | OpenAI + **API Higgsfield separada** (cobrança à parte do plano do app) + R2/S3 | tudo isso + conta n8n |
| Determinismo | médio (núcleo em código) | alto | alto |
| Usa os créditos do plano Higgsfield | sim (MCP) | não | não |
| Manutenção solo | 1 repo | 1 repo + secrets + storage | 2 sistemas, lógica fora do git |
| Pronto hoje à noite | sim | não (rede e chaves) | não |

B é o destino natural se o volume passar de ~6 vídeos/dia ou se as Routines se mostrarem instáveis. Por isso o núcleo Python já nasce agnóstico: o `executor` é uma interface, com uma implementação MCP hoje e uma REST amanhã. C eu descarto: duplica a lógica, tira o estado do git e dá mais uma conta para manter.

## 2. Onde fica o controle

**O painel Usina (artifact no claude.ai), com uma aba nova: "Caixa de aprovação" + "Saúde".**
- A Caixa lista os itens em `frames` e em `video` de cada página, com link para abrir a mídia (o artifact não mostra mídia inline, então é preciso aceitar um clique a mais), e botões Aprovar / Refazer (com nota) / Descartar. O clique grava só em `decisoes`.
- A Saúde mostra a última run, os erros, o gasto do dia contra o teto, o saldo do Higgsfield e o buffer de vídeos prontos por página.
- O painel continua podendo gerar na mão (o MVP), mas o que for gerado ali entra na fila como item `manual` para não sumir do registro.

**Alternativas:** (a) **app na Vercel**: mostraria mídia inline, mas hoje está bloqueado, exige chaves REST, banco próprio e deploy, e é a maior carga de manutenção. Deixo para a fase B. (b) **Aprovação por Gmail ou Drive** (responder e-mail, mover arquivo de pasta): é frágil de interpretar, não tem trilha clara e esbarra na regra de não enviar e-mail por agente. O painel ganha porque já existe, já fala com o Higgsfield e com o banco, e não tem servidor.

## 3. Portões humanos

**Dois portões, ambos baratos para o Caio:**
1. **Frames** (antes do gasto caro). A imagem custa centavos e o vídeo custa dólares. Este é o portão que mais economiza.
2. **Vídeo final**, que vira o pacote. Como a postagem é manual, postar é o próprio "ok" final.

Rodam sem aprovação: radar, ideias, roteiro, legenda e frames. Itens sem decisão expiram em 72 h (viram `descartado`, sem custo). Em fase posterior, um "modo confiança" por página pula o portão 1 quando a taxa de aprovação de frames passar de 80% em 2 semanas. Isso fica numa flag em `page.yaml`, não no código.

## 4. Publicação

**Pacote pronto + o Caio posta.** São três motivos de engenharia: o áudio em alta não sai pela Graph API, o rótulo de IA não tem campo oficial confirmado, e o token de 60 dias seria mais uma credencial expirando em silêncio. O pacote no Drive leva `video.mp4` 1080x1920 (H.264, faststart), `legenda.txt`, `musica.txt` (sugestão + BPM), capa e um checklist (marcar "AI info", não reutilizar o arquivo em outra conta). O sistema calcula o hash do MP4 e **bloqueia** o mesmo arquivo em duas páginas. Fase 2: Graph API só para Trial Reels, depois de 1.000 seguidores.

## 5. Cadência e orçamento

Começar com **1/dia só no Gersinho**, com um **buffer-alvo de 3 pacotes prontos**: o `plan` só gera quando o buffer cai. Isso absorve falha e fim de semana sem estresse. Tetos em código: 2 frames por item, 2 tentativas de vídeo, 720p, e upscale só no aprovado. Com a estimativa da pesquisa (US$ 6-9 por Reel), uma página custa ~US$ 200-270/mês; três páginas, ~US$ 600-800. Teto diário inicial: US$ 12 de Higgsfield e US$ 2 de OpenAI.

## 6. Três páginas

Página = dado, não código. `page.yaml` com `status: rascunho` faz o `plan` ignorar a página por completo. Para ligar uma página nova, basta preencher o YAML, pôr as refs e mudar o status para `ativo`. O agendador faz round-robin entre as páginas ativas. Crossover é um item com `pages: [a, b]` que gera **arquivos diferentes** (ângulo de cada personagem) e é ligado pelo campo `crossover_id`. Hoje à noite deixo `pagina-2` e `pagina-3` com YAML esqueleto e validado.

## 7. Mix e trends

Duas faixas na fila: **do zero** (frame inicial + final → Seedance, ~70%), totalmente automática; e **motion** (Genjutsu, ~30%), que exige um MP4 de origem. Pescar e baixar vídeo de TikTok sozinho é frágil e cinza nos termos de uso, então essa faixa começa com o Caio colando o link ou ID no painel. Pescar trends: uma Routine semanal (seg 07:10) faz pesquisa web e grava no Radar, com fonte. Apify só se o radar manual se mostrar insuficiente.

## 8. Riscos (operacionais)

- **Falha silenciosa** → dead-man switch + aba Saúde.
- **Gasto descontrolado** → teto diário em código + checagem de `balance` antes de cada vídeo.
- **Mudança no schema das ferramentas MCP do Higgsfield** → as chamadas ficam isoladas num adaptador, mais um teste de fumaça barato (listar modelos, sem gerar) em cada run.
- **Link do CDN expirando** → cópia no Drive.
- **Dependência de um fornecedor** → interface de executor (MCP/REST) e de imagem (OpenAI/Higgsfield).
- **Meta** → o hash impede o mesmo arquivo em contas diferentes, e o checklist de rótulo de IA vai no pacote.
- **Trend morrer** → o formato é configuração por página, e trocar o "mundo" do personagem não exige mexer no pipeline.

## Hoje à noite (sem o Caio) vs. depende dele

**Construir hoje:** `pipeline/tick.py` (plan/record, lock, orçamento, expiração, hash), `executor` com adaptador MCP, fallback de imagem via Higgsfield, `config/budget.yaml`, esqueletos `pagina-2/3`, testes com `USINA_MOCK=1`, a aba Caixa/Saúde no painel, as 3 Routines diárias + a semanal (rodando em mock/dry-run até o primeiro ok dele) e um runbook de 1 página.

**Depende do Caio:** liberar `api.openai.com` + `OPENAI_API_KEY` no ambiente (sem isso, o fallback Higgsfield cobre); confirmar o teto de gasto; criar as contas do IG + rótulo "AI-generated profile"; criar a pasta no Drive (ou autorizar que eu crie); aprovar o primeiro run real; mais tarde, decidir sobre API REST do Higgsfield / Graph API.

## Meu voto em 5 linhas

1. Routines como relógio, núcleo Python determinístico como cérebro, e o Claude só executa ações idempotentes.
2. Git é a fonte da verdade; o banco do painel é espelho + caixa de decisões, com um escritor por campo.
3. Dois portões (frames e vídeo); o resto roda sozinho, com teto de gasto em código.
4. Pacote no Drive e o Caio posta; Graph API só depois, para Trial Reels.
5. Páginas como YAML; 2 e 3 já ligáveis, sem tocar no código.

## O que eu vetaria

- **Publicação automática no IG agora** (áudio, rótulo e token: três pontos de falha silenciosa num ativo que não se recupera).
- **n8n/Make** como segunda fonte de verdade.
- **Deixar o LLM decidir o fluxo** sem trava de orçamento e sem idempotência (risco de gerar vídeo em dobro em loop).
- **MP4 no git** ou **Drive como `video_url`**.
- **Gerar vídeo sem passar pelo portão de frames** antes de ter 2 semanas de taxa de aprovação medida.
