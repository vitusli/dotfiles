import bpy

light_names = []
prev_light_names = set()

def create_light_groups(scene):
    global light_names
    for obj in scene.objects:
        light_args = obj.name.split(scene.LightGroupManager.lightgroup_separator)
        if len(light_args) >= scene.LightGroupManager.lightgroup_index + 1:
            light_group_name = light_args[scene.LightGroupManager.lightgroup_index]
            if light_group_name not in light_names:
                light_names.append(light_group_name)
                bpy.ops.scene.view_layer_add_lightgroup(name=light_group_name)

    # Checking for World
    if scene.world is not None:
        light_args = scene.world.name.split(scene.LightGroupManager.lightgroup_separator)
        if len(light_args) >= scene.LightGroupManager.lightgroup_index + 1:
            light_group_name = light_args[scene.LightGroupManager.lightgroup_index]
            if light_group_name not in light_names:
                light_names.append(light_group_name)
                bpy.ops.scene.view_layer_add_lightgroup(name=light_group_name)


def assign_light_groups(scene):
    global light_names
    for obj in scene.objects:
        light_args = obj.name.split(scene.LightGroupManager.lightgroup_separator)
        if len(light_args) >= scene.LightGroupManager.lightgroup_index + 1:
            light_group_name = light_args[scene.LightGroupManager.lightgroup_index]
            # Check if the light group exists in the scene, create if it doesn't.
            if light_group_name not in bpy.data.collections:
                bpy.ops.scene.view_layer_add_lightgroup(name=light_group_name)
            if light_group_name in light_names:
                obj.lightgroup = light_group_name

    # Checking for World
    if scene.world is not None:
        light_args = scene.world.name.split(scene.LightGroupManager.lightgroup_separator)
        if len(light_args) >= scene.LightGroupManager.lightgroup_index + 1:
            light_group_name = light_args[scene.LightGroupManager.lightgroup_index]
            if light_group_name not in bpy.data.collections:
                bpy.ops.scene.view_layer_add_lightgroup(name=light_group_name)
            if light_group_name in light_names:
                scene.world.lightgroup = light_group_name



def remove_unused_light_groups_on_name_change(scene):
    global prev_light_names
    # Here we gather the names of all the objects, not just the lights
    current_light_names = {obj.name for obj in scene.objects}
    bpy.ops.scene.view_layer_remove_unused_lightgroups()
    if current_light_names != prev_light_names:
        bpy.ops.scene.view_layer_remove_unused_lightgroups()
        prev_light_names = current_light_names.copy()


class LightGroupManager(bpy.types.PropertyGroup):
    automatic_lightGroup: bpy.props.BoolProperty(
        default=False,
        description="Start or Stop the automatic Light Group Manager",
    )
    lightgroup_index: bpy.props.IntProperty(
        default=1,
        min=0,
        description="the Index number is the slot space in which the add-on will look for the AOV name for each Light (starts at 0)",
    )
    lightgroup_separator: bpy.props.StringProperty(
        default="_",
        description="The separator is the symbol the add-on will use as a index separator between arguments",
    )


class LightGroupManagerStartOperator(bpy.types.Operator):
    bl_idname = "object.light_group_manager_start"
    bl_label = "Start Automatic Light Group Manager"

    _timer = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            if context.scene.LightGroupManager.automatic_lightGroup:
                create_light_groups(context.scene)
                assign_light_groups(context.scene)
                remove_unused_light_groups_on_name_change(context.scene)
        return {'PASS_THROUGH'}

    def execute(self, context):
        context.scene.LightGroupManager.automatic_lightGroup = True
        wm = context.window_manager
        self._timer = wm.event_timer_add(2.0, window=context.window)  # set interval here
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class LightGroupManagerSingleOperator(bpy.types.Operator):
    bl_idname = "object.light_group_manager_single"
    bl_label = "Single Automatic Light Group Manager Distribution"

    def execute(self, context):
        create_light_groups(context.scene)
        assign_light_groups(context.scene)
        remove_unused_light_groups_on_name_change(context.scene)
        return {'FINISHED'}

class LightGroupManagerStopOperator(bpy.types.Operator):
    bl_idname = "object.light_group_manager_stop"
    bl_label = "Stop Automatic Light Group Manager"

    def execute(self, context):
        global light_names
        light_names = []
        context.scene.LightGroupManager.automatic_lightGroup = False
        return {'FINISHED'}
