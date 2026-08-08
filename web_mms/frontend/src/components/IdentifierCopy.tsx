import { Copy } from "lucide-react";
export function IdentifierCopy({label,value}:{label:string;value?:string}){if(!value)return null;return <div className="identifier-copy"><span><small>{label}</small><code>{value}</code></span><button aria-label={`Copy ${label}`} onClick={()=>navigator.clipboard.writeText(value)}><Copy size={14}/></button></div>}
