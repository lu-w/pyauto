import math
import logging

from shapely.geometry import Polygon, LineString, Point

logger = logging.getLogger(__name__)


def split_polygon_into_boundaries(p: Polygon, splitting_points: tuple[Point, Point, Point] = None) \
        -> tuple[LineString, LineString, LineString, LineString]:
    """
    Splits a polygon into its left, right, front, and back boundaries (as a tuple of new LineString).
    Assumptions: The polygon has the same number of points on each side, and its ends (i.e, front and back) are
    represented only by two points. Then, the right part will be from the beginning of p to the end point of its first
    half, the front part will be from there to the beginning point of p's second half, and the part of the beginning of
    p's second half to the last point of p is the left part. The back connects the first and last point of p.
    Note: assumes at least four, and an even number of points present in p's boundary.
    :param p: The polygon to split
    :param splitting_points: If the above assumption does not hold, this is the set of points to split the polygon at.
        Right part will be from the beginning of p to the first splitting point, the front part will be from there to
        the second splitting point, and the part up to the last splitting point will be the left part. The back connects
        the first point of p with the last splitting point.
    :returns: A tuple of new LineString
    """
    # TODO: implement splitting points
    coords = p.boundary.coords[:-1]  # last point is the first for a closed polygon - ignore it
    assert(len(coords) >= 4 and len(coords) % 2 == 0)
    half = int(len(coords) / 2)
    right_coords = coords[:half]
    front_coords = [coords[half - 1], coords[half]]
    left_coords = reversed(coords[half:len(coords)])
    back_coords = [coords[0], coords[len(coords) - 1]]
    right = LineString(right_coords)
    front = LineString(front_coords)
    left = LineString(left_coords)
    back = LineString(back_coords)
    return left, right, front, back


def get_closest_point_from_yaw(ls: LineString, p: Point, yaw: float | int) -> Point:
    """
    Finds the nearest point in the line string based on the given point and yaw (i.e., only examines points within the
    180° field in which the yaw points from the given point).
    :param ls: The line string to examine
    :param p: The point for which to get the closest point
    :param yaw: The viewing angle to consider when looking for the closest point.
    :returns: The closes point of the line string based on the yaw or None if there is no point of ls in the 180° field.
    """
    yaw_p = (yaw - 90) % 360
    p_2 = Point(math.cos(math.radians(yaw_p)) + p.x, math.sin(math.radians(yaw_p)) + p.y)
    if p_2.x - p.x != 0:
        m = (p_2.y - p.y) / (p_2.x - p.x)
        b = p.y - m * p.x
    else:  # case: yaw is 0° or 180°
        m = None
        b = None
    relevant_points = []
    for lp in ls.coords:
        if m is not None:
            div_y = m * lp[0] + b
            if 0 < yaw <= 180:
                if lp[1] >= div_y:
                    relevant_points.append(lp)
            else:
                if lp[1] < div_y:
                    relevant_points.append(lp)
        else:
            if yaw == 0:
                if p.x <= lp[0]:
                    relevant_points.append(lp)
            elif yaw == 180:
                if p.x > lp[0]:
                    relevant_points.append(lp)
            else:
                logger.warning("Assumed yaw to be 0 or 180, but this does not seem to hold.")
    p_closest = None
    closest = None
    for rp in relevant_points:
        dist = p.distance(Point(rp))
        if p_closest is None or dist < closest:
            p_closest = Point(rp)
            closest = dist
    return p_closest
