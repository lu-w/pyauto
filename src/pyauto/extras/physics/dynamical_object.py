import math
import numpy
import sympy
import owlready2

from shapely import wkt
from owlready2_augmentator import augment, augment_class, AugmentationType

from ... import auto
from .spatial_object import _SPATIAL_PREDICATE_THRESHOLD
from .moving_dynamical_object import _INTERSECTING_PATH_MAX_PET

physics = auto.world.get_ontology(auto.Ontology.Physics.value)
geosparql = auto.world.get_ontology(auto.Ontology.GeoSPARQL.value)

with physics:

    @augment_class
    class Dynamical_Object(owlready2.Thing):

        def set_velocity(self, x: float, y: float, z: float = 0):
            """
            Sets the velocity vector of this object. Does not perform further computations.
            :param x: speed vector x
            :param y: speed vector y
            :param z: speed vector z (optional if 2D is sufficient)
            """
            self.has_velocity_x = x
            self.has_velocity_y = y
            self.has_velocity_z = z

        def set_acceleration(self, x: float, y: float, z: float = 0):
            """
            Sets the acceleration vector of this object. Does not perform further computations.
            :param x: acceleration vector x
            :param y: acceleration vector y
            :param z: acceleration vector z (optional if 2D is sufficient)
            """
            self.has_acceleration_x = x
            self.has_acceleration_y = y
            self.has_acceleration_z = z

        @augment(AugmentationType.DATA_PROPERTY, "has_speed")
        def get_speed(self) -> float:
            """
            Gets the speed (scalar) from this object's velocity vector. Returns None if not enough information is given.
            """
            v = [x for x in [self.has_velocity_x, self.has_velocity_y, self.has_velocity_z] if x is not None]
            if len(v) > 1:
                angle = math.degrees(math.atan2(v[1], v[0])) % 360
                sign = 1
                if 90 < angle < 270:
                    sign = -1
                return float(sign * numpy.linalg.norm(v))

        @augment(AugmentationType.DATA_PROPERTY, "has_yaw")
        def get_yaw(self) -> float:
            """
            Gets the yaw (degrees) from this object's velocity vector. Returns None if not enough information is given.
            """
            v = [x for x in [self.has_velocity_x, self.has_velocity_y, self.has_velocity_z] if x is not None]
            if len(v) > 1:
                return math.degrees(math.atan2(v[1], v[0])) % 360

        @augment(AugmentationType.DATA_PROPERTY, "has_acceleration")
        def get_acceleration(self) -> float:
            """
            Gets the acceleration (scalar) from this object's acceleration vector.
            """
            a = [x for x in [self.has_acceleration_x, self.has_acceleration_y, self.has_acceleration_z]
                 if x is not None]
            if len(a) > 1:
                angle = math.degrees(math.atan2(a[1], a[0])) % 360
                sign = 1
                if 90 < angle < 270:
                    sign = -1
                return float(sign * numpy.linalg.norm(a))

        @augment(AugmentationType.REIFIED_DATA_PROPERTY, physics.Has_Distance_To, "distance_from", "distance_to",
                 "has_distance")
        def augment_distance(self, other: physics.Spatial_Object) -> float:
            """
            Gets the Euclidian distance from this dynamical object to another spatial object. Due to performance reasons
            augmentation is only performed based on dynamical objects.
            :param other: The spatial object to measure distance to.
            """
            if self != other and self.has_geometry() and other.has_geometry():
                p1 = wkt.loads(self.hasGeometry[0].asWKT[0])
                p2 = wkt.loads(other.hasGeometry[0].asWKT[0])
                distance = float(p1.distance(p2))
                if distance <= _SPATIAL_PREDICATE_THRESHOLD:
                    return distance

        def intersects_path_with(self, other: physics.Moving_Dynamical_Object,
                                 max_pet: float = _INTERSECTING_PATH_MAX_PET) -> tuple[float, float]:
            """
            Whether this object has an intersecting path with the given other object.
            :param other: The other moving dynamical object.
            :param max_pet: The time interval of PET that classifies intersecting paths as critical.
            :returns: The times that self and other needs to the intersection point as a tuple, or None, None if there
                is no intersection point.
            """
            if self.has_geometry() and other.has_geometry() and self.has_yaw is not None and other.has_yaw is not None \
                    and self.has_speed and other.has_speed:
                p_1 = wkt.loads(self.hasGeometry[0].asWKT[0]).centroid
                p_2 = wkt.loads(other.hasGeometry[0].asWKT[0]).centroid
                p_self = sympy.Point(p_1.x, p_1.y)
                p_other = sympy.Point(p_2.x, p_2.y)
                if p_self != p_other:
                    self_yaw = self.has_yaw
                    other_yaw = other.has_yaw
                    if self.has_speed < 0:
                        self_yaw = (self.has_yaw + 180) % 360
                    if other.has_speed < 0:
                        other_yaw = (other.has_yaw + 180) % 360
                    p_self_1 = sympy.Point(p_1.x + math.cos(math.radians(self_yaw)),
                                              p_1.y + math.sin(math.radians(self_yaw)))
                    p_other_1 = sympy.Point(p_2.x + math.cos(math.radians(other_yaw)),
                                               p_2.y + math.sin(math.radians(other_yaw)))
                    self_path = sympy.geometry.Ray(p_self, p_self_1)
                    other_path = sympy.geometry.Ray(p_other, p_other_1)
                    p_cross = sympy.geometry.intersection(self_path, other_path)
                    if len(p_cross) > 0:
                        d_self = p_cross[0].distance(p_self)
                        d_other = p_cross[0].distance(p_other)
                        t_self = float(d_self) / self.has_speed
                        t_other = float(d_other) / other.has_speed
                        return (t_self, t_other)
            return (None, None)