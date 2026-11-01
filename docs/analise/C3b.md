# Ficha C3b — Lesões do começo do jogo

- Quem analisou / data: Claude, 2026-11-01
- Ferramenta: Capstone + pefile (`workspace/rea/tools/pe.py`), `fm.exe` 6.0.2 original,
  `server_db.original.dat` e `people_db.original.dat`
- Pergunta (docs/ANALISE_DE_CODIGO.md): onde fica a lesão de um jogador; dá para gravar as
  lesões de 2026 da `lesoes_suspensoes_2026.xlsx`?

## Conferido no código e no banco

### A tabela STARTING_INJURY

- O RTTI tem `DATABASE_TABLE<STARTING_INJURY>` ao lado de `DATABASE_TABLE<INJURY>` (o
  catálogo da ficha C3). Classe `STARTING_INJURY`: vtable `0x010E21F4` (e mais quatro de
  herança, `0x010E2198`…`0x010E21E0`), construtor `0x009EDDE0`, chamado só de `0x00A0E28E`.
- Leitor (método 10, `0x00AA7390`):
  - u32 em +0x1C e u32 em +0x20 (`0x00C59490`);
  - DATE em +0x24 e DATE em +0x2C (método +0x14 do objeto);
  - u8 em +0x34, +0x35 e +0x36;
  - o fim comum (`0x00A3AE50`).

  Depois, o registro entra na lista `[banco+0x98]` (`0x00AA743B`).
- Método 11 (`0x00AA7280`): resolve +0x1C por `0x009E3720` e +0x20 por `0x009E8360`
  (referências a objetos).
- O carregador do `server_db` (`0x00A117C0`) lê as listas em sequência:
  - COMP_HISTORY (+0x88, `0x00A0AE50`);
  - +0x94 (`0x00A0DCE0`);
  - **+0x98 (`0x00A0E190`, STARTING_INJURY)**;
  - +0x9C…

### No banco original

- A lista +0x94: 4.167 registros de 31 bytes em `0x13AEAAA`.
- Logo depois, a STARTING_INJURY: u32 1.225 em `0x13CE347` e registros de 28 bytes,
  `u8 0, u32 pessoa, u32 lesão, u16 dia, u16 ano, u16 dia, u16 ano, u8, u8, u8, u32 índice,
  u32 FFFFFFFF`.
- 807 registros têm data de início e 418 têm 0/1900 (sem data). Os três u8 são 0 em 709
  dos 807 com data; nos sem data costumam ser 0/1 e 1/0. O significado não foi visto.
- **A pessoa é o índice que fecha o registro da pessoa no `people_db`**:
  - 317 = Filippo Inzaghi (UID 811), lesão 11 "strained ankle ligaments", 31/5 a 31/8/2005;
  - 71 = Johan Mjällby, lesão 26 "torn knee ligaments" até 2006.
- A lista não está em ordem de pessoa; 41 pessoas têm mais de um registro.
- **A lesão é o índice no catálogo INJURY**: 83 tipos, u32 83 em `0x5C8041`. Cada registro
  traz o nome curto e o nome com artigo em UTF-16 ("twisted ankle" / "a twisted ankle") e
  fecha com o próprio índice. Os usados aqui: 9 damaged heel, 21 broken leg (lower),
  25 damaged knee cartilage.

## Consequência

`src/fm06patch/lesoes.py` e `scripts/aplicar_lesoes.py`, na etapa 3 do `aplicar_tudo`, logo
depois do `montar_elencos` (é ele que define os hospedeiros):

- acham o jogador pelo clube e nome na `jogadores_2026.xlsx` (nascimento), pelo nome e
  nascimento no `brasil_2026_jogadores.json` (UID) e pelo UID no `people_db` (índice);
- traduzem a coluna "lesao" para o tipo por palavras inteiras (`KINDS`);
- acrescentam o registro no fim da lista, com as datas do motor (ano − 20) e os três u8
  em 0. O `server_db` é lido em sequência, então a lista pode crescer;
- rodar de novo não duplica.

| Jogador | Pessoa | Lesão | Datas (real) | Motor |
|---|---|---|---|---|
| Neymar (Santos) | 139156 | 25 damaged knee cartilage | 22/12/2025 a 15/2/2026 | (355, 2005) a (45, 2006) |
| Saúl Ñíguez (Flamengo) | 132946 | 9 damaged heel | 20/1 a 30/4/2026 | (19, 2006) a (119, 2006) |
| Germán Cano (Fluminense) | 134987 | 25 damaged knee cartilage | 10/1 a 2/4/2026 | (9, 2006) a (91, 2006) |
| Paulinho (Palmeiras) | 134780 | 21 broken leg (lower) | 1/7/2025 a 30/4/2026 | (181, 2005) a (119, 2006) |

Hipóteses a ver no jogo:
1. A 1ª data é o início e a 2ª a volta.
2. Saúl e Cano começam depois do início do jogo (o New Game é no dia 359 de 2005 do motor,
   ficha C1b). Não se sabe se o jogo aplica uma lesão com início no futuro.

## Diário

- 01/11, tabela achada e lesões escritas (acima). Testes:
  - a lista original está em `0x13CE347` com 1.225 registros;
  - Inzaghi = pessoa 317, lesão 11;
  - `person_index` dá 811 → 317 e 114 → 71;
  - a inserção no banco falso e no original não mexe no resto do arquivo e não duplica;
  - o texto da planilha vira o tipo certo ("calcanhar" não cai em "lca").
- 01/11, instalado (`aplicar_tudo --rapido`, etapa 3 `aplicar_lesoes.py --apply`): no
  `server_db.dat` do jogo a lista está em `0x13D512C` (o banco cresce antes dela) com 1.229
  registros; os 4 últimos são os da tabela acima. Falta ver no jogo.
- 01/11, no jogo: Neymar e Paulinho **começam lesionados** (deu certo). Saúl e Cano **sem
  efeito**: não começam lesionados nem se machucam quando a data de início chega. Conclusão:
  1ª data = início e só vale lesão que já começou no New Game. Decidido (usuário): todos
  começam lesionados, como o Neymar. O início vai no máximo até `LATEST_START` = 22/12/2025
  (o do Neymar); a volta continua a da planilha. Instalado: Saúl e Cano agora começam em
  (355, 2005). Falta ver no jogo.
