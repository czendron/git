# Conselho, cadeira 4: Guardião de risco, compliance e reputação

*Premissa: o ativo que não pode cair é o Papo de Gato (~90k). As 3 páginas novas são experimento, e se algo der errado o dano tem que ficar nelas.*

## Posição sobre as 8 decisões

**1. Onde roda.** Routines + repositório, desde que nenhuma Routine tenha poder de publicar. Evitar n8n/Make por agora, porque é mais um lugar guardando credenciais.

**2. Controle.** Painel Usina no claude.ai (privado). Nenhum app público com token de Instagram.

**3. Portões humanos (foco).** São **2 obrigatórios**: (a) aprovar o vídeo final + legenda; (b) o "ok" que libera a publicação. Ideia e frames rodam sem aprovação, porque custam só crédito e não expõem marca nenhuma. Há também um portão leve no motion control: o Caio confirma a fonte do vídeo de referência.

**4. Publicação (foco).** Nas **4 primeiras semanas, o sistema entrega o pacote pronto e o Caio posta pelo app**. São três motivos: as contas novas precisam de aquecimento humano; o áudio em alta só existe no app; e o "AI info" é garantido no app, enquanto a Graph API não tem um campo oficial confirmado para isso. Depois desse período, a Graph API oficial (Instagram Login, uma conta Creator por página, app em modo dev) pode publicar **só o que passou pelo portão (a)**, com áudio próprio embutido. Evitar Ayrshare/Buzzfy, porque cada intermediário é um token a mais fora do nosso controle. No TikTok, a API deixa tudo SELF_ONLY até a auditoria, então lá a publicação é manual.

**5. Cadência.** 1 Reel/dia por página nas 2 primeiras semanas. Teto de gasto diário no código: ao atingir o limite, a Routine para.

**6. Três páginas.** Personagens bem distintos entre si (silhueta, paleta, cenário). Crossover pode, desde que cada conta tenha o seu próprio vídeo e nunca um repost. Nada que lembre o universo PdG.

**7 e 8.** Detalhados abaixo.

## Regras não negociáveis (a automação NUNCA faz sozinha)

1. Publicar, agendar ou apagar post.
2. Mandar DM, comentar, seguir ou curtir. Engajamento automatizado é exatamente o que a Meta pune como inautêntico.
3. Mexer em bio, link, @, rótulos ou configurações.
4. Gerar rosto, nome ou voz de pessoa real reconhecível.
5. Remover metadados C2PA/IPTC.
6. Ligar qualquer página nova ao PdG, seja por marcação, repost, e-mail ou link.
7. Passar do teto diário de créditos.
8. Tocar em cripto, token, sorteio ou link de terceiros.

## Rótulo de IA e originalidade

- **Rótulo:** ativar o "AI-generated profile" nas 3 contas no dia 1 e marcar "AI info" em todo Reel. Desde 31/08/2026, perfil de IA sem rótulo perde a recomendação para não seguidores, que é de onde vem o crescimento. Para um formato assumidamente absurdo, o rótulo não custa nada. Na bio, escrever "personagem de IA".
- **Originalidade:** a regra antiagregador olha os últimos 30 dias. Cada vídeo precisa de cenário, figurino, piada e legenda próprios. Motion de trend fica em **no máximo 30% do mix**, e os outros 70% são cenas originais do universo do personagem. Ainda não se sabe como o classificador trata motion transfer, então não dá para apostar nele.

## Três contas sem contaminar o PdG nem levar shadowban em cadeia

- **Isolamento:** um e-mail novo por conta (nenhum deles o do Caio ou o do PdG) e 2FA por app autenticador. Um **Business Portfolio separado** só para a Usina, fora do Accounts Center do PdG. As 3 páginas ficam de preferência num segundo aparelho, ou pelo menos sem o PdG logado no mesmo app.
- **Sem antidetect e sem proxy:** são contas legítimas e rotuladas. Ferramenta de "multilogin" é o que faz parecer fraude.
- **O que liga as contas no shadowban em cadeia** é conteúdo duplicado e comportamento idêntico. A regra é arquivo único, legenda e hashtags próprias, horários diferentes e nada de interação em massa entre as 3.
- **Aquecimento:** 7 a 14 dias de uso humano antes de aumentar o volume.

## Trends com pessoas reais e música

- **Jean Phil:** copiar o **formato** pode; copiar o **personagem** não (chanel loiro, bigode de guidão, houndstooth, nome parecido). Não marcar nem citar o perfil, e nunca chegar perto do $JEANPHIL, que foi acusado de pump-and-dump.
- **Hotel Lobby e parecidos (pessoa real como fonte de motion):** o vídeo entra só como movimento. O resultado não pode mostrar rosto, corpo, tatuagem ou voz da pessoa, nem sugerir que é ela. Proibido usar vídeo com menor de idade ou de alguém que viralizou contra a vontade. Registrar a fonte na Biblioteca e, se o dono pedir, tirar no mesmo dia.
- **Música:** pela API vai só áudio próprio (nativo do Seedance), royalty-free com licença arquivada, ou nenhum. Som em alta só entra pelo app, com a biblioteca do Instagram. Música comercial embutida no MP4 dá mute e, se repetir, strike.

## Tokens e credenciais

- `OPENAI_API_KEY` e as chaves do Higgsfield ficam nas variáveis do ambiente Claude Code ou em GitHub environment secrets. Nunca no repo, no artifact, no banco compartilhado ou em log.
- **Chave da OpenAI dedicada à Usina**, separada da do PdG, com limite mensal de gasto configurado na OpenAI.
- Tokens do Instagram: um por conta, com escopo mínimo (basic + content_publish, sem mensagens). O token dura 60 dias, e a renovação é feita por uma rotina que só avisa o Caio.
- `.gitignore` para `.env*`, secret scanning antes de push e repo privado.

## Se uma conta cair

1. **Kill switch:** um flag `PAUSE=1` que toda Routine lê antes de rodar. Pausar as 3 páginas.
2. Não criar conta substituta nem logar de outro lugar. Pedir revisão uma única vez, pelo app.
3. Auditar os últimos 10 posts (áudio, fonte do motion, legenda) e achar a causa antes de voltar.
4. As outras duas ficam paradas 48-72 h e voltam com volume menor.
5. Revogar e rotacionar o token da conta que caiu.
6. O PdG não toca no assunto. Com o isolamento, a queda não se propaga.
7. Manter backup de vídeos e fichas: o ativo é o personagem, a conta é só o canal.

## Riscos de negócio

- **A trend morre em semanas.** Por isso o foco é construir personagem e universo, não meme.
- **Meme coin: veto total.** Promover um ativo sem divulgação dá risco jurídico (CVM no Brasil, ASIC na Austrália) e reputacional. Golpistas vão aparecer oferecendo "lançar seu token": bloquear.

## Meu voto em 5 linhas

1. Gerar e empacotar no automático; publicar só com o "ok" do Caio, e à mão nas 4 primeiras semanas.
2. Rótulo de IA em tudo desde o dia 1, sem nunca remover metadados.
3. Contas isoladas do PdG (e-mail, Business Portfolio, chave OpenAI) e arquivos 100% únicos por conta.
4. Motion de trend em até 30% do mix, sem pessoa real visível; música só original/licenciada ou adicionada no app.
5. Secrets fora do repo, teto de gasto e kill switch antes de ligar qualquer Routine.

## O que eu vetaria

- Publicação, DM, comentário, follow ou curtida feitos pela automação sem o Caio.
- Meme coin, cripto ou link de "investimento".
- Remover rótulo ou metadados de IA.
- Copiar visual ou nome de criador real; mostrar pessoa real em vídeo gerado.
- Mesmo vídeo ou legenda em mais de uma conta.
- Ligar as páginas novas ao PdG antes de elas provarem que são seguras.
- Antidetect, proxy, compra de seguidores, engajamento automatizado.
- Token em código, artifact, banco compartilhado ou painel público.
