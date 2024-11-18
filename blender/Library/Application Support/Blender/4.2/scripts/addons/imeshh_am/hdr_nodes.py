import bpy
from . import utils
import os

def import_hdr_cycles(context):
    hdr = utils.get_selected_file(context)

    if not hdr:
        return

    scene = context.scene
    world = scene.world
    world.use_nodes = True
    node_tree = world.node_tree

    path_nodes_blend = os.path.join(os.path.dirname(__file__), 'hdrinodes.blend')
    
    if not 'OUTPUTNODE' in node_tree.nodes:
        node_output = None
        for node in node_tree.nodes:
            if node.bl_idname == 'ShaderNodeOutputWorld':
                node_output = node
        if not node_output:        
            node_output = node_tree.nodes.new("ShaderNodeOutputWorld")
        node_output.name = 'OUTPUTNODE'
    else:
        node_output = node_tree.nodes['OUTPUTNODE']

    if not 'Ground Projection Off/On' in bpy.data.node_groups or not 'HDRI Nodes' in bpy.data.node_groups:
        with bpy.data.libraries.load(path_nodes_blend, link = False) as (data_from, data_to):
            data_to.node_groups = data_from.node_groups

    if not 'HDRI_GROUP' in node_tree.nodes:
        hdri_group = node_tree.nodes.new('ShaderNodeGroup')
        hdri_group.name = 'HDRI_GROUP'
        hdri_group.node_tree = bpy.data.node_groups['HDRI Nodes']
    else:
        hdri_group = node_tree.nodes['HDRI_GROUP']

    if not 'GROUND_PROJECTION' in node_tree.nodes:
        ground_projection = node_tree.nodes.new('ShaderNodeGroup')
        ground_projection.name = 'GROUND_PROJECTION'
        ground_projection.node_tree = bpy.data.node_groups['Ground Projection Off/On']
    else:
        ground_projection = node_tree.nodes['GROUND_PROJECTION']
    
    if not 'ENVTEX' in node_tree.nodes:
        node_env_tex = node_tree.nodes.new("ShaderNodeTexEnvironment")
        node_env_tex.name = 'ENVTEX'
    else:
        node_env_tex = node_tree.nodes['ENVTEX']

    nodes = [
        node_output,
        hdri_group,
        node_env_tex,
        ground_projection,
    ]
    x = 600

    for i, node in enumerate(nodes):
        x -= nodes[i].width
        x -= 80
        node.location.x = x

    node_tree.links.new(ground_projection.outputs["Color"], node_env_tex.inputs["Vector"])
    node_tree.links.new(node_env_tex.outputs["Color"], hdri_group.inputs["HDRI"])
    node_tree.links.new(hdri_group.outputs["Shader"], node_output.inputs["Surface"])

    # Load in the HDR
    hdr_image = bpy.data.images.load(hdr)
    node_env_tex.image = hdr_image

# def import_hdr_corona(context):
#     hdr = utils.get_selected_file(context)


#     if not hdr:
#         return

#     corona = context.scene.world.corona
#     corona.mode = 'latlong'
#     corona.enviro_tex = hdr

# def update_hdri_strength_corona(corona, strength):
#     corona.map_gi.intensity = strength

# def update_hdri_rotation_corona(corona, rotation):
#     corona.latlong_enviro_rotate = rotation