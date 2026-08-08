from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.renderers.base import (PreviewResult, RenderResult, RendererError, RenderValidationResult,
    format_mrp, mm_to_dots, plan_two_up, png_bytes, snapshot_value, validate_barcode)

FORMAT_FIELDS = {
    "key_chain": ["Brand","Model Number","Comment","Color"],
    "pendant_locket": ["Brand","Model Number","Plating","Brand Color","Body Material"],
    "bangle_bracelet_armlet": ["Brand","Model Number","Bangle Size","Diameter","Color","Pack Of"],
    "earring": ["Brand","Model Number","Sales Package","Type","Color"],
    "jewellery_set": ["Brand","Model Number","Sales Package Id","Color"],
    "necklace_chain": ["Brand","Base Material","Type","Model Number","Color"],
    "car_hanging_ornament": ["Brand","Model Name","Model Number","Color"],
}
COMMON_FIELDS = ["Net Quantity","Dimensions","MRP","Generic Name"]


class FlipkartHybridTSPLRenderer:
    key = "flipkart_hybrid_tspl_v1"
    version = "1.0.0-experimental"

    def _layout(self, profile: dict) -> dict:
        dpi = int(profile.get("dpi",203)); config = profile.get("config") or {}
        font_path = str(config.get("font_path") or "")
        if not font_path or not Path(font_path).is_file(): raise RendererError("FONT_NOT_AVAILABLE", "Configured production TrueType font is unavailable.")
        width=mm_to_dots(profile.get("media_width_mm",101.5),dpi); height=mm_to_dots(profile.get("media_height_mm",50),dpi); label_width=width//2
        barcode_y=int(config.get("barcode_y",height-92)); barcode_height=int(config.get("barcode_height",52))
        if barcode_y < 100 or barcode_y+barcode_height+20>height: raise RendererError("INVALID_LAYOUT_PROFILE","Barcode zone is outside the label.")
        return {"dpi":dpi,"width":width,"height":height,"label_width":label_width,"margin":int(config.get("margin",12)),
            "heading_height":int(config.get("heading_height",28)),"product_top":int(config.get("product_top",35)),
            "barcode_y":barcode_y,"barcode_height":barcode_height,"barcode_quiet":int(config.get("barcode_quiet",24)),
            "font_path":font_path,"font_sizes":config.get("font_sizes",[16,14,12]),"layout_version":int(profile.get("layout_version",1))}

    @staticmethod
    def _field_values(snapshot: dict) -> list[tuple[str,str]]:
        format_key=str(snapshot.get("format") or "")
        if format_key not in FORMAT_FIELDS: raise RendererError("INVALID_LAYOUT_PROFILE",f"Unsupported Flipkart format: {format_key}")
        rows=[]
        for name in FORMAT_FIELDS[format_key]: rows.append((name,str(snapshot_value(snapshot,name,"") or "")))
        net=snapshot.get("net_quantity") or {}; common={"Net Quantity":f'{net.get("value","")} {net.get("unit","")}'.strip(),
            "Dimensions":str(snapshot_value(snapshot,"Dimensions","") or ""),"MRP":format_mrp(snapshot.get("mrp")),
            "Generic Name":str(snapshot.get("generic_name") or snapshot_value(snapshot,"Generic Name","") or "")}
        rows.extend((name,common[name]) for name in COMMON_FIELDS)
        return rows

    @staticmethod
    def _wrap(draw:ImageDraw.ImageDraw,text:str,font:ImageFont.FreeTypeFont,max_width:int)->list[str]:
        words=text.split(); lines=[]; current=""
        for word in words or [""]:
            candidate=f"{current} {word}".strip()
            if current and draw.textbbox((0,0),candidate,font=font)[2]>max_width: lines.append(current); current=word
            else: current=candidate
        if current: lines.append(current)
        return lines

    def _measure(self,snapshot:dict,layout:dict):
        rows=self._field_values(snapshot); available=layout["barcode_y"]-layout["product_top"]-6; max_width=layout["label_width"]-2*layout["margin"]
        probe=Image.new("1",(layout["label_width"],layout["height"]),1); draw=ImageDraw.Draw(probe)
        for size in layout["font_sizes"]:
            font=ImageFont.truetype(layout["font_path"],int(size)); line_height=draw.textbbox((0,0),"Ag",font=font)[3]+3; wrapped=[]
            for field,value in rows:
                if not value: raise RendererError("MISSING_DIMENSIONS" if field=="Dimensions" else "MISSING_REQUIRED_FIELD",f"Required field {field} is missing.",{"field":field})
                wrapped.extend((field,line) for line in self._wrap(draw,f"{field}: {value}",font,max_width))
            required=len(wrapped)*line_height
            if required<=available: return font,line_height,wrapped,{"font_size":size,"required_height":required,"available_height":available}
        raise RendererError("LABEL_TEXT_OVERFLOW","Required Flipkart text does not fit at minimum-readable size.",{"format":snapshot.get("format"),"required_height":required,"available_height":available})

    def validate(self,snapshots:list[dict],profile:dict)->RenderValidationResult:
        layout=self._layout(profile); errors=[]; decisions=[]
        for index,snapshot in enumerate(snapshots):
            try:
                validate_barcode(snapshot.get("fsn") or snapshot.get("listing_id")); _,_,_,decision=self._measure(snapshot,layout); decisions.append(decision)
            except RendererError as exc: errors.append({"code":exc.code,"line":index,"message":exc.message,**exc.diagnostics})
        return RenderValidationResult(not errors,errors,diagnostics={"layout":layout,"overflow_decisions":decisions,
            "barcode_zone":[layout["barcode_y"],layout["barcode_y"]+layout["barcode_height"]],"text_zone":[layout["product_top"],layout["barcode_y"]]})

    def _text_bitmap(self,snapshot:dict,layout:dict)->Image.Image:
        image=Image.new("1",(layout["label_width"],layout["barcode_y"]),1); draw=ImageDraw.Draw(image); font,line_height,rows,_=self._measure(snapshot,layout)
        heading=str(snapshot.get("generic_name") or snapshot_value(snapshot,"Generic Name","Product")); draw.text((layout["margin"],4),heading,font=font,fill=0)
        y=layout["product_top"]
        for _,line in rows: draw.text((layout["margin"],y),line,font=font,fill=0); y+=line_height
        return image

    def render(self,snapshots:list[dict],profile:dict)->RenderResult:
        validation=self.validate(snapshots,profile)
        if not validation.fits: raise RendererError(validation.errors[0]["code"],validation.errors[0].get("message","Flipkart validation failed."),validation.diagnostics)
        layout=validation.diagnostics["layout"]; pages=plan_two_up(snapshots); chunks=[f'SIZE {profile.get("media_width_mm",101.5)} mm,{profile.get("media_height_mm",50)} mm\r\n'.encode(),f'GAP {profile.get("gap_mm",2)} mm,0 mm\r\n'.encode()]
        for left,right in pages:
            chunks.append(b"CLS\r\n")
            for slot,snapshot in enumerate((left,right)):
                if snapshot is None: continue
                bitmap=self._text_bitmap(snapshot,layout); packed=bitmap.tobytes(); width_bytes=(layout["label_width"]+7)//8; x=slot*layout["label_width"]
                chunks.extend([f"BITMAP {x},0,{width_bytes},{layout['barcode_y']},0,".encode("ascii"),packed,b"\r\n"])
                barcode=validate_barcode(snapshot.get("fsn") or snapshot.get("listing_id")); barcode_x=x+layout["barcode_quiet"]
                chunks.append(f'BARCODE {barcode_x},{layout["barcode_y"]},"128",{layout["barcode_height"]},1,0,2,2,"{barcode}"\r\n'.encode("ascii"))
            chunks.append(b"PRINT 1,1\r\n")
        raw=b"".join(chunks); labels=sum(int(s["print_quantity"]) for s in snapshots)
        return RenderResult(raw,"application/vnd.tsc-tspl","raw_tspl",self.key,self.version,labels,[],{**validation.diagnostics,"pairs":len(pages),"total_labels":labels,"odd_final_label":bool(pages and pages[-1][1] is None)})

    def preview(self,snapshots:list[dict],profile:dict)->PreviewResult:
        validation=self.validate(snapshots,profile); layout=self._layout(profile); page=Image.new("RGB",(layout["width"],layout["height"]),"white"); draw=ImageDraw.Draw(page)
        labels=plan_two_up(snapshots)[0]
        for slot,snapshot in enumerate(labels):
            if snapshot is None: continue
            x=slot*layout["label_width"]; page.paste(self._text_bitmap(snapshot,layout).convert("RGB"),(x,0)); draw.rectangle((x+layout["barcode_quiet"],layout["barcode_y"],x+layout["label_width"]-layout["barcode_quiet"],layout["barcode_y"]+layout["barcode_height"]),outline="black",width=2)
            draw.text((x+layout["barcode_quiet"],layout["barcode_y"]+layout["barcode_height"]+2),str(snapshot.get("fsn") or snapshot.get("listing_id") or ""),fill="black")
        return PreviewResult(png_bytes(page),{**validation.diagnostics,"fits":validation.fits,"errors":validation.errors})
