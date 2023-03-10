import math
import numpy
import owlready2

from shapely.geometry import Polygon
from owlready2_augmentator import augment, augment_class, AugmentationType

from pyauto import auto
from pyauto.extras.l4.utils import get_relevant_area, _MAX_TIME_SMALL_DISTANCE

physics = auto._world.get_ontology(auto.Ontology.Physics.value)
l4_core = auto._world.get_ontology(auto.Ontology.L4_Core.value)

with l4_core:
    @augment_class
    class Vehicle(owlready2.Thing):
        @augment(AugmentationType.OBJECT_PROPERTY, "CP_150")
        def has_small_distance(self, other: physics.Spatial_Object):
            if self != other and self.has_geometry() and other.has_geometry() and self.has_speed is not None and \
                    self.has_yaw is not None and other.has_height is not None and other.has_height > 0:
                occ1 = get_relevant_area(self)
                occ2 = get_relevant_area(other)
                return occ1.intersects(occ2)

        def get_relevant_area_veh(self, a: Polygon, speed: float, yaw: float, max_yaw_rate: float,
                                  max_yaw: float = 20) -> Polygon:
            """
            Helper function for CP small distance for vehicles. Gets the relevant area of a vehicle as a Polygon.
            """
            yaw_sampling = 1
            samples = []
            for cur_max_yaw_rate in numpy.arange(-max_yaw_rate, max_yaw_rate + yaw_sampling, yaw_sampling):
                path = []
                if cur_max_yaw_rate < 0:
                    a_point = self.get_left_front_point()
                else:
                    a_point = self.get_right_front_point()
                if abs(cur_max_yaw_rate) == max_yaw_rate:
                    for t in numpy.arange(0, _MAX_TIME_SMALL_DISTANCE + 0.2, 0.2):
                        path.append(self.pos(a_point, speed, yaw, cur_max_yaw_rate, max_yaw, t))
                else:
                    path.append(self.pos(a_point, speed, yaw, cur_max_yaw_rate, max_yaw, _MAX_TIME_SMALL_DISTANCE))
                samples.append(path)
            geo = Polygon(samples[0] + [x[-1] for x in samples] + list(reversed(samples[-1])))
            return geo.union(a)

        def pos(self, a_pos: tuple, speed_pos: float, yaw_pos: float, max_yaw_rate_pos: float, max_yaw_pos: float,
                t_pos: float) -> tuple:
            """
            Simple prediction model. Calculates the 2D-point at which the actor will be  at time t + t_pos assuming
            the given parameters.
            """
            if abs(max_yaw_rate_pos * t_pos) <= max_yaw_pos:
                theta = (yaw_pos + (max_yaw_rate_pos * (t_pos ** 2)) / 2) % 360
            else:
                theta = (yaw_pos + (
                        -(max_yaw_pos ** 2) / (2 * max_yaw_rate_pos) + numpy.sign(max_yaw_rate_pos) * max_yaw *
                        t_pos)) % 360
            return speed_pos * t_pos * math.cos(math.radians(theta)) + a_pos[0], \
                       speed_pos * t_pos * math.sin(math.radians(theta)) + a_pos[1]
