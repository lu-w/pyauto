import owlready2

from shapely.geometry import Polygon, LineString

from .. import utils
from ... import auto

l1_core = auto.world.get_ontology(auto.Ontology.L1_Core.value)
geo = auto.world.get_ontology(auto.Ontology.GeoSPARQL.value)

with l1_core:

    class Road(owlready2.Thing):

        def cross_section(self, *cross_section: tuple[owlready2.ThingClass, float]):
            # assumption: road has constant width
            # assumption: the left part of the road is the boundary with the western most point in 2D view
            #  - if both boundaries share this point, then the northern most boundary is it
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
                entity = ele[0]()
                geom_e = geo.Geometry()
                entity.hasGeometry = [geom_e]
                lane_left = left.parallel_offset(offset)
                offset += ele[1] * road_width
                lane_right = left.parallel_offset(offset)
                poly_e = Polygon(list(lane_left.coords) + list(lane_right.coords))
                geom_e.asWKT = [poly_e.wkt]
            for c in cs:
                c.has_road = self
                self.has_lane.append(c)
            return cs

        def add_lane(self, lane: l1_core.Lane):
            lane.has_road = self
            self.has_lane.append(lane)
