// Central de Notícias (§8.9): a caixa do jogo e as notícias tiradas dela, por módulo.
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const ui = {module: "todas", filter: "todas", search: "", selected: null};
let data = null;

const FILTERS = [["todas", "Todas"], ["nao_lidas", "Não lidas"], ["pendentes", "Pedem resposta"], ["central", "Só na Central"]];

function dateText(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

function visible() {
  const term = ui.search.trim().toLowerCase();
  return data.noticias.filter(n =>
    (ui.module === "todas" || n.modulo === ui.module)
    && (ui.filter === "todas" || (ui.filter === "nao_lidas" && !n.lida) || (ui.filter === "pendentes" && n.pendente) || (ui.filter === "central" && n.onde === "central"))
    && (!term || `${n.manchete || ""} ${n.assunto} ${n.categoria}`.toLowerCase().includes(term)));
}

function tags(n) {
  return [`<span class="tag">${esc(n.categoria)}</span>`,
    n.pendente ? `<span class="tag pending">pede resposta</span>` : "",
    n.respondida ? `<span class="tag done">respondida</span>` : "",
    n.onde === "central" ? `<span class="tag central">só na Central</span>` : ""].join("");
}

function renderModules() {
  const all = {id: "todas", nome: "Todas", total: data.noticias.length,
    nao_lidas: data.noticias.filter(n => !n.lida).length, pendentes: data.noticias.filter(n => n.pendente).length};
  $("#modules").innerHTML = [all, ...data.modulos].map(m => `<button class="module-btn ${ui.module === m.id ? "active" : ""}" data-module="${m.id}" type="button">
      <b>${esc(m.nome)}</b><span>${m.total}</span>
      <small>${m.nao_lidas} não lidas${m.pendentes ? ` · <em>${m.pendentes} pedem resposta</em>` : ""}</small></button>`).join("")
    + `<p class="module-note">Lesões vão para o Departamento Médico e transferências para o módulo de Transferências, quando eles existirem. Notícia que pede resposta fica no jogo até o módulo saber responder.</p>`;
}

function renderList() {
  const list = visible();
  if (!list.some(n => n.serie === ui.selected)) ui.selected = list[0]?.serie ?? null;
  $("#news-filters").innerHTML = FILTERS.map(([id, label]) => `<button class="filter-chip ${ui.filter === id ? "active" : ""}" data-filter="${id}" type="button">${label}</button>`).join("");
  const box = $("#news-list"), top = box.scrollTop;                // a atualização a cada 6 s não pula a lista
  box.innerHTML = list.length ? list.map(n => `<button class="news-row ${n.lida ? "" : "unread"} ${n.serie === ui.selected ? "active" : ""}" data-serie="${n.serie}" type="button">
      <i class="dot"></i><span class="row-title ${n.manchete ? "" : "missing"}">${esc(n.manchete || `${n.assunto} (texto ainda não lido)`)}</span><span class="row-date">${dateText(n.data)}</span>
      <span class="row-meta">${tags(n)}</span></button>`).join("") : `<div class="loading">Nenhuma notícia aqui.</div>`;
  box.scrollTop = top;
}

function renderReader() {
  const n = data.noticias.find(item => item.serie === ui.selected);
  if (!n) { $("#reader").innerHTML = `<div class="loading">Escolha uma notícia.</div>`; return; }
  const body = (n.corpo || "").split(/\n+/).filter(Boolean).map(line => `<p>${esc(line)}</p>`).join("");
  const where = n.onde === "central"
    ? "Esta notícia saiu da caixa do jogo e existe só aqui."
    : n.pendente ? `Esta notícia pede uma escolha sua e fica na caixa do jogo: responda em <b>Técnico → Notícias</b>.`
    : "Esta notícia ainda está também na caixa do jogo.";
  const press = n.modulo === "imprensa" ? ` <a href="/">Ver pauta na Sala de Imprensa ›</a>` : "";
  $("#reader").innerHTML = `<div class="reader-kicker">${tags(n)}<span>${esc(n.assunto)}</span></div>
    <h2>${esc(n.manchete || n.assunto)}</h2><div class="reader-date">${dateText(n.data)} · notícia ${n.serie}</div>
    <div class="reader-body">${body || `<p class="row-title missing">O texto desta notícia ainda não foi lido do jogo. Ele chega em alguns segundos, com o jogo parado.</p>`}</div>
    <p class="reader-note ${n.pendente ? "pending" : ""}">${where}${press}</p>`;
}

function render() {
  $("#club-name").textContent = data.info.club || "—";
  $("#current-date").textContent = dateText(data.info.date);
  const unread = data.noticias.filter(n => !n.lida).length, pending = data.noticias.filter(n => n.pendente).length;
  $("#header-summary").innerHTML = [[data.noticias.length, "notícias"], [unread, "não lidas"], [pending, "pedem resposta"],
    [data.noticias.filter(n => n.onde === "central").length, "só na central"]].map(([v, l]) => `<div class="header-kpi"><b>${v}</b><span>${l}</span></div>`).join("");
  $("#footer-stats").textContent = data.sem_texto ? `${data.sem_texto} textos ainda por ler` : "todos os textos lidos";
  $("#footer-mode").textContent = data.info.aviso || "Lê a caixa do FM06 aberto";
  renderModules(); renderList(); renderReader();
}

async function load() {
  try {
    data = await (await fetch("/central", {cache: "no-store"})).json();
    render();
  } catch (error) {
    $("#news-list").innerHTML = `<div class="loading">Servidor não respondeu (${esc(error.message)}).</div>`;
  }
}

document.addEventListener("click", event => {
  const target = event.target.closest("[data-module],[data-filter],[data-serie]");
  if (!target || !data) return;
  if (target.dataset.module) ui.module = target.dataset.module;
  if (target.dataset.filter) ui.filter = target.dataset.filter;
  if (target.dataset.serie) ui.selected = Number(target.dataset.serie);
  if (!target.dataset.serie) ui.selected = null;
  render();
});
$("#news-search").addEventListener("input", event => { ui.search = event.target.value; if (data) render(); });
setInterval(() => { if (!document.hidden) load(); }, 6000);
load();
