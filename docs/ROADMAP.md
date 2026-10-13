# Roadmap: caixa de ferramentas

Primeiro conseguir alterar **tudo**. Só depois aplicar os dados de 2026.

Por onde cada alteração é feita:

| Caminho | Quando é aplicado | Exemplos |
|---|---|---|
| **Texto** (`.lnc` / `.edt` / `.ddt`) | jogo aplica no New Game | nomes, trocas de divisão, transferências |
| **Injetor** (memória) | logo após o New Game; depois salvar | ficha do jogador, contratos |
| **Banco** (`.dat`) | jogo lê no New Game | histórico, competições, jogadores novos |
| **Executável** (`fm.exe`) | sempre | ano de início, se estiver fixo no código |

## Jogador

| Item | Situação | Caminho | Observação |
|---|---|---|---|
| Nome | ✅ | texto | `CHANGE_PLAYER_NAME` |
| Data de nascimento / idade | ✅ | injetor | `year_shift` −21 |
| Altura, peso | ✅ | injetor | |
| CA, PA | ✅ | injetor | |
| Atributos visíveis | ✅ | injetor | validado com a ficha do jogo |
| Atributos ocultos (consistência, propensão a lesão…) | ✅ | injetor | ainda não estão na planilha |
| Posições, pé preferido | ✅ | injetor | |
| Personalidade | ✅ | injetor | |
| Preferred Moves | ✅ | injetor | |
| Reputação | ✅ | injetor | |
| Nacionalidade | ⚠️ | injetor | só copiando de um doador; falta escolher a nação pelo UID (Colômbia, Equador…) |
| Segunda nacionalidade | ❌ | ? | campo não localizado |
| Jogos e gols pela seleção | 🟡 | injetor | offsets conhecidos, falta expor |
| Contrato: salário, início, fim, situação, prêmios | 🟡 | injetor | layout conhecido, falta implementar |
| Número da camisa | 🟡 | injetor | offset conhecido, codificação pendente |
| Cláusula de rescisão | ❌ | injetor | não localizada |
| Retirar do elenco os jogadores de 2005 que sobraram | 🟡 | injetor | encerrar o contrato no 1º dia |
| Histórico de carreira | 🟡 | banco | `pl_hist_*.dat` já tem leitor no repo; falta o escritor |
| Lesões e suspensões iniciais | 🟡 | texto | comandos `INJURY` / `BAN` existem; sintaxe a confirmar |
| Criar jogador novo (sem hospedeiro) | ❌ | banco | exige formato completo do `people_db` |

## Clube

| Item | Situação | Caminho | Observação |
|---|---|---|---|
| Nome, nome curto e longo | ✅ | texto | `CLUB_NAME_CHANGE` etc. |
| Divisão em que joga | ✅ | texto / banco | `SWAP_TEAMS` (troca 1 por 1); no banco, `scripts/server_db_teams.py --set` (a testar no jogo) |
| Cores do uniforme | 🟡 | texto | `COLOUR_CHANGE` |
| Estádio e capacidade | 🟡 | texto | `STADIUM_MOVE`, `STADIUM_CAPACITY_CHANGE`, `GROUND_SHARE` |
| Dinheiro, reputação, público | 🟡 | texto / injetor | `BOOST_TEAM`; Cash no injetor |
| Orçamentos, instalações, base | ❌ | injetor | campos do clube não localizados |

## Competições

| Item | Situação | Caminho | Observação |
|---|---|---|---|
| Nome da competição | ✅ | texto | `COMP_NAME_CHANGE` no `brasil_2026.lnc` |
| Quais clubes estão em cada série | ✅ | texto | `SWAP_TEAMS`, limitado à estrutura existente |
| Número de clubes por divisão | 🟡 | executável | regras ficam no `fm.exe` (módulo Brasil em `0xBB2700`); ver `docs/reversing/competitions.md` |
| Formato (pontos corridos, turno e returno) | 🟡 | executável | idem |
| Acessos e rebaixamentos | ✅ | executável | `scripts/patch_exe.py` (campos `+0x11`/`+0x14` da fase); validado: Série A rebaixa 4, Série B sobe 4 |
| Criar a Série D | ✅ | executável + banco | `scripts/aplicar_brasil_2026.py`: Séries A–D com nomes, datas e clubes de 2026. Falta: playoffs da B, fases da C, 6 acessos da D |
| Vagas em Libertadores e Sul-Americana | ❌ | banco | idem |
| Classificação da temporada passada | 🟡 | banco | `scripts/server_db_teams.py --pos` / `--last` |
| Histórico de campeões (Séries A–D, pelo menos os últimos) | ❌ | banco | não localizado |
| Calendário | ✅ | executável | datas de A, B, C e D por patch; ver `docs/REGRAS_2026.md` |

## Jogo

| Item | Situação | Caminho | Observação |
|---|---|---|---|
| Ano de início 2026 | ❌ | banco / executável | hoje o jogo começa em 2005/06; as idades ficam certas com o `year_shift` do injetor. Investigar de onde vem a data inicial |

## Ordem sugerida

Meta do **primeiro teste de viabilidade**: um New Game com competições, clubes e
jogadores de 2026, jogado por uma temporada inteira, com a virada para a
seguinte funcionando.

1. ~~**Fechar as classificações.**~~ ✅ Acesso e rebaixamento entre as quatro
   séries validados na virada 2006 → 2007 (Série C com 24).
1b. **Calendário completo:** estaduais (e a vaga deles na Série D), Séries A–D,
   Copa do Brasil, Libertadores e Sul-Americana sem conflito; virada da
   temporada em 01/01; 10ª rodada dos grupos da D depois do mata-mata.
2. **Investigar o ano de início 2026.** Antes de criar jogadores em massa.
   Os dados dos jogadores ficam com as datas reais de 2026; o injetor aplica
   `year_shift` = ano do motor − 2026 (hoje −21, com 2026 de verdade vira 0).
   Se não der, o jogo continua em 2005/06 com idades certas e só o ano
   exibido fica errado.
3. **Regras restantes:** grupos da Série C por posição e final; Copa do Brasil
   com a nova C; vagas continentais; crescimento da C (24 e 28 clubes),
   contado por temporada desde o início e não por ano fixo; reposição da
   Série D.
4. **Criar os clubes que hoje são substitutos.**
5. **Jogadores de 2026:** fechar o injetor (nacionalidade por UID, contrato,
   camisa, seleção, sobras de 2005, atributos ocultos) e montar os elencos.
6. **Teste de viabilidade:** temporada 2026 completa e virada.
7. Depois: regens (nomes, critérios, Preferred Moves), base e instalações,
   entrevistas.

Legenda: ✅ feito e testado no jogo · 🟡 mapeado ou com comando, falta
implementar ou testar · ⚠️ funciona com limitação · ❌ não mapeado.
