from copy import deepcopy

from app.renderers.flipkart_hybrid_tspl_v1 import FlipkartHybridTSPLRenderer
from app.renderers.font_registry import resolve_font


class FlipkartHybridTSPLRendererV2(FlipkartHybridTSPLRenderer):
    key="flipkart_hybrid_tspl_v2"
    version="2.0.0"

    def _layout(self,profile:dict)->dict:
        effective=deepcopy(profile);config=effective.setdefault("config",{});identity=resolve_font(str(config.get("font_key") or "mms_default_sans"))
        config["font_path"]=identity["font_path"]
        layout=super()._layout(effective);layout.update(identity)
        return layout

    def validate(self,snapshots:list[dict],profile:dict):
        result=super().validate(snapshots,profile)
        result.diagnostics["field_orders"]={str(item.get("format")): [name for name,_ in self._field_values(item)] for item in snapshots}
        return result
