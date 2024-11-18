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

import bpy

class FixSceneSettings(bpy.types.Operator):
    bl_label = 'Reset Scene Color Settings'
    bl_idname = "render.render_raw_fix_scene_settings"
    bl_description = 'Sets the scene color management settings back to what Render Raw needs in order to function properly'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.view_settings.view_transform = 'Raw'
        context.scene.view_settings.exposure = 0
        context.scene.view_settings.look = 'None'
        context.scene.view_settings.use_curve_mapping = False
        return{'FINISHED'}
    
def register():
    bpy.utils.register_class(FixSceneSettings)

def unregister():
    bpy.utils.unregister_class(FixSceneSettings)