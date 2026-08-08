import { useEffect, useState } from "react";
import { api } from "./api/client";
import { AccountsPage } from "./features/accounts/AccountsPage";
import { ErrorsPage } from "./features/errors/ErrorsPage";
import { ImportsPage } from "./features/imports/ImportsPage";
import { InventoryPage } from "./features/inventory/InventoryPage";
import { AppLayout } from "./layouts/AppLayout";
import { ShellPage } from "./pages/ShellPage";
import type { CurrentUser } from "./types";

const descriptions:Record<string,string>={Dashboard:"Live operational summary foundation.",Packing:"Future adapter for the legacy app/ order and packing parser.",Consignments:"Future marketplace workflow for To Print and Printed / Reprint.","Print Queue":"Durable print jobs for the future outbound Windows agent.","PDF Tools":"Future adapter for tools/flipkart_cropper PDF processing.",Printers:"Outbound print agents, printers, and profile configuration.",Settings:"Shared platform configuration.",Users:"Role and user administration foundation.","Audit Log":"User-attributed operational history.",Admin:"System administration."};
export default function App(){const[active,setActive]=useState("Inventory"),[user,setUser]=useState<CurrentUser|null>(null);useEffect(()=>{api<CurrentUser>("/users/me").then(setUser).catch(()=>{})},[]);let page=active==="Inventory"?<InventoryPage/>:active==="Imports"?<ImportsPage/>:active==="Accounts"?<AccountsPage/>:active==="Errors"?<ErrorsPage/>:<ShellPage name={active} description={descriptions[active]??"Module foundation."}/>;return <AppLayout active={active} setActive={setActive} user={user}>{page}</AppLayout>}
