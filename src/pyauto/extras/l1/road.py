import owlready2

from functools import reduce
from shapely.geometry import Polygon, LineString

from .. import utils
from ... import auto

l1_core = auto.world.get_ontology(auto.Ontology.L1_Core.value)
geo = auto.world.get_ontology(auto.Ontology.GeoSPARQL.value)

with l1_core:

    class Road(owlready2.Thing):

        def cross_section(self, *cross_section: tuple[owlready2.ThingClass, float]) -> list:
            """
            Automatically creates a road layout from a given cross section, which is formatted as a tuple of classes
            (the type of the cross section element) and a float (the relative width that the element shall taken from
            the road).
            :param cross_section: A list of tuples representing the cross section.
            :returns: A list of the newly created lanes
            """
            # assumption: road has constant width
            cs_sum = reduce(lambda a, b: a + b, [x[1] for x in cross_section])
            if cs_sum > 1.0:
                raise TypeError("Parts of cross section must be lower than or equal to 1, but is " + str(cs_sum))
            cs = []
            geom = self.get_geometry()
            if not isinstance(geom, Polygon):
                raise TypeError("Can only create cross sections for roads with a polygon geometry")
            left, right, front, back = utils.split_polygon_into_boundaries(geom)
            if front.length != back.length:
                raise TypeError("Can not create cross section for roads with an uneven width")
            road_width = front.length
            offset = 0
            for i, ele in enumerate(cross_section):
                prev_offset = offset
                entity = ele[0]()
                geom_e = geo.Geometry()
                entity.hasGeometry = [geom_e]
                if offset > 0:
                    lane_left = left.parallel_offset(offset).coords
                else:
                    lane_left = reversed(left.coords)
                offset += ele[1] * road_width
                lane_right = reversed(left.parallel_offset(offset).coords)
                geom_e.asWKT = [Polygon(list(lane_right) + list(lane_left)).wkt]
                entity.has_length = self.has_length
                entity.has_width = offset - prev_offset
                cs.append(entity)
            for c in cs:
                c.has_road = self
                self.has_lane.append(c)
            return cs

        def add_lane(self, lane: l1_core.Lane):
            """
            Adds the given lane to the road and informs the lane about this road being its parent road.
            :param lane: The lane to add.
            """
            lane.has_road = self
            self.has_lane.append(lane)
