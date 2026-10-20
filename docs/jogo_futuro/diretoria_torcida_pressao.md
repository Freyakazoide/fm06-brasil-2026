# C9 — Diretoria, torcida e demissão

## Objetivo
Transformar resultado esportivo, finanças e identidade do clube em pressão previsível, mas não mecânica, sobre o técnico.

## Regras
1. Confiança da diretoria e humor da torcida variam de 0–100 e são separados. Começam em 60.
2. Diretoria avalia: resultado 45%, objetivos 25%, finanças 15%, vestiário 10%, base 5%. Pesos mudam por perfil do presidente.
3. Torcida avalia: resultado 45%, rival 20%, desempenho 15%, ídolos/base 10%, preço/gestão 10%.
4. Expectativa de liga vem da posição prevista: título (1–3), continental (4–8), meio (9–13), permanência (14–16), luta contra queda (17–20).
5. Jogo atualiza no máximo ±8; clássico/final pode chegar a ±14. Sequência usa média exponencial de seis jogos.
6. Demissão entra em pauta com diretoria <35; ocorre normalmente <25 após três jogos, ou imediatamente <15. Não demitir durante os primeiros 45 dias salvo confiança <10.
7. Troca de presidente aplica tolerância de 60 dias, mas oposição pode iniciar confiança 45 se prometeu outro técnico.
8. Protesto ocorre com torcida <30 por duas semanas; reduz mando em 0,03 e sócio-torcedor em 0,5–2% ao mês. Boa fase recupera gradualmente.
9. A IA calibra limiares para o número real de trocas; nunca força demissão nominal só para bater meta.

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| confiança inicial | 60 | neutro positivo |
| pauta/demissão | 35/25 | editorial |
| proteção inicial | 45 dias | evita rotação absurda |
| janela de forma | 6 jogos | curto prazo brasileiro |
| cancelamento mensal de sócios em crise | 0,5–2% | calibrável |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| favorito ao título em 9º após 12 rodadas | objetivo muito abaixo; confiança perde 10–20 pontos conforme finanças/vestiário |
| clube previsto 19º em 14º | resultado acima da meta; confiança cresce mesmo com futebol reativo |
| derrota em clássico e eliminação | queda combinada limitada a 14 no evento |
| confiança 24 por três jogos, sem proteção | demissão ao fechar o terceiro jogo |
| torcida 27 por 30 dias | protesta e sócios caem entre 0,5 e 2% |

## Casos de borda
Interino não é demitido por gatilho automático; título congela demissão por sete dias; salários atrasados reduzem a culpa atribuída ao técnico; presidente sem mandato usa conselho como ator.

## Liga com
Economia, resultados, imprensa, carreira, clássicos e sócio-torcedor.

## Perguntas em aberto
Preencher `tecnicos_demitidos` no C0 para calibrar limiares; cadastrar mandatos e perfis de dirigentes.

