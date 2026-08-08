import { AlertTriangle, Inbox } from "lucide-react";
export function LoadingSkeleton(){return <div className="skeleton-list" aria-label="Loading">{Array.from({length:8},(_,i)=><i key={i}/>)}</div>}
export function EmptyState({title,detail}:{title:string;detail:string}){return <div className="empty"><Inbox size={30}/><strong>{title}</strong><p>{detail}</p></div>}
export function ErrorState({message,retry}:{message:string;retry?:()=>void}){return <div className="empty error-state"><AlertTriangle size={30}/><strong>Couldn’t load this view</strong><p>{message}</p>{retry&&<button className="secondary" onClick={retry}>Try again</button>}</div>}
