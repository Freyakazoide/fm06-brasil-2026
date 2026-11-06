// Central de Notícias (§8.9): a caixa do jogo e as notícias tiradas dela, por módulo. Visual da
// Central de Desenvolvimento (central.css); aqui só o que é de notícia.
const ICONS = {
  mail: '<rect x="3" y="5" width="18" height="14" rx="1"/><path d="M3 7l9 6 9-6"/>',
  bolt: '<path d="M13 2L5 14h7l-1 8 8-12h-7z"/>',
  flag: '<path d="M5 22V3m0 2h12l-2 4 2 4H5"/>',
  dot: '<circle cx="12" cy="12" r="4"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0014 0M12 18v3"/>',
  cross: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 7v10M7 12h10"/>',
  swap: '<path d="M4 8h13l-3-3M20 16H7l3 3"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 2v6m10-6v6M3 10h18"/>'
};
const MODULE_ICON = {imprensa: "mic", medico: "cross", transferencias: "swap", geral: "mail", todas: "mail"};
const FILTERS = [["todas", "Todas"], ["nao_lidas", "Não lidas"], ["pendentes", "Pedem resposta"], ["central", "Só na Central"]];

const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const dateBR = value => value ? value.split("-").reverse().join("/") : "—";
const $ = id => document.getElementById(id);
function icon(name, size = 16) {
  return `<svg class="ui-icon" width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ICONS.info}</svg>`;
}

const ui = {module: "todas", filter: "todas", search: "", selected: null};
let data = null;

function visible() {
  const term = ui.search.trim().toLowerCase();
  return data.noticias.filter(n =>
    (ui.module === "todas" || n.modulo === ui.module)
    && (ui.filter === "todas" || (ui.filter === "nao_lidas" && !n.lida) || (ui.filter === "pendentes" && n.pendente) || (ui.filter === "central" && n.onde === "central"))
    && (!term || `${n.manchete || ""} ${n.assunto} ${n.categoria}`.toLowerCase().includes(term)));
}

function tags(n) {
  return [`<span class="mini-tag">${esc(n.categoria)}</span>`,
    n.pendente ? `<span class="mini-tag pending">PEDE RESPOSTA</span>` : "",
    n.respondida ? `<span class="mini-tag done">RESPONDIDA</span>` : "",
    n.onde === "central" ? `<span class="mini-tag central">SÓ NA CENTRAL</span>` : ""].join("");
}

function renderHeader() {
  const unread = data.noticias.filter(n => !n.lida).length, pending = data.noticias.filter(n => n.pendente).length;
  const only = data.noticias.filter(n => n.onde === "central").length;
  $("header-summary").innerHTML = `<div class="header-kpi">${icon("mail", 15)}<b>${data.noticias.length}</b><span>notícias</span></div>`
    + `<div class="header-kpi good">${icon("dot", 15)}<b>${unread}</b><span>não lidas</span></div>`
    + `<div class="header-kpi warn">${icon("bolt", 15)}<b>${pending}</b><span>pedem resposta</span></div>`
    + `<div class="header-kpi">${icon("flag", 15)}<b>${only}</b><span>só na central</span></div>`;
  $("when").textContent = `${data.info.club || "—"} · ${dateBR(data.info.date)}`;
  $("footer").textContent = data.info.aviso || (data.sem_texto ? `Lido ao vivo da caixa de entrada do jogo. ${data.sem_texto} textos ainda por ler (chegam com o jogo parado).`
    : "Lido ao vivo da caixa de entrada do jogo. Notícia que pede resposta fica no jogo até o módulo dela saber responder.");
}

function renderSidebar() {
  const all = {id: "todas", nome: "Todas", total: data.noticias.length};
  $("modules").innerHTML = [all, ...data.modulos].map(m =>
    `<button class="chip ${ui.module === m.id ? "on" : ""}" data-module="${m.id}" type="button">${esc(m.nome)}<b>${m.total}</b></button>`).join("");
  $("filters").innerHTML = FILTERS.map(([id, label]) =>
    `<button class="chip ${ui.filter === id ? "on" : ""}" data-filter="${id}" type="button">${label}</button>`).join("");
  const list = visible();
  if (!list.some(n => n.serie === ui.selected)) ui.selected = list[0]?.serie ?? null;
  $("result-count").textContent = `${list.length} de ${data.noticias.length}`;
  const box = $("cards"), top = box.scrollTop;                        // a atualização a cada 6 s não pula a lista
  box.innerHTML = list.length ? list.map(n => `<button class="news-card ${n.lida ? "" : "unread"} ${n.serie === ui.selected ? "selected" : ""}" data-serie="${n.serie}" type="button">
      <i class="dot"></i><span class="card-name ${n.manchete ? "" : "missing"}">${esc(n.manchete || `${n.assunto} (${n.onde === "central" ? "sem texto" : "texto ainda não lido"})`)}</span>
      <span class="card-age">${dateBR(n.data)}</span><span class="card-role">${tags(n)}</span></button>`).join("")
    : `<div class="empty">Nenhuma notícia aqui.</div>`;
  box.scrollTop = top;
}

function renderReader() {
  const n = data.noticias.find(item => item.serie === ui.selected);
  if (!n) { $("workspace").innerHTML = `<div class="empty">Escolha uma notícia.</div>`; return; }
  const module = data.modulos.find(m => m.id === n.modulo);
  const body = (n.corpo || "").split(/\n+/).filter(Boolean).map(line => `<p>${esc(line)}</p>`).join("");
  const where = n.onde === "central" ? "Esta notícia saiu da caixa do jogo e existe só aqui."
    : n.pendente ? "Esta notícia pede uma escolha sua e fica na caixa do jogo: responda em <b>Técnico → Notícias</b>."
    : "Esta notícia ainda está também na caixa do jogo.";
  const press = n.modulo === "imprensa" ? ` <a href="/">Ver a pauta na Sala de Imprensa ›</a>`
    : n.modulo === "medico" ? ` <a href="/medico">Ver no Departamento Médico ›</a>` : "";
  $("workspace").innerHTML = `<header class="player-header news-header">
      <div class="news-icon">${icon(MODULE_ICON[n.modulo], 28)}</div>
      <div class="identity"><span class="screen-kicker">NEWS CENTRE / ${esc(module ? module.nome : "Geral")} / NOTÍCIA ${n.serie}</span>
        <h1>${esc(n.manchete || n.assunto)}</h1>
        <div class="bio">${icon("calendar", 11)} ${dateBR(n.data)} <i></i> ${esc(n.assunto)} <i></i> ${n.lida ? (n.onde === "central" ? "lida" : "lida no jogo") : "não lida"}</div>
        <div class="tag-row">${tags(n).replaceAll("mini-tag", "tag")}</div></div></header>
    <div class="news-body">
      <section class="panel"><h3>${icon("mail", 13)} Notícia</h3><div class="news-text">${body || `<p class="card-name missing">${n.onde === "central" ? "Esta notícia saiu do jogo antes de a Central guardar os textos: o texto se perdeu." : "O texto desta notícia ainda não foi lido do jogo. Ele chega em alguns segundos, com o jogo parado."}</p>`}</div></section>
      <section class="panel news-where ${n.pendente ? "pending" : ""}"><h3>${icon("info", 13)} Onde está</h3><p>${where}${press}</p></section>
    </div>`;
}

function render() { renderHeader(); renderSidebar(); renderReader(); }

async function load() {
  try {
    data = await (await fetch("/central", {cache: "no-store"})).json();
    render();
  } catch (error) {
    $("cards").innerHTML = `<div class="empty">Servidor não respondeu (${esc(error.message)}).</div>`;
  }
}

document.addEventListener("click", event => {
  const target = event.target.closest("[data-module],[data-filter],[data-serie]");
  if (!target || !data) return;
  if (target.dataset.module) ui.module = target.dataset.module;
  if (target.dataset.filter) ui.filter = target.dataset.filter;
  ui.selected = target.dataset.serie ? Number(target.dataset.serie) : null;
  const opened = data.noticias.find(n => n.serie === ui.selected);
  if (target.dataset.serie && opened?.onde === "central" && !opened.lida) {
    opened.lida = true;
    fetch("/central/lida", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({chave: opened.chave})});
  }
  render();
});
$("search").addEventListener("input", event => { ui.search = event.target.value; if (data) render(); });
setInterval(load, 6000);                                 // também escondida: o servidor sabe que a página está aberta
load();
