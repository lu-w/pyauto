import owlready2
from shapely import geometry

from pyauto import auto

with auto.get_ontology(auto.Ontology.Physics):

    ge = auto.get_ontology(auto.Ontology.GeoSPARQL)

    class Spatial_Object(owlready2.Thing):
        def set_geometry(self, x: float, y: float, length: float = None, width: float = None):
            geom = ge.Geometry()
            if length is None or width is None:
                geom.asWKT = [geometry.Point(x, y).wkt]
            else:
                geom.asWKT = [geometry.Polygon([(x - length / 2, y - width / 2), (x - width / 2, y + length / 2),
                                                (x + width / 2, y + length / 2), (x + width / 2, y - length / 2)]).wkt]
            self.hasGeometry = [geom]
