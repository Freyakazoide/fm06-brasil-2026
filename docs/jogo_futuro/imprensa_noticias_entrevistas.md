# C10 — Imprensa, notícias e entrevistas em pt-BR

## Objetivo
Dar contexto e consequência às simulações com textos brasileiros variáveis, curtos e sem repetição perceptível.

## Regras
1. Cada modelo tem `id`, situação, manchete, texto, tom, peso, condições e variáveis obrigatórias.
2. Variáveis válidas: `{clube}`, `{rival}`, `{tecnico}`, `{jogador}`, `{idade}`, `{placar}`, `{rodada}`, `{competicao}`, `{estadio}`, `{posicao}`, `{data}`. Modelo com variável ausente não é elegível.
3. Não repetir o mesmo `id` em 30 dias nem a mesma manchete em 15; histórico é por save.
4. Tons: neutro, crítico, exaltado, institucional, rumor. Fonte institucional não usa rumor como fato.
5. Situações mínimas: estreia, clássico, goleada, virada, zebra, título, acesso, queda, lesão, suspensão, contratação, venda, renovação, pré-contrato, demissão, crise financeira, promessa da base, recorde, convocação e protesto.
6. Coletiva oferece três respostas: apaziguadora, firme e provocadora. Efeitos imediatos ficam entre −4 e +4; efeito máximo acumulado por coletiva é ±6.
7. Resposta pública incompatível com ação posterior reduz credibilidade em 2–6. Credibilidade baixa aumenta perguntas críticas.
8. Texto final tem 45–80 caracteres na manchete e 220–600 no corpo; pt-BR, voz ativa e nomes como estão no banco.

## Modelos iniciais
| situação | manchete | tom |
|---|---|---|
| vitória em clássico | `{clube} vence {rival} e pinta a cidade de suas cores` | exaltado |
| derrota em casa | `{clube} tropeça diante da torcida` | crítico |
| contratação | `{clube} anuncia {jogador} para a sequência da temporada` | institucional |
| lesão | `{jogador} vira desfalque no {clube}` | neutro |
| demissão | `{clube} encerra trabalho de {tecnico}` | institucional |
| base | `{jogador}, de {idade} anos, ganha chance entre os profissionais` | neutro |
| crise | `Atrasos aumentam pressão sobre a diretoria do {clube}` | crítico |
| acesso | `{clube} confirma acesso e celebra volta por cima` | exaltado |
| pré-contrato | `{clube} acerta chegada de {jogador} para {data}` | neutro |
| protesto | `Torcida do {clube} protesta após {placar}` | crítico |

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| intervalo do mesmo modelo | 30 dias | reduzir repetição |
| opções por pergunta | 3 | decisão rápida |
| efeito por resposta | −4 a +4 | manter impacto controlado |
| modelos mínimos por situação | 8 | variedade inicial |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| vitória 3–0 do Remo sobre Paysandu | manchete de clássico com clubes e placar resolvidos; tom exaltado |
| modelo exige `{jogador}`, evento sem atleta | modelo não é selecionado |
| técnico provoca rival (+3 torcida, −2 relação) | efeitos aplicados e salvos no histórico |
| mesmo título sorteado há 10 dias | bloqueado; selecionar variante |

## Casos de borda
Nome longo não é truncado no meio; empate sem gols evita “goleada”; atleta vendido não fala como membro do clube; variável malformada invalida o arquivo no editor.

## Liga com
Partida, mercado, diretoria, torcida, carreira e localização.

## Perguntas em aberto
Criar uma planilha própria quando o esquema for aprovado; definir vozes de veículos nacionais e regionais fictícios.

