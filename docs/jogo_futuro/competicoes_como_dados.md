# C11 — Competições como dados

## Objetivo
Descrever formatos, fases, vagas, desempates e datas em arquivos validados para que novas competições não exijam código.

## Regras
1. Cada competição tem `id`, edição, país, participantes, calendário, fases e regras de inscrição.
2. Uma fase define formato (`liga`, `grupos`, `mata_mata`), número de turnos, mando, pontuação, classificação, vagas e desempates em ordem.
3. Desempate é lista executada até resolver; sorteio só pode ser último item e deve ficar registrado.
4. Vaga aponta para fase/competição-alvo e temporada de destino. Rebaixamento e acesso são vagas com direção.
5. Conflito de calendário usa prioridade: seleção/FIFA 100, continental 90, nacional 80, regional 60, amistoso 10; jogo já iniciado não é remarcado.
6. Alteração de regulamento cria nova versão e não muda save em andamento.
7. Validador impede participante duplicado, datas invertidas, vagas impossíveis, grupo vazio e mata-mata com número incompatível sem bye explícito.

## Ficha inicial — Série A
| campo | valor |
|---|---|
| id | `bra_a_2026` |
| participantes | 20 |
| fase | liga, turno e returno, 38 rodadas |
| pontuação | vitória 3, empate 1, derrota 0 |
| campeão | 1º |
| rebaixamento | 17º–20º para Série B 2027 |
| desempate | vitórias; saldo; gols pró; confronto direto quando aplicável; cartões vermelhos; amarelos; sorteio |
| calendário | datas exatas vêm da tabela oficial importada |

## Ficha inicial — Paulista A1
| campo | valor |
|---|---|
| id | `paulista_a1_2026` |
| participantes | 16 |
| fase 1 | liga conforme regulamento da edição; grupos e cruzamentos parametrizados |
| mata-mata | quartas, semi e final com quantidade de jogos definida por fase |
| rebaixamento | parametrizado no regulamento da edição |
| desempate | lista explícita do regulamento oficial |

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| pontos vitória/empate | 3/1 | regra corrente |
| participantes Série A | 20 | regulamento 2026 |
| jogos por clube Série A | 38 | turno e returno |
| versões aceitas | esquema 1.x | compatibilidade semântica |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| dois clubes empatam em pontos; A tem mais vitórias | A fica acima sem avaliar saldo |
| vaga aponta para competição inexistente | erro de validação antes do save |
| mata-mata com 15 clubes e um bye | válido se bye declarado; inválido se omitido |
| regulamento 2027 carregado em save 2026 | aplicado apenas à edição 2027 |

## Casos de borda
Clube excluído após início gera resultado administrativo configurável; empate absoluto usa sorteio com seed; fases com melhor campanha definem “melhor” pela mesma lista de desempate; data sem estádio usa mando alternativo.

## Liga com
Calendário, partida, inscrições, mercado, premiação, notícias e editor.

## Perguntas em aberto
Transcrever datas e critérios de todos os estaduais diretamente dos regulamentos; fechar regras de vagas continentais após o calendário anual.

## Fontes
`docs/REGRAS_2026.md`, `docs/REGRAS_2026_ESTADUAIS_E_COPAS.md` e [REC Série A 2026](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/REC_Brasileiro_Serie_A_2026_c984f8cf05.pdf).

