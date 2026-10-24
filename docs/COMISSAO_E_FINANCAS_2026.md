# Técnicos, comissões e finanças de 2026

## Técnicos e comissão técnica

Dados: `python scripts/coletar_comissao.py` grava
`data/brasil/comissao/comissao_2026.csv` (clube, cargo, função, nome,
nacionalidade, nascimento, fonte):

- técnico: o atual do Sofascore (nome, nacionalidade, nascimento);
- comissão (auxiliares, preparadores físicos e de goleiros, analistas, médicos,
  fisioterapeutas, olheiros): a tabela de comissão do artigo do clube na
  Wikipédia em inglês. Nem todo clube tem, e algumas estão desatualizadas (coluna
  `atualizado`). Dá para editar o CSV à mão. Em 20/10/2026 a lista foi completada
  com a página de equipe técnica do Transfermarkt de cada clube
  (`comissao_2026_cobertura.csv` conta, clube a clube, quantos de cada cargo há).

Seleções: `data/brasil/comissao/selecoes_2026.csv` (nação, nome, nacionalidade,
nascimento, fonte). A linha com nome troca o técnico da seleção no banco: o contrato
com a seleção é o mesmo bloco do clube com 01 no lugar do 00 e o código da nação no
lugar do clube (`comissao.read_national_managers`; Parreira no Brasil, Pekerman na
Argentina, Fossati no Uruguai...). Em 22/10/2026 só o Brasil está preenchido (Carlo
Ancelotti, confirmado nas convocações de outubro); as outras seleções sul-americanas
trocaram de técnico depois da Copa e ficam em branco até alguém conferir.

No jogo: `python scripts\aplicar_comissao.py --apply` (depois do
`reforcar_elencos.py --apply`, porque grava sobre o people_db dele).

- Cada pessoa de 2026 ocupa alguém do FM06 com o mesmo cargo no clube (cargo no
  registro da pessoa: 16 técnico, 20 auxiliar, 2 treinador, 12
  fisioterapeuta/médico, 14 olheiro; `src/fm06patch/comissao.py`).
- O nome entra pelo `data\db\lnc\all\brasil_2026_comissao.lnc`
  (`CHANGE_PLAYER_NAME`, o mesmo comando dos jogadores; o jogo usa o mesmo caminho
  para staff) no New Game.
- A nacionalidade e, do técnico, o nascimento (20 anos antes, como os jogadores)
  vão direto no people_db.
- Clube sem gente bastante naquele cargo recebe alguém do mesmo cargo de um clube
  brasileiro fora de 2026 (muda o clube do contrato e o time no registro); quando
  eles acabam (os auxiliares acabam cedo), um de cada clube estrangeiro que tem mais
  de um no cargo. Até 1 técnico, 3 auxiliares, 5 treinadores, 5 médicos e 2
  olheiros de fora por clube (`DONOR_LIMIT`). Desde 24/10 quem vem de fora entra
  também na comissão do time no `server_db.dat` (`elenco_times.py`): auxiliares e
  treinadores numa lista, fisioterapeutas e médicos em outra, o técnico em TEAM+0x70
  (antes só o contrato e o campo "time" mudavam, e eles não apareciam no clube novo).
- Sem nacionalidade na planilha, a pessoa fica brasileira.
- Quem sobra continua com o nome de 2005. Clubes só de estadual não mudam.
- Lista: `workspace\mods\comissao_2026_hospedeiros.csv`.

## Finanças

`python scripts/montar_financas.py` grava `data/brasil/clubes/financas_2026.csv`
(pode editar à mão):

- `saldo_rs`: estimativa pelo tamanho da torcida (seguidores no Sofascore) em
  relação à mediana da série: base × (torcida / mediana)^0,6, com piso e teto.
  Base: A R$ 45 mi, B R$ 8 mi, C R$ 2,5 mi, D R$ 600 mil;
- `publico_medio`: estimativa, porque não achei público por clube em fonte
  acessível daqui: média da série × (torcida / mediana)^0,5, entre 0,35 e 2,2 vezes
  a média (A 26.222, a média real de 2025; B 9.000, C 4.500, D 1.800 estimadas).
  Flamengo 55.400, Chapecoense 12.200. Corrija no CSV se tiver o número real.

O `aplicar_brasil_2026.py --apply` grava no `server_db.dat`
(`src/fm06patch/financas.py`):

- o saldo, no bloco de finanças do registro do clube, em libras (o jogo guarda
  dinheiro em libras e mostra em reais a 5,08 por libra);
- o público médio, mínimo (metade) e máximo (o dobro, sem baixar o do banco).

O `BOOST_TEAM` do .lnc não serve: só grava o caixa em clubes com finanças
"completas", e os brasileiros do banco têm as "básicas".

Referência do banco (2005): Corinthians £6 mi, Santos e Palmeiras £4 mi, São
Paulo £3 mi, Flamengo £300 mil, clubes pequenos £1.

## Conferir no jogo

- Ficha do clube → Finanças: saldo (Flamengo ≈ R$ 110 mi, clube da Série D entre
  R$ 150 mil e R$ 2,5 mi).
- Ficha do clube → Comissão técnica: técnico de 2026 (Flamengo Leonardo Jardim,
  Palmeiras Abel Ferreira) com a nacionalidade certa; auxiliares e preparadores.
- Ficha do técnico: idade (Abel Ferreira, nascido em 22/12/1978).
