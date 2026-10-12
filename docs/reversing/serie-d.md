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
