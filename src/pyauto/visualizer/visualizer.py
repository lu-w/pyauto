# Visualizer is for debugging purposes only
import logging
import shutil
import math
import random
import threading
import os
import re
import webbrowser

import mpld3
import tqdm
import screeninfo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from shapely import wkt, geometry
from http.server import SimpleHTTPRequestHandler, HTTPServer

from .. import utils
from ..models.scene import Scene
from ..models.scenario import Scenario


####################
# Config constants #
####################

# Classes to not show in visualization
_NO_PRINTING_CLASSES = {"physics.Has_Distance_To", "perception.Is_Full_Occlusion", "perception.Is_Occlusion",
                        "geosparql.Geometry"}
# Data/object properties to hide from the individual tables shown when hovering
_NO_PRINTING_PROPERTIES = {"perceptional_property", "traffic_related_concept_property",
                           "descriptive_traffic_entity_property", "traffic_entity_property", "activity_property",
                           "physical_property", "traffic_modeling_property", "traffic_entity_property",
                           "automotive_urban_traffic_property", "L1_property", "L2_property", "L3_property",
                           "L4_property", "L5_property", "L6_property", "traffic_model_element_property",
                           "criticality_phenomenon_as_object_property", "has_positional_relation",
                           "has_spatial_relation", "has_dynamical_relation", "SF_spatial_relation",
                           "performance_spatial_relation", "EH_spatial_relation", "RCC8_spatial_relation", "rcc8dc",
                           "ehDisjoint", "comment"}
# If one hides long property lists, this is the number after which the list is cut off
_MAX_PROPS_DISPLAY = 4
_AVOID_LABEL_COLLISIONS = False
_CREATE_SVG_FILES = False

# Logging
logger = logging.getLogger(__name__)
# Suppresses unnecessary logging in debug mode by imported libraries for plotting.
logging.getLogger("matplotlib").setLevel(logging.ERROR)
logging.getLogger("PIL").setLevel(logging.WARNING)


# Helper function for sorting CPs & individuals
def _natural_sort_key(s, _nsre=re.compile("([0-9]+)")):
    return [int(text) if text.isdigit() else text.lower() for text in _nsre.split(str(s))]


# Redirect logging of HTTP server for visualizing to logger (debug)
class VisualizerHTTPHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.debug(args)

#######
# CSS #
#######

# Scene CSS (added is iframes to scenario HTML)
scene_css = """
        <style>
            svg * {
                font-size: 4pt;
            }
            table {
                border: solid 1px #DDEEEE;
                border-collapse: collapse;
                border-spacing: 0;
                font: normal 8px, sans-serif;
            }
            thead th {
                background-color: #DDEFEF;
                border: solid 1px #DDEEEE;
                color: #336B6B;
                padding: 3px;
                text-align: left;
                text-shadow: 1px 1px 1px #fff;
                font-size: 10pt;
            }
            tbody td {
                background-color: #FFFFFF;
                border: solid 1px #DDEEEE;
                color: #333;
                padding: 3px;
                text-shadow: 1px 1px 1px #fff;
                font-size: 8pt;
            }
            .cp-tooltip {}
        </style>
        """

# Scenario CSS (main CSS)
scenario_css = """
        <style>
            .slider {
              -webkit-appearance: none;  /* Override default CSS styles */
              appearance: none;
              width: 100%; /* Full-width */
              height: 25px; /* Specified height */
              background: #d3d3d3; /* Grey background */
              outline: none; /* Remove outline */
              opacity: 0.7; /* Set transparency (for mouse-over effects on hover) */
              -webkit-transition: .2s; /* 0.2 seconds transition on hover */
              transition: opacity .2s;
            }
            .slider:hover {
              opacity: 1; /* Fully shown on mouse-over */
            }
            .slider::-webkit-slider-thumb {
              -webkit-appearance: none; /* Override default look */
              appearance: none;
              width: 25px; /* Set a specific slider handle width */
              height: 25px; /* Slider handle height */
              background: #04AA6D; /* Green background */
              cursor: pointer; /* Cursor on hover */
            }
            .slider::-moz-range-thumb {
              width: 25px; /* Set a specific slider handle width */
              height: 25px; /* Slider handle height */
              background: #04AA6D; /* Green background */
              cursor: pointer; /* Cursor on hover */
            }
        </style>"""


def visualize(model: Scene | Scenario, cps: list = None):
    """
    Creates an HTML visualization of the given scene or scenario. Starts a web server at localhost:8000 (blocking).
    If port 8000 is used, it uses the first free port number after 8000.
    :param model: The scenario to visualize.
    :param cps: A list of criticality phenomena which optionally to visualize as well.
    :return: The path to the directory in which to find the created HTML visualization.
    """
    pl_html = []
    scenario_inst = None
    if cps is None:
        cps = []
    if isinstance(model, Scene):
        model = Scenario(scenes=[model])

    # Random numbers for coloring - just be consistent here
    rand = random.Random(1)

    # Assemble scenario title
    title = str(model)
    scenario_info = "(" + str(len(model)) + " Scenes)"

    # Create folder to serve from, copy CSS/JS files there
    tmp_dir = utils.make_temporary_subfolder("visualization")
    file_location = os.path.dirname(os.path.realpath(__file__)) + "/files"
    bootstrap_css = "css/bootstrap.min.css"
    bootstrap_js = "js/bootstrap.bundle.min.js"
    jquery_js = "js/jquery-3.6.0.min.js"
    d3_js = "js/d3.v5.js"
    mpld3_js = "js/mpld3.v0.5.7.js"
    ico = "ico/favicon.ico"
    bootstrap_css_pkg = file_location + "/" + bootstrap_css
    bootstrap_js_pkg = file_location + "/" + bootstrap_js
    jquery_js_pkg = file_location + "/" + jquery_js
    d3_js_pkg = file_location + "/" + d3_js
    mpld3_js_pkg = file_location + "/" + mpld3_js
    ico_pkg = file_location + "/" + ico
    os.mkdir(tmp_dir + "/css")
    os.mkdir(tmp_dir + "/js")
    shutil.copy(bootstrap_css_pkg, tmp_dir + "/css")
    shutil.copy(bootstrap_js_pkg, tmp_dir + "/js")
    shutil.copy(jquery_js_pkg, tmp_dir + "/js")
    shutil.copy(d3_js_pkg, tmp_dir + "/js")
    shutil.copy(mpld3_js_pkg, tmp_dir + "/js")
    shutil.copy(ico_pkg, tmp_dir)

    # Main HTML code for index.html
    html_body = """<!DOCTYPE html>
<html>
    <head>
        <link href=\"""" + str(bootstrap_css) + """\" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">
        <script src=\"""" + str(bootstrap_js) + """\" integrity="sha384-ka7Sk0Gln4gmtz2MlQnikT1wXgYsOg+OMhuP+IlRH9sENBO0LRn5q+8nbTov4+1p" crossorigin="anonymous"></script>
        <script src=\"""" + str(jquery_js) + """\"></script>
        <meta charset="utf-8">""" + scenario_css + """
        <title>""" + title + """</title>
    </head>
    <body>
        <div class=\"d-flex flex-row justify-content-center\"><div class=\"mt-3 py-1 px-6 alert alert-info\" style=\"display: inline-block\" role=\"alert\"><center><h5>""" + title + """ """ + scenario_info + """</h5></center></div></div>
        <div class=\"row\">
            <div class=\"col-md-1 text-center\">
                <button id=\"playButton\" type=\"button\" class=\"btn btn-primary center\">Play</button>
            </div>
            <div class=\"col-md-11\">
                <input type=\"range\" min=\"1\" max=\"""" + str(len(model)) + """\" value="1" class="slider" id="scenarioSlider">
            </div>
        </div>
        <script>
            function sleep(ms) {
              return new Promise(resolve => setTimeout(resolve, ms));
            }
        
            async function playScenario() {
              scenario_paused = false;
              $("#playButton").html("Pause");
              $("#playButton").unbind("click").bind("click", function() { scenario_paused = true; });
            
              scenes = $("#scenarioSlider").attr("max");
              var slider = document.getElementById("scenarioSlider");
              for (let i = last_set; i <= scenes; i++) {
                if (scenario_paused) {
                  break;
                }
                var t_prev = $("#plt" + last_set).find(".scene-plot").contents().find("#sceneTime").text();
                var t_now = $("#plt" + i).find(".scene-plot").contents().find("#sceneTime").text();
                var t_diff = t_now - t_prev;
                await sleep(t_diff * 1000);
                if (scenario_paused) {
                  break;
                }
                var last_output = document.getElementById("plt" + last_set);
                last_output.style.display = 'none';
                var output = document.getElementById("plt" + i);
                output.style.display = 'block';
                slider.value = i;
                last_set = i;
              }
              
              $("#playButton").html("Play");
              $("#playButton").unbind("click").bind("click", playScenario);
            }
            
            var slider = document.getElementById("scenarioSlider");
            var last_set = 1;
            var show_all_cps = true;
            var scenario_paused = true;
            
            $("#playButton").click(playScenario);
            
            slider.oninput = function() {
              var output = document.getElementById("plt" + this.value);
              var last_output = document.getElementById("plt" + last_set);
              last_output.style.display = 'none';
              output.style.display = 'block';
              last_set = this.value
            }
            
            function toggle_cps_all_iframes() {
                show_all_cps = !show_all_cps
                $(".cp-all-button").each(function(i) {
                  if (show_all_cps) {
                      this.parentElement.classList.add("active")
                      this.checked = true
                  } else {
                      this.parentElement.classList.remove("active")
                      this.checked = false
                  }
                })
                $(".cp-button").each(function(i) {
                  if (show_all_cps) {
                      this.parentElement.classList.add("active")
                      this.checked = true
                  } else {
                      this.parentElement.classList.remove("active")
                      this.checked = false
                  }
                })
                $(".scene-plot").each(function(i) {
                  this.contentWindow.toggle_cps(show_all_cps)
                })
            }
            function toggle_cp_class(ele, cp_cls_id) {
                // 0. disable automatically checked checkbox (will be added again at step 3)
                ele.checked = !ele.checked
                // 1. find active scene plot
                active_scene = $(".scene-plot-container").filter(function(i) {
                  return this.style.display !== "none"
                })[0]
                // 2. get CP pred. str for given cp_cls_id
                cp_pred = active_scene.getElementsByClassName("scene-plot")[0].contentWindow.cp_predicates[cp_cls_id]
                // 3. Toggle all buttons for this CP pred
                $("label > span:contains(" + cp_pred + ")").each(function(i) {
                  this.parentElement.classList.toggle("active")
                  this.parentElement.querySelector(".cp-button").checked = !this.parentElement.querySelector(".cp-button").checked
                })
                // 4. check if (and where) CP pred. str is present in cp_predicates, pass the resulting index
                $(".scene-plot").each(function(k) {
                  cp_cls_id_scene = -1
                  for (var i = 0; i < this.contentWindow.cp_predicates.length; i++) {
                    if (cp_pred === this.contentWindow.cp_predicates[i]) {
                        cp_cls_id_scene = i
                    }
                  }
                  if (cp_cls_id_scene >= 0) {
                    this.contentWindow.toggle_cp_class(cp_cls_id_scene, ele.checked)
                  }
                })
            }
        </script>
    """
    pl_html.append(html_body)
    iframes = []

    def get_color(rand):
        # Fetches a different color each time, but ensures that it has a readable contrast.
        _LUMA_LIMIT = 170
        color = 0
        luma = _LUMA_LIMIT
        while luma >= _LUMA_LIMIT:
            color = rand.randrange(0, 0xFFFFFF, 0xF)
            luma = 0.2126 * ((color >> 16) & 0xff) + 0.7152 * ((color >> 8) & 0xff) + 0.0722 * ((color >> 0) & 0xff)
        return "#" + "%06x" % color

    # Create HTML for each scene
    logger.info("Plotting " + str(len(model)) + (" scenes" if len(model) > 1 else " scene"))
    for i, scene in tqdm.tqdm(enumerate(model), total=len(model)):
        scene_cps = [cp for cp in cps if cp.is_representable_in_scene(scene)]
        cp_colors = list(map(get_color(rand), range(len([x for c in scene_cps for x in c.subjects]))))
        cp_color = 0
        no_geo_entities = []
        width = 24.5
        height = 10
        try:
            primary_screens = list(filter(lambda x: x.is_primary, screeninfo.get_monitors()))
            if len(primary_screens) > 0:
                width = (primary_screens[0].width_mm / 25.4) * 0.73
                height = (primary_screens[0].height_mm / 25.4) * 0.73
        except screeninfo.common.ScreenInfoError:
            logger.info("No screens found, using default plot size of " + str(width) + " in x " + str(height) + " in")
        fig = plt.figure(figsize=(width, height))
        plt.axis("equal")
        if _CREATE_SVG_FILES:
            plt.axis('off')
        entity_labels = []
        entity_relations = []
        relations_per_cp_class = dict()
        cps_relations = []
        cps_for_tooltips = []
        centroids_x = []
        centroids_y = []
        plotted_labels = []
        entity_points = dict()
        inds = list(scene.individuals())
        for entity in sorted(inds, key=lambda x: str(x.is_a[0]) if len(x.is_a) > 0 else str(x)):
            if len(entity.hasGeometry) > 0:
                for geo in [g for g in entity.hasGeometry if len(g.asWKT) > 0]:
                    shape = wkt.loads(geo.asWKT[0])
                    entity_cp_relations = []
                    points = None
                    if hasattr(shape, "exterior"):
                        points = shape.exterior.xy
                    try:
                        hasattr(shape, "coords")
                        points = shape.coords.xy
                    except NotImplementedError:
                        pass
                    try:
                        x = shape.centroid.x
                        y = shape.centroid.y
                    except IndexError:
                        points = None  # if we can not generate a centroid - do not print the object.
                    if points:
                        if (np.isclose(centroids_x, x) & np.isclose(centroids_y, y)).any():
                            x = shape.centroid.x + 0.0
                            y = shape.centroid.y + 0.8
                            if not _CREATE_SVG_FILES:
                                plt.plot((shape.centroid.x, x), (shape.centroid.y, y), "k-")
                        entity_points[entity] = (x, y)
                        centroids_x.append(x)
                        centroids_y.append(y)
                        color = None
                        if len([x for x in entity.INDIRECT_is_a if "l1" in str(x) or "l2" in str(x)]):
                            color = "black"
                        elif len([x for x in entity.INDIRECT_is_a if "Bicycle" in str(x)]):
                            color = "darkblue"
                        elif len([x for x in entity.INDIRECT_is_a if "Passenger_Car" in str(x)]):
                            color = "cornflowerblue"
                        elif len([x for x in entity.INDIRECT_is_a if "Pedestrian" in str(x)]):
                            color = "firebrick"
                        elif len([x for x in entity.INDIRECT_is_a if "Parking_Vehicle" in str(x)]):
                            color = "darkgoldenrod"
                        plt.plot(*points, alpha=.6, color=color)
                        if len([x for x in entity.INDIRECT_is_a if "Bikeway_Lane" in str(x)]):
                            plt.fill(*points, alpha=.25, color="red")
                        elif len([x for x in entity.INDIRECT_is_a if "Pedestrian_Crossing" in str(x)]):
                            bbox_x, bbox_y = shape.minimum_rotated_rectangle.exterior.coords.xy
                            bbox_x = bbox_x[:-1]
                            bbox_y = bbox_y[:-1]
                            min_bbox_y_ind = min(range(len(bbox_y)), key=bbox_y.__getitem__)
                            start_1 = (bbox_x[min_bbox_y_ind], bbox_y[min_bbox_y_ind])

                            len_side_1 = geometry.Point(bbox_x[min_bbox_y_ind], bbox_y[min_bbox_y_ind]).distance(
                                geometry.Point(bbox_x[(min_bbox_y_ind + 1) % len(bbox_y)],
                                               bbox_y[(min_bbox_y_ind + 1) % len(bbox_y)]))
                            len_side_2 = geometry.Point(bbox_x[min_bbox_y_ind], bbox_y[min_bbox_y_ind]).distance(
                                geometry.Point(bbox_x[(min_bbox_y_ind - 1) % len(bbox_y)],
                                               bbox_y[(min_bbox_y_ind - 1) % len(bbox_y)]))
                            if len_side_1 < len_side_2:
                                ped_length = len_side_2
                                next_p_index = (min_bbox_y_ind + 1) % len(bbox_y)
                            else:
                                ped_length = len_side_1
                                next_p_index = (min_bbox_y_ind - 1) % len(bbox_y)
                            start_2 = (bbox_x[next_p_index], bbox_y[next_p_index])
                            if bbox_x[next_p_index] - bbox_x[min_bbox_y_ind] != 0:
                                m = ((bbox_y[next_p_index] - bbox_y[min_bbox_y_ind]) /
                                     (bbox_x[next_p_index] - bbox_x[min_bbox_y_ind]))
                            else:
                                m = 0
                            if m != 0:
                                c = math.copysign(1, m) / math.sqrt(1+m**2)
                                s = -m / math.sqrt(1+m**2)
                            else:
                                c = 1
                                s = 0
                            strip_width = 0.4
                            strip_x_offset = strip_width * s
                            strip_y_offset = strip_width * c
                            strip_number = 0
                            for _ in range(math.floor(ped_length / strip_width)):
                                if strip_number % 2 == 0:
                                    strip_xs = [start_1[0] + strip_x_offset * strip_number, start_1[0] +
                                                strip_x_offset * (strip_number + 1), start_2[0] + strip_x_offset *
                                                (strip_number + 1), start_2[0] + strip_x_offset * strip_number]
                                    strip_ys = [start_1[1] + strip_y_offset * strip_number, start_1[1] +
                                                strip_y_offset * (strip_number + 1), start_2[1] + strip_y_offset *
                                                (strip_number + 1), start_2[1] + strip_y_offset * strip_number]
                                    plt.fill(strip_xs, strip_ys, color="black", alpha=.4)
                                strip_number += 1
                        elif len([x for x in entity.INDIRECT_is_a if "Dynamical_Object" in str(x)]) > 0:
                            plt.fill(*points, alpha=.5, color=color)
                            if entity.has_yaw is not None:
                                x_dir = (0.9 * math.cos(math.radians(entity.has_yaw)))
                                y_dir = (0.9 * math.sin(math.radians(entity.has_yaw)))
                                plt.arrow(shape.centroid.x, shape.centroid.y, dx=x_dir, dy=y_dir, shape="full",
                                          length_includes_head=True, color="gray", alpha=0.6, head_width=1)
                        entity_labels.append(_describe_entity(entity))
                        # Plot CPs
                        entity_scene_cps = list(filter(lambda scp: entity in scp.subjects, scene_cps))
                        if len(entity_scene_cps) > 0:
                            plt.plot(x, y, "o", color="r", mec="k", markersize=3, alpha=1)
                            ent_color = "red"
                        else:
                            ent_color = "black"
                        if len({"l4_core.L4_Entity", "l4_core.Traffic_Object", "l4_core.Traffic_Subject"}.intersection(
                                [str(c) for c in entity.INDIRECT_is_a])) > 0 and not _CREATE_SVG_FILES:
                            plt.annotate(entity.name, (x+0.2, y+0.2), color=ent_color)
                        already_drawn_cps = []
                        # init dict
                        for cp in entity_scene_cps:
                            if cp.predicate not in relations_per_cp_class.keys():
                                relations_per_cp_class[cp.predicate] = []
                        for cp in entity_scene_cps:
                            if cp not in already_drawn_cps:
                                same_line_cps = [x for x in entity_scene_cps if
                                                 [y for z in x.objects.values() for y in z] ==
                                                 [y for z in cp.objects.values() for y in z]]
                                labels = [(x.predicate.split("(")[0],
                                           (x.predicate.split("(")[1].replace(")", ""), str(x)))
                                          for x in same_line_cps]
                                already_drawn_cps += same_line_cps
                                subj_x = x
                                subj_y = y
                                for objs in cp.objects.values():
                                    for obj in objs:
                                        if len(obj.hasGeometry) > 0:
                                            if obj in entity_points.keys():
                                                obj_x = entity_points[obj][0]
                                                obj_y = entity_points[obj][1]
                                            else:
                                                geom_o = wkt.loads(obj.hasGeometry[0].asWKT[0])
                                                obj_x = geom_o.centroid.x
                                                obj_y = geom_o.centroid.y
                                            m = (obj_y - subj_y) / (obj_x - subj_x)
                                            b = subj_y - m * subj_x
                                            head_width = 0.2
                                            head_length = 1.5 * head_width
                                            arrow = plt.arrow(subj_x, subj_y, dx=(obj_x - subj_x), dy=(obj_y - subj_y),
                                                              color=cp_colors[cp_color], shape="full",
                                                              length_includes_head=True, head_width=head_width,
                                                              head_length=head_length)
                                            if len(labels[0]) > 1:
                                                label_row = " ".join([label[0] for label in labels])
                                            else:
                                                label_row = labels[0]
                                            x_offset = (len(label_row) * 0.055) / 2 - 0.055
                                            if subj_x > obj_x:
                                                label_x = obj_x + abs(subj_x - obj_x) / 2 - x_offset
                                            else:
                                                label_x = obj_x - abs(subj_x - obj_x) / 2 - x_offset
                                            a = math.degrees(math.atan(m))
                                            for l_i, label in enumerate(labels):
                                                label_string = label[0].replace("CP_", "")
                                                label_len = (len(label_string) * 0.09 + 0.1)
                                                label_x_offset = abs(math.cos(math.atan(m)) * label_len)
                                                while True:
                                                    # Finds a free space to plot label
                                                    label_y = m * label_x + b + 0.05
                                                    label_x_1 = label_x - label_x_offset / 2 + 0.05
                                                    label_y_1 = m * label_x_1 + b
                                                    label_x_2 = label_x + label_x_offset / 2 + 0.05
                                                    label_y_2 = m * label_x_2 + b
                                                    label_line1 = geometry.LineString([(label_x_1, label_y_1),
                                                                                        (label_x_2, label_y_2)])
                                                    new_bb = label_line1.buffer(0.1, cap_style=2)
                                                    new_bb_rect = list(zip(*new_bb.exterior.xy))[:-1]
                                                    if not _AVOID_LABEL_COLLISIONS or not \
                                                            _has_collision_with_bbs(plotted_labels, new_bb_rect):
                                                        break
                                                    label_x += label_x_offset / 10
                                                annot = plt.annotate(label_string,
                                                                     (label_x, label_y), color=cp_colors[cp_color],
                                                                     rotation=a, fontsize=2, rotation_mode="anchor")
                                                entity_cp_relations.append(annot)
                                                cps_relations.append(annot)
                                                relations_per_cp_class[same_line_cps[l_i].predicate] += [annot, arrow]
                                                cps_for_tooltips.append(same_line_cps[l_i])
                                                plotted_labels.append(new_bb_rect)
                                                label_x += label_x_offset
                                            subj_x = obj_x
                                            subj_y = obj_y
                                            entity_cp_relations += [arrow]
                                cp_color = (cp_color + 1) % len(cp_colors)
                        entity_relations.append(entity_cp_relations)
            elif len(set([str(y) for y in entity.INDIRECT_is_a]).intersection(_NO_PRINTING_CLASSES)) == 0:
                no_geo_entities.append(_describe_entity(entity))
        if not _CREATE_SVG_FILES:
            pl2 = plt.plot(centroids_x, centroids_y, "o", color="b", mec="k", markersize=6, mew=1, alpha=.2)
            tooltip_individuals = ToolTipAndClickInfo(pl2[0], labels=entity_labels, targets=entity_relations,
                                                      targets_per_cp=relations_per_cp_class)
            mpld3.plugins.connect(fig, tooltip_individuals)
        fig.tight_layout()
        if _CREATE_SVG_FILES:
            plt.savefig(tmp_dir + "/plot_" + str(i + 1) + ".svg", format="svg")
        for h, cp_text in enumerate(cps_relations):
            tooltip_cp = CPTooltip(cp_text, cps_for_tooltips[h])
            mpld3.plugins.connect(fig, tooltip_cp)
        html = "\n\t\t<div class=\"container-fluid scene-plot-container\" id=\"plt" + str(i + 1) + "\" style =\""
        if i != 0:
            html += "display: none;"
        html += "\">"
        html += """
            <div class="row">
                <div class="col-md-1">
                    """
        cp_count_total = len([x for x in cps if (isinstance(x.traffic_model, list) and scene in x.traffic_model) or
                              x.traffic_model == scenario_inst])
        html += """<div style="margin-top: 45px;">
                        <label class="btn btn-primary active" style="margin-bottom: 10px; width: %s">
                            <input type="checkbox" class="cp-all-button" id="cp-all-button-%s" autocomplete="off" onclick="toggle_cps_all_iframes();" checked>
                            <span>Show all criticality phenomena (%s)</span>
                        </label>""" % ("100%", str(i), str(cp_count_total))
        for l, pred in enumerate(sorted(relations_per_cp_class.keys(), key=_natural_sort_key)):
            cp_count = len([x for x in cps if x.predicate == pred and ((isinstance(x.traffic_model, list) and
                            scene in x.traffic_model) or x.traffic_model == scenario_inst)])
            html += """
                        <br />
                        <label class="btn btn-secondary active" style="margin-bottom: 5px; width: %s">
                            <input type="checkbox" class="cp-button" id="cp-button-%s-%s" autocomplete="off" onclick="toggle_cp_class(this, %s);" checked>
                            <span>%s (%s)</span>
                        </label>""" % ("100%", str(i), str(l), str(l), pred, str(cp_count))
        html += """
                    </div>
                </div>
                <div class="col-md-11">
                    """
        html += "<div class=\"embed-responsive embed-responsive-16by9\">\n"
        html += "\t\t\t\t\t\t<iframe class=\"scene-plot\" src=\"scene" + str(i + 1) + ".html\" class=\"embed-responsive-item\" style=\"width: 100%; height: " + str(height*1.27) + "in\" allowfullscreen></iframe>\n\t\t\t\t\t</div>\n"
        iframe_html = """<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <meta HTTP-EQUIV="Access-Control-Allow-Origin" CONTENT="localhost">
        <link href=\"""" + str(bootstrap_css) + """\" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">
        <script src=\"""" + str(bootstrap_js) + """\" integrity="sha384-ka7Sk0Gln4gmtz2MlQnikT1wXgYsOg+OMhuP+IlRH9sENBO0LRn5q+8nbTov4+1p" crossorigin="anonymous"></script>
        <script src=\"""" + str(jquery_js) + """\"></script>
    </head>
    <body>"""
        iframe_html += scene_css
        iframe_html += """
        <div class="d-flex flex-row justify-content-center">
            <div class="btn-group btn-group-toggle" data-bs-toggle="buttons">
                <label class="btn btn-secondary active">
                    <input type="checkbox" id="tooltip_button" checked autocomplete="off" onclick="toggle_tooltips(this);"> Show tooltip with information of individuals
                </label>
                <label class="btn btn-secondary active">
                    <input type="checkbox" id="descr_button" checked autocomplete="off" onclick="toggle_all_ind_relations(this);"> Show full individual relations in tooltip
                </label>
            </div>
        </div>
        <script>
            var show_tooltips = true
            var show_long_ind = true
            cps = []
            cp_targets = []
            cp_targets_per_class = []
            function toggle_tooltips(ele) {
                ele.parentElement.classList.toggle("active")
                show_tooltips = !show_tooltips
            }
            function toggle_all_ind_relations(ele) {
                ele.parentElement.classList.toggle("active")
                show_long_ind = !show_long_ind
            }
            function toggle_cp_targets(targets, state) {
                for (let j = 0; j < targets.length; j++) {
                    var x = mpld3.get_element(targets[j])
                    if (x) {
                        if ("path" in x) {
                            tog = x.path
                        } else if ("obj" in x) {
                            tog = x.obj
                        }
                        for (var k = 0; k < tog._groups.length; k++) {
                            for (var l = 0; l < tog._groups[k].length; l++){
                                if (state) {
                                    tog._groups[k][l].style.display = "block"
                                } else {
                                    tog._groups[k][l].style.display = "none"
                                }
                            }
                        }
                    }
                }
            }
            function toggle_cps(state) {
                for (let i = 0; i < cp_targets.length; i++) {
                    toggle_cp_targets(cp_targets[i], state)
                }
            }
            function toggle_cp_class(cp_class, state) {
                targets = cp_targets_per_class[cp_class]
                toggle_cp_targets(targets, state)
            }
        </script>
        <div class="card m-2">
            <div class="card-title d-flex flex-row justify-content-center m-1">
                <h5>"""
        time = "<span id=\"sceneTime\">%.3f</span> / %.3f" % (scene._timestamp, model._max_time)
        iframe_html += "Scene " + time + "<br />"
        iframe_html += """
                </h5>
            </div>
            <div class="card-body m-0 p-0 d-flex justify-content-center">
        """
        scene_html = mpld3.fig_to_html(fig, d3_url=d3_js, mpld3_url=mpld3_js)
        plt.close(fig)
        iframe_html += ''.join("\t\t"+line+"\n" for line in scene_html.splitlines())
        iframe_html += """
            </div>
        </div>"""
        if len(no_geo_entities) > 0:
            iframe_html += """
        <div class="d-flex flex-row justify-content-center">
            <a class="btn btn-primary" data-bs-toggle="collapse" href="#noGeoCollapse" role="button" aria-expanded="false" aria-controls="noGeoCollapse">
                Show scene individuals with no geometric representation (%s)
            </a>
        </div>
        <div class="container-fluid collapse" id="noGeoCollapse">
            <div class="card card-body m-2">""" % str(len(no_geo_entities))
            iframe_html += "".join(no_geo_entities)
            iframe_html += """
            </div>
        </div>"""
        iframe_html += "\t</body>\n</html>"
        iframes.append(iframe_html)
        html += "\t\t\t\t</div>\n\t\t\t</div>\n\t\t</div>"
        pl_html.append(html)

    # Assemble main HTML
    pl_html.append("\n\t</body>\n</html>")
    # Write main HTML to index.html
    index_path = tmp_dir + "/index.html"
    with open(index_path, "w") as file:
        for html in pl_html:
            file.write(html)

    # Write each scene HTML to a single file
    for i, iframe in enumerate(iframes):
        frame_path = tmp_dir + "/scene" + str(i + 1) + ".html"
        with open(frame_path, "w") as file:
            for html in iframe:
                file.write(html)

    logger.info("Saved visualization files to " + str(tmp_dir))

    # Starts webserver
    os.chdir(tmp_dir)
    not_running = True
    port = 8000
    while not_running and port < 65536:
        try:
            threading.Thread(target=HTTPServer(("", port), VisualizerHTTPHandler).serve_forever).start()
            not_running = False
        except OSError:
            port += 1
    if not not_running:
        logger.info("Visualization is available at http://localhost:" + str(port))
        webbrowser.open("http://localhost:" + str(port))
    else:
        logger.warning("Unable to create local web server")
    return tmp_dir


def _describe_entity(entity):
    """
    Describes the given traffic entity as an HTML list.
    :param entity: An object of an owlready2 class.
    :return: The HTML-representation of entity.
    """
    cls = utils.get_most_specific_classes([entity])
    label = "<table class=\"m-2\"><thead><tr><th>Individual</th><th>" + str(entity)
    if len(cls) > 0 and len(cls[0][1]) > 0:
        label += " (" + ", ".join(cls[0][1]) + ")"
    label += "</th></tr></thead><tbody><tr><td>is_a</td><td>"
    label += ", ".join([str(x) for x in entity.is_a])
    label += "</td></tr>"
    for prop in sorted(entity.get_properties(), key=lambda x: str(x)):
        if str(prop.python_name) not in _NO_PRINTING_PROPERTIES:
            label += "<tr>"
            label += "<td>"
            label += str(prop.python_name)
            label += "</td>"
            label += "<td>"
            label += ", ".join([str(x) for x in prop[entity][:_MAX_PROPS_DISPLAY]])
            if len(prop[entity]) > _MAX_PROPS_DISPLAY:
                label += "<text class=\"extended_ind_props\">"
                label += ", ".join([str(x) for x in prop[entity][_MAX_PROPS_DISPLAY:]]) + "</text>"
                label += "<text class=\"extended_ind_props_dots\" style=\"display: none;\">...</text>"
            label += "</td>"
            label += "</tr>"
    label += "</tbody></table>"
    return label


def _describe_cp(cp):
    label = "<table class=\"m-2\"><thead><tr><th>Criticality Phenomenon</th><th>" + \
            str(cp.predicate).split("(")[1].replace(")", "")
    label += "</th></tr></thead><tbody><tr><td>Start time</td><td>"
    time = cp.at_time()
    if isinstance(time, tuple):
        label += str(time[0])
    else:
        label += str(time)
    label += "</td></tr><tr><td>End time</td><td>"
    if isinstance(time, tuple):
        label += str(time[1])
    else:
        label += str(time)
    label += "</td></tr><tr><td>Subject(s)</td><td>"
    if len(cp.subjects) > 0:
        subj_and_classes = utils.get_most_specific_classes(cp.subjects)
        label += "<br />".join([str(x[0]) + " (" + ", ".join(x[1]) + ")" for x in subj_and_classes])
    label += "</td></tr><tr><td>Predicate</td><td>"
    label += str(cp.predicate)
    label += "</td></tr><tr><td>Object(s)</td><td>"
    if len(cp.objects) > 0:
        for obj_predicate in cp.objects.keys():
            obj_and_classes = utils.get_most_specific_classes(cp.objects[obj_predicate])
            label += obj_predicate + ":<br/>" + "<br />".join([str(x[0]) + " (" + ", ".join(x[1]) + ")" for x in
                                                               obj_and_classes])
            if len(cp.objects.keys()) > 1:
                label += "<br/>"
    label += "</td></tr>"
    label += "</tbody></table>"
    return label


#################
# MPLD3 Plugins #
#################

class ToolTipAndClickInfo(mpld3.plugins.PointHTMLTooltip):
    # Handles:
    # 1. the criticality phenomena toggling when clicking on CP subjects (red circles)
    # 2. the mouse-overs when hovering over subjects
    # 3. the Ctrl+Click new window action when clicking on subjects

    JAVASCRIPT = """
    var scene_css = `""" + scene_css + """`
    mpld3.register_plugin("htmltooltip", HtmlTooltipPlugin);
    HtmlTooltipPlugin.prototype = Object.create(mpld3.Plugin.prototype);
    HtmlTooltipPlugin.prototype.constructor = HtmlTooltipPlugin;
    HtmlTooltipPlugin.prototype.requiredProps = ["id"];
    HtmlTooltipPlugin.prototype.defaultProps = {labels:null,
                                                targets_per_cp:null,
                                                cps:null,
                                                hoffset:0,
                                                voffset:10,
                                                targets:null};
    function HtmlTooltipPlugin(fig, props){
        mpld3.Plugin.call(this, fig, props);
    };

    HtmlTooltipPlugin.prototype.draw = function(){
        var obj = mpld3.get_element(this.props.id)
        var labels = this.props.labels
        cps = obj.elements()
        cp_targets = this.props.targets
        cp_targets_per_class = this.props.targets_per_cp
        cp_predicates = this.props.cps
        var tooltip = d3.select("body").append("div")
            .attr("class", "mpld3-tooltip")
            .style("position", "absolute")
            .style("z-index", "10")
            .style("visibility", "hidden");
        
        function show_cp(d, i) {
            if (!window.event.ctrlKey) {
                for (let j = 0; j < cp_targets[i].length; j++) { 
                    var x = mpld3.get_element(cp_targets[i][j]);
                    if (x) {
                        if ("path" in x) {
                            tog = x.path
                        } else if ("obj" in x) {
                            tog = x.obj
                        }
                        for (var k = 0; k < tog._groups.length; k++){
                            for (var l = 0; l < tog._groups[k].length; l++){
                                if (tog._groups[k][l].style.display === "none"){
                                    tog._groups[k][l].style.display = "block"
                                } else {
                                    tog._groups[k][l].style.display = "none"
                                }
                            }
                        }
                    }
                }
            }
        }

        obj.elements()
            .on("mouseover", function(d, i) {
                if (show_tooltips) {
                    tooltip.html(labels[i]).style("visibility", "visible");
                    var long_descrs = document.getElementsByClassName("extended_ind_props")
                    var dots_descrs = document.getElementsByClassName("extended_ind_props_dots")
                    for (let i = 0; i < long_descrs.length; i++) {
                        if(!show_long_ind) {
                            long_descrs[i].style.display = "none";
                        } else {
                            long_descrs[i].style.display = "inline";
                        }
                    }
                    for (let i = 0; i < dots_descrs.length; i++) {
                        if(!show_long_ind) {
                            dots_descrs[i].style.display = "inline";
                        } else {
                            dots_descrs[i].style.display = "none";
                        }
                    }
                }
            })
            .on("mousemove", function(d, i) {
                tooltip
                .style("top", d3.event.pageY + this.props.voffset + "px")
                .style("left",d3.event.pageX + this.props.hoffset + "px");
            }.bind(this))
            .on("mousedown.callout", show_cp)
            .on("mouseout", function(d, i){
                tooltip.style("visibility", "hidden");
            })
            .on("click", function(d, i) {
                if (window.event.ctrlKey) {
                    var newWindow = window.open();
                    newWindow.document.write(
                        `<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">` + scene_css + tooltip.html(labels[i])._groups[0][0].innerHTML
                    );
                }
            });
    };
    """

    def __init__(self, points, labels=None, targets=None, targets_per_cp=None, hoffset=0, voffset=10, css=None):

        targets_ = []
        for x in targets or []:
            x_ = []
            for y in x:
                x_.append(mpld3.utils.get_id(y))
            targets_.append(x_)
        self.targets_per_cp = []
        self.cps = []
        if targets_per_cp:
            self.cps = sorted(targets_per_cp.keys(), key=_natural_sort_key)
            for cp in self.cps:
                x_ = []
                for y in targets_per_cp[cp]:
                    x_.append(mpld3.utils.get_id(y))
                self.targets_per_cp.append(x_)
        super().__init__(points, labels, targets_, hoffset, voffset, css)
        self.dict_["targets_per_cp"] = self.targets_per_cp
        self.dict_["cps"] = self.cps


class CPTooltip(mpld3.plugins.PluginBase):
    # Handles the Ctrl+Click action on criticality phenomena ID (opens a new tab).

    JAVASCRIPT = """
    var scene_css = `""" + scene_css + """`
    mpld3.register_plugin("cpstooltip", CPTooltip);
    CPTooltip.prototype = Object.create(mpld3.Plugin.prototype);
    CPTooltip.prototype.constructor = CPTooltip;
    CPTooltip.prototype.requiredProps = ["id", "tooltip_html"];
    function CPTooltip(fig, props){
        mpld3.Plugin.call(this, fig, props);
    };

    CPTooltip.prototype.draw = function(){
        var obj = mpld3.get_element(this.props.id);
        var tooltip_html = this.props.tooltip_html;
        var tooltip = d3.select("body").append("div")
            .attr("class", "cp-tooltip")
            .style("position", "absolute")
            .style("z-index", "10")
            .style("visibility", "hidden");
            
        obj.obj._groups[0][0].onmouseover = function(d, i) {
            tooltip.html(tooltip_html).style("visibility", "visible");
        };
        
        obj.obj._groups[0][0].onmousemove = function(d, i) {
            tooltip
                .style("top", d.clientY + 10 + "px")
                .style("left", d.clientX + 0 + "px");
        }.bind(this);
        
        obj.obj._groups[0][0].onclick = function(d, i) {
            if (window.event.ctrlKey) {
                var newWindow = window.open();
                newWindow.document.write(
                    `<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">` + scene_css + tooltip_html
                );
            }
        };
        
        obj.obj._groups[0][0].onmouseout = function(d, i) {
            tooltip.style("visibility", "hidden");
        };
    }
    """

    def __init__(self, text, cp):
        tooltip_html = _describe_cp(cp)
        self.dict_ = {"type": "cpstooltip",
                      "id": mpld3.utils.get_id(text),
                      "tooltip_html": tooltip_html}


def _has_collision_with_bbs(existing_bbs, new_bb):
    """
    Checks if the new rectangle (new_bb) collides with some existing rectangles.
    """
    a_left = min([x[0] for x in new_bb])
    a_right = max([x[0] for x in new_bb])
    a_bottom = min([x[1] for x in new_bb])
    a_top = max([x[1] for x in new_bb])
    for bb in existing_bbs:
        b_left = min([x[0] for x in bb])
        b_right = max([x[0] for x in bb])
        b_bottom = min([x[1] for x in bb])
        b_top = max([x[1] for x in bb])
        if a_left <= b_right and b_left <= a_right and a_top >= b_bottom and b_top >= a_bottom:
            return True
    return False
