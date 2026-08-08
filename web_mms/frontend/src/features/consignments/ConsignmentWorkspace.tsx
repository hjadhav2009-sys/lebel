import { useEffect, useState } from "react";
import { Archive, ArrowLeft, Printer } from "lucide-react";
import { api, queryString } from "../../api/client";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { EmptyState, ErrorState, LoadingSkeleton } from "../../components/States";
import { StatusBadge } from "../../components/StatusBadge";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import type { Consignment, ConsignmentLine, LinePage } from "../../types";
import { ConsignmentDrawer } from "./ConsignmentDrawer";
import { ConsignmentTable } from "./ConsignmentTable";

type Tab="to_print"|"printed"|"errors";

export function ConsignmentWorkspace({consignment,onBack,onStartNew}:{consignment:Consignment;onBack:()=>void;onStartNew:()=>void}) {
  const [tab,setTab]=useState<Tab>("to_print");
  const [rows,setRows]=useState<ConsignmentLine[]>([]);
  const [selected,setSelected]=useState(new Set<string>());
  const [search,setSearch]=useState(""), [format,setFormat]=useState("");
  const [errorsOnly,setErrorsOnly]=useState(false), [selectedOnly,setSelectedOnly]=useState(false);
  const [loading,setLoading]=useState(true), [error,setError]=useState(""), [notice,setNotice]=useState("");
  const [drawer,setDrawer]=useState<ConsignmentLine|null>(null), [confirm,setConfirm]=useState<"print"|"archive"|null>(null);
  const debounced=useDebouncedValue(search,300);

  function load(){
    setLoading(true); setError("");
    const qs=queryString({search:debounced,workflow_state:tab==="to_print"?undefined:tab==="errors"?undefined:tab,format_key:format,errors_only:tab==="errors"||errorsOnly,selected_only:selectedOnly,page_size:100});
    api<LinePage>(`/consignments/${consignment.id}/lines?${qs}`)
      .then(data=>{setRows(data.items);setSelected(new Set(data.items.filter(row=>row.selected_for_print).map(row=>row.id)));})
      .catch(reason=>setError(reason.message)).finally(()=>setLoading(false));
  }
  useEffect(load,[consignment.id,debounced,format,errorsOnly,selectedOnly,tab]);

  async function prepare(){try{const job=await api<{id:string}>("/print-jobs",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({consignment_id:consignment.id,line_ids:[...selected]})});setNotice(`Print job ${job.id.slice(0,8)} prepared. The line is not Printed until successful completion.`);}catch(reason){setNotice(reason instanceof Error?reason.message:"Preparation failed");}finally{setConfirm(null)}}
  async function archive(){await api(`/consignments/${consignment.id}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({status:"archived"})});setConfirm(null);onStartNew()}

  return <section className="content">
    <button className="back-link" onClick={onBack}><ArrowLeft size={15}/>All consignments</button>
    <div className="workspace-header"><div><span className={`badge ${consignment.marketplace}`}><b>{consignment.marketplace[0]}</b>{consignment.marketplace}</span><h1>{consignment.name}</h1><p>{consignment.account_name} · {consignment.reference_number||"No reference"} · <StatusBadge status={consignment.status}/></p></div><div><button className="secondary" onClick={()=>setConfirm("archive")}><Archive size={15}/>Finish & Archive</button><button className="primary" disabled={!selected.size} onClick={()=>setConfirm("print")}><Printer size={15}/>Prepare Print Job ({selected.size})</button></div></div>
    <div className="workspace-tabs"><button className={tab==="to_print"?"active":""} onClick={()=>setTab("to_print")}>To Print <b>{consignment.to_print??""}</b></button><button className={tab==="printed"?"active":""} onClick={()=>setTab("printed")}>Printed / Reprint <b>{consignment.printed??""}</b></button><button className={tab==="errors"?"active":""} onClick={()=>setTab("errors")}>Errors <b>{consignment.blocked??""}</b></button></div>
    {notice&&<div className="notice">{notice}</div>}
    <div className="toolbar"><label className="inventory-search">Search identifiers or title<input aria-label="Search lines" value={search} onChange={e=>setSearch(e.target.value)}/></label><input className="filter-input" aria-label="Filter format" placeholder="Format" value={format} onChange={e=>setFormat(e.target.value)}/><label className="check-filter"><input type="checkbox" checked={errorsOnly} onChange={e=>setErrorsOnly(e.target.checked)}/>Errors only</label><label className="check-filter"><input type="checkbox" checked={selectedOnly} onChange={e=>setSelectedOnly(e.target.checked)}/>Selected only</label><span className="toolbar-spacer"/><button className="tool-button" onClick={()=>setSelected(new Set())}>Clear selection</button></div>
    {loading?<LoadingSkeleton/>:error?<ErrorState message={error} retry={load}/>:rows.length?<ConsignmentTable rows={rows} selected={selected} setSelected={setSelected} onOpen={setDrawer} onChanged={updated=>setRows(rows.map(row=>row.id===updated.id?updated:row))}/>:<EmptyState title={tab==="printed"?"Nothing printed yet":"No matching rows"} detail={tab==="printed"?"Preparing a job does not mark rows Printed. Successful completion will appear here.":"Adjust the server-side search and filters."}/>}
    {drawer&&<ConsignmentDrawer line={drawer} consignment={consignment} onClose={()=>setDrawer(null)} onPrepare={()=>setConfirm("print")}/>}
    {confirm==="print"&&<ConfirmDialog title="Prepare immutable print job?" message={`${selected.size} selected, valid To Print row(s) will be snapshotted. No label is sent to a printer in Phase 2.`} confirmLabel="Prepare job" onCancel={()=>setConfirm(null)} onConfirm={()=>void prepare()}/>}
    {confirm==="archive"&&<ConfirmDialog title="Finish and archive?" message="This closes the workspace and starts fresh next time. Historical print records are retained." confirmLabel="Archive consignment" onCancel={()=>setConfirm(null)} onConfirm={()=>void archive()}/>}
  </section>;
}
