import math
import owlready2

from shapely.geometry import Polygon
from owlready2_augmentator import augment, augment_class, AugmentationType

from ... import auto
from ..l4.utils import _MAX_TIME_SMALL_DISTANCE

physics = auto.world.get_ontology(auto.Ontology.Physics.value)
l4_core = auto.world.get_ontology(auto.Ontology.L4_Core.value)

with l4_core:
    @augment_class
    class Pedestrian(owlready2.Thing):
        @augment(AugmentationType.OBJECT_PROPERTY, "CP_150")
        def has_small_distance(self, other: physics.Spatial_Object):
            if self != other and self.has_geometry() and other.has_geometry() and self.has_speed is not None and \
                    other.has_height is not None and other.has_height > 0:
                occ1 = self.get_relevant_area()
                occ2 = self.get_relevant_area()
                return occ1.intersects(occ2)

        def get_relevant_area(self) -> Polygon:
            """
            Gets the relevant area of a pedestrian as a Polygon. Can be used to determine small distances.
            """
            a = self.get_geometry()
            if self.has_speed > 0:
                return a.centroid.buffer(_MAX_TIME_SMALL_DISTANCE * self.has_speed + math.sqrt(a.area))
            else:
                return a
