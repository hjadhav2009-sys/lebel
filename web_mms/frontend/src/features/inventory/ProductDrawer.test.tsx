import { fireEvent, render, screen } from "@testing-library/react";
import { ProductDrawer } from "./ProductDrawer";
import type { Product } from "../../types";

const product:Product={id:"p1",sku:"SKU-1",title:"Test necklace",brand:"MMS",mrp:799,category:"Necklace",source_file:"catalog.xlsx",source_template:"template-a",source_category:"necklace",extra_attributes:{},created_at:"2026-08-01T00:00:00Z",updated_at:"2026-08-08T00:00:00Z",account:{id:"a1",marketplace:"amazon",name:"Mumbai",is_active:true,created_at:"2026-01-01T00:00:00Z",updated_at:"2026-01-01T00:00:00Z"},identifiers:[{kind:"asin",value:"B0123",source:"import"}],images:[{id:"i1",url:"https://example.test/image.jpg",kind:"main",position:0,source:"import",status:"available"}]};

test("images render only after the Images tab opens",()=>{render(<ProductDrawer product={product} close={()=>{}}/>);expect(screen.queryByAltText("Main product")).toBeNull();fireEvent.click(screen.getByText("Images"));expect(screen.getByAltText("Main product")).toBeTruthy()});
test("drawer close control calls the close handler",()=>{const close=vi.fn();render(<ProductDrawer product={product} close={close}/>);fireEvent.click(screen.getByLabelText("Close product drawer"));expect(close).toHaveBeenCalledOnce()});
