import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { EmptyState, LoadingSkeleton } from "../../components/States";
import { StatusBadge } from "../../components/StatusBadge";

type Printer={id:string;name:string;driver:string;port?:string;dpi:number;status:string;enabled:boolean;agent:string;agent_status:string;machine:string};
type Agent={id:string;name:string;machine_name:string;status:string;last_seen_at?:string;version?:string;last_error?:string};

export function PrintersPage(){
  const[printers,setPrinters]=useState<Printer[]>([]),[agents,setAgents]=useState<Agent[]>([]),[loading,setLoading]=useState(true);
  const[pairing,setPairing]=useState<any>(null),[selected,setSelected]=useState<Printer|null>(null),[profiles,setProfiles]=useState<any[]>([]);
  const[testJob,setTestJob]=useState(""),[formatKey,setFormatKey]=useState(""),[error,setError]=useState("");
  function load(){setLoading(true);Promise.all([api<Printer[]>("/printers"),api<Agent[]>("/print-agents")]).then(([p,a])=>{setPrinters(p);setAgents(a)}).catch(e=>setError(e.message)).finally(()=>setLoading(false))}
  async function loadProfiles(printer:Printer){setProfiles(await api<any[]>(`/printers/${printer.id}/profiles`))}
  useEffect(load,[]);useEffect(()=>{if(selected)void loadProfiles(selected)},[selected]);
  async function createPairing(){try{setPairing(await api("/print-agents/pairing-codes",{method:"POST"}))}catch(e:any){setError(e.message)}}
  async function addProfile(marketplace:"amazon"|"flipkart"){if(!selected)return;const renderer=marketplace==="amazon"?"amazon_dynamic_tspl_v1":"flipkart_hybrid_tspl_v1";const config:any={approved_dpi:selected.dpi};if(marketplace==="flipkart")config.font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf";try{await api(`/printers/${selected.id}/profiles`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({marketplace,media_width_mm:101.5,media_height_mm:50,gap_mm:2,renderer,config})});await loadProfiles(selected);load()}catch(e:any){setError(e.message)}}
  async function approve(profileId:string){try{await api(`/printer-profiles/${profileId}/approvals`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({test_print_job_id:testJob,format_key:formatKey||null})});setError("");alert("Renderer/profile/layout approved.")}catch(e:any){setError(e.message)}}
  return <section className="content"><div className="page-heading"><div><span className="eyebrow">LOCAL PRINT TRANSPORT</span><h1>Printers & Agents</h1><p>Pair Windows machines, review discovered queues, and approve versioned renderer profiles.</p></div><button className="primary" onClick={()=>void createPairing()}>Pair Print Agent</button></div>
    {pairing&&<div className="simulation-banner"><strong>Pairing code: {pairing.code}</strong> · expires {new Date(pairing.expires_at).toLocaleTimeString()}</div>}{error&&<p className="inline-error">{error}</p>}
    <div className="metric-grid">{agents.map(a=><article className="metric-card" key={a.id}><span>AGENT</span><strong>{a.name}</strong><p>{a.machine_name} · {a.version||"unknown version"}</p><StatusBadge status={a.status}/>{a.last_error&&<small>{a.last_error}</small>}</article>)}</div>
    {loading?<LoadingSkeleton/>:printers.length?<div className="printer-grid">{printers.map(p=><button className="printer-card" key={p.id} onClick={()=>setSelected(p)}><span><strong>{p.name}</strong><StatusBadge status={p.status}/></span><small>{p.driver} · {p.port||"unknown port"}</small><small>{p.dpi} DPI · {p.agent} ({p.agent_status})</small><b>{p.enabled?"Configured":"Setup required"}</b></button>)}</div>:<EmptyState title="No printers discovered" detail="Generate a pairing code, pair the Windows agent, and let it sync installed printer queues."/>}
    {selected&&<aside className="profile-panel"><div><span className="eyebrow">PRINTER PROFILE</span><h2>{selected.name}</h2><p>Editing creates a new layout version and invalidates prior approvals.</p></div><span><button className="primary" onClick={()=>void addProfile("amazon")}>Add Amazon 101.5×50</button> <button onClick={()=>void addProfile("flipkart")}>Add Flipkart 101.5×50</button></span><label>Completed test job ID<input value={testJob} onChange={e=>setTestJob(e.target.value)} placeholder="UUID"/></label><label>Format key (optional)<input value={formatKey} onChange={e=>setFormatKey(e.target.value)} placeholder="key_chain"/></label>{profiles.map(profile=><article key={profile.id}><strong>{profile.marketplace} · {profile.renderer}</strong><span>Layout v{profile.layout_version} · {profile.media_width_mm}×{profile.media_height_mm} mm · {selected.dpi} DPI</span><small>Approval requires a completed test job and passing barcode scan.</small><button onClick={()=>void approve(profile.id)} disabled={!testJob}>Approve exact version</button></article>)}</aside>}
  </section>;
}
