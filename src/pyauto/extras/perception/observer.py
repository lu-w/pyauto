import math
import numpy
import owlready2

from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely import wkt

from owlready2_augmentator import augment, augment_class, AugmentationType

from ... import auto

_DEFAULT_VISIBILITY = 50  # m, the visibility that is assumed if the observer does not have a specific visibility given
_OCCLUSION_SAMPLING_STEP = 0.25  # °, the step size that is used to sample the circular segment for occluded areas


def get_occluded_areas(others: list, fov, visibility=None):
    """
    Calculate occluded areas for a list of objects within a given field of view.
    This function computes the occluded areas of a list of objects based on their geometries and the field of view.
    The occluded areas are determined by considering the visibility from the field of view centroid to the object
    boundaries.
    :param others: A list of individuals for which occluded areas will be calculated.
    :param fov: The field of view geometry used for occlusion calculations.
    :param visibility: The optional visibility distance. If not provided, _DEFAULT_VISIBILITY is used.
    :return: A dictionary containing occluded areas as shapely geometries associated with their corresponding objects.
    """
    if visibility is None:
        visibility = _DEFAULT_VISIBILITY
    cutoffs = dict()
    geos = []
    for x in others:
        geo = wkt.loads(wkt.dumps(wkt.loads(x.hasGeometry[0].asWKT[0]), output_dimension=2)).buffer(0)
        geos.append(geo.intersection(fov))
    for i, a in enumerate(geos):
        if isinstance(a, Point):
            points = [(a.x, a.y)]
        else:
            points = list(zip(a.exterior.xy[0], a.exterior.xy[1]))
        angles = []
        angle_points = []
        for p in points:
            rel_p = (p[0] - fov.centroid.x, p[1] - fov.centroid.y)
            angles.append(math.degrees(math.atan2(rel_p[1], rel_p[0])) % 360)
            angle_points.append(p)
        y_points = [x[1] for x in points]
        if min(y_points) <= fov.centroid.y <= max(y_points) and len([x for x in angles if x < 90]) > 0 and \
                len([x for x in angles if x > 270]) > 0:
            min_angle = min([x for x in angles if x >= 180])
            max_angle = max([x for x in angles if x < 180])
        else:
            min_angle = min(angles)
            max_angle = max(angles)
        samples = []
        for alpha in numpy.arange(0, (max_angle - min_angle) % 360, _OCCLUSION_SAMPLING_STEP):
            angle = (min_angle + alpha) % 360
            samples.append((visibility * math.cos(math.radians(angle)) + fov.centroid.x,
                            visibility * math.sin(math.radians(angle)) + fov.centroid.y))
        samples += [points[angles.index(max_angle)], points[angles.index(min_angle)]]
        if len(samples) > 2:
            cutoff = Polygon(samples)
        elif len(samples) == 2:
            cutoff = LineString(samples)
        elif len(samples) == 1:
            cutoff = Point(samples)
        else:
            cutoff = Polygon()
        cutoff = cutoff.buffer(0).union(a)
        cutoffs[others[i]] = cutoff
    return cutoffs


def get_occlusions(others: list, cutoffs: dict, fov):
    """
    Compute occlusions for the given list of objects.

    This function calculates occlusions for a list of objects based on their geometries, cutoffs, and field of view.
    The occlusion calculation is performed by determining the intersection of object geometries with the field of view,
    considering cutoff geometries for occlusion checks.

    :param others: A list of objects to be considered for occlusion calculations.
    :param cutoffs: A dictionary containing the geometries of occluded areas as determined by get_occluded_areas().
    :param fov: The field of view geometry used for occlusion calculations.
    :return: A list of occlusions, where each occlusion is represented as a tuple containing:
              - A list of occluded geometries.
              - The occluded object.
              - The calculated occlusion percentage.
    """
    occs = []
    geos = [wkt.loads(wkt.dumps(wkt.loads(x.hasGeometry[0].asWKT[0]), output_dimension=2)).buffer(0)
            for x in others]
    for i, geom in enumerate(geos):
        fov_intersection = geom.intersection(fov).area
        if fov_intersection > 0:
            ints = []
            for a in cutoffs.keys():
                if a != others[i]:
                    intersection = geom.intersection(cutoffs[a])
                    if intersection.area > 0:
                        ints.append((a, intersection))
            if len(ints) > 0:
                union = ints[0][1]
                for j in ints[1:]:
                    union = union.union(j[1])
                percentage = min(int((union.area / fov_intersection) * 100) / 100, 1.0)
                occ = ([j[0] for j in ints], others[i], percentage)
                occs.append(occ)
    return occs


perception = auto.world.get_ontology(auto.Ontology.Perception.value)

with perception:

    @augment_class
    class Observer(owlready2.Thing):

        def is_in_fov(self, self_geom, other: owlready2.Thing, fov, ignore_height=False) -> bool:
            """
            Checks whether a given other object is in the field of view of this observer.
            :param self_geom: The geometry of this object.
            :param other: The object to check against.
            :param fov: A shapely geometry representing the field of view of this object.
            :param ignore_height: Whether to ignore the height, i.e. ignore things of height 0.
            """
            if self != other and other.has_geometry() and \
                    ((other.has_height is not None and other.has_height > 0.1) or ignore_height):
                other_geom = wkt.loads(other.hasGeometry[0].asWKT[0])
                return other_geom.intersects(fov) and (ignore_height or not (self_geom.within(other_geom) or
                                                       other_geom.within(self_geom) or
                                                       other_geom.equals(self_geom)))

        @augment(AugmentationType.CLASS_SUBSUMPTION, None)  # This is a bit hacky, but is more performant
        def augment_occlusion(self):
            """
            Computes occlusion to all other objects in the field of view and creates occlusion objects accordingly.
            """
            if self.has_geometry() and (self.has_yaw is not None or (len(self.drives) > 0 and self.drives[0].has_yaw
                                       is not None and self.drives[0].has_geometry())) and \
                    len(self.is_occluded_for_in_occlusion) == 0:
                if self.has_yaw is None:
                    yaw = self.drives[0].has_yaw
                else:
                    yaw = self.has_yaw
                self_geom = wkt.loads(self.hasGeometry[0].asWKT[0])
                if len(self.drives) > 0:
                    length = numpy.linalg.norm(numpy.array(self.drives[0].get_left_back_point()) -
                                               numpy.array(self.drives[0].get_left_front_point())) / 4
                    head = (self_geom.centroid.x + math.cos(math.radians(yaw)) * length,
                            self_geom.centroid.y + math.sin(math.radians(yaw)) * length)
                else:
                    head = (self_geom.centroid.x, self_geom.centroid.y)
                visibility = self.has_visibility_range or _DEFAULT_VISIBILITY
                fov = Point(head).buffer(visibility)
                occluding_others = [x for x in self.namespace.world.individuals() if
                                    self.is_in_fov(self_geom, x, fov)]
                occluded_others = [x for x in self.namespace.world.individuals() if
                                   self.is_in_fov(self_geom, x, fov, ignore_height=True)]
                occluded_areas = get_occluded_areas(occluding_others, fov, self.has_visibility_range or
                                                    _DEFAULT_VISIBILITY)
                occlusions = get_occlusions(occluded_others, occluded_areas, fov)
                for occ in occlusions:
                    if occ[2] > 0.2:
                        # only create occlusion object if more than 20 perc. occluded to avoid 'spamming' the A-Box
                        ont_occ = perception.Is_Occlusion()
                        ont_occ.is_occluded_for = [self]
                        ont_occ.is_occluded_by = occ[0]
                        ont_occ.is_occluded = [occ[1]]
                        ont_occ.has_occlusion_rate = occ[2]
                        ont_occ.in_traffic_model = self.in_traffic_model
