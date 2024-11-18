import bpy

class LightGroupManagerPreferences(bpy.types.AddonPreferences):
    bl_idname = "LuminarLightGroups"

    def draw(self, context):
        layout = self.layout

        # Start/Stop Automatic Light Group Manager buttons
        row = layout.row()
        if context.scene.LightGroupManager.automatic_lightGroup == False:
            row.operator("object.light_group_manager_start", text="Start Automatic Light Group Manager", icon="PLAY")
        else:
            row.operator("object.light_group_manager_stop", text="Stop Automatic Light Group Manager", icon="PAUSE")

        # Light Group Manager Settings
        row = layout.row()
        col = row.column()
        col.label(text="Light Group Settings:")

        row = layout.row()
        col = row.column()
        col.prop(context.scene.LightGroupManager, "lightgroup_index", text="Index")

        col = row.column()
        col.prop(context.scene.LightGroupManager, "lightgroup_separator", text="Separator")

    

def draw_func(self, context):
    layout = self.layout
    layout.operator("object.light_group_manager_single", text="Set Automatic Light Groups", icon="EVENT_L")