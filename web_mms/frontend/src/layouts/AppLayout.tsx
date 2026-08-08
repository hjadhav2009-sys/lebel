import { AlertTriangle, Boxes, ChevronDown, ClipboardList, FileUp, Gauge, History, PackageCheck, Printer, Scissors, Settings, ShieldCheck, Users } from "lucide-react";
import type { CurrentUser } from "../types";

const groups=[
  ["OVERVIEW",[["Dashboard",Gauge]]],
  ["OPERATIONS",[["Packing",ClipboardList],["Consignments",PackageCheck],["Print Queue",Printer]]],
  ["CATALOG",[["Inventory",Boxes],["Imports",FileUp]]],
  ["TOOLS",[["PDF Tools",Scissors]]],
  ["MANAGEMENT",[["Errors",AlertTriangle],["Accounts",Users],["Printers",Printer],["Settings",Settings]]],
  ["SYSTEM",[["Users",Users],["Audit Log",History],["Admin",ShieldCheck]]],
] as const;

export function AppLayout({active,setActive,user,children}:{active:string;setActive:(value:string)=>void;user:CurrentUser|null;children:React.ReactNode}){return <div className="app-shell"><aside className="sidebar"><div className="brand"><div className="brand-mark">M</div><div><strong>MMS</strong><span>Operations platform</span></div></div><nav className="grouped-nav">{groups.map(([group,items])=><div className="nav-group" key={group}><label>{group}</label>{items.map(([label,Icon])=><button className={active===label?"active":""} onClick={()=>setActive(label)} key={label}><Icon size={17}/><span>{label}</span></button>)}</div>)}</nav><div className="version">MMS Web · Phase 2</div></aside><main><header className="topbar"><div className="workspace-title"><strong>{active}</strong><span>Central operations workspace</span></div><div className="topbar-spacer"/><div className="user"><div>{(user?.display_name??"D").split(" ").map(x=>x[0]).join("").slice(0,2)}</div><span><strong>{user?.display_name??"Loading user…"}</strong><small>{user?.roles.join(", ")}</small></span><ChevronDown size={14}/></div></header>{children}</main></div>}
