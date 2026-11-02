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

Cada nação é um bloco seguido na tabela, e o jogo sorteia dentro do bloco. Até 01/11 os
nomes novos entravam no fim da tabela, e os regens que o jogo cria (reservas, juniores)
saíam com o nome de índice 0 (primeiro nome "Mohamed", sobrenome "Alamosi") e com nomes do
Chile, a nação seguinte ao Brasil (Zúñiga, Vidal, Riquelme). **Hipótese** que bate com o que
se viu: o jogo guarda, para cada nação, onde o bloco começa e quantos nomes tem. Com 40
nomes brasileiros no fim, o intervalo do Brasil entra no bloco do Chile e, quando o sorteio
passa da soma, cai no índice 0. Agora:

- **Nome novo** ("Enzo", "Kauã") ocupa, dentro do bloco da nação, o lugar de um nome que
  nenhuma pessoa do people_db cita (`nomes_regens.cited`: 270.696 pessoas lidas). Os
  compostos vão primeiro, depois os de menor uso. Índice e UID ficam, e nada entra no fim.
  Sem vaga, o nome não entra; os de menor peso ficam de fora primeiro.
- **Nome que a nação já tem** ("Gabriel", "Pedro"): o uso vai para o peso novo.
- **A soma do "uso" da nação fica a do original.** Os nomes da planilha somam 70% dela
  (`NEW_SHARE`), os compostos ficam com 0 ("Pedro Antônio" não sai) e os outros dividem o
  resto na proporção de hoje. Os de uso pequeno podem ir a 0: continuam no banco para quem
  tem o nome, mas não são sorteados.

Resultado no banco original:
- **Brasil:** os 40 primeiros nomes e os 19 sobrenomes novos entram; dos 111 apelidos novos,
  entram 66.
- **Argentina, Colômbia, Paraguai e Uruguai:** entram só os nomes que cabem.
- No total: 152 nomes novos, 982 que já existiam e 228 sem vaga. Nenhum nome citado por
  alguém muda.

A aba Regras_apelido (Gabriel → Gabrielzinho...) não entra no banco: o jogo não monta
apelido, só sorteia da tabela de nomes comuns. Os fictícios (`gerar_ficticios.py`) usam a
planilha direto, com todos os nomes e as regras.

## A conferir no jogo

Os reservas e juniores que o jogo cria (Marília Res., Portuguesa Res.) devem sair com
nomes brasileiros, sem "Alamosi" nem "Mohamed". Se ainda aparecerem, a hipótese do bloco
está errada.

## Quem sobra nos clubes de 2026

Os mesmos nomes servem para quem fica num clube de 2026 sem nome de 2026:

- jogadores de 2005 além do elenco da planilha (`montar_elencos.py`: o que não virou
  hospedeiro ganha um `CHANGE_PLAYER_NAME` no mesmo .lnc; lista em
  `workspace/mods/brasil_2026_jogadores_renomeados.csv`);
- comissão de 2005 que sobra (`aplicar_comissao.py`, no `brasil_2026_comissao.lnc`).

O nome é sorteado pelos pesos da planilha (prenome + sobrenome; 20% ganham também um
apelido), sempre o mesmo para o mesmo UID (`nomes_regens.Filler`). Idade e atributos
continuam os do jogador de 2005 (com o ano do motor, a idade bate com a de hoje).
