local Layout = {}

function Layout.textWidth(font, text)
    return getTextManager():MeasureStringX(font, tostring(text or ""))
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

function Layout.columnPadding()
    return 8
end

function Layout.progressBarHeight()
    return Layout.boxHeight(UIFont.Small, 2, 19)
end

return Layout
