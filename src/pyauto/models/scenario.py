from pyauto.models import scene


class Scenario(list):
    def __init__(self, scene_number: int = None, scenes: list[scene.Scene] = None, name: str = "Unnamed Scenario",
                 add_extras: bool = True, load_cp: bool = False):
        """
        Creates a new scenario, i.e., a list of scenes, which is iterable and supports indexing.
        :param scene_number: Optional number of empty scenes to create.
        :param scenes: Optional list of scenes that make up this scenario. scene_number is ignored if a scene list is
            given.
        :param name: Name of this scenario (for printing), "Unnamed Scenario" if not set.
        :param add_extras: Whether to import the extra functionality that is added the classes from owlready2.
        :param load_cp: Whether to load the criticality_phenomena.owl (and formalization) as well.
        """
        self._name = name
        if scenes is not None and len(scenes) > 0:
            super().__init__(scenes)
        else:
            super().__init__()
            if scene_number is None:
                scene_number = 0
            for _ in range(scene_number):
                self.new_scene(add_extras=add_extras, load_cp=load_cp)

    def __str__(self):
        return str(self._name)

    def new_scene(self, position: int = -1, timestamp: float | int = None, add_extras: bool = True,
                  load_cp: bool = False):
        """
        Adds a new scene to the scenario.
        :param position: Optional position at which to insert. If -1, the new scene is added at the end.
        :param timestamp: Optional timestamp of the scene. If None, the position is used.
        :param add_extras: Whether to import the extra functionality that is added the classes from owlready2.
        :param load_cp: Whether to load the criticality_phenomena.owl (and formalization) as well.
        """
        if timestamp is None:
            timestamp = position if position >= 0 else len(self)
        self.add_scene(scene.Scene(timestamp=timestamp, parent_scenario=self, add_extras=add_extras, load_cp=load_cp),
                       position)

    def add_scene(self, new_scene: scene.Scene, position: int = -1):
        """
        Adds the given scene to the scenario.
        :param new_scene: The new scene to add.
        :param position: Optional position at which to insert. If -1, the new scene is added at the end.
        """
        if position == -1:
            position = len(self)
        self.insert(position, new_scene)

    def save_abox(self, file: str = None, format: str = "rdfxml", **kargs):
        """
        Saves the ABoxes auf this A.U.T.O. scenario (without saving the TBox).
        Note that right now, only the "rdfxml" format is supported. If some other format is given, the plain save()
        method is executed. This method also removes all existing color individuals of A.U.T.O.'s physics ontology since
        we do not want to have those individuals doubly present.
        It adds an import to the internet location of A.U.T.O. such that the ABox is well-defined by the imports.
        Note: This method overwrites existing files.
        :param file: A string to a file location to save the ABox to. Scenes are appended by _i, where i is their index.
        :param format: The format to save in (one of: rdfxml, ntriples, nquads). Recommended: rdfxml.
        """
        for i, _scene in enumerate(self):
            if file is not None:
                if "." in file:
                    s = file.split(".")
                    s[len(s) - 2] = s[len(s) - 2] + "_" + str(i)
                    scene_file = ".".join(s)
                else:
                    scene_file = file + "_" + str(i)
            else:
                scene_file = None
            _scene.save_abox(scene_file, format, **kargs)
