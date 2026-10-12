# Arquivos de comando EDT / DDT / LNC (FM06 6.0.2)

O FM06 aplica arquivos de texto com comandos ao criar um **New Game**. É o
mecanismo oficial da SI para alterar o banco sem tocar nos `.dat`.

## Como o jogo carrega

Observado com Process Monitor durante um New Game:

| Ordem | O que o jogo faz |
|---|---|
| 1 | lê `server_db.dat` e `lang_db.dat` |
| 2 | procura `*.lnc` em `data\db`, `data\db\lnc` e `data\db\lnc\all` |
| 3 | procura `*.ddt` em `data\db` e lê o que encontrar |
| 4 | lê `people_db.dat` inteiro, em sequência |
| 5 | procura `*.edt` em `data\db`, `data\db\lnc` e `data\db\lnc\all` |
| 6 | lê `pl_hist_*.dat` |

- `client_db.dat` não foi lido durante o New Game.
- Arquivos novos colocados nessas pastas são aplicados automaticamente.
  Também aparecem em *Preferences → Options*.
- `.edt` e `.ddt` são texto ANSI. `.lnc` é UTF-16 com BOM.
- Formato: uma linha por comando, `"COMANDO"` seguido dos argumentos. Strings
  vão entre aspas, separadas por espaço ou TAB. Linhas com `#` são comentário.

## Testado no jogo

| Comando | Arquivo | Linha | Resultado |
|---|---|---|---|
| `CHANGE_PLAYER_NAME` | `lnc\all\teste.lnc` | `"CHANGE_PLAYER_NAME" 3100367 "Teste" "" "Funcionou"` | ✅ Saviola virou "Teste Funcionou" |
| `SWAP_TEAMS` | `teste.edt` | `"SWAP_TEAMS" "Flamengo" "Figueirense"` | ✅ Flamengo na Série B, Figueirense na Série A |
| `SWAP_TEAMS` | `harchester.edt` | `"SWAP_TEAMS" "151988" "737"` (linha comentada pela SI) | ❌ o jogo crashou |
| `FUTURE_TRANSFER` | `teste_transfer.edt` | 10 argumentos (formato do fórum) | ❌ ignorado; o FM06 exige 11 |

## Argumentos de cada comando (extraídos do `fm.exe`)

O despachante de comandos fica em `fm.exe` VA `0x00AA8F00`–`0x00AAA200`.
Cada comando recebe um código de tipo e um ponteiro para a lista de
argumentos. A lista é uma sequência de códigos de 4 letras gravados
invertidos (`'maet'` = `team`). Os nomes dos comandos estão em `.rdata`, a
partir de `0x0110C8E8`.

| Comando | Argumentos, em ordem |
|---|---|
| `RETAIN_PLAYERS` | team |
| `RETAIN_NATION_PLAYERS` | natn |
| `SET_INTERNATIONAL_PLAYER` | unid, name |
| `INT_RETIREMENT` | frnm, cmnm, scnm, team |
| `GROUND_SHARE` | team, stad, date |
| `FAKE_TEAM` | team |
| `RANDOMISE_TEAM` | team |
| `SELL_ON_PERCENTAGE` | frnm, cmnm, scnm, dob, sllt, perc |
| `MATCH_BAN` | bant, frnm, cmnm, scnm, team, numb |
| `PLAY_COMPETITION` | unid |
| **`FUTURE_TRANSFER`** | **frnm, cmnm, scnm, team, buyt, stdy, stmn, styr, cash, wage, cnln** |
| `STADIUM_MOVE` | team, stad, nwst, date |
| **`SWAP_TEAMS`** | **team, ottm** |
| `BOOST_TEAM` | team, cash, repu, atte |
| `INTERNATIONAL_FRIENDLY` | date, hmtm, awtm, stad |
| `CANNOT_FLY` | frnm, cmnm, scnm, team |
| `RETIRED_SQUAD_NUMBER` | team, sqnm |
| `DOMESTIC_` / `CONTINENTAL_` / `INTERNATIONAL_MANAGER_RECORD` | frnm, cmnm, scnm, naty, dob, hoft, natn, tplw, cuwo |
| `STADIUM_CHANGE_FOR_COMP` | team, comp, stad |
| `STADIUM_CHANGE_FOR_MATCH` | team, tea2, stad |
| `FUTURE_REGEN` | frnm, cmnm, scnm, dob, naty, fave |
| `STADIUM_CAPACITY_CHANGE` | stad, date, capc |
| `<CLUB\|CITY\|COMP\|AWARD\|STADIUM>_NAME_CHANGE` / `_SHORT_NAME_CHANGE` / `_LONG_NAME_CHANGE` | unid, name, lang |
| `<CLUB\|CITY\|COMP\|AWARD\|STADIUM>_GENDER_CHANGE` | unid, gend, lang |
| `COLOUR_CHANGE` | unid, indx, red1, gre1, blu1, red2, gre2, blu2 |
| `FAKE_NATIONAL_TEAM` | unid, enab |
| `CHANGE_PLAYER_NAME` | unid, frnm, cmnm, scnm |
| `AVERAGE_POINTS_2` | team, unid, comp, y1pt, y1gm, y2pt, y2gm |
| `AVERAGE_POINTS_3` | team, unid, comp, y1pt, y1gm, y2pt, y2gm, y3pt, y3gm |
| `WEIGHTING` | posi, attr, weig |

Há ainda variantes de lesão e de punição (`INJURY` e `BAN`) cujo nome exato
não foi isolado nesta extração.

### Significado provável dos códigos

| Código | Significado |
|---|---|
| frnm / cmnm / scnm | primeiro nome / nome comum / sobrenome |
| team, ottm, buyt, tea2, hmtm, awtm | clube; outro clube; clube comprador; segundo clube; mandante; visitante |
| unid | ID único |
| stdy / stmn / styr | dia / mês / ano de início |
| cash, wage, cnln | valor; salário; duração do contrato |
| repu, atte | reputação; público médio |
| naty, natn, dob | nacionalidade; nação; data de nascimento |
| stad, nwst, capc | estádio; estádio novo; capacidade |
| comp, lang, gend, name | competição; idioma; gênero; nome |
| posi, attr, weig | posição; atributo; peso |

### Ainda não verificado

- Se `team` aceita ID numérico, além do nome, em todos os comandos.
- A unidade de `wage` e de `cnln`.
- O efeito de `PLAY_COMPETITION` (só recebe `unid`).
- O efeito de `WEIGHTING`. Pode indicar que o motor recalcula a habilidade a
  partir dos atributos com pesos por posição, o que explicaria o teste de CA
  no `people_db` (`UID+15` 160→111) não ter aparecido no jogo.

### O que não tem comando

CA, PA, atributos, data de nascimento, criação de jogadores adultos, número de
clubes por divisão, criação de divisão e data de início. Isso continua exigindo
edição dos `.dat` ou do executável.
