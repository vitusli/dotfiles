import bpy
import platform

classes = {'CORE': [('ui.UILists', [('HistoryCursorUIList', ''),
                                    ('RedoAddObjectUIList', '')]),
                    ('ui.gizmos', [('Gizmo2DRing', '2d_ring'),
                                   ('Gizmo3DStem', '3d_stem'),
                                   ('GizmoGroupHyperCursor', 'hyper_cursor'),
                                   ('GizmoGroupHyperCursorSimple', 'hyper_cursor_simple'),
                                   ('GizmoGroupHyperCursorEditGeometry', 'hyper_cursor_edit_geometry'),
                                   ('GizmoGroupHyperCursorScaleGeometry', 'hyper_cursor_scale_geometry'),
                                   ('GizmoGroupHyperCursorObject', 'hyper_cursor_object'),
                                   ('GizmoGroupCursorHistory', 'cursor_history'),
                                   ('GizmoGroupPipeRadius', 'pipe_radius'),
                                   ('GizmoGroupCurveSurface', 'curve_surface'),
                                   ('GizmoGroupRemoveUnusedBooleans', 'remove_unused_booleans'),
                                   ('GizmoGroupPickObjectTree', 'pick_object_tree'),
                                   ('GizmoGroupPickHyperBevel', 'pick_hyper_bevel'),
                                   ('GizmoGroupEditCurve', 'edit_curve'),
                                   ('GizmoGroupBend', 'bend'),
                                   ('GizmoGroupTest', 'test')]),
                    ('properties', [('HistoryCursorCollection', ''),
                                    ('RedoAddObjectCollection', ''),
                                    ('ApplyAllBackupCollection', ''),
                                    ('PipeRadiiCollection', ''),
                                    ('CurveSurfaceCollection', ''),
                                    ('RemoveUnusedBooleansCollection', ''),
                                    ('PickHyperBevelsCollection', ''),
                                    ('PickObjectTreeCollection', ''),
                                    ('BendCollection', ''),
                                    ('HCSceneProperties', ''),
                                    ('HCObjectProperties', ''),
                                    ('HCNodeGroupProperties', '')]),
                    ('preferences', [('HyperCursorPreferences', '')]),
                    ('ui.operators.update', [('RemoveUpdate', 'remove_hypercursor_update'),
                                             ('UseFoundUpdate', 'use_hypercursor_update'),
                                             ('ReScanUpdates', 'rescan_hypercursor_updates')]),
                    ('ui.panels', [('PanelHyperCursor', 'hyper_cursor')]),
                    ('ui.menus', [('MenuHyperCursorMeshContext', 'hypercursor_mesh_context_menu')]),
                    ('ui.pies', [('PieAddObject', 'add_object_at_cursor'),
                                 ('PieEditEdge', 'edit_edge'),
                                 ('PieEditFace', 'edit_face')]),
                    ('ui.operators.panels', [('HyperCursorSettings', 'hyper_cursor_settings'),
                                             ('HyperCursorHelp', 'hyper_cursor_help'),
                                             ('HyperCursorObject', 'hyper_cursor_object')]),
                    ('ui.operators.call_operator', [('CallHyperCursorOperator', 'call_hyper_cursor_operator')]),
                    ('ui.operators.call_pie', [('CallHyperCursorPie', 'call_hyper_cursor_pie')]),
                    ('ui.operators.toggle', [('ToggleTools', 'toggle_hyper_cursor_tools'),
                                             ('ToggleGizmos', 'toggle_hyper_cursor_gizmos'),
                                             ('ToggleGeometryGizmos', 'toggle_hyper_cursor_geometry_gizmos'),
                                             ('ToggleEditMode', 'toggle_hyper_cursor_edit_mode'),
                                             ('ToggleXRayGizmos', 'toggle_hyper_cursor_xray_gizmos'),
                                             ('ToggleWorld', 'toggle_hyper_cursor_world')]),
                    ('ui.operators.asset', [('AddHyperCursorAssets', 'add_hyper_cursor_assets_path')]),
                    ('ui.operators.keymap', [('SetupGenericGizmoKeymap', 'setup_generic_gizmo_keymap'),
                                             ('ResetKeymaps', 'reset_hyper_cursor_keymaps')]),
                    ('ui.operators.draw', [('DrawLabel', 'draw_hyper_cursor_label')]),
                    ('ui.operators.reflect', [('Reflect', 'reflect')])],

           'TOOLS': [('ui.tools', [(('HyperCursor', 'machin3.tool_hyper_cursor'), {'after': 'builtin.select_lasso', 'separator': True, 'group': True}),
                                   (('HyperCursorSimple', 'machin3.tool_hyper_cursor_simple'), {'after': 'machin3.tool_hyper_cursor'}),
                                   (('HyperCursorEditMesh', 'machin3.tool_hyper_cursor'), {'after': 'builtin.select_lasso', 'separator': True, 'group': True}),
                                   (('HyperCursorSimpleEditMesh', 'machin3.tool_hyper_cursor_simple'), {'after': 'machin3.tool_hyper_cursor'})])],

           'MACROS': [('macros.transform', [('Translate', 'macro_hyper_cursor_translate'),
                                            ('Rotate', 'macro_hyper_cursor_rotate'),
                                            ('BooleanTranslate', 'macro_hyper_cursor_boolean_translate'),
                                            ('BooleanDuplicateTranslate', 'macro_hyper_cursor_boolean_duplicate_translate')]),
                      ('macros.mirror', [('MirrorHide', 'macro_mirror_hide')])],

           'TRANSFORM': [('operators.transform', [('TransformCursor', 'transform_cursor'),
                                                  ('SnapRotate', 'snap_rotate'),
                                                  ('CastCursor', 'cast_cursor'),
                                                  ('PointCursor', 'point_cursor')])],

           'HISTORY': [('operators.history', [('CycleCursorHistory', 'cycle_cursor_history'),
                                              ('ChangeCursorHistory', 'change_cursor_history'),
                                              ('ClearCursorHistory', 'clear_cursor_history'),
                                              ('DrawCursorHistory', 'draw_cursor_history'),
                                              ('SelectCursorHistory', 'select_cursor_history'),
                                              ('ChangeAddObjHistory', 'change_add_obj_history')])],
           'FOCUS': [('operators.focus', [('FocusCursor', 'focus_cursor'),
                                          ('FocusProximity', 'focus_proximity'),
                                          ('ResetFocusProximity', 'reset_focus_proximity')])],

           'ADD': [('operators.add', [('AddObjectAtCursor', 'add_object_at_cursor'),
                                      ('AddPipe', 'add_pipe'),
                                      ('AddCurveAsset', 'add_curve_asset')])],

           'ADJUST': [('operators.adjust', [('AdjustCylinder', 'adjust_cylinder'),

                                            ('AdjustPipe', 'adjust_pipe'),
                                            ('AdjustPipeArc', 'adjust_pipe_arc'),

                                            ('AdjustShell', 'adjust_shell'),
                                            ('AdjustDisplace', 'adjust_displace'),
                                            ('AdjustArray', 'adjust_array')])],

           'CHANGE': [('operators.change', [('ChangeRemoteBoolean', 'change_remote_boolean'),
                                            ('ChangeLocalBoolean', 'change_local_boolean'),

                                            ('ChangeEdgeBevel', 'change_edge_bevel'),
                                            ('ChangeSolidify', 'change_solidify'),

                                            ('ChangeMirror', 'change_mirror'),

                                            ('ChangeArray', 'change_array'),
                                            ('ChangeHyperArray', 'change_hyper_array'),

                                            ('ChangeOther', 'change_other'),
                                            ('ChangeBackup', 'change_backup')])],

           'ASSET': [('operators.asset', [('FetchAsset', 'fetch_asset'),
                                          ('CreateAsset', 'create_asset'),
                                          ('DisbandCollectionInstanceAsset', 'disband_collection_instance_asset'),
                                          ('SetDropAssetProps', 'set_drop_asset_props')])],

           'EDIT': [('operators.edit_edge', [('BevelEdge', 'bevel_edge'),
                                             ('RemoveEdge', 'remove_edge'),
                                             ('LoopCut', 'loop_cut'),
                                             ('SlideEdge', 'slide_edge'),
                                             ('CreaseEdge', 'crease_edge'),
                                             ('PushEdge', 'push_edge'),
                                             ('StraightenEdges', 'straighten_edges')]),

                    ('operators.edit_face', [('PushFace', 'push_face'),
                                             ('ScaleFace', 'scale_face'),
                                             ('InsetFace', 'inset_face'),
                                             ('ExtrudeFace', 'extrude_face'),
                                             ('ExtractFace', 'extract_face'),
                                             ('RemoveFace', 'remove_face'),
                                             ('MatchSurface', 'match_surface'),
                                             ('CurveSurface', 'curve_surface'),
                                             ('AdjustCurveSurfacePoint', 'adjust_curve_surface_point'),
                                             ('FlattenFace', 'flatten_face'),
                                             ('MoveFace', 'move_face')]),

                    ('operators.edit_mesh', [('ScaleMesh', 'scale_mesh')]),

                    ('operators.edit_curve', [('Blendulate', 'blendulate')])],

           'SELECT': [('operators.select', [('SelectEdge', 'select_edge'),
                                            ('ClearEdgeSelection', 'clear_edge_selection'),
                                            ('SelectFace', 'select_face'),
                                            ('ClearFaceSelection', 'clear_face_selection')])],

           'OBJECT': [('operators.object', [('PickObjectTree', 'pick_object_tree'),
                                            ('TogglePickObjectTree', 'toggle_pick_object_tree'),

                                            ('MergeObject', 'merge_object'),
                                            ('DuplicateObject', 'duplicate_object'),

                                            ('HideWireObjects', 'hide_wire_objects'),
                                            ('HideMirrorObj', 'hide_mirror_obj')]),

                      ('ui.operators.select', [('SelectObject', 'select_object')]),
                      ('ui.operators.draw', [('DrawActiveObject', 'draw_active_object')])],

           'MESH': [('operators.mesh', [('ToggleGizmoDataLayerPreview', 'toggle_gizmo_data_layer_preview'),
                                        ('ToggleGizmo', 'toggle_gizmo'),
                                        ('GeoGizmoSetup', 'geogzm_setup')])],

           'CUT': [('operators.cut', [('HyperCut', 'hyper_cut')])],

           'BEVEL': [('operators.bevel', [('HyperBevel', 'hyper_bevel'),
                                          ('PickHyperBevel', 'pick_hyper_bevel'),
                                          ('EditHyperBevel', 'edit_hyper_bevel'),
                                          ('ExtendHyperBevel', 'extend_hyper_bevel')])],

           'BEND': [('operators.bend', [('HyperBend', 'hyper_bend'),
                                        ('AdjustBendAngle', 'adjust_bend_angle'),
                                        ('AdjustBendOffset', 'adjust_bend_offset'),
                                        ('AdjustBendLimit', 'adjust_bend_limit'),
                                        ('AdjustBendContainment', 'adjust_bend_containment'),
                                        ('ToggleBend', 'toggle_bend')])],

           'MODIFIER': [('operators.modifier', [('RemoveBooleanFromParent', 'remove_boolean_from_parent'),
                                                ('RestoreBooleanOnParent', 'restore_boolean_on_parent'),
                                                ('DuplicateBooleanOperator', 'duplicate_boolean_operator'),

                                                ('HyperMod', 'hyper_modifier'),
                                                ('RemoveUnusedBooleans', 'remove_unused_booleans'),
                                                ('ToggleUnusedBooleanMod', 'toggle_unused_boolean_mod'),

                                                ('ApplyAll', 'apply_all_modifiers'),
                                                ('ToggleAll', 'toggle_all_modifiers'),
                                                ('RemoveAll', 'remove_all_modifiers')])],

           'DEBUG': [('operators.debug', [('Button', 'button')])],
           }

def get_box_select_keymaps():
    kmtype = 'EVT_TWEAK_L' if bpy.app.version < (3, 2, 0) else 'LEFTMOUSE'
    kmvalue = 'ANY' if bpy.app.version < (3, 2, 0) else 'CLICK_DRAG'

    keys = [("view3d.select_box", {"type": kmtype, "value": kmvalue}, {"properties": []}),
            ("view3d.select_box", {"type": kmtype, "value": kmvalue, "shift": True}, {"properties": [('mode', 'ADD')]}),
            ("view3d.select_box", {"type": kmtype, "value": kmvalue, "ctrl": True}, {"properties": [('mode', 'SUB')]})]

    return keys

def get_hide_wire_mod_keys():
    if platform.system() == "Windows":
        return {"alt": False, "shift": True}
    return {"alt": True, "shift": False}

keys = {'HYPERCURSOR': (*get_box_select_keymaps(),

                        ("machin3.toggle_hyper_cursor_gizmos", {"type": 'ESC', "value": 'PRESS'}, {}),
                        ("machin3.toggle_hyper_cursor_world", {"type": 'W', "value": 'PRESS', "shift": True}, {}),

                        ("machin3.toggle_hyper_cursor_geometry_gizmos", {"type": 'G', "value": 'PRESS', "shift": True}, {}),
                        ("machin3.toggle_hyper_cursor_xray_gizmos", {"type": 'X', "value": 'PRESS', "shift": True}, {}),
                        ("machin3.toggle_hyper_cursor_edit_mode", {"type": 'E', "value": 'PRESS', "shift": True}, {}),

                        ("machin3.cycle_cursor_history", {"type": 'WHEELUPMOUSE', "value": 'PRESS', "alt": True}, {}),
                        ("machin3.cycle_cursor_history", {"type": 'WHEELDOWNMOUSE', "value": 'PRESS', "alt": True}, {"properties": [('backwards', False)]}),

                        ("machin3.focus_cursor", {"type": 'F', "value": 'PRESS', "shift": True}, {}),
                        ("machin3.focus_proximity", {"type": 'F', "value": 'PRESS', "shift": True, "alt": True}, {}),

                        ("machin3.transform_cursor", {"type": 'RIGHTMOUSE', "value": 'PRESS', "ctrl": True}, {"properties": [('mode', 'DRAG')]}),
                        ("machin3.cast_cursor", {"type": 'C', "value": 'PRESS', "shift": True}, {}),
                        ("machin3.point_cursor", {"type": 'V', "value": 'PRESS', "shift": True}, {}),
                        ("machin3.point_cursor", {"type": 'RIGHTMOUSE', "value": 'PRESS', "shift": True}, {"properties": [('instant', True)]}),

                        ("machin3.call_hyper_cursor_pie", {"type": 'A', "shift": True, "value": 'PRESS'}, {'properties': [('idname', 'MACHIN3_MT_add_object_at_cursor')]}),

                        ("machin3.hyper_cut", {"type": 'X', "ctrl": True, "value": 'PRESS'}, {}),
                        ("machin3.hyper_bevel", {"type": 'B', "ctrl": True, "value": 'PRESS'}, {}),
                        ("machin3.hyper_bend", {"type": 'B', "shift": True, "value": 'PRESS'}, {}),

                        ("machin3.hide_wire_objects", {"type": 'ESC', **get_hide_wire_mod_keys(), "value": 'PRESS'}, {}),
                        ("machin3.pick_object_tree", {"type": 'Q', "alt": True, "value": 'PRESS'}, {}),
                        ("machin3.pick_hyper_bevel", {"type": 'B', "alt": True, "value": 'PRESS'}, {}),
                        ("machin3.hyper_modifier", {"type": 'W', "alt": True, "value": 'PRESS'}, {"properties": [('is_gizmo_invokation', False), ('mode', 'PICK')]}),
                        ("machin3.hyper_modifier", {"type": 'W', "shift": True, "alt":True, "value": 'PRESS'}, {"properties": [('is_gizmo_invokation', False), ('mode', 'ADD')]}),
                        ("machin3.remove_unused_booleans", {"type": 'X', "alt": True, "value": 'PRESS'}, {}),

                        ("machin3.macro_hyper_cursor_boolean_translate", {"type": 'G', "ctrl": True, "value": 'PRESS'}, {}),
                        ("machin3.macro_hyper_cursor_boolean_duplicate_translate", {"type": 'D', "shift": True, "value": 'PRESS'}, {}),

                        ("machin3.snap_rotate", {"type": 'E', "value": 'PRESS'}, {}),
                        ("machin3.extract_face", {"type": 'E', "alt": True, "value": 'PRESS'}, {"properties": [('evaluated', True)]})),

        'HYPERCURSOREDIT': (*get_box_select_keymaps(),

                            ("machin3.toggle_hyper_cursor_gizmos", {"type": 'ESC', "value": 'PRESS'}, {}),
                            ("machin3.toggle_hyper_cursor_world", {"type": 'W', "value": 'PRESS', "shift": True}, {}),

                            ("machin3.cycle_cursor_history", {"type": 'WHEELUPMOUSE', "value": 'PRESS', "alt": True}, {}),
                            ("machin3.cycle_cursor_history", {"type": 'WHEELDOWNMOUSE', "value": 'PRESS', "alt": True}, {"properties": [('backwards', False)]}),

                            ("machin3.focus_cursor", {"type": 'F', "value": 'PRESS', "shift": True}, {}),
                            ("machin3.focus_proximity", {"type": 'F', "value": 'PRESS', "shift": True, "alt": True}, {}),

                            ("machin3.transform_cursor", {"type": 'RIGHTMOUSE', "value": 'PRESS', "ctrl": True}, {"properties": [('mode', 'DRAG')]}),
                            ("machin3.cast_cursor", {"type": 'C', "value": 'PRESS', "shift": True}, {}),
                            ("machin3.point_cursor", {"type": 'V', "value": 'PRESS', "shift": True}, {}),
                            ("machin3.point_cursor", {"type": 'RIGHTMOUSE', "value": 'PRESS', "shift": True}, {"properties": [('instant', True)]}),

                            ("machin3.hyper_bevel", {"type": 'B', "shift": True, "value": 'PRESS'}, {})),

        'TOOLBAR': [{'label': 'HyperCursor Tool', 'keymap': 'Toolbar Popup', 'region_type': 'TEMPORARY', 'idname': 'wm.tool_set_by_id', 'type': 'C', 'value': 'PRESS', 'properties': [('name', 'machin3.tool_hyper_cursor')]},
                    {'label': 'HyperCursor Simple Tool', 'info': 'Likely to be removed!', 'keymap': 'Toolbar Popup', 'region_type': 'TEMPORARY', 'idname': 'wm.tool_set_by_id', 'type': 'C', 'shift': True, 'value': 'PRESS', 'active': False, 'properties': [('name', 'machin3.tool_hyper_cursor_simple')]}]}
