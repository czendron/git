# Revisor de frames A e B (playbook E, portões G1–G3, G5–G7, G9, G10)

Abra com Read o frame A (start), o frame B (end), o rosto.png, a silhueta.png e o painel 1 e o último do storyboard aprovado.

## Portões (um "não" reprova)
- **G1:** exatamente 1 protagonista e N figurantes (±1), N = `en.extras_count`.
- **G2:** mesmo rosto do rosto.png (dentes, bigode, olhos caídos, tortura do rosto).
- **G3:** mesma silhueta (topete inteiro no quadro, com folga de ~10% acima).
- **G5:** mãos ≤2 e com dono.
- **G6:** boca fechada, cantos nivelados, sem sorriso.
- **G7:** nenhum figurante olhando para ele.
- **G9:** sem texto sobreposto ou marca d'água.
- **G10:** props como o roteiro pede (frame A: `en.props`; frame B: `en.end_props`), lugares vagos vazios.
- **Coerência A↔B:** B tem a mesma câmera, o mesmo FOV, o mesmo lugar e a mesma luz de A; só muda o que `en.end_change` diz.
- **Orientação:** peito de frente para a lente (no máximo 30°), rosto visível, olhar na lente.
- **9:16:** os dois em retrato com a mesma proporção.

## Notas 0–5
S1, S2, S3, S6, S7 e S8 (o frame B sozinho conta a piada?).

## Veredito
**pass** quando tudo passa, a média ≥3,8 e S1, S2 e S3 ≥4.

`python -m pipeline review <page/id> frames pass|fail --notes "..."`
