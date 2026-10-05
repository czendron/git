# Revisor de storyboard (playbook E, portões G1–G3, G5, G6, G9, G10 + S10)

Abra o storyboard com Read, junto com `pages/<slug>/refs/rosto.png` e `silhueta.png`. Leia os `storyboard_panels` e o `en.panels` do roteiro. Analise **painel por painel**.

## Portões (um "não" reprova)
- **G1:** em cada painel há exatamente 1 protagonista e o número de figurantes pedido (±1)? Conte painel por painel.
- **G2:** o rosto do protagonista é a mesma pessoa do rosto.png em todos os painéis em que aparece?
- **G3:** o topete (laquê, bigode) tem a mesma forma, altura e volume da silhueta.png em todos os painéis?
- **G5:** no máximo 2 mãos dele, cada uma ligada a um braço?
- **G6:** boca fechada, sem sorriso, em todos os painéis?
- **G7:** nenhum figurante olha para ele?
- **G9:** sem texto, balão, numeração ou seta dentro dos painéis? (Letreiro do lugar pode.)
- **G10:** props com a contagem e a orientação do roteiro, e lugares vagos vazios?
- **Orientação:** em todos os painéis ele está de frente ou em 3/4 para a câmera, nunca de costas (a não ser que o roteiro peça)?
- **S10:** cada painel mostra o estado pedido para aquele tempo, na ordem certa?

## Notas 0–5
S1 identidade · S2 silhueta · S3 deadpan · S6 lugar brasileiro autêntico · S7 cara de celular real · S8 gag legível sem som · S10 fidelidade ao roteiro.

## Veredito
**pass** se todos os portões passam, a média ≥3,8, nenhuma nota <3 e S1, S2 e S3 ≥4. Senão **fail**.

Registre com uma linha de evidência por problema:
`python -m pipeline review <page/id> storyboard pass|fail --notes "G3 painel 3: topete achatado pela porta [physics]; S8=2: piada não lê"`
Categorias: identity-drift | wardrobe-contamination | extra-cuts | blocking-broken | performance | camera-wrong | physics | text-render | composition | other
