# Roadmap (23/10/2026)

Onde o mod está e o que falta, na ordem em que eu atacaria. O que você pode fazer por
fora está em [FRENTES_RODADA_2.md](FRENTES_RODADA_2.md) (planilhas e fichas de código); o que falta conferir no jogo, em
[TESTES_PENDENTES.md](TESTES_PENDENTES.md). Tudo roda com `python scripts\aplicar_tudo.py`.

Legenda: ✅ feito e conferido no jogo · 🧪 feito, falta conferir no jogo · 🟡 mapeado,
falta implementar · ⏳ precisa de ficha de código ou de dado · ❌ não mapeado.

## Onde estamos

### Estrutura e competições

| Item | Situação | Onde |
|---|---|---|
| Séries A, B, C (nova) e D com os clubes de 2026 | ✅ | `aplicar_brasil_2026.py`, patches do `fm.exe` |
| Acesso, rebaixamento, playoffs da B, fases da C, 6 acessos da D | ✅ | patches `serie_*` |
| Calendário 2026 (virada em 1º/1, pausa da Copa) | ✅ | `docs/CALENDARIO_2026.md` |
| Estaduais 2026 (268 clubes) | ✅ | `estaduais_clubes.py` |
| Copa do Brasil 2026 | ✅ | patch `copa_do_brasil_2026` |
| Libertadores e Sul-Americana 2026 (vagas e datas) | ✅ | patches `libertadores_*`, `sul_americana_2026` |
| Ano exibido 2026 (motor em 2006) | ✅ | patch `ano_exibido_mais_20` |
| Classificação de 2025 e histórico de campeões | ✅ | `campeoes.py`, `docs/HISTORICO.md` |
| Telas e textos em pt-BR | ✅ | `traducao.py`, `traduzir_telas.py` |

### Clubes

| Item | Situação | Onde |
|---|---|---|
| Nome, escudo, uniforme e cores | ✅ | `.lnc`, `gerar_graficos.py`, `cores.py` |
| Estádio, capacidade e cidade | ✅ | `estadios.py` |
| Saldo, público e reputação de 2026 | ✅ | `financas.py`, `reputacao.py` |
| Técnico e comissão de 2026 (499 pessoas) | ✅ | `aplicar_comissao.py` |
| Rivais e clássicos | 🧪 | `rivais.py` (a tela de informações não mostra; falta a notícia de clássico) |
| CT, base e captação de 2026 (40 clubes) | 🧪 | `instalacoes.py` + aba Estrutura |
| Orçamento de transferências de 2026 (40 clubes) | ✅ | `orcamentos.py` + aba Estrutura (ficha C5b); o salarial segue a fórmula do jogo |
| Clubes de 2026 que não existem no FM06 (38 nas séries, 88 nos estaduais) | ⚠️ | ocupam um clube de 2005 ("substitutos"); criar clube novo exige o formato completo do registro |

### Pessoas

| Item | Situação | Onde |
|---|---|---|
| Elencos de 2026 (6.244 jogadores) | ✅ | `montar_elencos.py` + `gravar_atributos.py` |
| Atributos, CA/PA, posições, pé, altura, peso | ✅ | `gravar_atributos.py` (direto no people_db) |
| Personalidade, ocultos e jogadas preferidas (220 titulares) | ✅ | `jogadores_perfil.xlsx` |
| Nacionalidade e nascimento | ✅ | `gravar_atributos.py` + patch `nascimento_lnc_fixo` |
| Contrato (salário, início, fim) e número da camisa | ✅ | `gravar_atributos.py` |
| Jogos e gols pela seleção | ✅ | `gravar_atributos.py` |
| Histórico de carreira (100 jogadores) | ✅ | `aplicar_historico.py` |
| Clubes e valores da carreira dos outros jogadores (~2.800, transferências do Sofascore) | 🧪 | `carreiras_2026.csv` + `aplicar_historico.py` |
| Jogadores de 2005 que sobravam | ✅ | nome de hoje ou saída para clubes fora de 2026 |
| Técnico da Seleção (Ancelotti) | ✅ | `selecoes_2026.csv` |
| Técnicos das outras 8 seleções da CONMEBOL | 🧪 | `selecoes_2026.csv` |
| Pessoa de 2005 que é alguém de 2026 (Ancelotti do Milan, Forlán jogador) | 🧪 | ganha nome de hoje (`aplicar_comissao.py`) |
| Árbitros de 2026 (18 do quadro FIFA) | 🧪 | `aplicar_arbitros.py` |
| Nomes dos regens | 🧪 | `nomes_regens.xlsx` |
| Joias da base (regens de verdade) | ✅ | 32 garotos na `regens_futuros_2026.xlsx` (`FUTURE_REGEN`): sub-17 de 2025/2026 e sub-15 do Palmeiras |
| Lesões no começo | 🧪 | `aplicar_lesoes.py` (STARTING_INJURY, ficha C3b); suspensões: a aba da planilha está vazia |
| Rigor dos árbitros | ➖ | fora do mod (decisão do usuário, 01/11): só os nomes de 2026 |
| Segunda nacionalidade, cláusula de rescisão | ❌ | campos não localizados |
| Jogador novo sem hospedeiro | ❌ | exige o formato completo do `people_db` |

## Próximas fases

### Fase 1: fechar o que está em teste (agora)

- Árbitros, rivais, nomes dos regens, elencos sem os doadores e a carreira pelas
  transferências (TESTES_PENDENTES).
- Joias da base (25 garotos), CT e base, técnicos das seleções e as pessoas repetidas:
  um `aplicar_tudo.py --rapido` e os itens 7 e 9 a 11 do TESTES_PENDENTES.

### Fase 2: base e regens

- ~~Campo de base e de instalações do clube (ficha C6)~~: entrou em 23/10.
- ~~Força da base de cada país~~: não há o campo (01/11, C10): "Development" é o nível
  econômico do país (1/2/3); a base sai da reputação da nação (Brasil 9550, a maior) e das
  notas de base dos clubes, que o mod já grava.
- Como a chegada da base funciona (ficha C7) e as joias em quantidade.

### Fase 3: dinheiro dos clubes

- ~~Orçamento de contratações de 2026 (ficha C5b)~~: entrou em 27/10 (tabela do
  FINANCE_MANAGER no server_db). Orçamento salarial: patch `orcamento_salarial_folha`
  (01/11, nunca abaixo da folha + 10%).
  Os empréstimos de 2005 foram zerados em 01/11.
- Patrocínio de 2026 (ficha C1b + `patrocinadores_2026.xlsx`, já preenchida).
- Premiação e cotas de TV de 2026 (ficha C9b + `premiacao_2026.xlsx`, já preenchida).

### Fase 4: o resto do continente

- ~~Elencos e técnicos de 2026 da primeira divisão dos outros 9 países da CONMEBOL~~:
  entrou em 24/10 (`coletar_estrangeiros.py`, `docs/JOGADORES_2026.md`, item 13 do
  TESTES_PENDENTES). Falta: a comissão além do técnico e os clubes de 2026 que não
  existem no FM06 (ficam de fora).
- ~~Técnicos das seleções (`selecoes_2026.csv`)~~: entrou em 22/10.
- ~~Regras de transferência de 2026 (ficha C8b)~~: entrou em 01/11 (janelas 5/1–3/3 e
  20/7–11/9, 9 estrangeiros por jogo e sem limite no elenco, 5 trocas e 12 reservas em todas
  as competições).

### ~~Atributos direto no people_db~~ (feito em 25/10)

- Engenharia reversa do leitor de jogadores no `fm.exe` (`docs/reversing/rea-atributos.md`):
  `gravar_atributos.py` grava tudo o que o injetor gravava e a etapa 4 saiu do
  `aplicar_tudo.py`. Ficam de fora 3 jogadores com registro ambíguo (Edson Duarte, Santiago
  Solari, Newton) e ~31 contratos ambíguos; Desportivismo e Temperamento recebem o sorteio do
  jogo no New Game.

### Fase 5: começo de jogo mais real

- ~~Lesões do começo de 2026 (ficha C3b)~~: entrou em 01/11 (tabela STARTING_INJURY do
  server_db, `aplicar_lesoes.py`); suspensões (STARTING_BAN) esperam dados na planilha.
- ~~Rigor dos árbitros~~: fora (01/11, decisão do usuário); os árbitros ficam só com o nome
  de 2026. Candidato anotado: o único getter de atributo do OFFICIAL é `0x00A6E010`
  (`[ecx-0x23]`, 4º dos 10 bytes), slot 127 da vtable `0x010F8FBC`.
- ~~Clubes que "gostam" de pessoas~~: entrou em 01/11 (`aplicar_relacoes.py`, etapa 3): 143
  relações tipo 3 de 54 clubes que apontavam para hospedeiros saíram.

### Fase 6: clubes de verdade no lugar dos substitutos

- Entender o registro completo do clube no `server_db` (já sabemos nomes, cores,
  estádio, saldo, rivais, times) para criar clubes novos em vez de ocupar um de 2005.
  É o maior trabalho que falta; os substitutos funcionam, então fica por último.

### Fase 7: acabamento

- ~~Prêmios históricos~~ ✅ (ficha C4b, conferido em 01/11): Bola de Ouro de 2006 a 2025 no histórico do jogo
  (`aplicar_premios.py`); Craque do Brasileirão e Bola de Prata não têm prêmio equivalente no
  jogo; faltam os artilheiros de 2005 a 2025 (não estão na planilha).
- Mídia de 2026 (ficha C11, 01/11): o FM06 só tinha mídia inglesa, polonesa e o O JOGO;
  entraram 23 fontes brasileiras (`aplicar_midia.py`), falta ver se as notícias citam.
- Logos das competições: campos ainda não procurados.
- Mais histórico e mais perfis a cada rodada de dados: jogos e gols por passagem para
  quem só tem os clubes (a `historico_carreira.xlsx` tem prioridade sobre as
  transferências).

## Jogo futuro

As especificações C1–C14 estão em [jogo_futuro](jogo_futuro/README.md). O mod continua
sendo a base de dados inicial (clubes, elencos, estádios, finanças, histórico e regras).
