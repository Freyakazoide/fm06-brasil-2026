# Plano: Série D e formato 2026

## Formato alvo (2026)

| Série | Clubes | Formato |
|---|---|---|
| A | 20 | pontos corridos, ida e volta |
| B | 20 | pontos corridos, ida e volta |
| C | 20 | fase de liga + fase final |
| D | 64+ | grupos + mata-mata |

## O que o FM06 tem hoje

| Série | Clubes | Formato | Classe / fase |
|---|---|---|---|
| A | 20 | liga | `0xBB2CC0` / `0xBBA400` |
| B | 20 | liga | `0xBB2DF0` / `0xBBA6A0` |
| C | 128 | 16 grupos de 8 (2 avançam) + mata-mata de 32 | `0xBB2EC0` / `0xBBFD00` |
| D | — | não existe | — |

A e B já têm o tamanho de 2026. A **Série C de 2005 tem o formato da Série D
de 2026** (grupos + mata-mata).

## Estratégia escolhida

1. **A Série C atual vira a Série D.**
   - Renomear por `.lnc`: `COMP_NAME_CHANGE 107192`.
   - Redimensionar por patch: `serie_c_64_clubes` (8 grupos de 8, avançam 4,
     mata-mata de 32), aguardando teste.
2. **Criar uma Série C nova** (20 clubes, liga) entre a B e a antiga C.
   - **Competição no banco:** reaproveitar uma competição brasileira
     nacional que já existe e não seja usada, renomeada por `.lnc`. Exemplos
     da tabela do `server_db`: Taça de Prata (319191), Champions Cup (309690).
   - **Código** (code cave):
     - `bra_get_settings` (`0xBB2710`): inserir a nova C no nível 2 e mover a
       antiga C para o nível 3; `finalizar(3)` passa a ser `finalizar(4)`.
     - `bra_setup_comps` (`0xBBA2C0`): construir a nova competição com um
       clone do construtor da Série B (`0xBB2DF0`) trocando o ID, e uma vtable
       clonada cujo slot 71 aponta para um clone da fase da Série B
       (`0xBBA6A0`) com destinos trocados: acesso para a B, rebaixamento para
       a antiga C.
     - Série B: rebaixamento passa a apontar para a nova C.
     - Antiga C (agora D): acesso passa a apontar para a nova C.
     - `bra_get_minimum_division_teams`: incluir a nova C com 20.
   - **Espaço para código novo:**
     - `.text` termina em VirtualSize 0xA2F3C2 dentro de 0xA30000 de dados
       crus, o que dá cerca de 3 KB livres;
     - `.rdata` tem cerca de 2,5 KB livres (0x48960B de 0x48A000).

     Dá para um construtor, uma fase e uma vtable clonados. Se faltar
     espaço, acrescentar uma seção nova ao executável.

## Testes no jogo

| Teste | Resultado |
|---|---|
| `serie_c_64_clubes` | ✅ 8 grupos de 8, "as quatro primeiras equipas qualificam-se", últimas 2 rebaixadas, 14 jogos por clube. Os 64 clubes que sobram continuam **cadastrados** na 3ª Divisão (ex.: Tubarão), mas sem grupo nem jogos. |
| `serie_a_datas_2026` | ✅ 29.1.2006 – 3.12.2006: o jogo arredonda para o domingo seguinte (28/1 e 2/12 de 2006 não são domingo) |

## Como a competição se liga ao banco

- Construtor base `FUN_00acf2f0(id, tipo, nível)`: chama `FUN_009ed0a0(id)`,
  que liga o objeto ao registro da competição no banco pelo ID. Guarda o tipo
  em `+0xAD` e o nível em `+0xB8`. Série A = (0x19017, 0, 0),
  B = (0x1A2B7, 1, 1), C = (0x1A2B8, 1, 2).
- `FUN_00ad0050(id, nível, flag)`: só registra o par no sistema de ligas da
  nação (lista em `+0x28`).
- `0x00ACAC30`: monta as fases chamando o método 71 de cada competição; a
  primeira fase recebe −1 (usa o tamanho padrão do código), as seguintes
  recebem a quantidade que veio da fase anterior.
- O executor do `SWAP_TEAMS` (tipo 0xA) está em `0x00AAC550`. Ele troca
  entre os dois clubes os campos `+0x54`, `+0x5C`, `+0x60` (byte) e `+0x64`,
  e `+0xDC`/`+0xEA` de um objeto obtido por `0x00A18CD0`. A divisão do clube
  está entre eles.
- Rodada 5 (decompilado do executor, `0x00AADB90` caso 10, conferido no
  disassembly em `0x00AAC550`):
  - `0x00AAABD0` acha pelo nome um objeto da lista global
    (`DAT_014EAA84`, item por `0x009E8CF0`). Pelo RTTI, é um **`TEAM`**
    (vtable `0x010EDF6C`), não o `CLUB` (vtable `0x010EFFCC`).
  - `0x00A18CD0(team)` devolve `team+0x38` (o `CLUB`) se `team+0x40 == 0`
    (0 = time de clube; senão, seleção).
  - `0x00A18CE0(team)` devolve `CLUB+0xDC`. Sondagem: é o **país**
    (`NATION`) do clube, não a divisão. Por isso `TEAM+0x64` só é trocado
    quando os países diferem. A divisão deve estar em `TEAM+0x5C` ou
    `TEAM+0x64`.
  - A troca: `TEAM+0x54`, `CLUB+0xDC`, `TEAM+0x5C`, `TEAM+0x64` (só se os
    `CLUB+0xDC` forem diferentes), `TEAM+0x60` (byte) e `CLUB+0xEA` (byte).
  - 1ª sondagem com essa leitura falhou porque tratou o `CLUB` como `TEAM`
    (desceu +0x38 a mais). No `CLUB`, `+0x64` é um `ARRAY<TEAM*>`
    (vtable `0x00E4DAD4`), constante em todos.
- `PLAY_COMPETITION` (tipo 0x24) em `0x00AA84C0` só grava o `unid` lido em
  `DAT_014EAB2C`.
- Executor de todos os comandos: `switch` em `0x00AADB90`, tabela em
  `0x00AADC5C`.
- Medição na memória (objetos com assinatura `0x010EFFCC 0x010EFFB8`,
  2.103 clubes): `+0x54` só vale 0–3 (1.409 clubes com 2); `+0x5C` e `+0x60`
  são ponteiros únicos por clube; `+0x64` é igual para todos. Nenhum desses
  campos é a divisão. O objeto que o `SWAP_TEAMS` troca deve ser outro tipo,
  provavelmente o "time" do clube (`[Club Team]` no FMM). Rodada 5 do Ghidra
  investiga isso.
- Ferramenta para achar o campo "divisão" do clube na memória:
  `scripts/probe_club_division.py`.

## O que ainda falta descobrir

1. **Como o New Game coloca clubes numa divisão.** O ID da competição
   (102423) quase não aparece no `server_db`; provavelmente os clubes
   apontam para o índice da competição na tabela (A = 73, B = 85, C = 86).
   Busca por UID de clube é inconclusiva (UIDs pequenos são ruído). Caminhos:
   o parser de clubes do repo (`src/fm06patch/server_db.py`) e a memória do
   jogo (objeto Club, `docs` do FMM).
2. **O que acontece quando a divisão tem mais clubes no banco do que vagas.**
   O teste `serie_c_64_clubes` responde isso: 128 clubes cadastrados, 64 vagas.
3. Regras da antiga C para quem vem de baixo: hoje rebaixa para `0x13DBB8`.

## Divisão inicial no banco (`server_db.dat`)

Sondagem com o jogo aberto (New Game Brasil, `fm_teste.exe`):

| Campo | Conteúdo |
|---|---|
| `CLUB+0xDC` | país do clube (`NATION`), não a divisão |
| `TEAM+0x54` | **divisão atual**: 20 times → `BRA_NAT_FIRST`, 20 → `BRA_NAT_SECOND`, 128 → `BRA_NAT_THIRD` |
| `TEAM+0x5C` | divisão da temporada passada |
| `TEAM+0x60` | classificação na temporada passada (byte) |
| `TEAM+0x64` | estadual (`BRA_STATE_*`) |

O objeto de regras de cada série é a própria competição (classe derivada de
`COMP`). Mesmo com a Série C em 64, os 128 times continuam apontando para ela;
o jogo só monta grupos para os primeiros.

Leitura do banco: o método 10 da vtable do `TEAM` (`0x00A1FA30`) lê, em
ordem, byte `+0x60`, word `+0x6C` (reputação), word, u32 `+0x54`, u32
`+0x5C`… O método 11 (`0x00A20760`) converte esses u32 em ponteiros com
`0x009E8280` (índice na lista de competições; `FFFFFFFF` = nenhuma).

No arquivo, o registro do time é:

```
u32 UID do clube | 0A 00 | u8 classificação anterior | u16 reputação | 00 00 |
u32 divisão atual | u32 divisão anterior
```

Índices: Série A = 73, B = 85, C = 86 (os mesmos da tabela de competições).
O padrão acha exatamente 20, 20 e 128 registros. A classificação anterior
bate com o Brasileirão 2004 (Santos 1º, São Paulo 3º, Palmeiras 4º; Grêmio,
Guarani, Vitória e Paysandu rebaixados).

Ferramenta: `scripts/server_db_teams.py` (`--list`, `--set "TIME=SÉRIE"`,
`--pos`, `--last`, `--apply`, `--restore`). Código em
`src/fm06patch/server_teams.py`.

Consequência para a Série D: os times entram numa série pelo índice gravado
no banco. A Série D precisa de um objeto de competição novo (code cave em
`bra_setup_comps`) ligado a um registro da tabela de competições; depois basta
gravar esse índice nos times dela.

## Patch `serie_c_nova` (code cave, a testar)

Código em `src/fm06patch/exe_cave.py`; aplicado por `scripts/patch_exe.py`.

- Competição do banco reaproveitada: **Taça de Prata** (ID 319191, índice
  376), registro brasileiro que nenhum código do jogo cria. Outras opções:
  Brazilian Champions Cup (309690), Taça Brazil (311872).
- `bra_get_settings`: nova C no nível 2, antiga C no nível 3, `finalizar(4)`.
- `bra_setup_comps`: cria a nova C logo depois da antiga C.
- `bra_get_minimum_division_teams`: nova C com 20.
- Classe: cópia do construtor da Série B (ID 319191, nível 2) com uma cópia
  da vtable da B (150 métodos) cujo método 71 é uma cópia da fase da B:
  20 clubes, acesso de 4 para a Série B, rebaixamento de 2 para a antiga C.
- Série B rebaixa para a nova C; antiga C sobe para a nova C; antiga C passa
  ao nível 3 no construtor.
- Áreas livres usadas: `.text` 0x00E303D0–0x00E30750, `.rdata`
  0x012BA610–0x012BA86C. VirtualSize das duas seções ampliado até o fim dos
  dados crus.

Ainda iguais à Série B na nova C: datas, horários, ID de tipo da classe e o
resto dos métodos. A função `0x00BB9550` (provável Copa do Brasil, até 64
clubes de A, B e C) não inclui a nova C.

Teste: `patch_exe.py serie_c_nova serie_c_64_clubes` +
`server_db_teams.py --top "C:20:NOVA_C" --apply`.
