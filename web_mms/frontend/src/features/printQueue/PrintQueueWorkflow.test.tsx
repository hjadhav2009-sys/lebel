import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { PrintJobDrawer } from "./PrintJobDrawer";

const job={id:"job-12345678",consignment_id:"c1",account_id:"a1",marketplace:"amazon",status:"completed",rows:1,labels:2,created_at:"2026-01-01",updated_at:"2026-01-01",simulation:true};
const detail={...job,simulation_enabled:true,lines:[{id:"pl1",copies:2,status:"completed",result:"success",snapshot:{sku:"S1",print_quantity:2}}],events:[{id:"e1",type:"completed",created_at:"2026-01-01",payload:{result:"success"}}]};

test("Printed exact snapshot reprint creates a new API request",async()=>{const fetchMock=vi.fn((url:string,init?:RequestInit)=>Promise.resolve(new Response(JSON.stringify(init?.method==="POST"?{id:"new-job"}:detail),{status:init?.method==="POST"?201:200,headers:{"Content-Type":"application/json"}})));vi.stubGlobal("fetch",fetchMock);render(<PrintJobDrawer job={job} onClose={vi.fn()} onChanged={vi.fn()}/>);await waitFor(()=>expect(screen.getByText("Reprint Exact Snapshot")).toBeTruthy());fireEvent.click(screen.getByText("Reprint Exact Snapshot"));await waitFor(()=>expect(fetchMock.mock.calls.some(call=>String(call[0]).endsWith("/reprint"))).toBe(true))});

test("print job drawer exposes immutable snapshot and events",async()=>{vi.stubGlobal("fetch",vi.fn(()=>Promise.resolve(new Response(JSON.stringify(detail),{status:200,headers:{"Content-Type":"application/json"}}))));render(<PrintJobDrawer job={job} onClose={vi.fn()} onChanged={vi.fn()}/>);fireEvent.click(screen.getByText("Snapshot"));await waitFor(()=>expect(screen.getByText(/print_quantity/)).toBeTruthy());fireEvent.click(screen.getByText("Events"));expect(screen.getByText("completed")).toBeTruthy()});
