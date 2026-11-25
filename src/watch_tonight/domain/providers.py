"""Launch countries and a minimal static list of their main streaming services.

IDs are TMDB watch-provider IDs, from spike 08 Q5 (`docs/spikes/08-tmdb-and-providers.md`).
The real curated list, with ad tiers and channels, is built in the ingest feature (feat-020).
"""

from collections.abc import Mapping
from typing import Final, Literal

Country = Literal["ES", "US", "BO"]

PROVIDERS: Final[Mapping[Country, Mapping[int, str]]] = {
    "ES": {
        8: "Netflix",
        119: "Amazon Prime Video",
        337: "Disney Plus",
        149: "Movistar Plus+ Ficción Total",
        1899: "HBO Max",
        1773: "SkyShowtime",
        63: "Filmin",
        350: "Apple TV+",
    },
    "US": {
        8: "Netflix",
        9: "Amazon Prime Video",
        337: "Disney Plus",
        1899: "HBO Max",
        15: "Hulu",
        386: "Peacock Premium",
        350: "Apple TV+",
    },
    "BO": {
        8: "Netflix",
        119: "Amazon Prime Video",
        337: "Disney Plus",
        1899: "HBO Max",
        531: "Paramount Plus",
    },
}


def streamable_key(country: Country, provider_id: int) -> str:
    """The `"country:provider"` string stored in `Movie.streamable` (architecture §5)."""
    return f"{country}:{provider_id}"
