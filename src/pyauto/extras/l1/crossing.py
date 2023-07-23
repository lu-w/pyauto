import math

import owlready2

from ... import auto

l1_de = auto.world.get_ontology(auto.Ontology.L1_DE.value)

with l1_de:

    class Crossing(owlready2.Thing):

        _TOLERANCE_PARALLEL_LANE_DEGREES = 15  # °

        def set_roads(self, *roads):
            self.connects = [r for r in roads]
            self._set_lane_positions()

        def _set_lane_positions(self):
            if self.has_geometry():
                p_int = self.get_geometry().centroid
                lanes = [l for r in self.connects for l in r.has_lane]
                for lane in lanes:
                    for other_lane in lanes:
                        if lane != other_lane and lane.has_geometry() and other_lane.has_geometry():
                            p_lane = lane.get_geometry().centroid
                            p_other_lane = other_lane.get_geometry().centroid
                            yaw_l = math.degrees(math.atan2(p_int.y - p_lane.y, p_int.x - p_lane.x))
                            yaw_other_l = math.degrees(math.atan2(p_lane.y - p_other_lane.y, p_lane.x - p_other_lane.x))
                            rel_yaw = (yaw_l - yaw_other_l) % 360
                            if math.isclose(lane.get_geometry().centroid.x, other_lane.get_geometry().centroid.x) or \
                                    math.isclose(lane.get_geometry().centroid.y,
                                                 other_lane.get_geometry().centroid.y) or \
                                    math.isclose(rel_yaw, 180, abs_tol=self._TOLERANCE_PARALLEL_LANE_DEGREES) or \
                                    math.isclose(rel_yaw, 0, abs_tol=self._TOLERANCE_PARALLEL_LANE_DEGREES) or \
                                    math.isclose(rel_yaw, 360, abs_tol=self._TOLERANCE_PARALLEL_LANE_DEGREES):
                                lane.is_lane_parallel_to.append(other_lane)
                            elif self.left(p_other_lane, p_lane, yaw_l):
                                lane.is_lane_right_of.append(other_lane)
                            else:
                                lane.is_lane_left_of.append(other_lane)
