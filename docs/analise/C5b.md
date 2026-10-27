# Ficha C5b — Orçamento de contratações e de salários (em andamento)

- Quem analisou / data: Claude, 2026-10-27 (Ghidra 12.1.4 headless + capstone + memória do jogo aberto)

## O que já se sabe

- Os clubes brasileiros têm finanças do tipo **básico** no `server_db` (`financas.py`): objeto
  de 0x1C bytes, vtable `0x010EF344`, com o **saldo em +4** (libras). Conferido na memória do
  New Game de 27/10: Flamengo £24.137.930 (× 5,08 = R$ 122,6 mi, igual à tela "Balance R$122M";
  o banco tinha £21.714.567, a diferença é a receita do 1º mês, R$ 10,9 mi).
- O objeto básico **não guarda orçamentos**: a classe os devolve por métodos virtuais. Métodos da
  vtable `0x010EF344` com constante: 13 e 76 → 100, 18 → 25.000, 19 e 46 → 1.000,
  57 → 67.500, 79 → 50.000.000; com conta: 12 (`0x00A7C8A0`), 48–53, 55, 58, 60. O
  `0x008AC550` (método 49) é uma fórmula com o público médio do clube (`CLUB+0xF0`), faixas
  de reputação e constantes; ainda não está claro qual método é qual orçamento.
- Tela do Flamengo (27/10): orçamento de transferências R$ 253.999 (= **£50.000**, valor
  redondo), "75% da transferência disponibilizada", patrocínio R$ 6,66 mi/época, empréstimo
  R$ 115 mi (banco, R$ 1,2 mi/mês até 2037), orçamento salarial R$ 8,5 mi/mês, folha atual
  R$ 10,57 mi/mês.

## Consequência

Não há campo de orçamento para gravar: o caminho é ajustar as entradas da fórmula (saldo,
dívidas, público, reputação) para o orçamento sair perto da aba Estrutura. Falta a fórmula.

## Próximo

1. Telas de finanças de clubes com entradas diferentes (Palmeiras, Corinthians, um da Série B,
   um da Série D) para comparar com saldo/público/reputação do banco.
2. Achar qual método a tela de finanças chama para cada orçamento e descompilar a fórmula.
