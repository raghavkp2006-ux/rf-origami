"""Origami pattern generators for RF Origami.

Provides procedural generators for:
- BasePattern interface and verification utilities
- MiuraOriPattern (parallelogram herringbone tessellation)
- YoshimuraPattern (triangular/diamond cylinder pattern)
- WaterbombPattern (waterbomb base and tessellations)
- Degree4VertexPattern (isolated degree-4 flat-foldable unit cells)
"""

from rf_origami.patterns.base import BasePattern
from rf_origami.patterns.miura_ori import MiuraOriPattern
from rf_origami.patterns.yoshimura import YoshimuraPattern
from rf_origami.patterns.waterbomb import WaterbombPattern
from rf_origami.patterns.degree4_vertex import Degree4VertexPattern

__all__ = [
    "BasePattern",
    "MiuraOriPattern",
    "YoshimuraPattern",
    "WaterbombPattern",
    "Degree4VertexPattern",
]
