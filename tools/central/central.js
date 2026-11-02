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
const TABS = [["overview","Visão geral"],["development","Desenvolvimento"],["performance","Desempenho"],["position","Posição e função"],["health","Saúde"],["contract","Contrato e carreira"],["staff","Comissão"]];

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

function stars(value, big=false) {
  let out = "";
  for (let i=1; i<=5; i++) { const n=value-(i-1)*2; out += n>=2 ? "★" : n===1 ? '<span class="half">★</span>' : '<span class="off">★</span>'; }
  return `<span class="stars ${big?"big":""}" title="${value}/10">${out}</span>`;
}
function bar(value, max=100, colour="var(--positive)") { return `<div class="bar"><i style="width:${clamp(value/max*100,0,100)}%;background:${colour}"></i></div>`; }
function metric(label, value, note="") { return `<div class="metric"><span>${esc(label)}</span><b>${value}</b>${note?`<small>${esc(note)}</small>`:""}</div>`; }
function positionTag(pos) { const sector=(PITCH[pos]||[0,0,"mid"])[2]; return `<span class="tag position" style="background:${LINE_COLOR[sector]}">${esc(pos)}</span>`; }

function pitch(j, full=false) {
  const entries = full ? Object.entries(j.familiaridades || {}).filter(([,v]) => v >= 5) : j.posicoes.map((p,i)=>[p,i?15:20]);
  const dots = entries.map(([p,familiarity]) => { const [x,y,sector]=PITCH[p]||[]; if(x===undefined)return "";
    const opacity=full ? clamp(familiarity/20,.3,1) : 1; const radius=full ? 4+familiarity/5 : 6;
    return `<circle cx="${x}" cy="${y}" r="${radius}" fill="${LINE_COLOR[sector]}" stroke="#071016" stroke-width="1.3" opacity="${opacity}"/><text x="${x+(x>60?-8:8)}" y="${y+2.3}" text-anchor="${x>60?"end":"start"}" font-size="6" fill="#eef4f2">${esc(p)}${full?` ${familiarity}`:""}</text>`;
  }).join("");
  const suggested=PITCH[j.adjunto?.nova_posicao];
  return `<svg viewBox="0 0 100 104" aria-label="Mapa de posições"><rect x="2" y="2" width="96" height="100" rx="3" fill="#164127" stroke="#6c9c78" stroke-width=".8"/>${suggested?`<circle cx="${suggested[0]}" cy="${suggested[1]}" r="9" fill="none" stroke="var(--accent)" stroke-width="1.4" stroke-dasharray="2 2"/>`:""}<g stroke="#6c9c78" stroke-width=".7" fill="none"><line x1="2" y1="52" x2="98" y2="52"/><circle cx="50" cy="52" r="10"/><rect x="28" y="84" width="44" height="18"/><rect x="38" y="95" width="24" height="7"/><rect x="28" y="2" width="44" height="18"/></g>${dots}</svg>`;
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
  document.getElementById("cards").innerHTML=list.length?list.map(j=>{const sector=line(j);return `<button class="player-card ${!ui.academy&&ui.selectedUid===j.uid?"selected":""}" data-uid="${j.uid}"><span class="sector" style="background:${LINE_COLOR[sector]}">${LINE_NAME[sector]}</span><span class="card-name">${esc(short(j))}</span><span class="card-meta">${j.idade} anos · ${esc(j.analise.fase)} · ${esc(j.adjunto?.alvo||"—")}</span><span class="card-score"><b>${j.analise.prioridade}</b><small>prioridade</small></span></button>`}).join(""):'<div class="empty">Nenhum jovem neste filtro.</div>';
}
function renderHeaderSummary() {
  const priority=data.jovens.filter(j=>j.analise.fase==="Prioridade"||j.analise.prioridade>=60).length;
  const ready=data.jovens.filter(j=>j.analise.fase==="Pronto para minutos"||j.analise.prontidao>=70).length;
  document.getElementById("header-summary").innerHTML=`<div class="header-kpi"><b>${data.jovens.length}</b><span>jovens</span></div><div class="header-kpi"><b>${priority}</b><span>prioridades</span></div><div class="header-kpi"><b>${ready}</b><span>prontos</span></div>`;
}
function academyScatter(players) {
  const W=500,H=235,L=34,B=25,x=v=>L+(W-L-12)*v/10,y=v=>8+(H-B-8)*(1-v/10);
  const grid=[0,2,4,6,8,10].map(v=>`<line class="axis" x1="${x(v)}" x2="${x(v)}" y1="8" y2="${H-B}"/><line class="axis" x1="${L}" x2="${W-12}" y1="${y(v)}" y2="${y(v)}"/><text x="${x(v)}" y="${H-7}" text-anchor="middle">${v}</text><text x="4" y="${y(v)+3}">${v}</text>`).join("");
  const dots=players.map(j=>`<circle cx="${x(j.hab)}" cy="${y(j.pot)}" r="${3+(20-j.idade)}" fill="${LINE_COLOR[line(j)]}" opacity=".82"><title>${esc(short(j))}: hab. ${j.hab}, pot. ${j.pot}</title></circle>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}">${grid}${dots}<text x="${W/2}" y="${H-1}" text-anchor="middle">Habilidade da comissão</text><text x="12" y="12">Potencial</text></svg>`;
}
function renderAcademy() {
  const players=[...data.jovens], phases={}; players.forEach(j=>phases[j.analise.fase]=(phases[j.analise.fase]||0)+1);
  const avg=Math.round(players.reduce((s,j)=>s+j.analise.prontidao,0)/(players.length||1)); const top=[...players].sort((a,b)=>b.analise.prioridade-a.analise.prioridade).slice(0,6);
  const maxPhase=Math.max(1,...Object.values(phases));
  document.getElementById("workspace").innerHTML=`<div class="academy"><div class="academy-hero"><div><h1>Visão da base</h1><p>O que exige decisão e como está o caminho até o time principal.</p></div><span class="tag">Atualizado em ${dateBR(data.info.data)}</span></div>
    <div class="kpi-grid"><div class="kpi"><b>${players.length}</b><span>jovens monitorados</span><small>Principal, B e Sub-20</small></div><div class="kpi"><b>${players.filter(j=>j.pot>=7).length}</b><span>potencial alto</span><small>7/10 ou mais na comissão</small></div><div class="kpi"><b>${avg}</b><span>prontidão média</span><small>indicador interno da Central</small></div><div class="kpi"><b>${players.filter(j=>j.adjunto?.nova_posicao).length}</b><span>mudanças sugeridas</span><small>nova posição a avaliar</small></div></div>
    <div class="grid-2"><section class="panel"><h2>Fila de decisões</h2><div class="decision-list">${top.map(j=>`<button class="decision" data-open="${j.uid}" style="background:none;border:0;color:inherit;text-align:left;cursor:pointer"><b>${esc(short(j))}</b><span>${esc(j.analise.fase)} · ${esc(j.analise.funcao_alvo)}</span><strong>${j.analise.prioridade}</strong></button>`).join("")}</div></section>
    <section class="panel chart"><h2>Mapa de talento</h2>${academyScatter(players)}<div class="legend"><span>Tamanho = juventude</span><span>Cor = setor</span></div></section></div>
    <div class="grid-2"><section class="panel"><h2>Pipeline de desenvolvimento</h2>${Object.entries(phases).sort((a,b)=>b[1]-a[1]).map(([name,count])=>`<div class="phase-row"><span>${esc(name)}</span>${bar(count,maxPhase,name==="Pronto para minutos"?"var(--positive)":"var(--accent)")}<b>${count}</b></div>`).join("")}</section>
    <section class="panel"><h2>Leitura rápida</h2><div class="alerts"><div class="alert oportunidade"><small>Oportunidade</small>${players.filter(j=>j.pot-j.hab>=3).length} jovens têm grande distância entre habilidade e potencial percebido.</div><div class="alert"><small>Decisão</small>${players.filter(j=>j.idade>=18&&j.time!=="Principal"&&j.analise.prontidao>=60).length} jogadores mais velhos estão perto de precisar de nível competitivo maior.</div><div class="alert risco"><small>Atenção</small>${players.filter(j=>j.moral<=8).length} jogadores aparecem com moral baixa.</div></div></section></div></div>`;
}

function playerHeader(j) {
  const name=short(j).toUpperCase();
  return `<header class="player-header"><div class="shirt"><img src="/camisa.png" alt=""><svg viewBox="0 0 210 210"><path id="name-arc" d="M 48 72 Q 105 55 162 72" fill="none"/><text><textPath href="#name-arc" startOffset="50%" text-anchor="middle">${esc(name)}</textPath></text></svg></div><div class="identity"><h1>${esc(short(j))}</h1><div class="bio">${esc(j.nome)} · ${j.idade} anos · ${esc(j.time)} · ${j.altura} cm · ${j.peso} kg</div><div class="tag-row">${j.posicoes.map(positionTag).join("")}<span class="tag">pé ${esc(j.pe_preferido)}</span><span class="tag">${esc(j.analise.fase)}</span></div><div class="headline-metrics"><div><b>${stars(j.hab)}</b><span>habilidade</span></div><div><b>${stars(j.pot)}</b><span>potencial</span></div><div><b>${j.analise.prontidao}/100</b><span>prontidão</span></div></div></div><div class="mini-pitch">${pitch(j)}</div></header>`;
}
function renderTabs(j) {
  const nav=`<nav class="tabs" role="tablist">${TABS.map(([id,label])=>`<button class="tab ${ui.tab===id?"active":""}" data-tab="${id}" role="tab" aria-selected="${ui.tab===id}">${label}</button>`).join("")}</nav>`;
  return `${playerHeader(j)}${nav}<div class="tab-content">${renderTab(j)}</div>`;
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
function overviewTab(j) {
  const role=roleRow(j), points=data.historico?.[String(j.uid)]||[];
  return `<div class="metric-grid">${metric("Fase",esc(j.analise.fase),"plano de carreira")}${metric("Função-alvo",esc(j.analise.funcao_alvo),j.adjunto?.alvo||"")}${metric("Nota na função",role.nota?.toFixed(1)??"—",role.futuro?`projeção ${role.futuro.toFixed(1)}`:"")}${metric("Prioridade",`${j.analise.prioridade}/100`,"ordena a fila de decisões")}</div><div class="callout"><b>Parecer executivo</b><br>${esc(verdict(j))}</div><div class="grid-3"><section class="panel radar"><h3>Perfil de atributos</h3>${radar(j)}</section><section class="panel chart"><h3>Evolução observada</h3>${historyChart(points)}</section><section class="panel"><h3>Alertas e oportunidades</h3>${alerts(j)}</section></div><div class="grid-2"><section class="panel"><h3>Plano recomendado</h3><div class="focus-list">${(j.adjunto?.treino||[]).map(t=>`<div class="focus-item"><b>${esc(t.categoria)}</b><p>${t.atributos.map(([n,v,g])=>`${esc(n)} ${v} → ${g}`).join(" · ")}</p></div>`).join("")||'<div class="empty">Nenhuma lacuna urgente.</div>'}</div></section><section class="panel"><h3>Onde pode crescer mais</h3><div class="decision-list">${bestGrowth(j).map(([name,v,f])=>`<div class="decision"><b>${esc(name)}</b><span>${v} agora</span><strong>→ ${f}</strong></div>`).join("")}</div></section></div>`;
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
  return `<div class="grid-2" style="margin-top:0"><section class="panel"><h2>Mapa completo de posições</h2><div class="mini-pitch" style="max-width:360px;margin:auto;display:block">${pitch(j,true)}</div><div class="legend"><span>15–20 natural</span><span>12–14 competente</span><span>8–11 familiar</span><span>5–7 aprendendo</span></div></section><section class="panel"><h2>Diagnóstico da posição</h2><div class="callout" style="margin-top:0">${esc(j.adjunto?.sugestao||"Sem parecer.")}</div><p><b>Pé preferido:</b> ${esc(j.pe_preferido)}.</p><p><b>Pontos fortes:</b> ${(j.adjunto?.pontos_fortes||[]).map(([n,v])=>`${esc(n)} ${v}`).join(" · ")||"—"}</p><p><b>Lacunas:</b> ${(j.adjunto?.pontos_fracos||[]).map(([n,v])=>`${esc(n)} ${v}`).join(" · ")||"—"}</p></section></div><section class="panel" style="margin-top:12px"><h2>Ranking de encaixe</h2><table class="role-table"><thead><tr><th>Posição</th><th>Perfil</th><th>Familiaridade</th><th>Agora</th><th>Projeção</th></tr></thead><tbody>${rows.map(r=>`<tr class="${r.pos===j.adjunto?.alvo?"target":""}"><td><b>${esc(r.pos)}</b></td><td>${esc(r.nome)} ${r.pos===j.adjunto?.nova_posicao?'<span class="tag">sugerida</span>':""}</td><td><span class="familiarity" style="background:${attrColor(r.familiaridade)};color:#071016">${r.familiaridade}</span> ${familiarityLabel(r.familiaridade)}</td><td>${r.nota.toFixed(1)}</td><td>${r.futuro.toFixed(1)}</td></tr>`).join("")}</tbody></table></section>`;
}
function healthTab(j) {
  const moral=clamp(j.moral,0,20);
  return `<div class="metric-grid">${metric("Moral",`${moral}/20`,moral>=15?"alta":moral>=10?"estável":"baixa")}${metric("Condição",j.condicao_raw,"valor interno confirmado")}${metric("Ritmo de jogo",j.ritmo_raw,"valor interno confirmado")}${metric("Cansaço",j.cansaco_raw,"valor interno confirmado")}</div><div class="grid-2"><section class="panel"><h2>Moral</h2>${bar(moral,20,moral>=10?"var(--positive)":"var(--danger)")}<p class="raw-note">A moral usa a escala nativa de 0 a 20.</p></section><section class="panel"><h2>Disponibilidade</h2><div class="unavailable"><b>Leitura física sem falsa porcentagem</b>Os offsets de condição, ritmo e cansaço estão confirmados, mas a conversão dos valores internos para a porcentagem visual do jogo ainda não. Por isso a Central mostra o bruto e não inventa 0–100%.</div></section></div>`;
}
function contractTab(j) {
  return `<div class="metric-grid">${metric("Valor pedido",j.valor_pedido_raw.toLocaleString("pt-BR"),"unidade monetária interna")}${metric("Time atual",esc(j.time),"equipe do clube")}${metric("Número", "—", "contrato ainda não ligado")}${metric("Fim do vínculo","—","contrato ainda não ligado")}</div><div class="unavailable" style="margin-top:12px"><b>Contrato vivo preparado, mas não ativado nesta versão</b>Salário, datas, status e empréstimo têm offsets conhecidos. A ligação atual exige uma varredura completa de memória; ela será integrada quando puder ser indexada sem deixar cada atualização lenta.</div><div class="callout">O valor mostrado é o campo <b>Ask Value</b> confirmado, mantido na unidade interna do jogo. Ele não é rotulado como valor de mercado nem convertido para reais.</div>`;
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
