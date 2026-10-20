# C7 — Evolução e declínio

## Objetivo
Fazer a carreira responder a idade, minutos, treino, personalidade e lesões sem crescimento automático nem colapso súbito aos 30.

## Regras
1. Atualização é mensal. O atleta ganha pontos de desenvolvimento (PD): `idade × minutos × treino × estrutura × personalidade × saúde`.
2. Fator etário de crescimento: 15–17=1,35; 18–20=1,20; 21–23=1,00; 24–26=0,55; 27–29=0,20; 30+=0. Não ultrapassa PA.
3. Minutos: <90/mês=0,35; 90–359=0,70; 360–719=1,00; 720+=1,10. Jogos de base valem 0,55; empréstimo profissional vale 1,00.
4. Treino 1–20 vira 0,65–1,20; instalações 1–20 vira 0,75–1,15. Profissionalismo/ambição médios viram 0,70–1,25.
5. Ganho mensal-base é 0,10 ponto CA20. O sistema distribui o ganho entre atributos treinados e lacunas da posição.
6. Declínio físico anual: 30=−0,3; 31=−0,6; 32=−1,0; 33=−1,4; 34+=−1,8 pontos de atributo físico. Condição natural 16+ reduz 35%; 8− aumenta 30%.
7. Mentais podem subir até 32: Decisões, Posicionamento, Compostura e Influência recebem até +0,25/ano com minutos e profissionalismo.
8. Lesão de 60–179 dias reduz o ganho do período e pode retirar 0–0,5 físico; 180+ dias pode retirar 0,5–1,5. Propensão a lesão muda probabilidade, não dano determinístico.
9. CA é recalculado pelos pesos de posição após cada alteração; forma é separada e temporária.

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| ganho-base | 0,10 CA20/mês | editorial para calibração |
| teto de minutos | 720/mês | evita bônus por calendário excessivo |
| declínio físico | começa aos 30 | curva inicial |
| ganho mental tardio | até +0,25/ano | experiência |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| 17 anos, PA170, 720 min, treino/estrutura/personalidade neutros | +17,8 CA200/ano aproximadamente |
| mesmo jovem com <90 min/mês | +5,7 CA200/ano aproximadamente |
| 23 anos, 500 min/mês, fatores neutros | +12,0 CA200/ano |
| 32 anos, condição natural 18 | declínio físico anual ≈ −0,65 por atributo afetado |
| lesão de 210 dias | sem PD no afastamento e perda física sorteada 0,5–1,5 |

## Casos de borda
Atleta no PA ainda pode redistribuir atributos sem subir CA; recuperação nunca deixa atributo abaixo de 1; goleiro começa declínio dois anos depois; retorno de lesão limita minutos recomendados por quatro semanas.

## Liga com
Atributos, regens, treino, lesões, partida, valor e carreira.

## Perguntas em aberto
Calibrar ganho anual por faixa usando carreiras reais; decidir se mudanças de posição consomem PD separado.

