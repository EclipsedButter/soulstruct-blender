from __future__ import annotations

__all__ = [
    "BaseMaterialShaderInfo",
    "DS1MaterialShaderInfo",
    "BBMaterialShaderInfo",
    "ERMaterialShaderInfo",
]

import abc
import re
import typing as tp
from dataclasses import dataclass, field
from pathlib import Path

from soulstruct.base.models.flver.vertex_array import *
from soulstruct.base.models.mtd import MTD, MTDShaderCategory
from soulstruct.darksouls1r.models.mtd import MTDBND
from soulstruct.eldenring.models.matbin import MATBIN, MATBINBND
from soulstruct.utilities.files import read_json
from soulstruct.utilities.maths import Vector2

from io_soulstruct.utilities.operators import LoggingOperator


@dataclass(slots=True)
class BaseMaterialShaderInfo(abc.ABC):
    """Various summarized properties that tell Soulstruct how to generate FLVER vertex array layouts and Blender
    shader node trees (for appearance purposes only!)."""

    shader_stem: str
    # List of sampler types that FLVER material is expected to have, in order.
    sampler_types: list[str] = field(default_factory=list)
    # Ordered dict mapping sampler type names like 'g_Diffuse' to their FLVER vertex UV index/Blender layer.
    sampler_type_uv_indices: dict[str, int] = field(default_factory=dict)

    # Unknown value to write to generated `VertexArrayLayout` elements.
    type_unk_x00: int = 0

    alpha: bool = False
    edge: bool = False

    @property
    def used_uv_indices(self) -> list[int]:
        """Sorted set of UV indices used by all samplers."""
        return sorted(set(self.sampler_type_uv_indices.values()))

    # region Abstract Methods/Properties

    @abc.abstractmethod
    def get_map_piece_layout(self):
        ...

    @abc.abstractmethod
    def get_character_layout(self):
        ...

    @property
    @abc.abstractmethod
    def is_water(self) -> bool:
        ...

    @property
    @abc.abstractmethod
    def slot_count(self) -> int:
        ...

    # endregion


@dataclass(slots=True)
class DS1MaterialShaderInfo(BaseMaterialShaderInfo):

    MTD_DSBH_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[(D)?(S)?(B)?(H)?\].*")  # TODO: support 'T' (translucency)
    MTD_M_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[(M|ML|LM)\].*")  # two texture slots (Multiple)
    MTD_L_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[(L|ML|LM)\].*")  # lightmap texture slot
    MTD_N_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[(N|NL|LN)\].*")  # unshaded
    MTD_Dn_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[Dn\].*")  # unshaded
    # Checked separately: [Dn] (g_Diffuse only), [We] (g_Bumpmap only)

    # TODO: Hardcoding a set of 'foliage' shader prefixes I've encountered in DSR.
    MTD_FOLIAGE_PREFIXES: tp.ClassVar[set[str]] = {
        "M_2Foliage",
    }
    MTD_IVY_PREFIXES: tp.ClassVar[set[str]] = {
        "M_3Ivy",
    }

    # All MTD stems in DSR that use a 'FRPG_Water*' SPX shader but don't have [We] in their name.
    WATER_STEMS: tp.ClassVar[set[str]] = {
        "M_5Water[B]",  # FRPG_Water_Reflect
        "A10_00_Water_drainage",  # FRPG_Water_Reflect
        "A10_01_Water[B]",  # FRPG_Water_Reflect
        "A11_Water[W]",  # FRPG_Water_Reflect
        "A12_Little River",  # FRPG_Water_Reflect
        "A12_River",  # FRPG_Water_Reflect
        "A12_River_No reflect",  # FRPG_Water_Reflect
        "A12_Water",  # FRPG_Water_Reflect
        "A12_Water_lake",  # FRPG_Water_Reflect
        "A14Water[B]",  # FRPG_Water_Reflect
        "S[DB]_Alp_water",  # FRPG_WaterWaveSfx
        "A12_DarkRiver",  # FRPG_Water_Reflect
        "A12_DarkWater",  # FRPG_Water_Reflect
        "A12_NewWater",  # FRPG_Water_Reflect
        "A12_Water_boss",  # FRPG_Water_Reflect
    }

    SNOW_STEMS: tp.ClassVar[set[str]] = {
        "M_8Snow",  # FRPG_Snow
        "A10_slime[D][L]",  # FRPG_Snow_Lit
        "A11_Snow",  # FRPG_Snow
        "A11_Snow[L]",  # FRPG_Snow_Lit
        "A11_Snow_stair",  # FRPG_Snow
        "A11_Snow_stair[L]",  # FRPG_Snow_Lit
        "A14_numa",  # FRPG_Snow (Blighttown swamp)
        "A14_numa2",  # FRPG_Snow (Blighttown swamp)
        "A15_Tar",  # FRPG_Snow
        "A18_ash",  # FRPG_Snow
        "A19_Snow",  # FRPG_Snow
        "A19_Snow[L]",  # FRPG_Snow_Lit
    }

    # Subset of `SNOW_STEMS` that use a 'FRPG_Snow*' SPX shader and also have a 'g_SnowMetalMask' param and an extra
    # 'g_Bumpmap_3' texture type.
    SNOW_METAL_MASK_STEMS: tp.ClassVar[set[str]] = {
        "A10_slime[D][L]",  # FRPG_Snow_Lit
        "A11_Snow",  # FRPG_Snow
        "A11_Snow[L]",  # FRPG_Snow_Lit
        "A11_Snow_stair",  # FRPG_Snow
        "A11_Snow_stair[L]",  # FRPG_Snow_Lit
        "A14_numa",  # FRPG_Snow (Blighttown swamp)
        "A14_numa2",  # FRPG_Snow (Blighttown swamp)
        "A15_Tar",  # FRPG_Snow
        "A19_Snow",  # FRPG_Snow
        "A19_Snow[L]",  # FRPG_Snow_Lit
    }

    # Non-[Dn] MTD names that use `FRPG_NormalToAlpha` shader. Only one case in DS1R.
    NORMAL_TO_ALPHA_STEMS: tp.ClassVar[set[str]] = {
        "M_Tree[D]_Edge",
    }

    # TODO: Some shaders simply don't use the always-empty 'g_DetailBumpmap', but I can find no reliable way to detect
    #  this from their MTD names alone. I may have to guess that they do unless the MTD file is provided.

    spec: bool = False
    detb: bool = False  # I don't think these shaders are used in DS1. Also `g_EnvSpcSlotNo = 2`...
    shader_category: MTDShaderCategory = MTDShaderCategory.PHN

    # Has one or two extra 'g_Bumpmap' textures and 'g_Snow[Roughness/MetalMask/DiffuseF0]' params.
    # Differs in PTDE vs. DS1R.
    has_snow_roughness: bool = False

    mtd_name: str = ""

    @property
    def used_uv_indices(self) -> list[int]:
        sampler_uv_indices = set(self.sampler_type_uv_indices.values())
        if "Foliage" in self.mtd_name or "Ivy" in self.mtd_name:
            # Foliage and Ivy shaders use wind animation data in UV. We put it in maps 3 and 4.
            # Note that the second UV here (4) is often all zero in the FLVER, but it does exist.
            sampler_uv_indices |= {3, 4}
        return sorted(sampler_uv_indices)

    @classmethod
    def from_mtd(cls, mtd: MTD):
        """Extract critical MTD information (mainly for generating FLVER vertex array layouts) directly from MTD.

        NOTES:
            - There are only a couple dozen different shaders (SPX) used by all MTDs.
            - All FLVER vertex arrays have normals, at least one vertex color.
        """
        info = cls(
            shader_stem=mtd.shader_name.split(".")[0],
            mtd_name=mtd.path.name if mtd.path else "",
        )

        info.shader_category = mtd.shader_category

        for sampler in mtd.samplers:
            # NOTE: Each MTD may not use certain UV indices -- e.g. 'g_Lightmap' always uses UV index 3, even if there
            # is no second texture slot to use UV index 2. This is obviously desirable to keep the same UV layouts
            # together, and we do the same in Blender.
            info.sampler_types.append(sampler.sampler_type)
            if info.shader_category == MTDShaderCategory.SNOW and sampler.sampler_type == "g_Bumpmap_2":
                # Unfortunate known case of LIES in DS1. This texture says it uses UV index 2 (1-indexed) but actually
                # uses the first UV index, even if you add a second UV array manually.
                info.sampler_type_uv_indices[sampler.sampler_type] = 0
            else:
                info.sampler_type_uv_indices[sampler.sampler_type] = sampler.uv_index - 1  # 1-indexed -> 0-indexed

        blend_mode = mtd.get_param("g_BlendMode", default=0)
        if blend_mode == 1:
            info.edge = True
        elif blend_mode == 2:
            info.alpha = True

        env_spc_slot_no = mtd.get_param("g_EnvSpcSlotNo", default=0)
        if env_spc_slot_no == 1:
            info.spec = True

        detail_bump_power = mtd.get_param("g_DetailBump_BumpPower", default=0.0)
        if detail_bump_power > 0.0:
            info.detb = True

        # TODO: PTDE and DS1R differ here. Only the latter uses 'g_Bumpmap_3'.
        info.has_snow_roughness = mtd.has_param("g_SnowRoughness")  # only present in some Snow shaders

        return info

    @classmethod
    def from_mtd_name(cls, mtd_name: str, operator: LoggingOperator):
        """Guess as much information about the shader as possible purely from its name.

        Obviously, getting the texture names right is the most important part, but we can also guess whether the shader
        uses a lightmap (L), two texture slots (M), or has extra features like alpha (Alp/Edge).
        """
        mtd_stem = Path(mtd_name).stem
        info = cls(shader_stem=mtd_stem, mtd_name=mtd_name)

        if dsbh_match := cls.MTD_DSBH_RE.match(mtd_stem):
            if dsbh_match.group(1):
                info.sampler_types.append("g_Diffuse")
                info.sampler_type_uv_indices["g_Diffuse"] = 0
            if dsbh_match.group(2):
                info.sampler_types.append("g_Specular")
                info.sampler_type_uv_indices["g_Specular"] = 0
            if dsbh_match.group(3):
                info.sampler_types.append("g_Bumpmap")
                info.sampler_type_uv_indices["g_Bumpmap"] = 0
            if dsbh_match.group(4):
                info.sampler_types.append("g_Height")
                info.sampler_type_uv_indices["g_Height"] = 0
        elif cls.MTD_Dn_RE.match(mtd_stem) or cls.MTD_N_RE.match(mtd_stem) or mtd_stem in cls.NORMAL_TO_ALPHA_STEMS:
            # Unshaded skyboxes, mist, some trees, etc.
            info.sampler_types.append("g_Diffuse")
            info.sampler_type_uv_indices["g_Diffuse"] = 0
        elif "[We]" in mtd_stem or mtd_stem in cls.WATER_STEMS:
            # Water has a Bumpmap only.
            info.sampler_types.append("g_Bumpmap")
            info.sampler_type_uv_indices["g_Bumpmap"] = 0
        else:
            operator.warning(
                f"Unusual MTD name '{mtd_name}' could not be parsed for its textures. You may need to define it in "
                f"your own custom MTD/MTDBND."
            )

        if cls.MTD_M_RE.match(mtd_stem):
            for sampler_type, _ in info.sampler_type_uv_indices:
                # Second slot for each texture type.
                info.sampler_types.append(sampler_type + "_2")
                info.sampler_type_uv_indices[sampler_type + "_2"] = 1

        if cls.MTD_L_RE.match(mtd_stem):
            # Lightmap is present. Use third slot even if there's no second texture slot.
            info.sampler_types.append("g_Lightmap")
            info.sampler_type_uv_indices["g_Lightmap"] = 2

        if "[We]" in mtd_stem or mtd_stem in cls.WATER_STEMS:
            info.shader_category = MTDShaderCategory.WATER
        elif any(mtd_name.startswith(prefix) for prefix in cls.MTD_FOLIAGE_PREFIXES):
            # Has two extra UV slots.
            info.shader_category = MTDShaderCategory.FOLIAGE
        elif any(mtd_name.startswith(prefix) for prefix in cls.MTD_IVY_PREFIXES):
            # Has two extra UV slots.
            info.shader_category = MTDShaderCategory.IVY
        elif mtd_stem in cls.SNOW_STEMS:
            info.shader_category = MTDShaderCategory.SNOW
            # Could have an extra 'g_Bumpmap_3' texture type.
            info.has_snow_roughness = mtd_stem in cls.SNOW_METAL_MASK_STEMS
        else:
            # TODO: Can't distinguish between `Phn` and `Sfx` based on name?
            info.shader_category = MTDShaderCategory.PHN

        info.alpha = "_Alp" in mtd_stem
        info.edge = "_Edge" in mtd_stem
        info.spec = "_Spec" in mtd_stem
        info.detb = "_DetB" in mtd_stem

        if "g_Bumpmap" in info.sampler_type_uv_indices:
            # Add useless 'g_DetailBumpmap' for completion.
            # TODO: Some shaders, even with 'g_Bumpmap', do not have this. I have no way to detect from the name.
            #  Currently assuming that it doesn't matter at all if FLVERs have an (empty) texture definition for it.
            info.sampler_types.append("g_DetailBumpmap")
            info.sampler_type_uv_indices["g_DetailBumpmap"] = 0  # always

        return info

    @classmethod
    def from_mtdbnd_or_name(cls, operator: LoggingOperator, mtd_name, mtdbnd: MTDBND = None):
        """Get DS1 material info for a FLVER material, which is needed to determine which material uses which UV
                layers from Blender, and for layout generation.
                """
        if not mtdbnd:
            return cls.from_mtd_name(mtd_name, operator)

        # Use real MTD file (much less guesswork).
        try:
            mtd = mtdbnd.mtds[mtd_name]
        except KeyError:
            operator.warning(
                f"Could not find MTD '{mtd_name}' in MTD dict. Guessing info from name."
            )
            return cls.from_mtd_name(mtd_name, operator)
        return cls.from_mtd(mtd)

    @property
    def slot_count(self) -> int:
        return sum([sampler_type.startswith("g_Diffuse") for sampler_type in self.sampler_types])

    @property
    def is_water(self):
        return self.shader_category == MTDShaderCategory.WATER

    @property
    def has_tangent(self):
        """Present IFF bumpmaps are present."""
        return any(sampler.startswith("g_Bumpmap") for sampler in self.sampler_type_uv_indices)

    @property
    def has_bitangent(self):
        """Present IFF multiple bumpmaps are present (excluding extra bumpmaps for Snow shader roughness)."""
        return self.has_tangent and self.slot_count == 2

    @property
    def has_lightmap(self):
        return "g_Lightmap" in self.sampler_type_uv_indices

    @property
    def has_detail_bumpmap(self):
        return "g_DetailBumpmap" in self.sampler_type_uv_indices

    def get_map_piece_layout(self) -> VertexArrayLayout:
        """Get a standard DS1 map piece layout with the given number of UV layers."""

        data_types = [  # always present
            VertexPosition(VertexDataFormatEnum.Float3, 0),
            VertexBoneIndices(VertexDataFormatEnum.FourBytesB, 0),
            VertexNormal(VertexDataFormatEnum.FourBytesC, 0),
            # Tangent/Bitangent will be inserted here if needed.
            VertexColor(VertexDataFormatEnum.FourBytesC, 0),
            # UV/UVPair will be inserted here if needed.
        ]

        if self.has_tangent:
            data_types.insert(3, VertexTangent(VertexDataFormatEnum.FourBytesC, 0))
            if self.slot_count > 1:  # uses `bitangent` for second slot
                data_types.insert(4, VertexBitangent(VertexDataFormatEnum.FourBytesC, 0))
        elif self.slot_count > 1:  # has Bitangent but not Tangent (probably never happens)
            data_types.insert(3, VertexBitangent(VertexDataFormatEnum.FourBytesC, 0))

        uv_member_index = 0
        uv_count = len(self.used_uv_indices)
        while uv_count > 0:  # extra UVs
            # For odd counts, single UV member is added first.
            if uv_count % 2:
                data_types.append(VertexUV(VertexDataFormatEnum.UV, uv_member_index))
                uv_count -= 1
                uv_member_index += 1
            else:  # must be a non-zero even number remaining
                # Use a UVPair member.
                data_types.append(VertexUV(VertexDataFormatEnum.UVPair, uv_member_index))
                uv_count -= 2
                uv_member_index += 1

        for data_type in data_types:
            data_type.unk_x00 = self.type_unk_x00

        return VertexArrayLayout(data_types)

    def get_character_layout(self) -> VertexArrayLayout:
        """Get a standard vertex array layout for character (and probably object) materials in DS1."""
        data_types = [
            VertexPosition(VertexDataFormatEnum.Float3, 0),
            VertexBoneIndices(VertexDataFormatEnum.FourBytesB, 0),
            VertexBoneWeights(VertexDataFormatEnum.FourShortsToFloats, 0),
            VertexNormal(VertexDataFormatEnum.FourBytesC, 0),
            VertexTangent(VertexDataFormatEnum.FourBytesC, 0),
            VertexColor(VertexDataFormatEnum.FourBytesC, 0),
        ]
        # TODO: Assuming no DS1 character material (or any material) has more than two slots.
        uv_count = len(self.used_uv_indices)
        if uv_count == 2:  # has Bitangent and UVPair
            data_types.insert(5, VertexBitangent(VertexDataFormatEnum.FourBytesC, 0))
            data_types.append(VertexUV(VertexDataFormatEnum.UVPair, 0))
        elif uv_count == 1:  # one UV
            data_types.append(VertexUV(VertexDataFormatEnum.UV, 0))
        else:
            raise ValueError(f"Invalid UV count for DS1 character layout: {uv_count}. Must be 1 or 2.")

        for data_type in data_types:
            data_type.unk_x00 = 0  # DS1

        return VertexArrayLayout(data_types)


@dataclass(slots=True)
class BBMaterialShaderInfo(BaseMaterialShaderInfo):

    ARSN_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[(A)?(R)?(S)?(N)?\].*")
    M_RE: tp.ClassVar[re.Pattern] = re.compile(r".*_m(_.*|$)")  # two texture slots (Multiple)
    L_RE: tp.ClassVar[re.Pattern] = re.compile(r".*_l(_.*|$)")  # lightmap texture slot
    Dn_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[Dn\].*")  # unshaded
    # Checked separately: [Dn] (g_Diffuse only), [We] (g_Bumpmap only)

    shader_category: MTDShaderCategory = MTDShaderCategory.PHN
    mtd_name: str = ""

    @classmethod
    def from_mtd(cls, mtd: MTD):
        """Extract critical MTD information (mainly for generating FLVER vertex array layouts) directly from MTD.

        NOTES:
            - There are only a couple dozen different shaders (SPX) used by all MTDs.
            - All FLVER vertex arrays have normals, at least one vertex color.
        """
        info = cls(
            shader_stem=mtd.shader_stem,
            mtd_name=mtd.path.name if mtd.path else "",
        )

        info.shader_category = mtd.shader_category

        for sampler in mtd.samplers:
            # NOTE: Each MTD may not use certain UV indices -- e.g. 'g_Lightmap' always uses UV index 3, even if there
            # is no second texture slot to use UV index 2. This is obviously desirable to keep the same UV layouts
            # together, and we do the same in Blender.
            info.sampler_types.append(sampler.sampler_type)
            # TODO: Check for 'UV index lies' like in `FRPG_Snow` shader in DS1.
            info.sampler_type_uv_indices[sampler.sampler_type] = sampler.uv_index  # 1-indexed!

        blend_mode = mtd.get_param("g_BlendMode", default=0)
        if blend_mode == 1:
            info.edge = True
        elif blend_mode == 2:
            info.alpha = True

        env_spc_slot_no = mtd.get_param("g_EnvSpcSlotNo", default=0)
        if env_spc_slot_no == 1:
            info.spec = True

        return info

    @classmethod
    def from_mtd_name(cls, mtd_name: str, operator: LoggingOperator):
        """Guess as much information about the shader as possible purely from its name.

        Obviously, getting the texture names right is the most important part, but we can also guess whether the shader
        uses a lightmap (L), two texture slots (M), or has extra features like alpha (Alp/Edge).
        """
        mtd_stem = Path(mtd_name).stem
        info = cls(shader_stem=mtd_stem, mtd_name=mtd_name)

        if arsn_match := cls.ARSN_RE.match(mtd_stem):
            # NOTE: The 'ARSN' initials don't match up with the sampler slot names (except Shininess).
            if arsn_match.group(1):
                info.sampler_types.append("g_DiffuseTexture")  # Albedo
                info.sampler_type_uv_indices["g_DiffuseTexture"] = 1
            if arsn_match.group(2):
                info.sampler_types.append("g_SpecularTexture")  # Reflective
                info.sampler_type_uv_indices["g_SpecularTexture"] = 1
            if arsn_match.group(3):
                info.sampler_types.append("g_ShininessTexture")  # Shininess
                info.sampler_type_uv_indices["g_ShininessTexture2"] = 1
            if arsn_match.group(4):
                info.sampler_types.append("g_BumpmapTexture")  # Normal
                info.sampler_type_uv_indices["g_BumpmapTexture"] = 1
        elif cls.Dn_RE.match(mtd_stem):
            # Unshaded skyboxes, mist, some trees, etc.
            info.sampler_types.append("g_DiffuseTexture")
            info.sampler_type_uv_indices["g_DiffuseTexture"] = 1
        # TODO: water samplers?
        # elif "[We]" in mtd_stem or mtd_stem in cls.WATER_STEMS:
        #     # Water has a Bumpmap only.
        #     info.sampler_types.append("g_BumpmapTexture")
        #     info.sampler_type_uv_indices["g_BumpmapTexture"] = 1
        else:
            operator.warning(
                f"Unusual MTD name '{mtd_name}' could not be parsed for its textures. You may need to define it in "
                f"your own custom MTD/MTDBND."
            )

        if cls.M_RE.match(mtd_stem):
            for sampler_type, _ in info.sampler_type_uv_indices:
                # Second slot for each texture type.
                info.sampler_types.append(sampler_type + "2")  # no underscore
                info.sampler_type_uv_indices[sampler_type + "2"] = 2

        if cls.L_RE.match(mtd_stem):
            # Lightmap is present. Slot is 3 even if there's no second texture slot.
            info.sampler_types.append("g_Lightmap")
            info.sampler_type_uv_indices["g_Lightmap"] = 3

        # TODO: needs work
        if "water" in mtd_stem.lower():
            info.shader_category = MTDShaderCategory.WATER
        else:
            # TODO: Can't distinguish between `Phn` and `Sfx` based on name?
            info.shader_category = MTDShaderCategory.PHN

        info.alpha = "_alp" in mtd_stem.lower()
        info.edge = "_edge" in mtd_stem.lower()
        info.spec = False

        if "g_Bumpmap" in info.sampler_type_uv_indices:
            # Add useless 'g_DetailBumpmap' for completion.
            # TODO: Some shaders, even with 'g_Bumpmap', do not have this. I have no way to detect from the name.
            #  Currently assuming that it doesn't matter at all if FLVERs have an (empty) texture definition for it.
            info.sampler_types.append("g_DetailBumpmap")
            info.sampler_type_uv_indices["g_DetailBumpmap"] = 1  # always

        return info

    @classmethod
    def from_mtdbnd_or_name(cls, operator: LoggingOperator, mtd_name, mtdbnd: MTDBND = None):
        """Get DS1 material info for a FLVER material, which is needed to determine which material uses which UV
                layers from Blender, and for layout generation.
                """
        if not mtdbnd:
            return cls.from_mtd_name(mtd_name, operator)

        # Use real MTD file (much less guesswork).
        try:
            mtd = mtdbnd.mtds[mtd_name]
        except KeyError:
            operator.warning(
                f"Could not find MTD '{mtd_name}' in MTD dict. Guessing info from name."
            )
            return cls.from_mtd_name(mtd_name, operator)
        return cls.from_mtd(mtd)

    @property
    def slot_count(self) -> int:
        return sum([sampler_type.startswith("g_Diffuse") for sampler_type in self.sampler_types])

    @property
    def is_water(self):
        return self.shader_category == MTDShaderCategory.WATER

    @property
    def has_tangent(self):
        """Present IFF bumpmaps are present."""
        return any(sampler.startswith("g_Bumpmap") for sampler in self.sampler_type_uv_indices)

    @property
    def has_bitangent(self):
        """Present IFF multiple bumpmaps are present (excluding extra bumpmaps for Snow shader roughness)."""
        return self.has_tangent and self.slot_count == 2

    @property
    def has_lightmap(self):
        return "g_Lightmap" in self.sampler_type_uv_indices

    @property
    def has_detail_bumpmap(self):
        return "g_DetailBumpmap" in self.sampler_type_uv_indices

    def get_map_piece_layout(self) -> VertexArrayLayout:
        """Get a standard DS1 map piece layout."""

        data_types = [  # always present
            VertexPosition(VertexDataFormatEnum.Float3, 0),
            VertexBoneIndices(VertexDataFormatEnum.FourBytesB, 0),
            VertexNormal(VertexDataFormatEnum.FourBytesC, 0),
            # Tangent/Bitangent will be inserted here if needed.
            VertexColor(VertexDataFormatEnum.FourBytesC, 0),
            # UV/UVPair will be inserted here if needed.
        ]

        if self.has_tangent:
            data_types.insert(3, VertexTangent(VertexDataFormatEnum.FourBytesC, 0))
            if self.slot_count > 1:  # still has Bitangent
                # TODO: Why is Bitangent needed for double slots? Does it actually hold a second tangent or something?
                data_types.insert(4, VertexBitangent(VertexDataFormatEnum.FourBytesC, 0))
        elif self.slot_count > 1:  # has Bitangent but not Tangent (probably never happens)
            data_types.insert(3, VertexBitangent(VertexDataFormatEnum.FourBytesC, 0))

        # Calculate total UV map count and use a combination of UVPair and UV format members below.
        uv_count = len(self.used_uv_indices)
        if uv_count > 4:
            # TODO: Might be an unnecessary assertion. True for DS1, for sure.
            raise ValueError(f"Cannot have more than 4 UV maps in a vertex array (got {uv_count}).")

        uv_member_index = 0
        while uv_count > 0:  # extra UVs
            # For odd counts, single UV member is added first.
            if uv_count % 2:
                data_types.append(VertexUV(VertexDataFormatEnum.UV, uv_member_index))
                uv_count -= 1
                uv_member_index += 1
            else:  # must be a non-zero even number remaining
                # Use a UVPair member.
                data_types.append(VertexUV(VertexDataFormatEnum.UVPair, uv_member_index))
                uv_count -= 2
                uv_member_index += 1

        for data_type in data_types:
            data_type.unk_x00 = self.type_unk_x00

        return VertexArrayLayout(data_types)

    def get_character_layout(self) -> VertexArrayLayout:
        """Get a standard vertex array layout for character (and probably object) materials in DS1."""
        data_types = [
            VertexPosition(VertexDataFormatEnum.Float3, 0),
            VertexBoneIndices(VertexDataFormatEnum.FourBytesB, 0),
            VertexBoneWeights(VertexDataFormatEnum.FourShortsToFloats, 0),
            VertexNormal(VertexDataFormatEnum.FourBytesC, 0),
            VertexTangent(VertexDataFormatEnum.FourBytesC, 0),
            VertexColor(VertexDataFormatEnum.FourBytesC, 0),
        ]
        # TODO: Assuming no character material (or any material) has more than two slots.
        if self.slot_count > 1:  # has Bitangent and UVPair
            data_types.insert(5, VertexBitangent(VertexDataFormatEnum.FourBytesC, 0))
            data_types.append(VertexUV(VertexDataFormatEnum.UVPair, 0))
        else:  # one UV
            data_types.append(VertexUV(VertexDataFormatEnum.UV, 0))

        for data_type in data_types:
            data_type.unk_x00 = 0  # DS1

        return VertexArrayLayout(data_types)


@dataclass(slots=True)
class ERMaterialShaderInfo(BaseMaterialShaderInfo):

    METAPARAMS: tp.ClassVar[dict[str, list[dict[str, str]]]] = read_json(
        Path(__file__).parent / "resources/er_shader_metaparams.json"
    )

    # Basic shader stem segments, each in square brackets.
    AMSN_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[(?P<A>A)?(?P<M>M)?(?P<S>S)?(?P<N>N)?(?P<V>_V)?\].*")
    MULTI_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[Mb(?P<count>\d)(?P<suffix>_[_\w]+)?\].*")  # 2 to 5 observed
    OV_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[Ov_(?P<suffix>[_\w]+)\].*")  # e.g. '[Ov_N]'
    FAR_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[Far_(?P<suffix>[_\w]+)\].*")  # e.g. '[Far_AN]'

    # Special shader types.
    SPIDERWEB_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[Spiderweb\].*")
    TRANSLUCENCY_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[Translucency\].*")
    WAX_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[Wax\].*")
    SWAY_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[Sway\].*")
    MASK_RE: tp.ClassVar[re.Pattern] = re.compile(r".*\[(?P<mask>\d)Mask(?P<suffix>_[_\w]+)?\].*")  # e.g. 'ch18'
    # TODO: A bunch more: Birds, Birds_liner, Flag, Flag2, Flag3, Flower_m10, Interior, PlacidLake, Rainbow, Sky...
    #  Probably easiest to have a simple list of these 'one-word' bracketed labels.

    # Shader suffix patterns.
    # TODO: These never seem to be combined, but potentially could be. Maybe safest to split name by final square
    #  bracket and run a check for '_{suffix}[_$]' for each suffix.
    Alpha_RE: tp.ClassVar[re.Pattern] = re.compile(r".*_Alpha$")
    Edge_RE: tp.ClassVar[re.Pattern] = re.compile(r".*_Edge$")
    Emissive_Glow_RE: tp.ClassVar[re.Pattern] = re.compile(r".*_Emissive_Glow$")
    Grass_RE: tp.ClassVar[re.Pattern] = re.compile(r".*_Grass$")
    Grass2_RE: tp.ClassVar[re.Pattern] = re.compile(r".*_Grass2$")
    Grass2_LOD1_RE: tp.ClassVar[re.Pattern] = re.compile(r".*_Grass2_LOD1$")
    MeshDecalBlend_RE: tp.ClassVar[re.Pattern] = re.compile(r".*_MeshDecalBlend$")
    Skin_PaintDecal_RE: tp.ClassVar[re.Pattern] = re.compile(r".*_Skin_PaintDecal$")
    Vesitation_RE: tp.ClassVar[re.Pattern] = re.compile(r".*_Vesitation$")  # surely typo of 'Visitation'
    NoLight_RE: tp.ClassVar[re.Pattern] = re.compile(r".*_NoLight.*")  # TODO: seen with '_Alpha' after it

    # AMSN
    albedo: bool = True
    metallic: bool = True
    sheen: bool = True
    normal: bool = True  # bumpmap
    v: bool = False  # TODO: presence implies absence of metallic?

    # Maps sampler names to their UV scale, which is specified (by UV group) in MATBIN params.
    sampler_uv_scales: dict[str, Vector2] = field(default_factory=dict)
    sampler_uv_groups: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_matbin(cls, matbin: MATBIN):
        """Extract critical material information directly from MATBIN.

        TODO: Focusing on characters first, as they use relatively few shaders ('C[DetailBlend]', 'C[Fur', etc.).
        """

        info = cls(shader_stem=matbin.shader_stem)

        for sampler in matbin.samplers:
            info.sampler_types.append(sampler.sampler_type)
            # TODO: How to detect UV index in ER?

        # Still here, like in MTD.
        blend_mode = matbin.get_param("g_BlendMode", default=0)
        if blend_mode == 1:
            info.edge = True
        elif blend_mode == 2:
            info.alpha = True

        # print(f"   Shader: {matbin.shader_name}")
        amsn = cls.AMSN_RE.match(matbin.shader_stem)
        if amsn:  # entire group could be absent
            info.albedo = bool(amsn.group("A"))
            info.metallic = bool(amsn.group("M"))
            info.sheen = bool(amsn.group("S"))
            info.normal = bool(amsn.group("N"))
            info.v = bool(amsn.group("V"))
        # else:
        #     for sampler in matbin.samplers:
        #         print("   ", sampler.sampler_type, sampler.path, sampler.key, sampler.unk_x14)

        info.shader_stem = matbin.shader_name.split(".")[0]

        metaparam = cls.METAPARAMS.get(info.shader_stem, None)
        if not metaparam:
            raise ValueError(
                f"No shader metaparam information known to Soulstruct for shader '{matbin.shader_name}'. Cannot get "
                f"Blender material info, as sampler UV grouping cannot be determined."
            )
        grouped_sampler_types = {}  # type: dict[str, list[str]]
        for sampler in metaparam:
            group_name = sampler["group_name"]
            if group_name:
                grouped_sampler_types.setdefault(group_name, []).append(sampler["name"])

        info.sampler_type_uv_indices = {sampler.sampler_type: 0 for sampler in matbin.samplers}  # default 0
        first_texture_found = False  # first group uses UV index 0; remainder all use index 2 for non-blend textures
        for group_name in sorted(grouped_sampler_types):
            sampler_types = grouped_sampler_types[group_name]

            if not group_name:
                # Unlabelled group. Leave UV index as default (0).
                for sampler in sampler_types:
                    info.sampler_uv_scales[sampler] = Vector2.one()
                continue

            group_index = int(group_name.split("_")[1])
            uv_scale = Vector2(matbin.get_param(f"group_{group_index}_CommonUV-UVParam", default=(1.0, 1.0)))
            for sampler in sampler_types:
                info.sampler_uv_scales[sampler] = uv_scale
                info.sampler_uv_groups[sampler] = group_index

            if any("albedo" in sampler.lower() for sampler in sampler_types):
                # Standard texture.
                # TODO: Meow's hotfix for handling Elden Ring fur blur samplers.
                #  Looks like we still allow UV index 0 for the NEXT group if this group is 'furblurnoise'.
                is_fur_blur = False
                for sampler in sampler_types:
                    if "albedo" in sampler.lower() or "metallic" in sampler.lower() or "normal" in sampler.lower():
                        info.sampler_type_uv_indices[sampler] = 0 if not first_texture_found else 2
                        if "furblurnoise" in str(matbin.get_sampler_path(sampler)):
                            is_fur_blur = True
                    elif "mask" in sampler.lower():  # will catch "blendmask"
                        info.sampler_type_uv_indices[sampler] = 1
                    elif "mask3" in sampler.lower():
                        info.sampler_type_uv_indices[sampler] = 0  # being explicit
                    # Otherwise, leave as default 0.
                if not is_fur_blur:
                    first_texture_found = True
            else:
                # Just check for blend samplers and leave others as UV index 0.
                for sampler in sampler_types:
                    if "mask" in sampler.lower():  # will catch "blendmask"
                        info.sampler_type_uv_indices[sampler] = 1

        # TODO: Notes.
        #  - The sampler types have prefixes from the shader stem, with square brackets replaced by underscores,
        #  followed by '_snp_', then a meaningful suffix like 'Texture2D_2_AlbedoMap_0'.
        #   - Not sure what 'snp' means, but it could just be 'specular, normal, physical' or something.
        #       - Could also be a mistranslated abbreviation of 'sampler'?
        #   - 'Texture2D' obviously fairly standard.
        #  - The index after that varies. Some kind of slot. Seems always unique, but not always contiguous, and also
        #    kind of random in order (e.g. normal 1, normal 2, albedo 1, albedo 2, mask1map, normal 0).
        #  - Then map type, then 'group' of that map type (but only in the same slot?).
        #   - I know it's 'group' because it corresponds to present 'group_#_CommonUV-UVParam' params.
        #   - Although the numbering doesn't always line up. [Mb2][Ov_N] has three UV 'group' params but has two real
        #     albedo/normal groups plus the extra normal map.
        #  - 'Multi-group' materials appear to have [Mb#] in the shader stem. Have seen 2 and 3 so far.
        #   - They also have 'GSBlendMap' between the index and map type in the sampler type.
        #   - They also have an extra sampler slot with type '_BlendEdge' (extra underscore) or 'Mask1Map'.
        #  - '[Ov_N]' shader suffix seems to be just albedo and normal. No metallic. Has two normals in same group;
        #    possibly 'standard' (7) and 'detailed' (2).
        #  - Shaders with no suffix, like just 'M[AMSN_V], have one albedo and one bumpmap.
        #  - Suffixes can stack: [Mb2][Ov_N] has two albedo/normal groups AND one extra normal (plus 'Mask1Map').
        #  - '[Ov_AN]' suffix has an extra albedo AND normal map (though I've seen the normal map path empty).
        #  - '[Sway]' suffix probably for... swaying stuff like trees. Has a few 'Sway' param floats defined.
        #  - g_BlendMode == 2 for alpha, 0 otherwise. Have seen no other values.
        #  - 'M[A]' has albedo only. Have only seen this used for low-ID materials using dummy SYSTEX textures.
        #  - The V in M[AMSN_V] seems to indicate the ABSENCE of metallic textures.

        # TODO: Action items.
        #  - First order, to get import working, is just to detect basic shader setups in the same way as DS1.
        #   - Need to handle multi-groups, name textures appropriately, and find DDS textures in AET/TEX binders.
        #   - Node tree builder below

        return info

    @classmethod
    def from_matbin_name(cls, matbin_name, operator: LoggingOperator):
        """Guess as much information about the shader as possible purely from its name.

        Obviously, getting the texture names right is the most important part, but we can also guess whether the shader
        uses a lightmap (L), two texture slots (M), or has extra features like alpha (Alp/Edge).
        """
        raise NotImplementedError("Cannot yet guess ER shader info from name. MATBIN must be given.")

    @classmethod
    def from_matbin_name_or_matbinbnd(cls, operator: LoggingOperator, matbin_name: str, matbinbnd: MATBINBND = None):
        """Get info for a FLVER material, which is needed for both material creation and assignment of vertex UV
        data to the correct Blender UV data layer during mesh creation.
        """
        if not matbinbnd:
            raise NotImplementedError("Cannot yet guess MATBIN info from name. MATBINBND must be given.")

        # Use real MATBIN file (much less guesswork -- currently required).
        try:
            matbin = matbinbnd.get_matbin(matbin_name)
        except KeyError:
            raise NotImplementedError(f"Could not find MATBIN '{matbin_name}' in MATBINBND and cannot yet guess info.")
        # print()
        # print(matbin_name)  # todo
        return cls.from_matbin(matbin)

    @property
    def slot_count(self) -> int:
        return 2 if 2 in self.used_uv_indices else 1

    @property
    def is_water(self):
        return False  # TODO

    def get_map_piece_layout(self) -> VertexArrayLayout:
        """Get a standard ER map piece layout."""

        data_types = [  # always present
            VertexPosition(VertexDataFormatEnum.Float3, 0),
            VertexBoneIndices(VertexDataFormatEnum.FourBytesB, 0),
            VertexNormal(VertexDataFormatEnum.FourBytesC, 0),
            # Tangent/Bitangent will be inserted here if needed.
            VertexColor(VertexDataFormatEnum.FourBytesC, 0),
            # UV/UVPair will be inserted here if needed.
        ]

        if self.has_tangent:
            data_types.insert(3, VertexTangent(VertexDataFormatEnum.FourBytesC, 0))
            if self.slot_count > 1:  # still has Bitangent
                # TODO: Why is Bitangent needed for double slots? Does it actually hold a second tangent or something?
                data_types.insert(4, VertexBitangent(VertexDataFormatEnum.FourBytesC, 0))
        elif self.slot_count > 1:  # has Bitangent but not Tangent (probably never happens)
            data_types.insert(3, VertexBitangent(VertexDataFormatEnum.FourBytesC, 0))

        # Calculate total UV map count and use a combination of UVPair and UV format members below.
        uv_count = self.slot_count  # TODO: + int(self.has_lightmap)

        # TODO
        # if self.shader_category in {MTDShaderCategory.FOLIAGE, MTDShaderCategory.IVY}:
        #     # Foliage shaders have two extra UV slots for wind animation control.
        #     uv_count += 2

        if uv_count > 4:
            # TODO: Might be an unnecessary assertion. True for DS1, for sure.
            raise ValueError(f"Cannot have more than 4 UV maps in a vertex array (got {uv_count}).")

        uv_member_index = 0
        while uv_count > 0:  # extra UVs
            # For odd counts, single UV member is added first.
            if uv_count % 2:
                data_types.append(VertexUV(VertexDataFormatEnum.UV, uv_member_index))
                uv_count -= 1
                uv_member_index += 1
            else:  # must be a non-zero even number remaining
                # Use a UVPair member.
                data_types.append(VertexUV(VertexDataFormatEnum.UVPair, uv_member_index))
                uv_count -= 2
                uv_member_index += 1

        for data_type in data_types:
            data_type.unk_x00 = self.type_unk_x00

        return VertexArrayLayout(data_types)

    def get_character_layout(self) -> VertexArrayLayout:
        """Get a standard vertex array layout for character (and probably object) materials in ER."""
        # TODO: Need to detect number of tangents (UV count? Replaces bitangent?) and vertex color count.
        data_types = [
            VertexPosition(VertexDataFormatEnum.Float3, 0),
            VertexNormal(VertexDataFormatEnum.FourBytesB, 0),
            VertexTangent(VertexDataFormatEnum.FourBytesB, 0),
            VertexBoneIndices(VertexDataFormatEnum.FourBytesB, 0),
            VertexBoneWeights(VertexDataFormatEnum.FourBytesC, 0),
            VertexColor(VertexDataFormatEnum.FourBytesC, 0),
            VertexColor(VertexDataFormatEnum.FourBytesC, 0),
        ]
        if self.slot_count > 1:  # has UVPair
            data_types.append(VertexUV(VertexDataFormatEnum.UVPair, 0))
        else:  # one UV
            data_types.append(VertexUV(VertexDataFormatEnum.UV, 0))

        for data_type in data_types:
            data_type.unk_x00 = self.type_unk_x00

        return VertexArrayLayout(data_types)