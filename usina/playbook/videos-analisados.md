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

## 5. "Consistent Character Sheets in Seedance 2.0 (Prompts Included)" · https://www.youtube.com/watch?v=Fx5aNgLlYQ0
- **A tese em uma frase (falada):** "The start image builds the scene. The character sheet locks the identity." Mesmo com um start frame bom, a ficha entra **em toda geração** (no frame e no vídeo), porque "keeps reminding the model: same face, same outfit, same hairstyle". Confirma o pacote padrão do B3 (rosto + silhueta sempre junto do `start_image`). Só image-to-video não basta.
- **Prompt da ficha mostrado na tela:** "Create a clean character reference sheet of the same person, showing front view, side view, back view, and close-up face details. Keep the same outfit, same hairstyle, same facial features, same color palette, and same character identity. Professional character design sheet, clean layout, neutral background, high detail, consistent proportions." Entrada: **uma** imagem do personagem.
- **Primeira ficha simples:** "No five different outfits. No ten different expressions. No random poses everywhere. Start simple. One character, one outfit." Só depois que o personagem estabiliza é que se testa cena nova, ângulo novo ou troca de figurino. Para nós: uma ficha por figurino, nunca várias roupas na mesma ficha.
- A ficha dele traz painéis de detalhe (luvas, patches, botas) e de equipamento. Para nós isso equivale à ficha de prop separada (regra 24), não a mais painéis na ficha do personagem.
- Ele admite que nem sempre fica perfeito: mostra uma grade de rostos com X vermelho nos que derivaram. A curadoria continua necessária.

## 6. "GPT Image 2 Character Sheets: Mastering Layouts & Consistency" · https://www.youtube.com/watch?v=d7EOD-rdDNw
- **Entrada mínima:** uma imagem-base do personagem nas referências e um prompt longo de ficha (o do Nexora, no X) com perfil psicológico, guarda-roupa, callouts de itens e lista de planos. O mínimo a preencher no topo é **nome e identidade**. O que o prompt não define, o GPT Image puxa da imagem de referência.
- **Configuração mostrada:** proporção **4:3** (ou 16:9), resolução **4K**, qualidade **high**. O motivo dito: "if I zoom in, we don't lose details of the subject". Para nós vale a mesma lógica, porque o `rosto.png` é um recorte de 1/4 da ficha: gere na maior resolução disponível.
- **Mais de uma referência = mais precisão:** anexe várias imagens do personagem quando houver.
- **Conserto da ficha:** a primeira geração tem pequenas inconsistências. Ele **sobe a ficha como referência e pede as correções** numa edição, sem regerar do zero. Confirma o C1 (edição pontual, nunca uma segunda passada completa).
- **Versão enxuta:** a ficha completa "might be overkill". Um prompt cortado, com grade mais simples, manteve a qualidade "top tier". Para nós continua a ficha 2×2 do C1.
- **Leia a ficha inteira antes de usar:** o GPT Image 2 escreve bem, mas o texto e os detalhes precisam de revisão. Para nós a ficha **não leva texto** (regra 10, o rótulo vaza no vídeo); as notas ficam no arquivo de projeto.
- **Variações de expressão a partir da ficha:** ele pede imagens novas com a personagem rindo, a partir da ficha séria. Para nós é o contrário: a ficha já é deadpan e a expressão nunca muda.
- **Roteamento por custo:** ele faz o vídeo no **Kling 3.0 Omni** e só depois no Seedance, porque "Seedance is just pretty expensive". Bate com a nossa rota F (Kling 3.0 como opção barata para plano simples).

## 7. "Insane Seedance Prompts & Tricks" · https://www.youtube.com/watch?v=MOkjfFIIb6E
**Análise falhou.** O job `712609bd-c4d0-4b4a-96af-d844fd7c387d` voltou com `failed` ("Something went wrong. Try another video."). Uma nova tentativa (`34020da0-57f0-495c-bb9d-86ed551a2d72`) ainda estava na fila quando este arquivo foi escrito. **Repetir** e preencher esta seção quando o job concluir.

## 8. "Kling 3.0 Motion Control Deep Dive" (OpenArt, comparação com Kling 2.6 e DreamActor M2) · https://www.youtube.com/watch?v=DvXDQfoy7t4
- **3.0 vs 2.6:** o ganho é pequeno. O 3.0 sai um pouco mais nítido, foca melhor os olhos, copia melhor a boca da fonte e mantém o rosto quando ele sai do quadro ou é coberto pelas mãos. Mas **exagera a nitidez em barba e rugas** ("unnatural and processed"). Ele não acha que a diferença justifica o preço. Para nós: o 2.6 é um A/B barato válido, e o revisor deve reprovar o "pele processada" (S7).
- **Falha "not enough upper body":** com a câmera perto e a cabeça saindo do quadro, o Kling **recusou todas as gerações**. A correção foi refilmar **mais afastado, com mais corpo no quadro**. Bate com a nossa exigência de corpo inteiro na fonte (C5).
- **Mãos que não aparecem na fonte são inventadas:** quando a fonte não mostra as mãos, os dois Klings criam movimento de mão, com borrão nas partes rápidas. Num caso a mão do 3.0 ficou "definitely not usable". A fonte precisa mostrar as mãos o tempo todo.
- **Character Orientation: Exact vs Partial.** O *Exact* aceita fonte de até **30 s** e copia a posição da fonte. O *Partial* permite que o personagem fique noutra posição, que a câmera se mova e que o fundo mude, mas só até **10 s**.
- **Fundo morto:** no *Partial*, só a fonte não gerou movimento de câmera nem de fundo. No 3.0 o fundo ficou "just kind of a dead image", sem nem a carroça andando. **Com prompt de cena** ("the man is actively walking down a road and turning the camera and his body while talking and walking"), o 2.6 passou a mover câmera e fundo, mas o rosto derivou um pouco em volta dos olhos. O 3.0 com o mesmo prompt deu fundo com glitch. Para nós: o movimento dos figurantes **tem de estar escrito** no prompt do MC, porque a fonte não o fornece.
- **A composição da imagem tem de bater com a fonte:** mesmo tamanho do sujeito e mesma posição. Com a personagem bem maior na imagem do que na fonte, ou com o cabo apontado para a câmera em vez de seguir o ângulo da fonte, saiu "weird physics" (o personagem fora do cabo). **Truque:** ele colou uma faixa de papel no chão como guia, andou sobre ela, e pediu à imagem que o cabo "should follow the path of the white line". Para nós: qualquer prop ou marca de chão que interage com a dança (meio-fio, faixa de pedestre, degrau) tem de estar **na mesma linha e ângulo** do 1º frame da fonte. Reforça a técnica do §2 (imagem = edição do 1º frame).
- **Rosto pequeno na imagem = rosto genérico no vídeo:** no plano aberto, "this is all the face information it has". A identidade melhora quando o personagem chega perto da câmera.
- **Uso que não é dança: maneirismos de série.** Para um entrevistador recorrente que "points with his pen", a única forma de ter consistência é uma pessoa real gravar o movimento. "I can't trust the model to come up with that on its own when I can do it with my face exactly." Para nós: **o Caio pode gravar a dança de assinatura de cada personagem** (corpo inteiro, câmera parada, deadpan) e reusar a mesma fonte em todos os vídeos dele. A assinatura fica idêntica entre episódios, coisa que o prompt de texto (regra 20) não garante.
- **Duas fontes, dois personagens:** a entrevista usou dois vídeos-fonte gravados separados, um por personagem, montados depois.
- DreamActor M2 (ByteDance): até 20 s, tem o "partial" embutido e move câmera e fundo melhor, mas o rosto sai mais mole e borra no movimento rápido. Não está no nosso stack. Fica só como referência.

---

## O que muda no sistema
1. **Playbook C5 (motion control):**
   - A imagem do personagem passa a ser **sempre uma edição do 1º frame do vídeo-fonte** (técnica 2).
   - O Genjutsu recebe um **prompt de cena** (ambiente, câmera, visual, rigidez do topete e deadpan).
   - A fonte preferida é a **motion library do Higgsfield**, ou uma trend recortada.
2. **Novo passo de segurança:** antes do primeiro vídeo de um personagem novo, faça **um teste de 4 s** para pegar a moderação de rosto. Se der flag, gere uma ficha nova e neutra.
3. **Ensaio barato:** o template novo passa primeiro por 480p ou Kling std. Já está na regra F; agora tem o caso real de 22 planos que falharam como motivo.
4. **Object swap** entra no reparo C6 como opção (d): trocar o figurino ou o prop errado sem regerar.
5. **Ficha em toda geração:** rosto e silhueta entram em todo frame e em todo vídeo, mesmo com `start_image` bom (§5). Já era o pacote padrão; agora está confirmado pelo uso. **Uma ficha por figurino**, nunca várias roupas na mesma ficha.
6. **Ficha na maior resolução disponível** (§6, 4K/high): o `rosto.png` é um recorte de 1/4 da ficha. Inconsistências da ficha se corrigem com edição sobre ela, nunca com outra passada.
7. **C5 (motion control), requisitos novos da fonte e da imagem** (§8):
   - mãos visíveis a fonte inteira;
   - corpo suficiente no quadro (perto demais, o Kling recusa);
   - sujeito com **o mesmo tamanho e posição** na imagem e na fonte;
   - marcas de chão e props que a dança toca, na mesma linha e ângulo do 1º frame.
8. **Prompt do MC escreve o fundo:** a fonte não traz movimento de figurante nem de câmera, e o Kling 3.0 deixa o fundo parado. O movimento de cada figurante vai escrito. Kling `Exact` (até 30 s, padrão) e `Partial` (até 10 s, só se o personagem precisa estar noutra posição).
9. **Fonte própria de assinatura:** o Caio grava a dança de assinatura de cada personagem uma vez (corpo inteiro, câmera parada, 9:16, deadpan) e ela vira a fonte fixa de MC dele. É a assinatura idêntica entre episódios (§8).
10. **Kling MC 2.6 como A/B barato:** o 3.0 ganha pouco e exagera a nitidez em pele e barba. O revisor reprova "pele processada" em S7.
11. **Pendente:** refazer a análise do §7 (job `34020da0-57f0-495c-bb9d-86ed551a2d72`).
