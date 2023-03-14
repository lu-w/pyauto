from pyauto.models.scene import Scene


class Scenery(Scene):
    def __init__(self, add_extras: bool = True, load_cp: bool = False):
        super().__init__(add_extras, load_cp)
        self.iri = None  # can only be set once save_abox was called since the IRI depends on the file name

    def save_abox(self, file: str = None, format: str = "rdfxml", to_ignore: set[str] = None, **kargs) -> str:
        # Scenery can not save scenery, therefore parameters are omitted.
        iri = super().save_abox(file=file, format=format, save_scenery=False, to_ignore=to_ignore, **kargs)
        # We only update self's iri once with the file name
        if self.iri is None:
            self.iri = "file://" + file + "#"
        return iri
