// Departamento Médico (§8.10): as notícias de lesão da Central, por jogador.
const ICONS = {
  cross: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 7v10M7 12h10"/>',
  bolt: '<path d="M13 2L5 14h7l-1 8 8-12h-7z"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 2v6m10-6v6M3 10h18"/>'
};
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const dateBR = value => value ? value.split("-").reverse().join("/") : "—";
const $ = id => document.getElementById(id);
const icon = (name, size = 16) => `<svg class="ui-icon" width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;
let data = null, selected = null;

function renderHeader() {
  const followed = data.jogadores.filter(p => p.tom !== "good").length;
  $("header-summary").innerHTML = `<div class="header-kpi">${icon("cross", 15)}<b>${data.jogadores.length}</b><span>jogadores</span></div>`
    + `<div class="header-kpi warn">${icon("bolt", 15)}<b>${data.pendentes}</b><span>decisões</span></div>`
    + `<div class="header-kpi">${icon("cross", 15)}<b>${followed}</b><span>acompanhados</span></div>`;
  $("when").textContent = `${data.info.club || "—"} · ${dateBR(data.info.date)}`;
}

function renderCards() {
  if (!data.jogadores.some(p => p.id === selected)) selected = data.jogadores[0]?.id ?? null;
  $("result-count").textContent = data.jogadores.length;
  const box = $("cards"), top = box.scrollTop;
  box.innerHTML = data.jogadores.length ? data.jogadores.map(p => `<button class="news-card ${p.nao_lidas ? "unread" : ""} ${p.id === selected ? "selected" : ""}" data-id="${p.id}" type="button">
      <i class="dot"></i><span class="card-name">${esc(p.nome)}</span><span class="card-age">${dateBR(p.ultima)}</span>
      <span class="card-role"><span class="mini-tag ${p.tom === "pending" ? "pending" : p.tom === "good" ? "done" : ""}">${esc(p.situacao.toUpperCase())}</span>${p.no_elenco ? "" : `<span class="mini-tag">FORA DO ELENCO</span>`}</span></button>`).join("")
    : `<div class="empty">Nenhuma notícia de lesão.</div>`;
  box.scrollTop = top;
}

function story(n) {
  const body = (n.corpo || "").split(/\n+/).filter(Boolean).map(line => `<p>${esc(line)}</p>`).join("");
  return `<section class="panel"><h3>${icon("calendar", 13)} ${dateBR(n.data)} · ${esc(n.manchete || n.assunto)}</h3><div class="news-text">${body || `<p class="card-name missing">Sem texto.</p>`}</div>
    ${n.pendente ? `<p class="news-where pending medical-note">Esta notícia pede uma escolha sua. Por enquanto, responda em <b>Técnico → Notícias</b>, no jogo.</p>` : ""}</section>`;
}

function renderPlayer() {
  const p = data.jogadores.find(item => item.id === selected);
  if (!p) { $("workspace").innerHTML = `<div class="empty">Nenhum jogador em acompanhamento.</div>`; return; }
  const bio = [p.nome_completo, p.posicao, p.idade && `${p.idade} anos`, p.time].filter(Boolean).map(esc).join(" <i></i> ");
  $("workspace").innerHTML = `<header class="player-header news-header"><div class="news-icon">${icon("cross", 28)}</div>
      <div class="identity"><span class="screen-kicker">MEDICAL CENTRE / UID ${p.id}</span><h1>${esc(p.nome)}</h1><div class="bio">${bio}</div>
      <div class="tag-row"><span class="tag">${esc(p.situacao)}</span>${p.moral != null ? `<span class="tag">Moral ${p.moral}/20</span>` : ""}<span class="tag">${p.noticias.length} ${p.noticias.length === 1 ? "notícia" : "notícias"}</span></div></div></header>
    <div class="news-body">${p.noticias.map(story).join("")}</div>`;
}

function render() { renderHeader(); renderCards(); renderPlayer(); }

async function load() {
  try {
    data = await (await fetch("/medico/dados", {cache: "no-store"})).json();
    render();
  } catch (error) {
    $("cards").innerHTML = `<div class="empty">Servidor não respondeu (${esc(error.message)}).</div>`;
  }
}

document.addEventListener("click", event => {
  const card = event.target.closest("[data-id]");
  if (!card || !data) return;
  selected = Number(card.dataset.id);
  render();
});
setInterval(load, 6000);
load();
