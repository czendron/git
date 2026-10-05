# Usina de Virais

Painel para pesquisar vídeos virais, escrever roteiros com o Claude e gerar frames, vídeos (Seedance 2.5) e motion control (Genjutsu) no Higgsfield. Formato padrão: 9:16.

**Onde roda:** artifact publicado no claude.ai (privado, só o dono abre):
https://claude.ai/artifact/2yF5cU2n9MDbWtQHFj5p4c

## Como funciona

O painel não guarda chave de API. Ele roda dentro do claude.ai e usa três recursos da sua conta:

| Recurso | Para quê |
|---|---|
| Conector **Higgsfield** (`mcp`) | gerar imagens (`gpt_image_2_5`), vídeos (`seedance_2_5`), motion control (`hf_mult_motion_control`), importar vídeo por link, analisar vídeo do YouTube, consultar status e créditos |
| **Claude** (`sample`) | escrever roteiros e prompts; gerar novas ideias pro radar |
| **Banco** (`db`) | radar de ideias, elenco, roteiros, jobs e análises. Compartilhado, sobrevive a atualizações |

Na primeira vez que você usar cada recurso, o claude.ai pede permissão.

## Abas

1. **Radar**: referências virais do Brasil e de fora, já pesquisadas (Jean Phil, Gang Gang, Hotel Lobby, That's My Dawg, Baby Laugh, Chiki Sha…), mais as nossas ideias. Botão para o Claude gerar ideias novas.
2. **Elenco**: personagens com o ID da imagem de referência aprovada. Essa referência entra em todas as gerações.
3. **Roteiro**: ideia → o Claude devolve linha do tempo, prompts do primeiro e do último frame, prompt do vídeo, legenda e sugestão de música → gerar frames → gerar vídeo no Seedance 2.5 usando os frames.
4. **Motion control**: personagem + vídeo-fonte (link direto .mp4 ou ID de vídeo no Higgsfield) → Genjutsu. Também analisa vídeo do YouTube cena a cena e vira roteiro.
5. **Biblioteca**: todos os jobs, com status que atualiza sozinho e link para abrir o arquivo.

## Limitações do MVP

- **Mídia abre em outra aba.** A página do artifact não consegue carregar imagem ou vídeo de domínios externos (CDN do Higgsfield), então mostra links.
- **Vídeo-fonte do motion control** precisa ser o arquivo (.mp4), não a página do TikTok ou do Instagram. Caminho prático: baixar o vídeo, subir em higgsfield.ai e colar o ID.
- **O Claude não navega na web dentro do painel.** As ideias novas vêm do que ele já sabe e do radar. Pesquisa com fontes é feita numa sessão do Claude Code, que grava no banco.

## Levar para a Vercel (próximo passo)

Para hospedar fora do claude.ai, com mídia inline:
1. Criar uma API key em platform.higgsfield.ai e uma da Anthropic.
2. Portar este HTML para Next.js: rotas `/api/generate`, `/api/status` e `/api/script` chamam a API do Higgsfield e a do Claude no servidor; o banco vira Supabase ou Vercel KV.
3. Conectar o repositório na Vercel e definir `HIGGSFIELD_API_KEY` e `ANTHROPIC_API_KEY`.

Não deu para fazer isso nesta sessão: a rede do ambiente bloqueia `vercel.com` e a API do Higgsfield, e não havia chaves configuradas.
