# FM06 Brasil 2026 — Missão Codex para reconstrução de estruturas via FMM

## Objetivo

Usar o `FMM.txt`, o FMM 2.x funcionando com Football Manager 2006 6.0.2 e os scripts já existentes no repositório para reconstruir, com evidência, o maior número possível de campos de:

- jogador;
- dados pessoais;
- atributos;
- posições;
- preferred moves;
- contrato;
- clube;
- nação;
- staff/coaching;
- demais estruturas explicitamente descritas pelo FMM.

O objetivo **não** é apenas achar valores em RAM. O objetivo final é produzir um mapa técnico confiável que permita relacionar:

```text
FMM.txt
    ↓
estrutura da partida em RAM
    ↓
save / objetos vivos
    ↓
people_db.dat / server_db.dat / client_db.dat
    ↓
patcher/editor do projeto fm06-brasil-2026
```

O trabalho deve ser investigativo e automatizado. Não pare a cada descoberta pequena. Faça lotes grandes de análise, gere scripts reutilizáveis e entregue relatórios de melhores matches com níveis de confiança.

---

# 1. Regras obrigatórias

## 1.1. Não inventar semântica

Se um campo ainda não estiver comprovado, **não dê nome definitivo**.

Use nomes como:

```text
unknown_u8_01
unknown_u16_02
candidate_home_reputation
candidate_contract_start
reference_raw
```

Nunca transformar uma hipótese em fato apenas porque o valor “parece fazer sentido”.

---

## 1.2. Evidência mínima para confirmar um campo

Um campo só pode ser marcado como `CONFIRMED` se houver uma destas situações:

### Regra A — alteração controlada

O FMM altera **um único campo conhecido** e o diff de RAM encontra a alteração exata.

Exemplo já confirmado:

```text
Javier Saviola
UID = 3100367

CA:
160 -> 161

RAM:
UID address = 0x0FC90168
CA address  = UID - 204
A0 -> A1
```

Isso é evidência forte.

### Regra B — repetição estrutural

O mesmo offset relativo funciona para pelo menos 3 jogadores diferentes e os valores batem com o FMM.

### Regra C — FMM.txt + RAM + valor conhecido

O `FMM.txt` define explicitamente o campo e o valor é localizado na mesma estrutura em jogadores diferentes.

---

## 1.3. Níveis de confiança

Todo resultado deve receber uma classificação:

```text
CONFIRMED
HIGH
MEDIUM
LOW
REJECTED
```

Critérios sugeridos:

### CONFIRMED

- alteração controlada;
- ou 3+ jogadores com mesmo offset e valor exato;
- ou evidência equivalente.

### HIGH

- 2 jogadores com mesmo offset e valor exato;
- e estrutura coerente.

### MEDIUM

- 1 jogador com match exato;
- ou vários jogadores com transformação ainda não compreendida.

### LOW

- proximidade numérica;
- coincidência parcial;
- match sem estrutura consistente.

### REJECTED

- hipótese testada e contrariada pelos dados.

---

# 2. Build alvo

Football Manager 2006:

```text
FileVersion    = 6.0.2
ProductVersion = 6.0.2f72973
```

Executável:

```text
C:\Games\Football Manager 2006\fm.exe
```

O projeto está normalmente em:

```text
C:\Users\Pichau\Desktop\fm06-brasil-2026
```

Não trocar para FM 6.0.3.

---

# 3. FMM.txt é a referência principal de schema

Localize `FMM.txt` dentro do projeto ou em arquivos disponíveis.

Ele contém categorias como:

```text
[City]
[Club]
[Club Team]
[Coaching]
[Contract]
[Division]
[Finance]
[Gamer]
[Nation]
[Nation Team]
[Person Name]
[PData]
[Player]
[Player Staff]
[Playing]
[Stadium]
[Staff]
```

Os números hexadecimais no começo do arquivo devem ser tratados inicialmente como **endereços/raízes/candidatos específicos de versões/builds**, e não como offsets de campo confirmados.

Determine por validação qual linha/conjunto corresponde ao FM 6.0.2f72973 em execução.

Não assumir pela posição da linha.

---

# 4. Schema conhecido pelo FMM

## 4.1. Playing Attrib

O FMM declara 79 campos de atributos/posição.

Entre eles:

```text
Crossing
Dribbling
Finishing
Heading
Long Shots
Marking
Passing
Tackling
First Touch
Technique
Penalty
Corner
Set Pieces
Throwing

Creativity
Anticipation
Decision
Positioning
Off the ball
Composure
Concentration
Flair
Influence
Dirtiness
Bravery
Consistency
Aggression
Imp. match
Versatility
Determination
Team work
Work rate

Acceleration
Strength
Stamina
Pace
Jumping
Balance
Injury prone.
Natural fit.
Agility

Left foot
Right foot

Handling
Aer ability
Cmd of area
Communiction
Kicking
Long throws
One on one
Reflexes
Eccentricity
Rushing out

Punch
Goalkeeper
Sweeper
Defender
Def. Mid.
Midfielder
Att. Mid.
Attacker
Wing back
Free role

Right side
Left side
Center side

Left Def.
Center Def.
Right Def.
Def. C.M.
Mid. Left
Mid. Center
Mid. Right
Att. M.L.
Att. M.C.
Att. M.R.
Att. Center
Wing B.L.
Wing B.R.
```

Reconstruir ordem, tamanho e offsets reais em RAM.

---

## 4.2. Personal Info

O FMM conhece explicitamente:

```text
Nationality
Born
Value
Ask Value
Current Ability
Potential Ability
Height
Weight
Home Rep.
Current Rep.
World Rep.
Int. Caps
Int. Goals
U21 Caps
U21 Goals
Morale
Fitness
Jadedness
Match Exercise
Adaptability
Ambition
Loyalty
Pressure
Professional
Sportsmanship
Temperament
Controversy
```

Esses nomes devem ser usados como candidatos prioritários para o mapeamento.

---

## 4.3. Contract Info

O FMM conhece:

```text
Club
Wages
Started
Expires
Squad Status
Transfer
Loan
Unhappy
Happiness
Squad Number
Apears
Goal
Assist
Clean Sheet
Mini Release
Agreed Price
```

Objetivo: reconstruir completamente o bloco de contrato vivo.

---

## 4.4. Nation Info

```text
Capital
FIFA Ranking
Ranking Points
Stadium
Group Member
Importance
League Standard
Development
Economic Factor
Reputation
```

---

## 4.5. Club Info

```text
Last Division
Last Position
Match Day
Prof. Status
Reputation
Facilites
Youth Setup
Average Attend
Minimum Attend
Maximum Attend
Cash
Transfer Budget
Budget Remain
Available(%)
Wage Budget
Used
Name
Capacity
Seating
Used Cap.
Expansion Cap.
Pitch Width
Pitch Length
```

---

## 4.6. Preferred Moves

O FMM lista 48 preferred moves.

Reconstruir:

- representação;
- bitmask/array/flags;
- offsets;
- ordem;
- relação com a lista textual do `FMM.txt`.

---

# 5. Âncoras conhecidas

## 5.1. Javier Saviola

```text
Public UID = 3100367
Nationality = Argentina
DOB = 11/12/1981
Height = 168
Weight = 61

FMM antes da alteração:
CA = 160
PA = 179

FMM reputations:
Home Rep.    = 8198
Current Rep. = 7998
World Rep.   = 5862

Int Caps  = 29
Int Goals = 1
U21 Caps  = 0
U21 Goals = 0

Morale         = 20
Fitness        = 4000
Jadedness      = 0
Match Exercise = 7080

Adaptability = 12
Ambition      = 18
Loyalty       = 13
Pressure      = 14
Professional  = 15
Sportsmanship = 5
Temperament   = 12
Controversy   = 8
```

A partida mostra Saviola no Sevilla, emprestado pelo Barcelona.

Contrato de empréstimo Sevilla:

```text
Wages   = R$650.000/mês
Started = 01/06/2005
Expires = 30/06/2006
Loan from Barcelona
```

Contrato Barcelona:

```text
Started = 01/07/2001
Expires = 30/06/2007
Release clause = R$180.000.000
```

---

## 5.2. CA vivo confirmado

Para Saviola:

```text
RAM player UID address = 0x0FC90168
CA                     = UID - 204
PA                     = UID - 202
```

Alteração controlada:

```text
CA 160 -> 161

0x0FC9009C
A0 -> A1
```

Logo:

```text
candidate layout:
player_uid_relative(-204) = Current Ability
player_uid_relative(-202) = Potential Ability
```

Validar em outros jogadores.

Não hardcodar o endereço absoluto `0x0FC...`.

O offset relativo é o que interessa.

---

## 5.3. Saviola no people_db.dat

```text
people_db UID offset = 0x03B71E4E

nation_internal_id = 187
marker              = 255
player_type_raw     = 1

candidate rating #1 = 150
candidate rating #2 = 150
candidate rating #3 = 125

database CA = 160
database PA = 180

unknown_before_year = 0
year_like           = 1900
unknown_before_uid  = 136524
unknown_reference   = 136255
```

Importante:

```text
database PA = 180
live/FMM PA = 179
```

Não assumir regra `database PA - 1`.

Descobrir por comparação com outros jogadores.

---

## 5.4. Zinedine Zidane

```text
Public UID = 8076

FMM/live:
CA = 185
PA = 192
```

O layout `UID-204 / UID-202` já foi observado funcionando também no teste vivo.

Usar Zidane como âncora adicional.

---

## 5.5. Rogério Ceni

```text
Public UID = 3300977
```

O layout vivo também foi testado e bate com os dados observados.

Usar como terceira âncora.

---

## 5.6. Outros UIDs úteis

```text
Sávio          = 104318
Fred           = 321081
Rogério Ceni   = 3300977
Zinedine Zidane= 8076
Javier Saviola = 3100367
```

---

# 6. Nation internal IDs já observados

Existem namespaces diferentes para UID público e identificador interno.

Observados:

```text
Brasil   nation_internal_id = 189
França   nation_internal_id = 143
Espanha  nation_internal_id = 170
Argentina candidate         = 187
```

Public UIDs conhecidos:

```text
Brasil = 1651
França = 769
```

Não misturar os namespaces.

---

# 7. Club mapping já conhecido

Estrutura do `client_db` observada para clubes:

```text
[field_a u32]
[field_b u32]
[00]
[nation_internal_id u32]
```

Exemplos:

```text
São Paulo
public UID = 337
field_a = 212
field_b = 336
nation_internal_id = 189

Lyon
public UID = 865
field_a = 589
field_b = 864
nation_internal_id = 143

Real Madrid
public UID = 1736
field_a = 1313
field_b = 1733
nation_internal_id = 170

Zaragoza
public UID = 1749
field_a = 1324
field_b = 1746
nation_internal_id = 170
```

Não assumir fórmula entre `club_uid`, `field_a` e `field_b`.

---

# 8. Player history já decodificado

Não refazer isto.

Arquivos:

```text
pl_hist_index.dat
pl_hist_id.dat
pl_hist_dt.dat
```

Estrutura confirmada de cada registro em `pl_hist_dt.dat`:

```text
+0x00 u16 year
+0x02 u8  is_loan
+0x03 u8  appearances
+0x04 u8  goals
+0x05 u32 outgoing_transfer_fee_raw
+0x09 u32 club_uid
+0x0D u32 next_relative_offset
```

Usar os módulos/scripts existentes.

---

# 9. Estratégia de investigação

## Fase A — identificar o verdadeiro player object em RAM

Para cada jogador:

1. localizar todas as ocorrências de `public UID` na RAM do `fm.exe`;
2. testar `UID-204` como CA;
3. testar `UID-202` como PA;
4. comparar com FMM;
5. atribuir score ao candidato;
6. escolher o player object mais provável.

Não confiar simplesmente na primeira ocorrência do UID.

---

## Fase B — reconstruir Personal Info em RAM

Para o objeto selecionado:

Procurar ao redor do UID por representações:

```text
u8
u16 LE
u32 LE
signed values se necessário
bitfields
references/pointers
```

Começar pelos valores de alta entropia:

```text
Home Rep.    8198
Current Rep. 7998
World Rep.   5862
Fitness      4000
Match Exercise 7080
```

Esses valores são melhores marcadores que `20`, `12`, `15` etc.

Depois identificar offsets menores por correlação estrutural.

---

## Fase C — alteração controlada em lote

Criar ferramentas para snapshot/diff.

Sempre alterar apenas um campo por experimento.

Exemplos:

```text
CA 160 -> 161
PA 179 -> 178
Height 168 -> 169
Weight 61 -> 62
Home Rep. 8198 -> 8197
Current Rep. 7998 -> 7997
World Rep. 5862 -> 5861
Adaptability 12 -> 13
```

Automatizar a análise dos diffs.

Para cada alteração produzir:

```text
field
old
new
absolute address
relative to player UID
byte width
old bytes
new bytes
other changed bytes
confidence
```

---

# 10. Atributos

Para reconstruir os 79 campos:

1. capturar valores atuais do FMM;
2. capturar RAM;
3. alterar um atributo raro por vez;
4. produzir diff;
5. associar offset;
6. verificar em outros jogadores;
7. reconstruir sequência completa.

Não assumir que todos são `u8`, embora seja provável.

Não assumir que estão contíguos sem verificar.

---

# 11. Preferred Moves

Investigar se são:

```text
bitmask
u32 flags
u64 flags
array de IDs
array de bytes
lista dinâmica
```

Procedimento:

1. jogador sem determinado move;
2. snapshot;
3. ativar 1 preferred move pelo FMM;
4. snapshot;
5. diff;
6. repetir para moves distantes na lista;
7. identificar padrão.

Produzir mapa:

```text
move_name
index_from_FMM_txt
storage_type
byte_offset
bit
confidence
```

---

# 12. Contract Info

Depois que player object estiver confirmado, usar FMM para alterar um campo por vez:

```text
Wages
Started
Expires
Squad Status
Transfer
Loan
Unhappy
Happiness
Squad Number
Appearance bonus
Goal bonus
Assist bonus
Clean Sheet bonus
Minimum Release
Agreed Price
```

Não procurar datas por ano literal antes de observar a alteração controlada.

O diff do FMM deve determinar a codificação.

Especialmente para:

```text
Started
Expires
```

fazer alteração de apenas 1 dia e analisar bytes alterados.

Exemplo ideal:

```text
30/06/2007 -> 01/07/2007
```

Isso permite descobrir o formato de data sem adivinhar.

---

# 13. Relação RAM ↔ database

Depois de mapear os campos vivos, procurar correspondência em:

```text
people_db.dat
server_db.dat
client_db.dat
```

Usar jogadores âncora.

Não exigir que os valores sejam idênticos.

Classificar relações possíveis:

```text
DIRECT
SCALED
ENUM
REFERENCE
DERIVED
RUNTIME_MUTATED
UNKNOWN
```

Exemplo conhecido:

```text
Saviola:
people_db PA = 180
live PA      = 179

=> não classificar como DIRECT ainda
```

---

# 14. Scripts existentes

Antes de criar novos scripts, listar e ler os existentes.

Há trabalho anterior para:

```text
lang_db
entity_mapping
server_db
player_history
people_db
live_player_memory
inspect_player_core
inspect_live_player_layout
club mapping
history mapping
```

Reutilizar módulos existentes.

Não duplicar parser já implementado.

---

# 15. Segurança

Não modificar os `.dat` originais durante investigação.

Não sobrescrever:

```text
people_db.dat
server_db.dat
client_db.dat
lang_db.dat
fm.exe
```

Para testes:

- modificar apenas RAM via FMM;
- ou cópias em `workspace/`;
- ou patches reversíveis com backup/hash.

Não distribuir arquivos proprietários do jogo.

---

# 16. Output esperado do Codex

Criar diretório:

```text
reverse/fmm/
```

ou reutilizar um diretório equivalente existente.

Produzir ao final:

```text
reverse/fmm/FMM_SCHEMA.md
reverse/fmm/player_live_layout.json
reverse/fmm/player_live_layout.csv
reverse/fmm/contract_live_layout.json
reverse/fmm/playing_attributes_layout.json
reverse/fmm/preferred_moves_layout.json
reverse/fmm/club_live_layout.json
reverse/fmm/nation_live_layout.json
reverse/fmm/unresolved_fields.md
```

Também criar scripts reutilizáveis em:

```text
scripts/
```

Exemplos desejáveis:

```text
scan_live_player.py
diff_live_field.py
map_fmm_personal_info.py
map_fmm_playing_attributes.py
map_fmm_contract.py
map_fmm_preferred_moves.py
crosscheck_live_vs_database.py
```

Os nomes podem mudar se houver arquitetura melhor.

---

# 17. Estrutura obrigatória do relatório final

## Resumo

```text
Campos confirmados:
Campos high confidence:
Campos unresolved:
Hipóteses rejeitadas:
```

## Player object

Tabela:

| Campo | Offset relativo ao UID | Tipo | Evidência | Confiança |
|---|---:|---|---|---|
| Current Ability | -204 | ? | Saviola 160→161 + cross-check | CONFIRMED |
| Potential Ability | -202 | ? | Saviola 179→178 + cross-check | CONFIRMED |

Não preencher tipos sem prova.

---

## Personal Info

Tabela de todos os campos do FMM.

---

## Playing attributes

Uma linha para cada campo do `[Playing Attrib]`.

---

## Contract

Uma linha para cada campo do `[Contract Info]`.

---

## Preferred Moves

Uma linha por preferred move.

---

## Club / Nation

Mapear o máximo possível.

---

## Database relation

Para cada campo relevante:

| Campo | RAM | people_db/server_db/client_db | Relação | Confiança |
|---|---|---|---|---|

---

# 18. Ranking de matches

Quando houver vários possíveis matches, não escolher silenciosamente apenas um.

Gerar os melhores candidatos.

Formato:

```text
FIELD: Home Reputation
KNOWN VALUE: 8198

Candidate #1
  address: ...
  rel_uid: ...
  type: u16
  players matched: 3/3
  controlled diff: yes/no
  score: 98
  confidence: HIGH

Candidate #2
  ...
```

Score recomendado:

```text
+100 alteração controlada exata
+50 mesmo offset em outro jogador
+50 terceiro jogador
+30 valor exato de alta entropia
+20 coerência com ordem do FMM.txt
+20 tamanho/tipo consistente
-50 conflito com jogador conhecido
-100 alteração controlada contraditória
```

Pode melhorar a fórmula, mas documentar.

---

# 19. Não parar cedo

Não retornar após mapear apenas CA/PA.

Prosseguir de forma autônoma por:

```text
Personal Info
Playing attributes
Contract
Preferred Moves
Club
Nation
```

até:

- acabar a evidência disponível;
- ou uma próxima etapa exigir interação manual no FMM.

Se precisar de interação manual, agrupar pedidos.

Não pedir:

```text
“mude um campo e me responda”
```

dez vezes.

Pedir um lote como:

```text
Faça estes 8 testes controlados:
1. Height 168→169
2. Weight 61→62
3. Home Rep 8198→8197
...
```

e fornecer comandos/scripts para capturar tudo.

---

# 20. Regra crítica sobre conhecimento de FM06

Quando o significado funcional de algum campo do Football Manager estiver ambíguo, **não inferir sozinho pelo nome ou por futebol moderno**.

Registrar a dúvida no relatório.

O usuário conhece FM06 profundamente e pode esclarecer a semântica da interface.

Perguntar somente quando a ambiguidade realmente bloquear o mapeamento técnico.

---

# 21. Critério de sucesso

O sprint será considerado bem-sucedido quando houver um schema suficiente para criar uma API como:

```python
player = live.player(3100367)

player.current_ability
player.potential_ability
player.home_reputation
player.current_reputation
player.world_reputation

player.height
player.weight
player.nationality

player.attributes.crossing
player.attributes.dribbling
player.attributes.finishing

player.contract.club
player.contract.wages
player.contract.started
player.contract.expires

player.preferred_moves
```

e, posteriormente:

```python
database_player = db.player(3100367)

database_player.current_ability
database_player.potential_ability
database_player.attributes
database_player.contract
```

com relação documentada entre o valor inicial da database e o valor vivo criado pelo engine.

---

# 22. Primeira execução

Comece imediatamente com:

1. inventário do repositório;
2. leitura do `FMM.txt`;
3. leitura dos scripts de RAM existentes;
4. validação de `UID-204` e `UID-202`;
5. geração automática de candidatos para todos os campos de `Personal Info`;
6. relatório preliminar;
7. preparação dos experimentos controlados em lote necessários para resolver ambiguidades.

Não recomeçar a engenharia reversa do zero.

Aproveitar tudo que já existe.
