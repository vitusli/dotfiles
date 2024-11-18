import bpy
from .. utils.system import splitpath
from .. utils.asset import get_pretty_assetpath

class HistoryCursorUIList(bpy.types.UIList):
    bl_idname = "MACHIN3_UL_history_cursor"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        hc = context.scene.HC

        layout.operator('machin3.select_cursor_history', text='', emboss=False, icon='RESTRICT_SELECT_OFF').index = index

        layout.prop(item, 'name', text="", emboss=False)

        if index == hc.historyIDX:
            row = layout.row(align=True)

            op = row.operator('machin3.change_cursor_history', text='', emboss=False, icon='TRIA_UP')
            op.mode = 'MOVEUP'
            op.index = index

            op = row.operator('machin3.change_cursor_history', text='', emboss=False, icon='TRIA_DOWN')
            op.mode = 'MOVEDOWN'
            op.index = index

        op = layout.operator('machin3.change_cursor_history', text='', emboss=False, icon='X')
        op.mode = 'REMOVE'
        op.index = index

class RedoAddObjectUIList(bpy.types.UIList):
    bl_idname = "MACHIN3_UL_redo_add_object"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if item.name in ['CUBE', 'CYLINDER']:
            objname = item.name.title()

            if item.name == 'CUBE':
                objicon = 'MESH_CUBE'
            else:
                objicon = 'MESH_CYLINDER'
        else:
            objname = get_pretty_assetpath(item)
            objicon = 'MESH_MONKEY'

        split = layout.split(factor=0.5)

        row = split.row()

        if item.name in ['CUBE', 'CYLINDER']:
            row.label(text='', icon='BLANK1')
        else:
            op = row.operator('machin3.change_add_obj_history', text='', emboss=False, icon='RESTRICT_SELECT_OFF')
            op.index = index
            op.mode = 'SELECT'

        row.label(text=objname, icon=objicon)

        row = split.row()
        row.prop(item, 'size', text='', emboss=False)

        if context.active_object:
            op = row.operator('machin3.change_add_obj_history', text='', emboss=False, icon='SORT_ASC')
            op.index = index
            op.mode = 'FETCHSIZE'
        else:
            row.label(text='', icon='BLANK1')

        if item.boolean:
            row.prop(item, 'hide_boolean', text='', emboss=False, icon='HIDE_ON' if item.hide_boolean else 'HIDE_OFF')
        else:
            row.label(text='', icon='BLANK1')

        op = row.operator('machin3.change_add_obj_history', text='', emboss=False, icon='X')
        op.index = index
        op.mode = 'REMOVE'
