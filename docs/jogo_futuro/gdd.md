# C1 — Documento-mãe do jogo

## Objetivo
Criar um manager de futebol brasileiro profundo, legível e rápido, da Série D à Libertadores, no qual regras, economia, pressão e calendário locais sejam parte do jogo — não apenas nomes brasileiros sobre um modelo europeu.

## Regras
1. Os quatro pilares são: **Brasil autêntico**, **decisões com consequência**, **simulação explicável** e **dados moddáveis**.
2. O público principal é quem gosta de FM06, Elifoot e Brasfoot, mas quer temporadas rápidas com decisões mais profundas que “escalar e avançar”.
3. A versão 1 inclui Brasil A–D, estaduais dos clubes carregados, Copa do Brasil, Supercopa, Copa do Nordeste, Copa Verde, Libertadores e Sul-Americana; carreira de técnico; mercado; finanças; base; motor 2D; notícias; editor.
4. A versão 1 não inclui futebol feminino, seleções jogáveis, categorias abaixo do sub-20, multiplayer, 3D, ligas estrangeiras completas nem licenciamento comercial.
5. Toda decisão simulada deve ter explicação acessível: fatores, pesos e último evento que alterou o resultado.
6. Um mês de jogo deve levar no máximo 5 minutos em um PC intermediário quando o usuário não estiver vendo partidas.
7. Uma temporada deve ser concluível em 8–15 horas; telas recorrentes aceitam confirmação em até três ações.
8. Do FM06: copiar densidade, continuidade e ficha do atleta; evitar telas labirínticas. Do Elifoot/Brasfoot: copiar ritmo; evitar resultados opacos e economia rasa.

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| clubes ativos | 124 | banco atual do mod |
| jogadores por clube | 25–35 | elenco profissional + jovens |
| duração-alvo da temporada | 8–15 h | parâmetro editorial |
| autosaves rotativos | 3 | reduzir perda sem encher disco |
| idiomas no v1 | pt-BR | foco e qualidade editorial |
| resolução-base | 1440 × 900 | desktop; escala de 100–200% |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| carreira com Remo, acesso e caixa curto | diretoria celebra acesso, mas limita folha e cobra sustentabilidade |
| usuário simula 30 dias | recebe apenas decisões pendentes, lesões, propostas e jogos |
| informação altera valor de um atleta | ficha mostra fatores: idade, CA, contrato, forma, seleção e liga |
| mod com competição nova válida | aparece sem recompilar o jogo |

## Casos de borda
Clube sem estádio usa mando alternativo; clube insolvente não desaparece, entra em crise controlada; competição cancelada gera calendário reparado e log de validação; dado ausente usa padrão documentado, nunca zero silencioso.

## Liga com
Todos os sistemas C2–C14; o GDD decide prioridade quando houver conflito.

## Perguntas em aberto
Licenciamento e uso de marcas; plataforma além de Windows; escopo exato de estaduais; limite mínimo de hardware.

