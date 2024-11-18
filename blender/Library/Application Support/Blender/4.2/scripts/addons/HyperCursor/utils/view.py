import bpy
import bmesh
from typing import Tuple
from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_origin_3d, region_2d_to_vector_3d
from typing import Union
from . math import get_loc_matrix, get_sca_matrix
from . ui import get_scale

cache = {}

def focus_on_cursor(focusmode='SOFT', ignore_selection=False, cache_bm=False):
    scene = bpy.context.scene
    mode = bpy.context.mode

    if mode == 'OBJECT':

        if ignore_selection:
            sel = [obj for obj in bpy.context.selected_objects]

            for obj in sel:
                obj.select_set(False)

        empty = bpy.data.objects.new(name="focus", object_data=None)
        scene.collection.objects.link(empty)
        empty.select_set(True)

        empty.matrix_world = scene.cursor.matrix
        empty.scale *= scene.HC.focus_proximity

        bpy.ops.view3d.view_selected('INVOKE_DEFAULT' if focusmode == 'SOFT' else 'EXEC_DEFAULT')

        bpy.data.objects.remove(empty, do_unlink=True)

        if ignore_selection:
            for obj in sel:
                obj.select_set(True)

    elif mode == 'EDIT_MESH':
        global cache

        active = bpy.context.active_object
        mxi = active.matrix_world.inverted_safe()

        scale = scene.HC.focus_proximity
        loc = mxi @ scene.cursor.location

        if cache_bm and active.name in cache:
            bm = cache[active.name]

        else:
            bm = bmesh.from_edit_mesh(active.data)
            bm.normal_update()
            bm.verts.ensure_lookup_table()

        if cache_bm:
            cache[active.name] = bm

        sel_verts = [v for v in bm.verts if v.select]
        sel_edges = [e for e in bm.edges if e.select]
        sel_faces = [f for f in bm.faces if f.select]

        if ignore_selection:
            for v in sel_verts:
                v.select_set(False)

            bm.select_flush(False)

        coords = (Vector((-1, 1, -1)), Vector((1, 1, -1)), Vector((1, -1, -1)), Vector((-1, -1, -1)),
                  Vector((-1, 1, 1)), Vector((1, 1, 1)), Vector((1, -1, 1)), Vector((-1, -1, 1)))

        verts = []

        for co in coords:
            v = bm.verts.new(get_loc_matrix(loc) @ get_sca_matrix(scale * mxi.to_scale()) @ co)
            v.select_set(True)
            verts.append(v)

        indices = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]

        for ids in indices:
            e = bm.edges.new([verts[i] for i in ids])
            e.select_set(True)

        indices = [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0), (0, 1, 2, 3), (4, 7, 6, 5)]

        for ids in indices:
            f = bm.faces.new([verts[i] for i in ids])
            f.select_set(True)

        bpy.ops.view3d.view_selected('INVOKE_DEFAULT' if focusmode == 'SOFT' else 'EXEC_DEFAULT')

        for v in verts:
            bm.verts.remove(v)

        if ignore_selection:
            for v in sel_verts:
                v.select_set(True)

            for e in sel_edges:
                e.select_set(True)

            for f in sel_faces:
                f.select_set(True)

def clear_focus_cache():
    global cache

    cache = {}

def get_view_bbox(context, bbox, border_gap=200):
    scale = get_scale(context)
    gap = border_gap * scale

    coords = []

    for co in bbox:
        coords.append(get_location_2d(context, co, default=Vector((context.region.width / 2, context.region.height / 2))))
    xmin = round(min(context.region.width - gap, max(gap, min(coords, key=lambda x: x[0])[0])))
    xmax = round(min(context.region.width - gap, max(gap, max(coords, key=lambda x: x[0])[0])))

    ymin = round(min(context.region.height - gap, max(gap, min(coords, key=lambda x: x[1])[1])))
    ymax = round(min(context.region.height - gap, max(gap, max(coords, key=lambda x: x[1])[1])))

    return [Vector((xmin, ymin)), Vector((xmax, ymin)), Vector((xmax, ymax)), Vector((xmin, ymax))]

def get_view_origin_and_dir(context, coord=None) -> Tuple[Vector, Vector]:
    if not coord:
        coord = Vector((context.region.width / 2, context.region.height / 2))

    view_origin = region_2d_to_origin_3d(context.region, context.region_data, coord)
    view_dir = region_2d_to_vector_3d(context.region, context.region_data, coord)

    return view_origin, view_dir

def ensure_visibility(context, obj: Union[bpy.types.Object, list[bpy.types.Object]], view_layer=True, local_view=True, unhide=True):
    view = context.space_data

    objects = obj if type(obj) == list else [obj]

    if view_layer:
        for obj in objects:
            if obj.name not in context.view_layer.objects:
                context.collection.objects.link(obj)
                obj.select_set(False)  # it's automatically selected when being linked, but if we actually want this, we'll do it intentionally

    if local_view:
        if view.local_view:
            for obj in objects:
                obj.local_view_set(view, True)

    if unhide:
        for obj in objects:
            if not obj.visible_get():
                obj.hide_set(False)

def get_location_2d(context, co3d, default=(0, 0), debug=False):
    if default == 'OFF_SCREEN':
        default = Vector((-1000, -1000))
    co2d = Vector(round(i) for i in location_3d_to_region_2d(context.region, context.region_data, co3d, default=default))
    if debug:
        print(tuple(co3d), "is", tuple(co2d))

    return co2d
