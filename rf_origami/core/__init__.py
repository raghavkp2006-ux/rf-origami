"""Core module for RF Origami Design Generator.

Contains fundamental data structures and mathematical representations for:
- 3D Geometry and vector operations
- Crease pattern graphs and flat-foldability rules
- Folded 3D mesh representation
- Parameter definition, validation, and design-space sampling
"""

from rf_origami.core.geometry import (
    Vector3D,
    Point3D,
    rotation_matrix_axis_angle,
    rotation_matrix_euler,
    create_affine_matrix,
    transform_points,
    polygon_normal,
    polygon_area,
    polygon_centroid,
    is_coplanar,
)
from rf_origami.core.crease_pattern import (
    CreaseType,
    Crease,
    Face,
    CreasePattern,
)
from rf_origami.core.mesh import (
    FoldedMesh,
)
from rf_origami.core.parameters import (
    ParameterType,
    Parameter,
    ParameterSet,
)

__all__ = [
    "Vector3D",
    "Point3D",
    "rotation_matrix_axis_angle",
    "rotation_matrix_euler",
    "create_affine_matrix",
    "transform_points",
    "polygon_normal",
    "polygon_area",
    "polygon_centroid",
    "is_coplanar",
    "CreaseType",
    "Crease",
    "Face",
    "CreasePattern",
    "FoldedMesh",
    "ParameterType",
    "Parameter",
    "ParameterSet",
]
