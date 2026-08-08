import { useState } from "react";
import { AddressProfiles } from "./AddressProfiles";
import { LabelFormats } from "./LabelFormats";
export function SettingsPage(){const[tab,setTab]=useState<"addresses"|"formats">("addresses");return <section className="content"><div className="page-heading"><div><span className="eyebrow">CONFIGURATION</span><h1>Settings</h1><p>Account-scoped print preparation metadata.</p></div></div><div className="section-tabs"><button className={tab==="addresses"?"active":""} onClick={()=>setTab("addresses")}>Address Profiles</button><button className={tab==="formats"?"active":""} onClick={()=>setTab("formats")}>Label Formats</button></div>{tab==="addresses"?<AddressProfiles/>:<LabelFormats/>}</section>}
