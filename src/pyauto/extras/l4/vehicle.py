import math

import numpy
import owlready2
import sympy

from shapely.geometry import Polygon
from owlready2_augmentator import augment, augment_class, AugmentationType

from ... import auto
from ... import extras
from ..l4.utils import _MAX_TIME_SMALL_DISTANCE

physics = auto.world.get_ontology(auto.Ontology.Physics.value)
l4_core = auto.world.get_ontology(auto.Ontology.L4_Core.value)

with l4_core:
    @augment_class
    class Vehicle(owlready2.Thing):
        def add_driver(self, cls: owlready2.ThingClass):
            driver = cls(self.name + "_driver")
            driver.is_a.append(l4_core.Driver)
            if self.has_geometry():
                geo = self.get_geometry().centroid.xy
                driver.set_geometry(*geo[0], *geo[1])
            driver.has_speed = self.has_speed
            driver.has_yaw = self.has_yaw
            driver.drives = [self]
            return driver

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
            max_yaw_rates = [x for y in self.is_a if hasattr(y, "has_maximum_yaw_rate") for x in y.has_maximum_yaw_rate]
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
            max_yaws = [x for y in self.is_a if hasattr(y, "has_maximum_yaw") for x in y.has_maximum_yaw]
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

        def _get_relevant_lanes(self):
            """
            :returns: A list of lanes in which the vehicle can be validly be located upon.
            """
            return self.namespace.world.get_ontology(auto.Ontology.L1_Core.value).\
                search(type=self.namespace.world.get_ontology(auto.Ontology.L1_Core.value).Driveable_Lane)

        def spawn(self, length=4.3, width=1.8, height=1.7, speed=5, driver=l4_core.Driver, spawn_lane=None,
                  max_number_of_tries=25, offset=None) -> l4_core.Driver:
            """
            Spawns the vehicle on some random lane with the given geometry parameters. Avoid conflicts with other
            vehicles.
            :returns: the spawned driver (or self, if no driver shall be added) or None if vehicle could not be spawned
            """
            if spawn_lane is None:
                lanes = self._get_relevant_lanes()
            pos_taken = True
            number_of_unsuccessful_tries = 0
            while pos_taken and number_of_unsuccessful_tries <= max_number_of_tries:
                if spawn_lane is None:
                    lane = self.namespace.world._random.choice(sorted(lanes, key=str))
                else:
                    lane = spawn_lane
                left, right, front, back = extras.utils.split_polygon_into_boundaries(lane.get_geometry())
                medium = sympy.Segment(*front.centroid.coords, *back.centroid.coords)
                x = sympy.Symbol("x")
                if offset is None:
                    rel_offset = 0.2
                else:
                    rel_offset = offset / lane.has_length
                pos = self.namespace.world._random.uniform(0 + rel_offset, 1 - rel_offset)
                spawn_point = medium.arbitrary_point(x).subs({x: pos})
                null_line = sympy.Ray((0, 0), (1, 0))
                yaw = (360 - math.degrees(
                    null_line.closing_angle(sympy.Ray(*front.centroid.coords, *back.centroid.coords)))) % 360
                if len(lane.has_successor_lane) == 0:
                    yaw = (yaw + 180) % 360
                self.set_geometry(spawn_point.x, spawn_point.y, width=width, length=length, rotate=(yaw))
                pos_taken = False
                for other in self.namespace.world.search(
                        type=self.namespace.world.get_ontology(auto.Ontology.L4_Core.value).Vehicle):
                    if other != self and other.get_geometry().intersects(self.get_geometry().buffer(1)):
                        pos_taken = True
                        number_of_unsuccessful_tries += 1
                        break
            if number_of_unsuccessful_tries <= max_number_of_tries:
                self.has_speed = speed
                self.has_yaw = yaw
                self.has_height = height
                if driver is not None:
                    return self.add_driver(driver)
                else:
                    return self
            else:
                return None
