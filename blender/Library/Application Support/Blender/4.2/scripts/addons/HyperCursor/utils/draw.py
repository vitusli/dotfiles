import bpy
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Vector, Matrix, Quaternion
from math import sin, cos, pi
import gpu
from gpu_extras.batch import batch_for_shader
import blf
from . import math
from . math import get_world_space_normal
from . tools import get_active_tool
from . registration import get_prefs
from .. colors import red, green, blue, yellow, white

def get_builtin_shader_name(name):
    if bpy.app.version >= (4, 0, 0):
        return name
    else:
        return f"3D_{name}"

def draw_point(co, mx=Matrix(), color=(1, 1, 1), size=6, alpha=1, xray=True, modal=True, screen=False):
    def draw():
        shader = gpu.shader.from_builtin(get_builtin_shader_name('UNIFORM_COLOR'))
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.point_size_set(size)

        batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co]})
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_points(coords, indices=None, mx=Matrix(), color=(1, 1, 1), size=6, alpha=1, xray=True, modal=True, screen=False):
    def draw():
        shader = gpu.shader.from_builtin(get_builtin_shader_name('UNIFORM_COLOR'))
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')
        gpu.state.point_size_set(size)

        if indices:
            if mx != Matrix():
                batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co for co in coords]}, indices=indices)
            else:
                batch = batch_for_shader(shader, 'POINTS', {"pos": coords}, indices=indices)

        else:
            if mx != Matrix():
                batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co for co in coords]})
            else:
                batch = batch_for_shader(shader, 'POINTS', {"pos": coords})

        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_line(coords, indices=None, mx=Matrix(), color=(1, 1, 1), alpha=1, width=1, xray=True, modal=True, screen=False):
    def draw():
        nonlocal indices

        if indices is None:
            indices = [(i, i + 1) for i in range(0, len(coords)) if i < len(coords) - 1]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_lines(coords, indices=None, mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, xray=True, modal=True, screen=False):
    def draw():
        nonlocal indices

        if not indices:
            indices = [(i, i + 1) for i in range(0, len(coords), 2)]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_vector(vector, origin=Vector((0, 0, 0)), mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, fade=False, normal=False, xray=True, modal=True, screen=False):
    def draw():
        if normal:
            coords = [mx @ origin, mx @ origin + get_world_space_normal(vector, mx)]
        else:
            coords = [mx @ origin, mx @ origin + mx.to_3x3() @ vector]

        colors = ((*color, alpha), (*color, alpha / 10 if fade else alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": coords, "color": colors})
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_vectors(vectors, origins, mx=Matrix(), color=(1, 1, 1), width=1, alpha=1, fade=False, normal=False, xray=True, modal=True, screen=False):
    def draw():
        coords = []
        colors = []

        for v, o in zip(vectors, origins):
            coords.append(mx @ o)

            if normal:
                coords.append(mx @ o + get_world_space_normal(v, mx))
            else:
                coords.append(mx @ o + mx.to_3x3() @ v)

            colors.extend([(*color, alpha), (*color, alpha / 10 if fade else alpha)])

        indices = [(i, i + 1) for i in range(0, len(coords), 2)]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": coords, "color": colors})
        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_circle(loc=Vector(), rot=Quaternion(), radius=100, segments='AUTO', width=1, color=(1, 1, 1), alpha=1, xray=True, modal=True, screen=False):
    def draw():
        nonlocal segments

        if segments == 'AUTO':
            segments = max(int(radius), 16)

        else:
            segments = max(segments, 16)

        indices = [(i, i + 1) if i < segments - 1 else (i, 0) for i in range(segments)]

        coords = []

        for i in range(segments):

            theta = 2 * pi * i / segments

            x = radius * cos(theta)
            y = radius * sin(theta)

            coords.append(Vector((x, y, 0)))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        if len(loc) == 2:
            mx = Matrix()
            mx.col[3] = loc.resized(4)
            batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)

        else:
            mx = Matrix.LocRotScale(loc, rot, Vector.Fill(3, 1))
            batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)

        batch.draw(shader)

    if modal:
        draw()

    elif screen:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_cross_3d(co, mx=Matrix(), color=(1, 1, 1), width=1, length=1, alpha=1, xray=True, modal=True):
    def draw():
        x = Vector((1, 0, 0))
        y = Vector((0, 1, 0))
        z = Vector((0, 0, 1))

        coords = [(co - x) * length, (co + x) * length,
                  (co - y) * length, (co + y) * length,
                  (co - z) * length, (co + z) * length]

        indices = [(0, 1), (2, 3), (4, 5)]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_tris(coords, indices=None, mx=Matrix(), color=(1, 1, 1), alpha=1, xray=True, modal=True):
    def draw():

        shader = gpu.shader.from_builtin(get_builtin_shader_name('UNIFORM_COLOR'))
        shader.bind()
        shader.uniform_float("color", (*color, alpha))

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA' if alpha < 1 else 'NONE')

        if mx != Matrix():
            batch = batch_for_shader(shader, 'TRIS', {"pos": [mx @ co for co in coords]}, indices=indices)

        else:
            batch = batch_for_shader(shader, 'TRIS', {"pos": coords}, indices=indices)

        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_mesh_wire(batch, color=(1, 1, 1), width=1, alpha=1, xray=True, modal=True):
    def draw():
        nonlocal batch
        coords, indices = batch

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        b = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
        b.draw(shader)

        del shader
        del b

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_bbox(bbox, mx=Matrix(), color=(1, 1, 1), corners=0, width=1, alpha=1, xray=True, modal=True):
    def draw():
        if corners:
            length = corners

            coords = [bbox[0], bbox[0] + (bbox[1] - bbox[0]) * length, bbox[0] + (bbox[3] - bbox[0]) * length, bbox[0] + (bbox[4] - bbox[0]) * length,
                      bbox[1], bbox[1] + (bbox[0] - bbox[1]) * length, bbox[1] + (bbox[2] - bbox[1]) * length, bbox[1] + (bbox[5] - bbox[1]) * length,
                      bbox[2], bbox[2] + (bbox[1] - bbox[2]) * length, bbox[2] + (bbox[3] - bbox[2]) * length, bbox[2] + (bbox[6] - bbox[2]) * length,
                      bbox[3], bbox[3] + (bbox[0] - bbox[3]) * length, bbox[3] + (bbox[2] - bbox[3]) * length, bbox[3] + (bbox[7] - bbox[3]) * length,
                      bbox[4], bbox[4] + (bbox[0] - bbox[4]) * length, bbox[4] + (bbox[5] - bbox[4]) * length, bbox[4] + (bbox[7] - bbox[4]) * length,
                      bbox[5], bbox[5] + (bbox[1] - bbox[5]) * length, bbox[5] + (bbox[4] - bbox[5]) * length, bbox[5] + (bbox[6] - bbox[5]) * length,
                      bbox[6], bbox[6] + (bbox[2] - bbox[6]) * length, bbox[6] + (bbox[5] - bbox[6]) * length, bbox[6] + (bbox[7] - bbox[6]) * length,
                      bbox[7], bbox[7] + (bbox[3] - bbox[7]) * length, bbox[7] + (bbox[4] - bbox[7]) * length, bbox[7] + (bbox[6] - bbox[7]) * length]

            indices = [(0, 1), (0, 2), (0, 3),
                       (4, 5), (4, 6), (4, 7),
                       (8, 9), (8, 10), (8, 11),
                       (12, 13), (12, 14), (12, 15),
                       (16, 17), (16, 18), (16, 19),
                       (20, 21), (20, 22), (20, 23),
                       (24, 25), (24, 26), (24, 27),
                       (28, 29), (28, 30), (28, 31)]

        else:
            coords = bbox
            indices = [(0, 1), (1, 2), (2, 3), (3, 0),
                       (4, 5), (5, 6), (6, 7), (7, 4),
                       (0, 4), (1, 5), (2, 6), (3, 7)]

        gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
        gpu.state.blend_set('ALPHA')

        shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        shader.uniform_float("color", (*color, alpha))
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("viewportSize", gpu.state.scissor_get()[2:])
        shader.bind()

        batch = batch_for_shader(shader, 'LINES', {"pos": [mx @ co for co in coords]}, indices=indices)
        batch.draw(shader)

    if modal:
        draw()

    else:
        bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def draw_init(self):
    self.offset = 0

def get_text_dimensions(context, text='', size=12):

    from . ui import get_scale
    scale = get_scale(context)

    font = 1
    fontsize = int(size * scale)

    blf.size(font, fontsize)
    return blf.dimensions(font, text)

def draw_label(context, title='', coords=None, offset=0, center=True, size=12, color=(1, 1, 1), alpha=1):
    if not coords:
        region = context.region
        width = region.width / 2
        height = region.height / 2
    else:
        width, height = coords

    from . ui import get_scale
    scale = get_scale(context)

    shadow = get_prefs().modal_hud_shadow

    font = 1
    fontsize = int(size * scale)

    if shadow:
        shadow_blur = int(get_prefs().modal_hud_shadow_blur)
        shadow_offset = round(get_prefs().modal_hud_shadow_offset * scale)

    blf.size(font, fontsize)
    blf.color(font, *color, alpha)

    if shadow:
        blf.enable(font, blf.SHADOW)
        blf.shadow(font, shadow_blur, 0, 0, 0, 1)
        blf.shadow_offset(font, shadow_offset, -shadow_offset)

    if center:
        dims = blf.dimensions(font, title)
        blf.position(font, width - (dims[0] / 2), height - (offset * scale), 1)

    else:
        blf.position(font, width, height - (offset * scale), 1)

    blf.draw(font, title)

    if shadow:
        blf.disable(font, blf.SHADOW)

    return blf.dimensions(font, title)

def draw_fading_label(context, text='', x=None, y=100, gap=18, center=True, size=12, color=(1, 1, 1), alpha=1, move_y=0, time=5, delay=1, cancel=''):
    scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

    if x is None:
        x = (context.region.width / 2)

    if isinstance(text, list):

        coords = (x, y + gap * (len(text) - 1) * scale)

        for idx, t in enumerate(text):
            line_coords = (coords[0], coords[1] - (idx * gap * scale))
            line_color = color if isinstance(color, tuple) else color[idx if idx < len(color) else len(color) - 1]
            line_alpha = alpha if (isinstance(alpha, int) or isinstance(alpha, float)) else alpha[idx if idx < len(alpha) else len(alpha) - 1]
            line_move = int(move_y + (idx * gap)) if move_y > 0 else 0
            line_time = time + idx * delay
            
            bpy.ops.machin3.draw_hyper_cursor_label(text=t, coords=line_coords, center=center, size=size, color=line_color, alpha=line_alpha, move_y=line_move, time=line_time, cancel=cancel)

    else:
        coords = (x, y)

        bpy.ops.machin3.draw_hyper_cursor_label(text=text, coords=coords, center=center, size=size, color=color, alpha=alpha, move_y=move_y, time=time, cancel=cancel)

def draw_hyper_cursor_HUD(context):
    view = context.space_data

    from .. ui.gizmos import HUD_offset2d
    from . ui import is_on_screen

    if view.show_gizmo and context.scene.HC.show_gizmos and view.overlay.show_overlays:
        hc = context.scene.HC
        ui_scale = context.preferences.system.ui_scale

        active_tool = get_active_tool(context).idname

        if active_tool in ['machin3.tool_hyper_cursor', 'machin3.tool_hyper_cursor_simple'] and hc.show_gizmos and (hc.draw_HUD or hc.draw_pipe_HUD):
            coords = Vector(context.window_manager.HC_cursor2d)

            if is_on_screen(context, coords):
                if active_tool == 'machin3.tool_hyper_cursor':
                    offset = Vector(HUD_offset2d)

                    if hc.draw_pipe_HUD:
                        dims = draw_label(context, "Pipe Curve ", coords=coords + offset, center=False, size=12, color=blue, alpha=1)
                    else:
                        dims = (0, 0)

                    if hc.draw_HUD:
                        offset += Vector((dims[0], 0))

                        if hc.use_world:
                            dims = draw_label(context, "World ", coords=coords + offset, center=False, size=12, color=green, alpha=1)
                        else:
                            dims = (0, 0)

                        is_current_stored = hc.historyCOL and math.compare_matrix(context.scene.cursor.matrix, hc.historyCOL[hc.historyIDX].mx)

                        if (hc.historyCOL and hc.show_button_history) or is_current_stored:

                            offset += Vector((dims[0], 0))
                            title = f"{hc.historyIDX + 1} "

                            color, alpha = (green, 1) if is_current_stored else (white, 0.3)
                            dims = draw_label(context, title, coords=coords + offset, center=False, size=12, color=color, alpha=alpha)

                            offset += Vector((dims[0], 0))
                            title = f"/ {len(hc.historyCOL)} "
                            dims = draw_label(context, title, coords=coords + offset, center=False, size=12, color=white, alpha=0.3)

                            if hc.auto_history:
                                offset += Vector((dims[0], 0))
                                draw_label(context, title="Auto History", coords=coords + offset, center=False, size=12, color=green, alpha=1)

                        if is_current_stored:
                            draw_circle(coords, radius=10 * ui_scale, width=2 * ui_scale if active_tool == 'machin3.tool_hyper_cursor' else 1, segments=64, color=(0, 0.8, 0), alpha=1)

def draw_hyper_cursor_VIEW3D(context):
    view = context.space_data

    if view.show_gizmo and context.scene.HC.show_gizmos and view.overlay.show_overlays:
        active_tool = get_active_tool(context).idname

        if context.scene.HC.draw_HUD:
            if active_tool == 'machin3.tool_hyper_cursor':
                if not view.overlay.show_cursor:
                    view.overlay.show_cursor = True

            elif active_tool == 'machin3.tool_hyper_cursor_simple':
                if view.overlay.show_cursor:
                    view.overlay.show_cursor = False

        if context.scene.HC.draw_cursor_axes:
            if active_tool == 'machin3.tool_hyper_cursor_simple':
                gizmo_scale = context.window_manager.HC_gizmo_scale

                axes = [(Vector((1, 0, 0)), red), (Vector((0, 1, 0)), green), (Vector((0, 0, 1)), blue)]

                cmx = context.scene.cursor.matrix
                corigin = cmx.decompose()[0]

                for axis, color in axes:
                    coords = [corigin + cmx.to_3x3() @ axis * gizmo_scale * 0.1, corigin + cmx.to_3x3() @ axis * gizmo_scale * 0.5]
                    draw_line(coords, color=color, width=2, alpha=1)
    else:
        if not view.overlay.show_cursor:
            view.overlay.show_cursor = True

get_zoom_factor = None

def draw_cursor_history(context):
    global get_zoom_factor

    view = context.space_data

    if view.overlay.show_overlays:
        if get_active_tool(context).idname in ['machin3.tool_hyper_cursor', 'machin3.tool_hyper_cursor_simple']:

            if not get_zoom_factor:
                from HyperCursor.utils.ui import get_zoom_factor

            hc = context.scene.HC

            if hc.historyCOL and hc.draw_history:

                locations = [entry.location for entry in hc.historyCOL.values()]

                active_location = locations[hc.historyIDX]

                inactive_locations = locations.copy()
                inactive_locations.pop(hc.historyIDX)

                draw_line(locations, width=1, alpha=0.2, modal=True)

                if inactive_locations:
                    draw_points(inactive_locations, size=4, alpha=0.5, modal=True)

                draw_point(active_location, alpha=1, color=yellow, modal=True)

                axes = [(Vector((1, 0, 0)), red), (Vector((0, 1, 0)), green), (Vector((0, 0, 1)), blue)]

                orientations = [entry.rotation for entry in hc.historyCOL.values()]

                active_orientation = orientations[hc.historyIDX]

                inactive_orientations = orientations.copy()
                inactive_orientations.pop(hc.historyIDX)

                for axis, color in axes:

                    size = 1
                    coords = []

                    for origin, orientation in zip(inactive_locations, inactive_orientations):
                        factor = get_zoom_factor(context, origin, scale=20, ignore_obj_scale=True)

                        coords.append(origin + (orientation @ axis).normalized() * size * factor * 0.1)
                        coords.append(origin + (orientation @ axis).normalized() * size * factor)

                    if coords:
                        draw_lines(coords, color=color, alpha=0.6)

                    size = 1.75
                    coords = []

                    factor = get_zoom_factor(context, active_location, scale=20, ignore_obj_scale=True)

                    coords.append(active_location + (active_orientation @ axis).normalized() * size * factor * 0.1)
                    coords.append(active_location + (active_orientation @ axis).normalized() * size * factor)

                    draw_line(coords, color=color, width=3, alpha=1)

def draw_cursor_history_names(context):
    view = context.space_data

    if view.overlay.show_overlays:
        if get_active_tool(context).idname in ['machin3.tool_hyper_cursor', 'machin3.tool_hyper_cursor_simple']:
            hc = context.scene.HC

            from . ui import get_scale
            scale = get_scale(context)

            gizmo_size = context.preferences.view.gizmo_size / 75

            offset = Vector((10, 5)) * scale

            if hc.historyCOL and hc.draw_history:

                locations = [(entry, location_3d_to_region_2d(context.region, context.region_data, entry.location)) for entry in hc.historyCOL.values()]

                labels = {}

                for idx, (entry, loc) in enumerate(locations):

                    if loc:

                        inted = tuple([int(co) for co in loc])

                        if inted in labels:
                            labels[inted].append(entry)
                        else:
                            labels[inted] = [entry]

                        entry.location2d = inted

                    else:
                        entry.gzm_location2d = Vector((-1000, -1000))

                for loc, entries in labels.items():

                    voffset = 0

                    for idx, entry in enumerate(entries):

                        color, size, alpha = (yellow, 14, 1) if entry.index == hc.historyIDX else (white, 10, 0.5)

                        coords = Vector(loc) + offset + Vector((0, voffset))
                        dims = draw_label(context, title=entry.name, coords=coords, center=False, size=size, color=color, alpha=alpha)

                        voffset -= 14 * scale * gizmo_size

                        gap = 7 * gizmo_size
                        gzm_location2d = coords + Vector((dims[0], dims[1] / 2)) + Vector((gap, 0)) * scale

                        entry.gzm_location2d = gzm_location2d

def draw_split_row(self, layout, prop='prop', text='', label='Label', factor=0.2, align=True, toggle=True, expand=True, info=None, warning=None):
    row = layout.row(align=align)
    split = row.split(factor=factor, align=align)
    
    text = text if text else str(getattr(self, prop)) if str(getattr(self, prop)) in ['True', 'False'] else ''
    split.prop(self, prop, text=text, toggle=toggle, expand=expand)

    if label:
        split.label(text=label)

    if info:
        split.label(text=info, icon='INFO')

    if warning:
        split.label(text=warning, icon='ERROR')

    return row
