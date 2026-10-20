# C5 — Mercado de transferências brasileiro

## Objetivo
Representar contratos, janelas, empréstimos, luvas, pré-contrato e participações econômicas sob regras atuais, com decisões explicáveis da IA.

## Regras
1. Terceiro (empresário, fundo) não pode possuir direito econômico de jogador. O jogo aceita percentuais entre clubes e cláusula de mais-valia; legado pré-2015 só existe em saves históricos.
2. Transferência só é registrada com soma das participações dos clubes em 100%, documentos completos, vaga de inscrição e janela aberta.
3. Multa nacional pode chegar a 2.000 vezes o salário médio contratual; multa internacional é livre. O preço negociado pode ser diferente.
4. Pré-contrato é permitido nos seis meses finais. A IA compara salário total, luvas, bônus, papel no elenco e reputação.
5. Luvas são custo garantido, pago à vista ou parcelado; entram no custo total do contrato mesmo se o atleta sair cedo.
6. Empréstimo define salário pago por cada clube, taxa, opção ou obrigação, gatilho da obrigação e permissão para enfrentar o dono.
7. Janelas nacionais de 2026: 05/01–03/03 e 20/07–11/09. Fora delas, negociar é permitido, mas registro espera a próxima janela, salvo exceção regulamentar.
8. Mecanismo de solidariedade reserva até 5% da compensação internacional aos clubes formadores, distribuído por idade conforme a regulamentação FIFA.
9. IA compradora calcula utilidade de 0–100: qualidade 35, necessidade 25, potencial 15, custo total 15, adaptação 10. Faz oferta se utilidade ≥ 62 e orçamento comportar 18 meses.
10. IA vendedora aceita quando oferta líquida ≥ preço mínimo e substituto é viável; titular na reta decisiva exige prêmio de 15–35%.

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---:|---|
| pré-contrato | últimos 6 meses | regra internacional |
| solidariedade | até 5% | FIFA |
| multa nacional máxima | 2.000 × salário médio | Lei 14.597/2023, art. 86 |
| análise de caixa | 18 meses | parâmetro editorial |
| piso de utilidade da IA | 62/100 | calibrável |

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|
| clube A tem 60%, clube B 20%, ex-clube C 20% | válido: três clubes somam 100%; empresário não pode ser titular |
| clube A 80%, “agente” 20% em 2026 | inválido; registro bloqueado |
| contrato termina 30/06 e proposta em 01/01 | pré-contrato permitido; transferência sem taxa em 01/07 |
| empréstimo com obrigação após 15 jogos; atleta faz 15º | compra torna-se obrigação e cria contas a pagar |
| negociação em 10/04 sem exceção | contrato pode ser acordado; registro só na janela de julho |

## Casos de borda
Percentuais arredondados devem fechar em 100,00%; atleta livre pode assinar fora da janela, mas inscrição segue regulamento; transferência parcelada converte moeda por vencimento; queda de divisão não cancela obrigação de compra salvo cláusula.

## Liga com
Valor, economia, inscrições, contratos, carreira e notícias.

## Perguntas em aberto
Limites de inscrição de cada competição devem vir do arquivo C11; definir exceções de janela por rescisão e retorno de empréstimo.

## Fontes
[Lei Geral do Esporte](https://planalto.gov.br/ccivil_03/_ato2023-2026/2023/lei/l14597.htm), [janelas CBF 2026](https://www.cbf.com.br/a-cbf/por-dentro-da-cbf/comissao-dopagem/a/cbf-oficializa-datas-do-calendario-do-futebol-do-brasil-profissional-masculino-de-2026), [FIFA — Third-party influence/ownership](https://img.fifa.com/image/upload/jhre73qeqmjn6hzi81rn.pdf).

