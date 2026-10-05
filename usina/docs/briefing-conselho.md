# Briefing do conselho: Usina de Virais (3 páginas)

## Pedido do Caio (05/10/2026)
"Vou montar 3 páginas de Instagram. 3 personagens diferentes, mesmo estilo e tudo rodando aqui. De maneira automatizada, pra que os vídeos sejam gerados da forma mais automática possível. Pesquise a fundo como o pessoal está fazendo isso (faceless channels, shorts). Monte uma automação excelente. Não gera vídeos no Higgsfield ainda. Use a API do ChatGPT pra imagens, como no Papo de Gato. Já deixa tudo pronto pras 3 páginas, mesmo que os outros 2 personagens não tenham sido definidos."

## Quem é o Caio
- Criador do Papo de Gato (PdG): IP de personagens felinos de IA, cerca de 90k seguidores no Instagram, produção 100% solo. Mora na Austrália; o conteúdo é em português, para o público brasileiro.
- Já tem pipeline próprio no PdG: `tools/gpt_image.py` (OpenAI Images API, modelo `gpt-image-2.5-sunburst`, edição com referências), Higgsfield (Seedance), Kling, CapCut, Claude Code.
- Regras de marca que ele aplica no PdG: brand-safe (sem política, religião, futebol, sexo, palavrão). DM e e-mail nunca são enviados por agente sem ele aprovar (risco de conta).
- Usa "conselho" (painel de especialistas que debate e decide) para decisões estratégicas.

## O formato (trend Jean Phil, set/out 2026)
- Personagem de IA com silhueta absurda (cabelo geométrico, bigode), cara séria (deadpan), dançando ou fazendo algo banal em lugares comuns enquanto ninguém reage. Selfie POV com grande angular, ou câmera parada de passante. Sem diálogo; a música entra na edição.
- O Jean Phil fez 145k seguidores em 3 dias. Surgiram cópias (Phil Jean) e rivais (Archibald Brown, 110k).
- A versão do Caio é o personagem 1, **Gerson Brilhantina ("Gersinho")**: brega brasileiro, topete gigante e rígido, cara torta, dentuço, camisa de seda tropical, corrente de ouro, gravado "no Brasil" (busão, feira, calçadão, padaria, laje). O design já foi aprovado (ref Higgsfield `c4c11710-…`).
- Personagens 2 e 3: **ainda não definidos**. Existe um rascunho, a Dona Cleide (tia do laquê), mas não foi aprovada.

## O que já existe
- **Usina de Virais (MVP)**: artifact no claude.ai com abas Radar, Elenco, Roteiro, Motion control e Biblioteca. Usa o conector Higgsfield (MCP), o Claude (sample) e um banco compartilhado. Testado: o próprio painel consultou o Higgsfield e atualizou o banco.
- Vídeos de teste já gerados: padaria (Kling), busão (Seedance 2.5 com primeiro e último frame), feira, calçadão, laje e um teste de motion control.
- Repositório GitHub `czendron/git`, branch `usina-de-virais`.

## Restrições técnicas reais do ambiente
- As sessões em nuvem do Claude Code ("aqui") rodam num container com rede restrita. Hoje `api.openai.com`, `vercel.com` e a API REST do Higgsfield estão bloqueados; PyPI e npm funcionam. O Caio pode liberar domínios e adicionar variáveis de ambiente (ex.: `OPENAI_API_KEY`) nas configurações do ambiente.
- Existem **Routines** (gatilhos agendados por cron) que abrem uma sessão nova do Claude Code neste ambiente a cada disparo. A sessão tem acesso aos conectores MCP (Higgsfield, Google Drive, Gmail etc.) e ao repositório.
- O artifact (painel) não carrega mídia externa inline e não chama APIs fora dos conectores.
- O Higgsfield via MCP gera imagem (inclusive `gpt_image_2_5`, o mesmo modelo da OpenAI), vídeo (Seedance 2.5, Kling 3), motion control (Genjutsu) e análise de vídeo do YouTube.
- Publicar no Instagram: não há conector instalado. Opções: plugins do diretório (Ayrshare, Posty, Buzzfy), a Instagram Graph API direto, ou o Caio posta à mão com o pacote pronto.
- O Caio vai dormir: o sistema precisa ficar pronto para rodar sem perguntas.

## Decisões que o conselho precisa tomar
1. **Onde a automação roda**: Routines do Claude Code, GitHub Actions + APIs, n8n/Make, ou uma combinação.
2. **Onde fica o controle**: o painel Usina (claude.ai), um app na Vercel, ou outra coisa.
3. **Portões humanos**: quantos e em que etapas (ideia, frames, vídeo final, post). O que roda sem aprovação.
4. **Publicação**: automática (qual via) ou pacote pronto para o Caio postar. Música/áudio em alta.
5. **Cadência e volume** por página; orçamento de créditos (OpenAI, Higgsfield, Claude).
6. **Estratégia das 3 páginas**: como diferenciar os personagens 2 e 3 no "mesmo estilo"; o que deixar pronto antes de eles existirem; crossovers e rivalidades.
7. **Mix de conteúdo**: do zero vs motion control de trend; como pescar trends automaticamente.
8. **Riscos**: políticas da Meta (rótulo de IA, originalidade, várias contas), dependência de uma trend que pode morrer, custos.
