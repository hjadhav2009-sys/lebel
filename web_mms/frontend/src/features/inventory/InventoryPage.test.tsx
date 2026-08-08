import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { InventoryPage } from "./InventoryPage";

const product={id:"p1",sku:"SKU-1",title:"Server product",brand:"MMS",mrp:799,category:"Necklace",source_file:"catalog.xlsx",source_template:"template-a",source_category:"necklace",extra_attributes:{},created_at:"2026-08-01T00:00:00Z",updated_at:"2026-08-08T00:00:00Z",account:{id:"a1",marketplace:"amazon",name:"Mumbai",is_active:true,created_at:"2026-01-01T00:00:00Z",updated_at:"2026-01-01T00:00:00Z"},identifiers:[],images:[]};

beforeEach(()=>{vi.stubGlobal("fetch",vi.fn(async(input:string|URL)=>{const url=String(input);const body=url.includes("/accounts")?[]:url.includes("/stats")?{total:1,with_images:0,missing_images:1}:{items:[product],total:1,page:1,page_size:50,page_count:1};return {ok:true,json:async()=>body} as Response}))});

test("renders API totals and rows without a thumbnail column",async()=>{render(<InventoryPage/>);expect(await screen.findByText("Server product")).toBeTruthy();expect(document.querySelector(".stats span")?.textContent).toContain("1 total products");expect(screen.queryByText("Image",{selector:"th"})).toBeNull()});
test("debounced search creates a server request",async()=>{render(<InventoryPage/>);const input=screen.getByPlaceholderText(/Search SKU/);fireEvent.change(input,{target:{value:"ABC 123"}});await waitFor(()=>expect(vi.mocked(fetch).mock.calls.some(call=>String(call[0]).includes("search=ABC+123"))).toBe(true),{timeout:1200})});
