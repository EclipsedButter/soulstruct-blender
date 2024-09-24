"""
Import MCG files (with/without DCX) into Blender 3.3+ (Python 3.10+ scripting required).

MCG files contain gate nodes and edges connecting them. Gate nodes lie on the boundaries between navmesh parts and edges
cross through a particular navmesh to connect two gate nodes.

This file format is only used in DeS and DS1 (PTDE/DSR).
"""
from __future__ import annotations

__all__ = [
    "ImportMCG",
    "ImportSelectedMapMCG",
    "ImportMCP",
    "ImportSelectedMapMCP",
]

import traceback
from pathlib import Path

import bpy
from bpy_extras.io_utils import ImportHelper
from io_soulstruct.exceptions import NavGraphMissingNavmeshError
from io_soulstruct.utilities import *
from soulstruct.darksouls1r.maps import MSB
from soulstruct.darksouls1r.maps.navmesh import MCG, MCP, NavmeshAABB
from .types import BlenderMCG


class ImportMCG(LoggingOperator, ImportHelper):
    bl_idname = "import_scene.mcg"
    bl_label = "Import MCG"
    bl_description = "Import an MCG navmesh node/edge graph file. Supports DCX-compressed files"

    filename_ext = ".mcg"

    filter_glob: bpy.props.StringProperty(
        default="*.mcg;*.mcg.dcx",
        options={'HIDDEN'},
        maxlen=255,
    )

    custom_msb_path: bpy.props.StringProperty(
        name="Custom MSB Path",
        description="Custom MSB path to use for MCG import. Leave blank to auto-find",
        default="",
    )

    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    directory: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        self.info("Executing MCG import...")

        file_paths = [Path(self.directory, file.name) for file in self.files]

        if not self.custom_msb_path:
            directory_path = Path(self.directory)
            msb_path = directory_path.parent / "MapStudio" / f"{directory_path.stem}.msb"
        else:
            msb_path = Path(self.custom_msb_path)
        if not msb_path.is_file():
            return self.error(f"Could not find MSB file '{msb_path}'.")
        try:
            msb = MSB.from_path(msb_path)
        except Exception as ex:
            return self.error(f"Could not load MSB file '{msb_path}'. Error: {ex}")

        navmesh_part_names = [navmesh.name for navmesh in msb.navmeshes]

        mcgs = []
        for file_path in file_paths:
            try:
                mcg = MCG.from_path(file_path)
            except Exception as ex:
                self.warning(f"Error occurred while reading MCG file '{file_path.name}': {ex}")
            else:
                # We don't set MSB navmesh references; Blender importer works directly with the navmesh indices.
                mcgs.append(mcg)

        for i, mcg in enumerate(mcgs):
            map_stem = file_paths[i].name.split(".")[0]
            try:
                BlenderMCG.new_from_soulstruct_obj(
                    self,
                    context,
                    mcg,
                    name=f"{map_stem} MCG",
                    collection=None,
                    navmesh_part_names=navmesh_part_names,
                )
            except Exception as ex:
                traceback.print_exc()
                self.error(f"Error occurred while importing MCG file '{file_paths[i].name}': {ex}")

        return {"FINISHED"}


class ImportSelectedMapMCG(LoggingOperator):
    bl_idname = "import_scene.quick_mcg"
    bl_label = "Import MCG"
    bl_description = "Import MCG navmesh node/edge graph file from selected game map"

    # MSB always auto-found.

    @classmethod
    def poll(cls, context):
        return bool(cls.settings(context).map_stem)

    def execute(self, context):

        settings = self.settings(context)
        map_stem = settings.get_latest_map_stem_version()  # MCG uses latest
        if not map_stem:
            return
        try:
            mcg_path = settings.get_import_map_file_path(f"{map_stem}.mcg", map_stem=map_stem)
        except FileNotFoundError:
            return self.error(f"Could not find MCG file '{map_stem}.mcg' in selected map {map_stem}.")
        try:
            msb_path = settings.get_import_msb_path(map_stem)
        except FileNotFoundError:
            return self.error(f"Could not find MSB file for selected map {map_stem}.")
        try:
            msb = MSB.from_path(msb_path)
        except Exception as ex:
            return self.error(f"Could not load MSB file '{msb_path}'. Error: {ex}")

        navmesh_part_names = [navmesh.name for navmesh in msb.navmeshes]

        try:
            mcg = MCG.from_path(mcg_path)
        except Exception as ex:
            return self.error(f"Error occurred while reading MCG file '{mcg_path}': {ex}")
        # We don't set MSB navmesh references; Blender importer works directly with the navmesh indices.

        try:
            BlenderMCG.new_from_soulstruct_obj(
                self,
                context,
                mcg,
                name=f"{map_stem} MCG",
                collection=None,
                navmesh_part_names=navmesh_part_names,
            )
        except NavGraphMissingNavmeshError as ex:
            traceback.print_exc()
            return self.error(
                f"Error occurred while importing MCG file '{mcg_path}' due to missing an MSB Navmesh. The matching MSB "
                f"must be imported before importing the map's MCG NavGraph. Full error: {ex}"
            )
        except Exception as ex:
            traceback.print_exc()
            return self.error(f"Error occurred while importing MCG file '{mcg_path}': {ex}")

        return {"FINISHED"}


class ImportMCP(LoggingOperator, ImportHelper):
    bl_idname = "import_scene.mcp"
    bl_label = "Import MCP"
    bl_description = "Import an MCP file containing MSB navmesh AABBs and connections. Supports DCX-compressed files"

    filename_ext = ".mcp"

    filter_glob: bpy.props.StringProperty(
        default="*.mcp;*.mcp.dcx",
        options={'HIDDEN'},
        maxlen=255,
    )

    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    directory: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        file_paths = [Path(self.directory, file.name) for file in self.files]

        mcps = []
        for file_path in file_paths:
            try:
                mcp = MCP.from_path(file_path)
            except Exception as ex:
                self.warning(f"Error occurred while reading MCP file '{file_path.name}': {ex}")
            else:
                mcps.append(mcp)

        for i, mcp in enumerate(mcps):
            import_mcp(self, context, mcp, f"{file_paths[i].stem} MCP")

        return {"FINISHED"}


class ImportSelectedMapMCP(LoggingOperator):
    bl_idname = "import_scene.selected_map_mcp"
    bl_label = "Import MCP"
    bl_description = "Import MCP file containing MSB navmesh AABBs and connections from selected game map"

    def execute(self, context):

        settings = self.settings(context)
        map_stem = settings.get_latest_map_stem_version()  # MCP uses latest
        try:
            mcp_path = settings.get_import_map_file_path(f"{map_stem}.mcp", map_stem=map_stem)
        except FileNotFoundError:
            return self.error(f"Could not find MCP file '{map_stem}.mcp' in selected map {map_stem}.")

        try:
            mcp = MCP.from_path(mcp_path)
        except Exception as ex:
            return self.error(f"Error occurred while reading MCP file '{mcp_path}': {ex}")

        import_mcp(self, context, mcp, f"{mcp_path.stem} MCP")

        return {"FINISHED"}


def import_mcp(
    operator: LoggingOperator, context: bpy.types.Context, mcp: MCP, bl_name: str, navmesh_part_names: list[str] = None
) -> bpy.types.Object:
    operator.info(f"Importing MCP: {bl_name}")

    operator.to_object_mode()
    operator.deselect_all()

    mcp_parent = bpy.data.objects.new(bl_name, None)  # empty parent for all AABB meshes
    context.scene.collection.objects.link(mcp_parent)

    for i, aabb in enumerate(mcp.aabbs):
        aabb: NavmeshAABB
        bl_aabb = create_aabb(aabb)
        bl_aabb.name = f"AABB {i} ({navmesh_part_names[i]})" if navmesh_part_names else f"AABB {i}"
        bl_aabb.parent = mcp_parent

    return mcp_parent


def create_aabb(aabb: NavmeshAABB):
    """Create an AABB prism representing `aabb`. Position is baked into mesh data fully, just like the navmesh."""
    start_vec = GAME_TO_BL_VECTOR(aabb.aabb_start)
    end_vec = GAME_TO_BL_VECTOR(aabb.aabb_end)
    bpy.ops.mesh.primitive_cube_add()
    bl_box = bpy.context.active_object
    # noinspection PyTypeChecker
    box_data = bl_box.data  # type: bpy.types.Mesh
    for vertex in box_data.vertices:
        vertex.co[0] = start_vec.x if vertex.co[0] == -1.0 else end_vec.x
        vertex.co[1] = start_vec.y if vertex.co[1] == -1.0 else end_vec.y
        vertex.co[2] = start_vec.z if vertex.co[2] == -1.0 else end_vec.z
    bpy.ops.object.modifier_add(type="WIREFRAME")
    bl_box.modifiers[0].thickness = 0.2
    return bl_box
