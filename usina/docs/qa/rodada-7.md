# QA rodada 7 (05/10/2026)

Escopo:
- trava de gasto no Higgsfield (o Caio, em 05/10: "não gaste mais créditos do Higgsfield");
- ficha da contraparte humana no quadro (a lacuna de `docs/qa/lint-tutoriais.md`, "Limites": B4.11 pede "ficha própria antes de qualquer vídeo").

Nada foi gerado: zero chamadas ao Higgsfield e à OpenAI (só mock). Testes: **187 passando** (173 antes + 14 em `tests/test_qa_rodada7.py`). O `index.html` e o `playbook/` não mudaram.

## 1. Trava do Higgsfield

`budget.yaml` ganhou `switches.higgsfield_spend_enabled: false`. Sem a chave, vale travado (falha fechada). Só o Caio muda.

| Onde | Com a trava |
|---|---|
| `video-request` (próprio, trend/Genjutsu, `--gag`, `--repair`, `--no-grid`) | Recusa antes de tudo, com a mensagem que nomeia o interruptor. Não imprime pedido. |
| `image ... --provider higgsfield` (storyboard, frames, as 4 opções da trend) e `sheet --provider higgsfield` | Recusam, mesmo com `image_fallback_allowed: true`. |
| `budget.can_spend_higgsfield` | Devolve "travado" primeiro: qualquer caminho futuro que consulte o teto também para. |
| `plan` | `blockers` e uma nota `BLOQUEIO`. Item pronto para vídeo, gag ou frame B pelo Higgsfield vira `blocked` (o frame B sugere refazer pela OpenAI). Não pede `check_balance`. |
| `status --morning` | Linha própria em "Bloqueios". |
| SKILL | Regra nova em "Regras que nunca quebram": nenhuma ferramenta paga do Higgsfield, `video_analysis_create` incluída, e só o Caio muda o interruptor. |

Leituras seguem: `balance`, `jobs_wait` e `record-video` de um job já pago, `show_*`, `transactions`. O `media_upload` não gasta crédito e ficou liberado no código, mas o SKILL diz para não subir nada, já que o envio que usaria o arquivo está travado.

## 2. Ficha da contraparte humana

**Quando:** a contraparte é humana e aparece com rosto no quadro, no clipe ou no gag da trend (`lint.sheet_counterparts`). A contraparte fora do quadro (B4.10), o bicho e o objeto (saco de pancada, poste…) não ganham ficha. Quando o substantivo engana, `counterpart.kind` decide.

**Passos:**
1. `image <ref> counterpart` gera a ficha C1 2x2 pela OpenAI (`images.generate`, sem a ref dele, mock nos testes). Pessoa fictícia, de rosto comum e não reconhecível, sem ser sósia de ninguém. É de propósito outra pessoa: outro rosto, outra idade e outro cabelo, sem o topete e sem o figurino dele. A aparência vem de `counterpart.look`, campo novo no `script.md`. Fica em `item.counterpart` e no livro-caixa como `image_counterpart`.
2. O `plan` pede a ficha depois do storyboard aprovado e antes dos frames. Na trend, ela vem antes das 4 opções, se o gag tiver uma pessoa no quadro. O `image frames` recusa enquanto a ficha não existir.
3. **Frames A/B:** a ficha entra como imagem a mais (A: rosto, silhueta, [storyboard], ficha; B: frame A, rosto, silhueta, ficha). Uma linha diz que só ela define essa pessoa. Sem figurantes, "only person" vira "Besides <ela>, he is the only person". No fallback Higgsfield, ela vai como `image_references` (pede `record-upload <ref> counterpart`).
4. **`video-request`:** a ficha é mais um `image_references`, depois da grade. No ACTIVE REFERENCES ganha uma linha própria: "@Image N (the 4-panel reference sheet of another person on grey) is <NOME>'s reference … nothing of GERSINHO comes from @Image N". O N acompanha o `--no-grid`. No `--gag` da trend, ela entra como @Image 3.
5. **Mídia:** chave `counterpart` no `media-status`, `panel-asset` e `media-restore`, com conserto próprio em `lost`.
6. **Revisão:** `review_frames.md` ganhou o G11: ela bate com a ficha e não é sósia dele. A ação de `review_image` traz a ficha no `file`.
7. Reescrever o roteiro com outra contraparte (ou sem nenhuma) descarta a ficha velha.

**Limites:** uma ficha por item, só a da 1ª contraparte. Com duas pessoas no quadro, a 2ª segue sem ficha (há aviso). A ficha não tem portão de QA próprio: quem confere é o G11, nos frames. A ficha só sai pela OpenAI.
