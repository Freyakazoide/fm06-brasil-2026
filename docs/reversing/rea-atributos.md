# Atributos dos jogadores direto no people_db.dat (engenharia reversa do fm.exe)

## Objetivo

Gravar CA, PA, os atributos 1–20, as posições e a personalidade dos jogadores de 2026
**direto no `data/db/people_db.dat`**, como o mod já faz com nome, nacionalidade,
nascimento, contrato, clube e campo "time". Hoje esses dados vão pela memória do jogo
aberto (`scripts/live_player_editor.py`, etapa 4 do `aplicar_tudo.py`), o que exige:

- o jogo aberto e um segundo New Game;
- que o jogo tenha carregado o jogador (a opção "Carregar Todos Jogadores de" do New
  Game; sem ela os clubes da CONMEBOL ficavam vazios);
- o mesmo save depois (o que o injetor muda só existe naquela partida).

Com os atributos no arquivo, o mod fica: planilhas -> scripts -> um New Game.

Princípios do REA (`github.com/morluto/rea`, "Reverse Engineer Anything"): achados
com evidência (endereço, bytes, teste), uma hipótese por vez, cada teste num arquivo
de cópia, e o que não deu certo registrado aqui.

## O que já se sabe

Do arquivo (`docs/reversing/people-db.md`):

- cabeçalho com os totais das tabelas: A (pessoas, 277.936, tamanho variável), T2
  (277.340, 17 bytes: u32 índice, u32 UID, 9 bytes), T3 (222.888, 89 bytes: u32
  índice, u32 UID, 81 bytes de 0 a 20) e duas tabelas ainda não localizadas (56.704 e
  144.090);
- no registro A do Saviola (UID 3100367), `+15` u16 = 160 bate com o CA da memória em 3
  de 4 âncoras, mas **mudar esse campo não muda o CA no jogo** (recalculado? o comando
  `WEIGHTING` de posição × atributo × peso aponta para isso). `+17` (PA?) nunca bateu;
- T2 não bate com a personalidade da memória (PData) e T3 não bate com os bytes da
  memória (Playing), nem ×5 nem por fórmula linear;
- gravar um padrão nos 81 bytes da T3 do Saviola **travou o New Game**
  (`fm.exe` 0x009F02C5, método virtual num elemento nulo): parte da T3 são
  referências ou flags. Mexer uma coluna por vez, com valores plausíveis;
- o registro A tem nomes, nascimento, nação, seleção, campo "time", cargo e contrato
  (`src/fm06patch/comissao.py`, `people_contracts.py`).

Da memória (`src/fm06patch/live_player.py`, `reverse/fmm/*.json`):

- objetos Player (456 bytes), PData (36) e Playing (112), cada um começando por 5
  ponteiros e o UID;
- o 1º ponteiro é a **vtable** da classe, no `.rdata` do `fm.exe` 6.0.2 original:
  Player 0x010F1034, PData 0x010B697C, Playing 0x010BA73C (todas apontam para
  funções no `.text`). Conferido em 25/10;
- atributos em Playing: absolutos (memória = 5 × valor), relativos ao CA (byte com
  sinal; exibido = (memória + base) / 5, base 86 com CA 160 e 97 com CA 185) e
  posições direto em 1–20 (`reverse/fmm/playing_attributes_layout.json`).

## Passos

1. **Ferramentas.** No PC: Ghidra (precisa do JDK 21) e, se quiser o fluxo do REA, o
   servidor MCP dele (Node.js 22+; instruções no README do repositório). Analisar o
   `fm.exe` **original** (o 6.0.2 sem patches; não o `fm_brasil.exe`), numa cópia.
   Um depurador (x64dbg) ajuda nos passos 3 e 4.
2. **Achar o leitor do people_db.** Pontos de partida: as referências à string
   `people_db` e as funções que gravam as vtables acima (construtores de Player,
   PData e Playing). Quem chama o construtor do Playing durante o New Game e de onde
   vêm os bytes que ele guarda: é o leitor da T3 (ou de outra tabela).
3. **Mapear os campos.** Para cada byte que o leitor copia do arquivo para o Playing e
   o PData, a coluna da T3/T2/A de origem e a conversão. Conferir com 3 ou 4 jogadores
   conhecidos (Saviola 3100367, Zidane, e os das âncoras em `reverse/fmm/anchor_*.json`).
4. **CA e PA.** Achar se o CA é lido do arquivo ou recalculado dos atributos (pesos por
   posição). Se recalculado, o gravador escreve os atributos e o CA sai deles; o PA
   tem de vir de algum campo.
5. **Gravador offline.** `src/fm06patch/` novo módulo que escreve os campos mapeados
   no people_db a partir do `brasil_2026_jogadores.json` do `montar_elencos.py`.
   Validar com 5 a 10 jogadores no jogo (ficha igual à planilha) antes de usar em todos.
6. **Trocar o injetor.** O `aplicar_tudo.py` grava os atributos na etapa 3 e a etapa 4
   (jogo aberto, injetor) sai. O `live_player_editor.py` fica para conferência.

## Regras

- Nunca mexer no original: partir sempre de `workspace/baseline/*.original.dat` e de
  uma cópia do `fm.exe`.
- Um teste por vez, com o resultado (deu certo, travou, sem efeito) registrado aqui.
- Achado só entra no mod com teste no jogo.

## Diário

- 25/10: plano; vtables de Player, PData e Playing conferidas no `.rdata` do `fm.exe`
  6.0.2; a string `people_db` existe no executável (ASCII).
