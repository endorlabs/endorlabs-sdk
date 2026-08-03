"""Render the Endor Patches executive report page."""

from __future__ import annotations

import json
from typing import Any

from endorlabs.workflows.reports.export.html import chrome
from endorlabs.workflows.reports.export.html import copy as copy_mod

_PATCHES_PAGE_CSS = """
.wrap { max-width:1400px; }
.top-band { display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px;margin:12px 0 8px;align-items:stretch; }
.impact-card,.top-band .glossary { margin:0;min-width:0;display:flex;flex-direction:column; }
.impact-card .card-h { display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap; }
.donut-wrap { display:grid;grid-template-columns:auto minmax(0,1fr);gap:14px 16px;align-items:center; }
.donut { width:100px;height:100px;border-radius:50%;display:grid;place-items:center;position:relative;flex-shrink:0;
  background:conic-gradient(var(--endor-accent) var(--pct),var(--endor-border) 0); }
.donut::after { content:"";position:absolute;inset:13px;border-radius:50%;background:var(--endor-panel); }
.donut-label { position:relative;z-index:1;font-size:1.25rem;font-weight:700;transition:transform .25s ease; }
.donut-meta { min-width:0;display:flex;flex-direction:column;gap:8px; }
.fixable-summary { font-size:.9rem;line-height:1.35; } .fixable-summary strong { font-size:1.1rem; }
.impact-controls { display:flex;flex-direction:column;gap:5px;font-size:.78rem;color:var(--endor-muted);max-width:28rem; }
.impact-k-row,.impact-slider-row { display:flex;align-items:center;gap:8px;flex-wrap:wrap; }
.impact-k-row input[type=number] { width:4.25rem;background:var(--endor-bg);color:var(--endor-text);border:1px solid var(--endor-border);border-radius:6px;padding:5px 8px; }
.impact-slider-row input { flex:1;height:6px;appearance:none;background:linear-gradient(90deg,var(--endor-accent) var(--impact-fill,0%),#2a2a2a var(--impact-fill,0%));border-radius:999px; }
.impact-slider-row input::-webkit-slider-thumb { appearance:none;width:16px;height:16px;border-radius:50%;background:var(--endor-accent);border:2px solid var(--endor-panel); }
.impact-slider-ends { display:flex;justify-content:space-between;font-size:.68rem;color:var(--endor-muted); }
.impact-flip { display:flex;align-items:center;gap:8px;font-size:.72rem;font-weight:600;color:var(--endor-muted); }
.impact-flip.on { color:var(--endor-accent); } .flip { position:relative;width:40px;height:22px;flex-shrink:0; }
.flip input { opacity:0;width:0;height:0;position:absolute; }
.flip-track { position:absolute;inset:0;border-radius:999px;cursor:pointer;background:#2a2a2a;border:1px solid var(--endor-border);transition:.2s; }
.flip-track::after { content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#c8c8c8;transition:.2s; }
.flip input:checked+.flip-track { background:color-mix(in srgb,var(--endor-accent) 35%,#1a1a1a);border-color:var(--endor-accent); }
.flip input:checked+.flip-track::after { transform:translateX(18px);background:var(--endor-accent); }
.impact-header-flips { display:flex;flex-direction:column;align-items:flex-end;gap:6px; }
.denom-mode { display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end; }
.denom-mode button { background:var(--endor-bg);color:var(--endor-muted);border:1px solid var(--endor-border);border-radius:6px;padding:4px 8px;font-size:.68rem;font-weight:650;cursor:pointer; }
.denom-mode button.active { border-color:var(--endor-accent);color:var(--endor-accent); }
.pct-caption { font-size:.72rem;color:var(--endor-muted);margin-top:2px; }
.risk-callout { font-size:.8rem;line-height:1.4;padding:8px 10px;border-radius:8px;margin-bottom:10px;background:color-mix(in srgb,var(--endor-accent) 10%,transparent);border:1px solid color-mix(in srgb,var(--endor-accent) 35%,var(--endor-border)); }
.glossary-grid { display:grid;grid-template-columns:1fr 1fr;gap:10px 16px;font-size:.78rem;color:var(--endor-muted); }
.glossary-grid dt { color:var(--endor-text);font-weight:650;margin-bottom:2px; } .glossary-grid dd { margin:0; }
.sev { display:inline-flex;font-size:.72rem;font-weight:700;padding:2px 7px;border-radius:4px;margin-right:4px; }
.sev.c { background:#3a1515;color:var(--endor-danger);border:1px solid var(--endor-danger); }
.sev.h { background:#3a2210;color:var(--endor-warn);border:1px solid var(--endor-warn); }
.status-stack { display:flex;flex-direction:column;gap:3px;align-items:flex-start; }
.status-pill { display:inline-block;font-size:.65rem;font-weight:650;padding:1px 7px;border-radius:999px;border:1px solid var(--endor-border);white-space:nowrap; }
.status-pill.available { border-color:var(--endor-ok);color:var(--endor-ok); } .status-pill.to-request { color:var(--endor-muted); }
table.data tr.family-row { cursor:pointer; } table.data tr.family-row:hover td { background:#141414; }
table.data tr.family-row.active td { outline:1px solid var(--endor-accent);background:color-mix(in srgb,var(--endor-accent) 10%,transparent); }
.family-name,.family-name code { font-size:.92rem;font-weight:700;color:var(--endor-text);background:transparent;word-break:break-all; }
#heatCard { transition:opacity .35s ease,transform .35s ease; } #heatCard.is-enter { opacity:0;transform:translateY(8px); }
.heat-family { font-size:1.05rem;font-weight:750;word-break:break-all; } .heat-sub { font-size:.78rem;color:var(--endor-muted); }
.sort-bar { display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 12px; }
.sort-bar button { background:var(--endor-bg);color:var(--endor-text);border:1px solid var(--endor-border);border-radius:6px;padding:6px 12px;cursor:pointer; }
.sort-bar button.active { border-color:var(--endor-accent);color:var(--endor-accent); } .sort-dir { opacity:0; } button.active .sort-dir { opacity:1; }
.legend { display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:.72rem;color:var(--endor-muted); }
.legend-grad { width:120px;height:8px;border-radius:4px;background:linear-gradient(90deg,#26d07c,#f0b429,#f07a29,#ff5c5c); }
.heatmap { margin-top:8px;position:relative; }
.bar-row { display:grid;grid-template-columns:minmax(100px,120px) 118px 1fr minmax(200px,260px);gap:10px;align-items:center;margin-bottom:7px;font-size:.75rem;will-change:transform; }
.bar-label { font-size:.82rem;font-weight:700;font-variant-numeric:tabular-nums; } .bar-label.sort-focus { color:var(--endor-accent);font-weight:800; }
.bar-track { background:#1a1a1a;height:10px;border-radius:5px;overflow:hidden; }
.bar-fill { height:100%;min-width:2px;border-radius:5px;transition:width .55s cubic-bezier(.22,1,.36,1),background-color .45s; }
.bar-meta { color:var(--endor-muted);font-size:.7rem; } .meta-bit.sort-focus { color:var(--endor-text);font-weight:750; }
@media(max-width:980px) { .top-band { grid-template-columns:1fr; } }
@media(max-width:800px) { .bar-row { grid-template-columns:88px 100px 1fr; } .bar-meta { grid-column:1/-1; } }
@media(max-width:560px) { .donut-wrap,.glossary-grid { grid-template-columns:1fr; } }
@media(prefers-reduced-motion:reduce) { .bar-fill,.bar-row,#heatCard,.donut-label,.flip-track,.flip-track::after { transition:none!important; } }
"""


def render_patches_html(cube: dict[str, Any]) -> str:
    """Return the complete interactive Endor Patches HTML page."""
    patches = (cube.get("reports") or {}).get("patches") or {}
    tenant = cube.get("tenant") or ""
    pulled = cube.get("pulledAt") or ""
    payload = json.dumps(patches, separators=(",", ":"))
    weights = patches.get("risk_weights") or {}
    critical_weight = weights.get("critical", 4)
    high_weight = weights.get("high", 2)
    reachable_weight = weights.get("reachable_or_prf", 3)
    unreachable_weight = weights.get("unreachable", 1)
    top_n = patches.get("top_n_families") or 5
    h1 = copy_mod.H1_ENDOR_PATCHES
    purpose = copy_mod.PURPOSE_ENDOR_PATCHES

    body = f"""{
        chrome.header(
            title=h1,
            purpose=purpose,
            tenant=tenant,
            pulled_at=pulled,
            nav_html=chrome.nav("pat"),
            meta_extra="Scope: Critical + High",
        )
    }
<div id="patchesEmpty"></div>
<div class="top-band">
  <aside class="card impact-card">
    <div class="card-h"><span>Impact calculator</span>
      <div class="impact-header-flips">
        <div class="impact-flip" id="includeWrap"><span>Include To Request</span>
          <label class="flip"><input type="checkbox" id="includeReq"/><span class="flip-track"></span></label></div>
        <div class="denom-mode" id="denomMode" role="group" aria-label="Denominator">
          <button type="button" class="active" data-mode="fixable">Fixable findings</button>
          <button type="button" data-mode="java">Java Crit/High estate</button>
        </div>
      </div>
    </div>
    <div class="donut-wrap"><div class="donut" id="donut" style="--pct:0%"><span class="donut-label" id="donutPct">0%</span></div>
      <div class="donut-meta"><div class="fixable-summary" id="summary"></div>
        <div class="pct-caption" id="pctCaption"></div>
        <div class="impact-controls">
        <div class="impact-k-row">Top <input type="number" id="topK" min="1" value="3"/> of <span id="total">0</span> <span id="kind">Available</span> versions</div>
        <div class="impact-slider-row"><input type="range" id="slider" min="1" value="3"/></div>
        <div class="impact-slider-ends"><span>1</span><span id="maxLabel">1</span></div>
      </div></div></div>
  </aside>
  <div class="glossary card"><div class="glossary-title">How to read this</div>
    <div class="risk-callout"><strong>Risk</strong> = <code>(Critical×{
        critical_weight
    } | High×{high_weight}) × reach</code>,
      where reach is <code>×{
        reachable_weight
    }</code> for reachable / potentially reachable and <code>×{
        unreachable_weight
    }</code> if unreachable.</div>
    <dl class="glossary-grid">
      <div><dt>Fixable findings</dt><dd>Default calculator denom (product UI): findings on the Endor Patch units in this view. Top‑K can reach 100%.</dd></div>
      <div><dt>Java Crit/High estate</dt><dd>Optional denom: all Maven Critical/High vulnerability findings in the estate.</dd></div>
      <div><dt>Available</dt><dd>Endor Patch exists today and is campaign-ready.</dd></div>
      <div><dt>To Request</dt><dd>Coverage is incomplete; mixed Available + To Request versions count here.</dd></div>
    </dl>
  </div>
</div>
<div class="card">
  <div class="card-h">Highest-impact families with Endor Patch coverage</div>
  <p class="caption">Top {
        top_n
    }, ranked by Available risk. Click a row for its version heat map.</p>
  <table class="data" id="familyTable"><thead><tr><th>#</th><th>Dependency family</th><th class="num">Available findings</th><th class="num">To Request versions</th><th class="num">Projects</th><th class="num">Versions in use</th><th class="num">Risk</th></tr></thead><tbody></tbody></table>
</div>
<div class="card" id="heatCard" hidden>
  <div><div class="heat-family" id="heatFamily"></div><div class="heat-sub" id="heatSub"></div></div>
  <div class="sort-bar"><button id="sortRisk" class="active" data-mode="risk">Sort by risk <span class="sort-dir">↓</span></button><button id="sortProjects" data-mode="projects">Sort by project consumers <span class="sort-dir"></span></button><button id="sortSemver" data-mode="semver">Sort by SemVer <span class="sort-dir"></span></button></div>
  <div class="legend"><span class="status-pill available">Available</span><span class="status-pill to-request">To Request</span><span>Color = risk</span><div class="legend-grad"></div><span>Length = projects</span></div>
  <div class="heatmap" id="heatmap"></div>
</div>
<script>
const PATCHES = {payload};
const families = PATCHES.families || [];
const patchUnits = PATCHES.patch_units || [];
const javaEstateDenom = PATCHES.estate_java_findings ?? null;
const javaEstateLabel = PATCHES.java_denominator_label
  || "Java (Maven) Critical/High vulnerability findings (estate)";
let denomMode = "fixable";
let activeIdx=0, sortMode="risk", sortDir=1, donutShown=0, donutRaf=0, heatFamily=null;
const reduceMotion=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const motionMs=reduceMotion?0:520;
function badges(c,h) {{ let s="";if(c)s+=`<span class="sev c">C ${{c}}</span>`;if(h)s+=`<span class="sev h">H ${{h}}</span>`;return s||"—"; }}
function pure(r) {{ return (r.available||0)>0&&!(r.to_request||0); }}
function unitFindings(u, include) {{
  return include ? (u.findings ?? ((u.available||0)+(u.to_request||0))) : (u.available||0);
}}
function riskColor(v,max) {{
  const t=max?Math.min(1,v/max):0, stops=[[0,[38,208,124]],[.35,[240,180,41]],[.65,[240,122,41]],[1,[255,92,92]]];
  let a=stops[0],b=stops.at(-1);for(let i=0;i<stops.length-1;i++)if(t>=stops[i][0]&&t<=stops[i+1][0]){{a=stops[i];b=stops[i+1];break;}}
  const u=(t-a[0])/((b[0]-a[0])||1);return `rgb(${{a[1].map((x,i)=>Math.round(x+(b[1][i]-x)*u)).join(",")}})`;
}}
function tweenDonut(target) {{
  const el=document.getElementById("donut"),label=document.getElementById("donutPct"),to=Math.max(0,Math.min(100,target||0));
  if(reduceMotion){{donutShown=to;el.style.setProperty("--pct",to+"%");label.textContent=Math.round(to)+"%";return;}}
  cancelAnimationFrame(donutRaf);const from=donutShown,start=performance.now();
  const run=now=>{{const t=Math.min(1,(now-start)/motionMs),v=from+(to-from)*(1-Math.pow(1-t,3));donutShown=v;el.style.setProperty("--pct",v+"%");label.textContent=Math.round(v)+"%";if(t<1)donutRaf=requestAnimationFrame(run);}};
  donutRaf=requestAnimationFrame(run);
}}
function activeUnits() {{
  const include=document.getElementById("includeReq").checked;
  const rows=patchUnits.filter(include?u=>(u.available||0)||(u.to_request||0):pure);
  rows.sort((a,b)=>include?(b.risk-a.risk)||((b.findings||0)-(a.findings||0)):(b.risk_available||b.risk)-(a.risk_available||a.risk));
  return {{include,rows}};
}}
function updateImpact(ev) {{
  const {{include,rows}}=activeUnits(),max=Math.max(1,rows.length),num=document.getElementById("topK"),slider=document.getElementById("slider");
  num.max=slider.max=max;document.getElementById("maxLabel").textContent=max;document.getElementById("total").textContent=rows.length;
  document.getElementById("kind").textContent=include?"Available + To Request":"Available";document.getElementById("includeWrap").classList.toggle("on",include);
  const source=ev?.target,k=Math.max(1,Math.min(max,parseInt(source?.value||num.value,10)||1));num.value=slider.value=k;
  slider.style.setProperty("--impact-fill",(max===1?100:(k-1)/(max-1)*100)+"%");
  let findings=0,crit=0,high=0;rows.slice(0,k).forEach(u=>{{
    findings+=unitFindings(u, include);
    crit+=include?(u.critical||0):(u.avail_critical??u.critical??0);
    high+=include?(u.high||0):(u.avail_high??u.high??0);
  }});
  // UI-aligned default: Fixable findings = findings on the same Endor Patch unit universe as the slider.
  const fixablePool = rows.reduce((s,u)=>s+unitFindings(u, include), 0);
  const useJava = denomMode === "java" && javaEstateDenom != null && javaEstateDenom > 0;
  const denom = useJava ? javaEstateDenom : fixablePool;
  const denomLabel = useJava
    ? javaEstateLabel
    : (include ? "Fixable findings (Available + To Request in this view)" : "Fixable findings (Available in this view)");
  const pct = denom > 0 ? 100 * findings / denom : null;
  if (pct == null) document.getElementById("donutPct").textContent = "—";
  else tweenDonut(pct);
  document.getElementById("pctCaption").textContent = useJava
    ? "Percentage of Java Crit/High estate"
    : "Percentage of Fixable Findings";
  document.getElementById("summary").innerHTML =
    `<strong>${{findings.toLocaleString()}}</strong> findings addressed` +
    `<br/><span class="caption">${{denom>0?`of ${{Number(denom).toLocaleString()}} ${{denomLabel}}`:"denominator pending"}}</span>` +
    `<br/>${{badges(crit,high)}}`;
}}
function renderFamilies() {{
  const tb=document.querySelector("#familyTable tbody");tb.innerHTML=families.map((f,i)=>{{
    const avail=(f.version_rows||[]).filter(pure).length,req=(f.version_rows||[]).filter(v=>!pure(v)&&((v.available||0)||(v.to_request||0))).length;
    return `<tr class="family-row ${{i===activeIdx?"active":""}}" data-i="${{i}}"><td>${{i+1}}</td><td class="family-name"><code>${{f.family}}</code></td><td class="num">${{badges(f.critical,f.high)}} ${{Number(f.findings||0).toLocaleString()}} <span class="caption">(${{avail}} patches)</span></td><td class="num">${{req}}</td><td class="num">${{Number(f.projects||0).toLocaleString()}}</td><td class="num">${{f.versions||0}}</td><td class="num"><strong>${{Number(f.risk||0).toFixed(0)}}</strong></td></tr>`;
  }}).join("");tb.querySelectorAll("tr").forEach(tr=>tr.onclick=()=>{{activeIdx=Number(tr.dataset.i);renderFamilies();renderHeat(true);}});
}}
function semver(v) {{ return String(v||"").split(/[.\\-+_]/).map(x=>{{const m=x.match(/^(\\d+)/);return m?[0,Number(m[1]),x.slice(m[0].length).toLowerCase()]:[1,0,x.toLowerCase()];}}); }}
function cmpSemver(a,b) {{ const x=semver(a.version),y=semver(b.version);for(let i=0;i<Math.max(x.length,y.length);i++)for(let j=0;j<3;j++){{const p=(x[i]||[1,0,""])[j],q=(y[i]||[1,0,""])[j];if(p<q)return-1;if(p>q)return 1;}}return 0; }}
function sortedRows(f) {{ const r=[...(f.version_rows||[])];if(sortMode==="semver")r.sort((a,b)=>sortDir*cmpSemver(a,b));else r.sort((a,b)=>sortDir*((sortMode==="projects"?(b.projects-a.projects):(b.risk-a.risk))||(b.risk-a.risk)));return r; }}
function status(r) {{ if(pure(r))return '<span class="status-pill available">Available</span>'; if((r.to_request||0)>0||(r.available||0)>0)return '<span class="status-pill to-request">To Request</span>'; return '<span class="status-pill to-request">—</span>'; }}
function meta(r) {{ const pc=sortMode==="projects"?"meta-bit sort-focus":"meta-bit",rc=sortMode==="risk"?"meta-bit sort-focus":"meta-bit";return `<span class="${{pc}}">${{r.projects||0}} projects</span> · <span class="${{rc}}">risk ${{Number(r.risk||0).toFixed(0)}}</span> · ${{r.reachable||0}} RF/PRF`; }}
function bar(r,w,color) {{ const el=document.createElement("div");el.className="bar-row";el.dataset.version=r.version;el.innerHTML=`<div class="bar-label">${{r.version}}</div><div class="status-stack">${{status(r)}}</div><div class="bar-track"><div class="bar-fill" style="width:${{w}}%;background:${{color}}"></div></div><div class="bar-meta">${{meta(r)}}</div>`;return el; }}
function renderHeat(changed=false) {{
  const f=families[activeIdx];if(!f)return;const card=document.getElementById("heatCard"),host=document.getElementById("heatmap"),rows=sortedRows(f),maxP=Math.max(1,...rows.map(r=>r.projects||0)),maxR=Math.max(1,...rows.map(r=>r.risk||0));
  card.hidden=false;document.getElementById("heatFamily").textContent=f.family;document.getElementById("heatSub").textContent=`${{(f.version_rows||[]).filter(pure).length}} Available · C${{f.critical||0}} / H${{f.high||0}} Available findings`;
  if(changed&&!reduceMotion){{card.classList.add("is-enter");requestAnimationFrame(()=>card.classList.remove("is-enter"));}}
  const old=new Map([...host.querySelectorAll(".bar-row")].map(x=>[x.dataset.version,x])),first=new Map([...old].map(([k,x])=>[k,x.getBoundingClientRect()]));host.innerHTML="";
  rows.forEach(r=>{{const w=(100*(r.projects||0)/maxP).toFixed(1),color=riskColor(r.risk||0,maxR),el=old.get(String(r.version))||bar(r,w,color);el.querySelector(".bar-label").className="bar-label"+(sortMode==="semver"?"":" sort-focus");el.querySelector(".status-stack").innerHTML=status(r);el.querySelector(".bar-meta").innerHTML=meta(r);el.querySelector(".bar-fill").style.cssText=`width:${{w}}%;background:${{color}}`;host.appendChild(el);}});
  if(!reduceMotion)rows.forEach(r=>{{const el=old.get(String(r.version)),a=first.get(String(r.version));if(!el||!a)return;const dy=a.top-el.getBoundingClientRect().top;if(Math.abs(dy)>.5){{el.style.transition="none";el.style.transform=`translateY(${{dy}}px)`;requestAnimationFrame(()=>{{el.style.transition=`transform ${{motionMs}}ms cubic-bezier(.22,1,.36,1)`;el.style.transform="";}});}}}});
  heatFamily=f.family;
}}
function arrow() {{ return sortMode==="semver"?(sortDir===1?"↑":"↓"):(sortDir===1?"↓":"↑"); }}
document.querySelectorAll(".sort-bar button").forEach(btn=>btn.onclick=()=>{{const mode=btn.dataset.mode;if(sortMode===mode)sortDir=-sortDir;else{{sortMode=mode;sortDir=1;}}document.querySelectorAll(".sort-bar button").forEach(b=>{{const on=b.dataset.mode===sortMode;b.classList.toggle("active",on);b.querySelector(".sort-dir").textContent=on?arrow():"";}});renderHeat();}});
["topK","slider"].forEach(id=>document.getElementById(id).addEventListener("input",updateImpact));
document.getElementById("includeReq").addEventListener("change",updateImpact);
document.querySelectorAll("#denomMode button").forEach(btn=>{{
  if (btn.dataset.mode === "java" && !(javaEstateDenom > 0)) {{
    btn.disabled = true;
    btn.title = "Java Crit/High estate count not available on this cube";
  }}
  btn.addEventListener("click", () => {{
    if (btn.disabled) return;
    denomMode = btn.dataset.mode || "fixable";
    document.querySelectorAll("#denomMode button").forEach(b => b.classList.toggle("active", b === btn));
    updateImpact();
  }});
}});
if (!families.length && !patchUnits.length) {{
  document.getElementById("patchesEmpty").innerHTML =
    `<div class="callout warn">No Endor Patch data in this packet — either the patches pull was skipped, or no Critical/High Maven findings in this namespace have an available patch or upgrade path.</div>`;
}}
renderFamilies();updateImpact();renderHeat(true);
</script>
"""
    return chrome.page(
        body,
        title=f"{h1} · {tenant}",
        include_chart_js=False,
        extra_css=_PATCHES_PAGE_CSS,
    )
