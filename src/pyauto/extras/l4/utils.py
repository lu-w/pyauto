import owlready2

from shapely import wkt
from shapely.geometry import Polygon

from pyauto import auto

_MAX_TIME_SMALL_DISTANCE = 1  # s, the time in which distances are considered to be 'small'


def get_relevant_area(thing: owlready2.Thing) -> Polygon:
    """
    Helper function for CP small distance. Dispatches to subclass helper functions.
    """
    l4_core = auto._world.get_ontology(auto.Ontology.L4_Core.value)
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
        return thing.get_relevant_area(geom, speed, yaw, max_yaw_rate, max_yaw)
    elif l4_core.Pedestrian in thing.INDIRECT_is_a:
        return thing.get_relevant_area(geom, speed)
    else:
        return geom
