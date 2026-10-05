# Ata do conselho: Usina de Virais (05/10/2026)

**Presentes:** Crescimento, Automação, Criativo, Risco e Financeiro (pareceres completos em `docs/conselho/`). Moderação e desempate: Claude (sessão principal).
**Pauta:** como rodar 3 páginas de personagens de IA no estilo Jean Phil, com produção o mais automática possível.
**Contexto novo (mesmo dia):** o Caio reprovou a qualidade dos vídeos de teste ("sem sentido"). Por isso a ata inclui uma decisão de qualidade (D9).

---

## Decisões

### D1. Onde roda: **Routines do Claude Code + núcleo Python determinístico** (unânime)
- Uma Routine dispara uma sessão do Claude Code neste ambiente. A sessão roda `pipeline/tick.py plan` e executa a lista de ações (roteiro, imagem pela OpenAI, vídeo pelo Higgsfield via MCP, pacote). Depois roda `tick.py record`.
- O LLM não decide o fluxo; quem decide é o código. Cada ação tem uma chave idempotente e o `job_id` é gravado antes do polling, para não pagar duas vezes.
- **Fonte da verdade:** a fila em JSON no git (`data/queue/`). O banco do painel é espelho e caixa de decisões, com um escritor por campo.
- GitHub Actions entra só depois, para publicar pela Graph API. n8n e Make: **vetados** nesta fase.

### D2. Controle: **painel Usina** (unânime)
Ganha as abas **Caixa de aprovação**, **Placar** (métricas lançadas à mão em 2 min/dia) e **Saúde** (última run, gasto, erros, kill switch). Vercel: não agora.

### D3. Portões humanos
- **Obrigatório, sempre:** o vídeo final com a legenda (unânime). Postar à mão já é o "ok".
- **Frames:** um revisor de IA aplica o checklist (refaz sozinho até 2 vezes; na 3ª reprovação, descarta). Nas **2 primeiras semanas de cada personagem**, o Caio também aprova os frames, para calibrar o prompt. Isso junta o portão financeiro (frame custa centavos e evita vídeo caro) com a calibragem que o Criativo pediu.
- **Pauta:** gerada sozinha. O Caio pode vetar ideias no painel, mas não é bloqueante (o Crescimento vetou gargalo).

### D4. Publicação: **pacote pronto, o Caio posta pelo app nas primeiras 4 semanas** (unânime)
- **Pacote:** MP4 sem música, capa, legenda, 3 sugestões de som em alta, checklist de rótulo de IA.
- **Motivos:** o áudio em alta só existe no app; não há campo oficial de rótulo de IA confirmado na Graph API; as contas novas são aquecidas por um humano.
- **Depois:** Graph API (Instagram Login, uma conta Creator por página) só para conteúdo já aprovado, mais Trial Reels a partir de 1k seguidores. O TikTok fica manual.

### D5. Cadência e orçamento
- **Gersinho:**
  - Começa com **1 por dia**.
  - Sobe para **2 por dia** quando houver ≥4 vídeos aprovados no estoque e o D7 mostrar tração (mediana >5k views ou um Reel >50k).
  - Desempate: o Crescimento queria 2 por dia já; o Financeiro e o Risco queriam 1. Ficou 1, com gatilho objetivo para subir.
- **Teto do mês 1:** US$ 300 (Higgsfield + OpenAI).
  - Teto diário: US$ 12 no Higgsfield e US$ 2 na OpenAI.
  - Avisos em 50% e 80% do mês. Em 80%, corta o Seedance 1080p e o Genjutsu. Em 100%, para tudo.
- **Paradas automáticas** (regras do Financeiro):
  - 4 tentativas ou 160 créditos na mesma ideia: descarta a ideia.
  - Aproveitamento <30% nas últimas 10 gerações: para e avisa.
  - Saldo Higgsfield <300 créditos: para.
  - Mais de 5 vídeos prontos e não postados na página: para de gerar.
  - 3 erros seguidos: pausa.
- **Livro-caixa:** toda geração registra o custo.
- **Resolução:** gerar em **720p**. Upscale só nos vídeos que performarem.

### D6. As 3 páginas
- **Fórmula da casa (fixa nas 3):**
  - Fotorrealismo de celular, 9:16, 8–12 s, sem diálogo.
  - **Deadpan absoluto**; ninguém reage.
  - Brasil popular real.
  - Estrutura chegada → gesto assinatura → piada física no fim, com loop.
  - Brand-safe; capa com até 4 palavras.
- **Varia por página:** silhueta-letra, gênero e BPM, mundo, gesto, piada recorrente, câmera padrão, voz da legenda.
- **Página 1:** Gerson Brilhantina, silhueta **I**, brega.
- **Página 2: Marlene Laquê**, silhueta **O**: a "ex/par" do Gersinho, axé lento, tira objetos de dentro do cabelo. É a fusão da Dona Cleide (Crescimento) com a Marlene (Criativo); os dois escolheram a tia do laquê.
- **Página 3: Wanderley Bigodão**, silhueta **—** (horizontal): o rival, pagode anos 90, alisa o bigode e gira 360°.
  - O Criativo preferia o Rubão Supino (silhueta V, maromba). O Wanderley venceu porque a barra horizontal contrasta com a vertical do Gersinho e tem menos risco de comentário sobre corpo (ressalva do próprio Crescimento).
  - O Rubão fica de reserva, e o Seu Tadeu Carimbo vira personagem recorrente de crossover.
- **Lançamento escalonado:**
  - A P2 estreia no mínimo no D+10 do Gersinho, com 10 vídeos em estoque e ficha aprovada.
  - A P3 estreia no mínimo no D+20.
  - Estreia via **cameo** no fundo de um vídeo do Gersinho e depois post Collab.
  - O Financeiro queria a P2 só depois do D21. Ficou D+10 condicionado a estoque e orçamento.
- **Deixar pronto agora:**
  - `page.yaml` completo das 3 (P2 e P3 com `status: rascunho`).
  - Prompts das fichas de referência.
  - 3 roteiros de crossover.
  - Teste da **silhueta preta na miniatura** (eliminatório).

### D7. Mix de conteúdo
- **60%** formato próprio do zero.
- **25%** trend com motion control, sempre com cenário e piada próprios. Teto de **30%** por página em 30 dias (Risco), por causa da regra de originalidade.
- **15%** série e crossover.
- **Radar:** a mesma trend nunca vai para duas páginas na mesma semana. A pontuação tem 5 critérios: coreografia ≤10 s, BPM compatível, letra limpa, trend com menos de 7 dias e piada física possível.

### D8. Riscos: regras do Risco adotadas integralmente
**A automação NUNCA:**
- publica, agenda ou apaga;
- manda DM, comenta, segue ou curte;
- mexe em bio ou configurações;
- gera pessoa real reconhecível;
- remove C2PA;
- liga as páginas ao PdG;
- passa do teto;
- toca em cripto.

**Demais regras:**
- Rótulo "AI-generated profile" e "AI info" em tudo desde o dia 1.
- Contas isoladas do PdG: e-mail próprio, Business Portfolio separado, chave OpenAI dedicada com limite de gasto.
- Nenhum arquivo, legenda ou trend duplicado entre contas.
- Kill switch `PAUSE` lido por toda run.
- Veto total a meme coin.

### D9. Qualidade (decisão do moderador, a pedido do Caio): **sistema profissional storyboard-first**
O vídeo da laje falhou por três motivos:
1. Ações demais num clipe só: olhar o celular, guardar, encarar, dançar.
2. Um conceito abstrato sem contraparte visível ("o brega desafia o boxe").
3. Nenhum quadro de controle intermediário.

Daqui em diante:
1. **Uma ideia = 1 gag visual que se entende sem som.** No máximo **2 ações por clipe de 10 s**, e a última é a piada.
2. **Planejamento por beats** (`playbook/`), com regras de duração e número de ações.
3. **Storyboard primeiro:** grade de painéis no GPT Image (centavos), curada pelo revisor de IA e pelo Caio, antes de qualquer vídeo. É o método já validado no PdG (Miauzada, Louie longboard).
4. **Primeiro e último frame** gerados a partir do storyboard aprovado. O Seedance 2.5 recebe frames + storyboard + referência de identidade, com o prompt na estrutura de blocos (`seedance-clean`).
5. **Revisor de IA de vídeo:** amostra frames, aplica a rubrica e reprova antes de chegar ao Caio.
6. **Livro de falhas:** cada reprovação vira uma linha em `playbook/falhas.md` (sintoma → causa → correção), e o gerador de prompt lê esse arquivo.
7. **Estudo contínuo:** a biblioteca de prompts profissional (OSideMedia, MIT) e as skills oficiais do Higgsfield ficam em `vendor/`. Os playbooks destilados ficam em `playbook/`.

---

## Depende do Caio (não bloqueia a construção)
1. Liberar `api.openai.com` e criar a `OPENAI_API_KEY` (chave dedicada à Usina) nas configurações do ambiente.
2. Criar as contas no Instagram: Gersinho já; Marlene e Wanderley só reservar o @. Ativar o rótulo de IA.
3. Confirmar os tetos (US$ 300/mês, US$ 12/dia).
4. Aprovar a ficha da Marlene e do Wanderley quando forem geradas.
5. Ligar a Routine diária (deixada pronta em modo `--mock`).

---

## Notas de implementação (QA rodada 2, 05/10/2026)
As decisões acima não mudaram. Estas notas só dizem onde cada regra vive no código, para a ata, o `SKILL.md`, a CLI e o painel lerem igual (detalhes em `docs/qa/rodada-2.md`).
- **D1:** o "`tick.py plan` / `tick.py record`" é `python -m pipeline plan` e os comandos `record-*`, `review` e `approve`.
- **D2:** a aba Saúde tem o kill switch (pausar e retomar viram decisões aplicadas pelo `panel-apply`), os erros seguidos, o saldo do Higgsfield e o gatilho de cadência.
- **D3:** sem `launched_at` no `page.yaml`, as 2 semanas de calibração contam a partir do 1º post registrado (`posted`). O veto de pauta é o botão "Vetar" da Fila: descarta o item se ele ainda está em ideia, roteiro ou storyboard.
- **D5:**
  - 50% do mês vira aviso no plano. Em 80%, o Genjutsu (trend) fica bloqueado e o Seedance sai só em 720p.
  - "Mais de 5 prontos" é `> max_unposted_per_page`. A trava para só o gasto novo; busca, revisão e pacote de vídeo já pago continuam.
  - Saldo < 300 créditos: `balance` grava o saldo lido, e o saldo vale por 24 h.
  - 3 erros seguidos: `record-error` cria o `PAUSE` sozinho.
  - Estorno: `record-video --failed --refunded` devolve os créditos ao teto da ideia, mas a tentativa continua contando.
  - Gatilho de 2 posts por dia: `cadence-check` usa o Placar e prefere as views de 7 dias. Ele só sugere; quem muda o `page.yaml` é o Caio.
- **D7:** o plano mostra a fatia de trend dos últimos 30 dias e avisa no teto de 30%. Trend sem vídeo-fonte há mais de 7 dias é descartada. A regra "mesma trend em 2 páginas na mesma semana" ainda não está no código.

## Notas de implementação (QA rodada 3, 05/10/2026)
As decisões não mudaram; detalhes em `docs/qa/rodada-3.md`.
- **D1/D8 (um ciclo por vez):** `tick-start` grava `usina/.lock` (TTL de 2 h) e `tick-end` libera. Com o lock de outro ciclo, o `plan` não devolve ações e o `video-request` recusa.
- **D6:** página em `rascunho` não gera nada (`image` e `video-request` recusam até com `--force`). Página ativa só gera com a ficha aprovada (face + silhouette com `higgsfield_id`). A P2 entra no D+10 e a P3 no D+20 do Gersinho (`launched_at` ou 1º post). Antes do 1º post, a página precisa de 10 prontos: o estoque-alvo vira 10 e o teto de 5 não vale. Tudo em `launch-check <página>` e nas `notes` do plano. O código nunca muda `status`.
- **D7:** a mesma trend (nome normalizado) em duas páginas na mesma semana é erro no `save-script`. Quando uma trend nova passaria de 30% em 30 dias, o plano manda `allow_trend: false` e avisa.
- **D9.6:** `memory <página>` imprime as últimas 15 falhas da página e as 15 gerais do `playbook/falhas.md`. O `save-script` avisa quando o cenário repete um dos últimos 20 roteiros da página.

## Notas de implementação (QA rodada 4, 05/10/2026)
As decisões não mudaram; detalhes em `docs/qa/rodada-4.md`.
- **D3:** na trend com gag, o Caio aprova o vídeo **final** (MC + gag). O card só aparece depois do gag aprovado ou descartado, e aprovação anterior vira obsoleta. O pacote pronto vira asset do painel (Baixar MP4), e o "Postei" da Fila, ou números no Placar, levam o item a `postado`.
- **D5:** estorno também no gag (`record-video --gag --refunded`). Vídeo reprovado com a ideia no teto vai direto para descarte.
