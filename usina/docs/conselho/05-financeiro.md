# Conselho, cadeira 5: CFO e operações

*Premissas: crédito Higgsfield ≈ **US$0,05** (plano de US$49, conforme a pesquisa; confirmar no plano real do Caio). Câmbio de ~R$5,5/US$. Reel publicado de ~10 s. Aproveitamento de vídeo de 1 em 2. Claude via Routines e GitHub Actions ficam dentro do que já é pago, com custo marginal ≈ 0. Nenhuma API paga foi chamada.*

## 1. Custo por vídeo publicado

| Receita | Imagens | Vídeo (com descarte) | Créditos | US$ |
|---|---|---|---|---|
| **A. Do zero, Kling 3.0** (2×5 s) | 4 nano_banana_pro = 8 cr | 2 tentativas × 20 cr = 40 cr | **48** | **~2,40** |
| **B. Do zero, Seedance 2.5** (10 s, herói) | 8 cr | 2 × 65 cr = 130 cr | **138** | **~6,90** |
| **C. Motion control Kling** (10 s) ⚠️ | 2 frames = 4 cr | ~2 × 20 cr (estimado) = 40 cr | **~44** | **~2,20** |
| **C'. Motion control Genjutsu** (10 s, 720p) ⚠️ | 4 cr | 2 × US$1,6–8 | — | **3,4–16** |
| Imagens pela OpenAI, como alternativa | 3 medium + 1 high ≈ US$0,29 | — | — | +0,29 |

**Mix recomendado** (70% A, 15% B, 15% C) ≈ **60 cr ≈ US$3,00 por Reel**. O descarte dobra o custo de vídeo. Por isso, a melhor alavanca financeira é **aprovar o frame (2 cr) antes de gastar 20 a 65 cr de vídeo**.

⚠️ **Ponto a verificar:** a API pay-as-you-go cita Seedance a ~US$0,074/s (US$0,74 por 10 s), contra ~US$3,25 pelo app. Se esse preço se confirmar, a API sai cerca de 4× mais barata em volume. Vale um teste de US$10 quando o domínio for liberado.

## 2. Custo mensal (3 páginas, 30 dias, mix de US$3,00 + 15% de reserva para refs e retrabalho)

| Cenário | Vídeos/mês | Créditos | US$/mês | R$/mês |
|---|---|---|---|---|
| **Enxuto**: 4/semana por página | ~51 | ~3.500 | **~US$175** | ~R$960 |
| **Base**: 1/dia por página | 90 | ~6.200 | **~US$310** | ~R$1.700 |
| **Agressivo**: 2/dia por página | 180 | ~12.400 | **~US$620** | ~R$3.400 |
| **Recomendado no mês 1**: só Gersinho 1/dia + fichas P2/P3 | 30 + testes | ~2.400 | **~US$120** | ~R$660 |

Custos fixos: Graph API, GitHub Actions e painel saem por US$0. Não pague Ayrshare (US$299) nem n8n Cloud (€24).

## 3. Tempo do Caio por dia

| Atividade | Por vídeo | Enxuto (1,7/dia) | Base (3/dia) | Agressivo (6/dia) |
|---|---|---|---|---|
| Aprovar frames no painel | 1 min | 2 | 3 | 6 |
| Aprovar vídeo final e legenda | 2 min | 4 | 6 | 12 |
| Postar com áudio em alta (manual) | 5 min | 9 | 15 | 30 |
| Comentários e aquecimento | por página | 15 | 20 | 30 |
| **Total/dia** | | **~30 min** | **~45 min** | **~80 min** |
| Mais o lote semanal de ideias | | 20 min/sem | 30 min/sem | 45 min/sem |

Um produtor solo que já toca o PdG não sustenta 80 min/dia. O agressivo só vale com publicação automática e para uma única página vencedora.

## 4. Orçamento-teto e alarmes (o sistema para sozinho)

**Teto:** US$150 no mês 1 (~3.000 cr). Nos meses 2 e 3, até US$350, só se passar pelos portões. Acima de US$350, só quando a receita da Usina cobrir 50% do gasto.

| Alarme | Gatilho | Ação automática |
|---|---|---|
| Por vídeo | 4 tentativas de vídeo ou 160 cr na mesma ideia | Ideia vai para "descartada" e o sistema segue a fila |
| Diário por página | > 2× a média diária do cenário (base: 140 cr) | Pausa a página até o dia seguinte |
| Aproveitamento | < 30% nas últimas 10 gerações | **Para tudo** e avisa (algo quebrou: prompt, ref ou modelo) |
| Mensal 50% | 50% do teto | Notifica |
| Mensal 80% | 80% do teto | Corta Seedance e Genjutsu, só Kling, só ideias aprovadas |
| Mensal 100% | teto | **Hard stop**, nada gera sem o Caio subir o teto |
| Saldo mínimo | saldo Higgsfield < 300 cr | Hard stop (reserva para emergência e publi) |
| Estoque | > 5 vídeos prontos não postados por página | Para de gerar (a trend morre e o estoque vira prejuízo) |
| Erros | 3 falhas ou recusas seguidas | Pausa a Routine e registra no log |

Cada geração grava créditos antes e depois no banco (ledger). O painel mostra o custo por vídeo real versus o estimado.

## 5. Go/kill por página (relógio começa no 1º post)

| Marco | KILL / pivot | MANTER | ESCALAR |
|---|---|---|---|
| **D21** (~21 posts) | < 1.000 seguidores **e** mediana < 3k views **e** nenhum Reel > 50k → um pivô de 14 dias (visual/cenário); se falhar, mata | entre os dois | > 5.000 seguidores **ou** 1 Reel > 500k **ou** mediana > 20k, com envios/alcance > 1% → 2/dia |
| **D35** (fim do pivô) | Mesmos critérios de kill → **arquiva** | — | — |
| **D60** | Custo por seguidor > US$0,05 **e** zero propostas de publi → cai para 3/semana de manutenção | | Receita ≥ 30% do custo → libera o teto |
| Sempre | Tempo do Caio > 60 min/dia por 7 dias → corta a cadência da página mais fraca | | |

**Regra de entrada:** P2 só nasce quando Gersinho passar o D21 com "manter" ou melhor. P3 só nasce quando P2 fizer o mesmo. O código e os slots ficam prontos, mas sem gastar crédito.

## 6. Posição sobre as 8 decisões

1. **Onde roda:** Routines do Claude Code, porque já estão pagas e acessam o MCP do Higgsfield. GitHub Actions só para cron de publicação no futuro. n8n/Make é custo e manutenção extra.
2. **Controle:** painel Usina, que já existe e custa zero. Vercel não.
3. **Portões:** dois obrigatórios: **frame** (o portão financeiro) e **vídeo final**. Ideias em lote semanal com aprovação tácita em 24 h.
4. **Publicação:** pacote pronto e o Caio posta com áudio em alta (a API não dá música). Graph API só depois do D21 do Gersinho, para Reels com áudio nativo.
5. **Cadência e orçamento:** mês 1 com Gersinho 1/dia e teto de US$150. Escalar só por métrica e nunca passar de 3 páginas × 1/dia antes de haver receita.
6. **Estratégia:** lançamento escalonado. P2/P3 ficam como config e ficha (até US$15 cada em imagens e 2 testes), sem cadência.
7. **Mix:** 70% Kling do zero, 15% Seedance herói, 15% motion control, este só em trend com < 72 h. Pescar trends com fontes grátis (radar e análise manual), sem Apify no mês 1.
8. **Riscos:** o maior risco financeiro é gerar estoque para uma trend que morre. Daí o teto de estoque e o go/kill curto. Rótulo de IA ativado desde o dia 1.

## Meu voto em 5 linhas
1. Mês 1: só Gersinho, 1 Reel/dia, teto duro de US$150 (~3.000 cr).
2. Portão de frame obrigatório antes de qualquer crédito de vídeo; ledger de créditos por geração.
3. Kling como padrão (US$2,40/Reel); Seedance só no vídeo herói; motion control só em trend fresca.
4. P2 e P3 prontos no código, ativados só por gatilho de D21; go/kill em 21+14 dias.
5. Testar o preço da API Higgsfield: se for 4× mais barata, migrar o volume para ela.

## O que eu vetaria
- Lançar as 3 páginas em cadência cheia no mês 1 (~US$310/mês, ~45 min/dia) com receita de R$500/mês.
- Qualquer geração sem teto automático ou sem ledger. Routine que gasta dormindo precisa de hard stop.
- Estoque de mais de 5 vídeos por página, ou motion control de trend com mais de 72 h.
- Ayrshare (US$299/mês), n8n Cloud ou Apify antes de alguma página passar no D21.
- Seedance ou Genjutsu 1080p como padrão. Upscale só para vencedores.
- Meme coin ou token como monetização.
