'''
Copyright (C) 2024 Orange Turbine
https://orangeturbine.com
orangeturbine@cgcookie.com

This file is part of the Render Raw add-on, created by Jonathan Lampel for Orange Turbine.

All code distributed with this add-on is open source as described below.

Render Raw is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <https://www.gnu.org/licenses/>.
'''

import bpy, os

def get_prefs(context):
    return context.preferences.addons[__package__].preferences

class render_raw_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    preset_path: bpy.props.StringProperty(
        name = 'Folder',
        description = 'The location custom presets will be saved to. This must be set before saving presets',
        default = ''
    )
    enable_compositing: bpy.props.EnumProperty(
        name = 'Auto Enable Viewport Compositing',
        description = 'Turn on Viewport Compositing for all 3D viewports when Render Raw is enabled, which is needed for the viewport colors to look correct',
        items = [
            ('ALL', 'In all 3D Viewports', 'Enables the viewport compositor in all 3d viewports in all workspaces'), 
            ('SCREEN', 'In active Workspace', 'Enables the viewport compositor in all 3d viewports in the active workspace'), 
            ('NONE', 'None', 'Does not enable viewport compositing when enabling Render Raw. This will cause the rendered view to look incorrect'), 
        ],
        default = 'ALL'
    )
    raw_while_rendering: bpy.props.BoolProperty(
        name = 'Show Raw During Rendering',
        description = 'Keeps the Raw transform and viewport compositing while rendering. Enabling this causes less flicker and may be slightly faster, but makes the render in progress harder to see',
        default = True
    )
    enable_OpenCL: bpy.props.BoolProperty(
        name = 'Enable OpenCL Compositing',
        description = 'Generally, this should be enabled unless your hardware does not have good OpenCL support',
        default = True
    )
    enable_buffer_groups: bpy.props.BoolProperty(
        name = 'Enable in 3D View Sidebar',
        description = 'Speeds up re-rendering at the cost of increased memory',
        default = True
    )

    enable_3d_view_sidebar: bpy.props.BoolProperty(
        name = 'Enable in 3D View Sidebar',
        default = True
    )

    enable_compositing_sidebar: bpy.props.BoolProperty(
        name = 'Enable in Compositor Sidebar',
        default = True
    )

    enable_image_sidebar: bpy.props.BoolProperty(
        name = 'Enable in Image Editor Sidebar',
        default = True
    )

    sidebar_category: bpy.props.StringProperty(
        name = 'Sidebar Category',
        description = 'Which tab in the sidebar the Render Raw panels will be added to',
        default = 'Render'
    )

    def draw(self, context):
        col = self.layout.column()
        col.use_property_split = True

        col.label(text='Presets')
        row = col.row()
        row.prop(self, 'preset_path')
        row.operator("render.render_raw_set_preset_directory", icon='FILE_FOLDER', text='')
        if self.preset_path == '' or not os.path.isdir(self.preset_path):
            split = col.split(factor=0.4)
            col1 = split.column(align=True)
            col1.alignment = 'RIGHT'
            col2 = split.column(align=True)
            col2.label(text='Folder must be set before saving presets', icon='ERROR')
        col.separator()

        col.label(text='Interface')
        interface = col.column(heading='Show Panels In')
        interface.prop(self, 'enable_3d_view_sidebar', text='3D View Sidebar')
        # interface.prop(self, 'enable_compositing_sidebar', text='Compositor Sidebar')
        # interface.prop(self, 'enable_image_sidebar', text='Image Editor Sidebar')
        col.separator()

        if bpy.app.version < (4, 2, 0):
            col.label(text='Render Compositing')
            render = col.column(heading='Auto Enable')
            render.prop(self, 'enable_OpenCL', text='OpenCL')
            render.prop(self, 'enable_buffer_groups', text='Buffer Groups')
            col.separator()

        col.label(text='Viewport Compositing')
        col.prop(self, 'enable_compositing', text='Auto Enable')

        col.label(text='Render Compositing')
        col.prop(self, 'raw_while_rendering')


def register():
    bpy.utils.register_class(render_raw_preferences)

def unregister():
    bpy.utils.unregister_class(render_raw_preferences)
