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
