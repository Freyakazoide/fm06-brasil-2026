
## Campeões anteriores (COMP_HISTORY)

`server_db.dat`, lista DB+0x88 (leitor `0x00A0AE50`, registro `0x00AA6BC0`):
u32 quantidade (17089 no original, em 0x130BF3F) e registros de 39 bytes: tipo
(0), u32 índice da competição, u16 ano, u32 campeão, u32 vice, u32 3º (índices
da lista de times, FFFFFFFF = nenhum), três referências, u32 índice e u32 UID do
registro. Todo registro de lista termina com o próprio (índice, UID): o par que
`server_teams` lê antes do `0A 00` é o fim do registro anterior, e o índice do
time é esse primeiro u32 + 1 (Flamengo 290, Palmeiras 297, Corinthians 287,
Vasco 307, Atlético-MG 283, Lanús 80).

O campeão anterior de cada competição (competição+0x1C, lido pela Libertadores
como `[+0x1C]+0x24`) é o registro de ano mais alto (`0x00AFD370`).
`src/fm06patch/historico.py` grava os campeões reais de 2025 como ano 2005 do
motor sem mudar o tamanho do arquivo: Libertadores e Copa do Brasil já têm
2005; a Série A reaproveita o registro mais antigo (1971). A Sul-Americana não
é gravada: a de 2005 do motor é jogada entre o início do New Game (julho de
2005) e o primeiro dia do jogador, e com o Lanús gravado o histórico mostrava
dois campeões de 2025.

## UID do clube: banco x memória

Cada registro de clube termina com o próprio (índice, UID). O par que o
repositório lê antes de `00 BD 00 00 00` (`server_teams.club_names`) é o fim do
registro anterior: o "UID" do repositório é o do clube anterior na lista
(Cruzeiro: repositório 320, jogo 321; Corinthians: 317 e 319, porque 318 não é
clube). O jogo usa o UID verdadeiro (`CLUB+0x14`); `server_teams.clubs_by_uid`
faz o mapa. O pipeline do banco continua na convenção do repositório (as
buscas são consistentes entre si); só quem lê a memória precisa do mapa novo.
`server_teams.true_uids` converte repositório -> jogo; no último clube de um
bloco (Vitória: repositório 339, jogo 340) o registro seguinte é de outro tipo
e o par é o primeiro (índice anterior + 1, UID) depois dos nomes. O UID do jogo
é o dos gráficos (`club/<UID>/logo`, `team/<UID>/kits/home`, confirmado com
"Show Unique IDs": Flamengo 322) e o do `CLUB_NAME_CHANGE`.

Alguns registros trazem, depois do clube, outros clubes sem `00 BD 00 00 00`
(o da Ferroviária (SP), índice 4328, leva Americano Paulista 4329 e Paissandu
4330). O par do fim do registro é então o do último deles, e não o do clube:
`server_teams.club_pairs` pega sempre o primeiro (índice anterior + 1, UID)
depois dos nomes quando o par do fim não tem esse índice. Conferido com o
técnico de cada clube no `people_db` (contrato 4328, campo "time" 4541 =
Ferroviária). Até a correção, nove clubes de 2026 (Ferroviária, Independência,
Operário VG, PSTC/São Joseense, São Raimundo-RR, Parintins, Jequié, Capixaba,
Naviraiense) apontavam para o clube errado: nome, escudo, elenco e comissão iam
para o Paissandu e afins, que nem carregam no jogo.

## Histórico de carreira (pl_hist_*.dat)

Três arquivos em `data\db`, lidos no New Game (depois do `people_db.dat`):

| Arquivo | Conteúdo |
|---|---|
| `pl_hist_index.dat` | `02 01 "tad." 27 01 00`, u32 n (181.294), n × (u32 UID da pessoa, u32 bloco), em ordem de UID |
| `pl_hist_id.dat` | `02 01 "tad." 01 00 00`, por bloco: u32 primeiro, u32 último registro (posições no `pl_hist_dt` sem o cabeçalho) |
| `pl_hist_dt.dat` | `02 01 "tad." 01 00 00`, registros de 17 bytes: u16 ano do motor, u8 empréstimo, u8 jogos, u8 gols (255 = sem dado), u32 valor da transferência (FFFFFFFF = sem), u32 UID do clube no jogo (o verdadeiro: São Paulo 337), u32 posição do próximo (FFFFFFFF = último) |

Na 6.0.2 os blocos vêm em sequência no `pl_hist_dt` e os anos de um bloco crescem.
Um jogador pode ter vários blocos (UID 29: 17 blocos de uma temporada) ou um só com a
carreira inteira (Rogério Ceni: 15 registros de 1990 a 2004); o jogo junta todos.
Há 10.421 registros de 2005 (a temporada em que o jogo começa). No ano de um
empréstimo só aparece o clube do empréstimo (Saviola 2004: Monaco, sem Barcelona).
`src/fm06patch/historico_jogadores.py` lê e regrava os três (sem mudança, byte a byte
igual); tirar um jogador renumera os blocos.
