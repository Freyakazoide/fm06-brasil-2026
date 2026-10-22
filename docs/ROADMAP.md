# Roadmap (22/10/2026)

Onde o mod está e o que falta, na ordem em que eu atacaria. O que você pode fazer por
fora está em [FRENTES_RODADA_2.md](FRENTES_RODADA_2.md); o que falta conferir no jogo, em
[TESTES_PENDENTES.md](TESTES_PENDENTES.md). Tudo roda com `python scripts\aplicar_tudo.py`.

Legenda: ✅ feito e conferido no jogo · 🧪 feito, falta conferir no jogo · 🟡 mapeado,
falta implementar · ⏳ precisa de captura ou dado · ❌ não mapeado.

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
| Instalações, base e orçamentos de 2026 | ⏳ | captura D2 + dados E1 |
| Clubes de 2026 que não existem no FM06 (38 nas séries, 88 nos estaduais) | ⚠️ | ocupam um clube de 2005 ("substitutos"); criar clube novo exige o formato completo do registro |

### Pessoas

| Item | Situação | Onde |
|---|---|---|
| Elencos de 2026 (6.244 jogadores) | ✅ | `montar_elencos.py` + injetor |
| Atributos, CA/PA, posições, pé, altura, peso | ✅ | injetor |
| Personalidade, ocultos e jogadas preferidas (220 titulares) | ✅ | `jogadores_perfil.xlsx` |
| Nacionalidade pelo código da nação | ✅ | injetor (sem doadores desde 22/10) |
| Contrato (salário, início, fim) e número da camisa | ✅ | injetor |
| Jogos e gols pela seleção | ✅ | injetor |
| Histórico de carreira (100 jogadores) | ✅ | `aplicar_historico.py` |
| Jogadores de 2005 que sobravam | ✅ | nome de hoje ou saída para clubes fora de 2026 |
| Técnico da Seleção (Ancelotti) | ✅ | `selecoes_2026.csv` |
| Árbitros de 2026 (18 do quadro FIFA) | 🧪 | `aplicar_arbitros.py` |
| Nomes dos regens | 🧪 | `nomes_regens.xlsx` |
| Joias da base (regens de verdade) | 🧪 | `regens_futuros_2026.xlsx` (`FUTURE_REGEN`), falta preencher |
| Lesões e suspensões no começo | ⏳ | captura D3 |
| Rigor dos árbitros | ⏳ | captura D4 |
| Segunda nacionalidade, cláusula de rescisão | ❌ | campos não localizados |
| Jogador novo sem hospedeiro | ❌ | exige o formato completo do `people_db` |

## Próximas fases

### Fase 1: fechar o que está em teste (agora)

- Árbitros, rivais, nomes dos regens e elencos sem os doadores (TESTES_PENDENTES).
- Joias da base: você preenche 3 a 5 (E2), roda o `aplicar_tudo.py` e espera a chegada
  dos juniores (D5).

### Fase 2: base e regens

- Campo de base e de instalações do clube (D2) e os valores de 2026 (E1).
- Força da base de cada país: achar no banco o "Development"/"League Standard" da nação
  (já conhecidos na memória).
- Joias da base em quantidade (E2 completa).

### Fase 3: dinheiro dos clubes

- Orçamento de contratações e de salários de 2026 (D2 + E1).
- Premiação e cotas de TV de 2026 (Brasileirão, Copa do Brasil): achar onde o `fm.exe`
  guarda os valores de cada competição.

### Fase 4: o resto do continente

- Elencos de 2026 dos clubes estrangeiros da Libertadores e da Sul-Americana (E6): coletor
  do Sofascore para eles e o mesmo caminho dos brasileiros.
- Técnicos das seleções (E3) e, depois, dos clubes estrangeiros.

### Fase 5: começo de jogo mais real

- Lesões e suspensões do começo de 2026 (D3, com a planilha que já existe).
- Rigor dos árbitros (D4).
- Clubes que "gostam" de pessoas (lista de relações do clube, tipo 3): limpar as que
  apontam para pessoas de 2005 que viraram outra pessoa de 2026.

### Fase 6: clubes de verdade no lugar dos substitutos

- Entender o registro completo do clube no `server_db` (já sabemos nomes, cores,
  estádio, saldo, rivais, times) para criar clubes novos em vez de ocupar um de 2005.
  É o maior trabalho que falta; os substitutos funcionam, então fica por último.

### Fase 7: acabamento

- Logos das competições (F1) e fotos (F2), se o jogo ler.
- Mídia (jornais) e prêmios (Bola de Prata e afins) de 2026: campos ainda não procurados.
- Mais histórico (E4) e mais perfis (E5) a cada rodada de dados.

## Jogo futuro

As especificações C1–C14 estão em [jogo_futuro](jogo_futuro/README.md). O mod continua
sendo a base de dados inicial (clubes, elencos, estádios, finanças, histórico e regras).
