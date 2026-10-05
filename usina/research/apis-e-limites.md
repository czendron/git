# APIs e limites: pipeline de Reels para 3 contas

> Pesquisa feita em 2026-10-05 por buscas na web. As páginas oficiais da Meta (developers.facebook.com) e da Higgsfield (docs.higgsfield.ai) estavam bloqueadas pelo proxy, então os fatos vêm dos resumos de busca. **Confirme na documentação oficial antes de colocar em produção.**
> Legenda: ✅ confirmado por fonte oficial ou por várias fontes · ⚠️ incerto ou com fontes em conflito.

---

## 1. API de imagens da OpenAI

### Modelos atuais
- ✅ **`gpt-image-2`**: lançado na API em 21/04/2026 e chegou ao ChatGPT como "ChatGPT Images 2.0". O modelo raciocina antes de gerar ("thinking"). [Wikipedia GPT Image](https://en.wikipedia.org/wiki/GPT_Image) · [OpenAI: Images 2.0](https://openai.com/index/introducing-chatgpt-images-2-0/) · [model page](https://developers.openai.com/api/docs/models/gpt-image-2)
- ✅ **GPT Image 2.5** ("ChatGPT Images 2.5") saiu em 08/09/2026, com cerca de 50% menos latência. Na API existem dois IDs:
  - **`gpt-image-2.5-flare`**: mais rápido. [model page](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare)
  - **`gpt-image-2.5-sunburst`**: mais detalhado e mais lento. [OpenAI: Images 2.5](https://openai.com/index/introducing-chatgpt-images-2-5/) · [Wikipedia](https://en.wikipedia.org/wiki/GPT_Image)
- Modelos antigos ainda listados: `gpt-image-1`, `gpt-image-1.5`, `gpt-image-1-mini`.

### Endpoints
- `POST /v1/images/generations` (`images.generate`): gera a partir de texto. [ref](https://developers.openai.com/api/reference/resources/images/methods/generate)
- `POST /v1/images/edits` (`images.edit`): multipart com **até 16 imagens de entrada** nos modelos GPT Image, além de `mask` opcional. [ref edit](https://developers.openai.com/api/reference/resources/images/methods/edit) · [prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)
  - Boa prática: no prompt, nomeie cada referência ("Image 1: personagem… Image 2: cenário…").
  - A **primeira imagem** é preservada com mais riqueza de textura. Para manter o rosto da persona consistente, coloque o rosto de referência em primeiro lugar. [cookbook high fidelity](https://developers.openai.com/cookbook/examples/generate_images_with_high_input_fidelity)
  - `input_fidelity` (`high`/`low`) vale só para gpt-image-1/1.5. **No `gpt-image-2`, omita esse parâmetro**, porque o modelo já usa alta fidelidade. ⚠️ Não confirmei o comportamento no 2.5. [ref edit](https://developers.openai.com/api/reference/resources/images/methods/edit)
- Também dá para gerar imagens pela Responses API, com a ferramenta `image_generation`. Isso é útil para edição multi-turn.

### Tamanhos
- `gpt-image-2`: aceita resolução livre. Os tamanhos comuns são `1024x1024`, `1536x1024` e **`1024x1536` (retrato 2:3)**. O 2K (até 2560x1440) é marcado como experimental. [buildfastwithai](https://www.buildfastwithai.com/blogs/chatgpt-images-2-0-gpt-image-2-2026) ⚠️ Os tamanhos 1792 citados em alguns blogs parecem herdados do DALL·E 3.
- GPT Image 2.5: inclui `1024x1536`, `2048x2048`, `2048x1152`, `3840x2160` e **`2160x3840` (4K retrato 9:16)**. Largura e altura precisam ser múltiplos de 16, com proporção entre 1:3 e 3:1. [fal: 2.5 vs 2](https://fal.ai/learn/devs/gpt-image-2-5-vs-gpt-image-2) · [omniakey](https://omniakey.com/blog/gpt-image-2-5-vs-gpt-image-2)
- **Para Reels 9:16:** gere em `1024x1536` e faça crop/outpaint para 1080x1920. No 2.5 também dá para pedir um tamanho 9:16 direto, por exemplo `1088x1920` ou `2160x3840` (⚠️ ainda não testei).

### Qualidade
- `gpt-image-2`: `low`, `medium`, `high` e `auto`.
- GPT Image 2.5: `auto`, `low`, `medium`, `high`, **`xhigh`** e **`max`**. Os rótulos foram renomeados, então compare pelo preço e não pelo nome. [fal](https://fal.ai/learn/devs/gpt-image-2-5-vs-gpt-image-2) · [tokencost](https://tokencost.app/blog/gpt-image-2-5-pricing-cost-per-image)

### Preço
O preço é por tokens: entrada de texto US$5/1M, entrada de imagem US$8/1M e saída de imagem US$30/1M. A tabela vale igual para gpt-image-2, 2.5-flare e 2.5-sunburst. [OpenAI pricing](https://developers.openai.com/api/docs/pricing) · [eesel](https://www.eesel.ai/blog/chatgpt-images-2-5-pricing)

Custo aproximado por imagem no `gpt-image-2` [buildfastwithai](https://www.buildfastwithai.com/blogs/chatgpt-images-2-0-gpt-image-2-2026):

| Tamanho | low | medium | high |
|---|---|---|---|
| 1024x1024 | ~US$0,006 | ~US$0,053 | ~US$0,211 |
| 1024x1536 (retrato) | ~US$0,005 | ~US$0,041 | ~US$0,165 |

⚠️ Os blogs divergem bastante nesses valores. Imagens de referência em `edit` somam tokens de entrada de imagem. No 2.5, em 1024², os blogs citam ~US$0,013 (medium), ~US$0,053 (high) e ~US$0,211 (max). Ou seja, o "max" do 2.5 custa o mesmo que o "high" do 2. [atlascloud](https://www.atlascloud.ai/blog/tips/gpt-image-2.5-api-cost)

### Limites de taxa (gpt-image-2, por organização)
Cada tier tem limite de TPM (tokens por minuto) e IPM (imagens por minuto):

| Tier | TPM | IPM |
|---|---|---|
| 1 | 100k | **5** |
| 2 | 250k | 20 |
| 3 | 800k | 50 |
| 4 | 3M | 150 |
| 5 | 8M | 250 |

[wavespeed](https://wavespeed.ai/blog/posts/gpt-image-2-rate-limits-2026/) · [model page](https://developers.openai.com/api/docs/models/gpt-image-2). ⚠️ Fonte secundária: confira em Settings > Limits. No Tier 1, faça as chamadas em série com backoff para o erro 429.

### Moderação e pessoas realistas
- O parâmetro `moderation` aceita `auto` (padrão) ou `low`. O `low` só relaxa o filtro, não o desliga. [ref generate](https://developers.openai.com/api/reference/resources/images/methods/generate)
- Bloqueios comuns (erro `moderation_blocked`): conteúdo sexual, menores em contexto fotorrealista, **figuras públicas reais (nomes de celebridades ou políticos)**, IP protegida e estilo de artistas vivos. [apiyi](https://help.apiyi.com/en/gpt-image-2-moderation-blocked-error-prompt-optimization-en.html)
- Pessoas fictícias fotorrealistas (personas de IA) são permitidas. Editar fotos de pessoas reais pode ser recusado.
- ⚠️ Há relatos de recusas em excesso no gpt-image-2, mesmo com `moderation: low`, para prompts que funcionam no ChatGPT. [community](https://community.openai.com/t/api-issue-moderation-over-refusals-on-gpt-image-2-with-moderation-low-where-chatgpt-always-succeeds/1388964)
- Na prática: trate a recusa como um caminho normal do código, reescreva o prompt e tente de novo.

---

## 2. Higgsfield API + Seedance 2.5

### API pública
✅ Existe uma API REST pública e pay-as-you-go (sem assinatura), separada dos planos do app.
- Console: `console.higgsfield.ai`. Playground: `open.higgsfield.ai`.
- Docs: [docs.higgsfield.ai](https://docs.higgsfield.ai/docs).
- SDKs oficiais: [Python](https://github.com/higgsfield-ai/higgsfield-client) e [Node/TS](https://github.com/higgsfield-ai/higgsfield-js).

### Autenticação
- ✅ A credencial tem um **key ID e um secret**. Header:
  `Authorization: Key ${HF_API_KEY_ID}:${HF_API_KEY_SECRET}`
  [docs auth](https://docs.higgsfield.ai/docs/authentication)
- Só use do lado do servidor, nunca no browser.

### Fluxo assíncrono
- Base URL: `https://api.higgsfield.ai`. [docs how-it-works](https://docs.higgsfield.ai/docs/how-to/introduction)
1. `POST` no endpoint do modelo com o JSON. A resposta traz um `request_id` e um `status_url`.
2. Faça **polling** em `GET /requests/{request_id}/status` **ou** passe uma **URL de webhook**.
3. Quando o status for `completed`, baixe o resultado.

### Caminhos de modelo
Vistos no playground:
- `bytedance/seedance-2.5/text-to-video` [console](https://console.higgsfield.ai/models/bytedance/seedance-2.5/text-to-video/playground)
- `bytedance/seedance-2.5/reference-to-video` [open](https://open.higgsfield.ai/models/bytedance/seedance-2.5/reference-to-video/playground)
- `kling-video/v3.0/std/text-to-video` [open](https://open.higgsfield.ai/models/kling-video/v3.0/std/text-to-video/playground)

Outros citados: `/kling-video/v3.0/pro/text-to-video` e `/kling-video/v3.0/4k/image-to-video`. ⚠️ Confirme o caminho exato e o schema na página de cada modelo nas docs.

### Preço
É cobrado em **US$**, com saldo pré-pago e cobrança por geração. Existe um endpoint de *estimate* que mostra o custo antes de rodar. [layer3labs](https://www.layer3labs.io/guides/higgsfield-api) · [higgsfield blog](https://higgsfield.ai/blog/best-ai-video-generation-apis)

| Modelo | Preço |
|---|---|
| Seedance 2.5 | a partir de **~US$0,0738/s** (um clipe de 15s sai por ~US$1,11) |
| Kling 3.0 | ~US$0,112/s |
| Kling 3.0 Motion Control | Pro ~US$0,084/s, Std ~US$0,063/s ⚠️ fonte de terceiro, cita 50% de desconto temporário ([evolink](https://evolink.ai/kling-v3-motion-control)) |

- ⚠️ As fontes divergem: uma diz que os fundos expiram em 1 ano, outra diz que não há créditos que expiram.
- Os planos do **app** (US$15, 39 e 99/mês, em créditos) são separados da API. [layer3labs pricing](https://www.layer3labs.io/guides/higgsfield-ai-pricing)

### Seedance 2.5
Anunciado em 23/06/2026 e lançado em 31/07/2026. [TNW](https://thenextweb.com/news/bytedance-seedance-2-5-ai-video-4k-30-seconds) · [higgsfield blog](https://higgsfield.ai/blog/seedance-2-5-on-higgsfield-2026)
- ✅ **Até 30s** em um único clipe contínuo. O Seedance 2.0 ia de 4s a 15s.
- ✅ **Omni-reference**: até 50 referências (30 imagens, 10 vídeos e 10 áudios).
- ✅ Áudio nativo sincronizado (10+ idiomas).
- Também faz edição e extensão de vídeo, além de edição por região.
- ✅ Controle de primeiro e último frame e de múltiplos keyframes. ⚠️ Uma fonte diz que, no Higgsfield, o modo 2.5 **não tem papel `start_image`/`end_image`** e fica limitado a **720p**. A ByteDance anunciou "4K nativo". Na prática, o modo first/last frame pode exigir o Seedance 2.0 ou o modo reference. [SKILL.md OSideMedia](https://github.com/OSideMedia/higgsfield-ai-prompt-skill/blob/main/skills/higgsfield-seedance-2-5/SKILL.md)
- Seedance 2.0, como referência: 480p/720p, 4–15s, até 9 imagens de referência. [fal](https://github.com/fal-ai/seedance-2.0-api)

---

## 3. Instagram API: publicação de Reels

### Requisitos
- A conta precisa ser **profissional** (Business ou Creator). Há dois caminhos:
  - **Instagram API with Instagram Login**: não exige Página do Facebook. Recomendado para publicar, ver insights e gerenciar comentários. Escopos: `instagram_business_basic` e `instagram_business_content_publish`. [Meta docs](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/)
  - **Instagram API with Facebook Login**: exige a conta IG vinculada a uma Página. Necessário para hashtag search e product tags. [overview](https://developers.facebook.com/docs/instagram-platform/overview/)
- Para as suas 3 contas próprias, o app pode ficar em modo dev, com as contas como testers. Para operar contas de terceiros, precisa de App Review.

### Fluxo
1. `POST /{ig-user-id}/media` com `media_type=REELS` e `video_url` público, mais `caption`, `share_to_feed`, `cover_url` ou `thumb_offset`, `audio_name`, `collaborators` e `location_id`.
   - Sem URL pública: use `upload_type=resumable` e envie o binário para `https://rupload.facebook.com/ig-api-upload/{api-version}/{container-id}`.
   - [postproxy](https://postproxy.dev/blog/instagram-reels-api-publishing-guide/) · [IG User Media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/)
2. Faça polling em `GET /{container-id}?fields=status_code` até receber `FINISHED`. Os outros estados são `IN_PROGRESS`, `ERROR`, `EXPIRED` (o container expira em 24h) e `PUBLISHED`. Recomendação: 1 chamada por minuto, por até 5 minutos.
3. `POST /{ig-user-id}/media_publish` com `creation_id={container-id}`. [dev.to](https://dev.to/alex97po/instagram-container-based-publishing-the-3-step-dance-for-reels-stories-carousels-4e26)

### Especificação do vídeo
[IG User Media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/) · [postproxy](https://postproxy.dev/blog/instagram-reels-api-publishing-guide/)
- Container MOV ou MP4 (moov atom no início, sem edit lists).
- Vídeo: H.264 ou HEVC, progressivo, closed GOP, 4:2:0, 23–60 fps, até 1920 px de largura, VBR de até 25 Mbps.
- Áudio: AAC, até 48 kHz, mono ou estéreo, 128 kbps.
- Duração de **3s a 15min** e arquivo de até **300 MB**.
- Para entrar na **aba Reels**, use **9:16 e 5–90s**. Fora disso o vídeo é publicado como vídeo comum. ⚠️ Esse corte é de fonte secundária.
- Alvo recomendado: **1080x1920, H.264 High, 30 fps, AAC 48 kHz, faststart**.

### Limite de publicação
- ⚠️ Os números conflitam: a doc atual da Meta fala em **100 posts publicados via API por 24h (janela móvel)** num trecho e em 50 noutro. Um carrossel conta como 1 post. [Meta content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/) · [keyapi](https://www.keyapi.ai/blog/instagram-api-rate-limits-2026-what-changed-and-how-to-adapt/)
- Consulte o limite real em `GET /{ig-user-id}/content_publishing_limit?fields=config,quota_usage`.
- Para poucos posts por dia por conta, nenhum dos dois números é problema.

### Áudio e música
- ✅ A API **não dá acesso à biblioteca de músicas licenciadas nem aos áudios em alta** do Instagram. O áudio precisa vir **embutido no MP4**. [postproxy](https://postproxy.dev/blog/instagram-reels-api-publishing-guide/)
- `audio_name` só renomeia o áudio original, e isso só pode ser feito uma vez.
- Opções para usar áudio em alta:
  - (a) Usar música royalty-free ou original embutida no vídeo.
  - (b) Publicar como rascunho ou manualmente pelo app e trocar o áudio. Não existe "rascunho" via API.
  - (c) Usar ferramentas de parceiros. ⚠️ A existência de "Instagram Music API" em terceiros, como bundle.social, não é API oficial da Meta.
- Usar música comercial sem licença embutida no vídeo pode levar a mute ou bloqueio.

### Rotulagem de IA
- ⚠️ **Não encontrei parâmetro oficial documentado pela Meta.** Um agregador (Ayrshare) expõe `isAIGenerated`, que aplica o rótulo "AI info". Não está claro se ele mapeia para um campo oficial da Graph API. [Ayrshare](https://www.ayrshare.com/docs/apis/post/social-networks/instagram)
- A Meta aplica "AI info" automaticamente quando detecta metadados C2PA/IPTC, que as imagens da OpenAI incluem.
- Desde 04/05/2026 existe o rótulo de perfil **"AI Creator"**, opcional e ativado no app. Vale considerar para personas de IA. [SocialMediaToday](https://www.socialmediatoday.com/news/instagram-adds-ai-creator-labels/819267/)

### Agendamento e Trial Reels
- ⚠️ As fontes conflitam sobre agendamento nativo de Reels via API. A maioria diz que a Graph API não tem `scheduled_publish_time` para IG e que o agendamento fica por sua conta (cron + publish). [postproxy](https://postproxy.dev/how-to/schedule-instagram-reels/) Assuma que você controla o timer. Lembre que o container expira em 24h, então crie-o perto da hora de publicar.
- ✅ **Trial Reels** (mostrados só para não seguidores) são suportados via `trial_params`, por exemplo `{"graduation_strategy":"MANUAL"}` ou `"SS_PERFORMANCE"`. [Meta content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/) · [postfa.st](https://postfa.st/blog/instagram-trial-reels)
- Token: o long-lived token vale 60 dias e precisa ser renovado (refresh) antes de expirar.

---

## 4. Claude API para roteiros (baixa prioridade)
- Convenção de IDs: `claude-{família}-{versão}` com hífen, sem data nos modelos recentes. Exemplos: `claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5`. [anthropics/skills models.md](https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/models.md)
- Lançamentos de 2026 citados por fontes secundárias: Sonnet 5 (30/06), Opus 5 (24/07) e Opus 5.5 (22/09/2026, ID `claude-opus-5-5`). [hidekazu-konishi timeline](https://hidekazu-konishi.com/entry/anthropic_claude_model_release_timeline.html) ⚠️ Confirme com `GET /v1/models` antes de fixar o ID.
- Para gerar roteiros curtos em lote, um Sonnet costuma ter o melhor custo-benefício. Use structured outputs (JSON) e prompt caching no system prompt de cada persona.

---

## 5. Orquestração: GitHub Actions e alternativas

### GitHub Actions
- **Cron:** intervalo mínimo de 5 min, sempre em UTC. Atrasos de dezenas de minutos são comuns em horários de pico, e execuções podem ser descartadas. Use minutos "quebrados" (ex.: `17 * * * *`) e tolere atraso. [cronbuilder](https://cronbuilder.dev/blog/github-actions-cron-schedule.html)
- **Desativação automática:** em **repositórios públicos**, workflows agendados são desativados após 60 dias sem atividade no repo. Commits de estado contam como atividade. [cronuru](https://cronuru.com/guides/github-actions-scheduled-workflows)
- **Minutos:** repositório público é ilimitado. Repositório privado tem 2.000 min/mês no Free e 3.000 no Pro.
  - Desde 01/01/2026, Linux custa US$0,006/min.
  - A cobrança de self-hosted foi adiada por tempo indefinido.
  - [cicdcost](https://cicdcost.com/github-actions-pricing) · [northflank](https://northflank.com/blog/github-pricing-change-self-hosted-alternatives-github-actions)
  - Um job dura no máximo 6h, mas o pipeline faz polling longo de vídeo. Para não queimar minutos, prefira webhook + `workflow_dispatch`/`repository_dispatch`.
- **Artifacts:** retenção padrão de 90 dias. Configurável de 1–90 dias em repositório público e de 1–400 em privado.
  - Desde **01/10/2026**, checks, runs e statuses também seguem essa retenção. [GitHub changelog](https://github.blog/changelog/2026-10-01-actions-retention-now-covers-checks-runs-and-statuses/) · [upload-artifact](https://github.com/actions/upload-artifact)
  - Os MP4s não devem ir para o git. Use artifact, release asset ou storage externo (R2/S3). O Instagram precisa de `video_url` público, ou então use upload resumable.
- **Secrets:** ficam em repository ou environment secrets e são lidos via `${{ secrets.X }}`. Exemplos: `OPENAI_API_KEY`, `HF_API_KEY_ID`, `HF_API_KEY_SECRET`, tokens IG por conta.
- **Commitar estado no repo:**
  - Dê `permissions: contents: write` ao `GITHUB_TOKEN` e use `git commit` + `git push` no job.
  - Use `concurrency:` para evitar corridas.
  - Push feito com `GITHUB_TOKEN` não dispara outros workflows (isso evita loops).
- Atenção: em repositório público, os logs e o estado commitado ficam visíveis. **Use repositório privado.**

### Alternativas
- **n8n Cloud:** o Starter custa ~€20/mês no plano anual (€24 no mensal), com 2.500 execuções/mês. Self-host é grátis, pagando só o VPS. [goodspeed](https://goodspeed.studio/blog/n8n-pricing) · [coworker](https://coworker.ai/blog/n8n-pricing)
- **Make.com:** cobra em créditos (antigas "operations"). No plano anual com 10k créditos/mês: Core US$9, Pro US$16, Teams US$29. No mensal: US$10,59, 18,82 e 34,12. [latenode](https://latenode.com/blog/make-com-pricing)
- **Para este caso:** o GitHub Actions em repositório privado deve ficar dentro dos 2.000 min/mês grátis, desde que os jobs sejam curtos e a espera pela geração de vídeo use webhook ou jobs curtos de polling.

---

## Pontos a validar manualmente
1. Limite de publicação do IG (50 ou 100): consultar `content_publishing_limit`.
2. Schema exato dos endpoints Seedance 2.5 e Kling no Higgsfield, se o 2.5 aceita first/last frame e qual a resolução máxima via API.
3. Seu tier de rate limit na OpenAI. No Tier 1 são 5 imagens/min.
4. Se existe hoje um campo oficial de rótulo de IA na Graph API.
5. Se a expiração do saldo da API Higgsfield é de 1 ano.
