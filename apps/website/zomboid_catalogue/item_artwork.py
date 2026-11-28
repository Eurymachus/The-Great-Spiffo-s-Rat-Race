def item_icon_key(properties):
    """Use an explicit icon, otherwise the first declared texture variant."""
    explicit = str(properties.get("Icon") or "").strip()
    if explicit:
        return explicit
    variants = str(properties.get("IconsForTexture") or "")
    return next((key.strip() for key in variants.split(";") if key.strip()), "")


def missing_icon_reason(entry, properties=None):
    """Classify source evidence without inventing inventory artwork."""
    properties = properties or {}
    if entry.kind == "skill":
        return "no_infobox_artwork_on_pzwiki"
    if entry.kind == "occupation" and entry.stable_id == "base:unemployed" and not entry.icon_key:
        return "occupation_has_no_source_icon"
    if entry.kind == "item":
        if (str(properties.get("hidden", "")).lower() == "true"
                and properties.get("ItemType") == "base:clothing"
                and properties.get("ClothingItem") and not item_icon_key(properties)):
            return "hidden_character_overlay_no_inventory_icon"
        if properties.get("WorldObjectSprite") and not item_icon_key(properties):
            return "world_sprite_requires_artwork"
        if entry.icon_key.casefold() == "default":
            return "placeholder_icon_requires_world_artwork"
    return "no_supported_icon_key"
