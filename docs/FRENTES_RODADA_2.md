# Frentes por fora, rodada 2 (22/10/2026)

A rodada 1 ([FRENTES_DE_TRABALHO.md](FRENTES_DE_TRABALHO.md)) virou mod: tradução,
perfis, comissão, árbitros, rivais, histórico de carreira e nomes de regens. Esta rodada
tem três tipos de entrega:

- **D. Capturas.** Você pega um arquivo ou a memória do jogo numa situação certa e eu
  interpreto. É o que destrava os campos que ainda não sei onde ficam (estrutura e
  orçamento dos clubes, lesões, rigor dos árbitros).
- **E. Dados.** Planilhas. Algumas entram no mod já; outras, depois da captura que
  destrava o campo.
- **F. Gráficos.** Imagens para o jogo.

## Como entregar

1. Planilha: preencha o arquivo de `data\modelos` e salve com o mesmo nome.
2. Rode `python scripts\validar_entregas.py`. Ele lista o que o mod não vai conseguir
   usar (nome que não bate com a `jogadores_2026.xlsx`, clube que não é de 2026, data fora
   do formato, nota fora de 1-20, jogada que o jogo não conhece). Corrija o que aparecer
   em `[CONFIRA]`.
3. Mande: `git add`, `git commit` e `git push` (ou anexe o arquivo aqui).
4. Captura: fica em `workspace\capturas` (fora do git). Zipe a pasta e anexe aqui.
5. As três regras de ouro continuam: fonte e data em todo dado real; branco é "não sei";
   nome do clube e do jogador igual ao da `jogadores_2026.xlsx`.

Já tem uma correção para você: o validador acusa que **Nico Ferreira e Diego Hernández**
(suspensões do Remo) não estão no elenco do Remo na `jogadores_2026.xlsx`. Confira o nome
lá (ou se eles saíram do clube).

## Mapa rápido

| # | Frente | Tipo | Destrava | Esforço |
|---|---|---|---|---|
| D1 | O arquivo `FMM.txt` do FMM2 | captura | o mapa de tudo que o FMM edita (staff, árbitro, lesão, clube) | 1 min |
| D2 | Telas de 12 clubes | captura | estrutura e orçamento dos clubes (E1) | 30 min |
| D3 | Um lesionado e um suspenso | captura | lesões e suspensões no começo do jogo | 20 min |
| D4 | Ficha de 3 árbitros | captura | o "rigor" dos árbitros | 15 min |
| D5 | Chegada da base | captura | conferir regens e joias da base | quando acontecer |
| E1 | Estrutura e dinheiro dos clubes | dados | CT, base e orçamento de 2026 no jogo | médio |
| E2 | Joias da base (`regens_futuros_2026.xlsx`) | dados | regens com nome, data e clube de garotos reais | médio |
| E3 | Técnicos das seleções | dados | as outras seleções além do Brasil | baixo |
| E4 | Histórico de mais jogadores | dados | aba Histórico dos titulares que faltam | médio |
| E5 | Perfil de mais jogadores | dados | personalidade e jogadas da Série B | alto |
| E6 | Elencos 2026 dos sul-americanos | dados | Libertadores e Sul-Americana com os elencos de hoje | alto |
| F1 | Logos das competições | gráficos | Séries A–D, Copa do Brasil, estaduais | médio |
| F2 | Fotos dos jogadores | gráficos | rosto na ficha (caminho a confirmar) | alto |

**Por onde começar:** D1 (1 minuto) e E2 com 3 a 5 garotos, para testar o mecanismo.
Depois D2 e E1, que mudam o jogo de verdade (orçamento e base).

---

## D. Capturas: você pega, eu interpreto

### Como capturar a memória

Com o jogo aberto na situação pedida (não precisa salvar):

    python scripts\capturar.py "<nome de 2026 ou UID>" <rótulo>

O script pergunta o que a tela mostra (escreva numa linha: "lesão no joelho, volta em
15/03"), acha todas as cópias do UID na memória e grava em `workspace\capturas\<rótulo>`.
O nome é procurado nas listas do mod (jogadores, comissão e árbitros de 2026; clubes pela
identidade). Se houver dois com o mesmo nome, ele mostra os UIDs. Ele não muda nada no jogo.

Por que funciona: eu comparo a mesma estrutura em situações diferentes (lesionado x
saudável, clube rico x pobre) e acho o byte que muda junto com o que a tela mostra. Foi
assim que saíram nacionalidade, contrato e caixa do clube na rodada com o FMM.

### D1. O arquivo `FMM.txt`

**Entregar:** o arquivo `C:\Games\Programas\FMM2\FMM.txt` (o "esquema" do FMM2: as
estruturas que ele sabe editar, com as raízes de cada versão do FM). Anexe aqui como está.

**Como eu uso:** o repositório só tem o que foi extraído dele para jogador, contrato,
clube e nação. Com o arquivo inteiro, vejo se ele conhece staff (atributos de técnico),
árbitro (os 10 atributos) e lesão, e monto as próximas capturas já sabendo o tamanho e a
raiz de cada estrutura.

### D2. Telas de 12 clubes

**Entregar:** num New Game (pode ser o seu save), para cada clube abaixo:

1. print da tela de informações do clube (instalações de treino, instalações da base /
   juniores, reputação, profissionalismo);
2. print da tela de finanças (orçamento de transferências e de salários);
3. com a tela aberta: `python scripts\capturar.py "<clube>" clube_<nome>` (ex.:
   `python scripts\capturar.py Flamengo clube_flamengo`).

Clubes: Flamengo, Palmeiras, São Paulo, Corinthians, Fluminense, Grêmio, Athletico-PR,
Bahia, Remo, Ituano, Real Madrid e Barcelona (dos dois últimos o UID é 1736 e 1708).
A mistura de clubes ricos, médios e pobres é proposital.

**Como eu uso:** o texto da tela ("Excelentes", "Boas", "Razoáveis") e os valores dão a
pedra de Roseta: acho o campo na memória e no registro do clube no `server_db` (o
registro de 2005 já tem números de 1 a 20 que parecem ser isso). Destrava a E1.

### D3. Um lesionado e um suspenso

**Entregar:** jogue até ter um jogador lesionado e um suspenso (qualquer clube). Para cada
um: print da ficha (tipo da lesão, volta prevista; jogos de suspensão) e
`python scripts\capturar.py "<nome>" lesionado` (ou `suspenso`). Depois, com o mesmo
jogador recuperado (dias depois), outra captura com rótulo `lesionado_depois`.

**Como eu uso:** acho a estrutura da lesão e da suspensão e ponho no injetor as 4 lesões
e as 2 suspensões da `lesoes_suspensoes_2026.xlsx` (frente A4, parada desde a rodada 1).

### D4. Ficha de 3 árbitros

**Entregar:** depois do `aplicar_tudo.py`, abra a ficha de Raphael Claus, Wilton Pereira
Sampaio e Gleika Oliveira Pinheiro (pela tela de um jogo ou pela busca de pessoas): print
de cada ficha e `python scripts\capturar.py "Raphael Claus" arbitro` (idem para os outros).

**Como eu uso:** o árbitro tem 10 atributos de 1 byte que estão zerados nos brasileiros.
Se a ficha mostrar algum (disciplina, vantagem...), acho qual é qual e ponho o "rigor"
da planilha.

### D5. Chegada da base

**Entregar:** quando chegarem os juniores (o jogo avisa), print da lista de alguns clubes
(Flamengo, São Paulo, Fluminense) e, se aparecer uma joia da E2, print da ficha dela
(nome, idade, clube, nacionalidade).

**Como eu uso:** confere os nomes de hoje (B1) e se o `FUTURE_REGEN` funcionou (nome,
data, clube). Se nenhuma joia aparecer em duas chegadas de juniores, eu reviso o comando.

---

## E. Dados

### E1. Estrutura e dinheiro dos clubes

**Entregar:** aba `Estrutura` da `data\modelos\clubes_estrutura_2026.xlsx`, para os 40
clubes das Séries A e B (os outros podem ficar em branco):

- `ct` e `base_instalacoes`: 1 a 20 (régua: 20 = o melhor do Brasil, como Ninho do Urubu,
  Academia de Futebol, Cotia e Xerém; 10 = CT próprio simples; 5 ou menos = sem CT);
- `orcamento_contratacoes_brl` e `folha_mensal_brl`: o que foi noticiado para 2026;
- fonte e data.

**Como eu uso:** depois da D2, gravo no registro do clube. A base do clube pesa na
qualidade dos regens que ele recebe; o orçamento muda o que a diretoria deixa gastar.

### E2. Joias da base (regens de verdade)

**Entregar:** `data\modelos\regens_futuros_2026.xlsx` (já está no repositório, com a
aba LEIA). Uma linha por garoto: clube, primeiro nome, sobrenome, nome comum, nascimento
(AAAA-MM-DD), nacionalidade, fonte e data. Só quem **não** está na `jogadores_2026.xlsx`:
sub-17, sub-15, a geração nascida de 2008 a 2012 (convocações da seleção sub-17,
Copinha, matérias sobre a base). Comece com 3 a 5 para testar.

**Como eu uso:** já entra. O `aplicar_brasil_2026.py` (e o `aplicar_tudo.py`) grava
`data\db\brasil_2026_regens.edt` com o comando `FUTURE_REGEN` do jogo, que guarda o
garoto na nação e o faz aparecer numa chegada de juniores com esse nome, essa data e esse
clube. Os atributos e a posição o jogo sorteia (não dá para escolher).

### E3. Técnicos das seleções

**Entregar:** `data\brasil\comissao\selecoes_2026.csv`: preencha nome, nacionalidade
(código: ARG, URU, ITA...), nascimento e fonte das 8 seleções sul-americanas em branco.
Se quiser mais seleções (as 48 da Copa de 2026), acrescente linhas com o código da nação;
eu completo os códigos que faltarem.

**Como eu uso:** já entra pelo `aplicar_comissao.py` (como o Ancelotti).

### E4. Histórico de mais jogadores

**Entregar:** mais linhas na aba `Historico` da `data\modelos\historico_carreira.xlsx`, no
mesmo formato (uma linha por passagem). Sugestão: os titulares das Séries A e B que não
estão entre os 100 de hoje. **Como eu uso:** já entra pelo `aplicar_historico.py`.

### E5. Perfil de mais jogadores

**Entregar:** mais linhas na aba `Perfil` da `data\modelos\jogadores_perfil.xlsx`
(personalidade, ocultos e até 5 jogadas). Sugestão: os 11 titulares de cada clube da
Série B. **Como eu uso:** já entra pelo `montar_elencos.py`.

### E6. Elencos 2026 dos clubes sul-americanos

**Entregar:** a lista dos clubes estrangeiros da Libertadores e da Sul-Americana de 2026
(nome, país, fonte). Eu adapto o coletor do Sofascore para eles e você roda aí (a coleta
precisa da internet da sua máquina).

**Como eu uso:** os elencos de hoje entram nos clubes estrangeiros pelo mesmo caminho dos
brasileiros (hospedeiros de 2005, nome, atributos, contrato). Hoje River, Boca e
companhia jogam a Libertadores de 2026 com os elencos de 2005.

---

## F. Gráficos

### F1. Logos das competições

**Entregar:** PNG com fundo transparente das Séries A, B, C e D, Copa do Brasil e dos
estaduais, nos tamanhos do escudo (60×60) e grande (180×180). Primeiro só um (Série A),
para eu confirmar o caminho no jogo (`graphics\pictures\comp\<UID>\logo`, como o dos
clubes, a confirmar).

### F2. Fotos dos jogadores

**Entregar:** só depois de eu confirmar que o FM06 lê foto de pessoa e em que pasta.
Comece com 1 foto (de uso livre ou sua) para o teste. Eu gero a pasta pelo UID de cada
jogador de 2026 (o do hospedeiro).

---

## Como fazer regens diferentes

O que já dá para mexer e o que não dá:

| Alavanca | Situação | Como |
|---|---|---|
| Nomes dos regens | ✅ no mod | `nomes_regens.xlsx` (B1): nomes de hoje com ~70% do peso de cada nação |
| Garotos reais na base | 🆕 testar | E2 (`FUTURE_REGEN`): nome, data e clube de verdade |
| Qualidade da base de cada clube | ⏳ D2 + E1 | o campo de base do clube pesa no regen que ele recebe |
| Força da base de cada país | ⏳ | a nação tem "Development" e "League Standard" (achados na memória pelo FMM); falta achar no banco |
| Posição e atributos de um regen sorteado | ❌ | o jogo sorteia; só dá para mexer depois que ele nasce (injetor) |
