# C6 — Geração de regens

## Objetivo
Renovar o banco com jovens plausíveis por clube, região e geração, mantendo rara a elite e usando nomes contemporâneos.

## Regras
1. Cada clube recebe candidatos anuais: A=12, B=10, C=8, D=6; apenas 4–8 assinam. CT não aumenta talento; instalações e recrutamento afetam detecção e desenvolvimento inicial.
2. Nota de captação `R = 0,45×recrutamento + 0,30×reputação/10 + 0,25×alcance`, todos normalizados a 1–20.
3. PA parte de distribuição nacional e recebe deslocamento `round((R−10)×1,2)`, limitado a ±12. Nenhum clube “fabrica” joia garantida.
4. Meta anual do Brasil: 1–2 atletas PA 170+, 16–24 PA 140–169, 110–150 PA 120–139; demais abaixo de 120. Ajustar globalmente depois de gerar todos.
5. Posição: GK 9%, CB 17%, laterais 16%, DM/CM 22%, AM/pontas 20%, ST 16%. Pé esquerdo 20%; ambos 3%.
6. Altura usa distribuição por posição: GK 188±6 cm, CB 185±6, ST 180±7, demais 175±7; limites 155–205.
7. Região vem do alcance do clube e alimenta `nomes_regens.xlsx`; nome de jogo não pode duplicar outro no elenco e respeita 15 caracteres.
8. CA inicial aos 15–17 é 30–45% do PA, modulado por instalações e idade. Personalidade é sorteada com correlação familiar/clube leve, nunca copiada de jogador de 2005.
9. A nacionalidade secundária tem 6% de chance no Brasil; aumenta para clubes em fronteira e depende de nacionalidades existentes na base regional.

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| candidatos A/B/C/D | 12/10/8/6 | editorial; desempenho aceitável do banco |
| joias PA 170+ Brasil/ano | 1–2 | raridade de elite mundial |
| PA 140–169/ano | 16–24 | elite nacional/exportação |
| pé E / ambos | 20% / 3% | ponto de partida a validar |
| idade de entrada | 15–17 | base brasileira |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| clube A, recrutamento 20, reputação 80, alcance 18 | R=15,9; deslocamento de PA +7, sem joia garantida |
| clube D, recrutamento 8, reputação 25, alcance 6 | R=5,85; deslocamento −5 |
| 10 temporadas completas | 10–20 PA 170+, 160–240 PA 140–169 antes de aposentadorias |
| elenco já tem “Dudu” | gerador usa nome completo ou outro apelido |
| GK sorteado | altura central 188 cm; não usa distribuição de ponta |

## Casos de borda
Clube sem base recebe 4 candidatos mínimos; nome sem combinação válida volta ao nome completo; atletas gêmeos podem compartilhar sobrenome e data; limite global corrige apenas PA ainda oculto.

## Liga com
Nomes de regens, atributos, evolução, instalações, regiões e mercado.

## Perguntas em aberto
Validar posição/pé/altura contra banco real de sub-20; decidir existência de academias independentes.

