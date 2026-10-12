# Campos não resolvidos e resultado das rodadas manuais

## Resultado aproveitado

As duas rodadas produziram baselines e diffs sequenciais. Além dos campos já confirmados de Player/PData/Playing, a rodada final resolveu:

- Personal Info: Nationality `UID+64`, Born `UID+52`, Ask Value `UID-192`, U21 Caps `UID+73` e U21 Goals `UID+75`.
- Playing: Finishing, Anticipation, Acceleration, Pace, Left foot e Handling nos offsets previstos pela permutação do FMM.txt.
- Preferred Moves: bitset de 48 bits começando em `Player UID-48`, LSB-first.
- Contract: Started `+24`, Expires `+32`, Squad Status `+37`, flags Transfer/Loan `+38`, Happiness `+48`, Squad Number `+49`, Agreed Price `+56` e bônus em `+76/+80/+84/+88`.
- Club: Cash `+248` u32 no Sevilla.
- Nation: Development `+228`, Economic Factor `+233` e Reputation `+252`.

Os dados integrais estão em `remaining_round_analysis.json` e `.csv`. Para os atributos Playing não posicionais, os offsets são sólidos, mas a fórmula geral de leitura dos raws originais 0..255 continua sem solução.

## Diffs não promovidos

- Value: o passo foi pulado. `Player UID-196` mudou apenas durante uma restauração acidental e permanece candidato, não campo confirmado.
- Contract Unhappy e Minimum Release não produziram alteração observável.
- Club: Maximum Attend, Capacity, Seating, Used Capacity, Expansion Capacity, Pitch Width e Pitch Length não produziram diff. Os demais campos foram marcados como ausentes/não editáveis.
- Nation Importance não produziu diff. League Standard alterou simultaneamente `+230` e `+231`, então os dois offsets ficaram como candidatos `LOW`. FIFA Ranking e Ranking Points estavam ausentes/não editáveis.
- O fato de um passo não produzir diff não rejeita a existência do campo; ele só impede a atribuição de um offset.

## Lacunas atuais

- Personal Info: Value ainda não confirmado.
- Playing: transformação raw→1..20 dos atributos não posicionais e confirmação individual dos offsets ainda marcados `HIGH`.
- Contract: Unhappy e Minimum Release; semântica completa dos bits Transfer/Loan e transformação de Squad Number.
- Club: todos os campos além de Cash.
- Nation: Capital, FIFA Ranking, Ranking Points, Stadium, Group Member, Importance e League Standard inequívoco.
- Staff/Coaching e demais estruturas do FMM.txt ainda têm somente raízes de schema, sem campanha controlada específica.

## Estado vivo observado na captura final

A captura chamada `restored_final` não voltou integralmente à baseline. Permaneceram na RAM Nationality, seis atributos Playing, os campos de contrato testados (inclusive Squad Number em raw `0x01`), Agreed Price e Club Cash. Nation foi restaurado por completo; Born, Ask Value, U21 e Preferred Moves também voltaram à baseline. Houve ainda uma alteração acidental em `Player UID-196`.

Como a partida não foi salva, o arquivo em disco não foi modificado. Para descartar o estado de teste, feche/recarregue a partida sem salvar. Não é necessária outra rodada manual para documentar os diffs já obtidos.
