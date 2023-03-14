import math
import numpy
import owlready2

from shapely import geometry, wkt
import sympy.geometry
from owlready2_augmentator import augment, augment_class, AugmentationType
from ... import auto

_INTERSECTING_PATH_THRESHOLD = 8   # s, the time interval in which future intersecting paths shall be detected
_INTERSECTING_PATH_MAX_PET = 3     # s, the time interval in which future intersecting paths shall be detected
_HIGH_REL_SPEED_THRESHOLD = 0.25   # rel., the relative difference in total speed in which CP 150 will be augmented
_DEFAULT_SPEED_LIMIT = 50          # km/h, the default speed limit that is assumed
_DEFAULT_MAX_SPEED = 50            # km/h, the default speed maximum speed that is assumed

physics = auto._world.get_ontology(auto.Ontology.Physics.value)
geosparql = auto._world.get_ontology(auto.Ontology.GeoSPARQL.value)

with physics:

    @augment_class
    class Moving_Dynamical_Object(owlready2.Thing):
        @augment(AugmentationType.OBJECT_PROPERTY, "has_intersecting_path")
        def intersects_path_with(self, other: physics.Moving_Dynamical_Object) -> bool:
            """
            Whether this object has an intersecting path with the given other object.
            :param other: The other moving dynamical object.
            :returns: True iff. the intersecting path condition is satisfied.
            """
            if self.has_geometry() and other.has_geometry() and self.has_yaw is not None and other.has_yaw is not None \
                    and self.has_speed and other.has_speed:
                p_1 = wkt.loads(self.hasGeometry[0].asWKT[0]).centroid
                p_2 = wkt.loads(other.hasGeometry[0].asWKT[0]).centroid
                p_self = geometry.Point(p_1.x, p_1.y)
                p_other = geometry.Point(p_2.x, p_2.y)
                if p_self != p_other:
                    self_yaw = self.has_yaw
                    other_yaw = other.has_yaw
                    if self.has_speed < 0:
                        self_yaw = (self.has_yaw + 180) % 360
                    if other.has_speed < 0:
                        other_yaw = (other.has_yaw + 180) % 360
                    p_self_1 = geometry.Point(p_1.x + math.cos(math.radians(self_yaw)),
                                              p_1.y + math.sin(math.radians(self_yaw)))
                    p_other_1 = geometry.Point(p_2.x + math.cos(math.radians(other_yaw)),
                                               p_2.y + math.sin(math.radians(other_yaw)))
                    self_path = sympy.geometry.Ray(p_self, p_self_1)
                    other_path = sympy.geometry.Ray(p_other, p_other_1)
                    p_cross = sympy.geometry.intersection(self_path, other_path)
                    if len(p_cross) > 0:
                        d_self = geometry.Point.distance(p_cross[0], p_self)
                        d_other = geometry.Point.distance(p_cross[0], p_other)
                        t_self = float(d_self) / self.has_speed
                        t_other = float(d_other) / other.has_speed
                        return t_self + t_other < _INTERSECTING_PATH_THRESHOLD and \
                               abs(t_self - t_other) < _INTERSECTING_PATH_MAX_PET
                    else:
                        return False

        @augment(AugmentationType.OBJECT_PROPERTY, "CP_163")
        def has_high_relative_speed_to(self, other: physics.Moving_Dynamical_Object):
            """
            Computes whether this object has a high relative speed w.r.t. the given other object.
            :param other: The other moving dynamical object.
            :returns: True iff. the high relative speed condition is satisfied.
            """
            if self != other and self.has_geometry() and other.has_geometry() and self.has_yaw is not None and \
                    other.has_yaw is not None and self.has_velocity_x is not None and self.has_velocity_y is not None \
                    and other.has_velocity_x is not None and other.has_velocity_x is not None:
                v_self = numpy.array(self.convert_local_to_global_vector([self.has_velocity_x, self.has_velocity_y]))
                v_othe = numpy.array(other.convert_local_to_global_vector([other.has_velocity_x, other.has_velocity_y]))
                s_rel = numpy.linalg.norm(v_self - v_othe)
                s_self_max = max([x for y in self.is_a for x in y.has_maximum_speed])
                if s_self_max is not None:
                    s_self_max = _DEFAULT_MAX_SPEED
                if self.has_speed_limit is not None:
                    s_rule_max = self.has_speed_limit
                elif len(self.in_traffic_model) > 0 and self.in_traffic_model[0].has_speed_limit is not None:
                    s_rule_max = self.in_traffic_model[0].has_speed_limit
                else:
                    s_rule_max = _DEFAULT_SPEED_LIMIT
                s_rel_normed = s_rel / (min(s_self_max, s_rule_max))
                return s_rel_normed >= _HIGH_REL_SPEED_THRESHOLD
