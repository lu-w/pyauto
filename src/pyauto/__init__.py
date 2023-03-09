import logging

# Suppresses unnecessary logging in debug mode by imported libraries for plotting / geometric computations.
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
logging.getLogger("shapely.geos").setLevel(logging.WARNING)
