import math
import owlready2

from functools import cache

from shapely import geometry, wkt, affinity
from owlready2_augmentator import augment, augment_class, AugmentationType
from ... import auto
from .. import utils

_SPATIAL_PREDICATE_THRESHOLD = 50  # m, the distance in which spatial predicates are augmented
_IS_NEAR_DISTANCE = 4              # m, the distance for which spatial objects are close to each other
_IS_IN_PROXIMITY_DISTANCE = 15     # m, the distance for which spatial objects are in proximity to each other

physics = auto.world.get_ontology(auto.Ontology.Physics.value)

with physics:

    @augment_class
    class Spatial_Object(owlready2.Thing):
        def set_geometry(self, x: float, y: float, length: float = None, width: float = None, rotate: float = 0):
            """
            Sets the geometry for this object as a WKT using a new GeoSPARQL Geometry individual with the data property
            hasWKT. If only x, y are given, sets as a point. If length and width are given, a rectangle around x, y is
            created.
            :param x: The x coordinate of the center of the object.
            :param y: The y coordinate of the center of the object.
            :param length: The length of the rectangle to create (along the x-coordinate).
            :param width: The width of the rectangle to create (along the y coordinate).
            :param rotate: An optional rotation angle in degrees. Positive angles are counter-clockwise and negative
                are clockwise rotations (as stated in the shapely documentation). Rotation is performed around the
                centroid.
            """
            geom = self.namespace.world.get_ontology(auto.Ontology.GeoSPARQL.value).Geometry()
            if length is None or width is None:
                geom.asWKT = [geometry.Point(x, y).wkt]
                self.has_width = 0
            else:
                if length >= width:
                    p = [(x - length / 2, y - width / 2),
                         (x + length / 2, y - width / 2),
                         (x + length / 2, y + width / 2),
                         (x - length / 2, y + width / 2)]
                else:
                    p = [(x + length / 2, y - width / 2),
                         (x + length / 2, y + width / 2),
                         (x - length / 2, y + width / 2),
                         (x - length / 2, y - width / 2)]
                g = geometry.Polygon(p)
                if rotate != 0:
                    g = affinity.rotate(g, rotate, origin="centroid")
                geom.asWKT = [g.wkt]
                self.has_length = length
                self.has_width = width
            self.hasGeometry = [geom]
            self.get_geometry.cache_clear()

        def set_shapely_geometry(self, geometry: geometry.base.BaseGeometry):
            """
            Sets the given shapely geometry for the spatial object, by creating a WKT string an the GeoSPARQL objects.
            :param geometry: The shapely geometry (has to support wkt property)
            """
            geom = self.namespace.world.get_ontology(auto.Ontology.GeoSPARQL.value).Geometry()
            geom.asWKT = [geometry.wkt]
            self.hasGeometry = [geom]

        def has_geometry(self) -> bool:
            """
            Returns true iff x has a geometry represented as a WKT literal.
            :returns: whether this object has a geometry.
            """
            try:
                return hasattr(self, "hasGeometry") and len(self.hasGeometry) > 0 and \
                    len(self.hasGeometry[0].asWKT) > 0 and self.hasGeometry[0].asWKT[0] != "POLYGON EMPTY"
            except TypeError:
                return False

        @cache
        def get_geometry(self) -> geometry.base.BaseGeometry:
            """
            Returns the geometry as a shapely BaseGeometry of this object, only if this object has a geometry.
            Otherwise, it returns None.
            :returns: The geometry of this object or None.
            """
            if self.has_geometry():
                return wkt.loads(self.hasGeometry[0].asWKT[0])  # .buffer(0)

        def get_distance(self, other: physics.Spatial_Object):
            if other is not None and self.has_geometry() and other.has_geometry():
                p1 = wkt.loads(self.hasGeometry[0].asWKT[0])
                p2 = wkt.loads(other.hasGeometry[0].asWKT[0])
                return float(p1.distance(p2))

        def compute_angle_between_yaw_and_point(self, p) -> float:
            """
            Computes the angle between the point p and the vector starting from self's centroid with self's yaw angle.
            If this object does not have geometry or yaw, returns None.
            :param p: A point (list, tuple, or geometry.Point)
            :returns: An angle a in degrees (0 <= a < 360)
            """
            geom = self.get_geometry()
            if geom is not None and self.has_yaw is not None:
                p_yaw = [math.cos(math.radians(self.has_yaw)), math.sin(math.radians(self.has_yaw))]
                p_self = [p[0] - geom.centroid.x, p[1] - geom.centroid.y]
                angle = math.degrees(math.atan2(*p_yaw) - math.atan2(*p_self)) % 360
                return angle

        def is_point_right_of(self, p) -> float:
            """
            :param p: A point (list, tuple, or geometry.Point)
            :returns: True iff. p is right of self, given self has a yaw to determine its direction. None otherwise.
            """
            geom = self.get_geometry()
            if geom is not None and self.has_yaw is not None:
                p_yaw = [math.cos(math.radians(self.has_yaw)), math.sin(math.radians(self.has_yaw))]
                p_self = [p[0] - geom.centroid.x, p[1] - geom.centroid.y]
                angle = math.degrees(math.atan2(*p_self)) - math.degrees(math.atan2(*p_yaw))
                return (0 < angle < 180) or (-360 < angle < -180)


        def compute_left_front_point(self) -> tuple:
            """
            :returns: The left front point of self's boundary (front-left determined through its yaw).
            """
            try:
                g = self.get_geometry()
                for p in zip(g.boundary.xy[0], g.boundary.xy[1]):
                    angle = self.compute_angle_between_yaw_and_point(p)
                    if 270 <= angle < 360:
                        return p
            except NotImplementedError:
                return self.centroid

        def compute_right_front_point(self) -> tuple:
            """
            :returns: The right front point of self's boundary (front-left determined through its yaw).
            """
            try:
                g = self.get_geometry()
                for p in zip(g.boundary.xy[0], g.boundary.xy[1]):
                    angle = self.compute_angle_between_yaw_and_point(p)
                    if 0 <= angle < 90:
                        return p
            except NotImplementedError:
                return self.centroid

        def compute_left_back_point(self) -> tuple:
            """
            :returns: The right front point of self's boundary (front-left determined through its yaw).
            """
            try:
                g = self.get_geometry()
                for p in zip(g.boundary.xy[0], g.boundary.xy[1]):
                    angle = self.compute_angle_between_yaw_and_point(p)
                    if 180 <= angle < 270:
                        return p
            except NotImplementedError:
                return self.centroid

        def compute_right_back_point(self) -> tuple:
            """
            :returns: The right front point of self's boundary (front-left determined through its yaw).
            """
            try:
                g = self.get_geometry()
                for p in zip(g.boundary.xy[0], g.boundary.xy[1]):
                    angle = self.compute_angle_between_yaw_and_point(p)
                    if 90 <= angle < 180:
                        return p
            except NotImplementedError:
                return self.centroid

        def convert_local_to_global_vector(self, v: list) -> tuple:
            """
            Converts the given vector in vehicle coordinate system to the global one under this object's yaw.
            If this object does not have a yaw, returns None.
            :param v: A list of scalars
            """
            if self.has_yaw is not None:
                vx = math.cos(math.radians(self.has_yaw)) * v[0] - math.sin(math.radians(self.has_yaw)) * v[1]
                vy = math.sin(math.radians(self.has_yaw)) * v[0] + math.cos(math.radians(self.has_yaw)) * v[1]
                return vx, vy

        @augment(AugmentationType.OBJECT_PROPERTY, "is_in_proximity")
        def in_proximity(self, other: physics.Spatial_Object):
            if other is not None and self.has_geometry() and other.has_geometry():
                p1 = wkt.loads(self.hasGeometry[0].asWKT[0])
                p2 = wkt.loads(other.hasGeometry[0].asWKT[0])
                if float(p1.distance(p2)) < _IS_IN_PROXIMITY_DISTANCE:
                    return True

        @augment(AugmentationType.OBJECT_PROPERTY, "is_near")
        def near(self, other: physics.Spatial_Object):
            if other is not None and self.has_geometry() and other.has_geometry():
                p1 = wkt.loads(self.hasGeometry[0].asWKT[0])
                p2 = wkt.loads(other.hasGeometry[0].asWKT[0])
                if float(p1.distance(p2)) < _IS_NEAR_DISTANCE:
                    return True

        @augment(AugmentationType.OBJECT_PROPERTY, "sfIntersects")
        def intersects(self, other: physics.Spatial_Object):
            if other is not None and self.has_geometry() and other.has_geometry():
                geo_self = wkt.loads(self.hasGeometry[0].asWKT[0])
                geo_other = wkt.loads(other.hasGeometry[0].asWKT[0])
                return geo_self.intersects(geo_other)

        @augment(AugmentationType.OBJECT_PROPERTY, "sfOverlaps")
        def overlaps(self, other: physics.Spatial_Object):
            if other is not None and self.has_geometry() and other.has_geometry():
                geo_self = wkt.loads(self.hasGeometry[0].asWKT[0])
                geo_other = wkt.loads(other.hasGeometry[0].asWKT[0])
                return geo_self.overlaps(geo_other)

        @augment(AugmentationType.OBJECT_PROPERTY, "sfTouches")
        def touches(self, other: physics.Spatial_Object):
            if other is not None and self.has_geometry() and other.has_geometry():
                geo_self = wkt.loads(self.hasGeometry[0].asWKT[0])
                geo_other = wkt.loads(other.hasGeometry[0].asWKT[0])
                return geo_self.touches(geo_other)

        @augment(AugmentationType.OBJECT_PROPERTY, "sfWithin")
        def within(self, other: physics.Spatial_Object):
            if other is not None and self.has_geometry() and other.has_geometry():
                geo_self = wkt.loads(self.hasGeometry[0].asWKT[0])
                geo_other = wkt.loads(other.hasGeometry[0].asWKT[0])
                return geo_self.within(geo_other)

        @augment(AugmentationType.OBJECT_PROPERTY, "sfDisjoint")
        def disjoint(self, other: physics.Spatial_Object):
            if other is not None and self.has_geometry() and other.has_geometry():
                geo_self = wkt.loads(self.hasGeometry[0].asWKT[0])
                geo_other = wkt.loads(other.hasGeometry[0].asWKT[0])
                if float(geo_self.distance(geo_other)) <= _SPATIAL_PREDICATE_THRESHOLD:
                    return geo_self.disjoint(geo_other)

        @augment(AugmentationType.OBJECT_PROPERTY, "sfCrosses")
        def crosses(self, other: physics.Spatial_Object):
            if other is not None and self.has_geometry() and other.has_geometry():
                geo_self = wkt.loads(self.hasGeometry[0].asWKT[0])
                geo_other = wkt.loads(other.hasGeometry[0].asWKT[0])
                return geo_self.crosses(geo_other)

        @augment(AugmentationType.OBJECT_PROPERTY, "sfContains")
        def contains(self, other: physics.Spatial_Object):
            if other is not None and self.has_geometry() and other.has_geometry():
                geo_self = wkt.loads(self.hasGeometry[0].asWKT[0])
                geo_other = wkt.loads(other.hasGeometry[0].asWKT[0])
                return geo_self.contains(geo_other)

        @augment(AugmentationType.OBJECT_PROPERTY, "is_behind")
        def behind(self, other: physics.Dynamical_Object):
            if other is not None and self != other and self.has_geometry() and other.has_geometry() and \
                    other.has_yaw is not None:
                p_1 = wkt.loads(self.hasGeometry[0].asWKT[0]).centroid
                p_2 = wkt.loads(other.hasGeometry[0].asWKT[0]).centroid
                if float(p_1.distance(p_2)) <= _SPATIAL_PREDICATE_THRESHOLD and not (math.isclose(p_1.x, p_2.x) and
                                                                                     math.isclose(p_1.y, p_2.y)):
                    p_yaw = [math.cos(math.radians(other.has_yaw)), math.sin(math.radians(other.has_yaw))]
                    p_self = [p_1.x - p_2.x, p_1.y - p_2.y]
                    angle = math.degrees(math.atan2(*p_yaw) - math.atan2(*p_self)) % 360
                    return 90 < angle < 270

        @augment(AugmentationType.OBJECT_PROPERTY, "is_left_of")
        def left_of(self, other: physics.Dynamical_Object):
            if other is not None and self != other and self.has_geometry() and other.has_geometry() and \
                    other.has_yaw is not None:
                p_1 = wkt.loads(self.hasGeometry[0].asWKT[0]).centroid
                p_2 = wkt.loads(other.hasGeometry[0].asWKT[0]).centroid
                if float(p_1.distance(p_2)) <= _SPATIAL_PREDICATE_THRESHOLD and not (math.isclose(p_1.x, p_2.x) and
                                                                                     math.isclose(p_1.y, p_2.y)):
                    p_yaw = [math.cos(math.radians(other.has_yaw)), math.sin(math.radians(other.has_yaw))]
                    p_self = [p_1.x - p_2.x, p_1.y - p_2.y]
                    angle = math.degrees(math.atan2(*p_yaw) - math.atan2(*p_self)) % 360
                    return 0 < angle < 180

        @augment(AugmentationType.OBJECT_PROPERTY, "is_right_of")
        def right_of(self, other: physics.Dynamical_Object):
            if other is not None and self != other and self.has_geometry() and other.has_geometry() and \
                    other.has_yaw is not None:
                p_1 = wkt.loads(self.hasGeometry[0].asWKT[0]).centroid
                p_2 = wkt.loads(other.hasGeometry[0].asWKT[0]).centroid
                if float(p_1.distance(p_2)) <= _SPATIAL_PREDICATE_THRESHOLD and not (math.isclose(p_1.x, p_2.x) and
                                                                                     math.isclose(p_1.y, p_2.y)):
                    p_yaw = [math.cos(math.radians(other.has_yaw)), math.sin(math.radians(other.has_yaw))]
                    p_self = [p_1.x - p_2.x, p_1.y - p_2.y]
                    angle = math.degrees(math.atan2(*p_yaw) - math.atan2(*p_self)) % 360
                    return 180 < angle < 360

        @augment(AugmentationType.OBJECT_PROPERTY, "is_in_front_of")
        def in_front_of(self, other: physics.Dynamical_Object):
            if other is not None and self != other and self.has_geometry() and other.has_geometry() and \
                    other.has_yaw is not None:
                p_1 = wkt.loads(self.hasGeometry[0].asWKT[0]).centroid
                p_2 = wkt.loads(other.hasGeometry[0].asWKT[0]).centroid
                if float(p_1.distance(p_2)) <= _SPATIAL_PREDICATE_THRESHOLD and not (math.isclose(p_1.x, p_2.x) and
                                                                                     math.isclose(p_1.y, p_2.y)):
                    return utils.in_front_of(p_1, p_2, other.has_yaw)

        @cache
        def get_end(self, angle: float, p: tuple, length: float=1) -> geometry.Polygon:
            """
            Returns the end of the spatial object when viewed from the given point at the given angle.
            Assumption: Only works if the geometry of this object is given as a polygon with a symmetrical point list.
            :param angle: Viewing angle (in degrees, global)
            :param p: Viewing point (as tuple)
            :param length: Length (meters) of the end piece to find, default is 1 meter.
            :returns: A polygon representing the end piece of the object, or the whole object geometry if no end could
                be uniquely determined (i.e., p is exactly in the middle and the angle points similarly away w.r.t. both
                ends.
            """
            def get_incremental_closest_point_from_yaw(line, p, angle, init_field_of_relevance=60,
                                                       max_field_over_relevance=100, step_size=10):
                i = 0
                p_c = None
                while p_c is None and init_field_of_relevance + i <= max_field_over_relevance:
                    p_c = utils.get_closest_point_from_yaw(line, p, angle, init_field_of_relevance + i)
                    i += step_size
                return p_c

            p = geometry.Point(p)
            g = self.get_geometry()
            _, _, front, back = utils.split_polygon_into_boundaries(g)
            p_f = get_incremental_closest_point_from_yaw(front, p, angle)
            p_b = get_incremental_closest_point_from_yaw(back, p, angle)
            end = None
            if p_b is None or (p_f is not None and p_f.distance(p) < p_b.distance(p)):
                end = front
            elif p_f is None or (p_b is not None and p_f.distance(p) >= p_b.distance(p)):
                end = back
            if end is not None:
                return end.centroid.buffer(length * 2).intersection(g)
            else:
                logger.warning("No end found for object " + str(self) + " from " + str(p) + " angled " + str(angle))
                return g

        def has_accident_with(self, other: physics.Spatial_Object):
            """
            :returns: True iff. this object has an accident with another object, i.e., their geometries have an
            intersection and both objects are of non-zero height.
            """
            return self.has_height and other.has_height and self.has_geometry() and other.has_geometry() and \
                other.get_geometry().intersects(self.get_geometry()) and \
                ((not hasattr(self, "drives") or other not in self.drives) and
                 (not hasattr(other, "drives") or self not in other.drives))
