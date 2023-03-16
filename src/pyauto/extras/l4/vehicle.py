import math
import numpy
import owlready2

from shapely.geometry import Polygon
from owlready2_augmentator import augment, augment_class, AugmentationType

from ... import auto
from ..l4.utils import _MAX_TIME_SMALL_DISTANCE

physics = auto.world.get_ontology(auto.Ontology.Physics.value)
l4_core = auto.world.get_ontology(auto.Ontology.L4_Core.value)

with l4_core:
    @augment_class
    class Vehicle(owlready2.Thing):
        @augment(AugmentationType.OBJECT_PROPERTY, "CP_150")
        def has_small_distance(self, other: physics.Spatial_Object):
            if self != other and self.has_geometry() and other.has_geometry() and self.has_speed is not None and \
                    self.has_yaw is not None and other.has_height is not None and other.has_height > 0 and \
                    hasattr(other, "get_relevant_area"):
                occ1 = self.get_relevant_area()
                occ2 = other.get_relevant_area()
                return occ1.intersects(occ2)

        def get_relevant_area(self) -> Polygon:
            """
            Gets the relevant area of a vehicle as a Polygon. Can be used to determine small distances.
            """
            max_yaw_rates = [x for y in self.is_a for x in y.has_maximum_yaw_rate]
            if len(max_yaw_rates) > 0:
                max_yaw_rate = max(max_yaw_rates)
            else:
                max_yaw_rate = 25
            yaw_sampling = 1
            samples = []
            for cur_max_yaw_rate in numpy.arange(-max_yaw_rate, max_yaw_rate + yaw_sampling, yaw_sampling):
                path = []
                if abs(cur_max_yaw_rate) == max_yaw_rate:
                    for t in numpy.arange(0, _MAX_TIME_SMALL_DISTANCE + 0.2, 0.2):
                        path.append(self.pos(cur_max_yaw_rate, t))
                else:
                    path.append(self.pos(cur_max_yaw_rate, _MAX_TIME_SMALL_DISTANCE))
                samples.append(path)
            geo = Polygon(samples[0] + [x[-1] for x in samples] + list(reversed(samples[-1])))
            return geo.union(self.get_geometry())

        def pos(self, max_yaw_rate_pos: float, t_pos: float) -> tuple:
            """
            Simple prediction model. Calculates the 2D-point at which the vehicle will be at time t + t_pos assuming
            the given max yaw rate.
            """
            if self.has_speed is not None:
                speed_pos = self.has_speed
            else:
                speed_pos = 0
            if self.has_yaw is not None:
                yaw_pos = self.has_yaw
            else:
                yaw_pos = 0
            if max_yaw_rate_pos < 0:
                a_pos = self.compute_left_front_point()
            else:
                a_pos = self.compute_right_front_point()
            max_yaws = [x for y in self.is_a for x in y.has_maximum_yaw]
            if len(max_yaws) > 0:
                max_yaw_pos = max(max_yaws)
            else:
                max_yaw_pos = 45
            if abs(max_yaw_rate_pos * t_pos) <= max_yaw_pos:
                theta = (yaw_pos + (max_yaw_rate_pos * (t_pos ** 2)) / 2) % 360
            else:
                theta = (yaw_pos + (
                        -(max_yaw_pos ** 2) / (2 * max_yaw_rate_pos) + numpy.sign(max_yaw_rate_pos) * max_yaw_pos *
                        t_pos)) % 360
            return speed_pos * t_pos * math.cos(math.radians(theta)) + a_pos[0], \
                       speed_pos * t_pos * math.sin(math.radians(theta)) + a_pos[1]
