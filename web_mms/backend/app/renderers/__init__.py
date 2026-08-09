from app.renderers.amazon_dynamic_tspl_v1 import AmazonDynamicTSPLRenderer
from app.renderers.amazon_dynamic_tspl_v2 import AmazonDynamicTSPLRendererV2
from app.renderers.flipkart_hybrid_tspl_v1 import FlipkartHybridTSPLRenderer
from app.renderers.flipkart_hybrid_tspl_v2 import FlipkartHybridTSPLRendererV2

RENDERERS = {
    AmazonDynamicTSPLRenderer.key: AmazonDynamicTSPLRenderer(),
    AmazonDynamicTSPLRendererV2.key: AmazonDynamicTSPLRendererV2(),
    FlipkartHybridTSPLRenderer.key: FlipkartHybridTSPLRenderer(),
    FlipkartHybridTSPLRendererV2.key: FlipkartHybridTSPLRendererV2(),
}


def get_renderer(key: str):
    renderer = RENDERERS.get(key)
    if not renderer:
        raise ValueError("HISTORICAL_RENDERER_UNAVAILABLE")
    return renderer
