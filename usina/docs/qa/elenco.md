# Elenco recorrente (06/10/2026)

**Por quê:** figurante com rosto, gerado só pelo texto, sai "gente genérica de IA" e muda de cara a cada vídeo. Quem volta em vários vídeos ganha uma ficha própria, aprovada uma vez e reusada sempre.

## O que é
- Um arquivo por pessoa: `pages/<página>/cast/<cast_id>.yaml` com `name`, `look` (inglês, vai no prompt), `pronoun`, `role`, `status` (`rascunho` | `aprovado`) e `refs` (`sheet`, `higgsfield_id`, `asset`/`url` do painel).
- Semeado no Gersinho: **Seu Tadeu Carimbo** (o tio do crossover, ata D6 e `roteiros-crossover.md` item 5), **Dona Neide** (feirante), **Seu Juvenal** (cobrador do busão) e **Kelly da Padaria**. Todos fictícios, sem semelhança com gente real; todos em `rascunho`, sem ficha.
- A ficha fica em `pages/<p>/cast/sheets/` (fora do git, como `refs/`) e no asset store do painel.

## Regra de uso ("às vezes")
- Passante de fundo: só no prompt (`extras_tasks`).
- Figurante em destaque (rosto visível, em 2+ estágios ou perto da câmera): ganha ficha. Do elenco com `cast_id`; de uma vez só com `look` (a ficha avulsa da rodada 7).
- No roteiro: `counterpart.cast_id` ou `en.featured_extras: [{cast_id | who + look, position, task}]`.
- O lint avisa contraparte humana ou figurante em destaque sem `cast_id` nem `look` e recusa `cast_id` inexistente.

## Fluxo
1. O `plan` vê um item que usa alguém do elenco sem ficha aprovada e pede `image <página> cast-sheet <cast_id>` (OpenAI, ficha C1 2x2, sem a ref do protagonista). Dois itens com a mesma pessoa: uma ação só.
2. O ciclo sobe a ficha (`media-status` → `cast asset`); o card **Elenco** aparece na Caixa. O Caio aprova (ou pede para refazer, com motivo: a nota entra no próximo prompt). Pelo terminal: `cast approve <p> <id> [--reject --notes]`.
3. Aprovada, a ficha entra:
   - nos frames A/B (depois da ficha avulsa, com a linha "X is defined only by image N");
   - no `video-request` (`image_references`, com a linha de papel no ACTIVE REFERENCES);
   - na trend: troca por alguém do elenco vira image 4, 5… na edição do 1º frame e vai ao Genjutsu depois do rosto e da silhueta;
   - no gag, quando a pessoa está no quadro do gag.
4. Ficha sem id no Higgsfield: `upload_first` com a chave `cast:<id>` → `record-upload <ref> cast:<id> --hf-id <id>` (o id fica no yaml e serve a todo vídeo).

## Comandos
`cast list|new|show|approve|asset|restore <página> [<cast_id>]` · `image <página> cast-sheet <cast_id>`

## Limites de referências
- OpenAI `images.edit`: até 16 imagens (GPT Image 2, vendor/higgsfield-ai-prompt-skill). O pipeline recusa com erro claro acima disso.
- Vídeo no Higgsfield: até 9 imagens por pedido. O Seedance 2.5 aceita 30 no `omni_reference`, mas o mapa `@Image N` dos prompts segue o limite de 9 do sistema de @ do 2.0, o único testado; o Genjutsu não documenta limite e fica no mesmo teto.

## Painel
- Aba **Elenco**: o elenco recorrente por página (ficha, estado, onde é usado), acima da lista antiga de personagens principais, que segue igual.
- Caixa: card **Elenco: ficha nova**, com o mesmo Aprovar/Refazer (coleção `decisoes`, `stage: "elenco"`, `ref: "<página>/<cast_id>"`).

## Limites
- Uma ficha avulsa por item (a 1ª pessoa sem `cast_id`); o resto do elenco não tem esse limite, só o de referências.
- A ficha do elenco não passa pelo revisor de IA antes do Caio; o G11 confere nos frames.
- Nenhuma ficha foi gerada de verdade (só mock): sem chamadas à OpenAI nem ao Higgsfield.
