# Conselho 01: Crescimento (contas faceless e personagens de IA)

**Premissa que guia tudo:** a janela da trend é curta. O Jean Phil postou pela primeira vez em 17/09; hoje é 05/10. Quem entrar em novembro chega numa onda saturada. Então velocidade de publicação vale mais que elegância de infraestrutura, e cada personagem precisa sobreviver depois que a dança deixar de ser novidade.

## 1. Onde a automação roda
**Routines do Claude Code agora, GitHub Actions só para publicar (e depois).** As Routines já falam com o Higgsfield via MCP e com o repo, ou seja, funcionam hoje sem liberar domínio nenhum. Configuração: uma Routine às 03:00 BRT (que é meio-dia na Austrália) que gera os candidatos do dia para cada página ativa. n8n e Make ficam vetados nesta fase, porque montar isso leva uma semana e essa semana é a trend.
**Risco:** a Routine falhar calada. Ela precisa escrever o status no banco do painel e mandar um alerta quando a fila do dia ficar vazia.

## 2. Onde fica o controle
**No painel Usina, com uma aba nova "Placar".** Nada de Vercel. Para crescer, o painel precisa mostrar por Reel: views nas primeiras 24 h, envios por alcance, retenção em 3 s e seguidores ganhos. O Caio lança esses números à mão em 2 minutos por dia, até existir a Graph API.
**Risco:** o painel virar vitrine de produção sem dizer o que funciona. Sem o placar, ninguém decide nada.

## 3. Portões humanos
**Um portão só, obrigatório: o corte final.** A Routine entrega **3 candidatos por post** (vídeo, legenda e capa) e o Caio escolhe 1 em cerca de 10 minutos de manhã. Ideia e frames passam sem aprovação; o critério de frame vira checklist automático (topete visível, rosto consistente, 9:16). Na primeira semana dá para pôr um portão opcional nos frames, só para calibrar o prompt de cada cenário.
**Risco:** se cada etapa precisar de aprovação, o Caio vira gargalo e a cadência morre.

## 4. Publicação
**Nos primeiros 30 dias, pacote pronto e o Caio posta à mão.** Aqui eu discordo do impulso de automatizar tudo: nesse formato, o **áudio em alta é o motor de distribuição**, e a API não tem acesso a ele. O pacote leva:
- o MP4 sem música;
- 3 sugestões de som em alta (via `tiktok_music_trending` do Higgsfield);
- a legenda e o frame de capa.

Postar também no **TikTok**, em conta própria. Foi lá que o Jean Phil explodiu (5,6 mi de views no dia 2), e o Instagram veio a reboque. A publicação via Graph API entra no 2º mês, junto com Trial Reels (a partir de 1k seguidores) para testar ganchos.
**Risco:** depender do Caio todo dia. Para isso existe um buffer de 2 dias na fila.

## 5. Cadência e orçamento
Aqui eu discordo da recomendação de começar com 1 por dia. Para contas legítimas e rotuladas, "aquecimento" é mito de vendedor de proxy, e a trend não espera.
- **Gersinho:** 2 Reels/dia (12:30 e 19:30 BRT) por 21 dias.
- **Página 2:** estreia no D+7 com 1/dia e sobe para 2/dia se a retenção segurar.
- **Página 3:** estreia no D+14.
- **Duração:** 7 a 10 s, em loop. O primeiro frame já mostra a silhueta em movimento, sem intro.

**Orçamento:** cerca de 120 Reels no mês 1. Em 720p, com 3 candidatos por post, isso dá uns US$ 4-5 por Reel publicado. **Teto de US$ 600 no mês 1** (Higgsfield + OpenAI; o Claude roda no plano). O upscale para 1080p fica só para Reels que passarem de 50k views.
**Regra de corte:** se o Gersinho chegar ao D+21 com menos de 5k seguidores e nenhum Reel acima de 100k views, o formato muda antes de gastar mais.

## 6. As 3 páginas
O "mesmo estilo" é a **gramática**, não a cara:
- deadpan;
- um traço físico absurdo e rígido;
- ninguém reage;
- selfie POV em grande angular;
- Brasil popular;
- mesma color grading;
- legenda de "celebridade convicta".

A diferenciação vem de **três silhuetas geométricas opostas** que se reconhecem numa miniatura de 3 cm: o Gersinho é uma **barra vertical** (o topete). Cada personagem também ganha um gênero musical e um território próprio.

**Conceito A, Dona Cleide Laquê.** Tia dos anos 90 com um laquê lilás em **cúpula perfeita**, larga como um capacete, óculos de gatinho enormes, ombreiras, pochete e leque. O mundo dela: fila do banco, salão de bairro, bingo, excursão de ônibus, chá de bebê. Dança axé lento com o leque. A assinatura é fechar o leque com um estalo e congelar o olhar. Diferencia por três coisas: é a única mulher, tem a silhueta redonda e é a **paixão não correspondida do Gersinho**.

**Conceito B, Wanderley Bigodão.** Tiozão com um **bigode horizontal rígido mais largo que os ombros**, regata, bermuda tactel, meia com chinelo e boné de posto. O mundo dele: posto de gasolina, churrasco de laje, oficina, praia lotada. Dança pagode dos anos 90 (miudinho). A assinatura é alisar o bigode com dois dedos e dar um giro de 360° lento. É a **barra horizontal** contra a vertical do Gersinho e o rival natural dele ("o calçadão é meu").

**Conceito C, Tonhão Marombinha.** A **silhueta é um triângulo invertido**: cabeça minúscula num tronco inflado, viseira, regata cavada e perninhas finas. O mundo dele: academia de bairro, praça, feira, caixa de supermercado. Faz poses de fisiculturismo no ritmo do funk melody (instrumental). A assinatura é a pose de bíceps que trava 2 s. A forma é ótima, mas há risco de comentário sobre corpo e de cair na "fitness meme" genérica.

**Escolho A e B.** Os três juntos formam um alfabeto visual (barra, cúpula, barra deitada), o que dá uma família, não três clones. E eles já nascem com relações prontas: um **triângulo amoroso brega** (Gersinho gosta da Cleide, Wanderley disputa). Foi a rivalidade que deu 110k ao Archibald em dias.

**O que deixar pronto antes de eles existirem:**
- os handles reservados agora (IG + TikTok) para os 3;
- um `page.yaml` rascunho para cada um;
- os slots na fila;
- o roteiro de estreia.

A estreia funciona assim:
1. **Cameo sem marcação** no fundo de um vídeo do Gersinho (D+4).
2. Os comentários perguntam quem é.
3. A conta abre no D+7 com post Collab (`collaborators`) junto do Gersinho.

**Risco:** os personagens 2 e 3 parecerem "o Gersinho de peruca". Por isso o teste de silhueta preta na miniatura é eliminatório.

## 7. Mix de conteúdo
- **60% do zero:** dança assinatura em cenário brasileiro novo a cada vídeo.
- **25% motion control de trend:** só com dança em alta e um cenário/piada próprio.
- **15% universo:** crossovers, "respostas" entre personagens e Collabs.

A meta escondida é transformar a dança do Gersinho numa trend replicável, porque o "Gang Gang Dance" multiplicou o Jean Phil.

**Pesca de trends:** uma Routine diária com `tiktok_music_trending` (BR) mais `video_analysis` nos 5 Reels de IA que mais cresceram. Apify só no 2º mês, se a pesca manual falhar.

**Risco:** motion control demais faz a conta parecer agregadora na regra de originalidade.

## 8. Riscos
1. **Morte da trend (o maior).** Defesa: personagem acima do formato. Até o D+30, cada página precisa ter 2 quadros recorrentes que não dependem de dança (ex.: "Gersinho avalia" e "Cleide na fila").
2. **Meta.** Ligar o rótulo "AI-generated profile" e o "AI info" desde o dia 1. Sem rótulo, a conta perde recomendação para não seguidores, que é onde está o crescimento. Nunca subir o mesmo arquivo em duas contas, e manter legendas e cenários distintos.
3. **Custo.** Teto mensal e taxa de descarte medida.
4. **Sem meme coin, nunca.**
5. **Cópia.** O Caio é "mais um Jean Phil". A defesa é ser brasileiro até o osso: piada local que um belga não faz.

## Meu voto em 5 linhas
1. Routines + MCP agora, painel Usina com Placar e um único portão (o corte final, 3 candidatos por post).
2. Postagem manual nos 30 primeiros dias, por causa do áudio em alta, espelhada no TikTok. Graph API e Trial Reels no mês 2.
3. Gersinho com 2 por dia a partir de já; Cleide no D+7 e Wanderley no D+14, com estreia via cameo e Collab.
4. Mix 60/25/15, Reels de 7-10 s em loop, teto de US$ 600 no mês 1 e regra de corte no D+21.
5. Rótulo de IA ligado, nenhum arquivo duplicado e personagens com quadros que sobrevivam à morte da trend.

## O que eu vetaria
- Lançar as 3 páginas no mesmo dia: divide a atenção do Caio e desperdiça a mecânica de estreia por rivalidade.
- Publicar automaticamente via API no mês 1, com música royalty-free no lugar do som em alta.
- Gastar a primeira semana montando n8n, Vercel ou Apify.
- Personagem 2 ou 3 que não passe no teste da silhueta preta na miniatura.
- Meme coin, ou qualquer link de cripto na bio.
- Gerar tudo em 1080p "por garantia".
