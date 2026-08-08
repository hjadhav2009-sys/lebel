from PIL import Image, ImageDraw

from app.renderers.base import (PreviewResult, RenderResult, RendererError, RenderValidationResult,
    format_mrp, mm_to_dots, plan_two_up, png_bytes, snapshot_value, tspl_escape, validate_barcode)


class AmazonDynamicTSPLRenderer:
    key = "amazon_dynamic_tspl_v1"
    version = "1.0.0"

    def _layout(self, profile: dict) -> dict:
        dpi = int(profile.get("dpi", 203)); config = profile.get("config") or {}
        if dpi not in {203, 300}: raise RendererError("INVALID_LAYOUT_PROFILE", "Only approved 203/300 DPI profiles are supported.")
        width = mm_to_dots(profile.get("media_width_mm", 101.5), dpi); height = mm_to_dots(profile.get("media_height_mm", 50), dpi)
        return {"dpi": dpi, "width": width, "height": height, "label_width": width // 2,
            "left_origin": int(config.get("left_origin", 18)), "right_origin": int(config.get("right_origin", width // 2 + 18)),
            "title_y": int(config.get("title_y", 38)), "product_row_gap": int(config.get("product_row_gap", 25)),
            "care_y": int(config.get("care_y", 205)), "address_y": int(config.get("address_y", 235)),
            "address_line_gap": int(config.get("address_line_gap", 18)), "max_address_lines": int(config.get("max_address_lines", 4)),
            "barcode_y": int(config.get("barcode_y", 300)), "barcode_height": int(config.get("barcode_height", 50)),
            "barcode_margin": int(config.get("barcode_margin", 30)), "layout_version": int(profile.get("layout_version", 1))}

    def validate(self, snapshots: list[dict], profile: dict) -> RenderValidationResult:
        layout = self._layout(profile); errors = []
        for index, snapshot in enumerate(snapshots):
            for field in ("sku", "fnsku", "title", "brand", "mrp", "net_quantity", "address_profile"):
                if not snapshot.get(field): errors.append({"code": "MISSING_REQUIRED_FIELD", "field": field, "line": index})
            try: validate_barcode(snapshot.get("fnsku")); format_mrp(snapshot.get("mrp"))
            except RendererError as exc: errors.append({"code": exc.code, "line": index, "message": exc.message})
            net = snapshot.get("net_quantity") or {}
            if int(net.get("value") or 0) < 1 or not net.get("unit"): errors.append({"code": "INVALID_NET_QTY", "line": index})
            address = snapshot.get("address_profile") or {}
            address_lines = [address.get(k) for k in ("marketed_by", "address_line_1", "address_line_2", "city_state", "email", "phone") if address.get(k)]
            if len(address_lines) > layout["max_address_lines"] + 2: errors.append({"code": "LABEL_TEXT_OVERFLOW", "field": "address", "line": index})
        return RenderValidationResult(not errors, errors, diagnostics={"layout": layout, "barcode_zone": [layout["barcode_y"], layout["barcode_y"] + layout["barcode_height"]]})

    def _label(self, snapshot: dict, x: int, layout: dict) -> list[str]:
        barcode = validate_barcode(snapshot.get("fnsku")); net = snapshot["net_quantity"]
        address = snapshot.get("address_profile") or {}; y = layout["title_y"]
        commands = [f'TEXT {x},{y},"0",0,1,1,"{tspl_escape(snapshot.get("title"))}"']; y += layout["product_row_gap"]
        rows = [("Brand", snapshot.get("brand")), ("Seller SKU", snapshot.get("sku")), ("ASIN", snapshot.get("asin")),
            ("Net Quantity", f'{net["value"]} {net["unit"]}'), ("MRP", format_mrp(snapshot.get("mrp"))),
            ("Generic Name", snapshot_value(snapshot, "generic_name", ""))]
        for key, value in rows:
            commands.append(f'TEXT {x},{y},"0",0,1,1,"{tspl_escape(key)}: {tspl_escape(value)}"'); y += layout["product_row_gap"]
        address_text = ", ".join(str(address.get(k)) for k in ("marketed_by", "address_line_1", "address_line_2", "city_state") if address.get(k))
        commands.append(f'TEXT {x},{layout["address_y"]},"0",0,1,1,"{tspl_escape(address_text)}"')
        commands.append(f'BARCODE {x + layout["barcode_margin"]},{layout["barcode_y"]},"128",{layout["barcode_height"]},1,0,2,2,"{barcode}"')
        return commands

    def render(self, snapshots: list[dict], profile: dict) -> RenderResult:
        validation = self.validate(snapshots, profile)
        if not validation.fits: raise RendererError(validation.errors[0]["code"], "Amazon label validation failed.", validation.diagnostics)
        layout = validation.diagnostics["layout"]; pages = plan_two_up(snapshots)
        output = [f'SIZE {profile.get("media_width_mm",101.5)} mm,{profile.get("media_height_mm",50)} mm', f'GAP {profile.get("gap_mm",2)} mm,0 mm', "DIRECTION 1", "CLS"]
        for left, right in pages:
            output.extend(self._label(left, layout["left_origin"], layout))
            if right: output.extend(self._label(right, layout["right_origin"], layout))
            output.extend(["PRINT 1,1", "CLS"])
        raw = ("\r\n".join(output) + "\r\n").encode("cp1252", errors="strict")
        return RenderResult(raw, "application/vnd.tsc-tspl", "raw_tspl", self.key, self.version,
            sum(int(s["print_quantity"]) for s in snapshots), [], {**validation.diagnostics, "pairs": len(pages), "odd_final_label": bool(pages and pages[-1][1] is None)})

    def preview(self, snapshots: list[dict], profile: dict) -> PreviewResult:
        validation = self.validate(snapshots, profile); layout = self._layout(profile)
        image = Image.new("RGB", (layout["width"], layout["height"]), "white"); draw = ImageDraw.Draw(image)
        draw.rectangle((0,0,layout["label_width"]-2,layout["height"]-2),outline="black"); draw.rectangle((layout["label_width"],0,layout["width"]-2,layout["height"]-2),outline="black")
        labels = plan_two_up(snapshots)[0]
        for slot, snapshot in enumerate(labels):
            if not snapshot: continue
            x = slot * layout["label_width"] + 15; draw.text((x,20),str(snapshot.get("title") or ""),fill="black")
            draw.text((x,60),f'Net Quantity: {snapshot.get("net_quantity",{}).get("value")} {snapshot.get("net_quantity",{}).get("unit")}',fill="black")
            draw.rectangle((x + 20,layout["barcode_y"],x + layout["label_width"]-35,layout["barcode_y"]+layout["barcode_height"]),outline="black")
        return PreviewResult(png_bytes(image), {**validation.diagnostics, "fits": validation.fits, "errors": validation.errors})
