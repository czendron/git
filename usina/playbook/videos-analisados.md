# Tutoriais assistidos (análise cena a cena do Higgsfield, com transcrição) · 05/10/2026

Fonte: `video_analysis` do Higgsfield nos tutoriais que a pesquisa (`creators-techniques.md`) indicou. Cada linha abaixo vem do áudio ou da tela do vídeo, não de resumo de busca.

## 1. "I Tested Seedance 2.5's 30-Second Mode — Here's the Prompt Structure" (BIBO) · https://www.youtube.com/watch?v=i_IdTsGm-Bk
- **Mais detalhe não resolve; estrutura clara resolve.** Um prompt de 1.300 palavras com 22 planos "crashed and burned": rostos tremendo e inconsistentes, quase tudo inutilizável. O que funcionou foi refazer com **mapa de referências primeiro** (ficha do personagem, props-chave e referências de cena), e assets, planos, ações e tempo formando "uma cadeia legível".
- **Densidade de ação:** um plano com 2 s que precisava de 4 fez o Seedance **forçar um corte cedo** para caber as instruções. A regra é escrever o tempo que a ação real leva e incluir as regras de ritmo junto do prompt. Confirma as regras 4 e 5 do playbook.
- **Uma tomada contínua de 30 s** ("one take": se arrumar no espelho, pôr o capacete, ir até o carro, sair dirigindo) funciona com estrutura simples: **Asset References → Narrative → Ambience**.
- **Moderação de rosto no Seedance 2.5:** o filtro bloqueia gerações inteiras. O contorno é **gerar uma ficha nova e neutra** e rodar **um teste de 4 s**: se passar sem flag, segue.
- **Ensaio barato:** testar o prompt antes num modelo mais barato (ela usa Wan 3.0, cerca de 1/5 do preço por segundo). "Wan é o ensaio, Seedance é o take final." Para nós: o draft de estrutura em 480p (playbook F) ou Kling 3.0 std.
- No 30 s, todas as decisões de direção ficam com você: o modelo não salva o planejamento ruim.

## 2. "Kling Motion Control 3.0 Full Tutorial" (The Creator Lab) · https://www.youtube.com/watch?v=Utono2euM24
- O MC 3.0 melhora sobretudo a **consistência e qualidade do rosto** em movimento complexo; agora tem lip-sync e expressão facial.
- **Standard vs Pro:** os dois saem em 1080p. O Standard serve para movimento simples (cabeça sem giros rápidos); o Pro, para movimento rápido ou complexo.
- **Elements (Kling):** sobe a imagem do personagem e gera **3 ângulos novos** para dar mais dados. Ajuda quando há giro de cabeça; em 90% dos vídeos simples não precisa.
- **A técnica que mais importa para trends, a imagem do personagem feita a partir do 1º frame do vídeo-fonte:**
  1. Pause o vídeo de dança no primeiro frame e tire um print.
  2. Edite esse print no gerador de imagem (ele usa Nano Banana Pro; para nós, GPT Image 2.5 `images.edit`).
  3. Prompt curto: "Ultra-realistic, extremely high detail, no smoothing, no CGI look, no stylization. Replace the man with [personagem]. Must look like a real behind-the-scenes photo of [personagem] inside the original scene." Proporção 9:16. Peça 4 variações e escolha uma.
  4. Use essa imagem + o vídeo-fonte no Motion Control.

  Assim **pose, enquadramento e cenário batem 100% com a fonte**. É a exigência do C5 ("mesma pose e enquadramento do primeiro frame da fonte") resolvida sem esforço.
- **Templates de dança em alta:** as plataformas oferecem bibliotecas de vídeos virais prontos para MC. O Higgsfield tem a **motion library** dentro do Genjutsu (ver 3).
- **Acabamento:** upscale com Topaz depois de aprovado (só nos vencedores, como decidido na ata D5).

## 3. "Higgsfield Genjutsu Tutorial: Replace Characters And Swap Objects" · https://www.youtube.com/watch?v=cE0GAkSGiUU
- **Correção no playbook:** o Genjutsu **aceita prompt**. Na transferência de movimento, você sobe o vídeo de referência e as imagens dos personagens e descreve no prompt **o ambiente, a câmera e o visual** que quer, inclusive mudando o mundo inteiro ("Hollywood action scene", "anime world"). Qualidade até **1080p**.
- Ele preserva **a caminhada, o tremor de câmera e o timing** do vídeo-fonte, inclusive com **dois personagens** (duas imagens).
- **Motion library do Higgsfield:** biblioteca de movimentos e ações prontos para usar como fonte, sem filmar nada. É a fonte de dança "limpa" (1 pessoa, câmera parada) que o C5 exige.
- **Object swap (outro modo):** sobe o vídeo e as imagens dos objetos (camisa, bandana, corrente) e diz no prompt cada troca. O resto da cena fica intacto. Para nós, serve para trocar um figurino ou prop num vídeo que já ficou bom, mais barato que regerar.
- Preço citado: no plano básico, 120 créditos/mês incluem MC e object swap (tabela por duração e resolução na tela). Confirmar com o estimate antes.

## 4. "Seedance 2.5 Masterclass & Early Review" (Theoretically Media) · https://www.youtube.com/watch?v=b5F81eip5BM
A análise cobriu só a abertura (30 s). O curta foi feito com o Seedance 2.5 e a promessa é de um bastidor com "tips and tricks". Nada técnico aproveitável nessa amostra. **Repetir** a análise num recorte posterior do vídeo ou no Short dele.

---

## O que muda no sistema
1. **Playbook C5 (motion control):**
   - A imagem do personagem passa a ser **sempre uma edição do 1º frame do vídeo-fonte** (técnica 2).
   - O Genjutsu recebe um **prompt de cena** (ambiente, câmera, visual, rigidez do topete e deadpan).
   - A fonte preferida é a **motion library do Higgsfield**, ou uma trend recortada.
2. **Novo passo de segurança:** antes do primeiro vídeo de um personagem novo, faça **um teste de 4 s** para pegar a moderação de rosto. Se der flag, gere uma ficha nova e neutra.
3. **Ensaio barato:** o template novo passa primeiro por 480p ou Kling std. Já está na regra F; agora tem o caso real de 22 planos que falharam como motivo.
4. **Object swap** entra no reparo C6 como opção (d): trocar o figurino ou o prop errado sem regerar.
