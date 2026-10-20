# C4 — Economia do clube brasileiro

## Objetivo
Simular caixa, competência contábil, dívida, SAF e atraso salarial sem transformar o jogo em planilha financeira incompreensível.

## Regras
1. Fechamento mensal separa caixa, receitas/despesas por competência, contas a receber, dívida financeira e obrigações fiscais.
2. TV entra conforme calendário do contrato; bilheteria = público pago × ingresso médio × 0,72 líquido; sócio-torcedor entra mensalmente com inadimplência.
3. Folha inclui salário, direito de imagem, encargos e prêmios. Custo total padrão = salário-base × 1,55; cada contrato pode substituir o fator.
4. Venda de atleta reconhece apenas a participação do clube, desconta solidariedade, comissão e impostos; parcelas viram recebíveis.
5. SAF e associação usam as mesmas contas. SAF pode receber aporte do controlador, mas a IA exige plano e não cobre déficit automaticamente.
6. Saldo abaixo de zero aciona crédito de emergência até 8% da receita anual, juros de 1,2% ao mês. Acima disso, bloqueia contratações com pagamento imediato.
7. Dois meses integrais de atraso salarial ou de imagem tornam o contrato rescindível no jogo; o sistema avisa aos 30 e 45 dias.
8. Dívida cara é renegociada se serviço anual superar 18% da receita; recuperação judicial reduz confiança e adia parte das obrigações, nunca apaga dívida sem evento explícito.
9. Orçamento de transferências não é caixa: é o menor entre caixa livre projetado, teto aprovado e 35% da receita recorrente restante.

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| custo total da folha | 1,55 × salário | parâmetro inicial |
| líquido de bilheteria | 72% | operação, taxas e tributos estimados |
| reserva mínima | 2 folhas mensais | proteção contra atraso |
| crédito emergencial | 8% da receita/ano | parâmetro editorial |
| juros emergenciais | 1,2% ao mês | calibrável por cenário |
| alerta de atraso | 30/45/60 dias | 60 dias liga à regra legal |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| 30 mil pagantes × R$80 | receita líquida R$1.728.000 |
| salários-base R$10 mi/mês | custo de folha padrão R$15,5 mi |
| venda €10 mi, clube possui 70%, custos 8% sobre sua parte | entrada econômica €6,44 mi antes das parcelas |
| caixa R$5 mi, folha total R$8 mi | reserva exigida R$16 mi; contratações em dinheiro bloqueadas |
| salários vencidos há 61 dias | atleta pode recusar jogo e pedir rescisão; diretoria recebe crise máxima |

## Casos de borda
Receita negativa é estorno; parcela em moeda estrangeira mantém câmbio da data do pagamento; clube sem balanço recebe estimativa por série marcada como tal; aporte não pode ocorrer após fechamento da janela para burlar registro financeiro.

## Liga com
Mercado, diretoria, torcida, contratos, competições e valor.

## Perguntas em aberto
Padronizar “dívida” como dívida líquida financeira ou passivo total; inserir contratos de TV e premiações oficiais quando disponíveis.

## Fontes
[Lei Geral do Esporte, arts. 90–91](https://planalto.gov.br/ccivil_03/_ato2023-2026/2023/lei/l14597.htm); valores-base de clubes em `clubes_estrutura_2026.xlsx`.

