bl_info = {
    "name" : "Luminar Light Groups",
    "author" : "ArtTizan3D",
    "description" : "Automatic Light Group managment for Cycle Lights",
    "blender" : (3, 4, 0),
    "version" : (1, 0, 3),
    "category" : "lighting",
}

import bpy
from . import operators
from . import ui

def register():
    bpy.utils.register_class(operators.LightGroupManagerStartOperator)
    bpy.utils.register_class(operators.LightGroupManagerSingleOperator)
    bpy.utils.register_class(operators.LightGroupManagerStopOperator)
    bpy.utils.register_class(operators.LightGroupManager)
    bpy.types.VIEW3D_MT_add.append(ui.draw_func)
    bpy.types.Scene.LightGroupManager = bpy.props.PointerProperty(type=operators.LightGroupManager)
    bpy.utils.register_class(ui.LightGroupManagerPreferences)
   
    
def unregister():
    bpy.utils.unregister_class(operators.LightGroupManagerStartOperator)
    bpy.utils.unregister_class(operators.LightGroupManagerSingleOperator)
    bpy.utils.unregister_class(operators.LightGroupManagerStopOperator)
    bpy.utils.unregister_class(operators.LightGroupManager)
    bpy.types.VIEW3D_MT_add.remove(ui.draw_func)
    del bpy.types.Scene.LightGroupManager
    bpy.utils.unregister_class(ui.LightGroupManagerPreferences)
    



if __name__ == "__main__":
    register()