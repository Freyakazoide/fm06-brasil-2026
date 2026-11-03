# Sala de Imprensa — estado atual e integração futura

## 1. O que esta entrega já faz

A Sala de Imprensa atual é uma demonstração completa e deliberadamente independente do FM06.
Ela não abre o processo do jogo, não lê memória e não grava no save.

Está implementado:

- interface visual no padrão azul/amarelo da Central de Desenvolvimento;
- agenda de entrevistas com busca e filtro por meio;
- coletiva pública com jornalista, pergunta, contexto e oito respostas;
- conversa individual com o jogador, também com oito abordagens;
- reação simulada do jogador, elenco, torcida, diretoria, imprensa e treinamento;
- personalidade do jogador influenciando a reação simulada;
- banco editorial pesquisável por categoria, gatilho, pergunta e tag;
- 54 situações editoriais;
- 162 perguntas iniciais;
- 8 intenções para cada situação, totalizando 432 combinações;
- 23 veículos nacionais e regionais carregados de `data/brasil/midia_2026.csv`;
- 46 jornalistas fictícios, dois por veículo;
- retrato pixelado determinístico para cada jornalista;
- identidade visual local para todos os veículos, sem dependência de internet.

## 2. Como executar agora

Na raiz do projeto:

```powershell
python tools\imprensa\servidor.py
```

Para escolher uma porta e não abrir o navegador automaticamente:

```powershell
python tools\imprensa\servidor.py --porta 8629 --sem-navegador
```

Depois, abrir `http://127.0.0.1:8629`.

O FM06 não precisa estar aberto. Toda escolha existe apenas na memória da página e desaparece ao
recarregar. Isso é intencional nesta fase.

## 3. Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `tools/imprensa/pagina.html` | Estrutura base da aplicação. |
| `tools/imprensa/imprensa.css` | Design, responsividade, painéis e estados visuais. |
| `tools/imprensa/imprensa.js` | Navegação, geração de retratos, simulação e renderização. |
| `tools/imprensa/banco.py` | Situações, perguntas, intenções, follow-ups e efeitos-base. |
| `tools/imprensa/veiculos.py` | Leitura do CSV, identidade dos veículos e jornalistas fictícios. |
| `tools/imprensa/demo.py` | Clube, jogadores, agenda e estatísticas fictícias. |
| `tools/imprensa/servidor.py` | Servidor HTTP local, sempre em modo demonstração. |
| `tests/test_imprensa.py` | Validação do tamanho, consistência e independência do banco. |

## 4. Modelo editorial

Cada situação contém:

```json
{
  "id": "poor_streak",
  "category": "Desempenho",
  "title": "Sequência abaixo do esperado",
  "pack": "performance",
  "trigger": "três notas abaixo de 6,5 em cinco jogos",
  "questions": ["...", "...", "..."],
  "tags": ["sequência", "confiança", "pressão"],
  "urgency": "alta",
  "subject": "jogador",
  "public": true
}
```

Cada intenção contém:

```json
{
  "id": "protect",
  "label": "Proteger o jogador",
  "tone": "acolhedora",
  "text": "{player} não será reduzido a um lance...",
  "follow_up": "Então a vaga dele não está em discussão?",
  "effects": {
    "player": 2,
    "squad": 1,
    "fans": 0,
    "board": 0,
    "media": -1,
    "training": 1
  },
  "risk": "baixo"
}
```

Os números atuais servem apenas para demonstrar diferenças entre respostas. Eles ainda não são as
regras finais do jogo.

## 5. Retratos dos entrevistadores

Cada jornalista possui um `seed` estável calculado a partir de veículo e índice. O JavaScript usa
esse número para escolher:

- tom de pele;
- cabelo e corte;
- olhos;
- barba ou bigode;
- óculos;
- paletó;
- gravata.

O mesmo `seed` sempre gera o mesmo rosto. Portanto, o jogador reconhece um setorista recorrente sem
que seja necessário armazenar uma imagem para cada jornalista.

Na integração definitiva, o identificador do jornalista deve ser persistido no estado da carreira.
O retrato continuará sendo gerado localmente a partir dele.

## 6. Identidades dos veículos

O endpoint `/logos/<slug>.svg` gera uma identidade vetorial local com nome, sigla e cores próprias.
Ela mantém a aplicação rápida e utilizável sem internet.

Essas peças são wordmarks inspiradas nas marcas, não reproduções oficiais perfeitas. Para substituir
por arquivos aprovados posteriormente, preservar o caminho lógico:

```text
data/brasil/telas/imprensa/assets/veiculos/<slug>.png
```

O campo `logo` devolvido por `veiculos.py` pode então apontar para o arquivo estático sem alterar o
HTML ou os componentes.

## 7. Contrato que o jogo deverá fornecer

A futura ponte com o FM06 deverá construir um objeto compatível com este formato:

```json
{
  "event_id": "save-301306-2026-08-04-poor_streak-2000007988",
  "date": "2026-08-04",
  "club": {"uid": 301306, "name": "Figueirense"},
  "competition": {"uid": 123, "name": "Campeonato Brasileiro"},
  "rival": {"uid": 302, "name": "Avaí"},
  "situation_id": "poor_streak",
  "player": {
    "uid": 2000007988,
    "name": "Afonso Guedes",
    "short_name": "Guedes",
    "age": 16,
    "position": "Meia central",
    "morale": 11,
    "form": [6.1, 6.3, 5.9, 6.6, 6.2],
    "stats": {"matches": 13, "goals": 2, "assists": 4, "rating": 6.34, "minutes": 738},
    "personality": {
      "ambition": 16,
      "professionalism": 14,
      "pressure": 8,
      "temperament": 12,
      "loyalty": 15,
      "controversy": 5
    }
  },
  "outlet_id": "ge",
  "journalist_id": "ge-1"
}
```

Não colocar endereços de memória ou regras de leitura na interface. A ponte deve normalizar os dados
e entregar somente esse contrato.

## 8. Etapas de integração com o FM06

### 8.1 Identificar a notícia aberta

É necessário mapear no executável o evento usado quando o jogador abre uma notícia. O patch precisa
capturar, no mínimo:

- identificador ou tipo da notícia;
- clube relacionado;
- pessoa relacionada, quando houver;
- data do jogo;
- competição e adversário, quando houver;
- contador de abertura para não processar duas vezes.

A Central já prova um padrão útil: um patch nativo registra a seção aberta e um servidor externo
observa a telemetria. A Sala de Imprensa pode seguir o mesmo desenho, mas com uma estrutura própria.

**Estado em 03/11 (investigação):** a notícia não abre tela nova. A caixa de entrada é a seção `Pnws`
(`data/screens/news.xml`: tabela `indx` com seleção de linhas e o texto embaixo), então o desvio de
abertura da Central (que anota a seção de cada tela) não diz qual notícia foi lida. Caminho escolhido,
sem patch: mapear a caixa de entrada do humano na memória e o observador externo notar quando uma
notícia passa de não lida para lida. Pistas no exe: entrega `0x753E10(notícia, clube, 0)` ao
gerenciador `0x0132AAD0`, que percorre a lista do clube (`+0x64`, quantidade `+0x6C`) e chama
`0x753C10` por destinatário. Próximo: achar na memória o texto de uma manchete conhecida e subir pelos
ponteiros até a lista e o campo "lida".

**03/11, caixa de entrada mapeada (memória, só leitura):** as notícias são classes com RTTI
`..._NEWS`/`..._NEWS_ITEM` (272 no exe, lista em `workspace/news_vtables.json`). A caixa do humano é o
único `NEWS_ITEM_ARRAY` (vtable `0x010F6DD4`) e fica em `[humano - 0x1E0]`: `+4` dados, `+8` quantidade
(75 no save). Cada notícia: `+0x14` data (u16 dia, u16 ano do motor; `0x07D600CB` = 23/07), `+0x18`
marcas (byte), `+0x1C` número de série crescente, e a pessoa num campo próprio da classe (Jhonnathan em
`MEDIA_PLAYER_FORM_NEWS+0x34`, Leonan em `RED_CARD_BAN_NEWS+0x5C`, João Ferro e Mailson em
`PHYSIO_REPORT_NEWS_ITEM+0x2C`). Manchetes conferidas com a tela: "Jhonnathan acusado de displicência",
"Leonan suspenso por um jogo", "Gustagol informa sobre Mailson/João Ferro". Ferramenta:
`tools/re/caixa_entrada.py` (foto/diff) para achar o bit de "lida".

**03/11, notícia lida -> pauta (feito, sem patch):** a marca de lida é o bit 0 do byte `+0x22` da
notícia (abrir "Jhonnathan acusado de displicência" mudou só esse byte, `0x10` -> `0x11`; as outras
74 ficaram iguais). `tools/imprensa/noticias.py` lê a caixa (série, classe, data, lida, jogador = 1º
ponteiro para jogador na notícia) e traduz a classe em situação do banco (`SITUATION`; ex.:
`MEDIA_PLAYER_FORM_NEWS` -> sequência ruim ou grande atuação pela nota do último jogo,
`RED_CARD_BAN_NEWS` -> cartão vermelho, `PHYSIO_REPORT_NEWS_ITEM` -> lesão, `CONTRACT_EXPIRES_SOON_NEWS`
-> renovação). No `--jogo`, o observador do servidor lê a caixa a cada 2 s; a notícia que passa a lida
entra à frente da agenda como pauta "agora" (motivo "notícia lida no jogo (dd/mm): ..."), a rota
`/evento` conta essas notícias e a página se atualiza sozinha (ou o observador abre o navegador).
Notícia de jogador de outro clube não vira pauta. As §8.2 e §8.3 (telemetria no exe) deixam de ser
necessárias para isso.
**Conferido pelo usuário (03/11):** ao abrir "Gustagol informa sobre Mailson" no jogo, a Sala trocou
sozinha para a pauta "Nova lesão" (SporTV, agora), com Mailson e o motivo "notícia lida no jogo
(22/07): relatório do fisioterapeuta".

### 8.2 Criar telemetria reservada

Reservar no bloco `.fm26` campos equivalentes a:

```text
press.open_count
press.news_uid
press.news_type
press.club_uid
press.person_uid
press.competition_uid
press.event_flags
```

O patch apenas registra o evento. Não deve abrir navegador nem calcular reações dentro do loop da
interface do jogo.

### 8.3 Criar o observador externo

O futuro `tools/imprensa/integracao.py` deverá:

1. observar `press.open_count`;
2. ler o contexto quando o contador mudar;
3. converter o tipo da notícia em `situation_id`;
4. consultar o leitor de jogadores;
5. escolher veículo e jornalista;
6. abrir `/entrevista?event=<event_id>`;
7. impedir duplicação com um histórico local.

### 8.4 Selecionar veículo e jornalista

Regras recomendadas:

1. veículo cujo campo `clubes` contenha o clube;
2. veículo da mesma cidade;
3. veículo nacional;
4. peso por meio conforme a situação;
5. jornalista já associado àquele clube, quando possível.

Exemplos:

- rumor de mercado: sites e colunistas recebem peso maior;
- pós-jogo imediato: TV e rádio;
- crise regional ou clássico: imprensa da cidade;
- recorde histórico: revista ou jornal.

### 8.5 Ler jogadores e personalidade

Reutilizar os dados já descobertos pela Central:

- moral;
- forma recente;
- estatísticas oficiais;
- contrato;
- personalidade;
- posição;
- idade;
- time atual.

O leitor da Sala de Imprensa deve importar uma camada estável, não duplicar offsets. O ideal é extrair
um módulo comum, por exemplo `tools/fm06_runtime/jogadores.py`, usado tanto pela Central quanto pela
Imprensa.

**Estado em 03/11 — feito (só leitura):** `tools/imprensa/ponte.py` monta o contrato da §7 a partir do
leitor da Central (`leitor.jovens(max_age=99)`, elenco inteiro do clube humano), sem repetir offsets.
`python tools\imprensa\servidor.py --jogo` usa o FM06 aberto (guarda a leitura por 2 minutos; com o
jogo fechado, volta à demonstração e avisa no selo do topo). Mapeamento:

- `stats`: jogos oficiais da temporada; sem nenhum, os **não oficiais** (Sub-20, amistosos), com
  `unofficial: true`. Minutos oficiais vêm do registro Global do objeto de estatísticas.
- `form`: as 5 últimas notas inteiras do jogo (`Pfrm`), da mais antiga para a mais recente (03/11:
  "Jhonnathan acusado de displicência" saiu com a forma 7, 7, 7, 6, 5).
- `personality`: os traços do PData (1 a 20); `position`: nome da função do adjunto.

Gatilhos reais (um assunto por jogador, até 7, ordenados por peso): `match_star` (nota ≥ 8 no último
jogo), `senior_debut` (≤ 19 anos, 1 a 3 jogos oficiais), `poor_streak` (3 notas < 6,5 e média < 6,3 em
5), `renewal` (contrato acaba em até 180 dias), `poor_match` (nota ≤ 5), `mental_pressure` (moral ≤ 7),
`youth_comparison` (≤ 19 anos, potencial ≥ 4 estrelas), `loan` (≥ 18 anos, sem jogos oficiais, fora do
Principal), `red_card` (vermelho na temporada), `stagnation` (≤ 21 anos e personalidade com chance
baixa). Sem fonte ainda: clássico, lesão, vestiário, mercado, treino e próximo adversário.

Veículo (§8.4): o que cobre o clube; se não houver (Florianópolis não tem veículo na planilha), um
nacional do meio preferido da situação. Jornalista e veículo são escolhidos por hash da data, situação
e jogador: a mesma pauta no mesmo dia sempre traz o mesmo repórter. Testes em
`tests/test_imprensa_ponte.py`.

### 8.6 Persistir o estado externo

Antes de qualquer escrita no jogo, guardar em arquivo local por carreira:

```text
workspace/imprensa/<save_id>/estado.json
workspace/imprensa/<save_id>/eventos.jsonl
```

O estado deve conter:

- entrevistas já respondidas;
- relação treinador-jogador;
- credibilidade com cada veículo;
- promessas feitas;
- modificadores temporários de treino;
- respostas anteriores para detectar contradições;
- última aparição de cada jornalista;
- cooldown de situações e perguntas.

O `eventos.jsonl` deve ser somente anexado e funcionar como auditoria e possibilidade de desfazer.

**03/11, feito (só arquivos externos):** `tools/imprensa/estado.py`. Carreira =
`<clube>-<uid do time>` (ex.: `figueirense-<uid>`); demo = `demo`. Cada pauta tem uma chave estável
(`noticia-<série>` para a notícia lida, ou `data:situação:jogador`). Na página, depois de escolher a
intenção, **Dar esta resposta** grava em `workspace/imprensa/<carreira>/eventos.jsonl` (só anexado) e
`estado.json` (respostas; somas de relação por jogador, resposta ao treino por jogador,
credibilidade por veículo, elenco, torcida e diretoria). Efeitos limitados a ±4 por resposta; uma
resposta por pauta. A pauta respondida fica marcada ("✓ respondida") e travada mesmo depois de
recarregar. Testes em `tests/test_imprensa_estado.py`. Ainda não: promessas, contradições, cooldown.

**03/11, agenda só com notícias reais (pedido do usuário):** as pautas inventadas pelos números
("Estreia no profissional", "Renovação"...) não eram notícias do jogo. No `--jogo`, a agenda agora é a
caixa de entrada: notícias dos últimos 14 dias que viram situação e são de jogador do clube (até 10,
uma por jogador), **lidas ou não** (as lidas antes de a Sala ligar também entram). A que acabou de ser
aberta no jogo fica como "agora"; o resto vai da mais nova à mais velha, com a data da notícia e o
status "lida no jogo"/"não lida no jogo". A chave da pauta é a série da notícia, então a resposta dada
continua marcada depois de reiniciar o servidor. Os gatilhos pelos números só entram se não houver
nenhuma notícia ("sugestão da assessoria").
Conferido pelo usuário (03/11): a agenda mostra só notícias reais do jogo.

### 8.7 Aplicar efeitos

Separar os efeitos em duas categorias.

**Estado do FM06:**

- moral, somente depois de validar o endereço e o intervalo;
- eventualmente relação com treinador, se o campo for mapeado com segurança.

**Estado externo:**

- confiança;
- pressão;
- relação detalhada;
- credibilidade;
- promessa;
- resposta ao treino;
- memória de entrevista.

Uma fala nunca deve aumentar diretamente Finalização, Técnica ou outro atributo. O efeito de treino
deve ser um multiplicador temporário e limitado:

```text
0.92 <= training_response <= 1.08
7 <= duration_days <= 21
```

Também limitar:

```text
abs(morale_delta_per_answer) <= 4
abs(cumulative_weekly_delta) <= 6
```

Antes de escrever, conferir:

- identidade do processo;
- identidade do save;
- data esperada;
- UID do jogador;
- valor antigo ainda igual ao lido;
- novo valor dentro do intervalo válido.

**03/11, moral no jogo (feito, a conferir no jogo):** `tools/imprensa/efeitos.py`. Ao dar a resposta
no `--jogo`, o servidor aplica o efeito "Jogador" da simulação na moral do FM06 (u8 em `UID-184`,
1 a 20; endereço CONFIRMED em `reverse/fmm/player_live_layout.json` e lido igual pelo leitor da
Central: Leonan, Jhonnathan e Mailson = 9 pelos dois caminhos). Travas: ±4 por resposta, ±6 por
semana do jogo por jogador (`efeitos.allowed`), valor final de 1 a 20, UID conferido e valor relido
logo antes de gravar, releitura depois. Cada mudança vai para `eventos.jsonl` (`tipo: moral`, antes e
depois) e para `estado.json` (`moral`). O botão mostra a prévia ("moral 9 → 11 no jogo") e o
cartão mostra o resultado. `--sem-efeitos` desliga. Ainda não: resposta ao treino no jogo, relação
treinador-jogador do FM06.
**Conferido (03/11):** 1ª tentativa sem efeito (bug: a condição do servidor lia uma marca que só
existe na resposta à página; corrigido). 2ª: resposta "Ouvir antes de julgar" ao Leonan (suspensão,
Jogador +2) gravou a moral **9 -> 11** no jogo (relida na memória depois: 11). Na ficha a palavra
continuou "OK": a escala tem faixas por palavra, e 12 é o valor de 18.475 dos ~35 mil jogadores (o
neutro). Falta mapear as faixas das palavras (Ruim/OK/Boa...) para a página mostrar a palavra.
**Conferido (03/11), faixas:** jogo reaberto sem salvar depois da resposta -> o save voltou com
moral 9 (a escrita vale só na memória; **para durar, é preciso salvar no jogo** depois de responder).
Teste de faixa (fora da Sala, `apply_morale` direto): Leonan 9 -> **15**, a ficha passou de "OK" para
**"Bom"** (conferido pelo usuário); devolvido para 9 em seguida (relido: 9). Pontos conhecidos:
9 = OK, 11 = OK, 15 = Bom. Depois 13 -> **Bom** e 12 -> **OK** (conferidos pelo usuário na ficha):
**"Bom" começa em 13**; o neutro 12 da maioria dos jogadores é o topo de "OK". Leonan devolvido para 9
(relido). Palavras abaixo de 9 e acima de 15 ainda não conferidas. A página mostra "OK (9) → Bom (13)"
(`moraleWord`/`moraleText` em `imprensa.js`) e, fora de 9..15, só o número.

### 8.8 Gerar notícia de repercussão

Depois da resposta, montar uma consequência com:

- manchete;
- trecho da declaração;
- reação do jogador;
- reação do elenco;
- credibilidade do treinador;
- possível follow-up.

**03/11, repercussão na Sala (feito):** `tools/imprensa/repercussao.py`. Ao gravar a resposta, o
servidor monta a matéria do veículo que perguntou: manchete (por tom: apoio, cobrança, tensão,
neutro; escolha fixa pela chave da pauta), trecho da declaração já preenchido, reação do jogador
(efeito "Jogador" + moral no jogo, se mudou), do elenco, credibilidade com o veículo (soma corrente
de `credibilidade`), torcida/diretoria quando mexem, e o follow-up (`status: pendente`). Fica em
`estado.json` (`respostas[chave].repercussao`) e em `eventos.jsonl` (`tipo: repercussao`). Respostas
anteriores ganham a matéria na 1ª leitura de `/dados` (a credibilidade delas usa a soma do momento).
Na página, o cartão de jornal substitui a "manchete provável" depois da resposta. Conferido na
página: Leonan / ESPN Brasil. Testes: `tests/test_imprensa_repercussao.py`. Ainda não: o follow-up
virar pauta nova (§10: um por assunto comum) e a notícia na caixa de entrada do FM06.

**03/11, tirar notícia da caixa do jogo (deu certo):** `tools/re/caixa_remover.py`. O
NEWS_ITEM_ARRAY é uma lista comum: `+0` vtable, `+4` dados, `+8` quantidade, `+0xC` capacidade
(75/100). Teste: remover a 963 (MEDIA_COMMENT_NEWS_ITEM, 23/07, lida; posição 72, objeto 0x107AFD48)
= deslocar os ponteiros seguintes e baixar a quantidade (75 -> 74); o objeto não é liberado.
Resultado (conferido pelo usuário): sumiu da caixa (23/07 com 2 notícias), jogo normal, **salvo em
save novo, fechado, reaberto: continua fora** (lista relida: 74, sem a 963). Em aberto: a tela diz
"74 de 75 mensagens exibidas, 41 não lidas", mas a lista tem 74 e 40 não lidas; o único 74 perto do
humano é a própria quantidade (`humano-0x1D8`). Hipótese: o 75º/41º é uma mensagem de outra lista
(não um contador velho). Conferir no save original da carreira (que ainda tem a 963): se ele mostrar
"75 de 76", é outra lista.
**Conferido depois (03/11):** o save original mostra "75 mensagens exibidas" (sem "de"): não há outra
lista; o "de 75" deve ser a tela daquela sessão lembrando o total antigo (perto do humano não há outro
75). Achado: **`humano-0x1E4` (caixa - 4) é o contador de não lidas** — com 83 notícias e 7 não lidas
valia 7; o usuário abriu "Figueirense enfrenta Ituano" (975, PRE_MATCH_ODDS_NEWS) e foi a 6, junto
com o bit de lida. `caixa_remover.py` agora baixa/sobe esse contador ao tirar/devolver notícia não
lida. 8 notícias de 25-26/07 (odds, transferência, resumo, melhor em campo, fase das equipes x2,
diretoria): nenhuma MEDIA_* nem do elenco do Figueirense; as de imprensa são raras (3 em duas semanas).

Há código de criação de notícia em `src/fm06patch/fornada.py` que pode servir como referência. Não
reutilizar cegamente: primeiro confirmar o tipo do objeto, ciclo de vida e campos exigidos pela caixa
de entrada.

## 9. Entrevistas dos clubes controlados pela IA

Executar em um tick diário ou semanal, nunca a cada quadro.

Para cada clube:

1. detectar somente eventos relevantes;
2. derivar o perfil do treinador;
3. escolher uma intenção ponderada;
4. aplicar efeitos limitados;
5. registrar a declaração;
6. criar notícia apenas quando houver interesse para o jogador humano.

Perfis iniciais:

```text
protetor
sereno
exigente
pragmático
provocador
instável
```

O treinador da IA deve usar a mesma estrutura de resposta da interface. Assim o mundo não possui um
sistema simplificado separado do jogador humano.

## 10. Regras editoriais recomendadas

- não repetir a mesma situação em 15 dias, salvo reincidência explícita;
- não repetir a mesma pergunta em 30 dias para o mesmo treinador;
- permitir no máximo um follow-up por assunto comum e dois em crise;
- não transformar uma única nota ruim de jovem em crise pública;
- dar mais peso a sequência do que a um jogo isolado;
- considerar minutos jogados antes de avaliar nota;
- preservar privacidade em saúde e assuntos pessoais;
- registrar promessas objetivas, como minutos ou permanência;
- cobrar contradições somente quando houver declaração anterior registrada;
- veículos regionais devem aparecer mais em clássicos e assuntos locais;
- perguntas agressivas precisam de um gatilho real, não apenas aleatoriedade.

## 11. Critérios de pronto para a integração

A parte visual pode ser considerada pronta para receber dados reais quando:

- os IDs de situação permanecerem estáveis;
- o contrato do evento estiver versionado;
- a seleção de veículo for determinística e testável;
- o histórico externo distinguir carreiras diferentes;
- a escrita de moral tiver teste de intervalo e valor antigo;
- houver log de todas as alterações;
- uma falha de integração nunca impedir o FM06 de continuar rodando;
- o modo demonstração continuar disponível sem o jogo aberto.

