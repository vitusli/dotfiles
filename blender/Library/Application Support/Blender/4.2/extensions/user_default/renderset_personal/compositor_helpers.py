#!/usr/bin/python3
# copyright (c) 2018- polygoniq xyz s.r.o.

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


import bpy
import typing
import logging
import enum
from . import polib

logger = logging.getLogger(f"polygoniq.{__name__}")


RENDER_LAYERS_NODE = "CompositorNodeRLayers"
OUTPUT_FILE_NODE = "CompositorNodeOutputFile"
OUTPUT_FILE_NODE_NAME = "renderset_file_output"


class RenderPassType(enum.Enum):
    CUSTOM = "Custom"
    COMPOSITE = "Composite"
    DEPTH = "Depth"
    NORMAL = "Normal"
    UV = "UV"
    VECTOR = "Vector"
    SHADOW = "Shadow"
    AO = "AO"
    MIST = "Mist"
    EMIT = "Emit"
    ENV = "Env"
    NOISY_IMAGE = "Noisy Image"
    FREESTYLE = "Freestyle"
    INDEX_OB = "IndexOB"
    INDEX_MA = "IndexMA"
    DIFF_DIR = "DiffDir"
    DIFF_IND = "DiffInd"
    DIFF_COL = "DiffCol"
    GLOSS_DIR = "GlossDir"
    GLOSS_IND = "GlossInd"
    GLOSS_COL = "GlossCol"
    TRANS_DIR = "TransDir"
    TRANS_IND = "TransInd"
    TRANS_COL = "TransCol"
    SUBSURFACE_DIR = "SubsurfaceDir"
    SUBSURFACE_IND = "SubsurfaceInd"
    SUBSURFACE_COL = "SubsurfaceCol"
    VOLUME_DIR = "VolumeDir"
    VOLUME_IND = "VolumeInd"

    @classmethod
    def get_render_pass_type(cls, render_pass_value: str) -> typing.Optional["RenderPassType"]:
        try:
            return cls(render_pass_value)
        except ValueError:
            return None


def get_render_layers_node(
    nodes: bpy.types.Nodes,
) -> typing.Optional[bpy.types.CompositorNodeRLayers]:
    render_layers_nodes = list(
        polib.node_utils_bpy.find_nodes_by_bl_idname(nodes, RENDER_LAYERS_NODE)
    )
    return render_layers_nodes[0] if len(render_layers_nodes) >= 1 else None


def ensure_render_layers_node_exists(nodes: bpy.types.Nodes) -> bpy.types.CompositorNodeRLayers:
    render_layers = get_render_layers_node(nodes)
    if render_layers is None:
        render_layers = nodes.new(RENDER_LAYERS_NODE)
    return render_layers


def ensure_file_output_node_exists(nodes: bpy.types.Nodes) -> bpy.types.CompositorNodeOutputFile:
    node = nodes.get(OUTPUT_FILE_NODE_NAME)
    if node is None:
        node = nodes.new(OUTPUT_FILE_NODE)
        node.name = OUTPUT_FILE_NODE_NAME
    return node


def get_scene_render_passes(
    scene: bpy.types.Scene, render_layers_node: bpy.types.CompositorNodeRLayers
) -> typing.List[RenderPassType]:
    render_passes = []
    view_layer = scene.view_layers[render_layers_node.layer]
    if view_layer.use_pass_z:
        render_passes.append(RenderPassType.DEPTH)
    if view_layer.use_pass_normal:
        render_passes.append(RenderPassType.NORMAL)
    if view_layer.use_pass_uv:
        render_passes.append(RenderPassType.UV)
    if view_layer.use_pass_vector:
        render_passes.append(RenderPassType.VECTOR)
    if view_layer.use_pass_shadow:
        render_passes.append(RenderPassType.SHADOW)
    if view_layer.use_pass_ambient_occlusion:
        render_passes.append(RenderPassType.AO)
    if view_layer.use_pass_object_index:
        render_passes.append(RenderPassType.INDEX_OB)
    if view_layer.use_pass_material_index:
        render_passes.append(RenderPassType.INDEX_MA)

    if view_layer.use_pass_mist:
        render_passes.append(RenderPassType.MIST)
    if view_layer.use_pass_emit:
        render_passes.append(RenderPassType.EMIT)
    if view_layer.use_pass_environment:
        render_passes.append(RenderPassType.ENV)

    if view_layer.use_pass_diffuse_direct:
        render_passes.append(RenderPassType.DIFF_DIR)
    if view_layer.use_pass_diffuse_indirect:
        render_passes.append(RenderPassType.DIFF_IND)
    if view_layer.use_pass_diffuse_color:
        render_passes.append(RenderPassType.DIFF_COL)

    if view_layer.use_pass_glossy_direct:
        render_passes.append(RenderPassType.GLOSS_DIR)
    if view_layer.use_pass_glossy_indirect:
        render_passes.append(RenderPassType.GLOSS_IND)
    if view_layer.use_pass_glossy_color:
        render_passes.append(RenderPassType.GLOSS_COL)

    if view_layer.use_pass_transmission_direct:
        render_passes.append(RenderPassType.TRANS_DIR)
    if view_layer.use_pass_transmission_indirect:
        render_passes.append(RenderPassType.TRANS_IND)
    if view_layer.use_pass_transmission_color:
        render_passes.append(RenderPassType.TRANS_COL)

    if view_layer.use_pass_subsurface_direct:
        render_passes.append(RenderPassType.SUBSURFACE_DIR)
    if view_layer.use_pass_subsurface_indirect:
        render_passes.append(RenderPassType.SUBSURFACE_IND)
    if view_layer.use_pass_subsurface_color:
        render_passes.append(RenderPassType.SUBSURFACE_COL)

    if view_layer.cycles.use_pass_volume_direct:
        render_passes.append(RenderPassType.VOLUME_DIR)
    if view_layer.cycles.use_pass_volume_indirect:
        render_passes.append(RenderPassType.VOLUME_IND)

    if view_layer.cycles.denoising_store_passes:
        render_passes.append(RenderPassType.NOISY_IMAGE)

    # Both view_layer.use_freestyle and scene.render.use_freestyle are needed for Blender to
    # compute freestyle pass. And view_layer.freestyle_settings.as_render_pass is a switch
    # whether freestyle will be overlaid in composite image or if it will be rendered as
    # a separate render pass.
    if (
        view_layer.use_freestyle
        and scene.render.use_freestyle
        and view_layer.freestyle_settings.as_render_pass
    ):
        render_passes.append(RenderPassType.FREESTYLE)

    return render_passes


def ensure_render_layers_file_out(scene: bpy.types.Scene, output_folder_path: str) -> None:
    nodes = scene.node_tree.nodes
    links = scene.node_tree.links

    render_layers_node = ensure_render_layers_node_exists(nodes)
    file_output_node = ensure_file_output_node_exists(nodes)
    file_output_node.base_path = output_folder_path
    # The output node only supports single frame formats
    # Let's use PNG for movies because it's the default for the output node
    file_output_node.format.file_format = (
        'PNG' if scene.render.is_movie_format else scene.render.image_settings.file_format
    )
    file_output_nodes = list(polib.node_utils_bpy.find_nodes_by_bl_idname(nodes, OUTPUT_FILE_NODE))

    # TODO: We only support file output and render layers nodes that are directly in the compositor
    # node_tree. Some work has already been done to support nodes inside groups but more work is
    # necessary in the functions that look for links.
    for render_pass in get_scene_render_passes(scene, render_layers_node):
        render_pass_socket_name = render_pass.value
        if not polib.node_utils_bpy.is_node_socket_connected_to(
            links, render_layers_node, render_pass_socket_name, file_output_nodes, None, True
        ):
            output_socket = polib.node_utils_bpy.get_node_output_socket(
                render_layers_node, render_pass_socket_name
            )
            input_socket = polib.node_utils_bpy.get_node_input_socket(
                file_output_node, render_pass_socket_name
            )

            if output_socket is None:
                logger.error(
                    f"Output socket {render_pass_socket_name} couldn't be retrieved! Skipping!"
                )
                return
            if input_socket is None:
                input_socket = file_output_node.file_slots.new(render_pass_socket_name)

            links.new(output_socket, input_socket)
