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
from typing import Literal

import numpy

def enable_viewport_compositing(context, viewports: Literal['ALL', 'SCREEN', 'SAVED', 'NONE']):
    if viewports == 'SAVED':
        disabled_areas = context.scene['render_raw']['disabled_areas']
        for disabled_area in disabled_areas:
            for workspace in bpy.data.workspaces:
                if workspace.name_full == disabled_area['workspace_name']:
                    for screen in workspace.screens:
                        if screen.name_full == disabled_area['screen_name']:
                            for area_index, area in enumerate(screen.areas):
                                if area_index == disabled_area['index']:
                                    area.spaces[0].shading.use_compositor = disabled_area['compositor']
        context.scene['render_raw']['disabled_areas'] = []
    elif viewports == 'ALL':
        for workspace in bpy.data.workspaces:
            for screen in workspace.screens:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.spaces[0].shading.use_compositor = 'ALWAYS'
    elif viewports == 'SCREEN':
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces[0].shading.use_compositor = 'ALWAYS'
    elif context.area.type == 'VIEW_3D':
        area.spaces[0].shading.use_compositor = 'ALWAYS'
    else:
        print("No viewports were updated")

def disable_viewport_compositing(context, viewports: Literal['ALL', 'SCREEN', 'NONE']):
    disabled_areas = []

    def save_area(workspace, screen, area, area_index):
        use_compositor = area.spaces[0].shading.use_compositor
        saved_area = {
            'workspace_name': workspace.name_full,
            'screen_name': screen.name_full,
            'index': area_index,
            'compositor': use_compositor
        }
        disabled_areas.append(saved_area)

    if viewports == 'ALL':
        for workspace in bpy.data.workspaces:
            for screen in workspace.screens:
                for area_index, area in enumerate(screen.areas):
                    if area.type == 'VIEW_3D' and area.spaces[0].shading.use_compositor != 'DISABLED':
                        save_area(workspace, screen, area, area_index)
                        area.spaces[0].shading.use_compositor = 'DISABLED'
    elif viewports == 'SCREEN':
        for area in context.screen.areas:
            if area.type == 'VIEW_3D' and area.spaces[0].shading.use_compositor != 'DISABLED':
                save_area(context.workspace, area.id_data, area)
                area.spaces[0].shading.use_compositor = 'DISABLED'
    elif context.area.type == 'VIEW_3D' and area.spaces[0].shading.use_compositor != 'DISABLED':
        save_area(context.workspace, area.id_data, area)
        context.area.spaces[0].shading.use_compositor = 'DISABLED'
    else:
        print("No viewports were updated")

    context.scene['render_raw']['disabled_areas'] = disabled_areas