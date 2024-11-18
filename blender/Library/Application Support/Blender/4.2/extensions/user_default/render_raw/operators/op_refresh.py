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
from ..update_nodes import refresh_RR_nodes

class RefreshNodeTree(bpy.types.Operator):
    bl_label = 'Refresh Node Tree'
    bl_idname = "render.render_raw_refresh_nodes"
    bl_description = 'Removes all Render Raw nodes and imports them again. Useful for when switching a project from one version of the addon to another'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        refresh_RR_nodes(self, context)
        return{'FINISHED'}
    
def register():
    bpy.utils.register_class(RefreshNodeTree)

def unregister():
    bpy.utils.unregister_class(RefreshNodeTree)