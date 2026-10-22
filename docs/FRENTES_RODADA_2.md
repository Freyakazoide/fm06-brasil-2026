# Frentes por fora, rodada 2 (22/10/2026)

A rodada 1 ([FRENTES_DE_TRABALHO.md](FRENTES_DE_TRABALHO.md)) virou mod: tradução,
perfis, comissão, árbitros, rivais, histórico de carreira e nomes de regens. Esta rodada
tem dois tipos de entrega, os dois sem abrir o jogo:

- **Planilhas:** dados para completar nos modelos de `data\modelos`.
- **Análise de código:** fichas de partes do `fm.exe` para você ler no Ghidra e me
  devolver como funcionam ([ANALISE_DE_CODIGO.md](ANALISE_DE_CODIGO.md)).

## Como entregar

1. Planilha: preencha o arquivo de `data\modelos` e salve com o mesmo nome.
2. Rode `python scripts\validar_entregas.py` e corrija o que aparecer em `[CONFIRA]`
   (nome que não bate com a `jogadores_2026.xlsx`, clube que não é de 2026, data fora do
   formato, nota fora de 1-20).
3. Ficha de código: copie `docs\analise\MODELO_RESPOSTA.md` para `docs\analise\C2.md`
   (o número da ficha) e preencha.
4. Mande: `git add`, `git commit` e `git push`, ou cole aqui.

As três regras de ouro continuam: fonte e data em todo dado real; branco é "não sei";
nome do clube e do jogador igual ao da `jogadores_2026.xlsx`.

## Planilhas

| Planilha | O que é | Quando entra | Ficha que destrava |
|---|---|---|---|
| `regens_futuros_2026.xlsx` (nova) | joias da base de 2026 (sub-17, sub-15) que não estão no elenco | já: vira `FUTURE_REGEN` no `.edt` | — |
| `patrocinadores_2026.xlsx` (nova) | patrocínio de cada clube (master, material esportivo...), com valor se divulgado | depois da ficha | C1 |
| `premiacao_2026.xlsx` (nova) | premiação de 2026 por posição ou fase (Séries, Copa do Brasil, CONMEBOL) e cotas de TV | depois da ficha | C9 |
| `premios_historico.xlsx` (nova) | vencedores de 2006 a 2025 (Bola de Ouro, Bola de Prata, Craque do Brasileirão, artilheiro) | depois da ficha | C4 |
| `clubes_estrutura_2026.xlsx`, aba Estrutura | CT e base (1-20), orçamento de contratações e folha dos 40 clubes das Séries A e B | depois das fichas | C5, C6 |
| `lesoes_suspensoes_2026.xlsx` | já preenchida; falta corrigir as 2 suspensões do Remo | depois das fichas | C2, C3 |
| `data\brasil\comissao\selecoes_2026.csv` | técnicos das 8 seleções sul-americanas em branco | já | — |
| `historico_carreira.xlsx` | mais jogadores (titulares das Séries A e B fora dos 100) | já | — |
| `jogadores_perfil.xlsx` | perfis dos titulares da Série B | já | — |

Detalhes de cada coluna na aba `LEIA` de cada planilha.

Correção que o validador achou: **Nico Ferreira e Diego Hernández** (suspensões do Remo)
não estão no elenco do Remo na `jogadores_2026.xlsx`. Confira o nome lá (ou se saíram).

**Joias da base:** comece com 3 a 5 garotos para testar. Só quem **não** está na
`jogadores_2026.xlsx`, nascidos de 2008 a 2012 (convocações sub-17 e sub-15, Copinha,
matérias sobre a base). O jogo sorteia atributos e posição; o nome, a data e o clube são
os da planilha.

**Régua para CT e base (1-20):** 20 = os melhores do Brasil (Ninho do Urubu, Academia de
Futebol, Cotia, Xerém); 10 = CT próprio simples; 5 ou menos = sem CT.

## Análise de código

As fichas, o guia do Ghidra, o glossário de funções já conhecidas e um exemplo resolvido
estão em [ANALISE_DE_CODIGO.md](ANALISE_DE_CODIGO.md). Resumo:

| Ficha | Assunto | Destrava |
|---|---|---|
| C1 | Patrocínio (`SPONSOR`) | patrocínio de 2026 |
| C2 | Suspensões no começo do jogo (`STARTING_BAN`) | as suspensões de 2026 direto no banco |
| C3 | Lesões (`INJURY`) | as lesões de 2026 |
| C4 | Prêmios (`AWARD`) | vencedores de 2006 a 2025 |
| C5 | Finanças do clube (`CLUB_FINANCE`) | orçamento de contratações e de salários |
| C6 | Instalações e base (fim do leitor do clube) | CT e base de 2026 |
| C7 | Regens e chegada da base | qualidade dos regens e uso das joias |
| C8 | Regras de transferência do Brasil | janelas e limite de estrangeiros de 2026 |
| C9 | Premiação das competições | premiação de 2026 |
| C10 | Força da base de cada país | regens mais fortes ou fracos por país |

Comece pela C2 (curta e já tem planilha esperando) e pela C6.

## Como fazer regens diferentes

| Alavanca | Situação | Como |
|---|---|---|
| Nomes dos regens | ✅ no mod | `nomes_regens.xlsx`: nomes de hoje com ~70% do peso de cada nação |
| Garotos reais na base | 🆕 testar | `regens_futuros_2026.xlsx` (`FUTURE_REGEN`): nome, data e clube de verdade |
| Qualidade da base de cada clube | ⏳ | ficha C6 + aba Estrutura: o campo de base do clube |
| Força da base de cada país | ⏳ | ficha C10: "Development" / "League Standard" da nação |
| Quando e como a base chega | ⏳ | ficha C7 |
| Posição e atributos de um regen sorteado | ❌ | o jogo sorteia; só dá para mexer depois que ele nasce (injetor) |
