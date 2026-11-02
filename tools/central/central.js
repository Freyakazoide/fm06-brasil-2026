"use strict";

const GROUPS = {
  "Técnicos": [["Heading","Cabeceio"],["Corner","Cantos"],["Long Shots","Chutes longe"],["Crossing","Cruzamentos"],["Tackling","Desarme"],["Finishing","Finalização"],["Dribbling","Finta"],["Throwing","Lançam. longos"],["Set Pieces","Livres"],["Marking","Marcação"],["Penalty","Penáltis"],["Passing","Passe"],["First Touch","Primeiro toque"],["Technique","Técnica"]],
  "Mentais": [["Aggression","Agressividade"],["Anticipation","Antecipação"],["Bravery","Bravura"],["Composure","Compostura"],["Concentration","Concentração"],["Creativity","Criatividade"],["Decision","Decisões"],["Determination","Determinação"],["Influence","Influência"],["Flair","Instinto"],["Positioning","Posicionamento"],["Off the ball","Sem bola"],["Team work","Trabalho de equipe"],["Work rate","Índice de trabalho"]],
  "Físicos": [["Acceleration","Aceleração"],["Agility","Agilidade"],["Balance","Equilíbrio"],["Natural fit.","Condição natural"],["Strength","Força"],["Jumping","Impulsão"],["Stamina","Resistência"],["Pace","Velocidade"]],
};
const KEEPER = [["Handling","Jogo de mãos"],["Reflexes","Reflexos"],["One on one","Um contra um"],["Aer ability","Alcance aéreo"],["Cmd of area","Comando de área"],["Communiction","Comunicação"],["Kicking","Pontapé"],["Rushing out","Saídas"],["Punch","Socar"],["Eccentricity","Excentricidade"],["Long throws","Lançamentos"]];
const AXES = [
  ["Ataque",["Finishing","Off the ball","Composure","Dribbling"]], ["Criação",["Passing","Creativity","Technique","First Touch"]],
  ["Defesa",["Tackling","Marking","Positioning","Anticipation"]], ["Físico",["Pace","Acceleration","Strength","Stamina"]],
  ["Mental",["Decision","Determination","Work rate","Team work"]], ["Jogo aéreo",["Heading","Jumping","Bravery"]],
];
const AXES_GK = [["Reflexos",["Reflexes","One on one"]],["Mãos",["Handling","Punch"]],["Área",["Aer ability","Cmd of area","Rushing out"]],["Distribuição",["Kicking","Long throws"]],["Mental",["Decision","Concentration","Composure","Communiction"]],["Físico",["Agility","Jumping","Acceleration"]]];
const PITCH = {"GR":[50,92,"gk"],"DE":[16,74,"def"],"DC":[50,76,"def"],"DD":[84,74,"def"],"AE":[12,60,"def"],"AD":[88,60,"def"],"MD":[50,62,"mid"],"M E":[16,46,"mid"],"M C":[50,48,"mid"],"M D":[84,46,"mid"],"MA E":[18,30,"att"],"MA C":[50,32,"att"],"MA D":[82,30,"att"],"PL":[50,16,"att"]};
const LINE_COLOR = {gk:"var(--gk)",def:"var(--def)",mid:"var(--mid-line)",att:"var(--att)"};
const LINE_NAME = {gk:"GR",def:"DEF",mid:"MEI",att:"ATA"};
const TABS = [["overview","Visão geral","dashboard"],["development","Desenvolvimento","trend"],["performance","Desempenho","chart"],["position","Posição e função","pitch"],["health","Saúde","pulse"],["contract","Contrato e carreira","briefcase"],["staff","Comissão","users"]];
const ICONS = {
  dashboard: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="4"/><rect x="14" y="11" width="7" height="10"/><rect x="3" y="14" width="7" height="7"/>',
  trend: '<path d="M3 18l5-5 4 3 8-10"/><path d="M15 6h5v5"/>',
  chart: '<path d="M4 20V10m6 10V4m6 16v-7m5 7H2"/>',
  pitch: '<rect x="3" y="3" width="18" height="18" rx="1"/><path d="M3 12h18M12 3v18"/><circle cx="12" cy="12" r="3"/>',
  pulse: '<path d="M2 12h5l2-5 4 10 2-5h7"/>',
  briefcase: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V4h8v3M3 12h18M10 12v2h4v-2"/>',
  users: '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20v-2c0-3 2.5-5 6-5s6 2 6 5v2M15 14c3 0 5 1.5 5 4v2"/>',
  search: '<circle cx="10" cy="10" r="6"/><path d="M15 15l6 6"/>',
  player: '<circle cx="12" cy="7" r="3"/><path d="M7 21v-3c0-3 2-6 5-6s5 3 5 6v3M8 14l-3 3m11-3 3 3"/>',
  target: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3"/>',
  star: '<path d="M12 3l2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
  flag: '<path d="M5 22V3m0 2h12l-2 4 2 4H5"/>',
  bolt: '<path d="M13 2L5 14h7l-1 8 8-12h-7z"/>',
  shield: '<path d="M12 2l8 3v6c0 5-3.4 9-8 11-4.6-2-8-6-8-11V5z"/><path d="M9 12l2 2 4-5"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 2v6m10-6v6M3 10h18"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/>',
  foot: '<path d="M8 4c2 1 3 4 3 7 0 2 2 3 5 4 3 1 4 3 3 5-2 3-9 1-12-2-3-3-3-7-1-10 1-2 2-1 2 3z"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 8a8 8 0 0113 3M18 16A8 8 0 015 13"/>'
};
const METRIC_ICON = {"Fase":"flag","Função-alvo":"target","Nota na função":"star","Prioridade":"bolt","Valor pedido":"briefcase","Time atual":"shield","Número":"player","Fim do vínculo":"calendar","Moral":"pulse","Condição":"shield","Ritmo de jogo":"bolt","Cansaço":"pulse","Seleção":"flag","Gols seleção":"target","Sub-21":"users","Gols Sub-21":"target","Confiança habilidade":"shield","Confiança potencial":"shield","Habilidade":"star","Potencial":"star"};

let data = null;
const saved = JSON.parse(localStorage.getItem("central.ui") || "{}");
const ui = {selectedUid: saved.selectedUid ?? null, team: saved.team || "Todos", tab: saved.tab || "overview", academy: saved.academy ?? true};
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const short = j => j.apelido || j.nome.split(" ").pop();
const dateBR = value => value ? value.split("-").reverse().join("/") : "—";
const attrColor = v => v >= 16 ? "var(--top)" : v >= 12 ? "var(--high)" : v >= 8 ? "var(--mid)" : "var(--low)";
const roleRow = j => (j.adjunto?.mapa_posicoes || j.adjunto?.posicoes || []).find(r => r.pos === j.adjunto?.alvo) || j.adjunto?.posicoes?.[0] || {};
const line = j => (PITCH[j.adjunto?.alvo || j.posicoes[0]] || [0,0,"mid"])[2];
const persist = () => localStorage.setItem("central.ui", JSON.stringify(ui));

function icon(name, size=16) {
  const body=ICONS[name]||ICONS.info;
  return `<svg class="ui-icon" width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true">${body}</svg>`;
}
function heading(label, iconName="info", level=2) {
  return `<h${level} class="panel-title">${icon(iconName,15)}<span>${esc(label)}</span></h${level}>`;
}
function readinessLabel(value) {
  return value >= 72 ? "pronto para minutos" : value >= 60 ? "perto da transição" : value >= 45 ? "em desenvolvimento" : "base em formação";
}
// Sprites de pixel no estilo do mockup do motor 2D: quadro 16x20, âncora no centro do pé, sombra à
// parte, uniforme do clube recolorido em tempo de execução (camisa listrada, calção, meião) e o setor
// num anel no chão. Três quadros: parado e dois de corrida (animados por CSS no selecionado).
const KITS = {
  club: {p:"#f4f6f8", q:"#15171b", t:"#2fa04f", o:"#15171b", k:"#f4f6f8", stripes:true},
  keeper: {p:"#2f9a4a", q:"#2f9a4a", t:"#0f5d2a", o:"#1c3a26", k:"#2f9a4a", stripes:false},
};
const SKINS = ["#efb27e","#d79a6a","#b9774a","#8d5634","#6a3d26"], HAIRS = ["#1d140f","#3b2416","#5a3a22","#171719","#7a5530"];
const BODY = ["......hhhh......",".....hhhhhh.....",".....hssssh.....",".....seases.....",".....ssssss.....","......ssss......",
              "....KKKttKKK....","...KKKKKKKKKK...","...sKKKKKKKKs...","...sKKKKKKKKs...","...sKKKKKKKKs...","....KKKKKKKK....",
              ".....oooooo.....",".....oooooo....."];
const LEGS = [
  [".....ss..ss.....",".....kk..kk.....",".....kk..kk.....",".....kk..kk.....","....bbb..bbb...."],
  ["....ss....ss....","....kk....kk....","...kk......kk...","...kk......kk...","..bbb......bbb.."],
  ["......ssss......","......kkkk......","......kk.kk.....",".....kk...kk....",".....bb....bb..."],
];
function spriteFrame(rows, kit, skin, hair) {
  const colour = (c, x) => ({h:hair, s:skin, e:"#1b1410", a:"#1b1410", t:kit.t, o:kit.o, k:kit.k, b:"#0b0d10",
    K: kit.stripes && Math.floor(x / 2) % 2 ? kit.q : kit.p})[c];
  let out = "";
  rows.forEach((row, y) => { for (let x = 0; x < row.length; x++) { const c = row[x]; if (c !== ".") out += `<rect x="${x}" y="${y}" width="1" height="1" fill="${colour(c, x)}"/>`; } });
  return out;
}
function spriteSVG({sector="mid", uid=0, run=false, ring=false, arrow=false, size=null} = {}) {
  const kit = sector === "gk" ? KITS.keeper : KITS.club;
  const skin = SKINS[Math.abs(uid) % SKINS.length], hair = HAIRS[Math.abs(uid >> 3) % HAIRS.length];
  const frames = LEGS.map((legs, i) => `<g class="fr fr${i}">${spriteFrame([...BODY, ...legs], kit, skin, hair)}</g>`).join("");
  const ringSvg = `<ellipse cx="8" cy="19.6" rx="6.4" ry="2.1" fill="none" stroke="${ring ? "#ffda3d" : LINE_COLOR[sector]}" stroke-width=".9" ${ring ? 'class="sel-ring" stroke-dasharray="1.6 1"' : 'opacity=".9"'}/>`;
  const arrowSvg = arrow ? `<g class="indicator"><polygon points="5,-6 11,-6 8,-2" fill="#e8322b" stroke="#3a0605" stroke-width=".5"/></g>` : "";
  const dims = size ? `width="${size}" height="${size * 1.3}"` : "";
  return `<svg class="pixel-player ${run ? "run" : ""}" ${dims} viewBox="-1 -7 18 29" shape-rendering="crispEdges" aria-hidden="true"><ellipse cx="8" cy="19.6" rx="5" ry="1.4" fill="#010810" opacity=".55"/>${ringSvg}${frames}${arrowSvg}</svg>`;
}
function playerSprite(sector, uid=0, run=false) { return spriteSVG({sector, uid, run}); }
function pixelBall(size=14) {
  return `<svg class="pixel-ball" width="${size}" height="${size}" viewBox="0 0 8 8" shape-rendering="crispEdges" aria-hidden="true"><rect x="2" y="0" width="4" height="1" fill="#e9eef3"/><rect x="1" y="1" width="6" height="6" fill="#f6f9fb"/><rect x="0" y="2" width="8" height="4" fill="#f6f9fb"/><rect x="2" y="7" width="4" height="1" fill="#cfd8e0"/><rect x="3" y="3" width="2" height="2" fill="#15181c"/><rect x="1" y="1" width="1" height="1" fill="#15181c"/><rect x="6" y="1" width="1" height="1" fill="#15181c"/><rect x="1" y="6" width="1" height="1" fill="#15181c"/><rect x="6" y="6" width="1" height="1" fill="#15181c"/></svg>`;
}
const inner = svg => svg.replace(/^<svg[^>]*>/, "").replace(/<\/svg>$/, "");
// sprite dentro de um SVG de campo (viewBox 0..100): x, y são o ponto do pé
function pitchSprite(x, y, opts) {
  const w = opts.w || 9, h = w * 29 / 18;
  return `<svg class="pixel-player ${opts.run ? "run" : ""}" x="${(x - w / 2).toFixed(2)}" y="${(y - h * 26.6 / 29).toFixed(2)}" width="${w}" height="${h.toFixed(2)}" viewBox="-1 -7 18 29" overflow="visible" shape-rendering="crispEdges">${inner(spriteSVG(opts))}</svg>`;
}

function stars(value, big=false) {
  let out = "";
  for (let i=1; i<=5; i++) { const n=value-(i-1)*2; out += n>=2 ? "★" : n===1 ? '<span class="half">★</span>' : '<span class="off">★</span>'; }
  return `<span class="stars ${big?"big":""}" title="${value}/10">${out}</span>`;
}
function bar(value, max=100, colour="var(--positive)") { return `<div class="bar"><i style="width:${clamp(value/max*100,0,100)}%;background:${colour}"></i></div>`; }
function metric(label, value, note="") { return `<div class="metric"><span class="metric-label">${icon(METRIC_ICON[label]||"info",13)}${esc(label)}</span><b>${value}</b>${note?`<small>${esc(note)}</small>`:""}</div>`; }
function positionTag(pos) { const sector=(PITCH[pos]||[0,0,"mid"])[2]; return `<span class="tag position" style="--sector:${LINE_COLOR[sector]}"><i></i>${esc(pos)}</span>`; }

function pitch(j, full=false) {
  const entries = full ? Object.entries(j.familiaridades || {}).filter(([,v]) => v >= 5) : j.posicoes.map((p,i)=>[p,i?15:20]);
  const target = j.adjunto?.alvo, suggested = j.adjunto?.nova_posicao;
  const markers = entries.map(([p,familiarity]) => { const [x,y,sector]=PITCH[p]||[]; if(x===undefined)return "";
    const opacity=full ? clamp(familiarity/20,.35,1) : 1;
    const centre=x>34&&x<66, labelX=centre?x:x+(x>60?-7.5:7.5), labelY=centre?y+7.2:y+1.8, anchor=centre?"middle":x>60?"end":"start";
    return `<g class="pitch-marker" opacity="${opacity}">${pitchSprite(x, y + 2, {sector, uid:j.uid, ring:p===target, w: full ? 11 : 12})}<text x="${labelX}" y="${labelY}" text-anchor="${anchor}">${esc(p)}${full?` · ${familiarity}`:""}</text></g>`;
  }).join("");
  const sug = PITCH[suggested];
  const ghost = sug && !entries.some(([p]) => p === suggested) ? `<g class="pitch-marker suggested">${pitchSprite(sug[0], sug[1] + 2, {sector:sug[2], uid:j.uid, ring:true, arrow:true, w: full ? 11 : 12})}<text x="${sug[0] < 30 ? sug[0] - 5 : sug[0] > 70 ? sug[0] + 5 : sug[0]}" y="${sug[1] + 9}" text-anchor="${sug[0] < 30 ? "start" : sug[0] > 70 ? "end" : "middle"}">${esc(suggested)} · sugerida</text></g>` : "";
  return `<svg class="pitch-svg" viewBox="0 0 100 104" aria-label="Mapa de posições">${pitchBase()}${markers}${ghost}</svg>`;
}
let pitchSeq = 0;
function pitchBase() {
  const id = `pitch-stripes-${++pitchSeq}`;
  return `<defs><pattern id="${id}" width="100" height="13" patternUnits="userSpaceOnUse"><rect width="100" height="6.5" fill="#1d6a37"/><rect y="6.5" width="100" height="6.5" fill="#22773e"/></pattern></defs><rect x="2" y="2" width="96" height="100" rx="1.5" fill="url(#${id})" stroke="#0d3a1e" stroke-width="1"/><g class="pitch-lines" fill="none"><rect x="4" y="4" width="92" height="96"/><line x1="4" y1="52" x2="96" y2="52"/><circle cx="50" cy="52" r="10"/><circle cx="50" cy="52" r=".8" fill="currentColor"/><rect x="28" y="84" width="44" height="16"/><rect x="38" y="94" width="24" height="6"/><rect x="28" y="4" width="44" height="16"/><rect x="38" y="4" width="24" height="6"/></g>`;
}
// campo com os jovens: cada um na posição-alvo do adjunto (escala do mockup "on-pitch preview")
function squadPitch(players) {
  const slots = {};
  const top = [...players].sort((a,b)=>b.analise.prioridade-a.analise.prioridade)[0];
  const sprites = players.map(j => {
    const pos = j.adjunto?.alvo || j.posicoes[0]; const base = PITCH[pos]; if (!base) return "";
    const n = (slots[pos] = (slots[pos] || 0) + 1) - 1, dx = [0, -14, 14, -28, 28][n] ?? n * 5;
    const x = clamp(base[0] + dx, 7, 93), y = base[1] + 3, isTop = top && j.uid === top.uid;
    return `<g class="squad-sprite" data-open="${j.uid}"><title>${esc(short(j))} · ${esc(pos)} · prioridade ${j.analise.prioridade}</title>${pitchSprite(x, y, {sector:base[2], uid:j.uid, run:isTop, ring:isTop, arrow:isTop, w: 13})}<text x="${x}" y="${y + 6.2 + (n % 2 ? 4.6 : 0)}" text-anchor="middle">${esc(short(j).slice(0, 10))}</text></g>`;
  }).join("");
  return `<svg class="pitch-svg squad" viewBox="0 0 100 104" aria-label="Campo da base">${pitchBase()}${sprites}<svg x="57" y="45" width="3.6" height="3.6" viewBox="0 0 8 8" shape-rendering="crispEdges">${inner(pixelBall(8))}</svg></svg>`;
}
function radar(j) {
  const axes=j.posicoes.includes("GR")?AXES_GK:AXES, n=axes.length, R=78, C=105;
  const avg=(src,keys)=>keys.reduce((s,k)=>s+(src[k]??0),0)/keys.length;
  const pt=(i,v)=>{const a=-Math.PI/2+2*Math.PI*i/n;return[C+Math.cos(a)*R*v/20,C+Math.sin(a)*R*v/20]};
  const poly=vals=>vals.map((v,i)=>pt(i,v).map(x=>x.toFixed(1)).join(",")).join(" ");
  const rings=[5,10,15,20].map(v=>`<polygon class="grid" points="${poly(Array(n).fill(v))}"/>`).join("");
  const spokes=axes.map((_,i)=>`<line class="grid" x1="${C}" y1="${C}" x2="${pt(i,20)[0]}" y2="${pt(i,20)[1]}"/>`).join("");
  const labels=axes.map(([name],i)=>{const[x,y]=pt(i,24.3);return`<text x="${x}" y="${y+3}" text-anchor="middle">${name}</text>`}).join("");
  const now=axes.map(([,keys])=>avg(j.atributos,keys)), future=axes.map(([,keys])=>avg(j.futuro,keys));
  return `<svg viewBox="-24 -4 258 218">${rings}${spokes}<polygon class="future" points="${poly(future)}"/><polygon class="now" points="${poly(now)}"/>${labels}</svg><div class="legend"><span><i style="background:var(--positive)"></i>agora</span><span><i style="background:transparent;border:1px dashed var(--accent)"></i>projeção da comissão</span></div>`;
}
function historyChart(points) {
  if(points.length<2)return '<div class="empty">Primeira observação guardada. Avance o jogo e atualize novamente para formar a série.</div>';
  const W=420,H=190,L=28,B=22,n=points.length,x=i=>L+(W-L-8)*i/(n-1),y=v=>8+(H-B-8)*(1-v/20);
  const path=(key,col,scale=1)=>`<polyline fill="none" stroke="${col}" stroke-width="2.2" stroke-linejoin="round" points="${points.map((p,i)=>`${x(i).toFixed(1)},${y((p[key]??0)*scale).toFixed(1)}`).join(" ")}"/>`;
  const ticks=[0,5,10,15,20].map(v=>`<line class="axis" x1="${L}" x2="${W}" y1="${y(v)}" y2="${y(v)}"/><text x="3" y="${y(v)+3}">${v}</text>`).join("");
  const dates=[0,n-1].map(i=>`<text x="${i?W-2:L}" y="${H-4}" text-anchor="${i?"end":"start"}">${dateBR(points[i].data)}</text>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}">${ticks}${dates}${path("tec","#59bd78")}${path("men","#5b9ed5")}${path("fis","#e5a94a")}${path("hab","#f0f4f5",2)}</svg><div class="legend"><span><i style="background:#59bd78"></i>técnicos</span><span><i style="background:#5b9ed5"></i>mentais</span><span><i style="background:#e5a94a"></i>físicos</span><span><i style="background:#f0f4f5"></i>habilidade</span></div>`;
}

function visiblePlayers() {
  const query=document.getElementById("search").value.trim().toLocaleLowerCase("pt-BR");
  const sort=document.getElementById("sort").value;
  const keys={prioridade:j=>[-j.analise.prioridade,-j.pot],prontidao:j=>[-j.analise.prontidao,-j.pot],pot:j=>[-j.pot,-j.hab],hab:j=>[-j.hab,-j.pot],idade:j=>[j.idade,-j.pot],nome:j=>[short(j).toLocaleLowerCase("pt-BR")]}[sort];
  return data.jovens.filter(j=>ui.team==="Todos"||j.time===ui.team).filter(j=>!query||(j.nome+" "+j.apelido).toLocaleLowerCase("pt-BR").includes(query)).sort((a,b)=>{const ka=keys(a),kb=keys(b);for(let i=0;i<ka.length;i++){if(ka[i]!==kb[i])return ka[i]<kb[i]?-1:1}return 0});
}
function renderList() {
  const teams=["Todos",...new Set(data.jovens.map(j=>j.time))];
  document.getElementById("filters").innerHTML=teams.map(t=>`<button class="chip ${t===ui.team?"on":""}" data-team="${esc(t)}">${esc(t)} · ${t==="Todos"?data.jovens.length:data.jovens.filter(j=>j.time===t).length}</button>`).join("");
  const list=visiblePlayers(); document.getElementById("result-count").textContent=`${list.length} jogador${list.length===1?"":"es"}`;
  document.getElementById("cards").innerHTML=list.length?list.map(j=>{const sector=line(j),ready=j.analise.prontidao;return `<button class="player-card ${!ui.academy&&ui.selectedUid===j.uid?"selected":""}" data-uid="${j.uid}" style="--sector:${LINE_COLOR[sector]}"><span class="player-sprite">${playerSprite(sector,j.uid,!ui.academy&&ui.selectedUid===j.uid)}</span><span class="card-name">${esc(short(j))}</span><span class="card-age">${j.idade} ANOS</span><span class="card-role"><i></i>${esc(j.analise.funcao_alvo||j.adjunto?.alvo||LINE_NAME[sector])}</span><span class="card-score"><b>${j.analise.prioridade}</b><small>PRIO</small></span><span class="card-progress"><small>${esc(readinessLabel(ready))}</small><span><i style="width:${ready}%"></i></span><b>${ready}%</b></span></button>`}).join(""):'<div class="empty">Nenhum jovem neste filtro.</div>';
}
function renderBrandBall() { const mark=document.querySelector(".fm-mark"); if(mark&&!mark.querySelector(".pixel-ball"))mark.insertAdjacentHTML("beforeend",pixelBall(18)); }
function renderHeaderSummary() {
  renderBrandBall();
  const priority=data.jovens.filter(j=>j.analise.fase==="Prioridade"||j.analise.prioridade>=60).length;
  const ready=data.jovens.filter(j=>j.analise.fase==="Pronto para minutos"||j.analise.prontidao>=70).length;
  document.getElementById("header-summary").innerHTML=`<div class="header-kpi">${icon("users",15)}<b>${data.jovens.length}</b><span>jovens</span></div><div class="header-kpi warn">${icon("bolt",15)}<b>${priority}</b><span>prioridades</span></div><div class="header-kpi good">${icon("shield",15)}<b>${ready}</b><span>prontos</span></div>`;
}
function academyScatter(players) {
  const W=500,H=235,L=34,B=25,x=v=>L+(W-L-12)*v/10,y=v=>8+(H-B-8)*(1-v/10);
  const grid=[0,2,4,6,8,10].map(v=>`<line class="axis" x1="${x(v)}" x2="${x(v)}" y1="8" y2="${H-B}"/><line class="axis" x1="${L}" x2="${W-12}" y1="${y(v)}" y2="${y(v)}"/><text x="${x(v)}" y="${H-7}" text-anchor="middle">${v}</text><text x="4" y="${y(v)+3}">${v}</text>`).join("");
  const dots=players.map(j=>{const r=3.1+clamp((19-j.idade)*.28,0,1.4),cx=x(j.hab),cy=y(j.pot);return `<g class="scatter-point"><circle class="scatter-halo" cx="${cx}" cy="${cy}" r="${(r+2).toFixed(1)}"/><circle cx="${cx}" cy="${cy}" r="${r.toFixed(1)}" fill="${LINE_COLOR[line(j)]}"/><circle cx="${cx-1}" cy="${cy-1}" r=".8" fill="#fff" opacity=".8"/><title>${esc(short(j))}: hab. ${j.hab}, pot. ${j.pot}</title></g>`}).join("");
  return `<svg class="talent-map" viewBox="0 0 ${W} ${H}"><rect class="plot-bg" x="${L}" y="8" width="${W-L-12}" height="${H-B-8}" rx="2"/>${grid}${dots}<text class="axis-label" x="${W/2}" y="${H-1}" text-anchor="middle">HABILIDADE DA COMISSÃO</text><text class="axis-label" x="${L+5}" y="20">POTENCIAL</text></svg>`;
}
function renderAcademy() {
  const players=[...data.jovens], phases={}; players.forEach(j=>phases[j.analise.fase]=(phases[j.analise.fase]||0)+1);
  const avg=Math.round(players.reduce((s,j)=>s+j.analise.prontidao,0)/(players.length||1)); const top=[...players].sort((a,b)=>b.analise.prioridade-a.analise.prioridade).slice(0,6);
  const maxPhase=Math.max(1,...Object.values(phases));
  document.getElementById("workspace").innerHTML=`<div class="academy"><div class="academy-hero"><div><span class="screen-kicker">YOUTH ANALYTICS / CLUB PIPELINE</span><h1>Visão da base</h1><p>Decisões prioritárias e o caminho até o time principal.</p></div><span class="status-badge">${icon("calendar",12)} ATUALIZADO ${dateBR(data.info.data)}</span></div>
    <div class="kpi-grid"><div class="kpi"><span class="kpi-icon">${icon("users",19)}</span><div><b>${players.length}</b><span>jovens monitorados</span><small>Principal, B e Sub-20</small></div></div><div class="kpi"><span class="kpi-icon">${icon("star",19)}</span><div><b>${players.filter(j=>j.pot>=7).length}</b><span>potencial alto</span><small>7/10 ou mais na comissão</small></div></div><div class="kpi"><span class="kpi-icon">${icon("shield",19)}</span><div><b>${avg}</b><span>prontidão média</span><small>indicador interno da Central</small></div></div><div class="kpi"><span class="kpi-icon">${icon("target",19)}</span><div><b>${players.filter(j=>j.adjunto?.nova_posicao).length}</b><span>mudanças sugeridas</span><small>nova posição a avaliar</small></div></div></div>
    <div class="grid-3 academy-top"><section class="panel squad-panel">${heading("Campo da base","pitch")}${squadPitch(players)}<div class="legend"><span><i class="legend-ring"></i>maior prioridade</span><span>clique para abrir</span></div></section><section class="panel">${heading("Fila de decisões","bolt")}<div class="decision-list">${top.map(j=>`<button class="decision" data-open="${j.uid}"><span class="decision-sprite">${playerSprite(line(j), j.uid)}</span><span class="decision-rank">${String(top.indexOf(j)+1).padStart(2,"0")}</span><b>${esc(short(j))}</b><span>${esc(j.analise.fase)} · ${esc(j.analise.funcao_alvo)}</span><strong>${j.analise.prioridade}<small>PRIO</small></strong></button>`).join("")}</div></section>
    <section class="panel chart">${heading("Mapa de talento","target")}${academyScatter(players)}<div class="legend"><span>${icon("info",11)} marcador menor = jogador mais velho</span><span class="sector-key"><i style="--key:var(--def)"></i> setor por cor</span></div></section></div>
    <div class="grid-2"><section class="panel">${heading("Pipeline de desenvolvimento","trend")}${Object.entries(phases).sort((a,b)=>b[1]-a[1]).map(([name,count])=>`<div class="phase-row"><span>${esc(name)}</span>${bar(count,maxPhase,name==="Pronto para minutos"?"var(--positive)":"var(--accent)")}<b>${count}</b></div>`).join("")}</section>
    <section class="panel">${heading("Leitura rápida","info")}<div class="alerts"><div class="alert oportunidade">${icon("trend",16)}<div><small>Oportunidade</small>${players.filter(j=>j.pot-j.hab>=3).length} jovens têm grande distância entre habilidade e potencial percebido.</div></div><div class="alert">${icon("bolt",16)}<div><small>Decisão</small>${players.filter(j=>j.idade>=18&&j.time!=="Principal"&&j.analise.prontidao>=60).length} jogadores mais velhos estão perto de precisar de nível competitivo maior.</div></div><div class="alert risco">${icon("flag",16)}<div><small>Atenção</small>${players.filter(j=>j.moral<=8).length} jogadores aparecem com moral baixa.</div></div></div></section></div></div>`;
}

function playerHeader(j) {
  const name=short(j).toUpperCase();
  const ready=j.analise.prontidao;
  return `<header class="player-header"><div class="shirt"><span class="shirt-frame"></span><img src="/camisa.png" alt=""><svg viewBox="0 0 210 210"><path id="name-arc" d="M 48 72 Q 105 55 162 72" fill="none"/><text><textPath href="#name-arc" startOffset="50%" text-anchor="middle">${esc(name)}</textPath></text>${j.numero?`<text class="shirt-number" x="105" y="134" text-anchor="middle">${j.numero}</text>`:""}</svg></div><div class="identity"><span class="screen-kicker">PLAYER DEVELOPMENT / UID ${j.uid}</span><h1>${esc(short(j))}</h1><div class="bio">${esc(j.nome)} <i></i> ${j.idade} anos <i></i> ${esc(j.time)} <i></i> ${j.altura} cm · ${j.peso} kg</div><div class="tag-row">${j.posicoes.map(positionTag).join("")}<span class="tag">${icon("foot",11)} pé ${esc(j.pe_preferido)}</span><span class="tag phase-tag">${icon("flag",11)} ${esc(j.analise.fase)}</span></div><div class="headline-metrics"><div class="star-metric">${icon("star",15)}<b>${stars(j.hab,true)}</b><span>habilidade</span></div><div class="star-metric">${icon("star",15)}<b>${stars(j.pot,true)}</b><span>potencial</span></div><div class="readiness-metric" title="${esc(j.analise.metodologia)}">${icon("shield",15)}<b>${ready}<small>/100</small></b><span>prontidão · ${esc(readinessLabel(ready))}</span><span class="head-readybar"><i style="width:${ready}%"></i></span><i class="readiness-help">?</i></div></div></div><div class="pitch-card"><span class="pitch-card-title">${icon("pitch",12)} MAPA POSICIONAL</span><div class="mini-pitch">${pitch(j)}</div></div></header>`;
}
function renderTabs(j) {
  const nav=`<nav class="tabs" role="tablist">${TABS.map(([id,label,tabIcon])=>`<button class="tab ${ui.tab===id?"active":""}" data-tab="${id}" role="tab" aria-selected="${ui.tab===id}">${icon(tabIcon,14)}<span>${label}</span></button>`).join("")}</nav>`;
  return `<div class="sticky-head">${playerHeader(j)}${nav}</div><div class="tab-content">${renderTab(j)}</div>`;
}
function verdict(j) {
  if(j.analise.fase==="Pronto para minutos")return "A comissão entende que ele já pode receber minutos controlados em nível mais alto.";
  if(j.analise.fase==="Prioridade")return "Potencial alto e janela de desenvolvimento apertando: precisa de uma decisão de carreira.";
  if(j.analise.fase==="Transição")return "Está entre formação e futebol adulto; treino e nível competitivo precisam andar juntos.";
  return "Ainda está em formação. O foco deve ser evolução consistente, sem apressar a promoção.";
}
function bestGrowth(j) {
  const names=Object.fromEntries([...GROUPS.Técnicos,...GROUPS.Mentais,...GROUPS.Físicos,...KEEPER]);
  return Object.entries(j.futuro).filter(([k])=>names[k]).map(([k,f])=>[names[k],j.atributos[k]??0,f]).sort((a,b)=>(b[2]-b[1])-(a[2]-a[1])).slice(0,5);
}
function alerts(j) { const list=j.analise.alertas||[]; return list.length?`<div class="alerts">${list.map(a=>`<div class="alert ${esc(a.nivel)}"><small>${esc(a.nivel)}</small>${esc(a.texto)}</div>`).join("")}</div>`:'<div class="alert oportunidade"><small>Sem urgência</small>Nenhum alerta automático para esta atualização.</div>'; }
function readinessBreakdown(j) {
  const role=roleRow(j), ability=j.hab*10, fit=Math.round((role.nota||0)*5), morale=Math.round(clamp(j.moral,0,20)*5);
  return `<div class="readiness-breakdown"><div class="readiness-copy">${icon("shield",18)}<div><b>O que significa ${j.analise.prontidao}/100?</b><span>É um indicador da Central para comparar proximidade do futebol principal — não é um atributo oculto do FM.</span></div></div><div class="readiness-parts"><div><span>Habilidade <b>60%</b></span>${bar(ability,100,"var(--info)")}<small>${ability}/100 na opinião da comissão</small></div><div><span>Encaixe na função <b>30%</b></span>${bar(fit,100,"var(--positive)")}<small>${fit}/100 como ${esc(j.analise.funcao_alvo)}</small></div><div><span>Moral <b>10%</b></span>${bar(morale,100,"var(--accent)")}<small>${morale}/100 nesta atualização</small></div></div></div>`;
}
function trainingPlan(j) {
  const plans=j.adjunto?.treino||[], total=plans.reduce((sum,p)=>sum+p.atributos.length,0);
  if(!plans.length)return '<div class="empty">Nenhuma lacuna urgente.</div>';
  return `<div class="module-summary"><span>${icon("calendar",16)}<b>Próximos 90 dias</b></span><span><b>${plans.length}</b> blocos de treino</span><span><b>${total}</b> atributos trabalhados</span></div><div class="training-plan">${plans.map((plan,index)=>`<article class="training-card"><span class="training-icon">${icon(["bolt","target","trend"][index%3],16)}</span><div class="training-head"><b>${esc(plan.categoria)}</b><small>FOCO ${String(index+1).padStart(2,"0")}</small></div><div class="training-attrs">${plan.atributos.map(([name,now,goal])=>`<div class="training-attr"><span>${esc(name)}</span><div class="dual-track"><i class="goal" style="width:${goal*5}%"></i><i style="width:${now*5}%"></i></div><b>${now}<em>→ ${goal}</em></b></div>`).join("")}</div></article>`).join("")}</div>`;
}
function growthPanel(j) {
  const growth=bestGrowth(j), total=growth.reduce((sum,[,now,future])=>sum+future-now,0);
  return `<div class="module-summary"><span>${icon("trend",16)}<b>Margem projetada</b></span><span><b>+${total}</b> pontos nos 5 maiores ganhos</span></div><div class="growth-list">${growth.map(([name,now,future],index)=>`<article class="growth-item"><span class="growth-rank">${String(index+1).padStart(2,"0")}</span><div><b>${esc(name)}</b><small>${future-now} ponto${future-now===1?"":"s"} de margem</small></div><div class="growth-track"><i class="future" style="width:${future*5}%"></i><i style="width:${now*5}%"></i></div><span class="growth-values"><small>${now} AGORA</small><b>→ ${future}</b></span></article>`).join("")}</div>`;
}
function overviewTab(j) {
  const role=roleRow(j), points=data.historico?.[String(j.uid)]||[];
  return `<div class="metric-grid">${metric("Fase",esc(j.analise.fase),"plano de carreira")}${metric("Função-alvo",esc(j.analise.funcao_alvo),j.adjunto?.alvo||"")}${metric("Nota na função",role.nota?.toFixed(1)??"—",role.futuro?`projeção ${role.futuro.toFixed(1)}`:"")}${metric("Prioridade",`${j.analise.prioridade}/100`,"ordena a fila de decisões")}</div>${readinessBreakdown(j)}<div class="callout"><b>Parecer executivo</b><br>${esc(verdict(j))}</div><div class="grid-3"><section class="panel radar">${heading("Perfil de atributos","chart",3)}${radar(j)}</section><section class="panel chart">${heading("Evolução observada","trend",3)}${historyChart(points)}</section><section class="panel">${heading("Alertas e oportunidades","flag",3)}${alerts(j)}</section></div><div class="grid-2 development-modules"><section class="panel">${heading("Plano recomendado","target",3)}${trainingPlan(j)}</section><section class="panel">${heading("Onde pode crescer mais","trend",3)}${growthPanel(j)}</section></div>`;
}
function attributes(j) {
  const groups=j.posicoes.includes("GR")?{"Goleiro":KEEPER,"Mentais":GROUPS.Mentais,"Físicos":GROUPS.Físicos}:GROUPS;
  return `<div class="attribute-groups">${Object.entries(groups).map(([title,attrs])=>`<section class="panel"><h3>${title}</h3>${attrs.map(([key,label])=>{const v=j.atributos[key]??0,f=j.futuro[key]??v;return`<div class="attr"><span>${label}</span><div class="compare-bar"><i class="future" style="width:${f*5}%;background:${attrColor(f)}"></i><i style="width:${v*5}%;background:${attrColor(v)}"></i></div><b>${v}${f>v?` <em>→${f}</em>`:""}</b></div>`}).join("")}</section>`).join("")}</div>`;
}
function developmentTab(j) {
  const points=data.historico?.[String(j.uid)]||[];
  return `<div class="grid-2" style="margin-top:0"><section class="panel chart"><h2>Linha de evolução</h2>${historyChart(points)}</section><section class="panel"><h2>Foco dos próximos 90 dias</h2><div class="focus-list">${(j.adjunto?.treino||[]).map(t=>`<div class="focus-item"><b>${esc(t.categoria)}</b><p>${t.atributos.map(([n,v,g])=>`${esc(n)} ${v} → ${g}`).join(" · ")}</p></div>`).join("")}</div></section></div><div class="callout">A área sombreada nos atributos é projeção da comissão, não garantia de evolução.</div><div style="margin-top:12px">${attributes(j)}</div>`;
}
function performanceTab(j) {
  const international=j.internacional||{};
  return `<div class="metric-grid">${metric("Seleção",international.jogos??0,"jogos")}${metric("Gols seleção",international.gols??0,"carreira internacional")}${metric("Sub-21",international.sub21_jogos??0,"jogos")}${metric("Gols Sub-21",international.sub21_gols??0,"carreira internacional")}</div><div class="unavailable" style="margin-top:12px"><b>Estatísticas da temporada ainda não são lidas com segurança</b>Partidas, minutos, gols pelo clube, assistências, nota e xG não aparecem como zero: permanecem indisponíveis até o bloco vivo de estatísticas ser mapeado.</div>`;
}
function familiarityLabel(v){return v>=15?"Natural":v>=12?"Competente":v>=8?"Familiar":v>=5?"Aprendendo":"Inadequado"}
function positionTab(j) {
  const rows=j.adjunto?.mapa_posicoes||j.adjunto?.posicoes||[];
  const target=rows.find(r=>r.pos===j.adjunto?.alvo)||rows[0]||{}, strengths=j.adjunto?.pontos_fortes||[], gaps=j.adjunto?.pontos_fracos||[];
  return `<div class="position-layout"><section class="panel position-map-panel">${heading("Mapa completo de posições","pitch")}<div class="position-map-shell"><div class="mini-pitch">${pitch(j,true)}</div></div><div class="position-legend"><span><i class="natural"></i>15–20 natural</span><span><i class="competent"></i>12–14 competente</span><span><i class="familiar"></i>8–11 familiar</span><span><i class="learning"></i>5–7 aprendendo</span></div></section><section class="panel diagnosis-panel">${heading("Diagnóstico da posição","target")}<div class="diagnosis-kpis"><div>${icon("target",14)}<span>FUNÇÃO-ALVO</span><b>${esc(target.nome||"—")}</b><small>${esc(target.pos||"—")}</small></div><div>${icon("foot",14)}<span>PÉ PREFERIDO</span><b>${esc(j.pe_preferido)}</b><small>perfil técnico</small></div><div>${icon("chart",14)}<span>ENCAIXE ATUAL</span><b>${target.nota?.toFixed(1)??"—"}<small>/20</small></b><small>${familiarityLabel(target.familiaridade||0)}</small></div><div>${icon("trend",14)}<span>PROJEÇÃO</span><b>${target.futuro?.toFixed(1)??"—"}<small>/20</small></b><small>${target.futuro&&target.nota?`+${(target.futuro-target.nota).toFixed(1)} de margem`:"—"}</small></div></div><div class="diagnosis-verdict">${icon("info",17)}<span>${esc(j.adjunto?.sugestao||"Sem parecer.")}</span></div><div class="diagnosis-traits"><div><h4>${icon("shield",13)} PONTOS FORTES</h4>${strengths.map(([name,value])=>`<span><b>${esc(name)}</b><i style="width:${value*5}%"></i><strong>${value}</strong></span>`).join("")||"—"}</div><div class="gaps"><h4>${icon("bolt",13)} LACUNAS PRIORITÁRIAS</h4>${gaps.map(([name,value])=>`<span><b>${esc(name)}</b><i style="width:${value*5}%"></i><strong>${value}</strong></span>`).join("")||"—"}</div></div></section></div><section class="panel role-ranking-panel">${heading("Ranking de encaixe","chart")}<div class="ranking-head"><span>#</span><span>POSIÇÃO E PERFIL</span><span>FAMILIARIDADE</span><span>ENCAIXE ATUAL → PROJEÇÃO</span><span>NOTA</span></div><div class="role-ranking">${rows.map((r,index)=>{const sector=(PITCH[r.pos]||[0,0,"mid"])[2],fit=clamp(r.nota/20*100,0,100),future=clamp(r.futuro/20*100,0,100);return `<div class="role-rank-row ${r.pos===j.adjunto?.alvo?"target":""}"><span class="rank-number">${String(index+1).padStart(2,"0")}</span><div class="rank-role"><span class="rank-pos" style="--sector:${LINE_COLOR[sector]}"><i></i>${esc(r.pos)}</span><div><b>${esc(r.nome)}</b>${r.pos===j.adjunto?.nova_posicao?'<small class="suggested-badge">SUGERIDA</small>':""}</div></div><div class="rank-familiarity"><b>${r.familiaridade}</b><span>${familiarityLabel(r.familiaridade)}</span></div><div class="rank-track"><i class="future" style="width:${future}%"></i><i style="width:${fit}%"></i></div><div class="rank-score"><span>${r.nota.toFixed(1)}</span><b>→ ${r.futuro.toFixed(1)}</b></div></div>`}).join("")}</div></section>`;
}
function pct(raw) { return raw > 0 && raw <= 10000 ? Math.round(raw / 100) : null; }
function signed16(raw) { return raw > 32767 ? raw - 65536 : raw; }
function healthTab(j) {
  const moral=clamp(j.moral,0,20), cond=pct(j.condicao_raw), sharp=pct(j.ritmo_raw), tired=signed16(j.cansaco_raw);
  const gauge=(label,value,colour)=>`<div class="gauge"><span>${label}</span>${bar(value??0,100,colour)}<b>${value===null?"—":`${value}%`}</b></div>`;
  return `<div class="metric-grid">${metric("Moral",`${moral}/20`,moral>=15?"alta":moral>=10?"estável":"baixa")}${metric("Condição",cond===null?j.condicao_raw:`≈ ${cond}%`,"0–10000 no jogo ÷ 100")}${metric("Ritmo de jogo",sharp===null?j.ritmo_raw:`≈ ${sharp}%`,"0–10000 no jogo ÷ 100")}${metric("Cansaço",tired,tired<0?"descansado":"acumulado")}</div><div class="grid-2"><section class="panel">${heading("Disponibilidade","pulse",3)}${gauge("Condição física",cond,cond>=85?"var(--positive)":cond>=70?"var(--warning)":"var(--danger)")}${gauge("Ritmo de jogo",sharp,"var(--info)")}${gauge("Moral",moral*5,moral>=10?"var(--positive)":"var(--danger)")}<p class="raw-note">Condição e ritmo usam a escala interna 0–10000 do FM (10000 = 100%). A conversão ÷100 ainda será conferida contra a tela do jogo.</p></section><section class="panel">${heading("Leitura da comissão","info",3)}<div class="callout" style="margin-top:0">${cond===null?"Sem leitura física nesta atualização.":cond>=90?"Fisicamente inteiro: pode treinar forte e jogar.":cond>=75?"Condição boa, mas vale controlar a carga desta semana.":"Condição baixa: priorize recuperação antes de minutos."}</div></section></div>`;
}
function monthsUntil(iso) { if (!iso || !data?.info?.data) return null; const [y1,m1]=data.info.data.split("-").map(Number), [y2,m2]=iso.split("-").map(Number); return (y2-y1)*12+(m2-m1); }
function contractTab(j) {
  const left=monthsUntil(j.contrato_fim), money=v=>`R$ ${Number(v||0).toLocaleString("pt-BR")}`;
  const status=j.contrato_fim===null?"sem data de fim (contrato de base)":left<=6?"vence em breve — decidir renovação":left<=12?"último ano de vínculo":"vínculo tranquilo";
  return `<div class="metric-grid">${metric("Número",j.numero??"—",j.numero?`camisa no ${j.time}`:"sem número no time")}${metric("Salário",`≈ ${money(j.salario_mes)}`,"por mês (calibrado na ficha do jogo)")}${metric("Fim do vínculo",j.contrato_fim?dateBR(j.contrato_fim):"—",j.contrato_fim?`${left} meses restantes`:"sem data de fim")}${metric("Valor pedido",j.valor_pedido_raw>=4294967295||!j.valor_pedido_raw?"—":j.valor_pedido_raw.toLocaleString("pt-BR"),j.valor_pedido_raw>=4294967295?"clube não definiu":"unidade interna do jogo")}</div>
  <div class="grid-2"><section class="panel">${heading("Situação do contrato","briefcase",3)}<div class="contract-line"><span>Início</span><b>${dateBR(j.contrato_inicio)}</b></div><div class="contract-line"><span>Fim</span><b>${j.contrato_fim?dateBR(j.contrato_fim):"sem data"}</b></div><div class="contract-line"><span>Time</span><b>${esc(j.time)}</b></div>${j.contrato_fim?`<div class="contract-track">${bar(clamp(100-(left/36)*100,0,100),100,left<=6?"var(--danger)":left<=12?"var(--warning)":"var(--positive)")}</div>`:""}<div class="callout" style="margin-top:10px">${esc(status[0].toUpperCase()+status.slice(1))}.</div></section>
  <section class="panel">${heading("Leitura da comissão","info",3)}<div class="callout" style="margin-top:0">${j.contrato_fim===null?"Contrato de formação: quando ele subir de nível, vale oferecer o primeiro contrato profissional para não perdê-lo de graça.":left<=6&&j.pot>=7?"Potencial alto e contrato no fim: prioridade de renovação.":left<=6?"Vence em menos de 6 meses: renovar agora ou deixar sair no fim do vínculo.":left<=12?"Entra no último ano: avaliar renovação ou empréstimo.":"Sem urgência contratual."}</div><p class="raw-note">Salário bruto no jogo: ${j.salario_raw} (semanal); mostrado em reais por mês pela conversão da ficha do jogo.</p></section></div>`;
}
function staffTab(j) {
  const ah=j.analise.confianca_habilidade, ap=j.analise.confianca_potencial;
  return `<div class="metric-grid">${metric("Confiança habilidade",esc(ah.nivel),`avaliador ${ah.avaliador}/20`)}${metric("Confiança potencial",esc(ap.nivel),`avaliador ${ap.avaliador}/20`)}${metric("Habilidade",stars(j.hab),"opinião da comissão")}${metric("Potencial",stars(j.pot),"opinião da comissão")}</div><div class="grid-2"><section class="panel"><h2>Parecer do adjunto</h2><div class="callout" style="margin-top:0">${esc(j.adjunto?.sugestao||"Sem parecer disponível.")}</div><p class="raw-note">${esc(j.analise.metodologia)}</p></section><section class="panel"><h2>Movimentos preferidos</h2>${j.movimentos.length?`<div class="tag-row">${j.movimentos.map(m=>`<span class="tag">${esc(m)}</span>`).join("")}</div>`:'<div class="empty">Nenhum movimento preferido registrado.</div>'}</section></div>`;
}
function renderTab(j) { return ({overview:overviewTab,development:developmentTab,performance:performanceTab,position:positionTab,health:healthTab,contract:contractTab,staff:staffTab}[ui.tab]||overviewTab)(j); }
function renderWorkspace() {
  if(ui.academy)return renderAcademy();
  const j=data.jovens.find(p=>p.uid===ui.selectedUid); if(!j){ui.academy=true;return renderAcademy()}
  document.getElementById("workspace").innerHTML=renderTabs(j);
}
function renderAll(){renderHeaderSummary();renderList();renderWorkspace();persist()}

async function load() {
  document.getElementById("when").textContent="lendo o jogo…";
  try { const response=await fetch("/dados"), body=await response.json(); if(!response.ok)throw new Error(body.erro||response.status); data=body;
    if(!data.jovens.some(j=>j.uid===ui.selectedUid))ui.selectedUid=data.jovens[0]?.uid??null;
    document.getElementById("when").textContent=`${dateBR(data.info.data)} · comissão ${data.info.avaliador_hab}/${data.info.avaliador_pot}`; renderAll();
  } catch(error) { document.getElementById("when").textContent="sem conexão com o jogo"; document.getElementById("workspace").innerHTML=`<div class="empty" style="color:var(--danger)">Não consegui ler o jogo: ${esc(error.message)}.<br>Abra o fm_brasil.exe e tente novamente.</div>`; }
}

document.getElementById("cards").addEventListener("click",event=>{const card=event.target.closest("[data-uid]");if(!card)return;ui.selectedUid=Number(card.dataset.uid);ui.academy=false;renderAll()});
document.getElementById("filters").addEventListener("click",event=>{const chip=event.target.closest("[data-team]");if(!chip)return;ui.team=chip.dataset.team;renderList();persist()});
document.getElementById("workspace").addEventListener("click",event=>{const tab=event.target.closest("[data-tab]");if(tab){ui.tab=tab.dataset.tab;renderWorkspace();persist();return}const open=event.target.closest("[data-open]");if(open){ui.selectedUid=Number(open.dataset.open);ui.academy=false;renderAll()}});
document.getElementById("search").addEventListener("input",renderList);
document.getElementById("sort").addEventListener("change",renderList);
document.getElementById("reload").addEventListener("click",load);
document.getElementById("academy-home").addEventListener("click",()=>{ui.academy=true;renderAll()});
load();

// Ao entrar na Central de Desenvolvimento do jogo, o servidor avisa: a página relê o jogo, volta
// para a visão da base e chama a atenção na aba do navegador.
let centroEntries = null;
async function watchGame() {
  try {
    const {centro} = await (await fetch("/evento")).json();
    if (centroEntries !== null && centro > centroEntries) {
      ui.academy = true; await load(); window.focus();
      const title = document.title; let blink = 0;
      const timer = setInterval(() => { document.title = blink++ % 2 ? title : "⚽ Central aberta no jogo"; if (blink > 7) { clearInterval(timer); document.title = title; } }, 600);
    }
    centroEntries = centro;
  } catch {}
}
setInterval(watchGame, 2000); watchGame();

// cabeçalho do jogador + abas ficam presos no topo; ao rolar, o cabeçalho encolhe
document.getElementById("workspace").addEventListener("scroll", event => {
  const head = event.currentTarget.querySelector(".sticky-head");
  if (head) head.classList.toggle("scrolled", event.currentTarget.scrollTop > 60);
});
