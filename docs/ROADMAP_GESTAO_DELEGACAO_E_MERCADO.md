# Roadmap — Gestão, delegação, escalação e mercado inteligente no FM06

> Documento de viabilidade. Nesta etapa, **nenhuma funcionalidade foi implementada**.
> O objetivo é registrar o que já sabemos, o que ainda precisa ser descoberto e uma ordem segura
> para desenvolver os sistemas sem transformar o FM06 em vários remendos independentes.

## 1. Visão do projeto

O projeto reúne três frentes que, por baixo da interface, precisam usar a mesma leitura do elenco:

1. **gestão rápida do elenco**: escalações automáticas, banco, rotação, comparação e planejamento;
2. **responsabilidades da comissão**: o usuário decide, recebe sugestão ou delega a execução;
3. **mercado inteligente**: clubes contratam e emprestam mais quando precisam, mas só trazem atletas
   que tenham função, espaço e custo coerentes.

A Central de Desenvolvimento já planejada é a quarta saída desse mesmo sistema. Ela não deve possuir
uma lógica isolada: suas recomendações de posição, treino, minutos e empréstimo devem vir do mesmo
mapa de elenco usado pelo adjunto, pela escalação automática e pela IA de transferências.

```text
dados do clube + elenco + calendário + finanças + comissão
                         │
                         ▼
              fotografia do elenco no dia
                         │
                         ▼
      mapa por posição, função, hierarquia e necessidade
          │              │               │
          ▼              ▼               ▼
     escalação       responsabilidades   mercado/ empréstimos
          │              │               │
          └──────────────┴───────┬───────┘
                                 ▼
                  Central + reunião semanal
```

Esse núcleo comum é a principal decisão de arquitetura deste roadmap.

## 2. O que já está comprovado no projeto e no FM06

### 2.1 Estrutura atual do mod

- o mod já altera o `fm.exe` 6.0.2 por patches e stubs gerados em Python;
- o banco de 2026 já contém elencos, comissão, finanças, reputação e orçamento de transferências;
- as janelas brasileiras de 2026 já possuem patch em `src/fm06patch/transferencias.py`;
- a Central de Desenvolvimento já existe no menu como `tcdv` e usa
  `person_search_panel` em `data/screens/team.xml`;
- `Pest`, `Pesp` e `Pmcl` já são propriedades novas respondidas pelo executável em
  `src/fm06patch/centro.py`;
- o mapa vivo dos contratos confirmou, entre outros campos, salário, datas, status no elenco,
  indicação de transferência/empréstimo, felicidade e número da camisa. A referência está em
  `reverse/fmm/FMM_SCHEMA.md`;
- `docs/reversing/transfer-ai.md` está vazio. Portanto, **a rotina de decisão de mercado da IA ainda
  não está mapeada** e nenhum endereço deve ser inventado antes da etapa de rastreamento.

### 2.2 Recursos nativos que podem ser reaproveitados

| Recurso | Evidência no FM06 | Utilidade futura |
|---|---|---|
| pedir ao adjunto uma escalação | `data/panels/team actions.xml`, ação `aatp` | ponto de entrada da escalação automática |
| limpar escalação | mesmo arquivo, ação `clts` | recomposição completa, se confirmada pelo usuário |
| escalações salvas | ação dinâmica `tsel` e `team selection list.xml` | presets Principal, Copa, Reservas e Jovens |
| preservar seleção atual | `go on holiday.xml`, caixa `usts` | prova de que a IA já sabe respeitar parte da seleção |
| tabela da convocação | `team selection.xml`, tabela `sqtb` | XI, banco e arrastar/soltar jogadores |
| escalações do principal/reserva/jovens | `screens/team.xml`: `0spn`, `1spn`, `2spn` | delegação separada por equipe |
| comparação de atletas | painel/classe nativa de comparação de pessoas | evita recriar comparação do zero |
| relatório do adjunto | `team actions.xml`, ação `gtrp`; `non player team report.xml` | carências e reunião semanal |
| autoatribuir treinadores | `training coaches list.xml`, evento `auto` | primeira responsabilidade executável de baixo risco |
| amistosos | `fixtures.xml`, ações `arrf`/`cafr`; `friendly.xml` | delegação da pré-temporada |
| contratos | `screens/contract offer.xml` e painéis de contrato | renovar/contratar staff por rotinas nativas |

Esses IDs mostram que a interface e parte do comportamento já existem. Eles **não provam** qual
função interna atende cada evento. Cada ação ainda precisa ser seguida no debugger antes de um hook.

### 2.3 Limites do XML

XML pode:

- criar a entrada no menu;
- organizar caixas, tabelas, botões, textos e imagens;
- ligar um controle a um evento que a classe nativa já reconhece;
- substituir visualmente um painel da skin mãe.

XML não pode, sozinho:

- avaliar elenco, forma, fadiga ou encaixe tático;
- criar o significado de `Eu decido`, `Adjunto sugere` e `Adjunto executa`;
- negociar contratos ou amistosos em segundo plano;
- alterar a decisão de compra dos outros clubes;
- persistir novas responsabilidades no save;
- registrar uma nova classe de painel que o executável desconhece.

A tela de Responsabilidades completa exigirá um controlador reconhecido pelo executável. Um XML com
`class="responsibilities_panel"` não funcionará enquanto essa classe não existir. Para o primeiro
MVP, é mais seguro reaproveitar um painel/modal nativo e entregar sugestões pela caixa de entrada.

## 3. Princípios obrigatórios

1. **Nunca executar sem autorização.** Uma tarefa em `Eu decido` não pode ser alterada por nenhum
   ciclo automático.
2. **Sugestão é uma proposta, não uma mutação.** Deve mostrar motivo, custo, prazo e o botão de
   aceitar/recusar.
3. **Execução tem limites.** Orçamento, salário, idade, duração, quantidade e cargos protegidos são
   configuráveis.
4. **Toda decisão é explicável.** “Precisamos de lateral porque só há um atleta apto” é melhor que
   “pontuação 73”.
5. **Forma ajuda, mas não apaga o contexto.** Um atleta que rendeu com o humano não deve ser comprado
   por outro clube se não couber na tática, no orçamento ou na hierarquia do comprador.
6. **Não revelar PA/CA ao usuário.** A comissão apresenta opinião sujeita a erro, como já ocorre com
   `Pest`/`Pesp`.
7. **Reaproveitar rotinas nativas.** Primeiro localizar o que `aatp`, `usts`, `auto`, `arrf` e os
   contratos já fazem; só escrever algoritmos novos onde faltar comportamento.
8. **Sem spam diário.** Planejamento é periódico; urgências são eventos excepcionais.
9. **IA joga pelas mesmas restrições.** Janelas, caixa, folha, inscrições e tamanho de elenco também
   limitam os clubes controlados pelo computador.
10. **Todo patch precisa falhar com segurança.** Se uma leitura estiver inválida, o jogo usa a rotina
    original e não toma a decisão nova.

## 4. Arquitetura comum proposta

### 4.1 Fotografia do elenco (`SquadSnapshot`)

Uma estrutura somente de leitura, refeita no máximo uma vez por dia do jogo ou quando houver evento
relevante. Para cada atleta, deve reunir:

- clube dono e equipe atual;
- principal, reserva, jovens ou emprestado;
- posições e adequação a cada setor;
- idade, status no elenco e contrato;
- condição, lesão, suspensão e disponibilidade;
- partidas, titularidades, minutos e nota recente, quando esses campos forem localizados;
- avaliação conhecida de habilidade/potencial;
- salário, valor e situação de transferência/empréstimo;
- registro na competição, quando necessário.

Dados ainda não localizados não devem virar zero. Devem aparecer como `desconhecido`, com o
respectivo critério temporariamente desativado.

### 4.2 Mapa do elenco (`DepthChart`)

Para cada posição/função da tática, classificar:

- titular provável;
- primeira e segunda cobertura;
- jovem em transição;
- improvisação aceitável;
- excedente;
- carência imediata;
- carência futura por idade ou fim de contrato.

O mapa não pode apenas colocar o jogador em sua “melhor posição”. Um volante capaz de ser o único
reserva da zaga não está livre para ser contado duas vezes. É necessário distribuir o elenco pelas
vagas e medir a cobertura depois da distribuição.

### 4.3 Proposta de decisão (`DecisionProposal`)

Toda ação planejada usa o mesmo envelope:

```text
tipo da tarefa
alvo (jogador, funcionário, adversário ou escalação)
responsável que propôs
motivos e evidências
custo e impacto esperado
prazo de validade
nível de risco
ação reversível ou irreversível
estado: aguardando / aceita / recusada / executada / falhou
```

### 4.4 Política de responsabilidade (`ResponsibilityPolicy`)

Cada tarefa tem um modo:

| Modo | Comportamento |
|---|---|
| **Eu decido** | o jogo só alerta; nenhuma proposta é enviada automaticamente e nada é executado |
| **Adjunto sugere** | a comissão cria uma proposta na caixa de entrada; o usuário confirma ou recusa |
| **Adjunto executa** | a comissão executa dentro dos limites e envia um resumo posterior |

O modo é aplicado **depois** de a proposta ser calculada. Assim, o mesmo algoritmo pode servir ao
humano, ao adjunto e aos outros clubes sem duplicação.

### 4.5 Executor e auditoria

O executor deve chamar as rotinas nativas do jogo para efetivar escalação, contrato, amistoso ou
empréstimo. Não é seguro editar ponteiros soltos quando o FM06 precisa atualizar várias listas.

Registrar para depuração:

- data do jogo;
- clube e responsável;
- proposta e modo vigente;
- limites verificados;
- rotina nativa chamada;
- resultado ou erro.

O log técnico pode ficar fora do save. As preferências e propostas pendentes precisam de persistência.

### 4.6 Onde guardar as novas preferências

Existem três caminhos, em ordem de dificuldade:

1. **arquivo lateral por save (MVP):** rápido de construir, versionar e depurar; deve usar nome do
   save, UID do humano/clube e uma assinatura para não aplicar dados ao save errado;
2. **campos nativos comprovadamente ociosos:** só usar depois de campanha de diffs e teste de várias
   temporadas; o risco de colisão é alto;
3. **bloco novo dentro do save:** experiência mais limpa, mas exige localizar serialização,
   carregamento, versão e checksum.

Para o MVP, o arquivo lateral é a opção realista. Se estiver ausente ou incompatível, todas as tarefas
voltam a `Eu decido`.

### 4.7 Limite da arquitetura atual de patches

Pequenos desvios e novas propriedades cabem bem nos stubs atuais. Um planejador completo, com listas,
texto, persistência e dezenas de regras, será difícil de manter apenas como bytes x86 gerados por
Python. Antes das fases complexas será preciso escolher entre:

- hooks finos que reaproveitam quase toda a lógica nativa; ou
- um componente de execução 32-bit carregado pelo jogo, mantendo no patch somente os trampolins.

Essa é uma decisão técnica de passagem. Não se deve começar a tela completa de Responsabilidades nem
reescrever a IA de mercado antes de provar o ciclo de carregamento, salvamento e chamada segura.

## 5. Frente A — escalação, banco e planejamento do elenco

### 5.1 Ações desejadas

| Ação | Regra principal |
|---|---|
| melhores titulares | qualidade por função, adequação, condição e disponibilidade |
| reservas | menos minutos/partidas recentes, sem desmontar todas as posições |
| jovens | limite de idade ou formado no clube, respeitando nível mínimo e proteção física |
| mista | cotas configuráveis de titulares, reservas e jovens |
| condição física | priorizar descansados; jogador exausto só entra se não houver cobertura |
| desempenho | média/forma recente como ajuste, nunca como único critério |
| banco automático | cobrir goleiro, defesa, laterais, meio e ataque dentro do limite da competição |
| rotação sugerida | alertar sequência excessiva, queda de condição e próximo calendário |
| salvar escalações | usar os presets nativos `tsel` |
| comparar jogadores | abrir comparação nativa lado a lado |
| planejador de elenco | mostrar titular, reserva, jovem e carência por posição |
| alertas | contrato, insatisfação, lesão, carga e posição sem cobertura |

### 5.2 “Preservar minhas escolhas”

Esse requisito é obrigatório e deve ser a primeira entrega funcional:

1. fotografar os jogadores já colocados no XI e no banco;
2. marcar seus slots como bloqueados;
3. remover esses atletas do conjunto de candidatos;
4. pedir ao seletor que preencha somente os slots vazios;
5. validar duplicidade, disponibilidade e limite do banco;
6. mostrar uma prévia antes de aplicar, até o fluxo estar estável.

A opção nativa `usts` — “Use current team selection when possible” — indica que o jogo já possui
semântica parecida durante férias. A primeira investigação deve localizar a função atendida por esse
checkbox e comparar com `aatp`. Reutilizar essa rotina é muito menos arriscado que criar um otimizador
completo imediatamente.

### 5.3 Ordem de entrega da escalação

1. rastrear `aatp`, `usts`, leitura e gravação da `sqtb`;
2. criar `Preencher vazios` preservando escolhas;
3. separar políticas Titulares, Condição e Jovens;
4. preencher banco por cobertura;
5. acrescentar Reservas e Mista;
6. integrar presets nativos;
7. só então criar planejador, alertas e rotação sugerida.

## 6. Frente B — Responsabilidades e comissão técnica

### 6.1 Matriz inicial

| Tarefa | Primeira entrega segura | Execução automática futura | Dificuldade |
|---|---|---|---|
| recomendar staff por cargo | lista explicada, sem contratar | abrir negociação ou ofertar dentro de limites | média/alta |
| renovar contratos do staff | alerta + proposta de termos | negociar antes do vencimento | alta |
| contratar/substituir staff | shortlist por carência | buscar, ofertar e dispensar com travas | muito alta |
| distribuir treinadores | prévia da atribuição | chamar o evento nativo `auto` | baixa/média |
| organizar amistosos | calendário sugerido | chamar rotinas de `arrf` e aceitar adversário | média/alta |
| controlar reservas | escalação sugerida | delegar escalação e rotina de jogos | alta |
| controlar juniores | plano e escalação sugeridos | gerir partidas e desenvolvimento | alta |
| entrevistas/imprensa | destacar resposta recomendada | responder segundo perfil do adjunto | muito alta |
| reunião semanal | notícia/resumo somente de leitura | criar propostas ligadas aos problemas | média |
| contratar jovens | shortlist com limites | observar, negociar e registrar promessa | muito alta |

### 6.2 Limites configuráveis por tarefa

Mesmo em `Adjunto executa`, o usuário define:

- orçamento máximo por contratação e por mês;
- salário máximo e aumento máximo numa renovação;
- duração máxima do contrato;
- quantidade máxima de funcionários por cargo;
- cargos que nunca podem ser dispensados automaticamente;
- idade, nacionalidade, reputação e nível mínimo do candidato;
- quantidade e nível dos amistosos;
- limite de jovens contratados e custo total;
- se empréstimos podem ter taxa, divisão salarial, opção ou obrigação;
- se uma decisão irreversível sempre exige confirmação.

Dispensar funcionário, vender jogador, aceitar obrigação de compra e ultrapassar o orçamento devem
continuar pedindo confirmação no primeiro ciclo do projeto, mesmo no modo executivo.

### 6.3 Recomendação e contratação de staff

O mapa de comissão compara o que cada cargo precisa com os atributos do pessoal disponível. A busca
deve considerar:

- cargo real e quantidade permitida;
- especialidade necessária;
- qualidade, adaptabilidade, reputação e conhecimento do país;
- salário, compensação e duração;
- ganho sobre o funcionário atual;
- custo de demissão e risco de deixar o cargo vazio.

Não substituir alguém por melhora mínima. Exigir um ganho relevante ou uma razão objetiva: contrato
acabando, cargo vazio, atributo crítico baixo ou funcionário querendo sair.

### 6.4 Renovações

Executar uma varredura semanal, com antecedência configurável. A proposta mostra:

- vínculo atual e vencimento;
- importância e desempenho do funcionário;
- substitutos possíveis;
- faixa salarial permitida;
- recomendação `renovar`, `aguardar` ou `substituir`.

O modo executivo só inicia a negociação; se a contraproposta ultrapassar os limites, a decisão volta
ao usuário.

### 6.5 Amistosos

O planejador usa o calendário para reservar:

- preparação física no começo;
- jogos progressivamente mais difíceis;
- intervalo mínimo entre partidas;
- viagem e local;
- receita/custo;
- um último teste próximo da estreia, sem prejudicar a recuperação.

Uma má campanha pode justificar amistoso durante intervalo, mas não preencher qualquer data vazia.
O FM06 já expõe `arrf`, `cafr` e o painel `friendly.xml`; falta localizar a criação e confirmação
interna do evento.

### 6.6 Reserva e juniores

As equipes `1spn` e `2spn` já existem. O controle delegado deve compartilhar a política de escalação,
mas com objetivos próprios:

- reserva: ritmo de jogo, retorno de lesão e cobertura do principal;
- juniores: desenvolvimento, minutos equilibrados e proteção física;
- o titular chamado para o principal fica indisponível para a equipe secundária;
- promessas não devem ser bloqueadas por veteranos sem futuro no clube;
- decisões de contrato, venda ou empréstimo continuam na responsabilidade correspondente.

### 6.7 Entrevistas e imprensa

Delegar imprensa não significa escolher sempre a resposta “neutra”. O adjunto precisa de um perfil:
calmo, protetor, exigente ou provocador, influenciado por seus atributos e personalidade. Como o
sistema de mídia possui consequências e caminhos próprios, esta frente fica depois das tarefas que
já têm ações nativas claras.

### 6.8 Reunião semanal da comissão

Começar como uma notícia única, gerada uma vez por semana, contendo no máximo:

- três problemas que exigem decisão;
- três destaques positivos;
- contratos próximos do fim;
- carga/rotação;
- carências de elenco e comissão;
- jovens que precisam de mudança de plano;
- propostas pendentes das responsabilidades.

Cada item abre a tela relevante. Isso conecta Central, elenco, staff e mercado sem obrigar a criar
uma nova classe de painel logo no começo.

## 7. Frente C — mercado inteligente dos outros clubes

### 7.1 O problema a corrigir

Hoje um clube pode comprar um atleta que jogou muito bem sob o comando do humano e, depois, deixá-lo
no banco porque:

- a forma pesou mais que a necessidade real;
- o comprador não comparou o atleta com os jogadores que já tinha;
- a tática e as posições disponíveis não foram consideradas;
- não houve definição de papel esperado;
- a decisão de contratar e a decisão de escalar parecem usar critérios diferentes.

A correção não é obrigar toda contratação a ser titular. Clubes também contratam reservas, apostas e
oportunidades. A correção é fazer o motivo da compra sobreviver depois da assinatura.

### 7.2 Funil de contratação da IA

#### Passo 1 — detectar a necessidade

Gerar uma prioridade por posição usando:

- quantidade de jogadores realmente utilizáveis;
- diferença entre titular, reserva e nível esperado do clube;
- lesões e suspensões longas;
- idade e fim de contrato;
- calendário e competições disputadas;
- status de transferência e insatisfação;
- desempenho recente abaixo do esperado;
- orçamento e folha disponíveis.

Sem carência, a IA só avança por uma oportunidade excepcional e precisa registrar o papel como aposta,
rotação ou sucessão futura.

#### Passo 2 — buscar candidatos conhecidos

O clube não deve conhecer igualmente todos os jogadores. Usar, conforme for possível localizar:

- conhecimento do país/liga;
- observação/shortlist;
- reputação;
- partidas contra o clube;
- indicação de staff;
- disponibilidade para transferência ou empréstimo.

O bom desempenho com o humano entra como evidência, não como passe livre para qualquer comprador.

#### Passo 3 — calcular encaixe

Pontuação editorial inicial, a ser calibrada por telemetria:

| Critério | Peso inicial |
|---|---:|
| necessidade na posição | 25% |
| melhora sobre titular/reserva atual | 20% |
| encaixe na tática e funções | 15% |
| custo total e salário | 15% |
| forma/desempenho recente | 10% |
| idade, potencial e revenda | 10% |
| adaptação e disponibilidade | 5% |

Os pesos não são verdade estatística nem devem ser gravados no executável antes dos testes. A regra
mais importante é um **portão de necessidade/encaixe**: forma alta não compensa uma posição já lotada.

#### Passo 4 — declarar um papel antes da oferta

Toda compra recebe um motivo:

- titular imediato;
- disputa/rotação;
- cobertura de emergência;
- sucessor futuro;
- jovem para desenvolver ou emprestar;
- oportunidade financeira.

O campo nativo `Squad Status` do contrato, confirmado em `+37`, pode ajudar a representar a hierarquia.
Ele não basta: os dados de minutos e escalação pós-compra ainda precisam ser localizados.

#### Passo 5 — validar o negócio

Antes de ofertar:

- confirmar janela/registro;
- reservar taxa, luvas, salário e bônus;
- simular folha por pelo menos a duração mínima definida no projeto;
- verificar limite de elenco/inscrição;
- impedir duplicação de propostas para a mesma necessidade;
- prever saída, empréstimo ou perda de espaço de alguém do elenco.

#### Passo 6 — revisar a integração

Após 30, 60 e 120 dias:

- o atleta recebeu o papel esperado?
- houve mudança de técnico/tática, lesão ou evolução de concorrente?
- se é jovem ou excedente, deve ser oferecido por empréstimo?
- se a contratação falhou, reduzir a confiança no mesmo perfil e evitar repetir imediatamente.

Não forçar uma escalação artificial só para justificar o negócio. A IA deve reavaliar com motivos
reais, mas o índice de “contratações mortas” precisa cair.

### 7.3 Reação a resultados ruins

Resultados ruins aumentam **urgência**, não criam dinheiro nem tornam todo jogador adequado.

Um ciclo quinzenal compara:

- pontos/posição atuais com a expectativa do clube;
- gols feitos e sofridos;
- notas e disponibilidade por setor;
- mudança recente de técnico;
- caixa e janela restante.

Se a causa provável estiver num setor carente, a prioridade sobe. Se o elenco é suficiente e o
problema é tático, moral ou lesões curtas, a IA não deve contratar por pânico. Rebaixamento, venda de
titular ou lesão longa criam gatilhos extraordinários.

### 7.4 Calendário de recrutamento

Em vez de uma chance aleatória igual todos os dias:

| Momento | Comportamento |
|---|---|
| 4–8 semanas antes da pré-temporada | planejar saídas, renovações, carências e listas |
| começo da primeira janela | maior volume de ofertas e empréstimos |
| após estadual/fase curta | reavaliar quem não funcionou e posições expostas |
| antes da competição nacional | segunda montagem para clubes de calendário brasileiro |
| segunda janela | correções, lesões, vendas e disputa esportiva |
| fora da janela | observação, pré-contrato e acordo para registro futuro |

Clubes com temporadas regionais e nacionais precisam de mais de uma revisão. Isso explica o padrão
do Figueirense melhor que uma única “janela de verão” de modelo europeu.

### 7.5 Mercado de empréstimos

Criar uma etapa de casamento entre duas listas.

**Clube que empresta oferece:**

- jovem sem minutos previstos;
- jogador excedente;
- atleta voltando de lesão que precisa de ritmo;
- percentual de salário que aceita pagar;
- nível mínimo/máximo da liga de destino;
- papel/minutos desejados;
- possibilidade de opção ou obrigação.

**Clube que recebe procura:**

- posição carente;
- qualidade compatível;
- custo dentro da folha;
- duração até o fim da competição;
- disponibilidade e inscrição;
- chance real de utilizar o atleta.

**Pontuação do acordo:** necessidade + nível + minutos esperados + custo + distância/adaptação +
relação entre clubes. A negociação cai se o recebedor já possui três opções melhores ou não pode
prometer participação razoável.

Para clubes com pouco caixa, o empréstimo pode ser o primeiro caminho; para clubes ricos, é mais
comum emprestar o excedente. Percentuais de salário, taxa e opção precisam usar as rotinas reais do
FM06 quando forem localizadas, não edição manual do contrato.

> Atenção: os “empréstimos” tratados em `src/fm06patch/orcamentos.py` são **dívidas bancárias dos
> clubes**, não empréstimos de jogadores. Os dois conceitos não podem compartilhar código ou nomes
> internos ambíguos.

## 8. Frequência de contratações: o que os dados permitem afirmar

Não existe uma média universal adequada para todos os clubes.

- A FIFA registrou **1.190 entradas internacionais em clubes brasileiros em 2025**, o maior total
  entre as associações. Esse número não inclui transferências domésticas e não deve ser dividido
  automaticamente por todos os clubes do Brasil.
- A metodologia pública da FIFA declara que seus relatórios cobrem exclusivamente transferências
  internacionais de profissionais no futebol de 11.
- Um levantamento histórico do CIES em primeiras divisões europeias encontrou extremos de **7,4 a
  14 novos jogadores por clube**, contando as contratações desde o começo do ano até a data daquele
  estudo. É uma referência de estabilidade, não uma média brasileira atual.
- O Figueirense contratou **24 jogadores entre a pré-temporada e o primeiro semestre de 2026**, segundo
  levantamento do ge. O caso confirma que clubes brasileiros de alta rotatividade podem ficar muito
  acima do padrão das ligas europeias estáveis.

Portanto, o jogo deve trabalhar com **perfis**, não com uma meta única:

| Perfil editorial | Faixa inicial para simulação* | Comportamento |
|---|---:|---|
| estável | 6–10 chegadas/ano | mantém base, contrata por melhoria clara |
| normal | 8–15 chegadas/ano | corrige setores nas duas janelas |
| alta rotatividade | 14–26 chegadas/ano | contratos curtos, empréstimos e revisões por competição |

\* Faixas de calibração propostas, não “médias oficiais do Brasil”. Devem variar por tamanho do
elenco, divisão, finanças, troca de técnico, vendas, lesões e desempenho. Não são cotas a cumprir: um
clube sem necessidade pode contratar menos; um elenco desmontado pode ultrapassar a faixa com trava
de tamanho e folha.

### Fontes de calibração

- [FIFA — Global Transfer Report 2025 e metodologia](https://inside.fifa.com/transfer-system/transfer-reports)
- [FIFA — Brasil liderou entradas internacionais em 2025](https://legal.fifa.com/transfer-system/media-releases/international-transfers-reach-historic-high-2025)
- [CBF — calendário e janelas anunciadas para 2026](https://www.cbf.com.br/a-cbf/por-dentro-da-cbf/comissao-dopagem/exame-antidoping-e-lbcd/cbf-oficializa-datas-do-calendario-do-futebol-do-brasil-profissional-masculino-de-2026)
- [CBF — consulta viva das janelas de transferência](https://www.cbf.com.br/a-cbf/drt/janela-de-transferencia)
- [CIES — referência histórica de novos jogadores por clube](https://football-observatory.com/-Newsletter_EN-?debut_articles_popup_jma=480&nb=120)
- [ge — 24 reforços do Figueirense no primeiro semestre de 2026](https://ge.globo.com/sc/futebol/times/figueirense/noticia/2026/06/18/aprovados-como-foram-os-reforcos-do-figueirense-no-primeiro-semestre-de-2026.ghtml)
- [Figueirense — exemplo oficial de contratação por empréstimo](https://figueirense.com.br/leonan-e-o-novo-contratado-do-figueirense/)

### Divergência de datas que precisa ser preservada como pendência

O anúncio inicial da CBF informa segunda janela nacional de 20/07 a 11/09. A consulta viva da CBF
mostra, atualmente, aberturas diferentes por divisão em 2026 (por exemplo, 09/07 na Série A e 06/07
na Série B). O patch atual do projeto usa 20/07. **Este roadmap não altera essa regra**, mas a data
deve ser validada antes de mexer novamente em `transferencias.py`.

## 9. Interface proposta

### 9.1 Tela de Responsabilidades

Organização sugerida:

```text
RESPONSABILIDADES

Elenco e partidas
  Escalação do principal       [Eu decido | Sugere | Executa]
  Time reserva                 [Eu decido | Sugere | Executa]
  Juniores                     [Eu decido | Sugere | Executa]
  Amistosos                    [Eu decido | Sugere | Executa]

Comissão
  Contratar funcionários       [Eu decido | Sugere | Executa] [Limites...]
  Renovar contratos            [Eu decido | Sugere | Executa] [Limites...]
  Distribuir treinadores       [Eu decido | Sugere | Executa]

Mercado e desenvolvimento
  Contratar jovens             [Eu decido | Sugere | Executa] [Limites...]
  Empréstimos de jovens        [Eu decido | Sugere | Executa] [Limites...]

Comunicação
  Entrevistas e imprensa       [Eu decido | Sugere | Executa] [Perfil...]
```

Cada linha precisa mostrar o funcionário responsável e avisar quando o clube não possui alguém no
cargo. O modo `Executa` fica desabilitado enquanto os limites obrigatórios não forem definidos.

### 9.2 Caixa de entrada como fila de aprovação

Enquanto a tela própria não existe, as sugestões podem ser entregues como decisões:

- “Renovar o preparador até dezembro de 2028 por até R$ X/mês”;
- “Agendar quatro amistosos entre datas A e B”;
- “Emprestar o jovem Y para clube de Série B, com expectativa de titularidade”;
- “Preencher as seis vagas restantes da escalação preservando os cinco escolhidos”.

Essa fila é mais importante que a arte final da tela, porque prova o ciclo sugerir → aprovar → executar.

### 9.3 Central de Desenvolvimento

A Central consome o mesmo `DepthChart` para explicar:

- por que um jovem está bloqueado na posição;
- se deve ficar no Sub-20, treinar com o principal ou sair por empréstimo;
- qual posição/função aumenta sua chance de minutos;
- quem da comissão avaliou;
- quando o plano será revisto.

O documento visual e técnico detalhado continua em `docs/CENTRO_DE_DESENVOLVIMENTO.md`.

## 10. Pesquisa de engenharia reversa necessária

### 10.1 Escalação

- seguir o evento `aatp` até a rotina que gera XI/banco;
- seguir `usts` e identificar como preserva a seleção atual;
- localizar leitura/escrita dos slots da tabela `sqtb`;
- identificar os critérios nativos de posição, condição e qualidade;
- descobrir como presets `tsel` são serializados.

### 10.2 Responsabilidades

- seguir `auto` em `training coaches list.xml`;
- seguir `arrf`/`cafr` e confirmação do `friendly.xml`;
- seguir abertura e envio de `contract offer.xml` para staff;
- localizar o agendador diário/semanal do clube humano;
- localizar criação de notícia com botões de decisão;
- descobrir como reservas e juniores recebem controle de IA;
- mapear o fluxo de mídia antes de tentar delegar entrevistas.

### 10.3 Mercado da IA

Começar por telemetria, sem alterar decisões:

1. marcar quando um clube inicia busca;
2. registrar posição/carência percebida;
3. registrar lista de candidatos e pontuações nativas;
4. registrar por que uma oferta é criada ou recusada;
5. registrar elenco e tática do comprador antes/depois;
6. observar status no elenco e uso do contratado;
7. rastrear colocação e aceitação de empréstimos.

Experimentos controlados úteis:

- mesmo jogador com forma alta/baixa;
- comprador com posição vazia/lotada;
- orçamento alto/baixo;
- status no elenco diferente;
- lesão longa do titular;
- atleta listado/não listado;
- jogador conhecido/desconhecido;
- janela aberta/fechada;
- clube em boa/má fase.

Só depois desses testes preencher `docs/reversing/transfer-ai.md` com endereços, registradores,
estruturas e chamadas confirmadas.

## 11. Roadmap por marcos

### Marco 0 — observabilidade e contrato técnico

**Objetivo:** entender os caminhos nativos sem mudar o jogo.

- rastrear `aatp`, `usts`, `auto`, `arrf`, contratos e decisão de mercado;
- criar logs opt-in e reproduzíveis;
- documentar estruturas e endereços;
- escolher persistência e arquitetura de runtime;
- criar saves/cenários mínimos de teste.

**Saída:** documentação de reversing preenchida e chamadas nativas comprovadas.

### Marco 1 — escalação que preserva escolhas

**Objetivo:** primeiro ganho real de cliques com baixo alcance.

- botão `Preencher posições vazias`;
- preservar XI/banco já escolhido;
- usar o seletor nativo;
- prévia e cancelar;
- testes com lesão, suspensão, goleiro e banco de 12.

**Saída:** nenhuma escolha manual é trocada quando a opção está ativa.

### Marco 2 — mapa de elenco e sugestões

**Objetivo:** criar o núcleo compartilhado sem automação irreversível.

- `SquadSnapshot` e `DepthChart`;
- políticas Titulares, Condição, Jovens e Mista;
- cobertura automática do banco;
- alertas de rotação e contratos;
- primeira reunião semanal somente de leitura.

**Saída:** escalação e Central explicam carências da mesma forma.

### Marco 3 — Responsabilidades em modo sugestão

**Objetivo:** provar o fluxo de aprovação.

- persistir `Eu decido`/`Adjunto sugere`;
- sugestões de distribuição de treinadores;
- propostas de amistosos;
- alertas de renovação e recomendações de staff;
- fila na caixa de entrada com aceitar/recusar.

**Saída:** nenhuma ação é executada antes da aprovação.

### Marco 4 — execução de tarefas seguras

**Objetivo:** liberar `Adjunto executa` somente onde as rotinas nativas estão comprovadas.

- autoatribuição de treinadores;
- amistosos dentro de limites;
- escalação de reservas/juniores;
- renovação com teto e retorno ao usuário em contraproposta;
- auditoria completa.

**Saída:** teste de uma temporada sem ação fora dos limites.

### Marco 5 — necessidades e coerência de mercado

**Objetivo:** reduzir compras sem função antes de aumentar o volume.

- mapa de necessidades para clubes da IA;
- portão por posição/encaixe;
- papel esperado antes da oferta;
- revisão pós-compra;
- métricas de utilização e contratação morta.

**Saída:** o clube consegue explicar por que comprou e onde pretende usar.

### Marco 6 — frequência, reação e empréstimos

**Objetivo:** representar o mercado brasileiro de maior rotatividade.

- perfis estável/normal/alta rotatividade;
- ciclos de pré-temporada, pós-estadual e segunda janela;
- urgência por desempenho ruim, lesão e venda;
- casamento de empréstimos;
- divisão salarial, taxa e expectativa de minutos;
- limites de folha e tamanho de elenco.

**Saída:** clubes pequenos se reforçam com mais frequência e empréstimos, sem acumular elencos
absurdos nem contratar posições lotadas.

### Marco 7 — tela final e delegações de alto risco

**Objetivo:** acabamento depois de a lógica estar estável.

- tela própria de Responsabilidades;
- contratação/substituição automática de staff;
- contratação delegada de jovens;
- entrevistas por perfil do adjunto;
- histórico de decisões e revisão de limites.

**Saída:** sistema completo, mas cada automação pode ser desligada individualmente.

## 12. Testes e critérios de aceitação

### 12.1 Segurança

- tarefa em `Eu decido` nunca executa ação;
- ausência/corrupção do arquivo lateral volta para `Eu decido`;
- nenhuma oferta ultrapassa orçamento ou salário configurado;
- falha no hook chama a rotina original ou cancela sem corromper o save;
- ação irreversível exige confirmação conforme a política;
- jogo continua carregando saves antigos e novos.

### 12.2 Escalação

- preservar escolhas mantém exatamente os slots bloqueados;
- não há jogador duplicado;
- lesionado/suspenso não é selecionado;
- banco cobre posições mínimas;
- jovem, reserva e titular mudam conforme a política;
- o resultado é determinístico com os mesmos dados, salvo desempate explicitamente aleatório.

### 12.3 Responsabilidades

- sugestão mostra responsável, motivo, custo e prazo;
- aceitar executa uma única vez;
- recusar não reapresenta a mesma proposta imediatamente;
- contraproposta fora do limite volta ao usuário;
- reunião semanal agrupa avisos e não cria dezenas de notícias.

### 12.4 Mercado

Medir por clube, divisão e temporada:

- chegadas, saídas e empréstimos;
- tamanho e folha do elenco;
- distribuição das chegadas por posição;
- proporção de contratados com papel definido;
- titularidades/minutos após 30, 60 e 120 dias;
- contratações sem uso e motivo posterior;
- carências não resolvidas;
- ofertas recusadas por custo, encaixe ou falta de necessidade;
- atividade por janela e resposta a lesões/vendas/má fase.

Não fixar metas finais antes da telemetria do FM06 original. Primeiro comparar 5–10 temporadas com e
sem o patch; depois calibrar os perfis usando clubes brasileiros reais de portes diferentes.

### 12.5 Cenários obrigatórios

- Figueirense com pré-temporada, estadual ruim e Série C próxima;
- clube estável e vencedor, sem necessidade de reformulação;
- clube rico com posição já lotada;
- clube pobre com duas carências e pouco salário disponível;
- jovem de clube grande sem minutos e clube menor precisando da posição;
- contratação que perde espaço por troca de técnico;
- venda de titular no último terço da janela;
- reserva/juniores jogando no mesmo dia do principal;
- humano escolhe cinco titulares e pede para preencher o restante.

## 13. Arquivos futuros prováveis

Nenhum deles foi criado por este documento; são nomes de organização sugeridos.

### Código do patch

- `src/fm06patch/escalacao.py`;
- `src/fm06patch/mapa_elenco.py`;
- `src/fm06patch/responsabilidades.py`;
- `src/fm06patch/transfer_ai.py`;
- registro dos novos patches em `src/fm06patch/exe_patches.py`;
- testes correspondentes em `tests/`.

### Documentação de reversing

- preencher `docs/reversing/transfer-ai.md`;
- criar `docs/reversing/team-selection.md`;
- criar `docs/reversing/responsibilities.md`.

### Telas/skin, somente após a lógica

- `data/sections.xml`;
- `data/screens/team.xml`;
- overrides em `data/skins/brasil 2026/panels/`;
- possivelmente uma tela/painel novo, se a classe correspondente for registrada no executável.

### Persistência

- pasta versionada de esquema/configuração no projeto;
- arquivo lateral criado ao lado do save ou em diretório próprio do mod, somente depois de confirmar
  o caminho real de saves e a identidade estável do humano/clube.

## 14. O que não fazer

- não criar primeiro uma tela bonita sem controlador;
- não alterar a quantidade de contratações antes de corrigir necessidade e encaixe;
- não usar uma cota rígida que obrigue todo clube a contratar;
- não comprar jogador apenas por forma ou CA;
- não usar PA exato nas explicações ao usuário;
- não escrever contratos diretamente na memória sem chamar a transação nativa;
- não automatizar demissões, vendas ou obrigações de compra na primeira versão;
- não tratar dívidas bancárias e empréstimos de jogadores como a mesma estrutura;
- não preencher endereços em `transfer-ai.md` por suposição;
- não misturar alterações deste roadmap com a atualização atual do banco de dados.

## 15. Próxima ação recomendada

Sem implementar o sistema completo, o próximo trabalho técnico deve ser uma rodada de
**engenharia reversa somente de leitura**:

1. seguir `aatp` e `usts` para viabilizar `Preservar minhas escolhas`;
2. seguir `auto` para provar o primeiro fluxo `sugerir → executar`;
3. instrumentar uma única decisão de compra da IA e preencher a primeira seção real de
   `docs/reversing/transfer-ai.md`;
4. capturar três saves comparáveis: clube com carência, clube com posição lotada e clube em má fase;
5. só depois escolher qual marco implementar primeiro.

Assim, a primeira entrega economiza cliques imediatamente, e o conhecimento obtido serve de fundação
para delegação, Central de Desenvolvimento e mercado — sem prometer ao XML um trabalho que pertence
ao executável.
