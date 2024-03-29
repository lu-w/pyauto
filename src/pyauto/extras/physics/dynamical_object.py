import math
import logging
from typing import Tuple, Any

import numpy
import sympy
import owlready2

from functools import cache
from shapely import wkt, geometry, affinity
from owlready2_augmentator import augment, augment_class, AugmentationType

from ... import auto
from ...extras import utils
from .spatial_object import _SPATIAL_PREDICATE_THRESHOLD

logger = logging.getLogger(__name__)

physics = auto.world.get_ontology(auto.Ontology.Physics.value)
geosparql = auto.world.get_ontology(auto.Ontology.GeoSPARQL.value)

with physics:

    @augment_class
    class Dynamical_Object(owlready2.Thing):

        _RELEVANT_LOWEST_SPEED = 0.15  # m/s
        _INTERSECTING_PATH_THRESHOLD = 8  # s, the time interval in which future intersecting paths shall be detected
        _INTERSECTING_PATH_MAX_PET = 5  # s, the time interval of PET that classifies intersecting paths as critical
        _HIGH_REL_SPEED_THRESHOLD = 0.25  # rel., the rel. difference in total speed in which CP150 will be augmented
        _DEFAULT_SPEED_LIMIT = 50  # km/h, the default speed limit that is assumed
        _DEFAULT_MAX_SPEED = 50  # km/h, the default speed maximum speed that is assumed

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
            if self.has_speed is not None:
                return self.has_speed
            else:
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
            if self.has_yaw is not None:
                return self.has_yaw
            else:
                v = [x for x in [self.has_velocity_x, self.has_velocity_y, self.has_velocity_z] if x is not None]
                if len(v) > 1:
                    return math.degrees(math.atan2(v[1], v[0])) % 360

        @augment(AugmentationType.DATA_PROPERTY, "has_acceleration")
        def get_acceleration(self) -> float:
            """
            Gets the acceleration (scalar) from this object's acceleration vector.
            """
            if self.has_acceleration is not None:
                return self.has_acceleration
            else:
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

        @augment(AugmentationType.OBJECT_PROPERTY, "has_intersecting_path")
        def augment_intersecting_paths(self, other: physics.Dynamical_Object):
            """
            Whether this object has an intersecting path with the given other object.
            :param other: The other moving dynamical object.
            :returns: True iff. the intersecting path condition is satisfied.
            """
            if self != other and ((len(self.drives) == 0 and len(other.drives) == 0) or
                                  (len(self.drives) > 0 and other not in self.drives) or
                                  (len(other.drives) > 0 and self not in other.drives)) \
                    and self.has_geometry() and other.has_geometry() and self.get_speed() or 0 > 0 and \
                    other.get_speed() or 0 > 0:
                t_self, t_other, _ = self.intersects_path_with(other)
                if t_self is None or t_other is None:
                    return False
                else:
                    return t_self + t_other < self._INTERSECTING_PATH_THRESHOLD and \
                        abs(t_self - t_other) < self._INTERSECTING_PATH_MAX_PET

        #@augment(AugmentationType.OBJECT_PROPERTY, "CP_163")
        def has_high_relative_speed_to(self, other: physics.Dynamical_Object):
            """
            Computes whether this object has a high relative speed w.r.t. the given other object.
            :param other: The other moving dynamical object.
            :returns: True iff. the high relative speed condition is satisfied.
            """
            if self != other and self.has_geometry() and other.has_geometry() and self.get_speed() or 0 > 0 and \
                    other.get_speed() or 0 > 0 and self.has_yaw is not None and other.has_yaw is not None and \
                    self.has_velocity_x is not None and self.has_velocity_y is not None and \
                    other.has_velocity_x is not None and other.has_velocity_x is not None:
                # TODO this crashes in combination with TOBM
                v_self = numpy.array(
                    self.convert_local_to_global_vector([self.has_velocity_x, self.has_velocity_y]))
                v_othe = numpy.array(
                    other.convert_local_to_global_vector([other.has_velocity_x, other.has_velocity_y]))
                s_rel = numpy.linalg.norm(v_self - v_othe)
                s_self_max = max([x for y in self.is_a for x in y.has_maximum_speed])
                if s_self_max is not None:
                    s_self_max = self._DEFAULT_MAX_SPEED
                if self.has_speed_limit is not None:
                    s_rule_max = self.has_speed_limit
                elif len(self.in_traffic_model) > 0 and self.in_traffic_model[0].has_speed_limit is not None:
                    s_rule_max = self.in_traffic_model[0].has_speed_limit
                else:
                    s_rule_max = self._DEFAULT_SPEED_LIMIT
                s_rel_normed = s_rel / (min(s_self_max, s_rule_max))
                return s_rel_normed >= self._HIGH_REL_SPEED_THRESHOLD

        def intersects_path_with(self, other: physics.Dynamical_Object, delta_t: float | int = 0.25,
                                 horizon: float | int = 10) -> tuple[Any | None, Any | None, Any | None]:
            """
            Whether this object has an intersecting path with the given other object. Uses sampling of a simple
            constant velocity, constant yaw rate prediction model based on bounding boxes.
            :param other: The other moving dynamical object.
            :param delta_t: The time delta for sampling within the prediction model.
            :param horizon: The prediction horizon in seconds to look for intersecting paths in the prediction model.
            :returns: The times that self and other needs and the intersection point as a triple, or None, None, None if
                there is no intersection point.
            """
            soonest_intersection = None
            t_1 = None
            t_2 = None

            if not hasattr(self, "intersects_path_with_cached"):
                self.intersects_path_with_cached = {}
            if not hasattr(other, "intersects_path_with_cached"):
                other.intersects_path_with_cached = {}

            if other not in self.intersects_path_with_cached.keys() and self != other and self.has_geometry() and \
                    other.has_geometry():
                p_1 = self.get_centroid()
                p_2 = other.get_centroid()
                if p_1 != p_2:
                    if isinstance(self, Dynamical_Object):
                        pred_1 = self.prediction(delta_t=delta_t, horizon=horizon)
                    else:
                        pred_1 = [(self.get_geometry(), i) for i in numpy.arange(delta_t, horizon + delta_t, delta_t)]
                    if isinstance(other, Dynamical_Object):
                        pred_2 = other.prediction(delta_t=delta_t, horizon=horizon)
                    else:
                        pred_2 = [(self.get_geometry(), i) for i in numpy.arange(delta_t, horizon + delta_t, delta_t)]
                    candidates = []
                    pred_1_union = pred_1[0][0]
                    for g_1, _ in pred_1:
                        pred_1_union = pred_1_union.union(g_1)
                    pred_2_union = pred_2[0][0]
                    for g_2, _ in pred_2:
                        pred_2_union = pred_2_union.union(g_2)
                    if pred_1_union.intersects(pred_2_union):
                        for g_1, t_p_1 in pred_1:
                            if g_1.intersects(pred_2_union):
                                for g_2, t_p_2 in pred_2:
                                    if t_p_1 + t_p_2 <= horizon and g_2.intersects(pred_1_union):
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
        def prediction(self, delta_t: float | int = 0.1, horizon: float | int = 8):
            """
            Implementation of a sampling-based, simple constant velocity, constant yaw rate prediction model based on
            bounding boxes.
            :param delta_t: The time delta for sampling.
            :param horizon: The time horizon (max. time that is sampled) for prediction.
            :return: A list of tuples of `shapely` geometries and time stamps, where ich geometry represents the object
                at the given point in time.
            """
            yaw_rate = self.has_yaw_rate or 0
            if len(self.drives) > 0:
                geo = self.drives[0].get_geometry()
                geo_c = self.drives[0].get_centroid()
            else:
                geo = self.get_geometry()
                geo_c = self.get_centroid()
            geos = [(geo, 0)]
            if self.has_yaw is None:
                yaw = 0
                speed = 0
            else:
                yaw = self.has_yaw
                if self.has_speed is not None:
                    # if speed is 0, we assume object speeds up to some rather low speed
                    if "l4_de.Parking_Vehicle" not in [str(x) for x in self.is_a]:
                        speed = max(self._RELEVANT_LOWEST_SPEED * 10, self.has_speed)
                    else:
                        speed = self.has_speed
                else:
                    speed = 0
            for i in numpy.arange(delta_t, horizon + delta_t, delta_t):
                prev_yaw = yaw
                yaw = prev_yaw + yaw_rate * delta_t
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
                    center = geometry.Point(geo_c.x + length * math.cos(inv_yaw), geo_c.y + length * math.sin(inv_yaw))
                else:
                    center = geo_c
                geo = affinity.rotate(geo, angle=yaw - prev_yaw, origin=center)
                geo = affinity.translate(geo, xoff=xoff, yoff=yoff)
                geos.append((geo, i))
                yaw_rate *= 1 - (0.4 * delta_t)  # linear reduction of yaw rate (40% reduction / s) in prediction
            return geos

        def get_target_following_polygon(self, polygon: geometry.Polygon, target_distance: float | int = 5) -> \
                tuple[float, float]:
            """
            Computes a target on the given polygon, such that this object can follow the shape of the polygon (by means
            of its dynamics). The target will be the given `target_distance` away from this object.
            :param polygon: A polygon that this object shall follow
            :param target_distance: The distance of the target from this object on the polygon
            :returns: A tuple of floats representing the point of the computed target
            """
            assert self.has_yaw is not None
            g = self.get_centroid()
            left, right, _, _ = utils.split_polygon_into_boundaries(polygon)
            # We have a driver: Choose vehicle front to determine where to look for new targets (if available)
            if len(self.drives) > 0:
                x, y = self.drives[0].get_geometry().minimum_rotated_rectangle.exterior.coords.xy
                edge_length = (geometry.Point(x[0], y[0]).distance(geometry.Point(x[1], y[1])),
                               geometry.Point(x[1], y[1]).distance(geometry.Point(x[2], y[2])))
                length = max(edge_length) * 0.75
            # We have a pedestrian
            else:
                length = 1
            g_front = geometry.Point(g.x + math.cos(math.radians(self.has_yaw)) * length,
                                     g.y + math.sin(math.radians(self.has_yaw)) * length)
            p_l_f = None
            p_r_f = None
            angle = 180
            max_angle = 290
            # Extracts the closest points
            while (p_l_f is None or p_r_f is None) and angle < max_angle:
                p_l_f = utils.get_closest_point_from_yaw(left, g_front, self.has_yaw, angle)
                p_r_f = utils.get_closest_point_from_yaw(right, g_front, self.has_yaw, angle)
                angle += 10
            x = None
            y = None
            if p_l_f is not None and p_r_f is not None:
                circ = g.buffer(target_distance)
                intersection = circ.intersection(polygon.exterior)
                if hasattr(intersection, "geoms"):
                    intersection = [p for g in intersection.geoms for p in g.coords]
                else:
                    intersection = list(intersection.coords)
                m_l, m_dist_l = None, None
                for int_p in intersection:
                    c_dist_l = p_l_f.distance(geometry.Point(int_p))
                    if m_dist_l is None or c_dist_l < m_dist_l:
                        m_dist_l = c_dist_l
                        m_l = int_p
                if m_l in intersection:
                    intersection.remove(m_l)
                m_r, m_dist_r = None, None
                for int_p in intersection:
                    c_dist_r = p_r_f.distance(geometry.Point(int_p))
                    if m_dist_r is None or c_dist_r < m_dist_r:
                        m_dist_r = c_dist_r
                        m_r = int_p
                if m_l is not None and m_r is not None:
                    res = geometry.LineString([m_l, m_r]).centroid
                    x = res.x
                    y = res.y
            if x is None or y is None:
                logger.debug(str(self) + ": Using target in front of object instead of polygon following computation "
                                           "since no closest point on polygon could be determined")
                x = target_distance * math.cos(math.radians(self.has_yaw)) + g.x
                y = target_distance * math.sin(math.radians(self.has_yaw)) + g.y
            return round(x, 2), round(y, 2)

        def is_intersection_possible(self, other, max_distance: int | float = 10):
            """
            Checks whether an intersection is possible with the given other individual, i.e., an over-approximation
            to prevent computations later on.
            """
            if hasattr(self, "drives") and len(self.drives) > 0:
                dist = other.get_distance(self.drives[0])
            else:
                dist = other.get_distance(self)
            # Excludes drivers (we handle their vehicles instead)
            return other != self and other not in self.drives and other.has_height and other.has_height > 0 and \
                (not hasattr(other, "drives") or len(other.drives) == 0) and \
                ((other.has_speed and self.has_speed and (dist / self.has_speed + dist / other.has_speed)
                  <= max_distance) or
                 (not other.has_speed and self.has_speed and (dist / self.has_speed) <= max_distance) or
                 (not self.has_speed and other.has_speed and (dist / other.has_speed) <= max_distance))

        @cache
        def get_intersecting_objects(self, horizon=10, delta_t=0.25) -> list:
            """
            :returns: a list of tuples of intersecting, spatial objects and their intersecting paths.
            """
            res = []
            for obj in self.namespace.world.search(
                    type=self.namespace.world.get_ontology(auto.Ontology.Physics.value).Spatial_Object):
                if self.is_intersection_possible(obj, max_distance=horizon):
                    if hasattr(self, "drives") and len(self.drives) > 0:
                        self_obj = self.drives[0]
                    else:
                        self_obj = self
                    int_path = self_obj.intersects_path_with(obj, delta_t=delta_t, horizon=horizon)
                    if None not in int_path:
                        res.append(tuple([obj]) + int_path)
            return res
