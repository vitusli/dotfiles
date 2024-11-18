import bpy
from bpy.types import Menu
from .. utils.registration import get_addon
from .. utils.modifier import subd_poll
from .. utils.workspace import get_assetbrowser_area, get_assetbrowser_space
from .. utils.asset import get_asset_details_from_space, get_pretty_assetpath

meshmachine = None
machin3tools = None

class PieAddObject(Menu):
    bl_idname = "MACHIN3_MT_add_object_at_cursor"
    bl_label = "Add Object at Cursor"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        area = get_assetbrowser_area(context)
        screen_areas = [area for area in context.screen.areas]

        pretty_path = None
        filename = None

        if area in screen_areas:
            space = get_assetbrowser_space(area)
            libname, libpath, filename, import_method = get_asset_details_from_space(context, space, debug=False)

            if 'Object/' in filename:
                pretty_path = get_pretty_assetpath([libname, filename], debug=False)

        op = pie.operator("machin3.add_object_at_cursor", text="Cube", icon='MESH_CUBE')
        op.type = 'CUBE'
        op.is_drop = False

        op = pie.operator("machin3.add_object_at_cursor", text="Cylinder", icon='MESH_CYLINDER')
        op.type = 'CYLINDER'
        op.is_drop = False

        if pretty_path:
            op = pie.operator("machin3.add_object_at_cursor", text="Asset", icon='MESH_MONKEY')
            op.type = 'ASSET'
            op.is_drop = False

        elif not area:
            row = pie.row()
            row.label(text="No Asset Browser on this Workspace")

        else:
            pie.separator()

        pie.operator("wm.call_menu", text="More", icon='MESH_ICOSPHERE').name = "VIEW3D_MT_add"

        pie.separator()

        pie.separator()

        pie.separator()

        if pretty_path:
            row = pie.row()
            row.label(text=pretty_path)

        elif filename or area:
            row = pie.row()
            row.label(text="No OBJECT Asset selected in Asset Browser")

        else:
            pie.separator()

class PieEditEdge(Menu):
    bl_idname = "MACHIN3_MT_edit_edge"
    bl_label = "Edit Edge"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        global meshmachine, machin3tools

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        if machin3tools is None:
            machin3tools = get_addon('MACHIN3tools')[0]

        index = self.index

        box = pie.split()

        col = box.column(align=True)
        col.scale_y = 1.2

        if subd_poll(context):
            col.operator("machin3.crease_edge", text="(A) Crease", icon='MOD_BEVEL').index = index

        col.operator("machin3.straighten_edges", text="Straighten", icon='IPO_LINEAR').index = index
        col.operator("machin3.push_edge", text="(D) Push", icon='EMPTY_SINGLE_ARROW').index = index
        col.separator()

        op = col.operator("machin3.bevel_edge", text="Bevel", icon='MOD_BEVEL')
        op.index = index
        op.is_profile_drop = False
        op.is_hypermod_invoke = False

        col.operator("machin3.loop_cut", text="(C) Loop Cut", icon='DRIVER_DISTANCE').index = index
        col.operator("machin3.slide_edge", text="(G) Slide", icon='ARROW_LEFTRIGHT').index = index

        col.separator()
        col.operator("machin3.remove_edge", text="(X) Remove", icon='X').index = index

        if meshmachine or (machin3tools and (getattr(bpy.types, 'MACHIN3_OT_smart_vert', False) or getattr(bpy.types, 'MACHIN3_OT_transform_edge_constrained'))):
            box = pie.split()

            col = box.column(align=True)
            col.scale_y = 1.3

            if meshmachine:
                col.operator("machin3.wedge", text="Wedge", icon='MESH_CUBE').index = index

            if machin3tools:
                col.separator()

                if getattr(bpy.types, 'MACHIN3_OT_smart_vert', False):
                    op = col.operator("machin3.smart_vert", text="Extend", icon='MESH_CUBE')
                    op.index = index
                    op.slideoverride = True

                if getattr(bpy.types, 'MACHIN3_OT_transform_edge_constrained', False):
                    op = col.operator("machin3.transform_edge_constrained", text="Rotate Edge Constrained")
                    op.transform_mode = 'ROTATE'
                    op.objmode = True
                    op.edgeindex = index
                    op.faceindex = -1

        else:
            pie.separator()

        pie.operator("machin3.clear_edge_selection", text="De-Select All", icon='SELECT_SET')

        pie.operator("machin3.select_edge", text="Select", icon='EDGESEL').index = index

        pie.separator()

        pie.separator()

        pie.separator()

        pie.separator()

class PieEditFace(Menu):
    bl_idname = "MACHIN3_MT_edit_face"
    bl_label = "Edit Face"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        global meshmachine, machin3tools

        if meshmachine is None:
            meshmachine = get_addon('MESHmachine')[0]

        if machin3tools is None:
            machin3tools = get_addon('MACHIN3tools')[0]

        index = self.index

        box = pie.split()

        col = box.column(align=True)
        col.scale_y = 1.3
        col.scale_x = 1.3

        col.operator("machin3.flatten_face", text="Flatten", icon='BLANK1').index = index

        col.separator()
        col.operator("machin3.move_face", text="(G) Move", icon='BLANK1').index = index
        col.operator("machin3.scale_face", text="Scale", icon='BLANK1').index = index

        col.separator()
        col.operator("machin3.inset_face", text="(D) Inset", icon='BLANK1').index = index
        col.operator("machin3.extrude_face", text="Extrude", icon='BLANK1').index = index

        col.separator()
        col.operator("machin3.remove_face", text="(X) Remove", icon='BLANK1').index = index
        op = col.operator("machin3.extract_face", text="Extract", icon='BLANK1')
        op.index = index
        op.evaluated = False

        box = pie.split()

        col = box.column(align=True)
        col.scale_y = 1.3

        col.operator("machin3.curve_surface", text="Curve Surface", icon='BLANK1').index = index
        col.separator()

        col.operator("machin3.match_surface", text="Match Surface", icon='BLANK1').index = index
        col.operator("machin3.merge_object", text="Merge Object", icon='BLANK1').index = index

        if machin3tools and getattr(bpy.types, 'MACHIN3_OT_transform_edge_constrained', False):
            col.separator()

            op = col.operator("machin3.transform_edge_constrained", text="Rotate Edge Constrained")
            op.transform_mode = 'ROTATE'
            op.objmode = True
            op.edgeindex = -1
            op.faceindex = index

        pie.operator("machin3.clear_face_selection", text="De-Select All", icon='SELECT_SET')

        pie.operator("machin3.select_face", text="Select", icon='FACESEL').index = index

        pie.separator()

        pie.separator()

        pie.separator()

        pie.separator()
