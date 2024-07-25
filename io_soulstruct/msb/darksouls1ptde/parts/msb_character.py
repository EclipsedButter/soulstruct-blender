from __future__ import annotations

__all__ = [
    "BlenderMSBCharacter",
]

import traceback
import typing as tp

import bpy
from io_soulstruct.exceptions import FLVERImportError
from io_soulstruct.flver.textures.import_textures import TextureImportManager
from io_soulstruct.flver.models import BlenderFLVER
from io_soulstruct.flver.utilities import get_flvers_from_binder
from io_soulstruct.msb.properties import MSBPartSubtype, MSBCharacterProps
from io_soulstruct.msb.utilities import find_flver_model
from io_soulstruct.types import *
from io_soulstruct.utilities import LoggingOperator, get_collection
from soulstruct.containers import Binder
from soulstruct.darksouls1ptde.maps.parts import MSBCharacter, MSBDummyCharacter
from .msb_part import BlenderMSBPart

if tp.TYPE_CHECKING:
    from soulstruct.darksouls1ptde.maps.msb import MSB


class BlenderMSBCharacter(BlenderMSBPart[MSBCharacter, MSBCharacterProps]):

    OBJ_DATA_TYPE = SoulstructDataType.MESH
    SOULSTRUCT_CLASS = MSBCharacter
    PART_SUBTYPE = MSBPartSubtype.CHARACTER
    MODEL_SUBTYPES = ["character_models"]

    data: bpy.types.Mesh  # type override

    AUTO_CHARACTER_PROPS = [
        "ai_id",
        "character_id",
        "talk_id",
        "platoon_id",
        "patrol_type",
        "player_id",
        "default_animation",
        "damage_animation",
    ]

    draw_parent: bpy.types.Object | None
    ai_id: int
    character_id: int
    talk_id: int
    platoon_id: int
    patrol_type: int
    player_id: int
    default_animation: int
    damage_animation: int

    @property
    def patrol_regions(self) -> list[bpy.types.Object | None]:
        return [
            getattr(self.subtype_properties, f"patrol_regions_{i}")
            for i in range(8)
        ]

    @patrol_regions.setter
    def patrol_regions(self, value: list[bpy.types.Object | None]):
        if len(value) > 8:
            raise ValueError("Cannot set more than 8 MSB Character patrol regions.")
        count = len(value)
        for i in range(8):
            if i < count:
                setattr(self.subtype_properties, f"patrol_regions_{i}", value[i])
            else:
                setattr(self.subtype_properties, f"patrol_regions_{i}", None)

    @classmethod
    def new_from_soulstruct_obj(
        cls,
        operator: LoggingOperator,
        context: bpy.types.Context,
        soulstruct_obj: MSBCharacter,
        name: str,
        collection: bpy.types.Collection = None,
        map_stem="",
    ) -> tp.Self:
        bl_character = super().new_from_soulstruct_obj(
            operator, context, soulstruct_obj, name, collection, map_stem
        )  # type: tp.Self

        bl_character.character_props.is_dummy = isinstance(soulstruct_obj, MSBDummyCharacter)
        bl_character.draw_parent = cls.entry_ref_to_bl_obj(
            operator, soulstruct_obj, "draw_parent", soulstruct_obj.draw_parent, SoulstructType.MSB_PART
        )

        bl_character.patrol_regions = [
            cls.entry_ref_to_bl_obj(
                operator,
                soulstruct_obj,
                f"patrol_regions[{i}]",
                soulstruct_obj.patrol_regions[i],
                SoulstructType.MSB_REGION,
            )
            for i in range(8)
        ]

        for name in cls.AUTO_CHARACTER_PROPS:
            setattr(bl_character, name, getattr(soulstruct_obj, name))

        return bl_character

    def create_soulstruct_obj(self):
        if self.subtype_properties.is_dummy:
            return MSBDummyCharacter(name=self.tight_name)
        return MSBCharacter(name=self.tight_name)

    def to_soulstruct_obj(
        self,
        operator: LoggingOperator,
        context: bpy.types.Context,
        map_stem="",
        msb: MSB = None,
    ) -> MSBCharacter:
        msb_character = super().to_soulstruct_obj(operator, context, map_stem, msb)  # type: MSBCharacter

        msb_character.draw_parent = self.bl_obj_to_entry_ref(msb, "draw_parent", self.draw_parent, msb_character)
        for i, bl_region in enumerate(self.patrol_regions):
            msb_character.patrol_regions[i] = self.bl_obj_to_entry_ref(
                msb, f"patrol_regions[{i}]", bl_region, msb_character
            )

        for name in self.AUTO_CHARACTER_PROPS:
            setattr(msb_character, name, getattr(self, name))

        return msb_character

    @classmethod
    def find_model(cls, model_name: str, map_stem: str):
        return find_flver_model(cls.PART_SUBTYPE, model_name)

    @classmethod
    def import_model(
        cls,
        operator: LoggingOperator,
        context: bpy.types.Context,
        model_name: str,
        map_stem="",  # not used
    ) -> BlenderFLVER:
        """Import the model of the given name into a collection in the current scene."""
        settings = operator.settings(context)

        flver_import_settings = context.scene.flver_import_settings
        chrbnd_path = settings.get_import_file_path(f"chr/{model_name}.chrbnd")

        operator.info(f"Importing character FLVER from: {chrbnd_path.name}")

        texture_import_manager = TextureImportManager(settings) if flver_import_settings.import_textures else None

        chrbnd = Binder.from_path(chrbnd_path)
        binder_flvers = get_flvers_from_binder(chrbnd, chrbnd_path, allow_multiple=False)
        if texture_import_manager:
            texture_import_manager.find_flver_textures(chrbnd_path, chrbnd)
        flver = binder_flvers[0]

        try:
            return BlenderFLVER.new_from_soulstruct_obj(
                operator,
                context,
                flver,
                model_name,
                texture_import_manager,
                collection=get_collection("Character Models", context.scene.collection),
            )
        except Exception as ex:
            traceback.print_exc()  # for inspection in Blender console
            raise FLVERImportError(f"Cannot import FLVER from CHRBND: {chrbnd_path.name}. Error: {ex}")


BlenderMSBCharacter.add_auto_subtype_props(*BlenderMSBCharacter.AUTO_CHARACTER_PROPS)
