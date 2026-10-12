def item_icon_key(properties):
    """Use an explicit icon, otherwise the first declared texture variant."""
    explicit = str(properties.get("Icon") or "").strip()
    if explicit:
        return explicit
    variants = str(properties.get("IconsForTexture") or "")
    return next((key.strip() for key in variants.split(";") if key.strip()), "")
