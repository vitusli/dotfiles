import bpy
from bpy.app.handlers import persistent


from ..preferences import get_prefs
from ..utilities.view_transforms import view_transforms_disable, view_transforms_enable
from ..utilities.viewport import enable_viewport_compositing, disable_viewport_compositing
from ..update_nodes import RR_node_name, RR_node_group_name

@persistent
def pre_render(scene):
    prefs = get_prefs(bpy.context)
    settings = bpy.context.scene.render_raw
    renderer = bpy.context.scene.render.engine
    realtime = renderer in ['BLENDER_WORKBENCH', 'BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE']
    if settings.enable_RR and not realtime and not prefs.raw_while_rendering:
        scene.view_settings.view_transform = view_transforms_disable[scene.render_raw.view_transform]
        disable_viewport_compositing(bpy.context, 'ALL')

@persistent
def pre_composite(scene):
    pass

@persistent
def post_render(scene):
    prefs = get_prefs(bpy.context)
    settings = bpy.context.scene.render_raw
    renderer = bpy.context.scene.render.engine
    realtime = renderer in ['BLENDER_WORKBENCH', 'BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE']
    if settings.enable_RR and not realtime and not prefs.raw_while_rendering:
        if scene.render_raw.view_transform == 'False Color':
            scene.view_settings.view_transform = 'False Color'
        else:
            scene.view_settings.view_transform = 'Raw'
        enable_viewport_compositing(bpy.context, 'SAVED')

def register():
    bpy.app.handlers.render_pre.append(pre_render)
    bpy.app.handlers.composite_pre.append(pre_composite)
    bpy.app.handlers.render_post.append(post_render)

def unregister():
    bpy.app.handlers.render_pre.remove(pre_render)
    bpy.app.handlers.composite_pre.remove(pre_composite)
    bpy.app.handlers.render_post.remove(post_render)

