import math
import random

import sympy
import owlready2

from shapely.geometry import Polygon
from owlready2_augmentator import augment, augment_class, AugmentationType

from ... import auto
from ... import extras
from ..l4.utils import _MAX_TIME_SMALL_DISTANCE

physics = auto.world.get_ontology(auto.Ontology.Physics.value)
l4_core = auto.world.get_ontology(auto.Ontology.L4_Core.value)

with l4_core:
    @augment_class
    class Pedestrian(owlready2.Thing):

        _RELEVANT_LOWEST_SPEED = 0.05

        @augment(AugmentationType.OBJECT_PROPERTY, "has_small_distance")
        def small_distance(self, other: physics.Spatial_Object):
            """
            Checks if this object has a small distance w.r.t. another object.
            This method determines if the current object and another object are close to each other based on their
            geometries, speeds, yaws, heights, and relevant areas.
            :return: True if the objects have a small distance, i.e. their relevant areas intersect, False otherwise.
            """
            if self != other and self.has_geometry() and other.has_geometry() and self.has_speed is not None and \
                    other.has_height is not None and other.has_height > 0:
                occ1 = self.get_relevant_area()
                occ2 = self.get_relevant_area()
                return occ1.intersects(occ2)

        def get_relevant_area(self) -> Polygon:
            """
            Gets the relevant area of a pedestrian as a Polygon. Can be used to determine small distances. It is based
            on simply examining the reachable area of the pedestrian interpreted as a circle around it.
            :return: The relevant area as a Polygon.
            """
            a = self.get_geometry()
            if self.has_speed > 0:
                return a.centroid.buffer(_MAX_TIME_SMALL_DISTANCE * self.has_speed + math.sqrt(a.area))
            else:
                return a

        def _get_relevant_walkways(self):
            """
            :returns: A list of walkways in which the pedestrian can be validly be located upon.
            """
            return [x for x in
                    self.namespace.world.get_ontology(auto.Ontology.L1_DE.value).search(
                        type=self.namespace.world.get_ontology(auto.Ontology.L1_DE.value).Walkway)
                    if x.get_geometry().area > 6]
        
        def spawn(self, width=0.4, length=0.4, height=1.75, speed=1, spawn_walkway=None, max_number_of_tries=25,
                  offset=None) -> bool:
            """
            Spawns the pedestrian on some random walkway with the given geometry parameters. Avoid conflicts with other
            pedestrians. Yaw is chosen randomly either facing upwards or downwards of the chosen walkway.
            :returns: False iff. the pedestrian could not be spawned
            """
            if spawn_walkway is None:
                walkways = self._get_relevant_walkways()
            pos_taken = True
            number_of_unsuccessful_tries = 0
            while pos_taken and number_of_unsuccessful_tries <= max_number_of_tries:
                if spawn_walkway is None:
                    walkway = self.namespace.world._random.choice(sorted(walkways, key=str))
                else:
                    walkway = spawn_walkway
                left, right, front, back = extras.utils.split_polygon_into_boundaries(walkway.get_geometry())
                medium = sympy.Segment(*front.centroid.coords, *back.centroid.coords)
                x = sympy.Symbol("x")
                if offset is None:
                    rel_offset = 0.2
                else:
                    rel_offset = offset / walkway.has_length
                pos = self.namespace.world._random.uniform(0 + rel_offset, 1 - rel_offset)
                spawn_point = medium.arbitrary_point(x).subs({x: pos})
                null_line = sympy.Ray((0, 0), (1, 0))
                yaw = (360 - math.degrees(
                    null_line.closing_angle(sympy.Ray(*front.centroid.coords, *back.centroid.coords)))) % 360
                if self.namespace.world._random.random() < 0.5:
                    yaw = (yaw + 180) % 360
                self.set_geometry(spawn_point.x, spawn_point.y, length=length, width=width, rotate=yaw)
                pos_taken = False
                others = list(
                    self.namespace.world.search(
                        type=self.namespace.world.get_ontology(auto.Ontology.L4_Core.value).Pedestrian)
                    ) + list(
                        self.namespace.world.search(
                            type=self.namespace.world.get_ontology(auto.Ontology.L4_Core.value).Vehicle)
                    )
                for other in others:
                    if other != self and other.get_geometry().intersects(self.get_geometry().buffer(2)):
                        pos_taken = True
                        number_of_unsuccessful_tries += 1
                        break
            if number_of_unsuccessful_tries <= max_number_of_tries:
                self.has_speed = speed
                self.has_yaw = yaw
                self.has_height = height
                return True
            else:
                return False
