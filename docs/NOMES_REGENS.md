# Nomes dos regens

`data/modelos/nomes_regens.xlsx` (aba Nomes: nação, tipo, nome, peso) entra no
`server_db.dat` pelo `aplicar_brasil_2026.py --apply` (`src/fm06patch/nomes_regens.py`).
Para não pôr: `--sem-nomes-regens`.

## As tabelas de nomes do banco

Três tabelas seguidas no server_db 6.0.2: primeiro nome (0x005F7416, 69.253 nomes),
sobrenome (0x0085C9F9, 159.272) e nome comum (0x00DE5A49, 25.334). Cada uma é u32
quantidade e, para cada nome:

    u8 0, u32 n, nome (UTF-16LE, n caracteres), 00 00, u16 uso, u32 nação, u32 índice, u32 UID

- **índice** é a posição na tabela; a pessoa (people_db) cita o nome pelo índice, então
  nada pode entrar no meio (os índices de depois mudariam).
- **uso** é quantas pessoas do banco têm o nome (confere em 96% dos nomes: "Marcelo" 273,
  "da Silva" 462).
- A ordem é por nação (o código do people_db: 0xBD Brasil) e, dentro dela, pelo uso.

## O que o script faz

- Nome que a nação já tem ("Gabriel", "Pedro"): o uso sobe para o peso novo, se for maior.
- Nome novo ("Enzo", "Kauã", "Endrick"): entra no fim da tabela, com índice = posição, a
  nação certa e UID a partir de 110.000.000.
- O peso da planilha é escalado para os nomes da planilha somarem 70% do uso da nação
  (`NEW_SHARE`): se o jogo sorteia pelo uso, 7 em cada 10 regens saem com nome de hoje.
- O resto do banco não muda (só anda para frente: o tamanho do arquivo cresce, como no
  histórico de campeões).

Resultado no banco original: 614 nomes novos (Brasil 365 primeiros nomes, 178
sobrenomes e 71 apelidos, mais Argentina, Uruguai, Colômbia e Paraguai) e 971 que já
existiam com peso maior.

A aba Regras_apelido (Gabriel → Gabrielzinho...) não entra: o jogo não monta apelido,
só sorteia da tabela de nomes comuns.

## A conferir no jogo

Não se sabe ainda como o FM06 sorteia: pelo uso, por igual entre os nomes da nação, ou
pela posição na tabela (os nomes novos estão fora do bloco da nação). Os regens da base
(a cada temporada, e os jovens que o jogo cria quando um clube fica sem jogadores)
mostram: se aparecerem Enzo, Kauã, Davi, funcionou. Se o New Game travar,
rode o `aplicar_brasil_2026.py --apply --sem-nomes-regens` e mande o dump.

## Quem sobra nos clubes de 2026

Os mesmos nomes servem para quem fica num clube de 2026 sem nome de 2026:

- jogadores de 2005 além do elenco da planilha (`montar_elencos.py`: o que não virou
  hospedeiro ganha um `CHANGE_PLAYER_NAME` no mesmo .lnc; lista em
  `workspace/mods/brasil_2026_jogadores_renomeados.csv`);
- comissão de 2005 que sobra (`aplicar_comissao.py`, no `brasil_2026_comissao.lnc`).

O nome é sorteado pelos pesos da planilha (prenome + sobrenome; 20% ganham também um
apelido), sempre o mesmo para o mesmo UID (`nomes_regens.Filler`). Idade e atributos
continuam os do jogador de 2005 (com o ano do motor, a idade bate com a de hoje).
