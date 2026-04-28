"""Phase H 드라이런 fixture 5종 — 만재/지은/준호/서연/도윤."""
from .doyoon import FIXTURE as DOYOON
from .jieun import FIXTURE as JIEUN
from .junho import FIXTURE as JUNHO
from .manjae import FIXTURE as MANJAE
from .seoyeon import FIXTURE as SEOYEON

ALL_FIXTURES = {
    "manjae": MANJAE,
    "jieun": JIEUN,
    "junho": JUNHO,
    "seoyeon": SEOYEON,
    "doyoon": DOYOON,
}

__all__ = ["DOYOON", "JIEUN", "JUNHO", "MANJAE", "SEOYEON", "ALL_FIXTURES"]
