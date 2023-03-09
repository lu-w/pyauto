import math
import numpy
import owlready2

from shapely import wkt
from shapely.geometry import Polygon

from owlready2_augmentator import augment, augment_class, AugmentationType
from pyauto import auto

_MAX_TIME_SMALL_DISTANCE = 1  # s, the time in which distances are considered to be 'small'

physics = auto._world.get_ontology(auto.Ontology.Physics.value)
l4_core = auto._world.get_ontology(auto.Ontology.L4_Core.value)


# TODO move these helper functions into the classes of Pedestrian / Vehicle
def get_relevant_area(thing: owlready2.Thing) -> Polygon:
    """
    Helper function for CP small distance. Dispatches to subclass helper functions.
    """
    geom = wkt.loads(thing.hasGeometry[0].asWKT[0]).buffer(0)
    if thing.has_speed is not None:
        speed = thing.has_speed
    else:
        speed = 0
    if thing.has_yaw is not None:
        yaw = thing.has_yaw
    else:
        yaw = 0
    if l4_core.Vehicle in thing.INDIRECT_is_a and speed > 0:
        max_yaws = [x for y in thing.is_a for x in y.has_maximum_yaw]
        max_yaw_rates = [x for y in thing.is_a for x in y.has_maximum_yaw_rate]
        if len(max_yaws) > 0:
            max_yaw = max(max_yaws)
        else:
            max_yaw = 45
        if len(max_yaw_rates) > 0:
            max_yaw_rate = max(max_yaw_rates)
        else:
            max_yaw_rate = 25
        return get_relevant_area_veh(geom, speed, thing, yaw, max_yaw_rate, max_yaw)
    elif l4_core.Pedestrian in thing.INDIRECT_is_a:
        return get_relevant_area_ped(geom, speed)
    else:
        return geom


def get_relevant_area_ped(a: Polygon, speed: float) -> Polygon:
    """
    Helper function for CP small distance for pedestrians. Gets the relevant area of a pedestrian as a Polygon.
    """
    if speed > 0:
        return a.centroid.buffer(_MAX_TIME_SMALL_DISTANCE * speed + math.sqrt(a.area))
    else:
        return a


def get_relevant_area_veh(a: Polygon, speed: float, thing: physics.Spatial_Object, yaw: float, max_yaw_rate: float, max_yaw: float = 20) -> \
        Polygon:
    """
    Helper function for CP small distance for vehicles. Gets the relevant area of a vehicle as a Polygon.
    """

    def pos(a_pos: tuple, speed_pos: float, yaw_pos: float, max_yaw_rate_pos: float, max_yaw_pos: float, t_pos: float) \
            -> tuple:
        """
        Simple prediction model. Calculates the 2D-point at which the actor will be  at time t + t_pos assuming the
        given parameters.
        """
        if abs(max_yaw_rate_pos * t_pos) <= max_yaw_pos:
            theta = (yaw_pos + (max_yaw_rate_pos * (t_pos ** 2)) / 2) % 360
        else:
            theta = (yaw_pos + (
                    -(max_yaw_pos ** 2) / (2 * max_yaw_rate_pos) + numpy.sign(max_yaw_rate_pos) * max_yaw *
                    t_pos)) % 360
        return speed_pos * t_pos * math.cos(math.radians(theta)) + a_pos[0], \
               speed_pos * t_pos * math.sin(math.radians(theta)) + a_pos[1]

    yaw_sampling = 1
    samples = []
    for cur_max_yaw_rate in numpy.arange(-max_yaw_rate, max_yaw_rate + yaw_sampling, yaw_sampling):
        path = []
        if cur_max_yaw_rate < 0:
            a_point = thing.get_left_front_point()
        else:
            a_point = thing.get_right_front_point()
        if abs(cur_max_yaw_rate) == max_yaw_rate:
            for t in numpy.arange(0, _MAX_TIME_SMALL_DISTANCE + 0.2, 0.2):
                path.append(pos(a_point, speed, yaw, cur_max_yaw_rate, max_yaw, t))
        else:
            path.append(pos(a_point, speed, yaw, cur_max_yaw_rate, max_yaw, _MAX_TIME_SMALL_DISTANCE))
        samples.append(path)
    geo = Polygon(samples[0] + [x[-1] for x in samples] + list(reversed(samples[-1])))
    return geo.union(a)


with l4_core:
    @augment_class
    class Pedestrian(owlready2.Thing):
        @augment(AugmentationType.OBJECT_PROPERTY, "CP_150")
        def has_small_distance(self, other: physics.Spatial_Object):
            if self != other and self.has_geometry() and other.has_geometry() and \
                    self.has_speed is not None and other.has_height is not None and other.has_height > 0:
                # TODO document in OWL
                occ1 = get_relevant_area(self)
                occ2 = get_relevant_area(other)
                return occ1.intersects(occ2)


    @augment_class
    class Vehicle(owlready2.Thing):
        @augment(AugmentationType.OBJECT_PROPERTY, "CP_150")
        def has_small_distance(self, other: physics.Spatial_Object):
            if self != other and self.has_geometry() and other.has_geometry() and self.has_speed is not None and \
                    self.has_yaw is not None and other.has_height is not None and other.has_height > 0:
                # TODO document in OWL
                occ1 = self.get_relevant_area()
                occ2 = other.get_relevant_area()
                return occ1.intersects(occ2)
