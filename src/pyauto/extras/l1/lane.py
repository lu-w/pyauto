import logging

import owlready2

from shapely.geometry import Polygon, Point

from .. import utils
from ... import auto

l1_core = auto.world.get_ontology(auto.Ontology.L1_Core.value)
geo = auto.world.get_ontology(auto.Ontology.GeoSPARQL.value)

logger = logging.getLogger(__name__)

with l1_core:

    class Lane(owlready2.Thing):

        def get_end(self, angle: float, p: Point, length: float = 1) -> Polygon:
            """
            Returns the end of the lane when viewed from the given point at the given angle.
            Assumption: Only works if the geometry of this lane is given as a polygon with a symmetrical point list.
            :param angle: Viewing angle (in degrees, global)
            :param p: Viewing point
            :param length: Length (meters) of the end piece to find, default is 1 meter.
            :returns: A polygon representing the end piece of the road, or the whole lane geometry if no end could be
                uniquely determined (i.e., p is exactly in the middle and the angle points similarly away w.r.t. both
                ends.
            """
            g = self.get_geometry()
            _, _, front, back = utils.split_polygon_into_boundaries(g)
            p_f = utils.get_closest_point_from_yaw(front, p, angle)
            p_b = utils.get_closest_point_from_yaw(back, p, angle)
            end = None
            if p_b is None or (p_f is not None and p_f.distance(p) < p_b.distance(p)):
                end = front
            elif p_f is None or (p_b is not None and p_f.distance(p) >= p_b.distance(p)):
                end = back
            if end is not None:
                return end.centroid.buffer(length * 2).intersection(g)
            else:
                logger.warning("No end found for lane " + str(self) + " from " + str(p) + " angled " + str(angle))
                return g
