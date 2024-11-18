import bpy
from bpy.props import FloatVectorProperty, StringProperty, IntProperty, BoolProperty, CollectionProperty, EnumProperty, FloatProperty, PointerProperty
from . utils.cursor import set_cursor
from . items import focus_mode_items, obj_type_items, obj_type_items_without_none, edit_mode_items, add_cylinder_side_items, axis_items, add_boolean_method_items, add_boolean_solver_items

class HistoryCursorCollection(bpy.types.PropertyGroup):
    name: StringProperty()
    index: IntProperty()

    mx: FloatVectorProperty(name="Cursor Matrix", subtype="MATRIX", size=(4, 4))

    location: FloatVectorProperty(name="Cursor Location", subtype="TRANSLATION")
    location2d: FloatVectorProperty(name="Cursor Location", subtype="TRANSLATION", size=2)
    gzm_location2d: FloatVectorProperty(name="Gizmo Location, next to the Label", subtype="TRANSLATION", size=2)

    rotation: FloatVectorProperty(name="Cursor Rotation", subtype="MATRIX", size=(3, 3))

class RedoAddObjectCollection(bpy.types.PropertyGroup):
    name: StringProperty()
    index: IntProperty()

    libname: StringProperty()
    blendpath: StringProperty()
    assetname: StringProperty()

    surface: BoolProperty(name="Add Object at Cursor's Surface (Z-Plane)", default=True)
    embed: BoolProperty(name="Add Object embedded in Cursor's Surface (Z-Plane)", default=False)
    embed_depth: FloatProperty(name="Embed Depth", default=0.1, min=0.1, max=0.9)
    apply_scale: BoolProperty(name="Apply Scale", default=True)
    size: FloatProperty(name="Size of Object", default=1)
    sides: IntProperty(name="Cylinder Sides", default=32, min=3)
    is_quad_sphere: BoolProperty(name="is Quad Sphere", default=False)
    is_plane: BoolProperty(name="is Plane", default=False)
    is_subd: BoolProperty(name="is SubD", default=False)
    subdivisions: IntProperty(name="Subdivide", default=3, min=1, max=5)
    is_rounded: BoolProperty(name="is Rounded", default=False)
    bevel_count: IntProperty(name="Bevel Mod Count", default=1, min=1, max=4)
    bevel_segments: IntProperty(name="Bevel Segments", default=0, min=0)
    align_axis: EnumProperty(name="Align with Axis", items=axis_items, default='Z')
    boolean: BoolProperty(name="Boolean", default=False)
    boolean_method: EnumProperty(name="Method", items=add_boolean_method_items, default='DIFFERENCE')
    boolean_solver: EnumProperty(name="Solver", items=add_boolean_solver_items, default='FAST')
    hide_boolean: BoolProperty(name="Hide Boolean", default=False)
    display_type: StringProperty(name="Display Type", default='WIRE')
    is_subset_mirror: BoolProperty(name="is Subset Mirror", default=True)
    original_mesh_max_dimension_factor: StringProperty(name="Original Mesh Max Dimension Factor", default="0")

class ApplyAllBackupCollection(bpy.types.PropertyGroup):
    name: StringProperty(name="Backup Name")
    index: IntProperty()

    collection: PointerProperty(type=bpy.types.Collection)
    active: PointerProperty(type=bpy.types.Object)

class PipeRadiiCollection(bpy.types.PropertyGroup):
    name: StringProperty()
    index: IntProperty()

    co: FloatVectorProperty(name="Radius Coordinate")
    modulate: FloatProperty(name="Modulate Radius", default=0)
    segment_modulate: FloatProperty(name="Modulate Segment", default=0)
    hide: BoolProperty(name="Hide Gizmo", default=False)
    area_pointer: StringProperty()

class CurveSurfaceCollection(bpy.types.PropertyGroup):
    name: StringProperty()
    index: IntProperty()

    co: FloatVectorProperty(name="Curve Point Coordinate")
    bind_co: FloatVectorProperty(name="Bind Coordinate", description="The initial Point Coord, on the subdivided but still uncurved Surface")

    normal: FloatVectorProperty(name="Face Normal")
    binormal: FloatVectorProperty(name="Face Binormal")
    tangent: FloatVectorProperty(name="Face Tangent")

    area_pointer: StringProperty()

class RemoveUnusedBooleansCollection(bpy.types.PropertyGroup):
    name: StringProperty()
    objname: StringProperty()

    index: IntProperty()

    co: FloatVectorProperty(name="Averaged BBox Location", size=3)
    co2d: FloatVectorProperty(name="Averaged BBox Location projected into Screen Space", size=2)

    remove: BoolProperty(name="Remove", default=True)
    is_highlight: BoolProperty(default=False)
    area_pointer: StringProperty()

class PickObjectTreeCollection(bpy.types.PropertyGroup):
    name: StringProperty()
    modname: StringProperty()
    modhostobjname: StringProperty()

    index: IntProperty()

    co: FloatVectorProperty(name="Averaged BBox Location", size=3)
    co2d: FloatVectorProperty(name="Averaged BBox Location projected into Screen Space", size=2)

    select: BoolProperty(name="Select", default=False)
    remove: BoolProperty(name="Remove", default=False)
    is_highlight: BoolProperty(default=False)
    show: BoolProperty(name="Show", default=True)  # Used to disable showing of Hyper Bevels
    avoid_repulsion: BoolProperty(name="Avoid Repulsion", default=False)  # Used to disable gzm repulsion for empty's which are drawin in view3d and hud, and so the two would separate if repulsed
    area_pointer: StringProperty()

    affect_all_visible_only: BoolProperty(name="Affect All Visible (only)", default=False)
    active_object: PointerProperty(type=bpy.types.Object)
    select_finish: BoolProperty(default=False)

class PickHyperBevelsCollection(bpy.types.PropertyGroup):
    name: StringProperty()
    index: IntProperty()

    obj: PointerProperty(type=bpy.types.Object)
    is_highlight: BoolProperty(default=False)
    active: BoolProperty(name="Remove", default=True)
    remove: BoolProperty(name="Remove", default=False)
    area_pointer: StringProperty()

class BendCollection(bpy.types.PropertyGroup):
    name: StringProperty()
    index: IntProperty()

    type: StringProperty(name='Gizmo Type', default="MAIN")
    obj: PointerProperty(type=bpy.types.Object)

    is_highlight: BoolProperty(default=False)
    cmx: FloatVectorProperty(name="Cursor Matrix", subtype='MATRIX', size=(4, 4))

    loc: FloatVectorProperty(name="Cursor Location", size=3)
    loc2d: FloatVectorProperty(name="Cursor Location 2D", size=2)

    rot: FloatVectorProperty(name="Cursor Rotation", subtype='QUATERNION', size=4)

    affect_children: BoolProperty(name="Affect Children", default=False)
    has_children: BoolProperty(name="Has Children", default=False)
    is_kink: BoolProperty(name="Kink instead of Bend", default=False)
    use_kink_edges: BoolProperty(name="Use Kink Edges", default=False)
    contain: BoolProperty(name="Contain", default=False)
    angle: FloatProperty(default=0, min=-360, max=360)
    segments: IntProperty(default=6, min=0)

    offset: FloatProperty()
    z_factor: FloatProperty()

    limit: FloatProperty(default=1)
    limit_distance: FloatProperty()

    mirror_bend: BoolProperty(name="Mirror the Bend", default=False)

    remove_redundant: BoolProperty(name="Remove Redundant Edges", default=True)

    bend: BoolProperty(name="Bend", default=True)
    bisect: BoolProperty(name="Bend", default=True)

    area_pointer: StringProperty()

class HCSceneProperties(bpy.types.PropertyGroup):
    debug: BoolProperty(default=False)
    avoid_update: BoolProperty(default=False)

    sidebar_fold_gizmos: BoolProperty(name="Fold Gizmos", default=True)
    sidebar_fold_geo_gizmo_limits: BoolProperty(name="Fold Geo Gizmo Limits", default=True)
    sidebar_fold_geo_gizmo_scale: BoolProperty(name="Fold Geo Gizmo Scale", default=True)
    sidebar_fold_cursor_history: BoolProperty(name="Fold Cursor History", default=True)
    sidebar_fold_object_history: BoolProperty(name="Fold Object History", default=True)
    sidebar_fold_focus: BoolProperty(name="Fold Focus", default=True)
    sidebar_fold_asset_creation: BoolProperty(name="Fold Asset Creation", default=True)
    sidebar_fold_keymaps: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_object_1: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_object_4: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_object_9: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_object_11: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_object_13: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_object_17: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_object_18: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_object_21: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_object_26: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_object_28: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_edit_mesh_1: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_edit_mesh_4: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_edit_mesh_6: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_edit_mesh_8: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_edit_mesh_10: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_keymaps_edit_mesh_14: BoolProperty(name="Fold Keymaps", default=True)
    sidebar_fold_links: BoolProperty(name="Fold Links", default=True)
    help_popup_fold_links: BoolProperty(name="Fold Help Links", default=True)

    sidebar_show_gizmos: BoolProperty(name="Show Gizmo Settings/Toggles", default=True)
    sidebar_show_cursor_history: BoolProperty(name="Show Cursor History", default=True)
    sidebar_show_object_history: BoolProperty(name="Show Object History", default=True)
    sidebar_show_focus: BoolProperty(name="Show Focus", default=True)
    sidebar_show_asset_creation: BoolProperty(name="Show Asset Creation", default=True)
    sidebar_show_keymaps: BoolProperty(name="Show Keymaps", default=True)
    sidebar_show_links: BoolProperty(name="Show Documentation and Support", default=True)

    historyCOL: CollectionProperty(type=HistoryCursorCollection)
    historyIDX: IntProperty(default=-1)
    def update_draw_history(self, context):
        if context.visible_objects:
            context.visible_objects[0].select_set(context.visible_objects[0].select_get())

    auto_history: BoolProperty(name="Automatically store Cursor whenever it changes", default=False)
    track_history: BoolProperty(name="Track Cursor changes and write them to the history", default=True)
    draw_history: BoolProperty(name="Draw entire Cursor History", default=False, update=update_draw_history)
    draw_history_select: BoolProperty(name="Draw Cursor History Select Buttons in 3D View", default=True, update=update_draw_history)
    draw_history_remove: BoolProperty(name="Draw Cursor History Remove Buttons in 3D View", default=True, update=update_draw_history)

    redoaddobjCOL: CollectionProperty(type=RedoAddObjectCollection)
    redoaddobjIDX: IntProperty()

    def update_use_world(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        if self.use_world:
            loc, rot, _ = context.scene.cursor.matrix.decompose()
            self.local_rotation = rot.to_matrix()

            set_cursor(location=loc)

        else:
            loc, _, _ = context.scene.cursor.matrix.decompose()
            set_cursor(location=loc, rotation=self.local_rotation.to_quaternion())

    local_rotation: FloatVectorProperty(name="Cursor's Local Rotation Matrix", subtype="MATRIX", size=(3, 3))
    use_world: BoolProperty(name="Use World Orientation", description="Temporarily use World Orientation", default=False, update=update_use_world)

    focus_proximity: FloatProperty(name='Focus Proximity', default=1, min=0)
    focus_mode: EnumProperty(name='Focus Mode', items=focus_mode_items, default='SOFT')
    focus_cycle: BoolProperty(name="Focus when Cycling the History", default=True)
    focus_transform: BoolProperty(name="Focus when Transforming the History", default=True)
    focus_cast: BoolProperty(name="Focus when Casting the Cursor", default=True)

    draw_HUD: BoolProperty(name="Draw HyperCursor HUD", default=True)
    draw_cursor_axes: BoolProperty(name="Draw Cursor Axes", default=True)
    draw_pipe_HUD: BoolProperty(name="Draw Pipe HUD", default=False)
    draw_remove_unused_booleans_HUD: BoolProperty(name="Draw Remove Unused Booleans HUD", default=False)

    show_gizmos: BoolProperty(name="Show Hyper Cursor Gizmos", default=True)
    show_object_gizmos: BoolProperty(name="Show Object Gizmos", default=True)
    def force_selection_event(self, context):
        if context.visible_objects:
            context.visible_objects[0].select_set(context.visible_objects[0].select_get())

    show_button_history: BoolProperty(name="Show Cursor History Buttons", default=True, update=force_selection_event)
    show_button_focus: BoolProperty(name="Show Cursor Focus Button", default=True, update=force_selection_event)
    show_button_settings: BoolProperty(name="Show Hyper Cursor Settings Button", default=True, update=force_selection_event)
    show_button_cast: BoolProperty(name="Show Cursor Cast Buttons", default=True, update=force_selection_event)
    show_button_object: BoolProperty(name="Show Hyper Cursor Object Buttons", default=True, update=force_selection_event)
    gizmo_xray: BoolProperty(name="Geometry Gizmo XRay", default=True)

class HCObjectProperties(bpy.types.PropertyGroup):

    ishyper: BoolProperty(description="Object was created with HyperCursor, and whill have Geometry Gizmos", default=False)

    ishyperbevel: BoolProperty(name="is Hyper Bevel", description="Objects marked like this are plane base cutter objects, before they have been bevelled and booleaned", default=False)

    ishyperasset: BoolProperty(name="is Hyper Asset", description="Use HyperCursor to place dropped Assets", default=False)
    assetpath: StringProperty(name="Asset Path")
    assetuuid: StringProperty(name="Asset UUID")

    libname: StringProperty(name="Library Name")
    blendpath: StringProperty(name="Blend Path", description="Relative Path of blend file in Library")
    assetname: StringProperty(name="Asset Name")

    isinset: BoolProperty(name="is Inset", description="An asset intended to be used for booleans", default=False)
    insettype: EnumProperty(name="Inset Boolean Type", items=add_boolean_method_items, default="DIFFERENCE")
    insetsolver: EnumProperty(name="Inset Boolean Solver", items=add_boolean_solver_items, default="FAST")
    autodisband: BoolProperty(name="Automatically Disband", default=False)
    issecondaryboolean: BoolProperty(name="is Secondary Boolean", description="Take the boolean mods on the root object, and bring them over to the new root's parent", default=False)

    dup_hash: StringProperty(description="Hash to find associated duplicate, after running bpy.ops.object.duplicate()")

    def update_objtype(self, context):
        if self.avoid_update:
            self.avoid_update = False
            return

        self.objtype = self.objtype_without_none
        print("INFO: changed objtype to", self.objtype)

        from . utils.ui import force_obj_gizmo_update
        force_obj_gizmo_update(context)

    objtype: EnumProperty(name="Hyper Cursor Object Type", items=obj_type_items, default='NONE')
    objtype_without_none: EnumProperty(name="Hyper Cursor Object Type", items=obj_type_items_without_none, default='CUBE', update=update_objtype)

    geometry_gizmos_show: BoolProperty(name="Show Geometry Gizmos", default=True)
    geometry_gizmos_edit_mode: EnumProperty(name="Geometry Gizmo Edit Mode", items=edit_mode_items, default='EDIT')
    geometry_gizmos_force_update: BoolProperty(name="Force Geometry Gizmo Update", default=False)

    def update_cube_limit(self, context):
        active = context.active_object

        if active.HC.objtype == 'CUBE' and self.geometry_gizmos_edit_mode == 'SCALE':
            if len(active.data.polygons) <= active.HC.geometry_gizmos_show_cube_limit:
                self.geometry_gizmos_edit_mode = 'EDIT'

    def update_cylinder_limit(self, context):
        active = context.active_object

        if active.HC.objtype == 'CYLINDER' and self.geometry_gizmos_edit_mode == 'SCALE':
            if len(active.data.edges) <= active.HC.geometry_gizmos_show_cylinder_limit:
                self.geometry_gizmos_edit_mode = 'EDIT'

    geometry_gizmos_show_limit: IntProperty(name="General Polygon Limit for all geometry gizmos", default=100000)
    geometry_gizmos_show_cube_limit: IntProperty(name="Cube Polygon Limit", description="Cube Polygon Count limit at which Edit Gizmos are still displayed\nIncreasing this Value may impact performance", default=250, min=0, update=update_cube_limit)
    geometry_gizmos_show_cylinder_limit: IntProperty(name="Cylinder Edge Limit", description="Cube Edge Count limit at which Edit Gizmos are still displayed\nIncreasing this Value may impact performance", default=600, min=0, update=update_cylinder_limit)

    def update_geometry_gizmos(self, context):
        if context.active_object and context.active_object.HC.ishyper:
            context.active_object.select_set(True)

    geometry_gizmos_scale: FloatProperty(name="Gizmo Scale", description="Per-Object Gizmo Size", default=1, min=0.0001, update=update_geometry_gizmos)
    geometry_gizmos_edge_thickness: FloatProperty(name="Edge Gizmo Thickness", description="Relative Edge Gizmo Thickness", default=0.7, min=0.1, max=3, update=update_geometry_gizmos)
    geometry_gizmos_face_tween: FloatProperty(name="Face Gizmo Tween", description="Relative Face Gizmo size, either evenly across the mesh based on its dimensions and complexity, or based on face size, or anything inbetween", default=0.7, min=0, max=1, update=update_geometry_gizmos)

    geometry_gizmos_show_previews: BoolProperty(name="Show Geometry Gizmo Previews", default=False)
    geometry_gizmos_preview_force_update: BoolProperty(name="Update the Geometry Gizmo Preview", default=False)

    backupCOL: CollectionProperty(type=ApplyAllBackupCollection)

    avoid_update: BoolProperty()

class HCNodeGroupProperties(bpy.types.PropertyGroup):
    version: StringProperty()
