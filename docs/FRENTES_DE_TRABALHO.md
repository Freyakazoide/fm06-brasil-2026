# Frentes de trabalho para fazer por fora

O que você pode produzir sozinho, sem esperar teste nem engenharia reversa. Está
dividido em três partes:

- **A. Entra no mod já.** O código já sabe aplicar; falta o dado.
- **B. Entra no mod depois.** Você prepara o dado agora e eu acho o campo no FM06.
- **C. Jogo futuro.** Especificações de sistemas para o seu jogo.

Cada frente diz **o que entregar**, **em que formato** e **como eu uso**.

## Formato das entregas

| Tipo de coisa | Formato | Onde salvar |
|---|---|---|
| Dados (listas, números, nomes) | planilha `.xlsx` com as colunas do modelo | `data/modelos/` tem um modelo para cada frente; salve a versão preenchida sem `_modelo` no nome, na pasta indicada na frente |
| Regras e sistemas (como algo funciona) | `.md` no formato do [modelo de especificação](#modelo-de-especificação) | `docs/jogo_futuro/` |
| Fórmulas | `.md` com a fórmula **e uma tabela de casos de teste** (entrada → resultado esperado) | `docs/jogo_futuro/` |
| Telas | imagem + lista do que cada elemento faz | `docs/jogo_futuro/telas/` |

Você não precisa escrever código. Pseudocódigo ajuda, mas o principal é:
**regra clara + números + exemplos**. Com os casos de teste eu consigo implementar
e provar que está certo.

Três regras de ouro:
1. **Fonte e data** em todo dado real (link + quando você conferiu).
2. **Nome do clube e do jogador igual ao da `jogadores_2026.xlsx`**, senão o script não acha.
3. **Branco é "não sei"**, nunca invente para preencher. O que ficar em branco fica como no FM06.

## Mapa rápido

| # | Frente | Parte | Impacto | Esforço | Modelo |
|---|---|---|---|---|---|
| A1 | Tradução pt-PT → pt-BR | mod já | 🔥🔥🔥 aparece em toda tela | médio | `traducao_ptbr.xlsx` |
| A2 | Personalidade, ocultos e jogadas preferidas | mod já | 🔥🔥🔥 muda como o jogador joga | alto | `jogadores_perfil.xlsx` |
| A3 | Jogos e gols pela seleção | mod já | 🔥 | baixo | colunas já na `jogadores_2026.xlsx` |
| A4 | Lesões e suspensões em jan/2026 | mod já | 🔥 | baixo | `lesoes_suspensoes_2026.xlsx` |
| A5 | Comissão técnica dos clubes que faltam | mod já | 🔥🔥 | médio | `comissao_2026.csv` |
| B1 | Nomes de regens modernos | mod depois | 🔥🔥🔥 | médio | `nomes_regens.xlsx` |
| B2 | Estrutura e dinheiro dos clubes | mod depois | 🔥🔥 | médio | `clubes_estrutura_2026.xlsx` |
| B3 | Rivais e clássicos | mod depois | 🔥🔥 | baixo | aba `Rivais` |
| B4 | Árbitros 2026 | mod depois | 🔥 | baixo | `arbitros_2026.xlsx` |
| B5 | Histórico de carreira dos craques | mod depois | 🔥 | alto | (planilha simples, ver texto) |
| C1–C14 | Sistemas do jogo futuro | futuro | — | — | `.md` |
| C0 | Números reais para calibrar | mod e futuro | 🔥🔥 | médio | `calibracao_partidas.xlsx` |

**Por onde começar:** A1 (tradução), depois A2 só com os titulares da Série A,
depois B1 (nomes de regens). São as três coisas que mais denunciam um jogo de
2005 vestido de 2026.

## Estado das entregas — 2026-10-20

| frente | estado | conteúdo entregue / observação |
|---|---|---|
| A1 | preenchida | 380 entradas de glossário e 35 frases; toda tradução longa tem alternativa que cabe |
| A2 | preenchida — editorial v2 | 220 titulares, 11 de cada clube da Série A 2026; todos os 13 ocultos e até 5 jogadas foram preenchidos por método explícito e determinístico, com fonte-base e aviso de revisão por scouting |
| A3 | preenchida para o lote prioritário | corte em 20/10/2026; 90 jogadores do lote foram associados a uma seleção principal e tiveram jogos/gols reaplicados a partir da fonte. Correspondências com data divergente ficam identificadas no histórico, não são silenciosas |
| A4 | preenchida | 4 lesões e 2 suspensões com fonte e data; somente casos confirmados, sem completar por suposição |
| A5 | 156 clubes cobertos; apoio público coletado | `comissao_2026.csv` contém 384 registros: 156 técnicos principais (um por clube) e 228 profissionais de apoio; 106 clubes têm pelo menos um auxiliar/preparador/analista/médico/olheiro publicado, e 50 permanecem só com o técnico porque a fonte consultada não expõe outros nomes. A auditoria por clube está em `comissao_2026_cobertura.csv` |
| B1 | preenchida | 1.650 nomes em 11 grupos e 15 regras de apelido |
| B2 | parcial para a Série A | 20 clubes com modelo societário; campos financeiros/estrutura sem fonte ficam em branco, salvo balanço verificado do Flamengo |
| B3 | preenchida | 42 relações de rivalidade |
| B4 | preenchida | 18 árbitros do quadro FIFA; nível/rigor são parâmetros editoriais |
| B5 | preenchida com ressalva auditável | 510 passagens de liga para os 100 jogadores de maior CA. Em 17 casos a data do banco diverge de 1 a 10 dias da fonte; as páginas foram validadas por nome completo e clube, e as duas datas aparecem no status e nas observações. A fonte agrega por passagem, não por temporada individual |
| C0 | preenchida parcialmente | 12 linhas de liga e 60 valores; lacunas ficam em branco quando a fonte não traz a métrica |
| C1–C14 | especificados | índice em [`docs/jogo_futuro/README.md`](jogo_futuro/README.md) |

As linhas cinzas de exemplo foram removidas das sete planilhas. Dados não
confirmados não foram apresentados como fatos: estimativas de gameplay estão
identificadas como editoriais e campos sem fonte confiável permanecem vazios.

### O que já entrou no mod

| frente | situação | onde |
|---|---|---|
| A1 | ✅ `lang_db` (prêmios, lesões, fases, descrições: 1.942 textos) e telas (`data/languages/portuguese.ltc`: 11.903 textos) | `traducao.py`, `ltc.py`, `traduzir_telas.py` (também roda no `aplicar_brasil_2026.py`); listas em `data/brasil/traducao_lang_db.csv` e `traducao_telas.csv` |
| A2 | ✅ os 220 jogadores | `montar_elencos.py` |
| A3 | ✅ | `montar_elencos.py` + injetor (Player +72/+74) |
| A4 | ⏳ depois: o `MATCH_BAN` cita o jogador pelo nome de 2005 e o comando de lesão não foi isolado | — |
| A5 | ✅ 511 pessoas (a versão nova + os 127 da Wikipédia que tinham saído); auxiliares de clubes estrangeiros quando os brasileiros acabam | `aplicar_comissao.py` |
| B1 | ✅ a testar: 614 nomes novos no fim das tabelas de nomes e 971 que já existiam com peso maior; os de hoje ficam com ~70% do peso de cada nação | `nomes_regens.py`, `aplicar_brasil_2026.py` (`--sem-nomes-regens` desliga) |
| B5 | ✅ a testar: carreira real dos 100 da planilha; os outros jogadores e a comissão de 2026 sem a carreira do jogador de 2005 | `historico_jogadores.py`, `aplicar_historico.py` (depois do `montar_elencos.py`) |
| B2–B4, C0 | ⏳ dados guardados; precisam de engenharia (campos de clube, árbitros) | — |

Das 35 frases da aba Frases, só "Utilizado num sistema de rotatividade do plantel"
existe igual no jogo; as outras não aparecem em nenhuma tela (o texto do jogo é outro)
e não mudam nada. Para acrescentar frases, copie o texto exato de
`data/brasil/traducao_telas.csv` (coluna "antes") ou de um print.

Nas telas, "equipa" vira "equipe" (feminino, como no original, para a frase continuar
certa), "médio" muda só nas posições ("Médio Direito" → "Meia Direita"; "Salário
Médio" fica), "subida"/"descida" só "de divisão" (acesso, rebaixamento), "desarme"
fica e "cabeceamento" vira "cabeceio". Termo que não cabe fica como está e o resto da
frase muda.

No glossário, quatro termos não servem nos textos do `lang_db` e ficaram de fora
lá: "partida" ("perna partida" é perna quebrada), "mão" ("mão partida"),
"Marcador" ("Melhor Marcador" vira "Artilheiro", não "Melhor Placar") e
"campeonato nacional" (vale para todos os países). "Eliminatória" vira "Fase" e
"dos Adeptos", "da Torcida". "equipa" → "time" muda o artigo junto ("antiga
equipa" → "antigo time"); com adjetivo de nacionalidade no feminino, o texto não muda.

---

## A. Entra no mod já

### A1. Tradução pt-PT → pt-BR

O FM06 está em português de **Portugal**: "Selecção", "golo", "plantel",
"prémio", "Tácticas", "Utilizado num sistema de rotatividade do plantel". Nos
seus prints isso aparece em toda tela. É a melhoria mais visível do mod.

**Entregar:** `data/modelos/traducao_ptbr.xlsx`, com duas abas:
- **Glossario:** palavra por palavra (golo → gol, equipa → time, guarda-redes →
  goleiro, relvado → gramado, avançado → atacante, médio → meia, plantel →
  elenco, treinador → técnico, adepto → torcedor, prémio → prêmio, contrato de
  formação, empréstimo…). Mire em umas 300 entradas.
- **Frases:** frase inteira de uma tela, com print. Use para o que não dá para
  traduzir palavra por palavra ("Utilizado num sistema de rotatividade do
  plantel" → "Usado no rodízio do elenco").

**Restrição importante:** o `lang_db.dat` não pode mudar de tamanho, então o
texto novo tem de ter **no máximo as mesmas letras** do antigo. A coluna `cabe`
é para isso; se não couber, ponha uma `alternativa_curta`. Quase tudo cabe
(pt-BR costuma ser mais curto: "Selecção" → "Seleção").

**Como eu uso:** um script como o dos nomes das fases (`nomes_fases.py`), que
já troca texto no `lang_db.dat` hoje.

Bônus: a aba **Jogadas** da `jogadores_perfil.xlsx` lista as 48 "jogadas
preferidas". Anotar como cada uma aparece no jogo ajuda a traduzir essas também.

### A2. Personalidade, atributos ocultos e jogadas preferidas

Hoje o jogador de 2026 herda a personalidade e os ocultos do jogador de 2005
que ele ocupa. Um Arrascaeta com a "cabeça" de um zagueiro reserva de 2005 joga
diferente do real.

**Entregar:** `data/modelos/jogadores_perfil.xlsx`, uma linha por jogador, tudo
na escala 1–20:
- **Personalidade (8):** adaptabilidade, ambição, lealdade, pressão,
  profissionalismo, desportivismo, temperamento, controvérsia.
- **Ocultos (5):** consistência, jogos importantes, propensão a lesão,
  versatilidade, jogo sujo.
- **Jogadas preferidas:** até 4–5, com os nomes da aba `Jogadas`.

Comece pelos **titulares da Série A** (~250). Branco = fica o de 2005.

Dicas para dar nota sem achismo:
- **Propensão a lesão:** quantas lesões e quantos dias parado nos últimos 3
  anos (Transfermarkt tem o histórico de lesões).
- **Consistência:** varia muito a nota de jogo para jogo? (Sofascore mostra as notas).
- **Jogos importantes:** como rendeu em finais e clássicos.
- **Controvérsia e temperamento:** expulsões, polêmicas, entrevistas.
- **Lealdade:** quanto tempo fica nos clubes; recusou proposta para ficar?

**Como eu uso:** o injetor já grava personalidade, ocultos e jogadas
preferidas. Eu só ligo esta planilha no `montar_elencos.py`.

### A3. Jogos e gols pela seleção

A `jogadores_2026.xlsx` já tem as colunas `jogos_selecao` e `gols_selecao`.
Preencha nos jogadores que já jogaram pela seleção (de qualquer país). A
Wikipédia de cada seleção tem a lista de convocados com jogos e gols. O
endereço desse campo no jogo já é conhecido; eu exponho no injetor.

### A4. Lesões e suspensões no começo de 2026

Quem começa janeiro de 2026 machucado ou suspenso.

**Entregar:** `data/modelos/lesoes_suspensoes_2026.xlsx` (abas Lesoes e
Suspensoes). **Como eu uso:** comandos `INJURY` e `BAN` do `.lnc` (falta só
confirmar a sintaxe).

### A5. Comissão técnica dos 156 clubes

Os 156 participantes de 2026 (20 A + 20 B + 20 C + 96 D) têm exatamente um
técnico principal cadastrado. A coleta pública de 20/10/2026 acrescentou 228
profissionais de apoio e elevou para 106 o número de clubes com pelo menos um
nome além do treinador. Nos 50 restantes a página consultada não publicou outro
profissional; não foram criados nomes fictícios para preencher cargo vazio.

**Entregar:** mais linhas no `data/brasil/comissao/comissao_2026.csv`, no mesmo
formato das que já estão lá (abra no Excel e copie uma linha como modelo):
- colunas `serie`, `clube`, `uf`, `cargo`, `funcao`, `nome`, `nacionalidade`,
  `nascimento`, `fonte`, `atualizado`;
- `cargo` é um destes: `auxiliar`, `preparador` (físico ou de goleiros),
  `medico` (médico ou fisioterapeuta), `analista` ou `olheiro`;
- `funcao` é o nome do cargo por extenso, em texto livre.

A fonte boa é o site oficial do clube (página "comissão técnica" ou
"departamento de futebol"). O `aplicar_comissao.py` já usa o arquivo tal como
está. Como fonte de cobertura nacional foi usada a página de equipe técnica do
Transfermarkt, sempre guardando a URL e a data em cada linha. O arquivo
`data/brasil/comissao/comissao_2026_cobertura.csv` registra, clube a clube, a
quantidade por cargo e se a fonte trouxe nomes de apoio.

---

## B. Entra no mod depois (prepare agora)

### B1. Nomes de regens

Os regens (jogadores gerados pelo jogo) brasileiros nascem com nomes do banco
de 2005: muitos "Ronaldinho", "Adriano", "Juninho". Os jovens de 2026 se chamam
Enzo, Kauã, Davi, Endrick, Estêvão, Vitor Roque.

**Entregar:** `data/modelos/nomes_regens.xlsx`:
- **Nomes:** prenomes, sobrenomes e **apelidos** (o brasileiro de uma palavra
  só), cada um com um `peso` (quão comum é), região opcional e geração.
  - Meta: 400 prenomes, 300 sobrenomes e 150 apelidos do Brasil;
  - mais 100 + 100 para Argentina, Uruguai, Colômbia e Paraguai.
  - Fonte boa de prenomes: o IBGE tem a frequência de nomes por década de nascimento.
- **Regras_apelido:** como nasce um apelido ("Gabriel → Gabrielzinho",
  "Wesley → Wesley Natal") e com que frequência.

**Como eu uso:** os nomes do FM06 ficam em tabelas por nação no `server_db` (já
mapeadas no `comissao.py`). Eu troco os nomes brasileiros que nenhuma pessoa do
banco usa pelos seus. No jogo futuro, a lista entra direto no gerador.

### B2. Estrutura e dinheiro dos clubes

**Entregar:** aba `Estrutura` da `data/modelos/clubes_estrutura_2026.xlsx`:
- CT, instalações da base e recrutamento da base (1–20);
- folha salarial, orçamento para contratações, receita e dívida;
- modelo (associação ou SAF), dono da SAF, presidente, sócios-torcedores.

Fontes: balanços publicados pelos clubes, levantamentos anuais de finanças do
futebol brasileiro e notícias.

**Como eu uso:** saldo e público já entram (`financas_2026.csv`). Orçamento e
instalações ainda não estão mapeados no FM06; eu procuro. No jogo futuro, isso é
a base da economia.

### B3. Rivais e clássicos

Aba `Rivais` da mesma planilha: clube, rival, nome do clássico e intensidade
(1–3). No FM06 deve ser uma das duas listas de clubes que o registro do clube
tem (a confirmar). No jogo futuro: clima de clássico, pressão, notícias.

### B4. Árbitros 2026

**Entregar:** `data/modelos/arbitros_2026.xlsx`: nome, UF, quadro (FIFA ou
CBF), nível e rigor. Fonte: a lista do quadro de árbitros FIFA e CBF de 2026.
No FM06 os árbitros são pessoas do `people_db` como o staff, então dá para
renomear do mesmo jeito (a confirmar).

### B5. Histórico de carreira dos craques

Para os ~100 principais jogadores: uma linha por **temporada e clube**, com
jogador, temporada, clube, jogos, gols e se foi empréstimo. Fonte: Transfermarkt
ou Sofascore. Entrou com `data/modelos/historico_carreira.xlsx` (uma linha por
passagem) pelo `scripts/aplicar_historico.py`; regras em `docs/JOGADORES_2026.md`.
Para mais jogadores, basta acrescentar linhas na aba Historico (nome e nascimento
iguais aos da `jogadores_2026.xlsx`).

---

## C. Jogo futuro

Aqui cada frente é **um `.md`** em `docs/jogo_futuro/`, no formato do modelo do
fim deste arquivo. A ordem sugerida é a da lista. O mod atual já é um ótimo
banco de dados inicial: clubes, elencos, estádios, finanças, histórico e regras
de 2026, tudo em planilha.

### C0. Números reais para calibrar (vale para o mod também)

Antes de inventar fórmula, colete o que a realidade faz.

**Entregar:** `data/modelos/calibracao_partidas.xlsx`:
- **Liga:** por série e temporada (2023–2025): gols por jogo, % de vitória do
  mandante, % de empates, cartões, pênaltis, escanteios, pontos do campeão e do
  17º, técnicos demitidos.
- **Valores:** 40–60 jogadores variados, com idade, posição, valor de mercado,
  fim de contrato e por quanto foram vendidos (se foram).

Com isso eu meço se o FM06 mod está realista (rodando uma temporada) e você tem a
meta para o motor de partida e a fórmula de valor do jogo futuro.

### C1. Documento-mãe (GDD)

Uma página:
- **Pilares:** 3 a 5 frases do que o jogo é (ex.: "o futebol brasileiro de
  verdade, da Série D à Libertadores").
- **Para quem é.**
- **O que entra na versão 1 e o que fica de fora.** O "fora" importa tanto quanto o "dentro".
- **Referências:** o que copiar e o que evitar de FM, Elifoot, Brasfoot.

Todo o resto se mede contra esse documento.

### C2. Atributos do jogador

- **Lista final de atributos:** pode ser a do FM06 (a aba `LEIA` da
  `jogadores_2026_modelo.xlsx` tem os nomes em português). Para cada um:
  definição em uma frase, escala e **em que lance da partida ele pesa**.
- **Peso de cada atributo por posição.** É isso que vira o "CA": um zagueiro
  não precisa de finalização.
- **Casos de teste:** 5 jogadores reais com atributos e o CA esperado.

### C3. Valor de mercado

Você pediu "formas de valor". Uma proposta inicial para você criticar e ajustar:

```
valor = base(CA, posição)
        × curva_idade(idade, PA − CA)
        × fator_contrato(meses até o fim)
        × fator_liga(reputação da liga/clube)
        × fator_forma(notas dos últimos 10 jogos)
        × fator_seleção(convocado?)
```

Para cada fator, uma tabela ou curva com números. Exemplos:
- `fator_contrato` é 1,0 com 3 anos ou mais de contrato e 0,35 com 6 meses ou menos;
- `curva_idade` tem o pico aos 24–26 anos; o jovem com PA alto vale pelo futuro.

Os casos de teste são a aba `Valores` do C0: a fórmula aplicada nos jogadores
reais tem de cair perto do valor real. Separe também **valor** (estimativa) de
**preço pedido** (o clube vendedor pede mais) e de **multa rescisória**.

### C4. Economia do clube brasileiro

- **Receitas:**
  - TV, com a divisão das cotas por série;
  - patrocínio master e de uniforme;
  - bilheteria, sócio-torcedor e premiações (CBF, CONMEBOL);
  - venda de jogadores, incluindo a parte que fica com o clube formador.
- **Despesas:** folha, direito de imagem, luvas, base, viagens.
- **Associação × SAF:** o que muda (aporte do dono, dívida, cobrança da torcida).
- **Dívida, salário atrasado e recuperação judicial:** o que acontece no jogo
  quando o caixa fica negativo. É muito brasileiro e quase nenhum jogo tem.

Use os números da B2 como ponto de partida.

### C5. Mercado de transferências brasileiro

Regras que um jogo estrangeiro não tem. Pesquise a regra atual de cada uma (a
Lei Geral do Esporte, de 2023, mudou várias):
- direitos econômicos divididos (clube 60%, empresário 20%, ex-clube 20%);
- multa rescisória nacional × internacional;
- pré-contrato nos últimos meses;
- luvas;
- empréstimo com opção ou obrigação de compra;
- janelas e registro no BID da CBF;
- limite de inscritos por competição;
- mecanismo de solidariedade para o clube formador.

Para cada regra: o que é, número, como a IA decide e um exemplo.

### C6. Regens (geração de jovens)

- **Quantos jovens por clube por ano**, e o que influencia: instalações da
  base, recrutamento, região, reputação.
- **Distribuição de talento:**
  - quantos "joias" (PA 170 ou mais) o Brasil inteiro gera por ano;
  - quantos PA 140–170;
  - quantos são só complemento de elenco.
  - Use a realidade: quantos brasileiros de cada geração chegam à seleção, à
    Europa e à Série A.
- **Posição, altura e pé** por região, se fizer diferença.
- **Nome:** usa a B1 (por região e geração).
- **Casos de teste:** "em 10 temporadas simuladas, o Brasil deve gerar X
  jogadores de seleção".

### C7. Evolução e declínio

- **Curva por idade de cada grupo de atributos:** físico cai cedo, mental cresce até tarde.
- **O que acelera ou trava:** minutos jogados, treino, instalações, lesão
  grave, personalidade (profissionalismo e ambição).
- **Casos de teste:** um jovem de PA 170 que joga sempre × um que não joga, aos
  17, 20 e 23 anos.

### C8. Motor de partida

Não precisa ser 3D. Defina:
- **A unidade de simulação:** lance a lance (posse → ação → resultado) ou por minuto.
- **A lista de eventos:** passe, drible, chute, falta, escanteio, pênalti,
  cartão, lesão, substituição. Para cada evento, quais atributos de quem pesam.
- **Influência da tática:** mentalidade, linha, pressão, largura.
- **Mando de campo, cansaço, clima e gramado:** sintético e altitude são muito
  da América do Sul.
- **Metas de calibração:** a aba `Liga` do C0. O motor está certo quando uma
  temporada simulada reproduz esses números.

Isso casa com o seu mockup de gráficos e sprites: o motor gera a sequência de
eventos e a tela desenha. Defina juntos o formato do "evento", que é a ponte
entre os dois.

### C9. Diretoria, torcida e pressão

- **Expectativa por tamanho de clube:** o que é fracasso para o Flamengo e para
  o Tocantinópolis.
- **Demissão do técnico:** o Brasil demite muito. Use o número real de trocas
  por temporada (C0) para calibrar quantos jogos ruins derrubam um técnico.
- **Eleição do clube:** associação tem presidente com mandato; candidato de
  oposição promete reforço, e isso muda o orçamento.
- **Torcida:** humor, protesto, sócio-torcedor que cancela, organizada.

### C10. Imprensa, notícias e entrevistas em pt-BR

O que dá vida ao jogo e é **só texto**: dá para você escrever centenas de modelos.

**Entregar:** planilha com:
- `situacao` (ex.: vitória em clássico, derrota em casa, contratação, demissão);
- `manchete` e `texto`, com variáveis: `{clube}`, `{rival}`, `{tecnico}`,
  `{jogador}`, `{placar}`, `{rodada}`;
- `tom` (neutro, crítico, exaltado).

Para coletivas, liste pergunta, respostas possíveis e o efeito de cada resposta
na moral e na torcida.

### C11. Competições como dados

As regras de 2026 já estão escritas: `docs/REGRAS_2026.md`,
`REGRAS_2026_ESTADUAIS_E_COPAS.md` e `docs/pesquisa/`. Para o jogo futuro, cada
competição vira uma ficha padronizada:
- fases;
- formato de cada fase (pontos corridos, grupos, mata-mata, ida e volta);
- critérios de desempate em ordem;
- vagas (acesso, rebaixamento, continental);
- datas.

Com um formato único, o motor roda qualquer campeonato sem código novo. Isso
inclui as que o FM06 não tem: Copa do Nordeste, Copa Verde, Supercopa.

Comece pela Série A e por um estadual; eu proponho o formato de arquivo a
partir delas.

### C12. Telas e navegação

Você já fez o mockup dos gráficos. Agora:
- **Mapa de telas:** lista de todas as telas e de onde se chega a cada uma.
- **As 10 telas principais em wireframe:** elenco, ficha do jogador, tática,
  partida, tabela, calendário, mercado, finanças, caixa de entrada, clube.
- **Para cada tela:** que informação mostra, que ações tem, e o "estado vazio"
  (sem jogos ainda, sem propostas).

Compare com as telas do FM06 que você já conhece: o que é útil e o que é
botão demais.

### C13. Objetivos e carreira do técnico

- Objetivos da diretoria por tamanho de clube (C9).
- Reputação do técnico, convites de outros clubes e da seleção.
- Conquistas (troféus, marcas: "subir da D à A", "Libertadores com clube do Norte").

### C14. Modo de edição (moddabilidade)

O seu jogo pode nascer moddável: os dados em planilha ou JSON, como neste
repositório. Defina quais arquivos o jogador pode editar e o formato de cada um.
As planilhas deste mod já são o primeiro rascunho desses formatos.

---

## Modelo de especificação

Copie para `docs/jogo_futuro/<sistema>.md` e preencha:

```markdown
# <Sistema>

## Objetivo
Uma ou duas frases: o que este sistema faz e por que o jogo precisa dele.

## Regras
Lista numerada, uma regra por item, sem ambiguidade.

## Números (parâmetros)
| parâmetro | valor | por quê / fonte |
|---|---|---|

## Exemplos / casos de teste
| entrada | resultado esperado |
|---|---|

## Casos de borda
O que acontece no limite (idade 15, saldo zero, empate em tudo...).

## Liga com
Que outros sistemas este usa ou afeta.

## Perguntas em aberto
O que você ainda não decidiu.
```

## Como me entregar

- Salve no repositório (pasta indicada) e me avise, ou anexe o arquivo aqui na conversa.
- Pode entregar aos pedaços: 50 jogadores de A2 já servem para eu ligar o
  script e testar.
- Se uma coluna não fizer sentido para um caso, escreva na `obs` em vez de
  forçar um valor.
