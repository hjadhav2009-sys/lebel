from PIL import Image,ImageDraw

from app.renderers.base import PreviewResult,RenderResult,RendererError,RenderValidationResult,format_mrp,mm_to_dots,plan_two_up,png_bytes,tspl_escape,validate_barcode


class AmazonDynamicTSPLRendererV2:
    key="amazon_dynamic_tspl_v2";version="2.0.0"

    def _layout(self,profile:dict)->dict:
        dpi=int(profile.get("dpi",203));config=profile.get("config") or {};width=mm_to_dots(profile.get("media_width_mm",101.5),dpi);height=mm_to_dots(profile.get("media_height_mm",50),dpi);label_width=width//2
        if dpi not in {203,300}:raise RendererError("INVALID_LAYOUT_PROFILE","Only approved 203/300 DPI profiles are supported.")
        return {"dpi":dpi,"width":width,"height":height,"label_width":label_width,"origins":[int(config.get("left_origin",12)),int(config.get("right_origin",label_width+12))],
            "heading_y":int(config.get("heading_y",8)),"product_y":int(config.get("product_y",30)),"product_row_gap":int(config.get("product_row_gap",18)),
            "care_x_offset":int(config.get("care_x_offset",0)),"care_y":int(config.get("care_y",120)),"care_font":str(config.get("care_font","0")),
            "address_x_offset":int(config.get("address_x_offset",0)),"address_y":int(config.get("address_y",149)),"address_font":str(config.get("address_font","0")),
            "address_line_gap":int(config.get("address_line_gap",16)),"max_address_lines":int(config.get("max_address_lines",6)),
            "barcode_y":int(config.get("barcode_y",252)),"barcode_height":int(config.get("barcode_height",46)),"barcode_x_offset":int(config.get("barcode_x_offset",24)),
            "readable_fnsku_y":int(config.get("readable_fnsku_y",306)),"bottom_title_y":int(config.get("bottom_title_y",330)),
            "max_chars":int(config.get("max_chars",44)),"layout_version":int(profile.get("layout_version",1))}

    @staticmethod
    def _address(snapshot:dict)->list[str]:
        address=snapshot.get("address_profile") or {}
        return [value for value in [address.get("marketed_by"),address.get("address_line_1"),address.get("address_line_2"),address.get("city_state"),
            f'Email Id: {address.get("email")}' if address.get("email") else None,f'Contact: {address.get("phone")}' if address.get("phone") else None,
            f'Origin: {address.get("origin")}' if address.get("origin") else None] if value]

    def _content(self,snapshot:dict)->dict:
        net=snapshot.get("net_quantity") or {};address=self._address(snapshot)
        return {"heading":"Product Information","rows":[("Brand",snapshot.get("brand")),("SKU No / Merchant SKU",snapshot.get("sku")),
            ("Net Quantity",f'{net.get("value","")} {net.get("unit","")}'.strip()),("MRP",format_mrp(snapshot.get("mrp"))),
            ("Generic Name",snapshot.get("generic_name"))],"care_heading":["Manufactured by / Marketed By /","Customer care Details:"],
            "address":address,"fnsku":validate_barcode(snapshot.get("fnsku")),"bottom_title":snapshot.get("title")}

    def validate(self,snapshots:list[dict],profile:dict)->RenderValidationResult:
        layout=self._layout(profile);errors=[]
        for index,snapshot in enumerate(snapshots):
            try:content=self._content(snapshot)
            except RendererError as exc:errors.append({"line":index,"code":exc.code,"message":exc.message});continue
            required=[content["heading"],*content["care_heading"],content["fnsku"],content["bottom_title"],*[f"{name}: {value}" for name,value in content["rows"]],*content["address"]]
            if any(value in (None,"") for value in required):errors.append({"line":index,"code":"MISSING_REQUIRED_FIELD"});continue
            too_long=[str(value) for value in required if len(str(value))>layout["max_chars"]]
            address_bottom=layout["address_y"]+len(content["address"])*layout["address_line_gap"]
            if too_long or len(content["address"])>layout["max_address_lines"] or address_bottom>layout["barcode_y"] or layout["bottom_title_y"]+18>layout["height"]:
                errors.append({"line":index,"code":"LABEL_TEXT_OVERFLOW","values":too_long,"address_bottom":address_bottom})
        return RenderValidationResult(not errors,errors,diagnostics={"layout":layout,"barcode_zone":[layout["barcode_y"],layout["barcode_y"]+layout["barcode_height"]],
            "preview_notice":"Preview is layout guidance; physical TSC output is authoritative for native printer-font metrics."})

    def _commands(self,snapshot:dict,x:int,layout:dict)->list[str]:
        content=self._content(snapshot);commands=[f'TEXT {x},{layout["heading_y"]},"0",0,1,1,"{tspl_escape(content["heading"])}"'];y=layout["product_y"]
        for name,value in content["rows"]:commands.append(f'TEXT {x},{y},"0",0,1,1,"{tspl_escape(name)}: {tspl_escape(value)}"');y+=layout["product_row_gap"]
        for index,value in enumerate(content["care_heading"]):commands.append(f'TEXT {x+layout["care_x_offset"]},{layout["care_y"]+index*14},"{layout["care_font"]}",0,1,1,"{tspl_escape(value)}"')
        y=layout["address_y"]
        for value in content["address"]:commands.append(f'TEXT {x+layout["address_x_offset"]},{y},"{layout["address_font"]}",0,1,1,"{tspl_escape(value)}"');y+=layout["address_line_gap"]
        commands.extend([f'BARCODE {x+layout["barcode_x_offset"]},{layout["barcode_y"]},"128",{layout["barcode_height"]},0,0,2,2,"{content["fnsku"]}"',
            f'TEXT {x+layout["barcode_x_offset"]},{layout["readable_fnsku_y"]},"0",0,1,1,"{content["fnsku"]}"',
            f'TEXT {x},{layout["bottom_title_y"]},"0",0,1,1,"{tspl_escape(content["bottom_title"])}"'])
        return commands

    def render(self,snapshots:list[dict],profile:dict)->RenderResult:
        validation=self.validate(snapshots,profile)
        if not validation.fits:raise RendererError(validation.errors[0]["code"],"Amazon v2 content does not fit.",validation.diagnostics)
        layout=validation.diagnostics["layout"];pages=plan_two_up(snapshots);output=[f'SIZE {profile.get("media_width_mm",101.5)} mm,{profile.get("media_height_mm",50)} mm',f'GAP {profile.get("gap_mm",2)} mm,0 mm',"DIRECTION 1"]
        for left,right in pages:
            output.append("CLS");output.extend(self._commands(left,layout["origins"][0],layout))
            if right:output.extend(self._commands(right,layout["origins"][1],layout))
            output.append("PRINT 1,1")
        raw=("\r\n".join(output)+"\r\n").encode("cp1252",errors="strict")
        return RenderResult(raw,"application/vnd.tsc-tspl","raw_tspl",self.key,self.version,sum(int(item["print_quantity"]) for item in snapshots),[],{**validation.diagnostics,"pairs":len(pages),"odd_final_label":bool(pages and pages[-1][1] is None)})

    def preview(self,snapshots:list[dict],profile:dict)->PreviewResult:
        validation=self.validate(snapshots,profile);layout=validation.diagnostics["layout"];image=Image.new("RGB",(layout["width"],layout["height"]),"white");draw=ImageDraw.Draw(image)
        for slot,snapshot in enumerate(plan_two_up(snapshots)[0]):
            if not snapshot:continue
            x=slot*layout["label_width"]+10;content=self._content(snapshot);draw.text((x,layout["heading_y"]),content["heading"],fill="black");y=layout["product_y"]
            for name,value in content["rows"]:draw.text((x,y),f"{name}: {value}",fill="black");y+=layout["product_row_gap"]
            for index,value in enumerate(content["care_heading"]):draw.text((x+layout["care_x_offset"],layout["care_y"]+index*14),value,fill="black")
            y=layout["address_y"]
            for value in content["address"]:draw.text((x+layout["address_x_offset"],y),value,fill="black");y+=layout["address_line_gap"]
            draw.rectangle((x+layout["barcode_x_offset"],layout["barcode_y"],x+layout["label_width"]-24,layout["barcode_y"]+layout["barcode_height"]),outline="black")
            draw.text((x+layout["barcode_x_offset"],layout["readable_fnsku_y"]),content["fnsku"],fill="black")
            draw.text((x,layout["bottom_title_y"]),str(content["bottom_title"]),fill="black")
        return PreviewResult(png_bytes(image),{**validation.diagnostics,"fits":validation.fits,"errors":validation.errors})
