# C2 — Atributos do jogador

## Objetivo
Converter qualidades de 1–20 em comportamento observável e em uma capacidade atual (CA) comparável entre jogadores sem premiar atributos irrelevantes à posição.

## Regras
1. Escala: 1–4 amador, 5–8 Série D/C, 9–12 Série B, 13–15 Série A, 16–17 elite continental, 18–20 elite mundial.
2. Cada atributo entra apenas nos eventos indicados. O mesmo lance combina técnica, mental e físico; nenhum atributo decide sozinho.
3. Peso por posição: `CA20 = soma(atributo × peso) / soma(pesos)` e `CA200 = arredondar(CA20 × 10)`, limitado a 10–200.
4. Pesos: 5 essencial, 3 importante, 1 útil, 0 irrelevante. Atributos não listados no perfil da posição têm peso 1, exceto atributos de goleiro, peso 0 para jogadores de linha.
5. Posição usada para CA é a de maior nota. Versatilidade não aumenta CA; apenas reduz a penalidade ao atuar fora da principal.

## Catálogo de atributos
| grupo | atributos | efeito principal no lance |
|---|---|---|
| técnica | Cabeceamento; Finalização; Remates Longe | precisão/potência de cabeçada e chute |
| técnica | Passe; Primeiro Toque; Técnica | erro de execução, domínio e variedade |
| técnica | Cruzamentos; Cantos; Livres; Marcação Penalties | qualidade da bola parada e cruzada |
| técnica | Finta; Desarme; Marcação | drible, tomada limpa e acompanhamento |
| técnica | Lançam. Longos | alcance e precisão da reposição lateral |
| mental | Antecipação; Decisões; Concentração | ler, escolher e sustentar a ação correta |
| mental | Criatividade; Instinto; Sem Bola; Posicionamento | enxergar passe, reagir, atacar e defender espaço |
| mental | Compostura; Determinação; Bravura | executar sob pressão, insistir e disputar |
| mental | Agressividade; Influência; Trabalho Equipa; Índice Trabalho | intensidade, liderança, cooperação e volume |
| físico | Aceleração; Velocidade; Agilidade; Balance | arrancada, máxima, mudança de direção e equilíbrio |
| físico | Força; Impulsão; Resistência; Cond. Fís. Natural | contato, salto, fadiga e recuperação |
| goleiro | Handling; Reflexes; One on one | segurar, reagir e fechar o atacante |
| goleiro | Aer ability; Cmd of area; Communication | bola aérea, domínio e organização da área |
| goleiro | Kicking; Long throws | distribuição com pés e mãos |
| goleiro | Rushing out; Punch; Eccentricity | saída, soco e propensão a ações não convencionais |

## Pesos por posição
| posição | peso 5 | peso 3 | peso 1 especial |
|---|---|---|---|
| GK | Reflexes, Handling, One on one, Posicionamento | Aer ability, Cmd of area, Communication, Rushing out, Agilidade | Kicking, Long throws, Punch, Eccentricity |
| CB | Marcação, Desarme, Posicionamento, Antecipação, Força, Impulsão | Cabeceamento, Concentração, Bravura, Velocidade | Passe, Técnica |
| RB/LB | Velocidade, Resistência, Cruzamentos, Marcação, Desarme | Aceleração, Sem Bola, Índice Trabalho, Passe, Decisões | Finalização, Cabeceamento |
| DM | Posicionamento, Desarme, Decisões, Passe, Concentração | Marcação, Antecipação, Força, Trabalho Equipa | Finalização, Finta |
| CM | Passe, Decisões, Técnica, Resistência, Trabalho Equipa | Primeiro Toque, Criatividade, Posicionamento, Sem Bola | Cabeceamento, Marcação |
| AM | Criatividade, Passe, Técnica, Primeiro Toque, Sem Bola | Finta, Decisões, Compostura, Finalização | Desarme, Marcação |
| RW/LW | Aceleração, Velocidade, Finta, Técnica, Sem Bola | Cruzamentos, Primeiro Toque, Finalização, Agilidade | Marcação, Força |
| ST | Finalização, Sem Bola, Compostura, Instinto, Primeiro Toque | Aceleração, Cabeceamento, Força, Antecipação | Marcação, Desarme |

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| faixa | 1–20 | compatível com o banco do mod |
| peso essencial/importante/útil | 5/3/1 | parâmetro editorial |
| penalidade posição secundária | 4% | reduzida por versatilidade |
| penalidade fora de posição | 12% a 30% | 30% × (21 − versatilidade)/20 |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| ST com média ponderada 16,46 | CA 165 |
| CB com Finalização 18, demais essenciais 10 | CA próximo de 100; finalização pesa só 1 |
| GK com Reflexes/Handling/One on one = 18 e demais ponderados = 15 | CA entre 158 e 168 |
| ponta CA 150, versatilidade 16, usado como AM | capacidade efetiva 144 (−4%) |
| ponta CA 150, versatilidade 8, usado como CB | capacidade efetiva 109 (−27%) |

## Casos de borda
Atributo ausente usa valor neutro 10 só na prévia, mas bloqueia exportação final; goleiro na linha usa perfil de posição com atributos de linha; CA não ultrapassa PA salvo forma temporária, que afeta partida e não CA persistente.

## Liga com
Motor de partida, evolução, regens, valor de mercado e mercado.

## Perguntas em aberto
Confirmar se “Balance” será traduzido para Equilíbrio e revisar cinco jogadores reais depois da primeira simulação.

