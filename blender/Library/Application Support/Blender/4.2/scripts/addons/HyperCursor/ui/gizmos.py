import bpy
import bmesh
from bpy_extras.view3d_utils import region_2d_to_vector_3d
from mathutils import Matrix, Vector
from math import radians, sqrt
from .. utils.tools import get_active_tool
from .. utils.gizmo import create_button_gizmo, is_valid_object, offset_button_gizmo
from .. utils.math import get_face_center, get_loc_matrix, create_rotation_matrix_from_vector, get_rot_matrix, get_sca_matrix, get_center_between_verts, get_world_space_normal, tween
from .. utils.mesh import get_bbox
from .. utils.bmesh import ensure_gizmo_layers, ensure_select_layers, ensure_edge_glayer
from .. utils.cursor import set_cursor_2d
from .. utils.workspace import get_assetbrowser_area
from .. utils.object import get_eval_bbox
from .. utils.view import get_view_bbox
from .. utils.registration import get_addon, get_prefs
from .. utils.system import printd
from .. utils.modifier import displace_poll, boolean_poll, hyper_array_poll, solidify_poll
from .. utils.curve import get_curve_as_dict, verify_curve_data
from .. utils.gizmo import is_modal
from .. utils.ui import is_on_screen
from .. shapes import ring, stem
from .. colors import white, yellow, red, blue, light_blue, light_yellow, green, light_green

machin3tools = None
meshmachine = None

force_obj_gizmo_update = False
force_geo_gizmo_update = False
force_pick_hyper_bevels_gizmo_update = False

class Gizmo2DRing(bpy.types.Gizmo):
    bl_idname = "MACHIN3_GT_2d_ring"

    def draw(self, context):
        self.draw_custom_shape(self.shape)

    def draw_select(self, context, select_id):
        self.draw_custom_shape(self.shape, select_id=select_id)

    def setup(self):
        self.draw_options = {}
        self.view_offset = (0, 0)
        self.shape = self.new_custom_shape('TRIS', ring)

class Gizmo3DStem(bpy.types.Gizmo):
    bl_idname = "MACHIN3_GT_3d_stem"

    def draw(self, context):
        self.draw_custom_shape(self.shape)

    def draw_select(self, context, select_id):
        self.draw_custom_shape(self.shape, select_id=select_id)

    def setup(self):
        self.shape = self.new_custom_shape('TRIS', stem)

def get_button_matrix(debug=False):
    button_matrix = {0: {'offset': (95, 0), 'occupied': False},
                     1: {'offset': (115, 0), 'occupied': False},      # center
                     2: {'offset': (135, 0), 'occupied': False},

                     10: {'offset': (90, -25), 'occupied': False},
                     11: {'offset': (110, -25), 'occupied': False},   # one down
                     12: {'offset': (130, -25), 'occupied': False},

                     20: {'offset': (90, 25), 'occupied': False},
                     21: {'offset': (110, 25), 'occupied': False},    # one up
                     22: {'offset': (130, 25), 'occupied': False},

                     30: {'offset': (80, -50), 'occupied': False},
                     31: {'offset': (100, -50), 'occupied': False},   # two down
                     32: {'offset': (120, -50), 'occupied': False},
                     }

    if debug:
        printd(button_matrix, name='empty matrix')

    return button_matrix

button_priority = ['focus', 'settings',
                   'point', 'cast',
                   'add_history', 'remove_history', 'draw_history',
                   'add_cube', 'add_cylinder', 'add_asset']

HUD_offset2d = (80, 50)

def get_HUD_offset2d(context, button_matrix, gizmo_size):

    global HUD_offset2d

    HUD_offset2d = (80, 50)

    for idx in [20, 0, 10, 30]:
        button_row = button_matrix[idx]

        if button_row['occupied'] or button_row['offset'][1] < 0:
            break

        else:
            HUD_offset2d = button_row['offset']

    ui_scale = context.preferences.system.ui_scale

    HUD_offset2d = (Vector(HUD_offset2d) - Vector((6, 6))) * gizmo_size * ui_scale

def get_button_map(context, debug=False):
    hc = context.scene.HC

    gizmo_size = context.preferences.view.gizmo_size / 75

    if debug:
        print("\ngetting button offset")

    button_matrix = get_button_matrix(debug=False)

    button_map = {}

    activated_buttons = []

    for name in button_priority:
        if name == 'focus' and hc.show_button_focus or name == 'settings' and hc.show_button_settings:
            activated_buttons.append(name)

        elif name in ['cast', 'point'] and hc.show_button_cast:
            activated_buttons.append(name)

        elif name in ['add_history', 'remove_history', 'draw_history'] and hc.show_button_history:
            activated_buttons.append(name)

        elif name in ['add_cube', 'add_cylinder', 'add_asset'] and hc.show_button_object:
            activated_buttons.append(name)

    if debug:
        print("\nactivated buttons")

    for name in activated_buttons:
        if debug:
            print("", name)

        for idx, data in button_matrix.items():
            if not data['occupied']:
                data['occupied'] = name

                if name in ['draw_history']:
                    button_map[name] = ((data['offset'][0] + 7) * gizmo_size, data['offset'][1] * gizmo_size)
                else:
                    button_map[name] = [o * gizmo_size for o in data['offset']]

                break

        if name == 'focus' and 'settings' not in activated_buttons or name == 'settings' and 'focus' not in activated_buttons:
            button_matrix[idx + 1]['occupied'] = True
            button_matrix[idx + 2]['occupied'] = True

        elif name in ['settings', 'cast']:
            button_matrix[idx + 1]['occupied'] = True

    for name in button_priority:
        if name not in activated_buttons:
            button_map[name] = (0, 0)

    get_HUD_offset2d(context, button_matrix, gizmo_size)

    if debug:
        printd(button_matrix, name='occupied matrix')
        printd(button_map, name='button map')

    return button_map

class GizmoGroupHyperCursor(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_hyper_cursor"
    bl_label = "Hyper Cursor Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    is_full_array = False

    @classmethod
    def poll(cls, context):
        view = context.space_data

        if view.overlay.show_overlays:
            if get_active_tool(context).idname == 'machin3.tool_hyper_cursor':
                hc = context.scene.HC

                return hc.show_gizmos and hc.draw_HUD

    def setup(self, context):
        self.button_map = get_button_map(context, debug=False)

        self.create_transform_gizmos(context)
        self.create_buttons(context)

    def refresh(self, context):
        if not is_modal(self):
            self.button_map = get_button_map(context, debug=False)

    def draw_prepare(self, context):
        def toggle_scale_visibility(context):
            active = context.active_object

            if context.mode == 'EDIT_MESH':

                if active and active.type == 'MESH' and active.select_get() and active.HC.ishyper:
                    bm = bmesh.from_edit_mesh(active.data)
                    bm.normal_update()
                    bm.verts.ensure_lookup_table()

                    verts = [v for v in bm.verts if v.select]

                    if verts:
                        for gzm in [self.scale_x, self.scale_y, self.scale_z]:
                            gzm.hide = False
                        return

                for gzm in [self.scale_x, self.scale_y, self.scale_z]:
                    gzm.hide = True

            elif context.mode == 'OBJECT':
                if active and active.type == 'MESH' and active.select_get() and active.HC.ishyper and len(active.data.polygons) < active.HC.geometry_gizmos_show_limit:
                    for gzm in [self.scale_x, self.scale_y, self.scale_z]:
                        gzm.hide = False

                else:
                    for gzm in [self.scale_x, self.scale_y, self.scale_z]:
                        gzm.hide = True

        if is_modal(self):

            for gzm in self.gizmos:
                if gzm.is_modal:
                    if gzm.bl_idname == "GIZMO_GT_dial_3d":
                        gzm.line_width = 1

                        if self.is_full_array:
                            gzm.arc_inner_factor = 0.9
                            gzm.draw_options = {'CLIP'}

                        else:
                            gzm.arc_inner_factor = 0.4
                            gzm.draw_options = {'ANGLE_VALUE'}

                else:
                    gzm.hide = True

        else:

            for gzm in self.gizmos:
                gzm.hide = False

                if gzm.bl_idname == "GIZMO_GT_dial_3d":
                    gzm.draw_options = {'CLIP'}
                    gzm.line_width = 2
                    gzm.arc_inner_factor = 0

            set_cursor_2d(context)

            self.drag.matrix_basis = context.scene.cursor.matrix

            context.window_manager.HC_gizmo_scale = self.drag.matrix_world.to_scale()[0]

            self.rot_x.matrix_basis = context.scene.cursor.matrix @ self.get_gizmo_rotation_matrix('X')
            self.rot_y.matrix_basis = context.scene.cursor.matrix @ self.get_gizmo_rotation_matrix('Y')
            self.rot_z.matrix_basis = context.scene.cursor.matrix

            self.move_x.matrix_basis = context.scene.cursor.matrix @ self.get_gizmo_rotation_matrix('X')
            self.move_y.matrix_basis = context.scene.cursor.matrix @ self.get_gizmo_rotation_matrix('Y')
            self.move_z.matrix_basis = context.scene.cursor.matrix

            self.scale_x.matrix_basis = context.scene.cursor.matrix @ self.get_gizmo_rotation_matrix('X')
            self.scale_y.matrix_basis = context.scene.cursor.matrix @ self.get_gizmo_rotation_matrix('Y')
            self.scale_z.matrix_basis = context.scene.cursor.matrix

            toggle_scale_visibility(context)

            hc = context.scene.HC
            offset = self.button_map

            offset_button_gizmo(context, self.add_history, offset['add_history'])
            offset_button_gizmo(context, self.remove_history, offset['remove_history'])
            offset_button_gizmo(context, self.draw_history, offset['draw_history'])

            offset_button_gizmo(context, self.proximity, offset['focus'])

            offset_button_gizmo(context, self.settings, offset['settings'])

            offset_button_gizmo(context, self.cast, offset['cast'])
            offset_button_gizmo(context, self.point, offset['point'])

            self.add_history.hide = not hc.show_button_history
            self.remove_history.hide = self.draw_history.hide = True if not hc.historyCOL or not hc.show_button_history else False

            self.proximity.hide = not hc.show_button_focus
            self.settings.hide = not hc.show_button_settings

            self.cast.hide = self.point.hide = not hc.show_button_cast

            if context.mode == 'OBJECT':

                offset_button_gizmo(context, self.add_cube, offset['add_cube'])
                offset_button_gizmo(context, self.add_cylinder, offset['add_cylinder'])
                offset_button_gizmo(context, self.add_asset, offset['add_asset'])

                self.add_cube.hide = self.add_cylinder.hide = self.add_asset.hide = not hc.show_button_object

                if not self.add_asset.hide:
                    self.add_asset.hide = not get_assetbrowser_area(context)

    def get_gizmo_rotation_matrix(self, axis):
        if axis == 'X':
            return Matrix.Rotation(radians(90), 4, 'Y')

        if axis == 'Y':
            return Matrix.Rotation(radians(-90), 4, 'X')

        elif axis == 'Z':
            return Matrix()

    def create_transform_gizmos(self, context):

        self.drag = self.create_drag_gizmo(context)

        self.rot_x = self.create_rotation_gizmo(context, axis='X')
        self.rot_y = self.create_rotation_gizmo(context, axis='Y')
        self.rot_z = self.create_rotation_gizmo(context, axis='Z')

        self.move_x = self.create_translation_gizmo(context, axis='X')
        self.move_y = self.create_translation_gizmo(context, axis='Y')
        self.move_z = self.create_translation_gizmo(context, axis='Z')

        self.scale_x = self.create_scale_gizmo(context, axis='X')
        self.scale_y = self.create_scale_gizmo(context, axis='Y')
        self.scale_z = self.create_scale_gizmo(context, axis='Z')

    def create_buttons(self, context):
        offset = self.button_map

        self.add_history = create_button_gizmo(self, context, 'machin3.call_hyper_cursor_operator', args={'idname': 'change_cursor_history', 'desc': 'Add current Cursor State to History', 'args': "{'mode': 'ADD'}"}, icon='RADIOBUT_OFF', scale=0.13, offset=offset['add_history'])
        self.remove_history = create_button_gizmo(self, context, 'machin3.call_hyper_cursor_operator', args={'idname': 'change_cursor_history', 'desc': 'Remove current Cursor State from History', 'args': "{'mode': 'REMOVE', 'index': -1}"}, icon='X', scale=0.13, offset=offset['remove_history'])

        self.draw_history = create_button_gizmo(self, context, 'machin3.call_hyper_cursor_operator', args={'idname': 'TOGGLE_HISTORY_DRAWING', 'desc': 'Toggle History Drawing'}, icon='CURSOR', scale=0.1, offset=offset['draw_history'])

        self.proximity = create_button_gizmo(self, context, 'machin3.focus_proximity', args={}, icon='HIDE_OFF', scale=0.13, offset=offset['focus'])
        self.settings = create_button_gizmo(self, context, 'machin3.hyper_cursor_settings', icon='WORDWRAP_ON', scale=0.13, offset=offset['settings'])

        self.cast = create_button_gizmo(self, context, 'machin3.cast_cursor', args={}, icon='PARTICLES', scale=0.11, offset=offset['cast'])
        self.point = create_button_gizmo(self, context, 'machin3.point_cursor', args={'instant': False}, icon='SNAP_NORMAL', scale=0.1, offset=offset['point'])

        if context.mode == 'OBJECT':

            self.add_cube = create_button_gizmo(self, context, 'machin3.add_object_at_cursor', args={'type': 'CUBE', 'is_drop': False}, icon='MESH_CUBE', scale=0.13, offset=offset['add_cube'])
            self.add_cylinder = create_button_gizmo(self, context, 'machin3.add_object_at_cursor', args={'type': 'CYLINDER', 'is_drop': False}, icon='MESH_CYLINDER', scale=0.13, offset=offset['add_cylinder'])
            self.add_asset = create_button_gizmo(self, context, 'machin3.add_object_at_cursor', args={'type': 'ASSET', 'is_drop': False}, icon='MESH_MONKEY', scale=0.13, offset=offset['add_asset'])

    def create_translation_gizmo(self, context, axis='Z', offset=0.5, scale=1.4, length=0, alpha=0.3, alpha_highlight=1, hover=False):
        gzm = self.gizmos.new("GIZMO_GT_arrow_3d")

        op = gzm.target_set_operator("machin3.transform_cursor")
        op.mode = 'TRANSLATE'
        op.axis = axis

        gzm.matrix_basis = context.scene.cursor.matrix @ self.get_gizmo_rotation_matrix(axis)
        gzm.matrix_offset = Matrix.Translation((0, 0, offset))

        gzm.draw_style = 'NORMAL'
        gzm.use_draw_offset_scale = True
        gzm.use_draw_modal = False
        gzm.use_draw_hover = hover

        gzm.length = length
        gzm.scale_basis = scale

        gzm.color = (1, 0.3, 0.3) if axis == 'X' else (0.3, 1, 0.3) if axis == 'Y' else (0.3, 0.3, 1)
        gzm.alpha = alpha
        gzm.color_highlight = (1, 0.5, 0.5) if axis == 'X' else (0.5, 1, 0.5) if axis == 'Y' else (0.5, 0.5, 1)
        gzm.alpha_highlight = alpha_highlight

        return gzm

    def create_rotation_gizmo(self, context, axis='Z', scale=0.6, line_width=2, alpha=0.3, alpha_highlight=1, hover=False):
        gzm = self.gizmos.new("GIZMO_GT_dial_3d")

        op = gzm.target_set_operator("machin3.transform_cursor")
        op.mode = 'ROTATE'
        op.axis = axis

        gzm.matrix_basis = context.scene.cursor.matrix @ self.get_gizmo_rotation_matrix(axis)

        gzm.draw_options = {'CLIP'}
        gzm.use_draw_value = True
        gzm.use_draw_hover = hover
        gzm.use_grab_cursor = True

        gzm.line_width = line_width
        gzm.scale_basis = scale

        gzm.color = (1, 0.3, 0.3) if axis == 'X' else (0.3, 1, 0.3) if axis == 'Y' else (0.3, 0.3, 1)
        gzm.alpha = alpha
        gzm.color_highlight = (1, 0.5, 0.5) if axis == 'X' else (0.5, 1, 0.5) if axis == 'Y' else (0.5, 0.5, 1)
        gzm.alpha_highlight = alpha_highlight

        return gzm

    def create_drag_gizmo(self, context, scale=0.4, color=(1, 1, 1), alpha=0.05, color_highlight=(0, 0, 0), alpha_highlight=0.5, hover=True):
        gzm = self.gizmos.new("GIZMO_GT_move_3d")

        op = gzm.target_set_operator("machin3.transform_cursor")
        op.mode = 'DRAG'

        gzm.matrix_basis = context.scene.cursor.matrix

        gzm.draw_style = 'RING_2D'
        gzm.draw_options = {'FILL', 'ALIGN_VIEW'}

        gzm.scale_basis = scale

        gzm.use_draw_hover = hover

        gzm.color = color
        gzm.alpha = alpha
        gzm.color_highlight = color_highlight
        gzm.alpha_highlight = alpha_highlight

        return gzm

    def create_scale_gizmo(self, context, axis='X', offset=-0.8, scale=1.0, length=0, alpha=0.3, alpha_highlight=1, hover=False):
        gzm = self.gizmos.new("GIZMO_GT_arrow_3d")

        op = gzm.target_set_operator("machin3.scale_mesh")
        op.direction = 'XMIN' if axis == 'X' else 'YMIN' if axis == 'Y' else 'ZMIN'
        op.cursor_space_rotation = True

        gzm.matrix_basis = context.scene.cursor.matrix @ self.get_gizmo_rotation_matrix(axis)
        gzm.matrix_offset = Matrix.Translation((0, 0, offset))

        gzm.draw_style = 'BOX'
        gzm.use_draw_offset_scale = True
        gzm.use_draw_modal = True
        gzm.use_draw_hover = hover

        gzm.length = length
        gzm.scale_basis = scale

        gzm.color = (1, 0.3, 0.3) if axis == 'X' else (0.3, 1, 0.3) if axis == 'Y' else (0.3, 0.3, 1)
        gzm.alpha = alpha
        gzm.color_highlight = (1, 0.5, 0.5) if axis == 'X' else (0.5, 1, 0.5) if axis == 'Y' else (0.5, 0.5, 1)
        gzm.alpha_highlight = alpha_highlight

        return gzm

class GizmoGroupHyperCursorSimple(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_hyper_cursor_simple"
    bl_label = "Hyper Cursor Simple Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    @classmethod
    def poll(cls, context):
        view = context.space_data

        if view.overlay.show_overlays:
            if get_active_tool(context).idname == 'machin3.tool_hyper_cursor_simple':
                hc = context.scene.HC

                return hc.show_gizmos and hc.draw_HUD

    def setup(self, context):
        self.active = context.active_object

        self.drag = self.create_drag_gizmo(context)

    def draw_prepare(self, context):
        self.drag.matrix_basis = context.scene.cursor.matrix

        context.window_manager.HC_gizmo_scale = self.drag.matrix_world.to_scale()[0] * 2

        set_cursor_2d(context)

    def create_drag_gizmo(self, context, scale=0.2, color=(1, 1, 1), alpha=0.05, color_highlight=(0, 0, 0), alpha_highlight=0.5, hover=True):
        gzm = self.gizmos.new("GIZMO_GT_move_3d")

        op = gzm.target_set_operator("machin3.transform_cursor")
        op.mode = 'DRAG'

        gzm.matrix_basis = context.scene.cursor.matrix

        gzm.draw_style = 'RING_2D'
        gzm.draw_options = {'FILL', 'ALIGN_VIEW'}

        gzm.scale_basis = scale

        gzm.use_draw_hover = hover

        gzm.color = color
        gzm.alpha = alpha
        gzm.color_highlight = color_highlight
        gzm.alpha_highlight = alpha_highlight

        return gzm

class GizmoGroupHyperCursorEditGeometry(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_hyper_cursor_edit_geometry"
    bl_label = "Edit Geometry"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'SCALE', 'PERSISTENT'}

    obj = None
    size = 0.2

    @classmethod
    def poll(cls, context):
        view = context.space_data

        if view.overlay.show_overlays:
            if context.mode == 'OBJECT':
                if get_active_tool(context).idname in ['machin3.tool_hyper_cursor', 'machin3.tool_hyper_cursor_simple']:
                    active = context.active_object
                    sel = context.selected_objects
                    hc = context.scene.HC

                    if hc.draw_HUD:
                        if active and active.HC.ishyper and active.visible_get() and active.type == 'MESH' and active.HC.geometry_gizmos_show and active.HC.geometry_gizmos_edit_mode == 'EDIT' and active.select_get() and len(sel) == 1:

                            facecount = len(active.data.polygons)
                            edgecount = len(active.data.edges)

                            if facecount:
                                if active.HC.objtype == 'CUBE':
                                    return facecount <= active.HC.geometry_gizmos_show_cube_limit

                                elif active.HC.objtype == 'CYLINDER':
                                    return edgecount <= active.HC.geometry_gizmos_show_cylinder_limit

    def setup(self, context):
        self.obj = context.active_object

        self.face_gizmos, self.edge_gizmos = self.create_face_and_edge_gizmos(context, size=self.size)

        self.states = self.get_states(context)

    def refresh(self, context):

        if not is_modal(self):

            if self.is_state_change(context):
                self.gizmos.clear()
                self.obj = context.active_object

                if self.obj and not self.gizmos:
                    self.face_gizmos, self.edge_gizmos = self.create_face_and_edge_gizmos(context, size=self.size)

    def draw_prepare(self, context):

        if is_modal(self):

            for gzm in self.gizmos:
                gzm.hide = not gzm.is_modal

        else:
            if self.is_state_change(context):
                self.gizmos.clear()
                self.obj = context.active_object

                if self.obj and not self.gizmos:
                    self.face_gizmos, self.edge_gizmos = self.create_face_and_edge_gizmos(context, size=self.size)

                else:
                    return

            if self.obj:
                view_dir = region_2d_to_vector_3d(context.region, context.region_data, (context.region.width / 2, context.region.height / 2))

                is_xray = context.scene.HC.gizmo_xray
                is_wire = self.obj.display_type in ['WIRE', 'BOUNDS']

                for gzm, normals, selected in self.edge_gizmos:

                    if not is_wire:
                        dots = [n.dot(view_dir) for n in normals]
                        is_obscured = any([d > 0.0001 for d in dots])

                        if is_xray:
                            gzm.hide = False

                            if selected:
                                gzm.alpha = 0.2 if is_obscured else 0.3
                            else:
                                gzm.alpha = 0.01 if is_obscured else 0.05

                            gzm.alpha_highlight = 0.1 if is_obscured else 0.5

                        else:
                            gzm.hide = is_obscured

                for gzm, normal, gzmtype, _, selected, scale in self.face_gizmos:
                    dot = normal.dot(view_dir)

                    is_obscured = dot > 0.0001
                    is_facing = abs(dot) > 0.9999

                    if gzmtype == 'SCALE':
                        if gzm.is_highlight and scale == gzm.scale_basis:
                            gzm.scale_basis = 1.3 * scale
                        elif not gzm.is_highlight and scale != gzm.scale_basis:
                            gzm.scale_basis = scale

                    if not is_wire:

                        if is_xray:
                            gzm.hide = False

                            if selected:
                                gzm.alpha = 0.2 if is_obscured else 0.3
                            else:
                                gzm.alpha = 0.02 if is_obscured else 0.1

                            gzm.alpha_highlight = 0.2 if is_obscured else 1

                        else:
                            gzm.hide = is_obscured
                            gzm.alpha = 0.3 if selected else 0.1
                            gzm.alpha_highlight = 0.2 if is_obscured else 1

                    if gzmtype == 'PUSH':
                        if is_facing and not gzm.hide:
                            gzm.hide = True

                        elif not is_facing and gzm.hide:
                            if is_wire or is_xray:
                                gzm.hide = False

                            else:
                                gzm.hide = is_obscured

    def get_states(self, context):
        states = [active := context.active_object]

        if active:
            if is_valid_object(active):
                from .. handlers import mode_history, event_history

                states.append(active.type)                                # obj type
                states.append(active.select_get())                        # selection
                states.append(active.visible_get())                       # visibility
                states.append(get_prefs().geometry_gizmos_scale)          # gizmo scale (prefs)
                states.append(active.HC.geometry_gizmos_scale)            # gizmo scale (obj prop)
                states.append(active.HC.geometry_gizmos_edit_mode)        # gizmo edit mode
                states.append(active.HC.geometry_gizmos_edge_thickness)   # gizmo edge thickness
                states.append(active.HC.geometry_gizmos_face_tween)       # gizmo face tween
                states.append(active.display_type)                        # display type
                states.append(len(active.data.vertices))                  # vert count
                states.append(len(active.data.edges))                     # edge count
                states.append(len(active.data.polygons))                  # face count
                states.append(active.matrix_world.copy())                 # world matrix
                states.append(mode_history)                               # mode history
                states.append(event_history)                              # event history (undo/redo)

        return states

    def is_state_change(self, context, debug=False):
        global force_geo_gizmo_update

        if force_geo_gizmo_update:
            force_geo_gizmo_update = False

            if debug:
                print()
                print("  Edit Geometry Gizmo forced update!!")
                print()
            return True

        if (states := self.get_states(context)) != self.states:
            if debug:
                print()
                print("  Edit Geometry Gizmo state has changed!!")
                print("    from:", self.states)
                print("      to:", states)
                print()

            self.states = states
            return True

        return False

    def create_face_and_edge_gizmos(self, context, size=0.2):
        mx = self.obj.matrix_world

        scale_mx = get_sca_matrix(mx.decompose()[2])

        edge_thickness = self.obj.HC.geometry_gizmos_edge_thickness

        face_tween = self.obj.HC.geometry_gizmos_face_tween

        ui_scale = context.preferences.system.ui_scale

        gizmo_size = context.preferences.view.gizmo_size / 75

        gizmo_scale_prefs = get_prefs().geometry_gizmos_scale
        gizmo_scale_obj = self.obj.HC.geometry_gizmos_scale

        gizmo_scale = gizmo_scale_prefs * gizmo_scale_obj

        _, _, dims = get_bbox(self.obj.data)
        mesh_dim = sum([abs(d) for d in get_sca_matrix(mx.to_scale()) @ dims]) / 3

        if self.obj.HC.objtype == 'CYLINDER':
            mesh_density = 1

        else:
            mesh_density = 10 * pow(0.8, 0.3 * (len(self.obj.data.polygons) + 35)) + 0.4

        bm = bmesh.new()
        bm.from_mesh(self.obj.data)

        edge_glayer, face_glayer = ensure_gizmo_layers(bm)
        edge_slayer, face_slayer = ensure_select_layers(bm)

        edge_gizmos = []

        edges = [e for e in bm.edges if e[edge_glayer] == 1]

        for e in edges:
            e_dir = mx.to_3x3() @ (e.verts[1].co - e.verts[0].co)

            loc = get_loc_matrix(mx @ get_center_between_verts(*e.verts))
            rot = create_rotation_matrix_from_vector(e_dir.normalized())
            sca = get_sca_matrix(Vector((1, 1, (e_dir.length) / (size * mesh_dim * mesh_density * ui_scale * gizmo_scale * gizmo_size * edge_thickness))))

            gzm = self.gizmos.new("MACHIN3_GT_3d_stem")
            op = gzm.target_set_operator("machin3.call_hyper_cursor_pie")
            op.idname = 'MACHIN3_MT_edit_edge'
            op.index = e.index

            gzm.matrix_basis = loc @ rot @ sca
            gzm.scale_basis = size * mesh_dim * mesh_density * gizmo_scale * gizmo_size * edge_thickness

            selected = e[edge_slayer] == 1 if edge_slayer else False

            gzm.color = (0.5, 1, 0.5) if selected == 1 else (1, 1, 1)
            gzm.alpha = 0.3 if selected == 1 else 0.05
            gzm.color_highlight = (1, 0.5, 0.5)
            gzm.alpha_highlight = 0.5

            edge_gizmos.append((gzm, [get_world_space_normal(f.normal, mx) for f in e.link_faces], selected))

        face_gizmos = []

        faces = [f for f in bm.faces if f[face_glayer] == 1]

        for face in faces:

            loc = get_loc_matrix(mx @ get_face_center(face, method='PROJECTED_BOUNDS'))

            rot = create_rotation_matrix_from_vector(get_world_space_normal(face.normal, mx))
            face_dim = (scale_mx @ Vector((sqrt(face.calc_area()), 0, 0))).length * 1.3

            face_size = tween(mesh_dim * mesh_density, face_dim, face_tween)

            gzm = self.gizmos.new("MACHIN3_GT_2d_ring")

            op = gzm.target_set_operator("machin3.call_hyper_cursor_pie")
            op.idname = 'MACHIN3_MT_edit_face'
            op.index = face.index

            gzm.matrix_basis = loc @ rot
            gzm.scale_basis = size * gizmo_size * gizmo_scale * 0.18 * face_size

            selected = face[face_slayer] == 1 if face_slayer else False

            gzm.color = (0.5, 1, 0.5) if selected == 1 else (1, 1, 1)
            gzm.alpha = 0.3 if selected == 1 else 0.05
            gzm.color_highlight = (1, 0.5, 0.5)
            gzm.alpha_highlight = 1

            face_gizmos.append((gzm, get_world_space_normal(face.normal, mx), 'SCALE', face.index, selected, gzm.scale_basis))

            gzm = self.gizmos.new("GIZMO_GT_arrow_3d")

            op = gzm.target_set_operator("machin3.push_face")
            op.index = face.index

            gzm.matrix_basis = loc @ rot
            gzm.scale_basis = size * gizmo_size * gizmo_scale * face_size

            gzm.draw_style = 'NORMAL'
            gzm.length = 0.1

            gzm.color = (1, 1, 1)
            gzm.alpha = 0.1
            gzm.color_highlight = (1, 0.5, 0.5)
            gzm.alpha_highlight = 1

            face_gizmos.append((gzm, get_world_space_normal(face.normal, mx), 'PUSH', face.index, False, gzm.scale_basis))

        return face_gizmos, edge_gizmos

class GizmoGroupHyperCursorScaleGeometry(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_hyper_cursor_scale_geometry"
    bl_label = "Scale Geometry"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'SCALE', 'PERSISTENT'}

    obj = None
    size = 0.2

    @classmethod
    def poll(cls, context):
        view = context.space_data

        if view.overlay.show_overlays:
            if context.mode == 'OBJECT':
                if get_active_tool(context).idname in ['machin3.tool_hyper_cursor', 'machin3.tool_hyper_cursor_simple']:
                    active = context.active_object
                    sel = context.selected_objects
                    hc = context.scene.HC

                    if hc.draw_HUD:
                        if active and active.HC.ishyper and active.visible_get() and active.type == 'MESH' and active.HC.geometry_gizmos_show and active.HC.geometry_gizmos_edit_mode == 'SCALE' and active.select_get() and len(sel) == 1:

                            if active.HC.geometry_gizmos_edit_mode == 'SCALE':
                                return len(active.data.polygons) <= active.HC.geometry_gizmos_show_limit

    def setup(self, context):
        self.obj = context.active_object

        self.scale_gizmos = self.create_scale_gizmos(context, size=self.size)

        self.states = self.get_states(context)

    def refresh(self, context):
        if not is_modal(self):

            if self.is_state_change(context):
                self.gizmos.clear()
                self.obj = context.active_object

                if self.obj and not self.gizmos:
                    self.scale_gizmos = self.create_scale_gizmos(context, size=self.size)

    def draw_prepare(self, context):
        if is_modal(self):
            for gzm in self.gizmos:
                if not gzm.is_modal:
                    gzm.hide = True
        else:
            if self.is_state_change(context):
                self.gizmos.clear()
                self.obj = context.active_object

                if self.obj and not self.gizmos:
                    self.scale_gizmos = self.create_scale_gizmos(context, size=self.size)

                else:
                    return

            if self.obj:
                view_dir = region_2d_to_vector_3d(context.region, context.region_data, (context.region.width / 2, context.region.height / 2))

                is_xray = context.scene.HC.gizmo_xray
                is_wire = self.obj.display_type in ['WIRE', 'BOUNDS']

                for gzm, normal in self.scale_gizmos:
                    dot = normal.dot(view_dir)

                    is_obscured = dot > 0.0001
                    is_facing = abs(dot) > 0.9999

                    if not is_wire:

                        if is_xray:
                            gzm.hide = False
                            gzm.alpha = 0.02 if is_obscured else 0.1
                            gzm.alpha_highlight = 0.2 if is_obscured else 1

                        else:
                            gzm.hide = is_obscured
                            gzm.alpha = 0.1
                            gzm.alpha_highlight = 1

                    if is_facing and not gzm.hide:
                        gzm.hide = True

                    elif not is_facing and gzm.hide:
                        if is_wire or is_xray:
                            gzm.hide = False
                        else:
                            gzm.hide = is_obscured

    def get_states(self, context):
        states = [active := context.active_object]

        if active:
            if is_valid_object(active):
                from .. handlers import mode_history, event_history

                states.append(active.type)                                # obj type
                states.append(active.select_get())                        # selection
                states.append(active.visible_get())                       # visibility
                states.append(active.HC.geometry_gizmos_edit_mode)        # gizmo edit mode
                states.append(active.display_type)                        # display type
                states.append(len(active.data.vertices))                  # vert count
                states.append(len(active.data.edges))                     # edge count
                states.append(len(active.data.polygons))                  # face count
                states.append(active.matrix_world.copy())                 # world matrix
                states.append(mode_history)                               # mode history
                states.append(event_history)                              # event history (undo/redo)

        return states

    def is_state_change(self, context, debug=False):
        global force_geo_gizmo_update

        if force_geo_gizmo_update:
            force_geo_gizmo_update = False

            if debug:
                print()
                print("  Edit Geometry Gizmo forced update!!")
                print()
            return True

        if (states := self.get_states(context)) != self.states:
            if debug:
                print()
                print("  Edit Geometry Gizmo state has changed!!")
                print("    from:", self.states)
                print("      to:", states)
                print()

            self.states = states
            return True

        return False

    def create_scale_gizmos(self, context, size=0.2):
        mx = self.obj.matrix_world

        bbox, centers, dims = get_bbox(self.obj.data)
        dim = sum([d for d in get_sca_matrix(mx.to_scale()) @ dims]) / 3

        xmin = centers[0]
        xmax = centers[1]
        ymin = centers[2]
        ymax = centers[3]
        zmin = centers[4]
        zmax = centers[5]

        scale_gizmos = []

        loc = get_loc_matrix(mx @ xmin)
        normal = (xmin - xmax).normalized()
        rot = create_rotation_matrix_from_vector(mx.to_quaternion() @ normal)

        self.xmin = self.create_mesh_scale_gizmo(context, 'XMIN', mx, loc, rot, size, dim, length=0.1, color=(1, 1, 1), alpha=0.1, color_highlight=(1, 0.5, 0.5), alpha_highlight=1)
        scale_gizmos.append((self.xmin, mx.to_quaternion() @ normal))

        loc = get_loc_matrix(mx @ xmax)
        normal = (xmax - xmin).normalized()
        rot = create_rotation_matrix_from_vector(mx.to_quaternion() @ normal)

        self.xmax = self.create_mesh_scale_gizmo(context, 'XMAX', mx, loc, rot, size, dim, length=0.1, color=(1, 1, 1), alpha=0.1, color_highlight=(1, 0.5, 0.5), alpha_highlight=1)
        scale_gizmos.append((self.xmax, mx.to_quaternion() @ normal))

        loc = get_loc_matrix(mx @ ymin)
        normal = (ymin - ymax).normalized()
        rot = create_rotation_matrix_from_vector(mx.to_quaternion() @ normal)

        self.ymin = self.create_mesh_scale_gizmo(context, 'YMIN', mx, loc, rot, size, dim, length=0.1, color=(1, 1, 1), alpha=0.1, color_highlight=(1, 0.5, 0.5), alpha_highlight=1)
        scale_gizmos.append((self.ymin, mx.to_quaternion() @ normal))

        loc = get_loc_matrix(mx @ ymax)
        normal = (ymax - ymin).normalized()
        rot = create_rotation_matrix_from_vector(mx.to_quaternion() @ normal)

        self.ymax = self.create_mesh_scale_gizmo(context, 'YMAX', mx, loc, rot, size, dim, length=0.1, color=(1, 1, 1), alpha=0.1, color_highlight=(1, 0.5, 0.5), alpha_highlight=1)
        scale_gizmos.append((self.ymax, mx.to_quaternion() @ normal))

        loc = get_loc_matrix(mx @ zmin)
        normal = (zmin - zmax).normalized()
        rot = create_rotation_matrix_from_vector(mx.to_quaternion() @ normal)

        self.zmin = self.create_mesh_scale_gizmo(context, 'ZMIN', mx, loc, rot, size, dim, length=0.1, color=(1, 1, 1), alpha=0.1, color_highlight=(1, 0.5, 0.5), alpha_highlight=1)
        scale_gizmos.append((self.zmin, mx.to_quaternion() @ normal))

        loc = get_loc_matrix(mx @ zmax)
        normal = (zmax - zmin).normalized()
        rot = create_rotation_matrix_from_vector(mx.to_quaternion() @ normal)

        self.zmax = self.create_mesh_scale_gizmo(context, 'ZMAX', mx, loc, rot, size, dim, length=0.1, color=(1, 1, 1), alpha=0.1, color_highlight=(1, 0.5, 0.5), alpha_highlight=1)
        scale_gizmos.append((self.zmax, mx.to_quaternion() @ normal))

        return scale_gizmos

    def create_mesh_scale_gizmo(self, context, direction, mx, loc, rot, size, dim, length=0.1, color=(1, 1, 1), alpha=0.1, color_highlight=(1, 0.5, 0.5), alpha_highlight=1):
        gzm = self.gizmos.new("GIZMO_GT_arrow_3d")

        op = gzm.target_set_operator("machin3.scale_mesh")
        op.direction = direction
        op.cursor_space_rotation = False

        gzm.matrix_basis = loc @ rot
        gzm.scale_basis = size * dim
        gzm.length = length

        gzm.draw_style = 'BOX'
        gzm.color = color
        gzm.alpha = alpha
        gzm.color_highlight = color_highlight
        gzm.alpha_highlight = alpha_highlight

        return gzm

class GizmoGroupHyperCursorObject(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_hyper_cursor_object"
    bl_label = "Object"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', '3D'}

    @classmethod
    def poll(cls, context):
        view = context.space_data

        if view.overlay.show_overlays:
            if context.mode == 'OBJECT':
                if get_active_tool(context).idname in ['machin3.tool_hyper_cursor', 'machin3.tool_hyper_cursor_simple']:
                    hc = context.scene.HC

                    if hc.draw_HUD and hc.show_object_gizmos:
                        active = context.active_object
                        sel = context.selected_objects

                        return active and active.HC.ishyper and active.visible_get() and active.select_get() and len(sel) == 1

    def setup(self, context):
        global machin3tools, meshmachine

        if machin3tools is None:
            machin3tools = get_addon('MACHIN3tools')[0]

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        self.obj = context.active_object

        self.create_object_gizmos(context)

        self.states = self.get_states(context)

    def refresh(self, context):

        if self.is_state_change(context):
            self.gizmos.clear()
            self.obj = context.active_object

            if self.obj and not self.gizmos:
                self.create_object_gizmos(context)

    def draw_prepare(self, context):

        if self.is_state_change(context):
            self.gizmos.clear()
            self.obj = context.active_object

            if self.obj and not self.gizmos:
                self.create_object_gizmos(context)

            else:
                return

        if self.obj:
            gizmo_size = context.preferences.view.gizmo_size / 75

            global machin3tools, meshmachine

            if is_modal(self):
                for gzm in self.gizmos:
                    gzm.hide = True

            else:
                for gzm in self.gizmos:
                    gzm.hide = False

                corners = self.get_view_bbox_corners(context)

                offset = Vector((10, 10)) * gizmo_size

                offset_button_gizmo(context, self.objmenu_gzm, offset=offset, loc2d=corners['TOP_RIGHT'])
                offset -= Vector((0, 25)) * gizmo_size 

                if self.geogzm_setup_gzm:
                    offset_button_gizmo(context, self.geogzm_setup_gzm, offset=offset, loc2d=corners['TOP_RIGHT'])

                offset = Vector((10, -10)) * gizmo_size

                show_reflect_gizmo = (machin3tools and get_prefs().show_machin3tools_mirror_gizmo) or (meshmachine and get_prefs().show_meshmachine_symmetrize_gizmo and self.obj.type == 'MESH')

                if show_reflect_gizmo:
                    offset_button_gizmo(context, self.reflect_gzm, offset=offset, loc2d=corners['BOTTOM_RIGHT'])

                    if self.hypermod_gzm:
                        offset_button_gizmo(context, self.hypermod_gzm, offset=offset + Vector((25, 0)) * gizmo_size, loc2d=corners['BOTTOM_RIGHT'])

                    offset += Vector((0, 25)) * gizmo_size

                elif self.hypermod_gzm:
                    offset_button_gizmo(context, self.hypermod_gzm, offset=offset, loc2d=corners['BOTTOM_RIGHT'])
                    offset += Vector((0, 25)) * gizmo_size

                if self.cylinder_gzm:
                    offset_button_gizmo(context, self.cylinder_gzm, offset=offset, loc2d=corners['BOTTOM_RIGHT'])
                    offset += Vector((0, 25)) * gizmo_size

                if self.pipe_gzm:
                    offset_button_gizmo(context, self.pipe_gzm, offset=offset, loc2d=corners['BOTTOM_RIGHT'])
                    offset += Vector((0, 25)) * gizmo_size

                if self.shell_gzm:
                    offset_button_gizmo(context, self.shell_gzm, offset=offset, loc2d=corners['BOTTOM_RIGHT'])
                    offset += Vector((0, 25)) * gizmo_size

                if self.displace_gzm:
                    offset_button_gizmo(context, self.displace_gzm, offset=offset, loc2d=corners['BOTTOM_RIGHT'])
                    offset += Vector((0, 25)) * gizmo_size

                if self.array_gzm:
                    offset_button_gizmo(context, self.array_gzm, offset=offset, loc2d=corners['BOTTOM_RIGHT'])
                    offset += Vector((0, 25)) * gizmo_size

    def get_states(self, context):
        states = [active := context.active_object]

        if active:
            if is_valid_object(active):
                from .. handlers import mode_history, event_history

                states.append(active.type)             # obj type, so you can watch curve to mesh conversion for instance
                states.append(active.select_get())     # selection state
                states.append(active.visible_get())    # visibility state
                states.append(len(active.modifiers))   # modifier count
                states.append(mode_history)            # mode history
                states.append(event_history)           # event history (undo/redo)

        return states

    def is_state_change(self, context, debug=False):
        global force_obj_gizmo_update

        if force_obj_gizmo_update:
            force_obj_gizmo_update = False

            if debug:
                print()
                print("  Object button Gizmo forced update!!")
                print()
            return True

        if (states := self.get_states(context)) != self.states:
            if debug:
                print()
                print("  Object Button Gizmo state has changed!!")
                print("    from:", self.states)
                print("      to:", states)
                print()

            self.states = states
            return True

        return False

    def get_view_bbox_corners(self, context):
        eval_bbox = get_eval_bbox(self.obj)
        view_bbox = get_view_bbox(context, [self.obj.matrix_world @ co for co in eval_bbox])

        corner_dict = {'BOTTOM_LEFT': view_bbox[0],
                       'BOTTOM_RIGHT': view_bbox[1],
                       'BOTTOM_CENTER': Vector((round((view_bbox[0].x + view_bbox[1].x) / 2), view_bbox[0].y)),
                       'TOP_RIGHT': view_bbox[2],
                       'TOP_LEFT': view_bbox[3]}

        return corner_dict

    def is_non_manifold(self):
        if self.obj.type == 'MESH':
            bm = bmesh.new()
            bm.from_mesh(self.obj.data)

            is_non_manifold = any([not e.is_manifold for e in bm.edges])

            bm.free()

            return is_non_manifold and self.obj.data.polygons
        return False

    def has_displace(self, context):
        if displace_poll(context):
            return True

        intersect_booleans = [mod for mod in boolean_poll(context) if mod.operation == 'INTERSECT']

        for mod in intersect_booleans:
            if displace_poll(context, obj=mod.object):
                return True

        return False

    def create_object_gizmos(self, context):

        global machin3tools, meshmachine

        self.objmenu_gzm = create_button_gizmo(self, context, 'machin3.hyper_cursor_object', icon='OBJECT_DATA', location=self.obj.location, scale=0.11)

        if self.obj.type == 'MESH':
            self.geogzm_setup_gzm = create_button_gizmo(self, context, 'machin3.geogzm_setup', icon='MOD_EDGESPLIT', location=self.obj.location, scale=0.11)
        else:
            self.geogzm_setup_gzm = None

        if (machin3tools and get_prefs().show_machin3tools_mirror_gizmo) or (meshmachine and get_prefs().show_meshmachine_symmetrize_gizmo and self.obj.type == 'MESH'):
            self.reflect_gzm = create_button_gizmo(self, context, 'machin3.reflect', icon='MOD_MIRROR', location=self.obj.location, scale=0.11)
        else:
            self.reflect_gzm = None

        if get_prefs().show_hypermod_gizmo and self.obj.type == 'MESH':
            self.hypermod_gzm = create_button_gizmo(self, context, 'machin3.hyper_modifier', args={'is_gizmo_invokation': True}, icon='MODIFIER_DATA', location=self.obj.location, scale=0.11)

        else:
            self.hypermod_gzm = None

        if self.obj.type == 'MESH' and self.obj.HC.objtype == 'CYLINDER':
            self.cylinder_gzm = create_button_gizmo(self, context, 'machin3.adjust_cylinder', icon='MESH_CYLINDER', location=self.obj.location, scale=0.11)
        else:
            self.cylinder_gzm = None

        if self.obj.type == 'CURVE':
            self.pipe_gzm = create_button_gizmo(self, context, 'machin3.adjust_pipe', args={'is_profile_drop': False}, icon='META_CAPSULE', location=self.obj.location, scale=0.11)
        else:
            self.pipe_gzm = None

        self.is_shell = solidify_poll(context) or self.is_non_manifold()

        if self.is_shell:
            self.shell_gzm = create_button_gizmo(self, context, 'machin3.adjust_shell', args={'is_hypermod_invoke': False}, icon='SNAP_OFF', location=self.obj.location, scale=0.11)
        else:
            self.shell_gzm = None

        self.is_displace = self.has_displace(context)
        
        if self.is_displace:
            self.displace_gzm = create_button_gizmo(self, context, 'machin3.adjust_displace', args={'is_hypermod_invoke': False}, icon='FULLSCREEN_EXIT', location=self.obj.location, scale=0.11)
        else:
            self.displace_gzm = None

        self.is_array = bool(hyper_array_poll(context))

        if self.is_array:
            self.array_gzm = create_button_gizmo(self, context, 'machin3.adjust_array', args={'is_hypermod_invoke': False}, icon='MOD_ARRAY', location=self.obj.location, scale=0.11)
        else:
            self.array_gzm = None

class GizmoGroupEditCurve(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_edit_curve"
    bl_label = "Object"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', '3D'}

    @classmethod
    def poll(cls, context):
        view = context.space_data

        if view.overlay.show_overlays:
            if context.mode == 'EDIT_CURVE':
                active = context.active_object
                data = get_curve_as_dict(active.data)

                if spline := verify_curve_data(data, 'has_active_spline'):
                    if spline['type'] in ['POLY', 'NURBS'] and len(spline['points']) >= 3:
                        if verify_curve_data(data, 'has_active_selection'):
                            if not verify_curve_data(data, 'is_active_end_selected'):
                                if verify_curve_data(data, 'is_active_selection_continuous'):
                                    return True

    def setup(self, context):
        self.obj = context.active_object

        self.data = get_curve_as_dict(self.obj.data)
        self.create_edit_curve_gizmos(context)

    def refresh(self, context):
        obj = context.active_object
        data = get_curve_as_dict(obj.data)

        if not is_modal(self) and (data != self.data or obj != self.obj):
            self.obj = obj
            self.data = data

            self.gizmos.clear()
            self.create_edit_curve_gizmos(context)

    def draw_prepare(self, context):
        if is_modal(self):
            for gzm in self.gizmos:
                gzm.hide = True
        else:
            for gzm in self.gizmos:
                gzm.hide = False

            gizmo_size = context.preferences.view.gizmo_size / 75

            corners = self.get_view_bbox_corners(context)

            offset = Vector((20, 20)) * gizmo_size

            offset_button_gizmo(context, self.blendulate, offset=offset, loc2d=corners['TOP_RIGHT'])

    def get_view_bbox_corners(self, context):
        view_bbox = get_view_bbox(context, [self.obj.matrix_world @ point['co'].xyz for point in self.data['active_selection']])

        corner_dict = {'BOTTOM_LEFT': view_bbox[0],
                       'BOTTOM_RIGHT': view_bbox[1],
                       'TOP_RIGHT': view_bbox[2],
                       'TOP_LEFT': view_bbox[3]}

        return corner_dict

    def create_edit_curve_gizmos(self, context):

        self.blendulate = create_button_gizmo(self, context, 'machin3.blendulate', icon='DRIVER_ROTATIONAL_DIFFERENCE', location=self.obj.matrix_world @ self.data['active_selection_mid_point'], scale=0.11)

class GizmoGroupCursorHistory(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_cursor_history"
    bl_label = "Object"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', '3D'}

    @classmethod
    def poll(cls, context):
        view = context.space_data
        hc = context.scene.HC

        if view.overlay.show_overlays:
            if get_active_tool(context).idname in ['machin3.tool_hyper_cursor', 'machin3.tool_hyper_cursor_simple']:
                return hc.draw_history and (hc.draw_history_select or hc.draw_history_remove)

    def setup(self, context):
        hc = context.scene.HC

        self.select = self.create_history_buttons(context, type='SELECT') if hc.draw_history_select else []
        self.remove = self.create_history_buttons(context, type='REMOVE') if hc.draw_history_remove else []

    def refresh(self, context):
        hc = context.scene.HC

        self.gizmos.clear()

        self.select = self.create_history_buttons(context, type='SELECT') if hc.draw_history_select else []
        self.remove = self.create_history_buttons(context, type='REMOVE') if hc.draw_history_remove else []

    def draw_prepare(self, context):
        gizmo_size = context.preferences.view.gizmo_size / 75

        for gzm, entry in self.select + self.remove:
            loc2d = entry.gzm_location2d

            if is_on_screen(context, loc2d):
                if gzm.hide:
                    gzm.hide = False

                offset = (15 * gizmo_size, 0) if context.scene.HC.draw_history_select and (gzm, entry) in self.remove else (0, 0)
                offset_button_gizmo(context, gzm, offset=offset, loc2d=loc2d)

            else:
                if not gzm.hide:
                    gzm.hide = True

    def create_history_buttons(self, context, type='SELECT'):
        hc = context.scene.HC

        buttons = []

        for entry in hc.historyCOL:
            if type == 'SELECT':
                idname = 'machin3.select_cursor_history'
                args = {'index': entry.index}
                icon = 'RESTRICT_SELECT_OFF'
                scale = 0.09

            elif type == 'REMOVE':
                idname = 'machin3.change_cursor_history'
                args = {'index': entry.index, 'mode': 'REMOVE'}
                icon = 'X'
                scale = 0.11

            gzm = create_button_gizmo(self, context, idname, args=args, icon=icon, location=entry.location, scale=scale)

            buttons.append((gzm, entry))

        return buttons

class GizmoGroupPipeRadius(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_pipe_radius"
    bl_label = "Pipe Radius"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    count = 0

    @classmethod
    def poll(cls, context):
        return context.window_manager.HC_piperadiiCOL

    def setup(self, context):
        self.create_pipe_radius_gizmos(context)

    def refresh(self, context):
        if len(self.gizmos) != len(context.window_manager.HC_piperadiiCOL):
            self.gizmos.clear()

            self.create_pipe_radius_gizmos(context)

    def draw_prepare(self, context):
        if is_modal(self):
            for gzm, _ in self.gzms:
                gzm.hide = True
        else:
            for gzm, r in self.gzms:
                gzm.hide = r.hide

    def create_pipe_radius_gizmos(self, context):
        self.gzms = []

        area_pointer = str(context.area.as_pointer())

        for idx, r in enumerate(context.window_manager.HC_piperadiiCOL):
            if r.area_pointer == area_pointer:
                gzm = create_button_gizmo(self, context, operator='machin3.adjust_pipe_arc', args={'index': idx}, icon='RADIOBUT_ON', location=r.co, scale=0.1)
                self.gzms.append((gzm, r))

class GizmoGroupCurveSurface(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_curve_surface"
    bl_label = "Pipe Radius"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    @classmethod
    def poll(cls, context):
        return context.window_manager.HC_curvesurfCOL

    def setup(self, context):
        self.create_curve_surface_point_gizmos(context)

    def refresh(self, context):
        if len(self.gizmos) != len(context.window_manager.HC_curvesurfCOL):
            self.gizmos.clear()

            self.create_curve_surface_point_gizmos(context)

    def draw_prepare(self, context):
        for gzm, p in self.gzms:
            gzm.matrix_basis.translation = p.co

        pass

    def create_curve_surface_point_gizmos(self, context):
        self.gzms = []

        area_pointer = str(context.area.as_pointer())

        for idx, p in enumerate(context.window_manager.HC_curvesurfCOL):
            if area_pointer == p.area_pointer:
                gzm = create_button_gizmo(self, context, operator='machin3.adjust_curve_surface_point', args={'index': idx}, icon='RADIOBUT_ON', location=p.co, scale=0.06)
                self.gzms.append((gzm, p))

class GizmoGroupRemoveUnusedBooleans(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_remove_unused_booleans"
    bl_label = "Remove Unused Booleans"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    @classmethod
    def poll(cls, context):
        if context.window_manager.HC_removeunusedbooleansCOL:
            return context.scene.HC.draw_remove_unused_booleans_HUD

    def setup(self, context):
        wm = context.window_manager

        self.gizmo_size = context.preferences.view.gizmo_size / 75
        self.active = wm.HC_removeunusedbooleansactive
        self.removeCOL = wm.HC_removeunusedbooleansCOL

        self.create_remove_unused_booleans_gizmos(context)

        self.states = self.get_states()

    def refresh(self, context):

        if self.is_state_change():
            self.gizmos.clear()
            self.create_remove_unused_booleans_gizmos(context)

    def draw_prepare(self, context):
        if self.is_state_change():
            self.gizmos.clear()
            self.create_remove_unused_booleans_gizmos(context)

        is_any_highlight = False

        for gizmos, r in self.gzms:
            
            is_highlight = any(gzm.is_highlight for gzm in gizmos)

            factor = 1 if is_highlight else 0.7

            offset = 0

            for gzm in gizmos:
                offset_button_gizmo(context, gzm, offset=(offset * self.gizmo_size * factor, 0), loc2d=Vector(r.co2d))
                offset += 20

                gzm.scale_basis = factor / 10

            r.is_highlight = is_highlight

            if is_highlight:
                is_any_highlight = True

        for gizmos, r in self.gzms:
            if is_any_highlight and not r.is_highlight:
                for gzm in gizmos:
                    gzm.hide = True

            elif not is_any_highlight:
                for gzm in gizmos:
                    gzm.hide = False

    def get_states(self):
        states = [r.remove for r in self.removeCOL]

        states.append([self.active.modifiers.get(r.name).show_viewport for r in self.removeCOL])

        return states

    def is_state_change(self, debug=True):
        if (states := self.get_states()) != self.states:
            if debug:
                print()
                print("  Remove Unused Booleans Gizmo state has changed!!")
                print("    from:", self.states)
                print("      to:", states)
                print()

            self.states = states
            return True

        return False

    def create_remove_unused_booleans_gizmos(self, context):
        self.gzms = []

        for idx, r in enumerate(self.removeCOL):
            if r.area_pointer == str(context.area.as_pointer()):
                mod = self.active.modifiers.get(r.name)

                icon = 'HIDE_OFF' if mod.show_viewport else 'HIDE_ON'
                mgzm = create_button_gizmo(self, context, operator='machin3.toggle_unused_boolean_mod', args={'index': idx, 'mode': 'MODIFIER'}, icon=icon, location=r.co, scale=0.1)

                icon = 'X' if r.remove else 'RADIOBUT_OFF'
                rgzm = create_button_gizmo(self, context, operator='machin3.toggle_unused_boolean_mod', args={'index': idx, 'mode': 'REMOVE'}, icon=icon, location=r.co, scale=0.1)

                self.gzms.append(((mgzm, rgzm), r))

class GizmoGroupPickObjectTree(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_pick_object_tree"
    bl_label = "Pick Object Tree"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    @classmethod
    def poll(cls, context):
        if context.window_manager.HC_pickobjecttreeCOL:
            return context.window_manager.HC_pickobjecttreeshowHUD

    def setup(self, context):
        wm = context.window_manager

        self.treeCOL = wm.HC_pickobjecttreeCOL

        self.states = [(t.remove, bpy.data.objects[t.modhostobjname].modifiers[t.modname].show_viewport if t.modhostobjname else None) for t in self.treeCOL]

        self.create_pick_object_tree_gizmos(context)

    def refresh(self, context):

        states = [(t.remove, bpy.data.objects[t.modhostobjname].modifiers[t.modname].show_viewport if t.modhostobjname else None) for t in self.treeCOL]

        if states != self.states:
            self.states = states
            self.create_pick_object_tree_gizmos(context)

    def draw_prepare(self, context):

        gizmo_size = context.preferences.view.gizmo_size / 75

        for select_gizmo, mod_gizmo, remove_gizmo, t in self.gzms:

            gizmos = [gzm for gzm in [select_gizmo, mod_gizmo, remove_gizmo] if gzm]

            factor = 1 if t.is_highlight else 0.7

            offset = 0

            for gzm in gizmos:
                offset_button_gizmo(context, gzm, offset=(offset * gizmo_size * factor, 0), loc2d=Vector(t.co2d))
                offset += 20

            if any(gzm.is_highlight for gzm in gizmos):
                for gzm in gizmos:
                    gzm.scale_basis = factor / 10

            else:
                for gzm in gizmos:
                    gzm.scale_basis = factor / 10

        is_any_highlight = False

        for select_gizmo, mod_gizmo, remove_gizmo, t in self.gzms:
            gizmos = [gzm for gzm in [select_gizmo, mod_gizmo, remove_gizmo] if gzm]
            t.is_highlight = any([gzm.is_highlight for gzm in gizmos])

            if t.is_highlight:
                is_any_highlight = True

        for select_gizmo, mod_gizmo, remove_gizmo, t in self.gzms:
            gizmos = [gzm for gzm in [select_gizmo, mod_gizmo, remove_gizmo] if gzm]

            for gzm in gizmos:
                gzm.hide = not t.show

            if t.show:
                t.is_highlight = any([gzm.is_highlight for gzm in gizmos])

                if is_any_highlight and not t.is_highlight:
                    for gzm in gizmos:
                        gzm.hide = True

                elif not is_any_highlight:
                    for gzm in gizmos:
                        gzm.hide = False

    def create_pick_object_tree_gizmos(self, context):
        self.gizmos.clear()
        self.gzms = []

        for idx, t in enumerate(self.treeCOL):
            if t.area_pointer == str(context.area.as_pointer()):

                icon = 'RESTRICT_SELECT_OFF'
                select_gizmo = create_button_gizmo(self, context, operator='machin3.toggle_pick_object_tree', args={'mode': 'SELECT'}, icon=icon, location=t.co, scale=0.1)

                if t.modname:
                    if t.modhostobjname:
                        modparent = bpy.data.objects[t.modhostobjname]
                        mod = modparent.modifiers.get(t.modname)

                        icon = 'HIDE_OFF' if mod.show_viewport else 'HIDE_ON'
                        mod_gizmo = create_button_gizmo(self, context, operator='machin3.toggle_pick_object_tree', args={'mode': 'TOGGLE'}, icon=icon, location=t.co, scale=0.1)

                icon = 'X' if t.remove else 'RADIOBUT_OFF'
                remove_gizmo = create_button_gizmo(self, context, operator='machin3.toggle_pick_object_tree', args={'mode': 'REMOVE'}, icon=icon, location=t.co, scale=0.1)

                self.gzms.append((select_gizmo, mod_gizmo if t.modname else None, remove_gizmo, t))

class GizmoGroupPickHyperBevel(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_pick_hyper_bevel"
    bl_label = "Pick Hyper Bevel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'SCALE'}

    count = 0

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            wm = context.window_manager
            return wm.HC_pickhyperbevelsCOL and wm.HC_pickhyperbevelshowHUD

    def setup(self, context):
        self.obj = context.active_object

        _, _, dims = get_bbox(self.obj.data)
        self.dim = sum([d for d in get_sca_matrix(self.obj.matrix_world.to_scale()) @ dims]) / 3

        self.create_hyper_bevel_gizmos(context)

    def refresh(self, context):

        global force_pick_hyper_bevels_gizmo_update

        if len(self.gzms) != len(context.window_manager.HC_pickhyperbevelsCOL) or force_pick_hyper_bevels_gizmo_update:
            if force_pick_hyper_bevels_gizmo_update:
                force_pick_hyper_bevels_gizmo_update = False

            self.gizmos.clear()

            self.create_hyper_bevel_gizmos(context)

    def draw_prepare(self, context):

        if is_modal(self):
            for edge_gizmos, _ in self.gzms:
                for gzm in edge_gizmos:
                    gzm.hide = True

        else:
            for edge_gizmos, bevel in self.gzms:

                is_highlight = any(gzm.is_highlight for gzm in edge_gizmos)

                bevel.is_highlight = is_highlight

                for gzm in edge_gizmos:
                    gzm.hide = False

                    if gzm.is_highlight:
                        gzm.color_highlight = red if bevel.remove else yellow
                        gzm.alpha_highlight = 0.5 if bevel.active else 0.25

                    if is_highlight and not gzm.is_highlight:
                        gzm.color = red if bevel.remove else yellow
                        gzm.alpha = 0.5 if bevel.active else 0.25
                    
                    elif not is_highlight:
                        gzm.color = red if bevel.remove else white
                        gzm.alpha = 0.1 if bevel.remove else 0.05 if bevel.active else 0.01

    def create_hyper_bevel_gizmos(self, context):
        def create_edge_gizmos(bevel, size=0.2):
            obj = bevel.obj
            mx = obj.matrix_world

            ui_scale = context.preferences.system.ui_scale

            gizmo_size = context.preferences.view.gizmo_size / 75

            bm = bmesh.new()
            bm.from_mesh(obj.data)

            edge_glayer = ensure_edge_glayer(bm)

            edges = [e for e in bm.edges if e[edge_glayer] == 1]

            edge_gizmos = []

            for e in edges:
                e_dir = mx.to_3x3() @ (e.verts[1].co - e.verts[0].co)

                loc = get_loc_matrix(mx @ get_center_between_verts(*e.verts))
                rot = create_rotation_matrix_from_vector(e_dir.normalized())
                sca = get_sca_matrix(Vector((1, 1, (e_dir.length) / (size * self.dim * self.obj.HC.geometry_gizmos_scale * ui_scale * gizmo_size))))

                gzm = self.gizmos.new("MACHIN3_GT_3d_stem")
                op = gzm.target_set_operator("machin3.edit_hyper_bevel")
                op.objname = self.obj.name
                op.modname = bevel.name
                op.is_profile_drop = False
                op.is_hypermod_invoke = False

                gzm.matrix_basis = loc @ rot @ sca

                gzm.scale_basis = size * self.dim * self.obj.HC.geometry_gizmos_scale * gizmo_size

                gzm.color = white
                gzm.alpha = 0.05
                gzm.color_highlight = yellow
                gzm.alpha_highlight = 0.5

                edge_gizmos.append(gzm)

            return edge_gizmos

        self.gzms = []

        area_pointer = str(context.area.as_pointer())

        for bevel in context.window_manager.HC_pickhyperbevelsCOL:
            if bevel.area_pointer == area_pointer:
                edge_gizmos = create_edge_gizmos(bevel)

                self.gzms.append((edge_gizmos, bevel))

class GizmoGroupBend(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_bend"
    bl_label = "Bend"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    @classmethod
    def poll(cls, context):
        return True

    def setup(self, context):
        wm = context.window_manager
        self.bendCOL = wm.HC_bendCOL

        self.toggles = ['affect_children', 'is_kink', 'use_kink_edges', 'mirror_bend', 'remove_redundant', 'bisect', 'bend']
        self.toggle_states = [(b.index, toggle, getattr(b, toggle)) for b in self.bendCOL for toggle in self.toggles]

        self.create_bend_gizmos(context)

    def refresh(self, context):
        show_bend_HUD = context.window_manager.HC_bendshowHUD

        if show_bend_HUD:
            toggle_states = [(b.index, toggle, getattr(b, toggle)) for b in self.bendCOL for toggle in self.toggles]

            if toggle_states != self.toggle_states:
                self.toggle_states = toggle_states

                self.create_bend_gizmos(context)

    def draw_prepare(self, context):
        show_HUD = context.window_manager.HC_bendshowHUD
        gizmo_size = context.preferences.view.gizmo_size / 75

        has_angle = self.main and self.main[0].angle != 0
        is_kink = self.main and self.main[0].is_kink
        has_children = self.main and self.main[0].has_children
        mirror_bend = self.main and self.main[0].mirror_bend
        contain = self.main and self.main[0].contain

        supports_pos_limit = self.positive_limit and (self.positive_limit[0].bisect or self.positive_limit[0].bend)
        supports_neg_limit = self.negative_limit and (self.negative_limit[0].bisect or self.negative_limit[0].bend)
        has_any_bisect = (self.positive_bisect and self.positive_bisect[0].bisect) or (self.negative_bisect and self.negative_bisect[0].bisect)

        has_positive_limit_distance = self.positive_limit and self.positive_limit[0].limit_distance
        has_negative_limit_distance = self.negative_limit and self.negative_limit[0].limit_distance

        if is_modal(self):
            for gzm in self.gizmos:
                if gzm.bl_idname == "GIZMO_GT_dial_3d":
                    gzm.line_width = 1
                    gzm.arc_inner_factor = 0.4

                gzm.hide = not gzm.is_modal

        else:
            for gzm in self.gizmos:
                if gzm.bl_idname == "GIZMO_GT_dial_3d":
                    gzm.line_width = 2
                    gzm.arc_inner_factor = 0
                    gzm.draw_options = {'FILL_SELECT'}

                gzm.hide = False

        if self.offset:
            b, gzm = self.offset

            if show_HUD:
                gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

            if not gzm.hide:
                gzm.hide = not has_angle

        if self.negative_limit:
            b, gzm = self.negative_limit

            if show_HUD:
                gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

            if not gzm.hide:
                gzm.hide = not supports_neg_limit or mirror_bend or is_kink or not has_negative_limit_distance

        if self.positive_limit:
            b, gzm = self.positive_limit

            if show_HUD:
                gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

            if not gzm.hide:
                gzm.hide = not supports_pos_limit or is_kink or not has_positive_limit_distance

        if self.negative_y_contain:
            b, gzm = self.negative_y_contain

            if show_HUD:
                gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

            if not gzm.hide:
                gzm.hide = not contain or not b.limit_distance

        if self.positive_y_contain:
            b, gzm = self.positive_y_contain

            if show_HUD:
                gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

            if not gzm.hide:
                gzm.hide = not contain or not b.limit_distance

        if self.negative_z_contain:
            b, gzm = self.negative_z_contain

            if show_HUD:
                gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

            if not gzm.hide:
                gzm.hide = not contain or not b.limit_distance

        if self.positive_z_contain:
            b, gzm = self.positive_z_contain

            if show_HUD:
                gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

            if not gzm.hide:
                gzm.hide = not contain or not b.limit_distance

        button_count = 0

        if has_positive_limit_distance:
            button_count += 1

        if is_kink:
            button_count += 1

        if has_children:
            button_count += 1

        if is_kink or has_any_bisect:
            button_count += 1

        offset = -10 * (button_count - 1)

        if self.is_kink:
            b, gzm = self.is_kink

            if show_HUD:
                offset_button_gizmo(context, gzm, offset=(offset * gizmo_size, -100 * gizmo_size), loc2d=Vector(b.loc2d))

            if not gzm.hide:
                gzm.hide = not show_HUD or not has_positive_limit_distance

        if self.use_kink_edges:
            b, gzm = self.use_kink_edges

            if is_kink:
                offset += 20

                if show_HUD:
                    offset_button_gizmo(context, gzm, offset=(offset * gizmo_size, -100 * gizmo_size), loc2d=Vector(b.loc2d))

            if not gzm.hide:
                gzm.hide = not show_HUD or not is_kink

        if self.affect_children:
            b, gzm = self.affect_children

            if has_children:
                if button_count > 2:
                    offset += 20

                if show_HUD:
                    offset_button_gizmo(context, gzm, offset=(offset * gizmo_size, -100 * gizmo_size), loc2d=Vector(b.loc2d))

            if not gzm.hide:
                gzm.hide = not show_HUD or not has_children

        if self.remove_redundant:
            b, gzm = self.remove_redundant

            if is_kink or has_any_bisect:
                if button_count > 1:
                    offset += 20

                if show_HUD:
                    offset_button_gizmo(context, gzm, offset=(offset * gizmo_size, -100 * gizmo_size), loc2d=Vector(b.loc2d))

            if not gzm.hide:
                gzm.hide = not show_HUD or (not has_any_bisect and not is_kink)

        if self.mirror_bend:
            b, gzm = self.mirror_bend

            if show_HUD:
                offset_button_gizmo(context, gzm, offset=(0, -120 * gizmo_size), loc2d=Vector(b.loc2d))

            if not gzm.hide:
                gzm.hide = not show_HUD or is_kink or not (has_positive_limit_distance and has_negative_limit_distance)

        if self.positive_bisect:
            b, gzm = self.positive_bisect

            if show_HUD:
                offset_button_gizmo(context, gzm, offset=(30 * gizmo_size, -120 * gizmo_size), loc2d=Vector(b.loc2d))

            if not gzm.hide:
                gzm.hide = not show_HUD or is_kink or not has_positive_limit_distance

        if self.negative_bisect:
            b, gzm = self.negative_bisect

            if show_HUD:
                offset_button_gizmo(context, gzm, offset=(-30 * gizmo_size, -120 * gizmo_size), loc2d=Vector(b.loc2d))

            if not gzm.hide:
                gzm.hide = not show_HUD or mirror_bend or is_kink or not has_negative_limit_distance

        if self.positive_bend:
            b, gzm = self.positive_bend

            if show_HUD:
                offset_button_gizmo(context, gzm, offset=(50 * gizmo_size, -120 * gizmo_size), loc2d=Vector(b.loc2d))

            if not gzm.hide:
                gzm.hide = not show_HUD or is_kink or not has_positive_limit_distance

        if self.negative_bend:
            b, gzm = self.negative_bend

            if show_HUD:
                offset_button_gizmo(context, gzm, offset=(-50 * gizmo_size, -120 * gizmo_size), loc2d=Vector(b.loc2d))

            if not gzm.hide:
                gzm.hide = not show_HUD or mirror_bend or is_kink or not has_negative_limit_distance

        for b, gzms in self.gzms:
            b.is_highlight = any(gzm.is_highlight for gzm in gzms)

    def create_bend_gizmos(self, context):
        self.gizmos.clear()
        self.gzms = []

        self.main = None
        self.is_kink = None
        self.use_kink_edges = None
        self.mirror_bend = None
        self.remove_redundant = None
        self.affect_children = None

        self.offset = None

        self.negative_limit = None
        self.negative_bisect = None
        self.negative_bend = None

        self.positive_limit = None
        self.positive_bisect = None
        self.positive_bend = None

        self.negative_y_contain = None
        self.positive_y_contain = None
        self.negative_z_contain = None
        self.positive_z_contain = None

        area_pointer = str(context.area.as_pointer())

        for idx, b in enumerate(self.bendCOL):
            if area_pointer == b.area_pointer:
                if b.type == 'MAIN':

                    gzm = self.gizmos.new("GIZMO_GT_dial_3d")
                    op = gzm.target_set_operator("machin3.adjust_bend_angle")

                    gzm.matrix_basis = b.cmx @ Matrix.Rotation(radians(90), 4, 'X')

                    gzm.draw_options = {'FILL_SELECT'}
                    gzm.use_draw_value = True
                    gzm.use_draw_hover = False

                    gzm.line_width = 2
                    gzm.scale_basis = 1

                    gzm.color = (0.3, 1, 0.3)
                    gzm.alpha = 0.3
                    gzm.color_highlight = (0.5, 1, 0.5)
                    gzm.alpha_highlight = 1

                    self.main = (b, gzm)
                    self.gzms.append((b, [gzm]))

                    icon = 'MOD_MIRROR' if b.mirror_bend else 'RADIOBUT_OFF'
                    gzm = create_button_gizmo(self, context, operator='machin3.toggle_bend', args={'prop': 'mirror_bend'}, icon=icon, location=b.loc, scale=0.1)
                    self.mirror_bend = (b, gzm)
                    self.gzms[-1][-1].append(gzm)

                    icon = 'LAYER_USED' if b.is_kink else 'MOD_OUTLINE'
                    gzm = create_button_gizmo(self, context, operator='machin3.toggle_bend', args={'prop': 'is_kink'}, icon=icon, location=b.loc, scale=0.1)
                    self.is_kink = (b, gzm)
                    self.gzms[-1][-1].append(gzm)

                    icon = 'MOD_SIMPLIFY' if b.use_kink_edges else 'LAYER_USED'
                    gzm = create_button_gizmo(self, context, operator='machin3.toggle_bend', args={'prop': 'use_kink_edges'}, icon=icon, location=b.loc, scale=0.1)
                    self.use_kink_edges = (b, gzm)
                    self.gzms[-1][-1].append(gzm)

                    icon = 'COMMUNITY' if b.affect_children else 'LAYER_USED'
                    gzm = create_button_gizmo(self, context, operator='machin3.toggle_bend', args={'prop': 'affect_children'}, icon=icon, location=b.loc, scale=0.1)
                    self.affect_children = (b, gzm)
                    self.gzms[-1][-1].append(gzm)

                    icon = 'TRASH' if b.remove_redundant else 'LAYER_USED'
                    gzm = create_button_gizmo(self, context, operator='machin3.toggle_bend', args={'prop': 'remove_redundant'}, icon=icon, location=b.loc, scale=0.1)
                    self.remove_redundant = (b, gzm)
                    self.gzms[-1][-1].append(gzm)

                elif b.type == 'OFFSET':
                    gzm = self.gizmos.new("GIZMO_GT_arrow_3d")
                    gzm.target_set_operator("machin3.adjust_bend_offset")

                    gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

                    gzm.draw_style = 'NORMAL'

                    gzm.length = 0.3
                    gzm.scale_basis = 1

                    gzm.color = blue
                    gzm.alpha = 0.5
                    gzm.color_highlight = light_blue
                    gzm.alpha_highlight = 1

                    self.offset = (b, gzm)
                    self.gzms.append((b, [gzm]))

                elif b.type == 'POSITIVE':

                    gzm = self.gizmos.new("GIZMO_GT_arrow_3d")
                    op = gzm.target_set_operator("machin3.adjust_bend_limit")
                    op.side = b.type

                    gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

                    gzm.draw_style = 'BOX'

                    gzm.length = 0.1
                    gzm.scale_basis = 1

                    gzm.color = yellow
                    gzm.alpha = 0.5
                    gzm.color_highlight = light_yellow
                    gzm.alpha_highlight = 1

                    self.positive_limit = (b, gzm)
                    self.gzms.append((b, [gzm]))

                    icon = 'STRANDS' if b.bisect else 'LAYER_USED'
                    gzm = create_button_gizmo(self, context, operator='machin3.toggle_bend', args={'prop': 'positive_bisect'}, icon=icon, location=b.loc, scale=0.1)
                    self.positive_bisect = (b, gzm)
                    self.gzms[-1][-1].append(gzm)

                    icon = 'MOD_SIMPLEDEFORM' if b.bend else 'LAYER_USED'
                    gzm = create_button_gizmo(self, context, operator='machin3.toggle_bend', args={'prop': 'positive_bend'}, icon=icon, location=b.loc, scale=0.1)
                    self.positive_bend = (b, gzm)
                    self.gzms[-1][-1].append(gzm)

                elif b.type == 'NEGATIVE':

                    gzm = self.gizmos.new("GIZMO_GT_arrow_3d")
                    op = gzm.target_set_operator("machin3.adjust_bend_limit")
                    op.side = b.type

                    gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

                    gzm.draw_style = 'BOX'

                    gzm.length = 0.1
                    gzm.scale_basis = 1

                    gzm.color = yellow
                    gzm.alpha = 0.5
                    gzm.color_highlight = light_yellow
                    gzm.alpha_highlight = 1

                    self.negative_limit = (b, gzm)
                    self.gzms.append((b, [gzm]))

                    icon = 'STRANDS' if b.bisect else 'LAYER_USED'
                    gzm = create_button_gizmo(self, context, operator='machin3.toggle_bend', args={'prop': 'negative_bisect'}, icon=icon, location=b.loc, scale=0.1)
                    self.negative_bisect = (b, gzm)
                    self.gzms[-1][-1].append(gzm)

                    icon = 'MOD_SIMPLEDEFORM' if b.bend else 'LAYER_USED'
                    gzm = create_button_gizmo(self, context, operator='machin3.toggle_bend', args={'prop': 'negative_bend'}, icon=icon, location=b.loc, scale=0.1)
                    self.negative_bend = (b, gzm)
                    self.gzms[-1][-1].append(gzm)

                elif b.type == 'CONTAIN_NEGATIVE_Y':
                    gzm = self.gizmos.new("GIZMO_GT_arrow_3d")
                    op = gzm.target_set_operator("machin3.adjust_bend_containment")
                    op.side = b.type

                    gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

                    gzm.draw_style = 'BOX'

                    gzm.length = 0.1
                    gzm.scale_basis = 1

                    gzm.color = green
                    gzm.alpha = 0.5
                    gzm.color_highlight = light_green
                    gzm.alpha_highlight = 1

                    self.negative_y_contain = (b, gzm)
                    self.gzms.append((b, [gzm]))

                elif b.type == 'CONTAIN_POSITIVE_Y':
                    gzm = self.gizmos.new("GIZMO_GT_arrow_3d")
                    op = gzm.target_set_operator("machin3.adjust_bend_containment")
                    op.side = b.type

                    gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

                    gzm.draw_style = 'BOX'

                    gzm.length = 0.1
                    gzm.scale_basis = 1

                    gzm.color = green
                    gzm.alpha = 0.5
                    gzm.color_highlight = light_green
                    gzm.alpha_highlight = 1

                    self.positive_y_contain = (b, gzm)
                    self.gzms.append((b, [gzm]))

                elif b.type == 'CONTAIN_NEGATIVE_Z':
                    gzm = self.gizmos.new("GIZMO_GT_arrow_3d")
                    op = gzm.target_set_operator("machin3.adjust_bend_containment")
                    op.side = b.type

                    gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

                    gzm.draw_style = 'BOX'

                    gzm.length = 0.1
                    gzm.scale_basis = 1

                    gzm.color = blue
                    gzm.alpha = 0.5
                    gzm.color_highlight = light_blue
                    gzm.alpha_highlight = 1

                    self.negative_z_contain = (b, gzm)
                    self.gzms.append((b, [gzm]))

                elif b.type == 'CONTAIN_POSITIVE_Z':
                    gzm = self.gizmos.new("GIZMO_GT_arrow_3d")
                    op = gzm.target_set_operator("machin3.adjust_bend_containment")
                    op.side = b.type

                    gzm.matrix_basis = get_loc_matrix(b.loc) @ get_rot_matrix(b.rot)

                    gzm.draw_style = 'BOX'

                    gzm.length = 0.1
                    gzm.scale_basis = 1

                    gzm.color = blue
                    gzm.alpha = 0.5
                    gzm.color_highlight = light_blue
                    gzm.alpha_highlight = 1

                    self.positive_z_contain = (b, gzm)
                    self.gzms.append((b, [gzm]))

class GizmoGroupTest(bpy.types.GizmoGroup):
    bl_idname = "MACHIN3_GGT_test"
    bl_label = "Test Gizmo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        return False

    def setup(self, context):
        print("Test Gizmo setup")

        gzm = self.gizmos.new("GIZMO_GT_arrow_3d")

        for d in dir(gzm):
            print(d)

    def refresh(self, context):

        pass

    def draw_prepare(self, context):

        pass
