
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
