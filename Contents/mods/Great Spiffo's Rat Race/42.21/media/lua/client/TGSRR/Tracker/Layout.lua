local Layout = {}

function Layout.textWidth(font, text)
    return getTextManager():MeasureStringX(font, tostring(text or ""))
end

function Layout.maxTextWidth(font, values)
    local width = 0
    for _, value in ipairs(values or {}) do
        width = math.max(width, Layout.textWidth(font, value))
    end
    return width
end

function Layout.lineHeight(font)
    return getTextManager():getFontHeight(font)
end

function Layout.boxHeight(font, verticalPadding, minimum)
    return math.max(minimum or 0, Layout.lineHeight(font) + (verticalPadding or 0) * 2)
end

function Layout.tabWidth(text)
    return math.max(86, Layout.textWidth(UIFont.Small, text) + 24)
end

function Layout.rowHeight(iconSize)
    return math.max(27, Layout.lineHeight(UIFont.Small) + 10, (iconSize or 0) + 8)
end

function Layout.threeColumns(width)
    return math.floor(width * 0.46), math.floor(width * 0.73)
end

function Layout.threeColumnWidth(first, second, third)
    return math.ceil(math.max(
        (first or 0) / 0.46,
        (second or 0) / 0.27,
        (third or 0) / 0.27
    ))
end

function Layout.columnPadding()
    return 8
end

function Layout.progressBarHeight()
    return Layout.boxHeight(UIFont.Small, 2, 19)
end

return Layout
