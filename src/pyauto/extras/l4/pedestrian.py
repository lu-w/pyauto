import math
import owlready2

from shapely.geometry import Polygon
from owlready2_augmentator import augment, augment_class, AugmentationType

from pyauto import auto
from pyauto.extras.l4.utils import get_relevant_area, _MAX_TIME_SMALL_DISTANCE

physics = auto._world.get_ontology(auto.Ontology.Physics.value)
l4_core = auto._world.get_ontology(auto.Ontology.L4_Core.value)

with l4_core:
    @augment_class
    class Pedestrian(owlready2.Thing):
        @augment(AugmentationType.OBJECT_PROPERTY, "CP_150")
        def has_small_distance(self, other: physics.Spatial_Object):
            if self != other and self.has_geometry() and other.has_geometry() and \
                    self.has_speed is not None and other.has_height is not None and other.has_height > 0:
                occ1 = get_relevant_area(self)
                occ2 = get_relevant_area(other)
                return occ1.intersects(occ2)


    def get_relevant_area(self, a: Polygon, speed: float) -> Polygon:
        """
        Helper function for CP small distance for pedestrians. Gets the relevant area of a pedestrian as a Polygon.
        """
        if speed > 0:
            return a.centroid.buffer(_MAX_TIME_SMALL_DISTANCE * speed + math.sqrt(a.area))
        else:
            return a
