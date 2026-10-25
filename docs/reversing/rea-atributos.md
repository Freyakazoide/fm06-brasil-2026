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

## Resultado (conferido no jogo em 25/10; detalhes no Diário)

**Mapa arquivo → memória → ficha.** Todo registro termina em `[u32 índice][u32 UID]`; os
dados vêm antes.

| Arquivo | Campo | Memória | Na ficha |
|---|---|---|---|
| T2 `[u8 0][8 bytes][índice][UID]`, desde `0x043902B1` | personalidade (Adaptabilidade … Controvérsia) | PData +0x1C..+0x23 (UID+8..+15) | oculto; Desportivismo e Temperamento recebem −sorteio no New Game (`0x00A998B0`) |
| T3 `[u8 0][79 bytes][u8][índice][UID]`, desde `0x0480F3D1` | 0–24 posições, 25–78 atributos (ordem `storage_index` do `playing_attributes_layout.json`), 1–20; 0 = sorteado | Playing +0x1C..+0x6A (UID+8..) | posições específicas iguais; genéricas recalculadas |
| A, jogador tipo 2: `[u32 índice][u8 2][u16 rep. casa][u16 rep. atual][u16 rep. mundo][u16 CA][u16 PA]…` | CA, PA, reputações (×50), peso, altura… | Player+0x14 (CA, UID−204), +0x16 (PA, UID−202) | — |

Conversão no New Game (`0x00A41C40` → `0x008E69C0` → `0x008CDE50`):
- relativos (25–48 menos 33; 77; 78): `cru = trunc((10·f − CA)/2)`; absolutos (33, 49–76):
  `cru = 5·f`;
- ajuste: delta igual em todos os atributos com peso até a média ponderada ficar no alvo
  `0,05·CA + 6` (pesos por posição em `0x014EABA0`, salvos em `workspace/rea/pesos_fm06.json`);
- toda vez que o ajuste roda de novo (ex.: ao abrir a ficha), o jogo **tira o efeito do
  treino do clube, ajusta e põe o treino de volta** (`TRAINING_MANAGER`, `0x00A659B0` /
  `0x00A657A0`). Na primeira vez, o saldo é o próprio bônus do treino (+1 a +3 internos);
- ficha: relativo `v = trunc(5·max(1, (2·cru + CA)/10 + 0,5))` (máx. 100), absoluto `v = cru`;
  exibido `trunc((v + 2)/5)`.

Consequência: com CA coerente e par, a ficha mostra o arquivo **mais o bônus do treino**;
os relativos ficam no topo da faixa, então o bônus vira +1 neles; os absolutos só sobem com
+3. Isso vale igualmente para o injetor (ele grava antes desse ajuste).

**CA e PA (passo 4):** lidos do registro A, não recalculados (8 de 8 no jogo). O que o jogo
recalcula são os atributos, para baterem com o CA.

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
- 25/10 **Teste 1 — deu certo (memória conferida).** Cópia do `people_db.dat` do jogo com
  8 jogadores do Flamengo regravados a partir de `workspace/mods/brasil_2026_jogadores.json`
  (Paquetá 3300989, Arrascaeta 316261, Pedro 316734, Samuel Lino 2103165, Danilo 3301241,
  Léo Ortiz 3301174, Jorginho 311145, Rossi 315094): os 79 bytes da T3, a personalidade da
  T2 e CA/PA do registro A (591 bytes; nada fora disso). New Game no `fm_brasil.exe` **sem
  o injetor**; memória lida (só leitura) por `workspace/rea/tools/conferir_teste.py`.
  - **CA e PA: 8 de 8 iguais ao arquivo** (ex.: Paquetá 136/168 → 168/168).
  - **Atributos: o modelo (conversão + ajuste com os pesos lidos de `0x014EABA0`) prevê a
    memória byte a byte** em todos os 54 atributos de todos os 8, fora os sorteios
    previstos (f = 20/1 nos relativos, f = 0). O ajuste deslocou igualmente os atributos
    com peso: Pedro −1, Danilo +1, Jorginho +1, os outros 5 com 0 (ficha = arquivo).
  - Posições: as específicas (Lateral D., Zagueiro C., Meia C. …) ficam como gravadas; as
    genéricas (Líbero, Volante, Meio-campo, Meia ofensivo) o `0x00A9A740` recalcula a
    partir das específicas (Paquetá Volante 12 → 1, Meio-campo 16 → 20).
  - Rossi: os ocultos que o JSON não traz e estavam 0 no arquivo (Desonestidade, Jogos
    Importantes, Versatilidade) foram sorteados — esperado.
  - **Personalidade:** campos 1–5 e 8 iguais ao arquivo nos 8; **Desportivismo e
    Temperamento caem entre 0 e 11** em todos. Causa achada: PData::completar
    `0x00A998B0` sorteia os campos fora de 1..20 e depois, conforme um código do objeto
    passado (método virtual +0x10; hipótese: região da nacionalidade), faz casos 4/0xC:
    −sorteio(12) nos dois; 6/8: −sorteio(10) no Desportivismo; 0xB: +sorteio(8) nos dois;
    0xD: −sorteio(5) nos dois. Não dá para fixar pelo arquivo (o injetor fixa).
  - **Fichas (screenshots do usuário, Paquetá, Arrascaeta, Pedro, Danilo) — tiradas depois
    de alguns jogos.** Duas correções:
    1. **Fórmula da ficha corrigida.** A de cima dava −1. O que bate com os 48 valores das 3
       fichas comparadas (com a memória relida na mesma hora): relativo
       `v = trunc(5 · max(1, (2·cru + CA)/10 + 0,5))` (máx. 100, o caminho "escala 1–100" do
       `0x00A3D720`) e **ficha = trunc((v + 2)/5)** para todos (a regra dos absolutos,
       `0x00A3CB50`). Com ajuste 0 e **CA par**, ficha = arquivo. Com **CA ímpar**, todo
       relativo com 10·f < CA aparece **f + 1** (o `trunc((10f − CA)/2)` de número negativo
       arredonda para cima) — explica Léo Ortiz (151) e Samuel Lino (153). O gravador tem
       de compensar (escolher o f que dá a ficha desejada).
    2. **A memória mudou com os dias de jogo:** na 2ª leitura todos os atributos com peso
       subiram de 1 a 3 (média ponderada 0,2–0,6 acima do alvo, CA parado). Logo depois do
       New Game o ajuste tinha deixado a média a ≤ 0,08 do alvo `0,05·CA + 6` nos 8. A
       subida é evolução do jogo com o tempo (não é leitura do arquivo); a validação tem de
       ser feita na ficha **antes de avançar** o calendário.
  - **Idade, nacionalidade, posição "errada" (Arrascaeta 22 anos, Pulgar PL brasileiro de
    18):** não vieram do teste (Pulgar nem foi gravado; o diff só tinha os 591 bytes). Para
    **jogadores**, o `people_db.dat` do mod ainda tem nome, nascimento, nação, altura e peso
    do jogador original do FM06 no UID (Arrascaeta 316261 = "Obina", 1983 → 2003 com o +20;
    Pulgar 2100693 = "Fabiano Oliveira", BRA, 1987). Quem troca isso hoje é o **injetor**
    (`LivePlayer.plan`: nascimento, nacionalidade, altura, peso, reputações). O gravador
    offline terá de gravar também esses campos no registro A (layout acima e em
    `comissao.py`), senão o mod sem injetor fica com as idades/nações erradas.
  - Tabela de pesos lida do jogo salva em `workspace/rea/pesos_fm06.json` (15 posições ×
    79, mapa de posições `[0, 1, 12, 13, …, 24]` de `0x012E3F80`).
- 25/10 **Teste 2 (preparado):** mesmos 8, a partir do backup do mod
  (`workspace/backups/people_db.antes_teste1.dat`), com **CA coerente** com os atributos
  (o CA par mais perto do da planilha para o qual o ajuste não mexe): Paquetá 168,
  Arrascaeta 160, Pedro 164 (planilha 154), Lino 152 (153), Danilo 138 (152), Léo Ortiz 152
  (151), Jorginho 136 (150), Rossi 142 (148); PA ≥ CA. Simulação: ficha = JSON em todos os
  atributos dos 8. Validar na ficha **no dia do New Game, sem clicar em Continuar**.
- 25/10 **Teste 2 — não bateu (resultado útil).** Fichas no dia do New Game (Paquetá,
  Danilo, Rossi): **absolutos e físicos iguais ao arquivo; relativos +1** em quase todos.
  CA/PA 8 de 8 iguais. Memória: o modelo (conversão + ajuste) está certo, mas **depois do
  ajuste algum passo soma +1 a +3 (sorteado por jogador) em todos os atributos com peso**,
  relativos e absolutos (Paquetá Pênaltis 75 → 77; k: Paquetá 2, Arrascaeta 1, Pedro 1,
  Lino 3, Danilo 2, Ortiz 2, Jorginho 3, Rossi 2). No teste 1 a 1ª leitura foi feita antes
  desse passo; a 2ª já o tinha (não era "evolução com os dias"). Como a conversão põe os
  relativos no topo da faixa (v = 5f + 2), qualquer k ≥ 1 vira f + 1 na ficha; os absolutos
  (v = 5f) só sobem com k = 3 (Lino, Jorginho).
  - Descartados: segundo ajuste (o alvo é `vtable[0]` = CA, `0x00A46A30`, e a média passou
    do alvo), `0x00A9CC40` (grava 1 byte em outro objeto), `0x00775B90` (gera regens).
  - Próximo: `workspace/rea/tools/vigia_escrita.py` (depurador só com registradores de
    depuração: para em `0x00A42D50`, depois do ajuste, e vigia a escrita no byte de Pênaltis
    dos jogadores do teste) para pegar o endereço de quem soma o k.
- 25/10 **Vigia (teste 2, novo New Game) — achado.** Parou no Arrascaeta (Playing
  `0x11185F50`, Pênaltis = 70 = modelo) depois de 5.120 jogadores. Na tela principal, sem
  abrir fichas, os bytes continuaram iguais ao modelo (Arrascaeta 70, Paquetá 75). Ao
  **abrir a ficha** do Arrascaeta, 3 escritas no byte:
  1. 70 → 68, EIP `0x00A648D9`, pilha `0x00A652DA ← 0x00A65BA0 ← 0x008CDEF1`
     (`0x00A659B0`, chamado no começo do ajuste: tira o efeito do treino);
  2. 68 → 69, EIP `0x008CE2F6` (o ajuste: delta +1);
  3. 69 → 71, EIP `0x00A648D9`, pilha `0x00A652DA ← 0x00A6598D ← 0x008CE34A`
     (`0x00A657A0`, no fim do ajuste: põe o treino de volta).
  As funções são do `TRAINING_MANAGER::get_modified_player_data()` /
  `PLAYER_TRAINING_INFO::apply_ability_changes()` (mensagens no código): 9 categorias de
  treino (`0x00A8B040`) distribuídas nos atributos (`0x00A651C0`), aplicadas por
  `0x00A65220` (relativos limitados a −14..115 em `0x00A648B0`). O +k é o bônus do treino
  do clube, somado na primeira vez que o ajuste roda depois do New Game. **Mapa e CA
  conferidos**; o +1 da ficha nos relativos é mecânica do jogo (vale para o injetor também).
  `people_db.dat` do mod restaurado do backup.
- 25/10 **Gravador offline (passo 5, aprovado pelo usuário com "CA coerente"):**
  `src/fm06patch/atributos_jogadores.py` + `scripts/gravar_atributos.py` (simulação; `--apply`;
  `--uids`; `--people`/`--out`) + `tests/test_atributos_jogadores.py` (o modelo bate com a
  memória do Arrascaeta e do Danilo no teste 1; a ficha com as das screenshots). Pesos em
  `reverse/fmm/pesos_posicoes.json`. Grava T3 (atributos e posições), T2 (personalidade) e,
  no registro do jogador, reputações (/50), CA, PA (≥ CA), peso (+38), altura (+40),
  nascimento (com `year_shift`) e nação (conferidos nas âncoras: peso/altura 4 de 4;
  Zidane 23/06/1972, França 0x8F). Ainda não grava preferred moves nem jogos/gols pela
  seleção. Registros A de tipo 0/1 (7 dos 6.542) ficam de fora.
  - **CA "coerente":** o CA par mais perto da planilha com o qual o ajuste do New Game desce
    os atributos 3 pontos internos (`ALVO_AJUSTE`); o treino (+1 a +3) os devolve para o meio
    da faixa e a ficha mostra a planilha com folga de ±1 ponto interno.
  - **Atenção (decisão pendente antes de usar em todos):** simulação com os 6.542 — o CA
    cai mediana −30 (CA 60–99 da planilha: −30 a −32; 140–159: −17). ~12 pontos são a
    compensação do treino; o resto é porque os atributos do JSON ficam abaixo do que o FM06
    espera para o CA da planilha (alvo 0,05·CA + 6). Com o injetor de hoje acontece o
    inverso: ao refazer o ajuste, o jogo sobe os atributos até o CA da planilha.
  - **Teste 3 (instalado):** `people_db_teste3_gravador.dat` = mod + gravador em 8 jogadores
    (Paquetá 168→158, Arrascaeta 160→150, Pedro 154, Danilo 152→126, Léo Ortiz 151→140,
    Rossi 148→130, Joaquín Freitas 116→104, Kaio Júnior 90→62); 647 bytes, nada fora do
    previsto. Ficha prevista = JSON em todos os atributos.
- 25/10 **Teste 3 — deu certo (com 2 ressalvas).** Fichas do usuário (Joaquín Freitas,
  Kaio Júnior, Léo Ortiz), New Game sem injetor: **Freitas e Ortiz: os 36 atributos iguais
  ao JSON**; altura, peso e nacionalidade certos nos três (Freitas argentino); o usuário
  diz que os outros 5 também bateram ("quase perfeito, alguns com 1 de diferença").
  - **Kaio Júnior (Sub-20): absolutos com peso −1** (Cantos, Livres, Pênaltis, Bravura,
    Influência, físicos); relativos certos. Hipótese: o treino dele deu saldo 0 (o gravador
    supõe +2); com saldo 0 o −3 do ajuste deixa os absolutos em 5f − 3. Não conferido na
    memória. Trocar o alvo para −2 erraria o caso oposto (saldo +3, 3 de 16 casos medidos).
  - **Nascimento: ano certo, dia/mês sorteados.** Não é o gravador: o executor do
    `CHANGE_PLAYER_NAME` (`0x00AAA4B0`) troca o nome e **sorteia um dia diferente do original
    no mesmo ano** (laço `aleatório(365)` em `0x00AAA600`, grava com `call [edx+0x1A0]` em
    `0x00AAA645`) — proteção do FM06 para nomes fictícios. Conferido na memória do jogo
    aberto: jogadores fora do mod 98/100 com a data do arquivo; do mod (renomeados pelo
    `.lnc`) 4/342. O injetor só acerta porque grava depois. Opção: patch de 6 bytes no
    `fm_brasil.exe` em `0x00AAA645` (`FF 92 A0 01 00 00` → `83 C4 04 90 90 90`, descarta o
    argumento e não chama) — não feito nem testado.
- 25/10 **Aprovado pelo usuário: gravar em todos com o CA coerente + patch do nascimento.**
  - Patch `nascimento_lnc_fixo` em `src/fm06patch/exe_patches.py` (0x6AA645 no arquivo) e na
    lista `EXE_PATCHES` do `aplicar_brasil_2026.py`. O `fm_brasil.exe` gerado difere do
    anterior só nesses 6 bytes (o anterior era idêntico ao da lista sem o patch). Backup do
    exe anterior em `workspace/backups/fm_brasil.antes_nascimento.exe`. A função chamada
    desempilha o argumento (nenhum `add esp` depois do `call`), por isso `add esp, 4`.
  - `gravar_atributos.py --apply` na etapa 3 do `aplicar_tudo.py` (por último). Com todos
    os 6.542: 6.535 gravados, 526.606 bytes mudados, nenhum fora do previsto, tabelas
    íntegras (`workspace/experiments/people_db_gravador_todos.dat`).
  - **A etapa 4 (injetor) continua no `aplicar_tudo.py`** e, se rodar, grava na memória o CA
    da planilha e os atributos por cima do que o gravador fez. Decidir se sai (passo 6).
  - Falta conferir no jogo: o dia do nascimento com o patch e algumas fichas com todos.
- 25/10 **New Game com todos — travou** (dump `FM 2006 v6.0.2.72973 (2026.10.25 13.30.56).dmp`):
  `0xC0000005` em `0x009F02C5` (`FUN_009EFCB0`), lendo [0]: a lista de pessoas
  (`param_1+0x34`) tinha o elemento 0 nulo, ou seja, a carga do people_db falhou. Causa: o
  separador de registros (u16 ano, 00 00 00, índice, UID) casa por acaso dentro de registros
  (~5.700 no banco); em 10 jogadores do mod o "início" do registro saiu errado e, em 3 deles
  (Renzo Garcés, Felipe 2114704, Neymar 3301206), o byte ali era 2: o gravador escreveu
  reputação/CA/PA/peso/altura no meio de outro registro e a leitura dessincronizou. O teste
  com 8 não pegou nenhum desses.
  - Correção em `person_records`: um fim com índice X só vale se outro fim anunciar X como o
    seguinte (o 1º vem de 0x19) e o u32 antes do início for X; pares sobrepostos saem os
    dois. Resultado: 275.043 registros, 0 com encadeamento quebrado, 0 sobrepostos; 9
    jogadores do mod sem registro confiável ficam de fora (aviso). O `apply` agora confere que
    tabelas e limites dos registros não mudaram, e o bloco de nomes não pode estar antes de
    +48. Teste novo com um falso fim de registro no meio de outro. Arquivo novo difere do que
    travou só nesses jogadores; `people_db.dat` do mod tinha sido restaurado logo após o crash.
