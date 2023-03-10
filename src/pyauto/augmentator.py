import owlready2_augmentator

from pyauto.models import scene, scenario


def augment(model: scene.Scene | scenario.Scenario):
    """
    Augments the given worlds by using the `owlready2_augmentator`. Augmentation methods are given in `extras`.
    Note that only those methods will be called for augmentations that are decorated with @augment within classes that
    are decorated with @augment_class.
    :param model: The worlds to run the augmentation on (in the given order). Worlds' individuals will be changed.
    """
    if isinstance(model, scenario.Scenario):
        for _scene in model:
            print(_scene)
            # _augment_scene(_scene)
    else:
        _augment_scene(model)


def _augment_scene(_scene: scene.Scene):
    """
    Resets the owlready2_augmentator and calls the augmentation process on the given scene. Changes the scene.
    :param _scene: The scene to augment.
    """
    # TODO enforce ordering of ontologies to be correct (i.e. physics first)
    owlready2_augmentator.reset()
    owlready2_augmentator.do_augmentation(*_scene.ontologies.values())