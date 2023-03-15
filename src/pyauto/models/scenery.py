from . import scene


class Scenery(scene.Scene):
    def __init__(self, add_extras: bool = True, more_extras: list[str] = None, load_cp: bool = False, name: str = None):
        super().__init__(add_extras=add_extras, more_extras=more_extras, load_cp=load_cp, name=name)

    def save_abox(self, file: str = None, format: str = "rdfxml", to_ignore: set[str] = None, **kargs) -> str:
        # Scenery can not save scenery, therefore parameters are omitted.
        return super().save_abox(file=file, format=format, save_scenery=False, to_ignore=to_ignore, **kargs)
