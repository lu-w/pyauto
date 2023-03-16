from shapely.geometry import Polygon, LineString, Point


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
