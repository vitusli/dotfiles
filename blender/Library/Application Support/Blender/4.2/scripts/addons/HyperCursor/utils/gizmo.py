import bpy
from bpy.types import GammaCrossSequence
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_origin_3d, region_2d_to_vector_3d
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_line_plane
from . cursor import get_cursor_2d
from . system import printd
from . object import is_valid_object

def print_shape():
    active = bpy.context.active_object

    if active:
        active.data.calc_loop_triangles()

        coords = [tuple(active.data.vertices[idx].co) for tri in active.data.loop_triangles for idx in tri.vertices]
        print(coords)

def is_modal(self):
    return any(gzm.is_modal for gzm in self.gizmos)

def create_button_gizmo(self, context, operator='', args={}, icon='MESH_CYLINDER', location='CURSOR', scale=0.13, offset=(0, 0)):
    gzm = self.gizmos.new("GIZMO_GT_button_2d")

    op = gzm.target_set_operator(operator)
    for prop, value in args.items():
        setattr(op, prop, value)

    gzm.icon = icon

    if location == 'CURSOR':
        gzm.matrix_basis = context.scene.cursor.matrix

    else:
        gzm.matrix_basis.translation = location

    gzm.scale_basis = scale

    if offset != (0, 0):
        offset_button_gizmo(context, gzm, Vector(offset))

    return gzm

def offset_button_gizmo(context, gzm, offset=(0, 0), loc2d=None):
    if not loc2d:
        loc2d = get_cursor_2d(context)

    loc2d_offset = loc2d + Vector(offset) * context.preferences.system.ui_scale

    view_origin = region_2d_to_origin_3d(context.region, context.region_data, loc2d_offset)
    view_dir = region_2d_to_vector_3d(context.region, context.region_data, loc2d_offset)

    button_3d = view_origin + view_dir * context.space_data.clip_start * 1.5

    gzm.matrix_basis = Matrix.Translation(button_3d)

def hide_gizmos(self, context, hypercursor=True, buttons=[], object=True, geometry=True, hud=True, debug=False):

    self.hidden_gizmos = {}

    if any([hypercursor, buttons, object, hud]):
        self.hidden_gizmos['SCENE'] = context.scene

    if any([geometry]):
        active = context.active_object

        if active and active.select_get() and active.HC.ishyper:
            self.hidden_gizmos['OBJECT'] = context.active_object

    if scene := self.hidden_gizmos.get('SCENE', None):
        hc = scene.HC

        if hypercursor:
            self.hidden_gizmos['show_gizmos'] = hc.show_gizmos
            hc.show_gizmos = False

        for button in buttons:
            prop =f"show_button_{button.lower()}"

            self.hidden_gizmos[prop] = getattr(hc, prop)
            setattr(hc, prop, False)

        if object:
            self.hidden_gizmos['show_object_gizmos'] = hc.show_object_gizmos
            hc.show_object_gizmos = False

        if hud:
            self.hidden_gizmos['draw_HUD'] = hc.draw_HUD
            hc.draw_HUD = False

    if obj := self.hidden_gizmos.get('OBJECT', None):
        hc = obj.HC

        if geometry and obj.type == 'MESH':
            self.hidden_gizmos['geometry_gizmos_show'] = hc.geometry_gizmos_show
            hc.geometry_gizmos_show = False

    if debug:
        printd(self.hidden_gizmos, name="hiding gizmos")

def restore_gizmos(self, debug=False):

    hidden = self if type(self) == dict else getattr(self, 'hidden_gizmos', None)

    if debug:
        printd(hidden, name="restoring gizmos")

    if hidden:
        if scene := hidden.get('SCENE', None):
            hc = scene.HC

            if 'show_gizmos' in hidden:
                hc.show_gizmos = hidden['show_gizmos']

            for button in ['HISTORY',  'FOCUS', 'SETTINGS', 'CAST', 'OBJECT']:
                prop =f"show_button_{button.lower()}"

                if prop in hidden:
                    setattr(hc, prop, hidden[prop])

            if 'show_object_gizmos' in hidden:
                hc.show_object_gizmos = hidden['show_object_gizmos']

            if 'draw_HUD' in hidden:
                hc.draw_HUD = hidden['draw_HUD']

            if 'draw_pipe_HUD' in hidden:
                hc.draw_pipe_HUD = hidden['draw_pipe_HUD']

        if obj := hidden.get('OBJECT', None):
            if is_valid_object(obj):
                hc = obj.HC

                if 'geometry_gizmos_show' in hidden:
                    hc.geometry_gizmos_show = hidden['geometry_gizmos_show']

            else:
                print("WARNING: Object has become invalid, can't restore geometry gizmos")

def get_highlighted_gizmo(gizmo_collection_property):
    for g in gizmo_collection_property:
        if g.show and g.is_highlight:
            return g
