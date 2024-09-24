
__all__ = []  # no star import

import typing as tp

if tp.TYPE_CHECKING:

    from soulstruct.base.maps.msb.parts import BaseMSBPart
    from soulstruct.base.maps.msb.regions import BaseMSBRegion
    from soulstruct.base.maps.msb.events import BaseMSBEvent

    from soulstruct.darksouls1ptde.maps.msb import MSB as PTDE_MSB
    from soulstruct.darksouls1r.maps.msb import MSB as DS1R_MSB
    from soulstruct.bloodborne.maps.msb import MSB as BB_MSB
    from soulstruct.eldenring.maps.msb import MSB as ER_MSB
    MSB_TYPING = tp.Union[PTDE_MSB, DS1R_MSB, BB_MSB, ER_MSB]

    from soulstruct.darksouls1ptde.maps.parts import MSBPart as PTDE_MSBPart
    from soulstruct.darksouls1r.maps.parts import MSBPart as DS1R_MSBPart
    from soulstruct.bloodborne.maps.parts import MSBPart as BB_MSBPart
    from soulstruct.eldenring.maps.parts import MSBPart as ER_MSBPart
    MSB_PART_TYPING = tp.Union[BaseMSBPart, PTDE_MSBPart, DS1R_MSBPart, BB_MSBPart, ER_MSBPart]

    from soulstruct.darksouls1ptde.maps.parts import MSBMapPiece as PTDE_MSBMapPiece
    from soulstruct.darksouls1r.maps.parts import MSBMapPiece as DS1R_MSBMapPiece
    from soulstruct.bloodborne.maps.parts import MSBMapPiece as BB_MSBMapPiece
    from soulstruct.eldenring.maps.parts import MSBMapPiece as ER_MSBMapPiece
    MSB_MAPPIECE_TYPING = tp.Union[BaseMSBPart, PTDE_MSBMapPiece, DS1R_MSBMapPiece, BB_MSBMapPiece, ER_MSBMapPiece]

    from soulstruct.darksouls1ptde.maps.parts import MSBCollision as PTDE_MSBCollision
    from soulstruct.darksouls1r.maps.parts import MSBCollision as DS1R_MSBCollision
    from soulstruct.bloodborne.maps.parts import MSBCollision as BB_MSBCollision
    from soulstruct.eldenring.maps.parts import MSBCollision as ER_MSBCollision
    MSB_COLLISION_TYPING = tp.Union[BaseMSBPart, PTDE_MSBCollision, DS1R_MSBCollision, BB_MSBCollision, ER_MSBCollision]

    from soulstruct.darksouls1ptde.maps.parts import MSBNavmesh as PTDE_MSBNavmesh
    from soulstruct.darksouls1r.maps.parts import MSBNavmesh as DS1R_MSBNavmesh
    from soulstruct.bloodborne.maps.parts import MSBNavmesh as BB_MSBNavmesh
    # Elden Ring has no MSB navmeshes.
    MSB_NAVMESH_TYPING = tp.Union[BaseMSBPart, PTDE_MSBNavmesh, DS1R_MSBNavmesh, BB_MSBNavmesh]

    from soulstruct.darksouls1ptde.maps.parts import MSBCharacter as PTDE_MSBCharacter
    from soulstruct.darksouls1r.maps.parts import MSBCharacter as DS1R_MSBCharacter
    from soulstruct.bloodborne.maps.parts import MSBCharacter as BB_MSBCharacter
    from soulstruct.eldenring.maps.parts import MSBCharacter as ER_MSBCharacter
    MSB_CHARACTER_TYPING = tp.Union[BaseMSBPart, PTDE_MSBCharacter, DS1R_MSBCharacter, BB_MSBCharacter, ER_MSBCharacter]

    from soulstruct.darksouls1ptde.maps.parts import MSBObject as PTDE_MSBObject
    from soulstruct.darksouls1r.maps.parts import MSBObject as DS1R_MSBObject
    from soulstruct.bloodborne.maps.parts import MSBObject as BB_MSBObject
    # Elden Ring uses Assets.
    MSB_OBJECT_TYPING = tp.Union[BaseMSBPart, PTDE_MSBObject, DS1R_MSBObject, BB_MSBObject]

    from soulstruct.eldenring.maps.parts import MSBAsset as ER_MSBAsset
    MSB_ASSET_TYPING = tp.Union[BaseMSBPart, ER_MSBAsset]

    from soulstruct.darksouls1ptde.maps.events import MSBEvent as PTDE_MSBEvent
    from soulstruct.darksouls1r.maps.events import MSBEvent as DS1R_MSBEvent
    from soulstruct.bloodborne.maps.events import MSBEvent as BB_MSBEvent
    from soulstruct.eldenring.maps.events import MSBEvent as ER_MSBEvent
    MSB_EVENT_TYPING = tp.Union[BaseMSBEvent, PTDE_MSBEvent, DS1R_MSBEvent, BB_MSBEvent, ER_MSBEvent]

    from soulstruct.darksouls1ptde.maps.regions import MSBRegion as PTDE_MSBRegion
    from soulstruct.darksouls1r.maps.regions import MSBRegion as DS1R_MSBRegion
    from soulstruct.bloodborne.maps.regions import MSBRegion as BB_MSBRegion
    from soulstruct.eldenring.maps.regions import MSBRegion as ER_MSBRegion
    MSB_REGION_TYPING = tp.Union[BaseMSBRegion, PTDE_MSBRegion, DS1R_MSBRegion, BB_MSBRegion, ER_MSBRegion]

    from soulstruct.darksouls1ptde.models import CHRBND as PTDE_CHRBND, OBJBND as PTDE_OBJBND, PARTSBND as PTDE_PARTSBND
    from soulstruct.darksouls1r.models import CHRBND as DS1R_CHRBND, OBJBND as DS1R_OBJBND, PARTSBND as DS1R_PARTSBND
    from soulstruct.bloodborne.models import CHRBND as BB_CHRBND, OBJBND as BB_OBJBND, PARTSBND as BB_PARTSBND
    CHRBND_TYPING = tp.Union[PTDE_CHRBND, DS1R_CHRBND, BB_CHRBND]
    OBJBND_TYPING = tp.Union[PTDE_OBJBND, DS1R_OBJBND, BB_OBJBND]
    PARTSBND_TYPING = tp.Union[PTDE_PARTSBND, DS1R_PARTSBND, BB_PARTSBND]

    from soulstruct.darksouls1ptde.models.shaders import MatDef as PTDE_MatDef
    from soulstruct.darksouls1r.models.shaders import MatDef as DS1R_MatDef
    from soulstruct.bloodborne.models.shaders import MatDef as BB_MatDef
    from soulstruct.eldenring.models.shaders import MatDef as ER_MatDef
    MATDEF_TYPING = tp.Union[PTDE_MatDef, DS1R_MatDef, BB_MatDef, ER_MatDef]
