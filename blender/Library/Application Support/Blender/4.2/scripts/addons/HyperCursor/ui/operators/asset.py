import bpy
import os
from ...utils.registration import get_path

class AddHyperCursorAssets(bpy.types.Operator):
    bl_idname = "machin3.add_hyper_cursor_assets_path"
    bl_label = "MACHIN3: Add Hyper Cursor Assets Path"
    bl_description = "Add's the HyperCursor Example Assets path to your Library Collection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("Adding Hyper Cursor Assets Path")

        librariesCOL = context.preferences.filepaths.asset_libraries

        bpy.ops.preferences.asset_library_add()

        lib = librariesCOL[-1]
        lib.name = 'HyperCursor Examples'
        lib.path = os.path.join(get_path(), 'assets')

        if bpy.app.version >= (3, 5, 0):
            lib.import_method = 'APPEND'
        
        return {'FINISHED'}
