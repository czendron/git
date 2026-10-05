---
name: usina
description: Roda um ciclo ("tick") da Usina de Virais — a fábrica de Reels dos personagens de IA do Caio (Gersinho, Marlene, Wanderley). Use quando uma Routine disparar "rode a usina", ou quando o Caio pedir "roda a usina", "gera os vídeos do dia", "tick da usina", "o que está esperando aprovação". Executa o plano determinístico do pipeline (roteiro → storyboard → frames → vídeo → revisão → pacote), revisa imagens e vídeos pela rubrica, sincroniza o painel e faz commit. Nunca publica nada.
---

# Usina de Virais: um ciclo

Você é o operador de produção. O **código decide o que fazer** (`python -m pipeline plan`); você executa e registra.
Ata do conselho: `usina/docs/conselho-ata.md`. Método de qualidade: `usina/playbook/seedance-master.md`.

## Regras que nunca quebram (ata D8)
- **Nunca** publicar, agendar ou apagar posts; nunca mandar DM, comentar, seguir ou curtir; nunca mexer em bio ou config de conta.
- Nunca gerar pessoa real reconhecível; nunca remover metadados de IA; nunca ligar as páginas ao Papo de Gato; nunca tocar em cripto.
- Nunca passar do teto (`usina/budget.yaml`). Se o plano disser `blocked`, pare aquela linha.
- Se existir `usina/PAUSE`, só sincronize o painel e saia.
- Páginas com `status: rascunho` não geram nada.

## 0. Preparar (uma vez por sessão)
```bash
cd usina
python3 -m venv .venv 2>/dev/null; .venv/bin/pip install -q openai pyyaml pillow pytest
alias P=".venv/bin/python -m pipeline"
.venv/bin/python -m pytest -q tests   # se falhar, PARE e reporte
```
Referências locais: `P pages`. Se aparecer FALTA, rode `P fetch-refs <página>`. Se o download for bloqueado pela rede, use as imagens pelo Higgsfield (`--provider higgsfield`) e anote no relatório.

## 0.5 Restaurar a mídia (out/ não vai para o git)
`P media-status`. Para cada item em `restore`: `Artifact(action="read", url=<painel>, path=<asset_id>)` → `P media-restore <ref> <key> --file <arquivo salvo>`. Sem isso, frames e vídeo de itens em andamento não existem nesta sessão.

## 1. Trazer as decisões do Caio do painel
Painel: https://claude.ai/artifact/2yF5cU2n9MDbWtQHFj5p4c
1. `ArtifactData list` da coleção `decisoes` (todas) → salve em `out/panel/decisoes.json`.
2. `P panel-apply out/panel/decisoes.json` → devolve `applied_ids` (aplicadas, obsoletas e inválidas; rodar de novo não reaplica).
3. Para cada id aplicado: `ArtifactData update` em `decisoes/<id>` com `{"applied": true}` (use o `version` lido).

## 2. Plano
`P plan` → JSON com `actions`, `waiting_caio` e `notes`. Execute **na ordem**, no máximo 12 ações por ciclo:

| `do` | O que fazer |
|---|---|
| `new_ideas` | Escolha ideias: coleção `ideas` do painel (radar), `docs/roteiros-crossover.md` ou ideias suas no formato da casa, nunca repetidas (`P memory <página>`). Crie com `P new <página> "título" --idea "..."`. |
| `write_script` | Leia `prompts/script.md` (as 8 leis), `pages/<página>/page.yaml`, `prompts/examples/gersinho-busao.json` (modelo), `playbook/falhas.md` e `P memory`. Escreva o JSON em `out/scripts/<id>.json` e rode `P save-script <ref> <arquivo>`. **Se o lint reprovar, corrija e salve de novo** (até 3 vezes; depois, `P discard`). |
| `run` | Rode o `cmd` como está. Se `image` falhar por rede ou chave da OpenAI e `switches.image_fallback_allowed` estiver `true`, refaça com `--provider higgsfield`, execute a chamada MCP que ele imprimir e rode o `record-image` indicado (frames saem em 2 passos: o B é edição do A; o plano pede o 2º). Com o fallback desligado, o comando recusa: anote o bloqueio. |
| `review_image` | Abra a(s) imagem(ns) com **Read** junto com `pages/<p>/refs/rosto.png` e `silhueta.png`, aplique a rubrica (`prompts/review_storyboard.md` ou `review_frames.md`) com rigor e registre com `P review ... pass|fail --notes "<gate/nota> <evidência> [categoria]"`. Na dúvida, **reprove**: imagem custa centavos e vídeo custa dólares. |
| `video_submit` | `P video-request <ref>`. Se `ready: false`: suba cada arquivo (`mcp__Higgsfield__media_upload` → `curl -X PUT --data-binary @arquivo '<upload_url>'` → `mcp__Higgsfield__media_confirm`) e rode `P record-upload <ref> <key> --hf-id <id>`; depois peça o video-request de novo. Com `ready: true`: chame `mcp__Higgsfield__generate_video_batch` com os `requests` exatos (se vier recomendação de preset, reenvie com `declined_preset_id`). Por fim, `P record-video <ref> --job <job_id> --credits <estimativa>`. |
| `video_poll` | `mcp__Higgsfield__jobs_wait` (timeout 15). Com o job completo: `P record-video <ref> --url <result_url>`. Job `failed`/`nsfw`/`cancelled`: `P record-video <ref> --failed "motivo"` (volta para frames e conta como tentativa). Senão, siga em frente; o próximo ciclo checa. |
| `review_video` | Abra com Read a folha (`*-sheet.jpg`), a folha do gag (`*-gag.jpg`) e o último frame, aplique `prompts/review_video.md` (12 portões e 9 notas) e veja os `cuts` no item. Registre com `P review ... video pass|fail --notes ...`. Na reprovação, decida a próxima tentativa pela triagem C6, mudando **uma** variável: `--no-grid`, `--repair "..."` ou reescrever o roteiro. |
| `discard` / `blocked` | Rode o comando de descarte ou anote o bloqueio no relatório. |

**Trend (format `trend`, motion control):** o roteiro segue `prompts/examples/gersinho-trend-calcadao.json`. Sem vídeo-fonte, o item fica em `waiting_caio` com a etapa `fonte`; o Caio (ou você, com um .mp4 da motion library do Higgsfield) roda `P motion-source <ref> --file fonte.mp4`. O frame do personagem é edição do 1º frame da fonte (`image ... frames`). No `video-request`, suba o frame (`record-upload ... start`) e a fonte como vídeo (`media_upload` type video → `motion-source <ref> --hf-id <id>`).

`waiting_caio` não é ação sua: só lista o que espera o Caio no painel.

## 3. Painel
1. **Arquivar e mostrar:** `P media-status` → para todo arquivo em `upload` (storyboard, frames, vídeo, folhas, último frame), suba com a ferramenta **Artifact** (`url` do painel, `asset: true`, `file_paths: [...]`, até 25 por chamada; vídeo .mp4 vai junto) e grave cada id com `P panel-asset <ref> <key> /_blob/<id>`. O asset é ao mesmo tempo a imagem da Caixa e o arquivo permanente da mídia. Rode `media-status` de novo: `upload` tem que ficar vazio.
2. `P panel-export` → `out/panel/batch.json` e os lotes `out/panel/batch-NN.json` (até 50 cada). Grave cada lote com `ArtifactData batch`. Documento já existente pede `if_version`: leia antes com `list` e passe a versão.
3. Para vídeo, o painel mostra o link `videoUrl` do Higgsfield.

## 4. Fechar
```bash
cd .. && git add usina && git commit -m "usina: tick $(date -u +%FT%H:%MZ)" && git push -u origin HEAD
```
Os arquivos de mídia (`usina/out/`) ficam fora do git. Relatório final em até 10 linhas:
- o que foi gerado e quanto custou (`P ledger`, `P status`);
- o que espera o Caio;
- erros e bloqueios;
- falhas novas registradas em `playbook/falhas.md`.

## Quando algo dá errado
- 3 erros seguidos no mesmo ciclo: `P pause "motivo"` e reporte.
- Aproveitamento baixo (`notes` do plano): não gere vídeo; releia `playbook/falhas.md` e proponha a mudança de prompt no relatório.
- Nunca "conserte" o teto de gasto, as regras ou a ata por conta própria.
