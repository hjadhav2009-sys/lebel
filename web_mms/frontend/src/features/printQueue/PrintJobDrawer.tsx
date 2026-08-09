import { useEffect, useState } from "react";
import { PanelRightClose } from "lucide-react";
import { api } from "../../api/client";
import { LoadingSkeleton } from "../../components/States";
import { StatusBadge } from "../../components/StatusBadge";
import type { PrintJob } from "../../types";

const tabs=["Overview","Preview","Lines","Snapshot","Artifact","Events","Transport"] as const;
type Tab=typeof tabs[number];

export function PrintJobDrawer({job,roles=["Admin"],onClose,onChanged}:{job:PrintJob;roles?:string[];onClose:()=>void;onChanged:()=>void}){
  const[detail,setDetail]=useState<any>(null),[tab,setTab]=useState<Tab>("Overview"),[error,setError]=useState("");
  const[diagnostics,setDiagnostics]=useState<any>(null),[lineId,setLineId]=useState(""),[scanned,setScanned]=useState(""),[verified,setVerified]=useState<boolean|null>(null);
  const quality=roles.some(role=>["Admin","QC"].includes(role));
  function load(){api(`/print-jobs/${job.id}`).then((value:any)=>{setDetail(value);setLineId(value.lines?.[0]?.id??"")}).catch(e=>setError(e.message))}
  useEffect(load,[job.id]);
  useEffect(()=>{if(tab==="Artifact"&&quality)api(`/print-jobs/${job.id}/diagnostics`).then(setDiagnostics).catch(e=>setError(e.message))},[tab,job.id,quality]);
  async function action(path:string,body:object={}){try{await api(`/print-jobs/${job.id}/${path}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});load();onChanged()}catch(e:any){setError(e.message)}}
  async function verify(){try{const result:any=await api(`/print-jobs/${job.id}/verify-barcode`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({print_job_line_id:lineId,scanned_value:scanned})});setVerified(result.passed)}catch(e:any){setError(e.message)}}
  function content(){
    if(!detail)return <LoadingSkeleton/>;
    if(tab==="Overview")return <><dl><div><dt>Status</dt><dd><StatusBadge status={detail.status}/></dd></div><div><dt>Marketplace</dt><dd>{detail.marketplace}</dd></div><div><dt>Labels</dt><dd>{detail.labels}</dd></div><div><dt>Renderer</dt><dd>{detail.renderer_key||"Not compiled"} {detail.renderer_version||""}</dd></div><div><dt>Layout</dt><dd>{detail.layout_version?`v${detail.layout_version}`:"Not compiled"}</dd></div></dl>{["ready","render_failed"].includes(detail.status)&&<button className="primary" onClick={()=>void action("compile")}>Compile immutable artifact</button>}{detail.status==="completed"&&<button className="primary" onClick={()=>void action("reprint")}>Reprint Exact Snapshot</button>}{roles.includes("Admin")&&detail.simulation_enabled&&["ready","waiting_for_agent"].includes(detail.status)&&<button className="simulation-button" onClick={()=>void action("simulate-success")}>SIMULATION · Successful Print</button>}</>;
    if(tab==="Preview")return <><p>Preview shares measurements, wrapping, overflow checks, and 2-up placement with the RAW renderer.</p><img className="label-preview" src={`/api/v1/print-jobs/${job.id}/preview`} alt="Label preview"/></>;
    if(tab==="Lines")return <div className="job-lines">{detail.lines.map((line:any)=><div key={line.id}><code>{line.snapshot.sku||line.snapshot.fsn||line.snapshot.fnsku}</code><span>{line.copies} copies</span><StatusBadge status={line.status}/></div>)}</div>;
    if(tab==="Snapshot")return <pre className="snapshot-view">{JSON.stringify(detail.lines.map((line:any)=>line.snapshot),null,2)}</pre>;
    if(tab==="Artifact")return quality?<pre className="snapshot-view">{JSON.stringify(diagnostics,null,2)}</pre>:<p>Access denied. Diagnostics require Admin or QC.</p>;
    if(tab==="Events")return <div className="history-list">{detail.events.map((event:any)=><div key={event.id}><i/><span><strong>{event.type}</strong><p>{JSON.stringify(event.payload)}</p><small>{new Date(event.created_at).toLocaleString()}</small></span></div>)}</div>;
    return <><dl><div><dt>Transport</dt><dd>{detail.transport_status||"Not started"}</dd></div><div><dt>Spool job</dt><dd>{detail.spool_job_id||"—"}</dd></div><div><dt>Error</dt><dd>{detail.transport_error_code||detail.transport_error_message||"—"}</dd></div></dl>{quality&&detail.status==="spooled"&&<button className="primary" onClick={()=>void action("confirm-physical-output")}>Confirm physical output</button>}{quality&&<><h3>Barcode verification</h3><select value={lineId} onChange={e=>setLineId(e.target.value)}>{detail.lines.map((line:any)=><option key={line.id} value={line.id}>{line.snapshot.sku||line.snapshot.fsn||line.snapshot.fnsku||line.id}</option>)}</select><input value={scanned} onChange={e=>setScanned(e.target.value)} placeholder="Scan printed barcode"/><button className="primary" onClick={()=>void verify()} disabled={!lineId||!scanned}>Verify server-derived expected value</button>{verified!==null&&<p className={verified?"success-text":"inline-error"}>{verified?"Barcode verified":"Barcode mismatch — block approval"}</p>}</>}</>;
  }
  return <><button className="backdrop" onClick={onClose} aria-label="Close print job"/><aside className="drawer product-drawer"><header><div><p>PRINT JOB</p><h2>{job.id.slice(0,8)}</h2></div><button className="icon-button" onClick={onClose}><PanelRightClose size={20}/></button></header><div className="drawer-tabs">{tabs.map(item=><button key={item} className={tab===item?"active":""} onClick={()=>setTab(item)}>{item}</button>)}</div><div className="drawer-body">{error&&<p className="inline-error">{error}</p>}{content()}</div></aside></>;
}
