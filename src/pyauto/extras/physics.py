import math
import numpy
import owlready2

from shapely import geometry
from owlready2_augmentator import augment, augment_class, AugmentationType
from pyauto import auto

with auto._world.get_ontology(auto.Ontology.Physics.value):

    ge = auto._world.get_ontology(auto.Ontology.GeoSPARQL.value)

    class Spatial_Object(owlready2.Thing):
        def set_geometry(self, x: float, y: float, length: float = None, width: float = None):
            geom = ge.Geometry()
            if length is None or width is None:
                geom.asWKT = [geometry.Point(x, y).wkt]
            else:
                geom.asWKT = [geometry.Polygon([((x - length) / 2, (y - width) / 2),
                                                ((x - length) / 2, (y + width) / 2),
                                                ((x + length) / 2, (y + width) / 2),
                                                ((x + length) / 2, (y - width) / 2)]).wkt]
            self.hasGeometry = [geom]

    @augment_class
    class Dynamical_Object(owlready2.Thing):

        def set_velocity(self, x: float, y: float, z: float = 0):
            self.has_velocity_x = x
            self.has_velocity_y = y
            self.has_velocity_z = z

        @augment(AugmentationType.DATA_PROPERTY, "has_speed")
        def set_speed(self):
            v = [x for x in [self.has_velocity_x, self.has_velocity_y, self.has_velocity_z] if x is not None]
            if len(v) > 1:
                angle = math.degrees(math.atan2(v[1], v[0])) % 360
                sign = 1
                if 90 < angle < 270:
                    sign = -1
                return float(sign * numpy.linalg.norm(v))
