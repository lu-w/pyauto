import math
import numpy
import sympy
import owlready2

from functools import cache
from shapely import wkt, geometry, affinity
from owlready2_augmentator import augment, augment_class, AugmentationType

from ... import auto
from ...extras import utils
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

        def intersects_path_with(self, other: physics.Moving_Dynamical_Object) -> tuple[float, float]:
            """
            Whether this object has an intersecting path with the given other object. Uses sampling of a simple
            constant velocity, constant yaw rate prediction model based on bounding boxes.
            :param other: The other moving dynamical object.
            :returns: The times that self and other needs and the intersection point as a triple, or None, None, None if
                there is no intersection point.
            """
            def get_time_obj_is_at(geometry, predictions):
                for geom_pred, t in predictions:
                    if geometry.intersects(geom_pred):
                        return t

            soonest_intersection = None
            t_1 = None
            t_2 = None

            if not hasattr(self, "intersects_path_with_cached"):
                self.intersects_path_with_cached = {}
            if not hasattr(other, "intersects_path_with_cached"):
                other.intersects_path_with_cached = {}

            if other not in self.intersects_path_with_cached.keys() and self != other and self.has_geometry() and \
                    other.has_geometry() and self.has_yaw is not None and other.has_yaw is not None and \
                    self.has_speed is not None and other.has_speed is not None:
                p_1 = wkt.loads(self.hasGeometry[0].asWKT[0]).centroid
                p_2 = wkt.loads(other.hasGeometry[0].asWKT[0]).centroid
                p_self = sympy.Point(p_1.x, p_1.y)
                p_other = sympy.Point(p_2.x, p_2.y)
                if p_self != p_other:
                    pred_1 = self.prediction()
                    pred_2 = other.prediction()
                    candidates = []
                    for g_1, t_p_1 in pred_1:
                        for g_2, t_p_2 in pred_2:
                            intersection = g_1.intersection(g_2)
                            if intersection.area > 0:
                                candidates.append((intersection.centroid, t_p_1, t_p_2))
                    if len(candidates) > 0:
                        candidates = sorted(candidates, key=lambda x: x[1] + x[2])
                        soonest_intersection = candidates[0][0]
                        t_1 = candidates[0][1]
                        t_2 = candidates[0][2]
                self.intersects_path_with_cached[other] = (t_1, t_2, soonest_intersection)
                other.intersects_path_with_cached[self] = (t_2, t_1, soonest_intersection)
            elif other in self.intersects_path_with_cached.keys() and \
                    self.intersects_path_with_cached[other] is not None:
                t_1 = self.intersects_path_with_cached[other][0]
                t_2 = self.intersects_path_with_cached[other][1]
                soonest_intersection = self.intersects_path_with_cached[other][2]

            return t_1, t_2, soonest_intersection

        @cache
        def prediction(self, delta_t: float | int = 0.1, horizon: float | int = 3.1):
            """
            Implementation of a sampling-based, simple constant velocity, constant yaw rate prediction model based on
            bounding boxes.
            :param delta_t: The time delta for sampling.
            :param horizon: The time horizon (max. time that is sampled) for prediction.
            :return: A list of tuples of `shapely` geometries and time stamps, where ich geometry represents the object
                at the given point in time.
            """
            yaw = self.has_yaw
            yaw_rate = self.has_yaw_rate
            if len(self.drives) > 0:
                geo = self.drives[0].get_geometry()
            else:
                geo = self.get_geometry()
            geos = [(geo, 0)]
            for i in numpy.arange(delta_t, horizon + delta_t, delta_t):
                prev_yaw = yaw
                yaw = prev_yaw + yaw_rate * delta_t
                # if speed is 0, we assume object speeds up to some rather low speed
                speed = max(Dynamical_Object._RELEVANT_LOWEST_SPEED * 4, self.has_speed)
                xoff = math.cos(math.radians(yaw)) * speed * delta_t
                yoff = math.sin(math.radians(yaw)) * speed * delta_t
                if isinstance(geo, geometry.Polygon):
                    length = self.has_length
                    if not length and len(self.drives) > 0:
                        length = self.drives[0].has_length
                    if not length:
                        length = 0
                    length *= 0.4
                    inv_yaw = math.radians(self.has_yaw + 180) % 360
                    center = geometry.Point(geo.centroid.x + length * math.cos(inv_yaw),
                                            geo.centroid.y + length * math.sin(inv_yaw))
                else:
                    center = geo.centroid
                geo = affinity.rotate(geo, angle=yaw - prev_yaw, origin=center)
                geo = affinity.translate(geo, xoff=xoff, yoff=yoff)
                geos.append((geo, i))
                yaw_rate *= 1 - (0.5 * delta_t)  # linear reduction of yaw rate (50% reduction / s) in prediction
            print("Predictions for " + str(self))
            print(geometry.MultiPolygon([x[0] for x in geos]))
            return geos
