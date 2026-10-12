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
| Divisão em que joga | ✅ | texto | `SWAP_TEAMS` (troca 1 por 1) |
| Cores do uniforme | 🟡 | texto | `COLOUR_CHANGE` |
| Estádio e capacidade | 🟡 | texto | `STADIUM_MOVE`, `STADIUM_CAPACITY_CHANGE`, `GROUND_SHARE` |
| Dinheiro, reputação, público | 🟡 | texto / injetor | `BOOST_TEAM`; Cash no injetor |
| Orçamentos, instalações, base | ❌ | injetor | campos do clube não localizados |

## Competições

| Item | Situação | Caminho | Observação |
|---|---|---|---|
| Nome da competição | 🟡 | texto | `COMP_NAME_CHANGE` |
| Quais clubes estão em cada série | ✅ | texto | `SWAP_TEAMS`, limitado à estrutura existente |
| Número de clubes por divisão | 🟡 | executável | regras ficam no `fm.exe` (módulo Brasil em `0xBB2700`); ver `docs/reversing/competitions.md` |
| Formato (pontos corridos, turno e returno) | 🟡 | executável | idem |
| Acessos e rebaixamentos | ✅ | executável | `scripts/patch_exe.py` (campos `+0x11`/`+0x14` da fase); validado: Série A rebaixa 4, Série B sobe 4 |
| Criar a Série D | ❌ | executável | 4º nível no sistema de ligas + reaproveitar uma competição existente; exige code cave |
| Vagas em Libertadores e Sul-Americana | ❌ | banco | idem |
| Histórico de campeões (Séries A–D, pelo menos os últimos) | ❌ | banco | não localizado |
| Calendário | ❌ | banco / executável | |

## Jogo

| Item | Situação | Caminho | Observação |
|---|---|---|---|
| Ano de início 2026 | ❌ | banco / executável | |

## Ordem sugerida

1. **Investigar as regras de competição no `server_db`.** É o maior risco: decide
   se a Série D e o formato de 2026 são possíveis. Melhor descobrir cedo.
2. **Fechar o jogador no injetor:** nacionalidade por UID da nação,
   contrato completo, número da camisa, seleção, retirar as sobras de 2005 e
   atributos ocultos na planilha. Tudo já está mapeado; é implementação.
3. **Histórico de carreira:** escritor para `pl_hist_*.dat`, que seria a
   primeira escrita de verdade no banco.
4. **Ano de início 2026.**
5. **Jogadores novos sem hospedeiro**, só se os hospedeiros não bastarem.

Legenda: ✅ feito e testado no jogo · 🟡 mapeado ou com comando, falta
implementar ou testar · ⚠️ funciona com limitação · ❌ não mapeado.
