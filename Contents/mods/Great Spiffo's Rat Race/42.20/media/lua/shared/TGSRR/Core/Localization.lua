local Localization = {}

function Localization.text(key, fallback)
    return getTextOrNull(key) or fallback
end

return Localization
