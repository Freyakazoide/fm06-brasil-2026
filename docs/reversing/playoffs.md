# Playoffs e mata-matas (para as regras de 2026)

## Desempate pela melhor campanha

O motor já tem a regra que a Série B de 2026 usa ("empate nos dois jogos:
sobe quem fez melhor campanha"). Textos em `.rdata`:

- `0x0109D2E0` "<%team#1-short> win if scores are still level, due their higher league position"
- `0x0109D280` "... level after ninety minutes, due their higher league position"
- `0x0109D388` "... still level, due to higher seeding"

Quem escolhe o texto: `0x006A1F2C`, que lê uma palavra de flags do confronto
(`+0x94`): bit `0x100` = vence a melhor posição na liga; bit `0x40` = vence o
melhor cabeça de chave. Falta achar onde a montagem da fase liga esses bits
(candidatos: `0x00B3BB10` / `0x00B3BAD0`, chamados na montagem do mata-mata
da antiga Série C, `0x00BC0143`–`0x00BC0449`).

Outras pistas: `LEAGUE_STAGE::check_for_position_playoff()` (`0x00B13301`),
"Fifth Placed Playoff" (`0x009F7C3C`).

## Plano

| Regra de 2026 | Ideia |
|---|---|
| Série B: 3º×6º e 4º×5º, ida e volta, sem pênaltis, vence a melhor campanha | 2ª fase na Série B: mata-mata de 4, uma rodada, bit `0x100`; vencedores sobem com o 1º e o 2º |
| Série C: grupos B (1,4,5,8) e C (2,3,6,7), ida e volta; final ida e volta com pênaltis | 2ª e 3ª fases na nova C; achar como o jogo semeia grupos pela posição |
| Série D: 6 acessos | refazer o mata-mata da antiga C |
