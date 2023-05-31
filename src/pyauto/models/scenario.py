import logging
import random
import time
import os

import numpy
import tqdm

from . import scene, scenery

# Logging
logger = logging.getLogger(__name__)


class Scenario(list):
    def __init__(self, scene_number: int = None, scenes: list[scene.Scene] = None, scenery: scenery.Scenery = None,
                 name: str = "Unnamed Scenario", add_extras: bool = True, more_extras: list[str] = None,
                 load_cp: bool = False, seed: int = None):
        """Ideally you would create loggers and set them based on the proper naming/configurations instead of accepting the default configuration.
        Creates a new scenario, i.e., a list of scenes, which is iterable and supports indexing.
        :param scene_number: Optional number of empty scenes to create.
        :param scenes: Optional list of scenes that make up this scenario. scene_number is ignored if a scene list is
            given.
        :param scenery: An optional scenery (i.e., static elements) of this scenario.
        :param name: Name of this scenario (for printing), "Unnamed Scenario" if not set.
        :param add_extras: Whether to import the extra functionality that is added the classes from owlready2.
        :param more_extras: A name of an importable module that contains more extra functionality to load from. Will be
            imported in the given order. Using wildcards at the end is possible, e.g. "a.b.*", which then recursively
            imports *all* Python files located in the package's (sub)folder(s).
        :param load_cp: Whether to load the criticality_phenomena.owl (and formalization) as well.
        :param seed: An optional seed for consistent random number generation.
        """
        if seed is not None:
            self._initialize_seed(seed)
        self._name = name
        self._scenery = scenery
        if scenery:
            scenery._random = self._random
            scenery._np_random = self._np_random
        logger.debug("Creating scenario " + str(self))
        if scenes is not None and len(scenes) > 0:
            super().__init__(scenes)
            for s in scenes:
                s._random = self._random
                s._np_random = self._np_random
                s.set_scenery(scenery)
        else:
            super().__init__()
            if scene_number is None:
                scene_number = 0
            for _ in range(scene_number):
                self.new_scene(add_extras=add_extras, more_extras=more_extras, load_cp=load_cp, scenery=scenery)
        self._duration = self[-1]._timestamp - self[0]._timestamp
        self._max_time = self[-1]._timestamp

    def _initialize_seed(self, seed: int):
        """
        Creates all required employed pseudo-random number generators with the given seed and stores it.
        :param seed: The seed to initialize with.
        """
        self._seed = seed
        self._random = random.Random(seed)
        self._np_random = numpy.random.RandomState(self._seed)

    def __str__(self):
        return str(self._name)

    def new_scene(self, position: int = -1, timestamp: float | int = None, add_extras: bool = True,
                  more_extras: list[str] = None, load_cp: bool = False, scenery=None):
        """
        Adds a new scene to the scenario.
        :param position: Optional position at which to insert. If -1, the new scene is added at the end.
        :param timestamp: Optional timestamp of the scene. If None, the position is used.
        :param add_extras: Whether to import the extra functionality that is added the classes from owlready2.
        :param more_extras: A name of an importable module that contains more extra functionality to load from. Will be
            imported in the given order. Using wildcards at the end is possible, e.g. "a.b.*", which then recursively
            imports *all* Python files located in the package's (sub)folder(s).
        :param load_cp: Whether to load the criticality_phenomena.owl (and formalization) as well.
        :param scenery: The scenery of the new scene to add.
        """
        if timestamp is None:
            timestamp = position if position >= 0 else len(self)
        self.add_scene(scene.Scene(timestamp=timestamp, parent_scenario=self, scenery=scenery, add_extras=add_extras,
                                   more_extras=more_extras, load_cp=load_cp), position)

    def add_scene(self, new_scene: scene.Scene, position: int = -1):
        """
        Adds the given scene to the scenario. Also propagates the pseudo random number generators of self to the scene.
        :param new_scene: The new scene to add.
        :param position: Optional position at which to insert. If -1, the new scene is added at the end.
        """
        if position == -1:
            position = len(self)
        self.insert(position, new_scene)
        self._duration = self[-1]._timestamp - self[0]._timestamp
        self._max_time = self[-1]._timestamp
        # Propagates RNGs
        new_scene._random = self._random
        new_scene._np_random = self._np_random

    def save_abox(self, file: str = None, format: str = "rdfxml",  save_scenery: bool = True,
                  to_ignore: set[str] = None, create_kbs_file = True, **kargs):
        """
        Saves the ABoxes auf this A.U.T.O. scenario (without saving the TBox).
        Note that right now, only the "rdfxml" format is supported. If some other format is given, the plain save()
        method is executed. This method also removes all existing color individuals of A.U.T.O.'s physics ontology since
        we do not want to have those individuals doubly present.
        It adds an import to the internet location of A.U.T.O. such that the ABox is well-defined by the imports.
        Note: This method overwrites existing files.
        :param save_scenery: Whether to save the scenery as well (otherwise, it will not be present in the saved
            ABoxes). If no file is given, the scenery is not saved to a file as well.
        :param file: A string to a file location to save the ABox to. Scenes are appended by _i, where i is their index.
        :param format: The format to save in (one of: rdfxml, ntriples, nquads). Recommended: rdfxml.
        :param to_ignore: If given, individuals (also indirectly) belonging to this set of classes are not saved.
            Classes are given as their string representation including their namespace (e.g. geosparql.Geometry).
        :param create_kbs_file: Will additionally create a .kbs file stored along the single scene ABoxes files named
            "file_base_name.kbs".
        """
        def inject_in_filename(filename: str, appendix: str, new_ending: str=None):
            if "." in filename:
                s = filename.split(".")
                s[-2] = s[-2] + appendix
                if new_ending is not None:
                    s[-1] = new_ending
                appended_filename = ".".join(s)
            else:
                if new_ending:
                    new_ending = "." + new_ending
                appended_filename = filename + appendix + (new_ending or "")
            return appended_filename

        # Saves scenery
        scenery_file = None
        if save_scenery:
            scenery_file = inject_in_filename(file, "_scenery")

        if self._scenery is not None:
            self._scenery.save_abox(file=scenery_file, format=format, to_ignore=to_ignore, **kargs)

        # Create IRI to use for all scenes
        file_name = os.path.basename(file)
        if "." in file_name:
            file_name = file_name.split(".")[0]
        iri = "http://purl.org/auto/" + file_name

        if create_kbs_file:
            kbs_file = inject_in_filename(file, "", new_ending="kbs")

        # Saves all scenes
        scene_files = []
        for i, _scene in enumerate(self):
            scene_file = None
            if file is not None:
                if "." in file:
                    s = file.split(".")
                    s[len(s) - 2] = s[len(s) - 2] + "_" + str(i)
                    scene_file = ".".join(s)
                else:
                    scene_file = file + "_" + str(i)
                if create_kbs_file:
                    scene_files.append(scene_file)
            _scene.save_abox(format=format, scenery_file=scenery_file, save_scenery=False, file=scene_file,
                                   to_ignore=to_ignore, iri=iri, **kargs)

        info_msg = "Saved ABox of " + str(self) + " to " + inject_in_filename(file, "_*")

        # Creates .kbs file
        if create_kbs_file:
            with open(kbs_file, "w") as f:
                f.write("\n".join(scene_files))
            info_msg += " and " + kbs_file

        logger.info(info_msg)

    def set_scenery(self, scenery: scenery.Scenery):
        """
        Sets the scenery for all scenes in this scenario. Note that this method shall be called after setting all
        scenes that shall have this scenery.
        """
        self._scenery = scenery
        scenery._scenario = self
        for sc in self:
            sc.set_scenery(scenery)

    def simulate(self, duration: float | int, delta_t: int | float, to_keep: set = None, prioritize: list[str] = None,
                 stop_at_accidents=True, seed: int = None) -> bool:
        """
        Simulates the future of this scenario, starting from its last scene up to the given duration. Discretizes with
        the given Hertz. Only works if this scenario has at least one scene.
        Note: Changes this scenario, and returns nothing.
        :param duration: The duration (in seconds) which to simulate.
        :param delta_t: The time period between each simulated scene (in seconds).
        :param to_keep: The properties of individuals to copy over when creating new scenes.
        :param prioritize: A list of OWL classes or attributes of those individuals who are to prioritize in simulation.
        :param stop_at_accidents: If true, stops the simulation if an accident happened.
        :returns: True iff. an accident happened in the simulated scenario.
        """
        accident_happened = False

        if len(self) > 0 and duration > 0:
            t = time.time()
            start_t = self[-1]._timestamp
            timestamps = numpy.linspace(start_t + delta_t, start_t + duration, int(duration / delta_t))
            logger.info("Simulating " + str(len(timestamps)) + " scenes (" + str(duration) + "s @ " +
                        str(int(1 / delta_t)) + "Hz) of " + str(self))
            if (logger.level >= logging.INFO) or \
                    (logger.level == logging.NOTSET and logging.root.level >= logging.INFO):
                timestamps = tqdm.tqdm(timestamps)
            for i in timestamps:
                if "." in str(delta_t):
                    i = numpy.round(i, len(str(delta_t).split(".")[1]))
                logger.debug("Simulating scene " + str(i) + " / " + str(start_t + duration))
                new_scene = self[-1].simulate(delta_t=delta_t, to_keep=to_keep, prioritize=prioritize)
                self.add_scene(new_scene)
                accident_happened |= new_scene.has_accident()
                if stop_at_accidents and accident_happened:
                    logger.info("Detected accident during simulation, aborting at " + str(i) + ".")
                    break
            total_time = time.time() - t
            if duration > 0:
                time_per_scene = total_time / (duration / delta_t)
                time_per_simulated_second = total_time / duration
            else:
                time_per_scene = 0.0
                time_per_simulated_second = 0.0
            logger.info("Simulation took %.2f seconds (%.2f seconds per scene and %.2f seconds per simulated second)." %
                        (total_time, time_per_scene, time_per_simulated_second))
        elif len(self) == 0:
            logger.warning("Can not simulate without an initial scene.")

        return accident_happened

    def augment(self):
        """
        Augments the scenes in this scenario by using the `owlready2_augmentator`. Augmentation methods are given in
        `extras`.
        Note that only those methods will be called for augmentations that are decorated with @augment within classes
        that are decorated with @augment_class and loaded by a Python import.
        """
        logger.info("Augmenting scenario " + str(self))
        for _scene in tqdm.tqdm(self):
            _scene.augment()

