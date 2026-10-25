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
- 25/10 (estático, cópia `workspace/rea/fm_602_original.exe`, SHA-256 `3C20470A…5B90`;
  Ghidra 12.1.4 headless + capstone). **Conferido no código e no arquivo:**
  - Leitor genérico de lista `0x00A0C100` (e ~40 cópias, uma por lista): u32 total, e por
    registro um **byte de tipo** e `switch`: 0 = Playing (`new 0x70`, ctor `0x007B9670`),
    1 = 0x140 (não jogador), 2 = Player (`new 0x1C8`, ctor `0x00A47930`), 3 = 0x210
    (os dois). Depois chama o `load` virtual (entrada 10 da vtable).
  - **Os dados vêm antes do índice e do UID.** O `load` da base `0x00A3AE50` lê u32 → +0x18
    (índice) e u32 → +0x14 (UID) no fim. A doc antiga lia as tabelas com o UID no começo,
    então os bytes "do Saviola" eram do jogador seguinte (por isso T2/T3 "não batiam" e o
    padrão na T3 travou: ele sobrescreveu tipo/índice/UID do próximo registro).
  - **T2 = personalidade** (PData `load` `0x00A99D70`: 8 × u8 → +0x1C..+0x23). Registro
    `[u8 tipo 0][8 bytes][u32 índice][u32 UID]`, início `0x043902B1` (o u32 em `0x043902AD`
    é o total 277.340). Os 277.340 índices conferem 0..n−1. Personalidade bate com a
    memória nas 5 âncoras nos campos 1–5 e 8; Desportivismo e Temperamento saem menores na
    memória em 4 das 5 (o 8076 bate inteiro) — hipótese: ajuste depois do load, a conferir.
  - **T3 = os 79 bytes do Playing** (`load` `0x00A9A6B0`: lê 0x4F bytes crus → +0x1C, zera
    +0x6B, u8 → +0x6C). Registro `[u8 tipo 0][79 bytes 1–20][u8][u32 índice][u32 UID]`,
    início `0x0480F3D1` (total em `0x0480F3CD`; depois vem `56704`). Ordem dos 79 =
    `storage_index` de `reverse/fmm/playing_attributes_layout.json` (0–24 posições, 25–78
    atributos). 0 = "não definido": `0x00A9A740` sorteia (usa CA/PA) e deriva as posições
    genéricas (lado direito/esquerdo/centro).
  - **Registro A do jogador:** `[u32 índice][u8 tipo 2][u16 rep. casa][u16 rep. atual]
    [u16 rep. mundo][u16 CA][u16 PA][u32][u32][u32][u8][u8][u16]…[u16 peso][u16 altura]…`
    e no fim a parte comum (nomes, nascimento… `0x00A717D0`) com `[u32 índice][u32 UID]`
    (Player `load` `0x00A3C3B0`, base virtual da vtable `0x010F1034` em Player+0xCC).
    Na memória: **CA = Player+0x14 = UID−204, PA = +0x16 = UID−202** (os do
    `live_player.py`). CA/PA do arquivo batem exatos com a memória em 3 âncoras
    (321081 155/188, 3300977 163/177, 8076 185/192). O teste antigo do CA (`A+15`
    160→111) mexeu no registro do **próximo** jogador (UID 3100020): por isso "sem efeito".
  - Preparação depois do load `0x00A41C40`: reputações × 50; CA/PA do arquivo ficam (só
    sorteia se fora de 1..200; se PA < CA, o jogo faz CA = PA − sorteio(40)); chama
    `0x00A9A740` (completa zeros), **`0x008E69C0(CA)`** (converte) e **`0x008CDE50`** (ajusta).
  - **Conversão `0x008E69C0`:** relativos (25–48 menos 33; 77; 78) `cru = trunc((10·f −
    CA)/2)` (f = 20 num atributo-chave da posição: + sorteio(50 − (200−CA)/2); f = 1 fora
    da posição: − sorteio(50 − CA/4)); absolutos (33, 49–76) `cru = 5·f`; posições iguais.
    Zidane (CA 185) e o goleiro 3300977 (CA 163) batem byte a byte com a memória.
  - **Ajuste `0x008CDE50` (pesos):** pesos por posição de `0x00A9A390` (tabela posição ×
    atributo em `0x014EABA0`, a do comando `WEIGHTING`; só posições com nota ≥ 10); alvo
    `T = 0,05·CA + 6` (`0x00A9A370`); média ponderada `M` dos atributos na escala 0–20;
    `delta = arred((T − M)·5)` somado a todos os atributos com peso; repete até |delta| ≤ 2
    (máx. 10). Explica o deslocamento igual por jogador nas âncoras (321081 +2, goleiro −1,
    Zidane 0) e por que Instinto, Determinação, Consistência etc. (peso 0) ficam exatos.
  - **Ficha:** relativo `trunc((2·cru + CA)/10 + 0,5)` (`0x00A3D720`, CA em
    `[base−0xB8]`); absoluto `trunc((cru + 2)/5)` (`0x00A3CB50`); ambos 1..20.
  - **Resposta do passo 4 (código):** o CA **é lido do arquivo** e não é recalculado; são
    os atributos que o jogo desloca até a média ponderada bater com o CA. O PA também vem
    do arquivo (A, logo depois do CA). Falta conferir no jogo (teste 1).
  - A tabela de pesos não está em nenhum arquivo de texto do jogo nem nos `.dat` (só em
    memória: 15 linhas de 79 bytes no heap); será lida da memória no teste 1.
