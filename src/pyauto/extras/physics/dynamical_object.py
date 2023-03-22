import math
import numpy
import owlready2

from shapely import wkt
from owlready2_augmentator import augment, augment_class, AugmentationType
from ... import auto
from .spatial_object import _SPATIAL_PREDICATE_THRESHOLD

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
