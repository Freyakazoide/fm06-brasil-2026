# Análise de código: fichas para você adiantar

Cada ficha é uma parte do `fm.exe` que eu ainda não li. Você abre o código no Ghidra, segue
a ficha e me devolve o que encontrou no [modelo de resposta](analise/MODELO_RESPOSTA.md).
Eu confiro no banco e transformo em mod. Não precisa abrir o jogo nem o FMM.

Já resolvido, como exemplo do que se espera: [EXEMPLO_arbitro.md](analise/EXEMPLO_arbitro.md)
(o leitor do árbitro, que virou o `aplicar_arbitros.py`).

## Preparar o Ghidra (uma vez)

1. Instale o Java 21 (Adoptium Temurin, "JDK 21", instalador .msi) e o Ghidra
   (ghidra-sre.org, o .zip; é só descompactar e abrir o `ghidraRun.bat`).
2. Copie o `fm.exe` **original** (o da instalação, não o `fm_brasil.exe`) para uma pasta de
   trabalho, por exemplo `C:\analise\fm.exe`. Nunca abra o do jogo.
3. No Ghidra: `File > New Project` (Non-Shared), depois `File > Import File` e escolha o
   `fm.exe`. Dê dois cliques nele para abrir o CodeBrowser e aceite a análise automática
   (`Analyze`, opções padrão). Demora de 10 a 30 minutos; deixe terminar.
4. Abra a janela de pseudo-código: `Window > Decompile`. É nela que você lê (parece C).

Atalhos que você vai usar:

| O quê | Como |
|---|---|
| Ir para um endereço | tecla `G`, digite `00aa71e0` |
| Dar nome a uma função ou variável | clique nela e tecle `L` |
| Quem chama esta função | clique no nome da função e `Ctrl+Shift+F` (References to) |
| Procurar texto | `Search > For Strings`, filtre ("sponsor") |
| Voltar | `Alt+←` |

## Como ler um "leitor" do banco

Quase toda ficha é um **leitor**: a função que lê um registro do `server_db.dat` ou do
`people_db.dat`, campo por campo, na ordem do arquivo. No pseudo-código ela é uma
sequência de chamadas assim (depois de dar os nomes do glossário):

    if (!ler_u32(stream, this + 0x20)) return false;   // 4 bytes do arquivo vão para this+0x20
    if (!ler_u16(stream, this + 0x2c)) return false;   // 2 bytes
    ler_u8(stream, this + 0x8);                         // 1 byte

Anote cada leitura em ordem: o que é lido (u8, u16, u32, texto, data), para onde vai
(`this + 0x..`) e, se der, o que é. Para descobrir o que é um campo, procure quem usa
aquele `this + 0x..` em outras funções (clique no campo e `Ctrl+Shift+F`) ou se aparece
perto de um texto de tela ("Sponsorship", "Transfer Budget").

Dois padrões que aparecem muito:

- `if (*(short *)(x + 0xee) >= 0xd2)`: o campo só existe a partir de certa versão do
  banco. Anote o número (0xd2, 0x103...); eu sei a versão do nosso.
- `operator_new(0x1c)` seguido de uma chamada: cria um objeto de 0x1c bytes; a chamada
  seguinte é o construtor e o leitor dele vem depois (é uma lista dentro do registro).

## Glossário: funções que já conheço

Dê esses nomes (tecla `L`) antes de começar; o pseudo-código fica legível.

| Endereço | Nome | O que faz |
|---|---|---|
| `00c59420` | `ler_u8` | lê 1 byte |
| `00c59430` | `ler_u16` | lê 2 bytes |
| `00c59460` | `ler_u16_b` | lê 2 bytes (outra variante) |
| `00c59490` | `ler_u32` | lê 4 bytes |
| `00c594e0` | `ler_4bytes` | lê 4 bytes (número com sinal ou fração) |
| `00c59720` | `ler_objeto` | chama o leitor do próprio objeto (texto, data...) |
| `00c561d0` | `DATA_nova` | cria uma data (dia do ano + ano) |
| `00c587d0` | `data_de_texto` | "dd/mm/aaaa" → data |
| `00c4e070` | `operator_new` | reserva memória para um objeto |
| `00a31c70` | `CLUB_ler` | leitor do clube (`docs/reversing/database.md`) |
| `00a1fa30` | `TEAM_ler` | leitor do time |
| `00a6d540` | `OFFICIAL_ler` | leitor do árbitro (exemplo resolvido) |
| `00aad070` | `cmd_FUTURE_REGEN` | comando FUTURE_REGEN do .edt |
| `00aa8f00`–`00aaa200` | despachante | comandos dos .lnc/.edt |

O leitor de uma classe costuma ser o método 10 da tabela de métodos (vtable): abra o
endereço da vtable da ficha e conte 10 entradas de 4 bytes a partir do zero.

## Fichas

Ordem sugerida: C2, C6, C5, C1, C7, C10, C3, C4, C8, C9 (as primeiras destravam coisa
que já tem planilha pronta).

| Ficha | Assunto | Começar em | Destrava |
|---|---|---|---|
| C1 | Patrocínio | `SPONSOR`, leitor `00aa6ec0` | `patrocinadores_2026.xlsx` |
| C2 | Suspensões no começo do jogo | `STARTING_BAN`, leitor `00aa71e0` | as 2 suspensões da `lesoes_suspensoes_2026.xlsx` |
| C3 | Lesões | `INJURY`, leitor `00a8d4e0` | as 4 lesões da mesma planilha |
| C4 | Prêmios | `AWARD`, leitor `00a174a0` | `premios_historico.xlsx` |
| C5 | Finanças do clube | `CLUB_FINANCE`, leitor `00a80fe0` | orçamentos da `clubes_estrutura_2026.xlsx` |
| C6 | Instalações e base do clube | `CLUB_ler`, de `00a325af` até o fim | CT e base da `clubes_estrutura_2026.xlsx` |
| C7 | Regens e chegada da base | `REGENERATION_MANAGER`, `FUTURE_REGEN_ARRAY` | `regens_futuros_2026.xlsx` e a qualidade dos regens |
| C8 | Regras de transferência do Brasil | `BRA_TRANSFER_RULES` | janelas e limite de estrangeiros de 2026 |
| C9 | Premiação das competições | `COMP_PRIZE_MONEY_NEWS` | `premiacao_2026.xlsx` |
| C10 | Força da base de cada país | leitor da nação `00a49850` | regens mais fortes ou fracos por país |

### C1. Patrocínio (`SPONSOR`)

- **Onde:** vtable `010e1fe4`; leitor (método 10) `00aa6ec0`.
- **Já sei:** o leitor faz `ler_objeto`, `ler_u8`, `ler_objeto`, `ler_u8`, `ler_u8`
  (provavelmente dois textos e três bytes).
- **Perguntas:**
  1. O que é cada um dos 5 campos? (nome do patrocinador? tipo? valor? duração?)
  2. Quem cria os `SPONSOR` (References to do construtor / da vtable): o clube, a nação
     ou uma lista solta? Em que leitor isso acontece?
  3. O valor do patrocínio vem desse registro ou é calculado? Procure onde o
     `FINANCES_INCOME_PANEL` mostra "Sponsorship".

### C2. Suspensões no começo do jogo (`STARTING_BAN`)

- **Onde:** vtable `010e2144`; leitor `00aa71e0`.
- **Já sei:** `ler_u32`, um objeto lido pelo método `+0x14` dele, `ler_u8`.
- **Perguntas:**
  1. O `u32` é o UID da pessoa, o índice dela ou outra coisa? (veja onde ele é usado
     depois: se procura uma pessoa, é a pessoa.)
  2. O objeto do meio é uma data? Uma competição?
  3. O `u8` é o número de jogos?
  4. Quem cria os `STARTING_BAN`: em que leitor do banco ficam (pessoa? competição?)
- **Por que é a primeira:** se for (pessoa, competição, jogos), eu gravo as suspensões
  de 2026 direto no banco.

### C3. Lesões (`INJURY`)

- **Onde:** vtable `010e1e84`; leitor `00a8d4e0`. Ver também `INJURY_MANAGER` (vtable
  `010a707c`) e as classes `INJURY_HISTORY`, `INJURY_DANGER_DATE`.
- **Já sei:** o leitor faz `ler_objeto`, `ler_u8`, `ler_u8`, `ler_objeto`, `ler_u8`.
- **Perguntas:**
  1. Este registro é o **tipo** de lesão (nome, gravidade, dias) ou a lesão de **um
     jogador** (quem, quando, até quando)?
  2. Se for o tipo: onde fica a lesão de um jogador (quem cria a lesão ativa e onde ela é
     guardada no jogador)?
  3. Existe lesão que já vem do banco no começo do jogo (como o `STARTING_BAN`)?

### C4. Prêmios (`AWARD`)

- **Onde:** vtable `010e18f4`; leitor `00a174a0`; ver `AWARD_DATA` (vtable `00e322b4`) e
  `AWARD_MANAGER`.
- **Já sei:** o leitor tem uns 25 campos (vários `u8`, dois `u16`, vários `u32`).
- **Perguntas:**
  1. Quais campos dizem o que é o prêmio (competição ou nação, tipo, mês/ano)?
  2. Onde fica a lista de **vencedores** de anos anteriores (quem lê; é parecida com a
     dos campeões, `docs/reversing/database.md`)?

### C5. Finanças do clube (`CLUB_FINANCE`)

- **Onde:** vtable `010efe14` (base `CLUB_FINANCE_BASE`, vtable `010ef344`); leitor
  `00a80fe0`. O objeto é criado no `CLUB_ler` (um `u8` de tipo: 1 cria o objeto grande
  de 0x280 bytes, 0 o pequeno de 0x1c).
- **Já sei:** o leitor começa com `ler_u32` em `+0x20`, `+0x1c`, `+0x28`, `+0x2c`...;
  o saldo e o público do clube já são gravados pelo `financas.py`.
- **Perguntas:**
  1. Liste todos os campos do leitor em ordem (até o fim da função).
  2. Quais são o orçamento de transferências e o de salários? (as telas
     `FINANCES_TRANSFERS_PANEL` e `FINANCES_SALARY_PANEL` mostram esses valores: veja de
     qual `this + 0x..` elas leem.)
  3. Algum é recalculado pelo jogo no começo (a partir do saldo e da reputação)? Se for,
     gravar no banco não adianta e eu tenho de ir pela regra.

### C6. Instalações e base do clube (fim do `CLUB_ler`)

- **Onde:** `CLUB_ler` (`00a31c70`), do endereço `00a325af` até o `ret`. Antes disso já
  está resolvido (nomes, cores, times do clube, lista de relações/rivais).
- **Já sei:** no arquivo, depois da lista de rivais vêm 18 bytes e o par (índice, UID).
  No Flamengo esses 18 bytes são `0c 00 0c 0e 10 0c 07 07 0b 0e 08 0d 10 18 03 02 04 00`;
  no Botafogo há números de 1 a 20 parecidos; no Vasco, quase tudo zero.
- **Perguntas:**
  1. Em ordem, o que o leitor lê depois de `00a325af` (tipos e destino `this + 0x..`,
     com as condições de versão)?
  2. Quais desses campos são instalações de treino, instalações da base e captação da
     base? (procure quem usa os campos: o painel de informações do clube e a chegada
     da base.)

### C7. Regens e chegada da base

- **Onde:** `REGENERATION_MANAGER` (vtable `010b6c78`), `FUTURE_REGEN_ARRAY` (vtable
  `010f18a4`), `YOUTH_PLAYER`, e o comando `cmd_FUTURE_REGEN` (`00aad070`), que guarda o
  regen futuro na nação (`00a48c00` ou `00a48c10`, conforme a idade).
- **Perguntas:**
  1. Quando acontece a chegada da base de cada país (data fixa? por nação?)
  2. O que decide a qualidade do regen: campos do clube (base), da nação, reputação?
  3. Como o jogo usa a lista de `FUTURE_REGEN`: idade em que o garoto aparece, se precisa
     ser no clube favorito, o que acontece se o clube não tiver vaga.

### C8. Regras de transferência do Brasil (`BRA_TRANSFER_RULES`)

- **Onde:** vtable `0113dbf8` (as outras nações têm a mesma estrutura: `ARG_`, `CHI_`...).
- **Perguntas:** datas das janelas de transferência, limite de estrangeiros (inscritos e
  em campo), regras de empréstimo. Anote o endereço de cada número (são os que eu troco
  por patch, como fiz com o calendário).

### C9. Premiação das competições

- **Onde:** a notícia `COMP_PRIZE_MONEY_NEWS` (vtable `010afe4c`). Procure quem cria essa
  notícia: ali perto o jogo calcula ou lê o valor do prêmio.
- **Perguntas:** de onde vem o valor (tabela no `fm.exe`, campo da competição no banco,
  cálculo pela reputação)? Para o Brasil, onde estão os valores da Série A e da Copa do
  Brasil?

### C10. Força da base de cada país (nação)

- **Onde:** leitor da nação, `00a49850` (método 10 da vtable `010f1934`).
- **Já sei:** na memória, a nação tem "Development" em `+228` (u8), "Economic Factor"
  em `+233` e "Reputation" em `+252` (achados com o FMM antes); "League Standard" é
  `+230` ou `+231`.
- **Perguntas:** em que ponto do leitor esses campos são lidos (para eu achar os bytes no
  `server_db`)? Há outros campos da nação que mexem nos regens ("youth rating")?

## Como mandar

Copie o [modelo de resposta](analise/MODELO_RESPOSTA.md) para `docs\analise\C2.md` (o
número da ficha), preencha e faça commit e push, ou cole aqui. Pode mandar parcial: uma
tabela com metade dos campos já adianta.
