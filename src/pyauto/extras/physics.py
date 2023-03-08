import owlready2
from shapely import geometry

from pyauto import auto


def apply(world: owlready2.World = owlready2.default_world):

    with world.get_ontology(auto.Ontology.Physics.value):

        ge = world.get_ontology(auto.Ontology.GeoSPARQL.value)

        class Spatial_Object(owlready2.Thing):
            def set_geometry(self, x: float, y: float, length: float = None, width: float = None):
                geom = ge.Geometry()
                if length is None or width is None:
                    geom.asWKT = [geometry.Point(x, y).wkt]
                else:
                    geom.asWKT = [geometry.Polygon([((x - length) / 2, (y - width) / 2),
                                                    ((x - length) / 2, (y + width) / 2),
                                                    ((x + length) / 2, (y + width) / 2),
                                                    ((x + length) / 2, (y - width) / 2)]).wkt]
                self.hasGeometry = [geom]
