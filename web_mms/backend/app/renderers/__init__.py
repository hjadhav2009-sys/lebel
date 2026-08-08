from app.renderers.amazon_dynamic_tspl_v1 import AmazonDynamicTSPLRenderer
from app.renderers.flipkart_hybrid_tspl_v1 import FlipkartHybridTSPLRenderer

RENDERERS = {
    AmazonDynamicTSPLRenderer.key: AmazonDynamicTSPLRenderer(),
    FlipkartHybridTSPLRenderer.key: FlipkartHybridTSPLRenderer(),
}


def get_renderer(key: str):
    renderer = RENDERERS.get(key)
    if not renderer:
        raise ValueError("HISTORICAL_RENDERER_UNAVAILABLE")
    return renderer
