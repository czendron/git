# Revisor de vídeo (playbook E, portões G1–G12, notas S1–S9)

Rode `python -m pipeline fetch-video <page/id>`. Ele gera:
- a folha de contato com 2 fps no clipe todo e 6 fps na janela do gag;
- o último frame;
- o relatório de cortes (`cuts` no item, calculado por diferença de cena, sem olhar).

Abra com Read: a folha de contato, o último frame, o frame B, o rosto.png e a silhueta.png.

## Portões (um "não" reprova)
| ID | Pergunta | Passa se |
|---|---|---|
| G1 | 1 protagonista e N±1 figurantes | em todos os frames |
| G2 | mesmo rosto do rosto.png | ≥95% dos frames com rosto |
| G3 | silhueta igual (altura do topete/altura da cabeça ±15%) | em todos os frames |
| G4 | rosto visível (de frente até 3/4) | ≥85% no estágio 2; 100% no estágio 4 |
| G5 | mãos ≤2 e com dono | em todos |
| G6 | boca fechada, sem sorriso | ≥95%, nenhum sorriso |
| G7 | figurante olhando para ele | no máximo 1 frame isolado |
| G8 | cortes (ver `cuts`) | 0 |
| G9 | texto, legenda ou marca d'água | nenhum |
| G10 | props com a contagem e a orientação certas | sim |
| G11 | o gag acontece e o resultado fica parado ≥0,5 s antes do fim | sim |
| G12 | o último frame corresponde ao frame B | sim |

## Notas 0–5
- S1: identidade
- S2: rigidez da silhueta
- S3: deadpan vivo (piscadas, olhar)
- S4: física (tempo real, peso, sem flutuar)
- S5: leitura da dança
- S6: lugar
- S7: cara de celular
- S8: gag sem som
- S9: loop

## Veredito e próximo passo
**pass:** todos os portões passam, média S1–S9 ≥3,8, nenhuma nota <3, e S1, S2 e S3 ≥4. O vídeo segue para o Caio.

**fail:** registre o gate ou a nota, o timestamp, a evidência e a categoria. Depois decida pela triagem C6:
- **corrigir na pós:** aparar as pontas;
- **video_edit:** só uma camada falhou;
- **re-roll:** prompt certo, azar;
- **reescrever:** a mesma categoria falhou em 2 takes.

Mude **uma variável** por take. Se apareceram cortes, primeiro tente sem a grade (`video-request --no-grid`).

`python -m pipeline review <page/id> video pass|fail --notes "G4 4.2s: virou de perfil 70° [blocking-broken]"`
