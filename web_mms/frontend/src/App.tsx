import { useEffect, useState } from "react";
import { api } from "./api/client";
import { AccountsPage } from "./features/accounts/AccountsPage";
import { LoginPage } from "./features/auth/LoginPage";
import { UsersPage } from "./features/auth/UsersPage";
import { ConsignmentsPage } from "./features/consignments/ConsignmentsPage";
import { ErrorsPage } from "./features/errors/ErrorsPage";
import { ImportsPage } from "./features/imports/ImportsPage";
import { InventoryPage } from "./features/inventory/InventoryPage";
import { PrintersPage } from "./features/printers/PrintersPage";
import { PrintQueuePage } from "./features/printQueue/PrintQueuePage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { AppLayout } from "./layouts/AppLayout";
import { ShellPage } from "./pages/ShellPage";
import type { CurrentUser } from "./types";

const descriptions:Record<string,string>={Dashboard:"Live operational summary foundation.",Packing:"Future adapter for the legacy order and packing parser.","PDF Tools":"Future adapter for Flipkart PDF processing.","Audit Log":"User-attributed operational history.",Admin:"System administration."};
const access:Record<string,string[]>={Printers:["Admin","QC"],Users:["Admin"],Admin:["Admin"],Settings:["Admin"],Accounts:["Admin"],Imports:["Admin","Packing"],Errors:["Admin","QC"]};
export default function App(){const[active,setActive]=useState("Consignments"),[user,setUser]=useState<CurrentUser|null|undefined>(undefined);useEffect(()=>{api<CurrentUser>("/auth/me").then(setUser).catch(()=>setUser(null))},[]);if(user===undefined)return <div className="app-loading">Loading MMS…</div>;if(user===null)return <LoginPage onLogin={setUser}/>;async function logout(){await api("/auth/logout",{method:"POST"});setUser(null)}const permitted=!access[active]||access[active].some(role=>user.roles.includes(role));let page=!permitted?<ShellPage name="Access denied" description="Your assigned role cannot open this module."/>:active==="Inventory"?<InventoryPage/>:active==="Imports"?<ImportsPage/>:active==="Accounts"?<AccountsPage/>:active==="Errors"?<ErrorsPage/>:active==="Consignments"?<ConsignmentsPage/>:active==="Print Queue"?<PrintQueuePage roles={user.roles}/>:active==="Printers"?<PrintersPage roles={user.roles}/>:active==="Users"?<UsersPage/>:active==="Settings"?<SettingsPage/>:<ShellPage name={active} description={descriptions[active]??"Module foundation."}/>;return <AppLayout active={active} setActive={setActive} user={user} onLogout={()=>void logout()}>{page}</AppLayout>}
