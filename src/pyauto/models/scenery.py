from functools import cache

from shapely import geometry, wkt

from pyauto import auto

from . import scene


class Scenery(scene.Scene):
    """
    The scenery contains all 'static' (i.e., temporally not changing) individuals.
    Individuals within the scenery are annotated with the _SCENERY_COMMENT of scene.Scene for unique identification in
    OWL files later on.
    """
    def __init__(self, add_extras: bool = True, more_extras: list[str] = None, folder: str = None,
                 load_cp: bool = False, name: str = None):
        super().__init__(add_extras=add_extras, more_extras=more_extras, folder=folder, load_cp=load_cp, name=name)

    def save_abox(self, file: str = None, format: str = "rdfxml", to_ignore: set[str] = None, **kargs) -> str:
        # Scenery can not save scenery, therefore parameters are omitted.
        return super().save_abox(file=file, format=format, save_scenery=False, to_ignore=to_ignore, **kargs)

    @cache
    def get_all_driveable_lanes_geometry(self) -> geometry.base.BaseGeometry:
        """
        :returns: The union of all the geometries of all driveable lanes in this scenery.
        """
        l1_core = self.ontology(auto.Ontology.L1_Core)
        lanes_geom = geometry.Point()
        for lane in self.search(type=l1_core.Driveable_Lane):
            if hasattr(lane, "hasGeometry") and len(lane.hasGeometry) > 0:
                lanes_geom = lanes_geom.union(wkt.loads(lane.hasGeometry[0].asWKT[0]))
        return lanes_geom
