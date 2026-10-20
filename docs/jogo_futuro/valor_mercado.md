# C3 — Valor de mercado

## Objetivo
Estimar valor econômico coerente com desempenho, idade, potencial e contrato, separando estimativa pública, preço pedido e multa.

## Regras
1. `valor = base_CA × posição × idade_potencial × contrato × liga_clube × forma × seleção`.
2. Interpolar a base em euros: CA 90=€0,15 mi; 110=€0,60 mi; 130=€2,5 mi; 150=€10 mi; 170=€35 mi; 190=€90 mi.
3. Fator posição: GK 0,72; laterais 0,85; CB 0,90; DM 0,95; CM 1,00; AM/pontas 1,15; ST 1,12.
4. Idade/potencial: até 19 = `0,75 + 0,015 × max(PA−CA,0)`; 20–23=1,20; 24–27=1,10; 28–30=0,85; 31–33=0,58; 34+=0,35. Limite 0,60–1,80.
5. Contrato: 36+ meses=1,00; 24=0,90; 12=0,68; 6=0,35; 0=0,10; interpolação linear.
6. Liga/clube = reputação do clube ÷ 100, limitado a 0,55–1,35. Forma = 0,85–1,15 pela média dos últimos dez jogos. Seleção = 1,00 sem convocação; 1,08 convocado; 1,15 titular recorrente.
7. O produto dos fatores após a base é limitado a 0,25–3,00 para evitar explosão multiplicativa.
8. Preço pedido = valor × necessidade esportiva × saúde financeira × disposição do atleta: cada fator 0,75–1,35; produto final limitado a 0,65–2,20.

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| erro-alvo mediano | ≤ 25% | comparação com aba Valores |
| erro-alvo P90 | ≤ 60% | cauda aceita para jovens/estrelas |
| atualização | mensal | evitar volatilidade diária |
| forma neutra | nota 6,8 | parâmetro editorial inicial |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| ST, CA150, 25 anos, 36m, clube 100, forma neutra, sem seleção | €12,32 mi (`10 × 1,12 × 1,10`) |
| GK, CA150, 32 anos, 6m, clube 90, forma neutra | €1,32 mi (`10 × .72 × .58 × .35 × .90`) |
| ponta, CA130/PA175, 18 anos, 48m, clube 105, convocado | €4,64 mi; fator jovem 1,425 |
| valor €10 mi, titular indispensável, caixa bom, atleta quer ficar | preço pedido €16,4 mi (1,35×1,10×1,10) |
| contrato encerrado | valor econômico mostrado, preço de transferência €0 |

## Casos de borda
Sem PA, usar CA + ganho esperado por idade; empréstimo usa valor do dono; lesão longa reduz forma, não CA; moeda é armazenada em centavos de EUR e convertida só na interface.

## Liga com
Atributos, contrato, mercado, economia, seleção e forma.

## Perguntas em aberto
Recalibrar faixas de base contra 60 jogadores e vendas reais; decidir se reputação é global ou por mercado comprador.

