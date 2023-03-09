import owlready2
import owlready2_augmentator


def augment(*worlds: owlready2.World):
    """
    Augments the given worlds by using the `owlready2_augmentator`. Augmentation methods are given in `extras`.
    Note that only those methods will be called for augmentations that are decorated with @augment within classes that
    are decorated with @augment_class.
    :param worlds: The worlds to run the augmentation on (in the given order). Worlds' individuals will be changed.
    """
    # TODO enforce ordering of ontologies to be correct (i.e. physics first)
    for world in worlds:
        owlready2_augmentator.reset()
        owlready2_augmentator.do_augmentation(*world.ontologies.values())
