"use strict";

let data = null;
const ui = {
  tab: "live",
  agendaId: null,
  agendaSearch: "",
  medium: "todos",
  question: 0,
  answers: {},
  privatePlayer: null,
  privateTopic: "poor_streak",
  bankCategory: "Todos",
  bankSearch: "",
  bankSituation: null,
};

const $ = selector => document.querySelector(selector);
const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
const esc = value => String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]);
const slugClass = value => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/gi, "-").toLowerCase();

function fill(text, extra = {}) {
  const context = {...(data?.info || {}), ...extra};
  return String(text).replace(/\{(\w+)\}/g, (_, key) => context[key] ?? `{${key}}`);
}

function outletBy(id) { return data.outlets.find(item => item.id === id) || data.outlets[0]; }
function playerBy(id) { return data.players.find(item => item.id === id) || data.players[0]; }
function situationBy(id) { return data.situations.find(item => item.id === id) || data.situations[0]; }
function agendaBy(id) { return data.agenda.find(item => item.id === id) || data.agenda[0]; }
function journalistBy(outlet, id) { return outlet.journalists.find(item => item.id === id) || outlet.journalists[0]; }
function selectedAgenda() { return agendaBy(ui.agendaId); }

function contextFor(player) {
  return {
    player: player.short_name,
    club: data.info.club,
    rival: data.info.rival,
    competition: data.info.competition,
    manager: data.info.manager,
    fact: data.info.fact,
  };
}

function seeded(seed) {
  let state = (Number(seed) || 1) >>> 0;
  return () => {
    state ^= state << 13; state ^= state >>> 17; state ^= state << 5;
    return (state >>> 0) / 4294967296;
  };
}

function portraitSVG(person, size = 96) {
  const random = seeded(person.seed);
  const skins = ["#f3c49f","#dca27e","#bd7c58","#8d563f","#603d31","#e8b68c"];
  const skin = skins[Math.floor(random() * skins.length)];
  const shade = ["#bc795d","#a8664e","#744734"][Math.floor(random() * 3)];
  const hairs = ["#17130f","#3a2518","#704324","#b8905f","#c5c8cf","#542c1e"];
  const hair = hairs[Math.floor(random() * hairs.length)];
  const jackets = ["#173f69","#252d3d","#4a2932","#264b43","#4d4f5b","#17324d"];
  const jacket = jackets[Math.floor(random() * jackets.length)];
  const tie = ["#ffda3d","#d94d55","#4ab981","#6caee5","#d37b38"][Math.floor(random() * 5)];
  const eye = random() > .58 ? "#2c5f70" : "#241812";
  const hairStyle = Math.floor(random() * 5);
  const glasses = random() > .64;
  const facial = random() > .72;
  const mouthY = random() > .5 ? 23 : 22;
  const hairShapes = [
    `<rect x="9" y="6" width="14" height="4" fill="${hair}"/><rect x="7" y="9" width="3" height="7" fill="${hair}"/><rect x="22" y="9" width="3" height="7" fill="${hair}"/>`,
    `<path d="M7 15V9h3V6h16v3h-2v3h-4V9h-4v3h-4v3z" fill="${hair}"/>`,
    `<rect x="8" y="7" width="16" height="5" fill="${hair}"/><rect x="6" y="10" width="5" height="8" fill="${hair}"/><rect x="22" y="10" width="4" height="8" fill="${hair}"/>`,
    `<path d="M8 13V8h3V5h4v2h4V5h5v3h2v7h-3v-4H11v4z" fill="${hair}"/>`,
    `<rect x="9" y="8" width="14" height="3" fill="${hair}"/><rect x="8" y="10" width="3" height="4" fill="${hair}"/>`,
  ];
  const glassesSvg = glasses ? `<rect x="9" y="15" width="6" height="4" fill="none" stroke="#17202a"/><rect x="18" y="15" width="6" height="4" fill="none" stroke="#17202a"/><rect x="15" y="16" width="3" height="1" fill="#17202a"/>` : "";
  const facialSvg = facial ? `<rect x="11" y="22" width="11" height="4" fill="${hair}" opacity=".8"/><rect x="13" y="21" width="7" height="1" fill="${hair}"/>` : "";
  return `<svg class="pixel-portrait" width="${size}" height="${Math.round(size * 1.1)}" viewBox="0 0 32 38" shape-rendering="crispEdges" role="img" aria-label="Retrato gerado de ${esc(person.name)}">
    <rect x="3" y="34" width="26" height="4" fill="#020a13" opacity=".55"/>
    <path d="M4 38v-7l7-4h10l7 4v7z" fill="${jacket}"/><path d="M11 27l5 7 5-7-2-2h-6z" fill="#eef3f6"/><path d="M15 30h2l2 8h-6z" fill="${tie}"/>
    <rect x="13" y="24" width="6" height="5" fill="${shade}"/><rect x="7" y="11" width="19" height="14" fill="${skin}"/><rect x="6" y="15" width="3" height="6" fill="${skin}"/><rect x="24" y="15" width="3" height="6" fill="${skin}"/>
    <rect x="8" y="21" width="2" height="3" fill="${shade}" opacity=".55"/><rect x="23" y="21" width="2" height="3" fill="${shade}" opacity=".55"/>
    ${hairShapes[hairStyle]}
    <rect x="11" y="16" width="2" height="2" fill="${eye}"/><rect x="20" y="16" width="2" height="2" fill="${eye}"/><rect x="16" y="18" width="2" height="3" fill="${shade}" opacity=".55"/>
    ${glassesSvg}${facialSvg}<rect x="14" y="${mouthY}" width="5" height="1" fill="#6f3031"/>
    <rect x="5" y="31" width="3" height="7" fill="#0c1b2a" opacity=".35"/><rect x="25" y="31" width="3" height="7" fill="#0c1b2a" opacity=".35"/>
    <title>${esc(person.name)} · rosto gerado pelo seed ${person.seed}</title>
  </svg>`;
}

function playerSprite(player) {
  const skin = ["#f0bd92","#d89b73","#ad6e4e","#754a36"][Math.abs(player.id) % 4];
  const boots = "#111820";
  return `<svg class="pixel-player" viewBox="0 0 16 23" shape-rendering="crispEdges" aria-hidden="true">
    <ellipse cx="8" cy="22" rx="6" ry="1.3" fill="#000" opacity=".45"/><rect x="6" y="1" width="5" height="5" fill="${skin}"/><rect x="5" y="1" width="7" height="2" fill="#2d2119"/>
    <rect x="4" y="6" width="8" height="8" fill="#101215"/><rect x="5" y="6" width="2" height="8" fill="#f3f3ed"/><rect x="9" y="6" width="2" height="8" fill="#f3f3ed"/><rect x="6" y="8" width="4" height="2" fill="#111"/>
    <rect x="2" y="7" width="2" height="7" fill="${skin}"/><rect x="12" y="7" width="2" height="7" fill="${skin}"/><rect x="4" y="14" width="8" height="3" fill="#f4f4f0"/>
    <rect x="5" y="17" width="2" height="4" fill="#e7e8eb"/><rect x="9" y="17" width="2" height="4" fill="#e7e8eb"/><rect x="4" y="21" width="4" height="1" fill="${boots}"/><rect x="9" y="21" width="4" height="1" fill="${boots}"/>
  </svg>`;
}

function riskClass(risk) { return risk === "alto" ? "high" : risk === "médio" ? "medium" : "low"; }

function renderHeader() {
  $("#club-name").textContent = data.info.club;
  $("#mode-badge").textContent = data.mode === "jogo" ? "FM06 ABERTO · SÓ LEITURA" : "MODO DEMO · SEM SAVE";
  $("#mode-badge").title = data.info.notice || "";
  $("#current-date").textContent = new Date(`${data.info.date}T12:00:00`).toLocaleDateString("pt-BR");
  const s = data.bank_stats;
  $("#header-summary").innerHTML = `<div class="header-kpi"><b>${data.agenda.length}</b><span>pautas</span></div><div class="header-kpi"><b>${data.outlets.length}</b><span>veículos</span></div><div class="header-kpi"><b>${s.situations}</b><span>situações</span></div><div class="header-kpi"><b>${s.response_combinations}</b><span>respostas</span></div>`;
  $("#footer-stats").textContent = `${s.situations} situações · ${s.questions} perguntas · ${s.response_combinations} combinações de resposta`;
}

function renderFilters() {
  const media = ["todos", ...new Set(data.outlets.map(outlet => outlet.medium))];
  $("#medium-filters").innerHTML = media.map(item => `<button class="filter-chip ${ui.medium === item ? "active" : ""}" data-medium="${esc(item)}" type="button">${item}</button>`).join("");
}

function renderAgenda() {
  const term = ui.agendaSearch.trim().toLocaleLowerCase("pt-BR");
  const list = data.agenda.filter(item => {
    const outlet = outletBy(item.outlet_id);
    const matchesMedium = ui.medium === "todos" || outlet.medium === ui.medium;
    const haystack = `${item.headline} ${outlet.name} ${playerBy(item.player_id).name}`.toLocaleLowerCase("pt-BR");
    return matchesMedium && (!term || haystack.includes(term));
  });
  $("#agenda-count").textContent = list.length;
  $("#agenda-list").innerHTML = list.length ? list.map(item => {
    const outlet = outletBy(item.outlet_id), player = playerBy(item.player_id);
    return `<button class="agenda-card ${item.id === ui.agendaId ? "active" : ""}" data-agenda="${item.id}" type="button">
      <img class="agenda-logo" src="${outlet.logo}" alt="${esc(outlet.name)}">
      <span class="agenda-outlet">${esc(outlet.name)}</span><span class="agenda-time">${esc(item.when)}</span>
      <strong class="agenda-title">${esc(item.headline)}</strong>
      <span class="agenda-meta"><i class="urgency ${esc(item.urgency)}"></i>${esc(player.short_name)} · ${esc(outlet.medium)} · ${esc(item.status)}</span>
      ${item.reason ? `<span class="agenda-reason">${esc(item.reason)}</span>` : ""}
    </button>`;
  }).join("") : `<div class="loading">Nenhuma pauta encontrada.</div>`;
}

function answerCards(situation, player, scope, selectedId) {
  const context = contextFor(player);
  return `<div class="answer-grid">${situation.intentions.map((answer, index) => `<button class="answer-card ${selectedId === answer.id ? "selected" : ""}" data-answer="${answer.id}" data-answer-scope="${scope}" type="button">
    <span class="answer-index">${index + 1}</span><b>${esc(answer.label)}</b><span class="answer-tone">${esc(answer.tone)}</span>
    <p>${esc(fill(answer.text, context))}</p><span class="answer-risk ${riskClass(answer.risk)}"><i></i> risco ${esc(answer.risk)}</span>
  </button>`).join("")}</div>`;
}

function impactFor(answer, player, situation) {
  const result = {...answer.effects};
  const p = player.personality;
  const id = answer.id;
  if (["challenge","raise_bar","meritocracy","objective","demand"].includes(id) && p.ambition >= 14) { result.player += 1; result.training += 1; }
  if (["private_standard","objective","group_code","medical"].includes(id) && p.professionalism >= 14) result.player += 1;
  if (["challenge","public_standard","attack_critics","cut_ties"].includes(id) && p.pressure <= 9) result.player -= 2;
  if (["provoke","attack_critics","pressure_agent"].includes(id) && p.temperament <= 9) result.player -= 1;
  if (["listen","protect","second_chance","pathway"].includes(id) && p.loyalty >= 14) result.player += 1;
  if (["provoke","attack_critics","challenge_source"].includes(id) && p.controversy >= 12) result.media -= 1;
  if (!situation.public) { result.media = 0; result.fans = 0; }
  Object.keys(result).forEach(key => result[key] = clamp(result[key], -4, 4));
  return result;
}

function impactRow(label, value) {
  const width = Math.abs(value) * 12.5;
  const left = value < 0 ? 50 - width : 50;
  const signal = value > 0 ? `+${value}` : String(value);
  return `<div class="impact-row"><span>${label}</span><div class="impact-track"><i class="${value < 0 ? "neg" : ""}" style="left:${left}%;width:${width}%"></i></div><b>${value === 0 ? "—" : signal}</b></div>`;
}

function impactCard(answer, player, situation, compact = false) {
  if (!answer) return `<section class="panel context-card"><h3 class="section-title"><i></i> Leitura da situação</h3><p class="impact-lead">Escolha uma intenção para visualizar uma reação simulada. Os números não são enviados ao FM06.</p></section>`;
  const effects = impactFor(answer, player, situation);
  const playerPhrase = effects.player >= 2 ? `${player.short_name} se sente respaldado.` : effects.player <= -2 ? `${player.short_name} recebe a fala como exposição pública.` : `${player.short_name} entende a mensagem, sem reação extrema.`;
  const headline = answer.risk === "alto" ? `${data.info.club}: resposta forte aumenta a tensão na coletiva` : `${data.info.club} define posição sobre ${situation.title.toLocaleLowerCase("pt-BR")}`;
  return `<section class="panel impact-card ${compact ? "compact" : ""}"><h3 class="section-title"><i></i> Reação simulada</h3><p class="impact-lead"><b>${esc(playerPhrase)}</b> A personalidade do jogador alterou o resultado-base desta resposta.</p>
    ${impactRow("Jogador", effects.player)}${impactRow("Elenco", effects.squad)}${impactRow("Torcida", effects.fans)}${impactRow("Diretoria", effects.board)}${impactRow("Imprensa", effects.media)}${impactRow("Resposta ao treino", effects.training)}
    <div class="impact-headline">MANCHETE PROVÁVEL · ${esc(headline)}</div><div class="follow-up"><b>Follow-up:</b> ${esc(fill(answer.follow_up, contextFor(player)))}</div>
    <button class="reset-answer" data-reset-answer type="button">Testar outra resposta</button></section>`;
}

function formClass(value) { return value < 6.3 ? "bad" : value < 7 ? "mid" : ""; }

function contextCards(player) {
  const p = player.personality;
  const traits = [["Ambição",p.ambition],["Profissionalismo",p.professionalism],["Pressão",p.pressure],["Temperamento",p.temperament],["Lealdade",p.loyalty],["Controvérsia",p.controversy]];
  return `<section class="panel context-card"><h3 class="section-title"><i></i> Contexto do jogador</h3><div class="context-grid"><div class="context-metric"><b>${player.stats.matches}</b><span>jogos</span></div><div class="context-metric"><b>${player.stats.goals}</b><span>gols</span></div><div class="context-metric"><b>${player.stats.assists}</b><span>assistências</span></div><div class="context-metric"><b>${String(player.stats.rating).replace(".",",")}</b><span>nota média</span></div></div><div class="form-row">${player.form.map(value => `<span class="form-chip ${formClass(value)}">${String(value).replace(".",",")}</span>`).join("")}</div></section>
  <section class="panel context-card"><h3 class="section-title"><i></i> Como ele tende a reagir</h3><div class="personality-list">${traits.map(([label,value]) => `<div class="trait"><span>${label}</span><i><i style="width:${value * 5}%"></i></i><b>${value}</b></div>`).join("")}</div></section>`;
}

// por que a pauta existe: o fato lido do jogo (modo jogo) ou a regra de gatilho (demo)
function whyCard(agenda, player, situation) {
  const source = player.stats.unofficial ? `Números de jogos <b>não oficiais</b> (${esc(player.team || "base")}): ${player.stats.matches} jogos, nota ${String(player.stats.rating).replace(".", ",")}.` : "";
  return `<section class="panel context-card why-card"><h3 class="section-title"><i></i> Por que esta pauta</h3>
    <p class="why-fact">${esc(agenda.reason || situation.trigger)}</p>
    <p class="why-rule"><b>Regra:</b> ${esc(situation.trigger)} · urgência ${esc(situation.urgency)}</p>${source ? `<p class="why-rule">${source}</p>` : ""}</section>`;
}
function renderLive() {
  const agenda = selectedAgenda(), outlet = outletBy(agenda.outlet_id), journalist = journalistBy(outlet, agenda.journalist_id);
  const player = playerBy(agenda.player_id), situation = situationBy(agenda.situation_id), question = situation.questions[ui.question % situation.questions.length];
  const answerKey = `${agenda.id}:${ui.question}`, selectedId = ui.answers[answerKey];
  const answer = situation.intentions.find(item => item.id === selectedId);
  $("#view").innerHTML = `<div class="live-layout"><section class="panel stage">
    <div class="stage-top"><img src="${outlet.logo}" alt="${esc(outlet.name)}"><div><strong>${esc(outlet.name)}</strong><small>${esc(journalist.role)} · ${esc(outlet.city)} · ${esc(outlet.voice)}</small></div><span class="live-pill">AO VIVO</span></div>
    <div class="press-stage"><div class="journalist-block"><div class="portrait-frame">${portraitSVG(journalist, 94)}<span class="portrait-seed">ID ${String(journalist.seed).slice(-5)}</span></div><b>${esc(journalist.name)}</b><span>${esc(journalist.role)} · ${esc(outlet.name)}</span><em>${esc(journalist.approach)}</em></div>
      <div class="question-block"><span class="question-label"><i></i> pergunta ${ui.question + 1} de ${situation.questions.length}</span><blockquote class="question-text">${esc(fill(question, contextFor(player)))}</blockquote><div class="question-nav"><div class="question-dots">${situation.questions.map((_, index) => `<button class="question-dot ${index === ui.question ? "active" : ""}" data-question="${index}" aria-label="Pergunta ${index + 1}" type="button"></button>`).join("")}</div><span class="question-context"><b>Gatilho:</b> ${esc(situation.trigger)}</span></div></div>
      <div class="subject-block"><div class="subject-head"><span class="player-token">${playerSprite(player)}</span><div><b>${esc(player.short_name)}</b><small>${player.age} anos · ${esc(player.position)}</small></div></div><span class="subject-status">${esc(player.status)}</span><div class="subject-stats"><div><b>${player.morale}</b><span>moral</span></div><div><b>${String(player.stats.rating).replace(".",",")}</b><span>nota</span></div><div><b>${player.stats.minutes}</b><span>minutos</span></div></div></div>
    </div><div class="answer-zone"><div class="answer-head"><div><strong>Escolha a intenção e o modo de falar</strong><small>O texto muda com o contexto; a consequência não é revelada antes da resposta.</small></div><span>8 caminhos disponíveis</span></div>${answerCards(situation, player, "live", selectedId)}</div>
  </section><aside class="context-stack">${whyCard(agenda, player, situation)}${answer ? impactCard(answer, player, situation) : contextCards(player) + impactCard(null, player, situation)}</aside></div>`;
}

const PRIVATE_TOPICS = ["match_star","poor_streak","training_drop","new_position","few_minutes","transfer_interest"];

function renderPrivate() {
  const player = playerBy(ui.privatePlayer), situation = situationBy(ui.privateTopic);
  const key = `private:${player.id}:${situation.id}`, selectedId = ui.answers[key];
  const answer = situation.intentions.find(item => item.id === selectedId);
  const coach = {name:data.info.manager, seed:63061979};
  $("#view").innerHTML = `<div class="private-layout"><aside class="panel private-roster"><h3 class="section-title"><i></i> Escolha o jogador</h3>${data.players.map(item => `<button class="private-player ${item.id === player.id ? "active" : ""}" data-private-player="${item.id}" type="button"><span class="player-token">${playerSprite(item)}</span><b>${esc(item.short_name)}</b><small>${esc(item.status)} · moral ${item.morale}/20</small></button>`).join("")}</aside>
  <section class="panel private-main"><div class="conversation-hero"><div class="portrait-frame">${portraitSVG(coach, 94)}<span class="portrait-seed">TÉCNICO</span></div><div class="conversation-copy"><span class="screen-kicker">CONVERSA PARTICULAR / PORTA FECHADA</span><h2>${esc(data.info.manager)} → ${esc(player.short_name)}</h2><p>Neste modo, imprensa e torcida não recebem efeito direto. A escolha trabalha confiança, relação e resposta ao treinamento.</p><div class="tag-list"><span class="tag">${esc(player.position)}</span><span class="tag">moral ${player.morale}/20</span><span class="tag">${esc(player.status)}</span></div></div></div>
    <div class="topic-grid">${PRIVATE_TOPICS.map(id => { const item = situationBy(id); return `<button class="topic-card ${id === situation.id ? "active" : ""}" data-private-topic="${id}" type="button"><b>${esc(item.title)}</b><small>${esc(item.trigger)}</small></button>`; }).join("")}</div>
    <div class="private-answers"><div class="answer-head"><div><strong>${esc(situation.title)}</strong><small>Oito abordagens possíveis para esta conversa.</small></div><span>efeitos simulados</span></div>${answerCards(situation, player, "private", selectedId)}</div>${answer ? `<div style="margin-top:9px">${impactCard(answer, player, {...situation, public:false}, true)}</div>` : ""}
  </section></div>`;
}

function filteredBank() {
  const term = ui.bankSearch.trim().toLocaleLowerCase("pt-BR");
  return data.situations.filter(item => {
    const category = ui.bankCategory === "Todos" || item.category === ui.bankCategory;
    const text = `${item.title} ${item.trigger} ${item.tags.join(" ")} ${item.questions.join(" ")}`.toLocaleLowerCase("pt-BR");
    return category && (!term || text.includes(term));
  });
}

function renderBank() {
  const list = filteredBank();
  if (!list.some(item => item.id === ui.bankSituation)) ui.bankSituation = list[0]?.id || null;
  const situation = ui.bankSituation ? situationBy(ui.bankSituation) : null;
  const stats = data.bank_stats;
  $("#view").innerHTML = `<div class="bank-toolbar"><input class="bank-search" id="bank-search" type="search" value="${esc(ui.bankSearch)}" placeholder="Buscar gatilho, pergunta, tag ou situação…"><div class="bank-stats"><div class="stat-pill"><b>${stats.situations}</b><span>situações</span></div><div class="stat-pill"><b>${stats.questions}</b><span>perguntas</span></div><div class="stat-pill"><b>${stats.response_combinations}</b><span>combinações</span></div></div></div>
    <div class="category-row">${["Todos",...new Set(data.situations.map(item => item.category))].map(category => `<button class="filter-chip ${category === ui.bankCategory ? "active" : ""}" data-bank-category="${esc(category)}" type="button">${esc(category)}</button>`).join("")}</div>
    <div class="bank-layout"><section class="panel scenario-list">${list.length ? list.map(item => `<button class="scenario-item ${item.id === ui.bankSituation ? "active" : ""}" data-scenario="${item.id}" type="button"><i></i><b>${esc(item.title)}</b><small>${esc(item.trigger)}</small><span>${item.intentions.length} intenções</span></button>`).join("") : `<div class="loading">Nenhuma situação encontrada.</div>`}</section>
    <section class="panel scenario-detail">${situation ? `<span class="detail-kicker">${esc(situation.category)} / ${situation.public ? "coletiva pública" : "conversa interna"}</span><h2>${esc(situation.title)}</h2><div class="tag-list">${situation.tags.map(tag => `<span class="tag">${esc(tag)}</span>`).join("")}<span class="tag">urgência ${esc(situation.urgency)}</span></div><div class="scenario-trigger"><b>REGRA DE GATILHO:</b> ${esc(situation.trigger)}</div><h3 class="section-title"><i></i> Perguntas disponíveis</h3><div class="question-list">${situation.questions.map((question,index) => `<div class="question-example"><b>0${index + 1}</b>${esc(fill(question, contextFor(data.players[0])))}</div>`).join("")}</div><h3 class="section-title" style="margin-top:12px"><i></i> Oito intenções de resposta</h3><div class="intention-table">${situation.intentions.map((answer,index) => `<article class="intention-row"><header><b>${index + 1}. ${esc(answer.label)}</b><em>${esc(answer.tone)} · risco ${esc(answer.risk)}</em></header><p>${esc(fill(answer.text, contextFor(data.players[0])))}</p><small>Follow-up: ${esc(fill(answer.follow_up, contextFor(data.players[0])))}</small></article>`).join("")}</div>` : `<div class="loading">Escolha uma situação.</div>`}</section></div>`;
}

function renderOutlets() {
  $("#view").innerHTML = `<div class="bank-toolbar"><div><span class="screen-kicker">REDE NACIONAL E REGIONAL</span><h2 style="margin:2px 0">${data.outlets.length} veículos cadastrados</h2></div><div class="bank-stats"><div class="stat-pill"><b>${data.outlets.reduce((sum,item)=>sum+item.journalists.length,0)}</b><span>jornalistas</span></div><div class="stat-pill"><b>100%</b><span>rostos gerados</span></div></div></div><div class="outlet-grid">${data.outlets.map(outlet => `<article class="panel outlet-card"><img src="${outlet.logo}" alt="${esc(outlet.name)}"><h3>${esc(outlet.name)}</h3><small>${esc(outlet.medium)} · ${esc(outlet.city)} · ${esc(outlet.voice)}</small><div class="focus-list">${outlet.focus.map(item => `<span>${esc(item)}</span>`).join("")}</div>${outlet.journalists.map(person => `<div class="journalist-mini">${portraitSVG(person,36)}<b>${esc(person.name)}</b><small>${esc(person.role)} · seed ${person.seed}</small></div>`).join("")}</article>`).join("")}</div>`;
}

function renderTabs() {
  document.querySelectorAll(".tab").forEach(button => button.classList.toggle("active", button.dataset.tab === ui.tab));
}

function renderView() {
  renderTabs();
  if (ui.tab === "live") renderLive();
  else if (ui.tab === "private") renderPrivate();
  else if (ui.tab === "bank") renderBank();
  else renderOutlets();
}

function renderAll() {
  renderHeader(); renderFilters(); renderAgenda(); renderView();
}

document.addEventListener("click", event => {
  const button = event.target.closest("button");
  if (!button || !data) return;
  if (button.dataset.tab) { ui.tab = button.dataset.tab; renderView(); return; }
  if (button.dataset.agenda) { ui.agendaId = button.dataset.agenda; ui.question = 0; ui.tab = "live"; renderAgenda(); renderView(); return; }
  if (button.dataset.medium) { ui.medium = button.dataset.medium; renderFilters(); renderAgenda(); return; }
  if (button.dataset.question !== undefined) { ui.question = Number(button.dataset.question); renderView(); return; }
  if (button.dataset.answer) {
    if (button.dataset.answerScope === "live") ui.answers[`${selectedAgenda().id}:${ui.question}`] = button.dataset.answer;
    else ui.answers[`private:${ui.privatePlayer}:${ui.privateTopic}`] = button.dataset.answer;
    renderView(); return;
  }
  if (button.hasAttribute("data-reset-answer")) {
    if (ui.tab === "live") delete ui.answers[`${selectedAgenda().id}:${ui.question}`];
    else delete ui.answers[`private:${ui.privatePlayer}:${ui.privateTopic}`];
    renderView(); return;
  }
  if (button.dataset.privatePlayer) { ui.privatePlayer = Number(button.dataset.privatePlayer); renderView(); return; }
  if (button.dataset.privateTopic) { ui.privateTopic = button.dataset.privateTopic; renderView(); return; }
  if (button.dataset.bankCategory) { ui.bankCategory = button.dataset.bankCategory; ui.bankSituation = null; renderView(); return; }
  if (button.dataset.scenario) { ui.bankSituation = button.dataset.scenario; renderView(); return; }
  if (button.id === "press-home") { ui.tab = "live"; renderView(); }
});

$("#agenda-search").addEventListener("input", event => { ui.agendaSearch = event.target.value; renderAgenda(); });
document.addEventListener("input", event => {
  if (event.target.id === "bank-search") { ui.bankSearch = event.target.value; renderBank(); requestAnimationFrame(() => { const input = $("#bank-search"); input?.focus(); input?.setSelectionRange(input.value.length,input.value.length); }); }
});

// --jogo: a notícia aberta no jogo vira a pauta "agora" (o servidor lê a caixa de entrada)
let newsSeen = null;
async function watchNews() {
  try {
    const {noticias} = await (await fetch("/evento", {cache:"no-store"})).json();
    if (newsSeen !== null && noticias > newsSeen) {
      data = await (await fetch("/dados", {cache:"no-store"})).json();
      ui.agendaId = data.agenda.find(item => item.active)?.id || data.agenda[0]?.id;
      ui.question = 0; ui.tab = "live"; renderAll(); window.focus();
      const title = document.title; let blink = 0;
      const timer = setInterval(() => { document.title = blink++ % 2 ? title : "📰 Nova pauta do jogo"; if (blink > 7) { clearInterval(timer); document.title = title; } }, 600);
    }
    newsSeen = noticias;
  } catch {}
}
setInterval(watchNews, 2000);

fetch("/dados", {cache:"no-store"}).then(response => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}).then(payload => {
  data = payload;
  ui.agendaId = data.agenda.find(item => item.active)?.id || data.agenda[0]?.id;
  ui.privatePlayer = data.players[0]?.id;
  ui.bankSituation = data.situations[0]?.id;
  renderAll();
}).catch(error => {
  $("#view").innerHTML = `<div class="loading big"><b>Não foi possível carregar a demonstração.</b><br>${esc(error.message)}</div>`;
});

