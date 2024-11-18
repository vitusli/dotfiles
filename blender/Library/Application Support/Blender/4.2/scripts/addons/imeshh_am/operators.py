import bpy
from . import utils, hdr_nodes
import webbrowser
import sys
import os
import subprocess

class IMESHH_OT_AddFolderPath(bpy.types.Operator):
    bl_idname = "imeshh.add_folder_path"
    bl_label = "Add folder entry"
    bl_description = "Add a row to config iMeshh folder"
    bl_options = {"UNDO", "REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        col = context.preferences.addons["imeshh_am"].preferences.paths
        col.add()
        return {"FINISHED"}

class IMESHH_OT_RemoveFolderPath(bpy.types.Operator):
    bl_idname = "imeshh.remove_folder_path"
    bl_label = "Remove folder entry"
    bl_description = "Remove a row to config iMeshh folder"
    bl_options = {"UNDO", "REGISTER"}
    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        col = context.preferences.addons["imeshh_am"].preferences.paths
        col.remove(self.index)
        return {"FINISHED"}

class IMESHH_OT_ImportObject(bpy.types.Operator):
    bl_idname = "imeshh.import_object"
    bl_label = "Append Object"
    bl_description = 'Appends object to scene'
    bl_options = {'REGISTER', 'UNDO'}
    link : bpy.props.BoolProperty(False)
    
    def store_tool_settings(self, context):
        ts = context.scene.tool_settings
        self.settings = {
            'use_snap' : ts.use_snap,
            'snap_elements' : ts.snap_elements,
            'snap_target' : ts.snap_target,
            'use_snap_align_rotation' : ts.use_snap_align_rotation
            }
    def restore_tool_settings(self, context):
        if hasattr(self, "settings"):
            for attr in self.settings.keys():
                try:
                    setattr(context.scene.tool_settings, attr, self.settings[attr])
                except:
                    continue

    def execute(self, context):
        utils.import_object(context, link=self.link)
        if context.scene.imeshh_am.snap:
            self.store_tool_settings(context)
            context.window_manager.modal_handler_add(self)
            context.scene.tool_settings.use_snap = True
            context.scene.tool_settings.snap_elements = {'FACE'}
            context.scene.tool_settings.snap_target = 'CLOSEST'
            context.scene.tool_settings.use_snap_align_rotation = False
            bpy.ops.transform.translate('INVOKE_DEFAULT')
            return {'RUNNING_MODAL'}
        else:
            return {'FINISHED'}

    
    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC', 'LEFTMOUSE'}:
            self.restore_tool_settings(context)
            return {'FINISHED'}
        return {'RUNNING_MODAL'}        
class IMESHH_OT_ImportMaterial(bpy.types.Operator):
    bl_idname = "imeshh.import_material"
    bl_label = "Import Material"
    bl_description = 'Imports material to scene'
    link : bpy.props.BoolProperty(False)

    def execute(self, context):
        utils.import_material(context, link=self.link)
        return {'FINISHED'}

class IMESHH_OT_ImportHDR(bpy.types.Operator):
    bl_idname = "imeshh.import_hdr"
    bl_label = "Import New HDRI"
    bl_description = "Imports an HDRI into the world material"

    def execute(self, context):
        hdr_nodes.import_hdr_cycles(context)
        
        return {'FINISHED'}

class IMESHH_OT_OpenThumbnail(bpy.types.Operator):
    """Open the thumbnail image"""
    bl_idname = "imeshh.open_thumbnail"
    bl_label = "Thumbnail"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        filepath = utils.get_selected_file(context)
        items = utils.CURR_PREVIEW
        from . import preview_collections
        for item in items:
            if item[0] == filepath:
                icon_id = item[3]
                for (preview_path, preview_image) in preview_collections["main"].items():
                    if icon_id == preview_image.icon_id and preview_path.endswith((".png", ".jpg")):
                        webbrowser.open(preview_path)

        return {'FINISHED'}

class IMESHH_OT_OpenBlend(bpy.types.Operator):
    """Open the .blend file for the asset"""
    bl_idname = "imeshh.open_blend"
    bl_label = ".blend"
    bl_options = {'REGISTER', 'UNDO'}

    def open_blend(self, binary, filepath):
        if sys.platform.startswith("win"):
            base, exe = os.path.split(binary)
            subprocess.Popen(["start", "/d", base, exe, filepath], shell=True)
        else:
            subprocess.Popen([binary, filepath])

    def execute(self, context):
        selected_blend = utils.get_selected_blend(context)
        self.open_blend(bpy.app.binary_path, selected_blend)
        return {'FINISHED'}

