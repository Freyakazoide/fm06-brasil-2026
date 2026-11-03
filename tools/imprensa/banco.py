"""Banco editorial da Sala de Imprensa.

Este módulo é deliberadamente independente do save. Ele descreve situações,
perguntas e intenções de resposta que a interface pode explorar em modo demo.
Mais tarde, o integrador do jogo só precisará entregar um contexto compatível.
"""

from __future__ import annotations

from typing import Any


def _intention(
    code: str,
    label: str,
    tone: str,
    text: str,
    follow_up: str,
    *,
    player: int = 0,
    squad: int = 0,
    fans: int = 0,
    board: int = 0,
    media: int = 0,
    training: int = 0,
    risk: str = "baixo",
) -> dict[str, Any]:
    return {
        "id": code,
        "label": label,
        "tone": tone,
        "text": text,
        "follow_up": follow_up,
        "effects": {
            "player": player,
            "squad": squad,
            "fans": fans,
            "board": board,
            "media": media,
            "training": training,
        },
        "risk": risk,
    }


# Oito respostas por família. Uma situação sempre referencia exatamente uma
# família, portanto toda pergunta do banco nasce com oito intenções distintas.
INTENTION_PACKS: dict[str, list[dict[str, Any]]] = {
    "performance": [
        _intention("protect", "Proteger o jogador", "acolhedora", "{player} não será reduzido a um lance. Ele tem nossa confiança e vai responder em campo.", "Então a vaga dele não está em discussão?", player=2, squad=1, media=-1, training=1),
        _intention("challenge", "Desafiar publicamente", "firme", "{player} conhece o padrão que exigimos. Agora precisa mostrar uma reação clara, sem desculpas.", "O senhor espera uma resposta já na próxima partida?", player=-1, fans=1, media=1, training=2, risk="médio"),
        _intention("share", "Dividir a responsabilidade", "serena", "O rendimento de {player} também depende de nós. A equipe precisa colocá-lo em melhores condições.", "O problema foi a maneira como o time jogou?", player=1, squad=1, board=1),
        _intention("explain", "Explicar tecnicamente", "analítica", "O número isolado engana. Estamos avaliando decisões, ocupação de espaço e impacto de {player} sem a bola.", "Há algum dado que sustente essa avaliação?", player=1, media=2),
        _intention("raise_bar", "Elevar a expectativa", "exigente", "Bom não basta para {player}. Pelo talento que possui, esperamos que seja decisivo com regularidade.", "Essa cobrança não pode pesar sobre ele?", player=0, fans=2, training=2, risk="médio"),
        _intention("merit", "Reconhecer o mérito", "entusiasmada", "{player} conquistou esse momento com trabalho. Hoje merece todo o reconhecimento.", "Ele se tornou indispensável?", player=2, squad=1, fans=2, media=1, training=1),
        _intention("reset", "Encerrar o assunto", "direta", "A análise já foi feita internamente. Não vamos transformar uma atuação em julgamento permanente.", "O senhor está evitando falar dos erros?", player=1, media=-1),
        _intention("provoke", "Confrontar a narrativa", "provocativa", "É curioso como uma manchete aparece antes da análise. Nós sabemos exatamente o que {player} entrega.", "A crítica da imprensa incomodou?", player=1, fans=1, media=-2, risk="alto"),
    ],
    "minutes": [
        _intention("pathway", "Apresentar um caminho", "construtiva", "{player} sabe o que precisa melhorar e quais etapas o aproximam da equipe. O caminho está aberto.", "Quais etapas são essas?", player=2, board=1, training=2),
        _intention("meritocracy", "Cobrar meritocracia", "firme", "Minutos não são distribuídos por expectativa. {player} precisa conquistá-los no treino e quando for chamado.", "Ele tem recebido oportunidades suficientes?", player=-1, squad=1, fans=1, training=2, risk="médio"),
        _intention("patience", "Pedir paciência", "acolhedora", "Não vamos queimar etapas com {player}. O desenvolvimento dele vale mais do que uma decisão apressada.", "Há receio de lançá-lo cedo demais?", player=2, board=1, media=-1),
        _intention("promise_none", "Evitar promessas", "pragmática", "Não prometo titularidade a ninguém. Prometo critérios claros e decisões honestas.", "Nem mesmo uma sequência curta?", squad=1, board=1, media=1),
        _intention("role_clarity", "Explicar a função", "analítica", "Estamos preparando {player} para uma função específica. O minuto certo precisa ter propósito, não ser apenas estatística.", "Qual função o senhor imagina para ele?", player=1, media=2, training=1),
        _intention("back_now", "Garantir oportunidade", "confiante", "{player} terá sua oportunidade. Ele mostrou que está pronto para ser testado em um nível maior.", "Isso acontecerá já no próximo jogo?", player=3, fans=1, board=-1, risk="alto"),
        _intention("hierarchy", "Defender a hierarquia", "institucional", "Há jogadores à frente neste momento e isso precisa ser respeitado. {player} seguirá competindo.", "Como ele recebeu essa decisão?", player=-1, squad=2, board=1),
        _intention("reject_pressure", "Rejeitar a pressão externa", "direta", "A escalação não será decidida por campanha pública. A comissão conhece o processo de {player}.", "A torcida está errada ao pedir o jogador?", player=1, fans=-1, media=-2, risk="alto"),
    ],
    "training": [
        _intention("praise_habit", "Elogiar o hábito", "positiva", "{player} tem dado exemplo na rotina. A evolução aparece porque o trabalho diário é sério.", "Ele é uma referência para o grupo?", player=2, squad=2, training=2),
        _intention("private_standard", "Cobrar em particular", "reservada", "Os padrões foram tratados diretamente com {player}. Não vou transformar o treino em espetáculo público.", "Houve uma advertência formal?", player=1, squad=1, media=-1, training=1),
        _intention("public_standard", "Expor o padrão esperado", "exigente", "Aqui ninguém treina pela metade. {player} precisa recuperar imediatamente o nível que o grupo exige.", "A posição dele está ameaçada?", player=-2, squad=2, fans=1, training=2, risk="alto"),
        _intention("adapt_plan", "Ajustar o plano", "analítica", "Talvez o plano precise servir melhor a {player}. Vamos ajustar carga, função e objetivos mensuráveis.", "A comissão errou no planejamento?", player=2, board=1, training=2),
        _intention("protect_load", "Proteger da sobrecarga", "cuidadosa", "{player} não é máquina. Recuperação faz parte do treino e vamos controlar a carga com responsabilidade.", "Ele corre risco de ficar fora?", player=2, squad=1, board=1),
        _intention("competition", "Criar competição", "firme", "O melhor estímulo é concorrência real. {player} sabe que cada sessão conta na disputa pela posição.", "Quem está à frente dele hoje?", player=0, squad=2, training=2, risk="médio"),
        _intention("objective", "Definir uma meta", "construtiva", "O próximo passo de {player} é claro e será acompanhado semanalmente. Queremos progresso, não pressa.", "Qual será o primeiro indicador avaliado?", player=2, training=3),
        _intention("deny", "Negar o problema", "defensiva", "Não existe crise de treinamento. Há oscilações normais e muita especulação em torno de {player}.", "Então os relatos internos estão incorretos?", player=1, media=-2, board=-1, risk="alto"),
    ],
    "market": [
        _intention("commit", "Reafirmar permanência", "segura", "{player} faz parte do nosso projeto e não trabalhamos com a ideia de perdê-lo agora.", "Isso significa que nenhuma proposta será ouvida?", player=2, fans=2, board=-1, risk="médio"),
        _intention("open_door", "Manter a porta aberta", "pragmática", "No futebol, toda situação precisa ser avaliada. O interesse existe, mas qualquer decisão protegerá o {club}.", "Há um valor que mudaria a posição do clube?", player=-1, board=2, media=1),
        _intention("player_choice", "Respeitar o jogador", "acolhedora", "Vamos ouvir {player}. Uma decisão importante de carreira não pode ser tomada ignorando quem entra em campo.", "Ele já manifestou vontade de sair?", player=2, squad=1, board=-1),
        _intention("sporting_plan", "Vender o projeto esportivo", "convincente", "{player} tem minutos, objetivos e espaço para crescer aqui. Nosso projeto vale mais que uma manchete de mercado.", "O clube oferecerá uma renovação?", player=2, fans=1, training=1),
        _intention("club_first", "Colocar o clube primeiro", "firme", "Nenhum nome está acima do {club}. Se houver negociação, será nos termos corretos para o clube.", "Essa postura pode afastar o jogador?", player=-1, squad=1, fans=2, board=2, risk="médio"),
        _intention("deny_rumor", "Negar a informação", "direta", "Não há negociação nos termos publicados. Estão transformando contato informal em acordo fechado.", "O senhor garante que não houve proposta?", player=1, media=-1, board=1),
        _intention("pressure_agent", "Responsabilizar o empresário", "agressiva", "Algumas pessoas falam para valorizar o próprio negócio. O foco de {player} deveria estar no campo.", "O empresário está prejudicando o atleta?", player=-2, fans=1, media=1, risk="alto"),
        _intention("no_comment", "Preservar a negociação", "institucional", "Assuntos contratuais serão tratados na mesa certa. Não vou negociar {player} por microfone.", "O silêncio indica que as conversas avançaram?", media=-1, board=1),
    ],
    "discipline": [
        _intention("listen", "Ouvir antes de julgar", "serena", "Vamos ouvir {player} e entender todos os lados antes de tomar qualquer decisão.", "Quando o clube pretende concluir essa apuração?", player=2, squad=1, board=1),
        _intention("internal", "Resolver internamente", "reservada", "O assunto será tratado dentro do clube, com firmeza e respeito. Exposição não ajuda ninguém.", "Haverá alguma punição?", player=1, squad=1, media=-1),
        _intention("zero_tolerance", "Estabelecer limite", "dura", "Há comportamentos incompatíveis com o {club}. Se confirmados, terão consequência clara.", "O jogador pode ser afastado?", player=-2, squad=2, fans=2, board=2, risk="alto"),
        _intention("second_chance", "Oferecer segunda chance", "humana", "Um erro não precisa definir {player}. Responsabilidade também significa permitir que ele repare o dano.", "O grupo concorda com essa oportunidade?", player=3, squad=0, fans=-1, risk="médio"),
        _intention("group_code", "Defender o código do grupo", "firme", "As regras foram construídas pelo elenco e valem para todos. {player} conhece esse compromisso.", "Os líderes participarão da decisão?", player=-1, squad=3, board=1),
        _intention("context", "Questionar a versão pública", "cautelosa", "Há informações incompletas circulando. Não vou condenar {player} com base em recortes.", "Qual parte da história está incorreta?", player=2, media=-1),
        _intention("apology", "Exigir reparação", "construtiva", "O próximo passo é reconhecer o impacto e reparar a confiança. {player} terá espaço para fazer isso.", "Ele vai pedir desculpas publicamente?", player=0, squad=2, fans=1, training=1),
        _intention("cut_ties", "Romper publicamente", "confrontadora", "Quem não respeita o grupo escolhe ficar fora dele. O {club} seguirá em frente.", "Isso confirma o afastamento definitivo?", player=-4, squad=2, fans=2, board=1, media=2, risk="alto"),
    ],
    "pressure": [
        _intention("calm", "Reduzir a temperatura", "serena", "O momento pede lucidez. Não vamos tomar decisões movidos pelo ruído ao redor do {club}.", "O senhor sente que ainda controla o ambiente?", squad=1, board=1, media=1),
        _intention("mobilize", "Mobilizar o grupo", "energética", "É a hora de mostrar caráter. O grupo sabe o tamanho da resposta que precisa dar.", "Essa partida se tornou uma decisão?", squad=2, fans=2, training=1),
        _intention("accept", "Assumir a responsabilidade", "franca", "A responsabilidade começa em mim. As escolhas foram minhas e preciso entregar soluções melhores.", "O senhor teme pelo próprio cargo?", player=1, squad=1, fans=1, board=-1, media=2),
        _intention("shield", "Blindar o elenco", "protetora", "A cobrança deve vir para mim, não para os jogadores. Eles estão trabalhando para sair dessa situação.", "O elenco está sentindo a pressão?", player=1, squad=2, fans=-1, board=-1),
        _intention("demand", "Cobrar uma reação", "exigente", "Representar o {club} exige resposta. Palavras perderam valor; agora precisamos agir.", "Quem não reagir pode perder espaço?", squad=1, fans=2, training=2, risk="médio"),
        _intention("process", "Defender o processo", "analítica", "Os resultados pressionam, mas os indicadores mostram onde corrigir. Não vamos abandonar o trabalho por ansiedade.", "Quais indicadores ainda sustentam o projeto?", squad=1, board=2, media=1),
        _intention("attack_critics", "Atacar os críticos", "provocativa", "Muita gente aparece nos momentos ruins para decretar fim de ciclo. Vamos lembrar disso quando a resposta vier.", "O senhor está comprando uma briga com a torcida?", squad=1, fans=-2, media=-2, risk="alto"),
        _intention("promise", "Prometer uma resposta", "confiante", "O torcedor verá uma equipe diferente. Eu assumo esse compromisso diante de todos.", "E se essa reação não acontecer?", squad=1, fans=3, board=-2, risk="alto"),
    ],
    "health": [
        _intention("protect", "Priorizar a pessoa", "humana", "Antes do atleta existe {player}. O retorno só acontecerá quando houver segurança e confiança.", "O clube trabalha com alguma data?", player=3, squad=1, board=1),
        _intention("medical", "Apoiar-se na equipe médica", "técnica", "A decisão seguirá critérios médicos, carga e resposta diária. Não haverá atalho.", "Qual é o estágio atual da recuperação?", player=1, board=2, media=2),
        _intention("optimistic", "Transmitir confiança", "otimista", "{player} está reagindo muito bem e o grupo está animado com a evolução.", "Há chance de retorno antecipado?", player=2, fans=1, risk="médio"),
        _intention("cautious", "Controlar a expectativa", "cautelosa", "Ainda é cedo para falar em retorno. Um dia bom não elimina os riscos de acelerar o processo.", "Houve alguma intercorrência?", player=1, media=-1),
        _intention("mental", "Reconhecer o lado mental", "acolhedora", "Recuperação também é confiança. Estamos dando a {player} o suporte necessário para voltar sem medo.", "Há acompanhamento psicológico?", player=3, squad=1),
        _intention("availability", "Cobrar disponibilidade", "firme", "Quando estiver liberado, {player} precisará recuperar ritmo e competir. O lugar não fica reservado.", "Ele pode voltar como opção de banco?", player=-1, squad=1, training=2, risk="médio"),
        _intention("privacy", "Preservar a privacidade", "institucional", "Há limites para o que deve ser exposto. O clube informará apenas o necessário.", "O silêncio não aumenta a especulação?", player=2, media=-2),
        _intention("review", "Revisar o planejamento", "responsável", "Se a carga contribuiu para o problema, nós vamos reconhecer e corrigir o processo.", "A comissão admite que pode ter errado?", player=2, board=-1, media=2),
    ],
    "institutional": [
        _intention("clarify", "Esclarecer os fatos", "objetiva", "A informação correta é simples: {fact}. Qualquer versão diferente disso não veio do {club}.", "Por que a versão anterior parecia diferente?", media=2, board=1),
        _intention("correct_self", "Corrigir a própria fala", "honesta", "Minha fala anterior não foi precisa. Eu deveria ter explicado melhor e assumo essa correção.", "O equívoco causou algum problema interno?", squad=1, fans=1, board=1, media=3),
        _intention("club_voice", "Unificar o discurso", "institucional", "O {club} falará por seus canais oficiais. Não vamos alimentar versões fragmentadas.", "Isso é uma tentativa de controlar a informação?", board=2, media=-1),
        _intention("transparency", "Abrir o contexto", "transparente", "O torcedor merece entender o contexto completo. Vamos apresentar os critérios e assumir as decisões.", "Esses dados serão divulgados?", fans=2, board=0, media=2),
        _intention("deny", "Negar com firmeza", "direta", "Essa história não corresponde aos fatos. Não existe o cenário que foi publicado.", "O veículo publicou uma informação falsa?", fans=1, media=-2, risk="médio"),
        _intention("redirect", "Redirecionar ao futebol", "pragmática", "O assunto institucional está tratado. Nossa energia agora precisa voltar ao campo.", "O senhor não está fugindo da pergunta?", squad=1, media=-1),
        _intention("challenge_source", "Cobrar a fonte", "confrontadora", "Quem fez a acusação precisa sustentá-la com fatos. Insinuação não pode virar verdade por repetição.", "O clube pretende tomar alguma medida?", fans=1, media=-3, risk="alto"),
        _intention("use_moment", "Transformar em mensagem", "política", "Esse episódio mostra por que o {club} precisa ser mais claro, unido e responsável em sua comunicação.", "Haverá mudança interna após o caso?", squad=1, fans=1, board=2, media=1),
    ],
}


def _s(
    code: str,
    category: str,
    title: str,
    pack: str,
    trigger: str,
    questions: tuple[str, str, str],
    tags: tuple[str, ...],
    *,
    urgency: str = "normal",
    subject: str = "jogador",
    public: bool = True,
) -> dict[str, Any]:
    return {
        "id": code,
        "category": category,
        "title": title,
        "pack": pack,
        "trigger": trigger,
        "questions": list(questions),
        "tags": list(tags),
        "urgency": urgency,
        "subject": subject,
        "public": public,
    }


SITUATIONS: list[dict[str, Any]] = [
    # Desempenho
    _s("match_star", "Desempenho", "Craque da partida", "performance", "nota >= 8,0 ou melhor em campo", ("{player} decidiu a partida. Foi a melhor atuação dele no {club}?", "O que mudou para {player} render nesse nível?", "Até onde esse desempenho pode levar {player}?"), ("elogio", "boa fase", "protagonismo")),
    _s("scoring_streak", "Desempenho", "Sequência de gols", "performance", "gol em três jogos consecutivos", ("{player} voltou a marcar e vive grande fase. O senhor esperava essa sequência?", "A equipe está jogando para potencializar {player}?", "Já dá para tratá-lo como a principal referência ofensiva?"), ("gols", "boa fase", "ataque")),
    _s("poor_match", "Desempenho", "Atuação individual ruim", "performance", "nota <= 6,2 com participação relevante", ("{player} teve uma noite difícil. Como o senhor avalia a atuação?", "A permanência de {player} no time está ameaçada?", "O erro de {player} foi determinante para o resultado?"), ("má fase", "cobrança", "erro"), urgency="alta"),
    _s("poor_streak", "Desempenho", "Sequência abaixo do esperado", "performance", "três notas abaixo de 6,5 em cinco jogos", ("A queda de rendimento de {player} já preocupa?", "Por que {player} continua recebendo oportunidades?", "Há um plano para recuperar a confiança de {player}?"), ("sequência", "confiança", "pressão"), urgency="alta"),
    _s("decisive_error", "Desempenho", "Erro decisivo", "performance", "erro ligado diretamente a gol ou eliminação", ("Como {player} saiu do vestiário depois do erro?", "O senhor teme que esse lance afete a confiança de {player}?", "Foi uma falha individual ou consequência do sistema?"), ("erro", "confiança", "decisão"), urgency="alta"),
    _s("missed_penalty", "Desempenho", "Pênalti desperdiçado", "performance", "pênalti perdido em momento relevante", ("{player} seguirá como cobrador depois de perder esse pênalti?", "O grupo consolou {player} no vestiário?", "Houve dúvida sobre quem deveria fazer a cobrança?"), ("pênalti", "confiança", "hierarquia"), urgency="alta"),
    _s("red_card", "Desempenho", "Expulsão determinante", "discipline", "cartão vermelho com impacto no resultado", ("A expulsão de {player} foi irresponsável?", "O clube pretende multar ou advertir {player}?", "Como evitar que esse comportamento se repita?"), ("disciplina", "expulsão", "consequência"), urgency="alta"),
    _s("comeback_performance", "Desempenho", "Retorno decisivo", "performance", "grande atuação após lesão ou afastamento", ("O retorno de {player} superou suas expectativas?", "{player} já está pronto para uma sequência como titular?", "O que esse desempenho representa para o elenco?"), ("retorno", "superação", "titularidade")),
    # Minutos e função
    _s("benched", "Espaço no time", "Perda da titularidade", "minutes", "titular fica no banco por dois jogos", ("Por que {player} perdeu a vaga no time?", "{player} entendeu a decisão de começar no banco?", "A mudança é pontual ou existe uma nova hierarquia?"), ("banco", "hierarquia", "decisão"), urgency="alta"),
    _s("few_minutes", "Espaço no time", "Poucos minutos", "minutes", "menos de 90 minutos em cinco jogos", ("{player} está recebendo uma oportunidade justa?", "Existe risco de {player} pedir para sair por falta de minutos?", "O que falta para {player} participar mais?"), ("minutos", "insatisfação", "plano")),
    _s("early_substitution", "Espaço no time", "Substituição precoce", "minutes", "substituído antes dos 55 minutos", ("A substituição de {player} foi uma punição pelo desempenho?", "{player} saiu visivelmente contrariado. Houve conversa?", "O senhor mudaria a decisão de escalar {player}?"), ("substituição", "reação", "tática"), urgency="alta"),
    _s("new_position", "Espaço no time", "Mudança de posição", "minutes", "jogador utilizado fora da função habitual", ("Por que {player} está sendo utilizado nessa nova posição?", "A mudança pode comprometer o desenvolvimento de {player}?", "Essa função será permanente ou uma solução de emergência?"), ("posição", "função", "desenvolvimento")),
    _s("senior_debut", "Espaço no time", "Estreia no profissional", "minutes", "primeira partida pela equipe principal", ("Como o senhor avalia a estreia de {player}?", "O que foi dito a {player} antes de entrar em campo?", "A estreia muda o planejamento para o restante da temporada?"), ("estreia", "base", "oportunidade")),
    _s("youth_promotion", "Espaço no time", "Promoção da base", "minutes", "jovem passa a treinar com o principal", ("Por que {player} foi promovido neste momento?", "{player} será integrado de vez ou apenas observado?", "Quais cuidados o clube terá com a exposição do jovem?"), ("base", "promoção", "planejamento")),
    _s("captaincy", "Espaço no time", "Braçadeira de capitão", "minutes", "novo capitão ou capitão muito jovem", ("O que fez {player} merecer a braçadeira?", "Como os jogadores mais experientes receberam a escolha?", "A liderança pode mudar o futebol de {player}?"), ("capitão", "liderança", "vestiário")),
    # Treino e evolução
    _s("training_star", "Treinamento", "Destaque nos treinamentos", "training", "avaliação de treino alta por três semanas", ("{player} tem sido o principal destaque dos treinos?", "O bom trabalho de {player} será recompensado com minutos?", "Que aspecto mais evoluiu na rotina de {player}?"), ("treino", "evolução", "mérito"), public=False),
    _s("training_drop", "Treinamento", "Queda de dedicação", "training", "comprometimento ou avaliação de treino baixa", ("A intensidade de {player} nos treinos caiu?", "O clube está preocupado com a postura de {player}?", "Essa queda de rendimento terá consequência na escalação?"), ("treino", "cobrança", "disciplina"), urgency="alta", public=False),
    _s("late_training", "Treinamento", "Atraso no treino", "discipline", "atraso ou ausência não justificada", ("{player} será punido pelo atraso?", "O comportamento de {player} desrespeitou o restante do grupo?", "Esse foi um episódio isolado ou já havia alertas?"), ("atraso", "regra", "punição"), urgency="alta"),
    _s("overload", "Treinamento", "Carga excessiva", "training", "fadiga alta ou reclamação de carga", ("{player} está treinando acima do limite?", "A comissão vai reduzir a carga antes da próxima partida?", "Existe conflito entre desempenho imediato e proteção física?"), ("carga", "fadiga", "prevenção")),
    _s("role_training", "Treinamento", "Treino de nova função", "training", "plano ativo de posição ou função", ("Por que {player} está treinando uma função diferente?", "Quanto tempo essa adaptação deve levar?", "A nova função aumenta as chances de {player} no time?"), ("função", "posição", "plano"), public=False),
    _s("stagnation", "Treinamento", "Evolução estagnada", "training", "indicadores sem progresso por período longo", ("A evolução de {player} parou?", "O clube considera mudar o plano de desenvolvimento?", "A falta de jogos está prejudicando {player}?"), ("estagnação", "desenvolvimento", "plano"), urgency="alta", public=False),
    _s("rehab_training", "Treinamento", "Retorno ao treino", "health", "liberado para atividade parcial", ("Qual é o estágio da recuperação de {player}?", "{player} já participa dos trabalhos com bola?", "Existe uma previsão realista para o retorno?"), ("recuperação", "carga", "retorno")),
    # Mercado e contratos
    _s("renewal", "Mercado", "Negociação de renovação", "market", "contrato perto do fim ou conversas abertas", ("As conversas para renovar com {player} avançaram?", "O clube teme perder {player} sem compensação?", "Existe divergência financeira na negociação?"), ("renovação", "contrato", "futuro"), urgency="alta"),
    _s("transfer_interest", "Mercado", "Interesse de outro clube", "market", "rumor ou proposta por jogador", ("O interesse em {player} é concreto?", "O {club} considera negociar {player}?", "Como {player} reagiu à possibilidade de transferência?"), ("mercado", "proposta", "rumor")),
    _s("wants_leave", "Mercado", "Desejo de sair", "market", "jogador ou empresário pede transferência", ("{player} comunicou que deseja deixar o clube?", "Ainda é possível convencer {player} a permanecer?", "O pedido de saída muda a forma como ele será utilizado?"), ("saída", "insatisfação", "contrato"), urgency="alta"),
    _s("bid_rejected", "Mercado", "Proposta recusada", "market", "oferta formal rejeitada", ("Por que o clube recusou a proposta por {player}?", "{player} ficou decepcionado com a decisão?", "Uma oferta maior poderia reabrir a negociação?"), ("proposta", "recusa", "valor"), urgency="alta"),
    _s("loan", "Mercado", "Possível empréstimo", "market", "jogador sem minutos e elegível para empréstimo", ("Um empréstimo seria o melhor caminho para {player}?", "Que tipo de clube o {club} procura para desenvolver {player}?", "Existe receio de perder controle sobre a evolução do jogador?"), ("empréstimo", "minutos", "desenvolvimento")),
    _s("release_clause", "Mercado", "Cláusula e valorização", "market", "cláusula baixa ou forte valorização", ("A cláusula de {player} preocupa a diretoria?", "O clube pretende oferecer um novo contrato imediatamente?", "O valor atual ainda corresponde ao papel de {player}?"), ("cláusula", "valor", "renovação")),
    _s("agent_comment", "Mercado", "Declaração do empresário", "market", "agente fala publicamente sobre futuro", ("Como o clube recebeu a declaração do empresário de {player}?", "O agente está pressionando por uma transferência?", "Essa exposição pode prejudicar a relação com {player}?"), ("empresário", "pressão", "bastidor"), urgency="alta"),
    # Disciplina e vestiário
    _s("player_conflict", "Vestiário", "Conflito entre jogadores", "discipline", "desentendimento público ou no treino", ("Houve uma discussão entre {player} e um companheiro?", "O episódio afetou o ambiente do vestiário?", "Os dois jogadores serão punidos?"), ("conflito", "grupo", "disciplina"), urgency="alta"),
    _s("public_complaint", "Vestiário", "Reclamação pública", "discipline", "jogador critica minutos ou treinador", ("O senhor se sentiu desrespeitado pela fala de {player}?", "{player} terá de se retratar com o grupo?", "Ainda existe confiança entre vocês?"), ("reclamação", "confiança", "hierarquia"), urgency="alta"),
    _s("unauthorized_absence", "Vestiário", "Ausência não autorizada", "discipline", "falta a compromisso do clube", ("Por que {player} não compareceu à atividade?", "O clube já decidiu qual será a punição?", "A ausência coloca o futuro de {player} em dúvida?"), ("ausência", "punição", "compromisso"), urgency="crítica"),
    _s("nightlife", "Vestiário", "Conduta fora de campo", "discipline", "registro público de comportamento inadequado", ("O clube vai investigar a conduta de {player} fora de campo?", "A vida pessoal está afetando o desempenho do atleta?", "Há regras específicas que podem ter sido violadas?"), ("conduta", "imagem", "disciplina"), urgency="alta"),
    _s("social_media", "Vestiário", "Publicação em rede social", "discipline", "postagem controversa ou indireta", ("A publicação de {player} foi uma indireta ao clube?", "O clube orienta os atletas sobre redes sociais?", "{player} será obrigado a apagar ou esclarecer a mensagem?"), ("rede social", "imagem", "comunicação")),
    _s("leadership_split", "Vestiário", "Divisão entre lideranças", "discipline", "grupos de liderança discordam publicamente", ("O vestiário está dividido?", "{player} tem usado sua influência de maneira positiva?", "Como reconstruir a confiança entre as lideranças?"), ("liderança", "divisão", "grupo"), urgency="crítica"),
    _s("public_apology", "Vestiário", "Pedido de desculpas", "discipline", "jogador reconhece erro publicamente", ("O pedido de desculpas de {player} encerra o assunto?", "O grupo aceitou a retratação?", "{player} terá uma segunda chance imediata?"), ("desculpas", "reparação", "segunda chance")),
    # Pressão do clube
    _s("derby", "Pressão", "Semana de clássico", "pressure", "próxima partida contra rival", ("O clássico contra o {rival} define o momento do {club}?", "Como controlar a ansiedade dos jogadores antes do clássico?", "O senhor mudaria seu estilo para vencer o maior rival?"), ("clássico", "rivalidade", "pressão"), urgency="alta", subject="clube"),
    _s("title_race", "Pressão", "Disputa pelo título", "pressure", "rodadas finais com chance de título", ("O {club} está pronto para lidar com a pressão do título?", "Ser líder muda a maneira de preparar as partidas?", "O elenco acredita que pode ser campeão?"), ("título", "expectativa", "reta final"), urgency="alta", subject="clube"),
    _s("relegation", "Pressão", "Luta contra o rebaixamento", "pressure", "clube na zona ou muito próximo", ("O medo do rebaixamento entrou no vestiário?", "O {club} ainda depende apenas de si?", "Que mensagem o senhor dá ao torcedor neste momento?"), ("rebaixamento", "crise", "torcida"), urgency="crítica", subject="clube"),
    _s("manager_pressure", "Pressão", "Treinador pressionado", "pressure", "sequência ruim e risco de demissão", ("O senhor teme ser demitido se não vencer?", "Ainda sente confiança da diretoria e do elenco?", "Por que o torcedor deveria acreditar na continuidade do trabalho?"), ("cargo", "pressão", "continuidade"), urgency="crítica", subject="treinador"),
    _s("fan_protest", "Pressão", "Protesto da torcida", "pressure", "manifestação antes ou depois de partida", ("O protesto da torcida foi justo?", "Os jogadores se sentem ameaçados ou intimidados?", "O que o clube pode fazer para recuperar o apoio?"), ("protesto", "torcida", "crise"), urgency="crítica", subject="clube"),
    _s("heavy_defeat", "Pressão", "Derrota por goleada", "pressure", "derrota por três ou mais gols", ("Como explicar uma derrota desse tamanho?", "O elenco deve desculpas ao torcedor?", "Haverá mudanças profundas depois da goleada?"), ("goleada", "crise", "resposta"), urgency="crítica", subject="clube"),
    _s("board_conflict", "Pressão", "Ruído com a diretoria", "institutional", "declarações divergentes entre técnico e direção", ("Existe um conflito entre o senhor e a diretoria?", "Quem decide de fato o planejamento do futebol?", "O projeto continua tendo apoio interno?"), ("diretoria", "poder", "bastidor"), urgency="crítica", subject="clube"),
    _s("booed", "Pressão", "Vaias ao time", "pressure", "torcida vaia equipe ou atleta", ("Como o elenco recebeu as vaias?", "A reação da torcida pode abalar os jogadores mais jovens?", "O time merece a impaciência das arquibancadas?"), ("vaias", "torcida", "confiança"), urgency="alta", subject="clube"),
    # Saúde e retorno
    _s("new_injury", "Saúde", "Nova lesão", "health", "lesão confirmada após jogo ou treino", ("Qual é a gravidade da lesão de {player}?", "A ausência de {player} muda o planejamento da equipe?", "Havia algum sinal de risco antes do problema?"), ("lesão", "prazo", "planejamento"), urgency="alta"),
    _s("return_injury", "Saúde", "Retorno após lesão", "health", "jogador volta a ser relacionado", ("{player} já está pronto para atuar sem restrições?", "O retorno será gradual ou ele pode começar jogando?", "Como está a confiança de {player} depois da recuperação?"), ("retorno", "minutos", "confiança")),
    _s("recurring_injury", "Saúde", "Lesão recorrente", "health", "reincidência ou terceiro problema semelhante", ("A sequência de lesões de {player} virou uma preocupação estrutural?", "O clube vai rever o método de recuperação?", "Ainda é possível contar com {player} a longo prazo?"), ("recorrência", "método", "futuro"), urgency="crítica"),
    _s("fatigue", "Saúde", "Sinais de desgaste", "health", "fadiga alta ou muitos minutos acumulados", ("{player} precisa ser poupado?", "O calendário está colocando o elenco em risco?", "Como equilibrar resultado imediato e recuperação?"), ("fadiga", "calendário", "rodízio")),
    _s("mental_pressure", "Saúde", "Pressão emocional", "health", "queda de moral ou exposição intensa", ("O clube está preocupado com o estado emocional de {player}?", "A exposição pública tem afetado o jogador?", "Existe suporte específico para ajudá-lo neste momento?"), ("saúde mental", "pressão", "apoio"), urgency="alta"),
    # Institucional e imprensa
    _s("contradiction", "Imprensa", "Declarações contraditórias", "institutional", "fala atual conflita com entrevista anterior", ("Sua declaração de hoje contradiz o que foi dito na semana passada. O que mudou?", "O torcedor recebeu informações incorretas?", "O clube está tendo dificuldade para alinhar a comunicação?"), ("contradição", "credibilidade", "comunicação"), urgency="alta", subject="treinador"),
    _s("rumor_denial", "Imprensa", "Rumor de bastidor", "institutional", "notícia sem confirmação oficial", ("O {club} confirma a informação publicada hoje?", "De onde pode ter partido esse rumor?", "O silêncio do clube não contribuiu para a especulação?"), ("rumor", "fonte", "bastidor"), subject="clube"),
    _s("referee", "Imprensa", "Arbitragem contestada", "institutional", "lance controverso ou reclamação formal", ("A arbitragem interferiu diretamente no resultado?", "O clube pretende formalizar uma reclamação?", "Criticar o árbitro não tira o foco dos próprios erros?"), ("arbitragem", "polêmica", "responsabilidade"), urgency="alta", subject="clube"),
    _s("youth_comparison", "Imprensa", "Comparação precoce", "institutional", "jovem comparado a ídolo ou estrela", ("{player} lembra o antigo ídolo do {club}?", "Essa comparação ajuda ou aumenta a pressão sobre o jovem?", "O senhor vê potencial para {player} atingir o mesmo nível?"), ("comparação", "base", "expectativa")),
    _s("record", "Imprensa", "Marca histórica", "performance", "recorde individual ou coletivo alcançado", ("O que esse recorde representa para {player} e para o {club}?", "A marca muda o lugar de {player} na história do clube?", "Qual foi o momento decisivo para alcançar esse número?"), ("recorde", "história", "reconhecimento")),
]


CATEGORIES = ["Desempenho", "Espaço no time", "Treinamento", "Mercado", "Vestiário", "Pressão", "Saúde", "Imprensa"]


def expand_situation(situation: dict[str, Any]) -> dict[str, Any]:
    """Devolve uma cópia pronta para a interface, já com as oito intenções."""
    return {**situation, "intentions": [dict(item) for item in INTENTION_PACKS[situation["pack"]]]}


def bank() -> list[dict[str, Any]]:
    return [expand_situation(item) for item in SITUATIONS]


def stats() -> dict[str, int]:
    return {
        "situations": len(SITUATIONS),
        "questions": sum(len(item["questions"]) for item in SITUATIONS),
        "response_combinations": sum(len(INTENTION_PACKS[item["pack"]]) for item in SITUATIONS),
        "intention_packs": len(INTENTION_PACKS),
    }


def validate() -> list[str]:
    problems: list[str] = []
    ids: set[str] = set()
    for item in SITUATIONS:
        if item["id"] in ids:
            problems.append(f"situação duplicada: {item['id']}")
        ids.add(item["id"])
        if item["pack"] not in INTENTION_PACKS:
            problems.append(f"pacote inexistente em {item['id']}: {item['pack']}")
            continue
        if len(item["questions"]) < 3:
            problems.append(f"menos de três perguntas em {item['id']}")
        intentions = INTENTION_PACKS[item["pack"]]
        if len(intentions) != 8:
            problems.append(f"{item['id']} não tem oito intenções")
        if len({answer["id"] for answer in intentions}) != len(intentions):
            problems.append(f"intenções duplicadas em {item['pack']}")
    return problems

