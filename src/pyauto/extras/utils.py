import math
import logging

from shapely.geometry import Polygon, LineString, Point

logger = logging.getLogger(__name__)


def split_polygon_into_boundaries(p: Polygon) -> tuple[LineString, LineString, LineString, LineString]:
    """
    Splits a polygon into its left, right, front, and back boundaries (as a tuple of new LineString).
    Assumptions: The polygon has the same number of points on each side, and its ends (i.e, front and back) are
    represented only by two points. Then, the right part will be from the beginning of p to the end point of its first
    half, the front part will be from there to the beginning point of p's second half, and the part of the beginning of
    p's second half to the last point of p is the left part. The back connects the first and last point of p.
    Note: assumes at least four, and an even number of points present in p's boundary.
    :param p: The `Polygon` to split
    :returns: A tuple of new `LineString`s
    """
    coords = p.boundary.coords[:-1]  # last point is the first for a polygon - ignore it
    assert(len(coords) >= 4)
    if len(coords) % 2 == 0:
        half = int(len(coords) / 2)
    else:
        half = int((len(coords) + 1) / 2)
    right_coords = coords[:half]
    front_coords = [coords[half - 1], coords[half]]
    left_coords = reversed(coords[half:len(coords)])
    back_coords = [coords[0], coords[len(coords) - 1]]
    right = LineString(right_coords)
    front = LineString(front_coords)
    left = LineString(left_coords)
    back = LineString(back_coords)
    return left, right, front, back


def get_closest_point_from_yaw(ls: LineString, p: Point, yaw: float | int, angle: float | int = 180) -> Point:
    """
    Finds the nearest point in the line string based on the given point and yaw (i.e., only examines points within the
    180° field in which the yaw points from the given point).
    :param ls: The line string to examine
    :param p: The point for which to get the closest point
    :param yaw: The viewing angle to consider when looking for the closest point.
    :param angle: An angle (in °) that depicts the viewing angle from the yaw in which the closest points are searched.
    :returns: The closes point of the line string based on the yaw or None if there is no point of ls in the 180° field.
    """

    def _get_relevant_points(yaw, p, ls, angle):
        """
        Helper method to determine the points of ls in front of yaw at point p, where in front of is defined by the
        given angle (which is understood relative to the yaw and draws a 'separating line').
        :return: A list of relevant points.
        """
        yaw_p = (yaw + angle) % 360
        p_2 = Point(math.cos(math.radians(yaw_p)) + p.x, math.sin(math.radians(yaw_p)) + p.y)
        if p_2.x - p.x != 0:
            m = (p_2.y - p.y) / (p_2.x - p.x)
            b = p.y - m * p.x
        else:  # case: yaw - angle is 90° or 270°
            m = None
            b = None
        relevant_points = []
        for lp in ls.coords:
            if m is not None:
                div_y = m * lp[0] + b
                if angle < 0:  # right of yaw
                    if 90 < yaw_p <= 270:
                        if lp[1] <= div_y:
                            relevant_points.append(lp)
                    else:
                        if lp[1] >= div_y:
                            relevant_points.append(lp)
                else:  # left of yaw:
                    if 90 < yaw_p <= 270:
                        if lp[1] >= div_y:
                            relevant_points.append(lp)
                    else:
                        if lp[1] <= div_y:
                            relevant_points.append(lp)
            else:
                if angle < 0:  # right of yaw
                    if yaw_p == 90:
                        if lp[0] <= p.x:
                            relevant_points.append(lp)
                    elif yaw_p == 270:
                        if lp[0] >= p.x:
                            relevant_points.append(lp)
                else:  # left of yaw
                    if yaw_p == 90:
                        if lp[0] >= p.x:
                            relevant_points.append(lp)
                    elif yaw_p == 270:
                        if lp[0] <= p.x:
                            relevant_points.append(lp)
        return relevant_points

    rel_points_1 = _get_relevant_points(yaw, p, ls, angle / 2)
    if not math.isclose(angle, 180):
        rel_points_2 = _get_relevant_points(yaw, p, ls, - angle / 2)
    else:
        rel_points_2 = rel_points_1
    p_closest = None
    closest = None
    for rp in set(rel_points_1).intersection(set(rel_points_2)):
        dist = p.distance(Point(rp))
        if p_closest is None or dist < closest:
            p_closest = Point(rp)
            closest = dist
    return p_closest