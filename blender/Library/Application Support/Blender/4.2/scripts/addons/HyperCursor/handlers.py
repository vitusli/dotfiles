import bpy
from bpy.app.handlers import persistent
from . utils.application import delay_execution
from . utils.math import compare_matrix
from . utils.history import add_history_entry
from . utils.object import get_active_object, get_visible_objects
from . utils.draw import draw_hyper_cursor_HUD, draw_cursor_history, draw_cursor_history_names, draw_fading_label
from . utils.registration import get_addon, get_prefs
from . utils.workspace import get_assetbrowser_area, get_3dview_area, get_window_region_from_area, get_assetbrowser_space
from . utils.gizmo import restore_gizmos
from . utils.asset import get_asset_import_method, set_asset_import_method
from . colors import red, yellow
from time import time

global_debug = False

def ensure_gizmo_and_HUD_drawing():
    global global_debug

    debug = global_debug

    if debug:
        print("  gizmo and HUD drawing")

    scene = getattr(bpy.context, 'scene', None)

    if scene:
        hc = scene.HC

        if not hc.show_object_gizmos:
            hc.show_object_gizmos = True

        if not hc.draw_HUD:
            hc.draw_HUD = True

hypercursorHUD = None
hypercursorVIEW3D = None
cursorhistoryVIEW3D = None
cursorhistoryHUD = None

def manage_HUD_and_VIEW3D_drawing():
    global global_debug, hypercursorHUD, hypercursorVIEW3D, cursorhistoryVIEW3D, cursorhistoryHUD

    debug = global_debug

    if debug:
        print("  HUD and VIEW3D drawing")

    scene = getattr(bpy.context, 'scene', None)

    if scene:
        hc = scene.HC

        if hypercursorHUD and "RNA_HANDLE_REMOVED" in str(hypercursorHUD):
            hypercursorHUD = None

        wm = bpy.context.window_manager

        if hc.historyCOL or hc.use_world or hc.draw_pipe_HUD:
            if not hypercursorHUD:
                if debug:
                    print("   adding new cursor HUD handler")

                hypercursorHUD = bpy.types.SpaceView3D.draw_handler_add(draw_hyper_cursor_HUD, (bpy.context,), 'WINDOW', 'POST_PIXEL')

        elif hypercursorHUD:
            if debug:
                print("   removing old cursor HUD handler")

            bpy.types.SpaceView3D.draw_handler_remove(hypercursorHUD, 'WINDOW')
            hypercursorHUD = None

        if hc.draw_pipe_HUD and not wm.HC_piperadiiCOL:
            if hidden := hc.get('hidden_gizmos'):
                if debug:
                    print("   restoring HC gizmo settings, after undoing Pipe Creation")

                else:
                    print("WARNING: Restoring HC gizmo settings, after undoing Pipe Creation")

                restore_gizmos(dict(hidden))

        if cursorhistoryVIEW3D and "RNA_HANDLE_REMOVED" in str(cursorhistoryVIEW3D):
            cursorhistoryVIEW3D = None

        if cursorhistoryHUD and "RNA_HANDLE_REMOVED" in str(cursorhistoryHUD):
            cursorhistoryHUD = None

        if hc.historyCOL and hc.draw_history:
            if not cursorhistoryVIEW3D:
                if debug:
                    print("   adding new history lines VIEW3D handler")

                cursorhistoryVIEW3D = bpy.types.SpaceView3D.draw_handler_add(draw_cursor_history, (bpy.context,), 'WINDOW', 'POST_VIEW')

            if not cursorhistoryHUD:
                if debug:
                    print("   adding new history lines HUD handler")

                cursorhistoryHUD = bpy.types.SpaceView3D.draw_handler_add(draw_cursor_history_names, (bpy.context,), 'WINDOW', 'POST_PIXEL')

        else:
            if cursorhistoryVIEW3D:
                if debug:
                    print("   removing old history lines VIEW3D handler")

                bpy.types.SpaceView3D.draw_handler_remove(cursorhistoryVIEW3D, 'WINDOW')
                cursorhistoryVIEW3D = None

            if cursorhistoryHUD:
                if debug:
                    print("   removing old history lines HUD handler")

                bpy.types.SpaceView3D.draw_handler_remove(cursorhistoryHUD, 'WINDOW')
                cursorhistoryHUD = None

def manage_legacy_updates():
    global global_debug

    debug = global_debug

    if debug:
        print("  legacy updates")

def manage_auto_history():
    global global_debug

    debug = global_debug

    if debug:
        print("  auto history")

    scene = getattr(bpy.context, 'scene', None)

    if scene:
        hc = scene.HC

        if hc.auto_history and hc.track_history:

            hmx = hc.historyCOL[hc.historyIDX].mx if hc.historyCOL else None
            cmx = scene.cursor.matrix

            if hmx is None or not compare_matrix(cmx, hmx, 4):
                add_history_entry(debug=debug)

mode_history = ()
event_history = ()

def manage_mode_history():
    global global_debug, mode_history

    debug = global_debug

    if debug:
        print("  mode history")

    if C := bpy.context:
        if debug:
            print("   mode:", C.mode)
        
        if (mode_history and mode_history[-1][0] != C.mode) or not mode_history:
            history = list(mode_history)
            history.append((C.mode, time()))

            if len(history) > 3:
                history = history[-3:]

            mode_history = history

        if debug:
            print("   history:", [h for h in mode_history])

def manage_undo_redo_history():
    global global_debug, event_history

    debug = global_debug

    if debug:
        print("  event history")

    history = list(event_history)
    history.append(('UNDO/REDO', time()))

    if len(history) > 3:
        history = history[-3:]

    event_history = tuple(history)

prev_active = None

def manage_redoCOL_selection_sync():
    global global_debug, prev_active

    debug = global_debug

    if debug:
        print("  redoCOL selection sync")

    scene = getattr(bpy.context, 'scene', None)

    if scene:
        hc = scene.HC
        active = get_active_object(bpy.context)

        if active and active != prev_active:
            prev_active = active

            if active.HC.assetpath:
                redoCOL = hc.redoaddobjCOL

                if active.HC.assetpath in redoCOL:
                    index = list(redoCOL).index(redoCOL[active.HC.assetpath])

                    if debug:
                        print("   new active is", active.name)
                        print("   index is:", index)

                    if hc.redoaddobjIDX != index:
                        hc.redoaddobjIDX = index

def manage_geo_gizmos():
    global global_debug

    debug = global_debug

    if debug:
       print("  geo gizmos")

    active = get_active_object(bpy.context)

    if active and active.mode == 'OBJECT' and active.type == 'MESH' and active.HC.ishyper:

        if len(active.data.polygons) > active.HC.geometry_gizmos_show_limit:
            active.HC.geometry_gizmos_show = False

        elif active.HC.geometry_gizmos_edit_mode == 'EDIT':
            if active.HC.objtype == 'CUBE' and len(active.data.polygons) > active.HC.geometry_gizmos_show_cube_limit:
                active.HC.geometry_gizmos_edit_mode = 'SCALE'

            elif active.HC.objtype == 'CYLINDER' and len(active.data.edges) > active.HC.geometry_gizmos_show_cylinder_limit:
                active.HC.geometry_gizmos_edit_mode = 'SCALE'

        if dm := getattr(active, 'DM', None):
            if dm.isdecal:
                active.HC.ishyper = False

last_op_global = None

def manage_asset_drop_takeover():
    global global_debug, last_op_global, was_asset_drop_takeover_executed

    debug = global_debug

    if debug:
        print("  asset drop takeover")

    C = bpy.context
    p = get_prefs()

    if C.mode == 'OBJECT':

        if p.avoid_append_reuse_import_method:

            workspace = getattr(C, 'workspace', None)

            if workspace:
                skip_names = [name.strip() for name in p.skip_changing_import_method.split(',')]

                if workspace.name not in skip_names:
                    area = get_assetbrowser_area(C)
                    screen_areas = [area for area in C.screen.areas]

                    if area in screen_areas:
                        space = get_assetbrowser_space(area)

                        if space.params:
                            if import_method := get_asset_import_method(space.params) != 'APPEND':
                                if debug:
                                    print(f"   changing import method {import_method} to APPEND")

                                set_asset_import_method(space.params, 'APPEND')

                                if not debug:
                                    area = get_3dview_area(C)

                                    if area:
                                        region, region_data = get_window_region_from_area(area)

                                        text = ["HyperCursor currently enforces the APPEND over the APPEND_REUSE or LINK asset import types",
                                                "ℹℹ This can be disabled in the addon preferences ℹℹ",
                                                "While APPEND_REUSE can work just fine, it can also cause problems if linked mesh data blocks have been adjusted on previous Insets, and are then going to be reused on new Insets of the same type."]

                                        with C.temp_override(area=area, region=region, region_data=region_data):
                                            draw_fading_label(C, text=text, y=100, color=[red, red, yellow], alpha=1, time=10)

        operators = C.window_manager.operators
        active = active if (active := get_active_object(C)) and (active.HC.ishyperasset or active.type == 'CURVE') else None

        if active and operators:
            last_op = operators[-1]

            if last_op != last_op_global:
                last_op_global = last_op

                if last_op.bl_idname in ["OBJECT_OT_transform_to_mouse", "OBJECT_OT_add_named"]:

                    if debug:
                        print(f"   initiating takevoer, as last op is {last_op.bl_idname}")

                    area = get_assetbrowser_area(C)
                    screen_areas = [area for area in C.screen.areas]

                    if area in screen_areas:
                        if debug:
                            print("    setting asset drop props")

                        with C.temp_override(area=area):
                            bpy.ops.machin3.set_drop_asset_props()

                        area = get_3dview_area(C)
                        region, region_data = get_window_region_from_area(area)

                        if active.HC.ishyperasset:
                            if debug:
                                print("    AddObjectAtCursor() takeover")

                            with C.temp_override(area=area, region=region, region_data=region_data):
                                bpy.ops.machin3.add_object_at_cursor('INVOKE_DEFAULT', is_drop=True, type='ASSET')

                        elif active.type == 'CURVE':
                            if debug:
                                print("    AddCurveAsset() takeover")

                            with C.temp_override(area=area, region=region, region_data=region_data):
                                bpy.ops.machin3.add_curve_asset('INVOKE_DEFAULT')

                    else:
                        if debug:
                            print("    second Blender Window is open, preventing the HyperCursor takeover")

                        else:
                            from . utils.ui import popup_message
                            popup_message("Close this Blender Window, or HyperCursor can't take over after the asset drop")

meshmachine = None
decalmachine = None
was_asset_drop_cleanup_executed = False

def manage_asset_drop_cleanup():
    global global_debug, was_asset_drop_cleanup_executed

    debug = global_debug

    if debug:
        print("  HC asset drop cleanup")

    if was_asset_drop_cleanup_executed:
        if debug:
            print("   skipping second (duplicate) run")

        was_asset_drop_cleanup_executed = False
        return

    if debug:
        print("   checking for asset drop cleanup")

    global meshmachine, decalmachine

    if meshmachine is None:
        meshmachine = get_addon('MESHmachine')[0]

        if meshmachine:
            import MESHmachine

            if 'manage_asset_drop_cleanup' in dir(MESHmachine.handlers):
                meshmachine = False

                if debug:
                    print("    the installed MESHmachine already manages the asset drop itself, setting MM to False")

    if decalmachine is None:
        decalmachine = get_addon('DECALmachine')[0]

        if decalmachine:
            import DECALmachine

            if 'manage_asset_drop_cleanup' in dir(DECALmachine.handlers):
                decalmachine = False

                if debug:
                    print("    the installed DECALmachine already manages the asset drop itself, setting DM to False")

    if debug:
        print("    meshmachine:", meshmachine)
        print("    decalmachine:", decalmachine)

    C = bpy.context

    if C.mode == 'OBJECT' and (meshmachine or decalmachine):
        operators = C.window_manager.operators
        active = active if (active := get_active_object(C)) and active.type == 'EMPTY' and active.instance_collection and active.instance_type == 'COLLECTION' else None

        if active and operators:
            lastop = operators[-1]

            if lastop.bl_idname == 'OBJECT_OT_transform_to_mouse':
                if debug:
                    print()
                    print("    asset drop detected!")

                visible = get_visible_objects(C)

                for obj in visible:
                    if meshmachine and obj.MM.isstashobj:
                        if debug:
                            print("     stash object:", obj.name)

                        for col in obj.users_collection:
                            if debug:
                                print(f"      unlinking from {col.name}")

                            col.objects.unlink(obj)

                    if decalmachine and obj.DM.isbackup:
                        if debug:
                            print("     decal backup object:", obj.name)

                        for col in obj.users_collection:
                            if debug:
                                print(f"      unlinking from {col.name}")

                            col.objects.unlink(obj)

            was_asset_drop_cleanup_executed = True

@persistent
def undo_and_redo_post(scene):
    global global_debug

    if global_debug:
        print()
        print("HyperCursor undo/redo post handler:")
        print(" managing event history")

    delay_execution(manage_undo_redo_history)

    if global_debug:
        print(" ensure gizmo and HUD can be drawn")

    delay_execution(ensure_gizmo_and_HUD_drawing)

@persistent
def load_post(scene):
    global global_debug

    if global_debug:
        print()
        print("HyperCursor load post:")

    if global_debug:
        print(" ensure gizmo and HUD can be drawn")

    delay_execution(ensure_gizmo_and_HUD_drawing)

    if global_debug:
        print(" manage legacy updates")

    delay_execution(manage_legacy_updates)

@persistent
def depsgraph_update_post(scene):
    global global_debug

    if global_debug:
        print()
        print("HyperCursor depsgraph update post handler:")

    if global_debug:
        print(" managing HUD and VIEW3D drawing")

    delay_execution(manage_HUD_and_VIEW3D_drawing)

    if global_debug:
        print(" managing auto history")

    delay_execution(manage_auto_history)

    if global_debug:
        print(" managing mode history")

    delay_execution(manage_mode_history)

    if global_debug:
        print(" managing redoCOL selection sync")

    delay_execution(manage_redoCOL_selection_sync)

    if global_debug:
        print(" managing geo gizmos")

    delay_execution(manage_geo_gizmos)

    if global_debug:
        print(" managing asset drop takeover")

    delay_execution(manage_asset_drop_takeover)

    if global_debug:
        print(" managing asset drop cleanup")

    delay_execution(manage_asset_drop_cleanup)
