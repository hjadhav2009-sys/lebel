from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EnrichedImage:
    url: str
    source: str


class ImageEnrichmentProvider(ABC):
    """On-demand provider boundary. No bulk scraping occurs during catalog import."""

    @abstractmethod
    async def images_for_fsn(self, fsn: str) -> list[EnrichedImage]: ...
