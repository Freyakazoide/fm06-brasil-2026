# C13 — Objetivos e carreira do técnico

## Objetivo
Criar uma trajetória na qual reputação, estilo, promessas e conquistas abram empregos coerentes no clube e na seleção.

## Regras
1. Reputação vai de 0–10.000 e tem componentes nacional, continental e global. Começo: amador 300, ex-jogador local 800, licença alta 1.200.
2. Ganho depende de surpresa: `base_evento × dificuldade × importância`; perder como favorito retira reputação, mas queda é 60% do ganho equivalente.
3. Clubes convidam se reputação ≥ 75% da reputação do cargo, estilo é compatível e salário cabe. Rivalidade reduz chance em 40%, não bloqueia.
4. Diretoria define 3–5 objetivos ponderados: liga, copa, finanças, base e estilo. Objetivo impossível pode ser negociado antes da assinatura.
5. Promessa tem texto, métrica, prazo e consequência. Promessa vaga não é permitida.
6. Seleções consideram reputação continental, nacionalidade, idioma e desempenho em mata-mata; acumular clube/seleção só se a federação permitir no cenário.
7. Conquistas registram temporada, clube, competição e dificuldade: acesso D→C 120; C→B 180; B→A 260; Série A 600; Libertadores 800; Mundial 1.000.
8. Desemprego oferece entrevistas; rejeitar uma proposta não gera punição, romper contrato voluntariamente reduz lealdade profissional.

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| reputação | 0–10.000 | granularidade |
| elegibilidade de cargo | 75% da reputação do cargo | permite aposta controlada |
| peso máximo de um objetivo | 40% | nenhum objetivo decide tudo |
| memória de promessa | até o prazo + 180 dias | consequência duradoura |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| técnico rep. 2.400; cargo 3.000 | elegível (80%) se estilo e salário passarem |
| campeão da Libertadores com azarão | ganho maior que favorito; conquista 800 × dificuldade |
| prometeu “usar 5 atletas sub-21 em 15 jogos” e usa 4 | promessa falha na data; confiança cai conforme peso |
| sobe da D à A no mesmo clube | três conquistas e marco especial “Da D à elite” |
| demitido com finanças em crise | reputação cai menos se objetivos financeiros eram impossíveis |

## Casos de borda
Clube extinto mantém histórico; título compartilhado credita ambos; técnico interino recebe 40% do ganho até ser efetivado; save sem seleções não gera convites invisíveis.

## Liga com
Diretoria, reputação de clubes, objetivos, competições, entrevistas e histórico.

## Perguntas em aberto
Licenças de treinador jogáveis; criação de avatar; negociação de equipe técnica própria.

