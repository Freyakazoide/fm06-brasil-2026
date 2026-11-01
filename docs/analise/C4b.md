# Ficha C4b — Histórico de prêmios (vencedores)

- Quem analisou / data: Claude, 2026-11-01
- Ferramenta: Capstone + pefile (`workspace/rea/tools/pe.py`), `fm.exe` 6.0.2 original,
  `server_db.original.dat` e `lang_db.original.dat`
- Pergunta: onde ficam os vencedores dos prêmios? Dá para gravar a Bola de Ouro de 2006 a
  2025 da `premios_historico.xlsx`?

## Conferido no código

- O RTTI tem `DATABASE_TABLE<PERSON_AWARD_HISTORY>` ao lado de `DATABASE_TABLE<AWARD>` (o
  catálogo da ficha C4). Classe: vtable `0x010E1C74`, construtor `0x009ED280`, chamado só
  por `0x00A0B7A0`, o leitor da lista DB+0x90. Ele é chamado em `0x00A125E8` pelo
  carregador `0x00A12120`, logo antes do histórico de campeões (DB+0x88, `0x00A0AE50`).
- Leitor do registro (`0x00A96C40`):
  - u32 prêmio (+0x1C) e u16 ano (+0x20);
  - u32 pessoa em +0x24, +0x38 e +0x4C (1º, 2º e 3º);
  - u8 em +0x28, +0x3C e +0x50;
  - a partir da versão 0xCF, três textos em +0x2C, +0x40 e +0x54 (o construtor faz os três
    com `0x00C50A00`, o mesmo dos textos);
  - o fim comum.
- Método 11 (`0x00A967E0`): o prêmio é resolvido por `0x009E8130` e as três pessoas por
  `0x009E3720`, o mesmo resolvedor de pessoa da `STARTING_INJURY` (ficha C3b).

## Conferido no banco original

- A lista: u32 5.362 em `0x1296FF5`, termina em `0x130BF3F`, onde começa a de campeões.
  Os registros têm tamanho variável por causa dos textos. Um texto é u32 n e n caracteres
  UTF-16 mais `00 00`; com n = 0, é só o u32.
- Há 428 prêmios. O índice do prêmio é a posição na lista de nomes do `lang_db` (a partir de
  `0x23C7AF`):
  - 0 = "World Footballer of the Year": Ronaldinho, Henry, Shevchenko em 2004;
  - 129 = "Brazilian 1st Division Player of the Year": Robinho 2004, Alex 2003, Kaká 2002,
    Alex Mineiro 2001, Romário 2000, Marcelinho Carioca 1999. É a Bola de Ouro da Placar;
  - 131 = "Brazilian 1st Division Top Goalscorer": os u8 são os gols (Washington 34 em
    2004, Dimba 31 em 2003);
  - 631 = "Brazilian Internet Voting Player of the Year" (2000–2004).

  São os únicos do Brasil com histórico. O 130 ("Team of the Year") e o 132 ("Young
  Player") não têm nenhum registro.
- A pessoa é o índice no `people_db` (o Kaká é 26326 no prêmio 63, o mesmo índice da
  relação do São Paulo). Vencedor fora do banco fica com FFFFFFFF e só o texto (Petr Cech,
  Ligue 1).

## Consequência

`src/fm06patch/premios.py` e `scripts/aplicar_premios.py`, na etapa 3 do `aplicar_tudo`,
fazem três coisas:

- **Anos**: os anos dos prêmios 129, 131 e 631 passam a −20 (74 registros), como no
  histórico de campeões. O jogo mostra +20; antes, o Robinho de 2004 aparecia como 2024.
- **Bola de Ouro de 2006 a 2025** no 129, como ano − 20 (1986 a 2005 do motor), no fim da
  lista com UID a partir de 101.000.000.
  - O vencedor com `jogador_2026`/`clube_2026` preenchidos na planilha fica ligado à pessoa.
    São 8: Rogério Ceni (técnico do Bahia), Neymar, Everton Ribeiro, Dudu, Gabigol, Hulk,
    Gustavo Scarpa e Arrascaeta, conferidos pela data de nascimento da `jogadores_2026.xlsx`.
  - Os outros entram só com o nome.
  - A ligação é explícita porque o nome sozinho pegava homônimos (um "Gabriel Jesus" do
    Barra, um "Estêvão" do CRB).
- **Ligações com hospedeiros**: em qualquer prêmio, a pessoa que é hospedeiro (virou outra
  de 2026) perde a ligação e fica só o nome. Foram 91 no banco instalado.

Rodar de novo não grava duas vezes.

Ficam de fora:
- o Craque do Brasileirão e a Bola de Prata, porque o jogo não tem prêmio com histórico
  equivalente;
- 2005 (Tevez), que não está na planilha;
- os artilheiros de 2005 a 2025, que também não estão na planilha. O 131 aceita os gols.

## Diário

- 01/11, escrito e instalado (`aplicar_tudo --rapido`). No `server_db` do jogo: 5.382
  registros; o 129 tem Robinho em 1984 (2004 na tela), Lucas Leiva em 1986 (2006) e
  Arrascaeta em 2005 (2025, pessoa 28628). Testes:
  - a lista original e a regravação idêntica;
  - os anos −20 e a inserção que não mexe no resto do arquivo;
  - rodar duas vezes não grava duas vezes;
  - a ligação com um hospedeiro sai.

  Falta ver no jogo.
- 01/11, **conferido no jogo** pelo usuário: o histórico do Jogador do Ano mostra 2025
  Arrascaeta, 2024 Estêvão, 2023 Luis Suárez ... 2006 Lucas Leiva. O clube aparece "-" (o
  registro não tem clube). A ficha dos jogadores ligados não mostra o prêmio: hipótese, não
  conferida no código, de que a ficha só lista prêmios ganhos durante o jogo.
