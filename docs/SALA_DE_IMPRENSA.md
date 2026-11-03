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
- `form`: as 5 últimas notas inteiras do jogo (`Pfrm`). Hipótese: a primeira é a mais recente.
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

### 8.8 Gerar notícia de repercussão

Depois da resposta, montar uma consequência com:

- manchete;
- trecho da declaração;
- reação do jogador;
- reação do elenco;
- credibilidade do treinador;
- possível follow-up.

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

