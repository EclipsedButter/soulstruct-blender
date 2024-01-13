from __future__ import annotations

__all__ = [
    "SoulstructGameEnums",
    "CLEAR_GAME_FILE_ENUMS",
]

import re
import typing as tp

import bpy

from soulstruct.games import *

from io_soulstruct.utilities.misc import CachedEnum, is_path_and_file, is_path_and_dir
from .cached import get_cached_file
from .core import SoulstructSettings

if tp.TYPE_CHECKING:
    from io_soulstruct.type_checking import MSB_TYPING

# Global variable to keep enum references alive, and the game and/or project paths used to cache them.
# NOTE: Only used for Binder and MSB entries at the moment, as loose files can just be selected from the file browser.
GAME_FILE_ENUMS = {
    # Loose files
    "MAP_PIECE": CachedEnum(),
    "CHRBND": CachedEnum(),
    "OBJBND": CachedEnum(),
    "PARTSBND": CachedEnum(),

    # Loose Binder entries
    "NVM": CachedEnum(),
    "HKX_MAP_COLLISION": CachedEnum(),

    # MSB parts
    "MSB_MAP_PIECE": CachedEnum(),
    "MSB_NAVMESH": CachedEnum(),
    "MSB_HKX_MAP_COLLISION": CachedEnum(),

}  # type: dict[str, CachedEnum]


def _clear_items(key: str) -> CachedEnum:
    """Clear cached enum items for the given key."""
    GAME_FILE_ENUMS[key] = CachedEnum()
    return GAME_FILE_ENUMS[key]


def CLEAR_GAME_FILE_ENUMS():
    """Forcibly clear all cached enum items (e.g. after a file export)."""
    for key in GAME_FILE_ENUMS:
        GAME_FILE_ENUMS[key] = CachedEnum()


# noinspection PyUnusedLocal
def get_map_piece_items(self, context):
    """Collect quick-importable map piece FLVERs in selected game's selected 'map/mAA_BB_CC_DD' directory.

    TODO: Not used anymore, but leaving this here as a potential future template.
    """
    key = "MAP_PIECE"

    settings = SoulstructSettings.from_context(context)
    game_map_directory = settings.get_import_map_path()
    project_map_directory = settings.get_project_map_path()
    if not is_path_and_dir(game_map_directory) and not is_path_and_dir(project_map_directory):
        return _clear_items(key).items

    # Find all map piece FLVER files in map directory.
    flver_glob = settings.game.process_dcx_path("*.flver")
    cached = GAME_FILE_ENUMS[key]
    if not cached.is_valid(game_map_directory, project_map_directory):
        cached = GAME_FILE_ENUMS[key] = CachedEnum.from_loose_files(
            game_map_directory,
            project_map_directory,
            flver_glob,
            use_value_source_suffix=True,
            desc_callback=lambda stem: f"{stem} in map {settings.map_stem}",
        )
    return cached.items


# noinspection PyUnusedLocal
def get_msb_map_piece_items(self, context):
    """Collect quick-importable `MSBMapPiece` parts in the selected game's selected map MSB.

    Does NOT 'merge' MSBs across project and game. Only uses the preferred imported MSB.

    TODO: Many MSBs, especially in later games, have too many Map Piece parts to reasonably display in Blender's limited
     enum pop-up window. I'm thinking of writing all the parts as file names to a temporarily folder and then using the
     file browser to select one of those, then deleting the temp folder afterward.
    """
    key = "MSB_MAP_PIECE"

    settings = SoulstructSettings.from_context(context)
    msb_path = settings.get_import_msb_path()  # we use preferred import location only
    if not is_path_and_file(msb_path):
        return _clear_items(key).items

    # Open MSB and find all Map Piece parts. NOTE: We don't check here if the part's model is a valid file.
    # It's up to the importer to handle and report that error case.
    cached = GAME_FILE_ENUMS[key]
    if cached.is_valid(msb_path, None):
        # Use cached enum items.
        # NOTE: Even if the MSB is written from Blender, Soulstruct cannot add or remove parts (yet).
        return cached.items

    try:
        msb_class = settings.get_game_msb_class()
        msb = get_cached_file(msb_path, msb_class)  # type: MSB_TYPING
    except (FileNotFoundError, ValueError) as ex:
        return _clear_items(key).items

    items = []
    for map_piece_part in msb.map_pieces:
        if not map_piece_part.model:
            continue  # part is missing MSB model
        full_model_name = map_piece_part.model.get_model_file_stem(settings.map_stem)
        identifier = f"{map_piece_part.name}|{full_model_name}"
        items.append(
            (identifier, map_piece_part.name, f"{map_piece_part.name} (Model {full_model_name})")
        )

    # NOTE: The cache key is the preferred imported MSB path only.
    cached = GAME_FILE_ENUMS[key] = CachedEnum(msb_path, None, items)
    return cached.items


# noinspection PyUnusedLocal
def get_nvm_items(self, context):
    """Collect navmesh NVM entries in selected game map's 'mAA_BB_CC_DD.nvmbnd' binder."""
    # TODO: Need to collect entries from both game (G) and project (P) and indicate their source in the enum value.
    key = "NVM"

    settings = SoulstructSettings.from_context(context)

    game_nvmbnd_path = settings.get_game_map_path(f"{settings.map_stem}.nvmbnd")
    project_nvmbnd_path = settings.get_project_map_path(f"{settings.map_stem}.nvmbnd")
    if not is_path_and_file(game_nvmbnd_path) and not is_path_and_file(project_nvmbnd_path):
        return _clear_items(key).items

    cached = GAME_FILE_ENUMS[key]
    if not cached.is_valid(game_nvmbnd_path, project_nvmbnd_path):
        # Find all NVM entries in map NVMBND. (Never compressed.)
        pattern = re.compile(r".*\.nvm$")
        cached = GAME_FILE_ENUMS[key] = CachedEnum.from_binder_entries(
            game_nvmbnd_path,
            project_nvmbnd_path,
            pattern,
            use_value_source_suffix=True,
        )
    return cached.items


# noinspection PyUnusedLocal
def get_nvm_part_items(self, context):
    """Collect MSB Navmesh entries in selected game map's MSB.

    TODO: Only set up for DS1.
    TODO: See Map Pieces above re: too many parts to display.
    """
    key = "MSB_NAVMESH"

    settings = SoulstructSettings.from_context(context)
    msb_path = settings.get_import_msb_path()  # we use preferred import location only
    if not is_path_and_file(msb_path):
        return _clear_items(key).items

    # Open MSB and find all Navmesh parts. NOTE: We don't check here if the part's model is a valid file.
    # It's up to the importer to handle and report that error case.
    cached = GAME_FILE_ENUMS[key]
    if cached.is_valid(msb_path, None):
        # Use cached enum items.
        # NOTE: Even if the MSB is written from Blender, Soulstruct cannot add or remove parts (yet).
        return cached.items

    try:
        msb_class = settings.get_game_msb_class()
        msb = get_cached_file(msb_path, msb_class)  # type: MSB_TYPING
    except (FileNotFoundError, ValueError) as ex:
        return _clear_items(key).items

    items = []
    for navmesh_part in msb.navmeshes:
        if not navmesh_part.model:
            continue
        full_model_name = navmesh_part.model.get_model_file_stem(settings.map_stem)
        identifier = f"{navmesh_part.name}|{full_model_name}"
        items.append(
            (identifier, navmesh_part.name, f"{navmesh_part.name} (Model {full_model_name})")
        )

    # NOTE: The cache key is the MSB path.
    cached = GAME_FILE_ENUMS[key] = CachedEnum(msb_path, None, items)
    return cached.items


# noinspection PyUnusedLocal
def get_hkx_map_collision_items(self, context):
    """Collect (hi-res) map collision HKX entries in selected game map's 'hAA_BB_CC_DD.hkxbhd' binder.

    Finds entries in both game and project directories, and indicates their source in the enum value.
    """
    key = "HKX_MAP_COLLISION"

    settings = SoulstructSettings.from_context(context)
    game_map_path = settings.get_game_map_path()
    project_map_path = settings.get_project_map_path()
    if not is_path_and_dir(game_map_path) and not is_path_and_dir(project_map_path):
        return _clear_items(key).items

    cached = GAME_FILE_ENUMS[key]
    if cached.is_valid(game_map_path, project_map_path):
        return cached.items  # use cached items

    if settings.is_game(DARK_SOULS_PTDE):
        # Loose HKX files. TODO: Need code for finding adjacent loose lo-res collisions as well.
        # TODO: Easily found, but I haven't finished map collision support for Havok 2010 yet.
        #  Just need to set up the SS Havok class and test the packfile writing.
        # return _scan_loose_files(key, map_path, "h*.hkx")
        return _clear_items(key).items
    elif settings.is_game(DARK_SOULS_DSR):
        # Compressed HKX files inside HKXBHD binder.
        game_hkxbhd_path = game_map_path / f"h{settings.map_stem[1:]}.hkxbhd"  # no DCX
        if not game_hkxbhd_path.is_file():
            game_hkxbhd_path = None
        project_hkxbhd_path = project_map_path / f"h{settings.map_stem[1:]}.hkxbhd"  # no DCX
        if not project_hkxbhd_path.is_file():
            project_hkxbhd_path = None
        pattern = re.compile(r".*\.hkx\.dcx")
        cached = GAME_FILE_ENUMS[key] = CachedEnum.from_binder_entries(
            game_hkxbhd_path,
            project_hkxbhd_path,
            pattern,
            use_value_source_suffix=True,
        )
        return cached.items

    # TODO: HKX collision not supported for other games. Not sure if I can handle `hkcdSimdTree` yet (or ever).
    return _clear_items(key).items


# noinspection PyUnusedLocal
def get_msb_hkx_map_collision_items(self, context):
    """Collect `MSBCollision` parts from selected game map's MSB."""
    key = "MSB_HKX_MAP_COLLISION"

    settings = SoulstructSettings.from_context(context)
    msb_path = settings.get_import_msb_path()  # we use preferred import location only
    if not is_path_and_file(msb_path):
        return _clear_items(key).items

    cached = GAME_FILE_ENUMS[key]
    if cached.is_valid(msb_path, None):
        # Use cached enum items.
        # NOTE: Even if the MSB is written from Blender, Soulstruct cannot add or remove parts (yet).
        return cached.items

    # Open MSB and find all Map Piece parts. NOTE: We don't check here if the part's model is a valid file.
    # It's up to the importer to handle and report that error case.

    try:
        msb_class = settings.get_game_msb_class()
        msb = get_cached_file(msb_path, msb_class)  # type: MSB_TYPING
    except (FileNotFoundError, ValueError) as ex:
        return _clear_items(key).items

    items = []
    for collision_part in msb.collisions:
        if not collision_part.model:
            continue  # part is missing MSB model
        full_model_name = collision_part.model.get_model_file_stem(settings.map_stem)
        identifier = f"{collision_part.name}|{full_model_name}"
        items.append(
            (identifier, collision_part.name, f"{collision_part.name} (Model {full_model_name})")
        )

    # NOTE: The cache key is the MSB path.
    cached = GAME_FILE_ENUMS[key] = CachedEnum(msb_path, None, items)
    return cached.items


class SoulstructGameEnums(bpy.types.PropertyGroup):
    """Files, Binder entries, and MSB entries of various types found in the game directory via on-demand scan."""

    # region Binder Entries

    nvm: bpy.props.EnumProperty(
        name="DS1 Navmesh",
        items=get_nvm_items,
    )

    hkx_map_collision: bpy.props.EnumProperty(
        name="HKX Map Collision",
        items=get_hkx_map_collision_items,
    )

    # endregion

    # region MSB Parts

    map_piece_parts: bpy.props.EnumProperty(
        name="MSB Map Piece Part",
        items=get_msb_map_piece_items,
    )

    nvm_parts: bpy.props.EnumProperty(
        name="MSB Navmesh Part",
        items=get_nvm_part_items,
    )

    hkx_map_collision_parts: bpy.props.EnumProperty(
        name="MSB Map Collision Part",
        items=get_msb_hkx_map_collision_items,
    )

    # endregion
