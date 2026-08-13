require "ISUI/ISPanel"
require "ISUI/ISScrollingListBox"

local Data = require "TGSRR/Tracker/Skills/Data"
local L = require "TGSRR/Core/Localization"
local State = require "TGSRR/Tracker/State"
local Layout = require "TGSRR/Tracker/Layout"

local View = ISPanel:derive("TGSRRSkillsTrackerView")
local HEADER_Y = 8
local MARGIN = 8
local SEGMENT_GAP = 2
local TREE_EXPANDED = getTexture("media/ui/inventoryPanes/Button_TreeExpanded.png")
local TREE_COLLAPSED = getTexture("media/ui/inventoryPanes/Button_TreeCollapsed.png")
local COLLAPSED_STATE_KEY = "skills.collapsedCategories"
local PIP_ACQUIRED = { 1, 0.89, 0.38 }
local PIP_CURRENT = { 0.48, 0.48, 0.48 }
local PIP_LOCKED = { 0.20, 0.20, 0.20 }
local SKILL_ICON_CACHE = {}
local SKILL_ICON_SIZE = 19
local function headerHeight() return Layout.boxHeight(UIFont.Small, 7, 28) end
local function footerHeight() return Layout.boxHeight(UIFont.Small, 5, 22) end
local function listTop() return HEADER_Y + headerHeight() end
local function rowHeight() return Layout.rowHeight(SKILL_ICON_SIZE) end

local function skillIcon(skillId)
    local cached = SKILL_ICON_CACHE[skillId]
    if cached ~= nil then return cached or nil end
    local texture = getTexture("media/ui/TGSRR_Skill_" .. tostring(skillId) .. ".png")
    SKILL_ICON_CACHE[skillId] = texture or false
    return texture
end

local function skillRight(width)
    local first = Layout.threeColumns(width)
    return first
end

local function progressLeft(width)
    local _, second = Layout.threeColumns(width)
    return second
end

local function scrollGutter(list)
    return list and list.vscroll and list.vscroll:getWidth() or 0
end

local function loadCollapsedCategories()
    local collapsed = {}
    local value = State.getValue(COLLAPSED_STATE_KEY, "")
    for id in tostring(value):gmatch("[^,]+") do collapsed[id] = true end
    return collapsed
end

local function saveCollapsedCategories(collapsed)
    local ids = {}
    for id, isCollapsed in pairs(collapsed) do
        if isCollapsed then ids[#ids + 1] = id end
    end
    table.sort(ids)
    State.setValue(COLLAPSED_STATE_KEY, table.concat(ids, ","))
end

function View:createChildren()
    ISPanel.createChildren(self)
    local listY = listTop()
    self.list = ISScrollingListBox:new(MARGIN, listY, self.width - MARGIN * 2,
        self.height - listY - footerHeight() - MARGIN * 2)
    self.list:initialise()
    self.list:instantiate()
    self.list.owner = self
    self.list.itemheight = rowHeight()
    self.list.doDrawItem = self.drawRow
    self.list.drawBorder = true
    self.list:setOnMouseDownFunction(self, View.onRowClicked)
    self.list:setOnMouseDoubleClick(self, View.onRowClicked)
    self:addChild(self.list)
    self:refresh(getSpecificPlayer(0) or getPlayer())
end

function View:prerender()
    ISPanel.prerender(self)
    local scrollWidth = scrollGutter(self.list)
    local frameWidth = self.width - MARGIN * 2
    local width = frameWidth - scrollWidth
    local header = headerHeight()
    local footer = footerHeight()
    self:drawRect(MARGIN, HEADER_Y, frameWidth, header, 0.9, 0.12, 0.12, 0.12)
    self:drawRectBorder(MARGIN, HEADER_Y, frameWidth, header, 0.7, 0.65, 0.65, 0.65)
    local textY = HEADER_Y + math.floor((header - Layout.lineHeight(UIFont.Small)) / 2)
    self:drawText(L.text("UI_TGSRR_Tracker_Skill", "Skill"), MARGIN + 8, textY, 1, 1, 1, 1, UIFont.Small)
    local levelX = skillRight(width)
    local progressX = progressLeft(width)
    self:drawTextCentre(L.text("UI_TGSRR_Tracker_Level", "Level"),
        MARGIN + levelX + math.floor((progressX - levelX) / 2), textY, 1, 1, 1, 1, UIFont.Small)
    self:drawTextCentre(L.text("UI_TGSRR_Tracker_Progress", "Progress"),
        MARGIN + progressX + math.floor((width - progressX) / 2),
        textY, 1, 1, 1, 1, UIFont.Small)

    local footerY = self.height - MARGIN - footer
    self:drawRect(MARGIN, footerY, frameWidth, footer, 0.8, 0.02, 0.02, 0.02)
    local snapshot = self.snapshot
    local percent = snapshot and snapshot.percent or 0
    if percent > 0 then
        self:drawRect(MARGIN + 1, footerY + 1, math.floor((frameWidth - 2) * percent / 100),
            footer - 2, 0.76, 0.12, 0.58, 0.18)
    end
    self:drawRectBorder(MARGIN, footerY, frameWidth, footer, 0.62, 0.55, 0.55, 0.55)
    local mastered = snapshot and snapshot.mastered or 0
    local total = snapshot and snapshot.total or 0
    local footerText = tostring(mastered) .. " " .. L.text("UI_TGSRR_Tracker_Of", "of") .. " " ..
        tostring(total) .. " " .. L.text("UI_TGSRR_Tracker_SkillsMastered", "skills mastered") ..
        " (" .. string.format("%.1f%%", percent) .. ")"
    local footerTextY = footerY + math.floor((footer - Layout.lineHeight(UIFont.Small)) / 2)
    self:drawTextCentre(footerText, MARGIN + frameWidth / 2, footerTextY, 1, 1, 1, 1, UIFont.Small)
end

local function drawSegments(self, x, y, width, height, skill)
    local availableWidth = math.max(10, math.floor(width) - SEGMENT_GAP * 9)
    local baseWidth = math.floor(availableWidth / 10)
    local remainder = availableWidth - baseWidth * 10
    local segmentX = math.floor(x)
    for index = 1, 10 do
        local segmentWidth = baseWidth + (index <= remainder and 1 or 0)
        self:drawRect(segmentX, y, segmentWidth, height, 0.82, 0.02, 0.02, 0.02)
        local acquired = index <= skill.level
        local current = not skill.complete and index == skill.level + 1
        local fill = acquired and 1 or (current and skill.levelProgress or 0)
        local color = acquired and PIP_ACQUIRED or (current and PIP_CURRENT or PIP_LOCKED)
        if fill > 0 then
            self:drawRect(segmentX + 1, y + 1,
                math.max(0, math.floor((segmentWidth - 2) * fill)), height - 2,
                0.92, color[1], color[2], color[3])
        end
        local border = current and PIP_CURRENT or color
        self:drawRectBorder(segmentX, y, segmentWidth, height,
            current and 0.82 or 0.68, border[1], border[2], border[3])
        segmentX = segmentX + segmentWidth + SEGMENT_GAP
    end
end

local function boostColor(boost)
    if boost == 0 then return 0.54, 0.54, 0.54 end
    if boost == 1 then return 0.80, 0.80, 0.80 end
    if boost == 3 then return 1, 0.83, 0 end
    return 1, 1, 1
end

local function compactValue(value)
    value = tonumber(value) or 0
    if math.abs(value - math.floor(value + 0.5)) < 0.05 then
        return tostring(math.floor(value + 0.5))
    end
    return string.format("%.1f", value)
end

local function drawCategoryProgress(self, x, y, width, height, category)
    self:drawRect(x, y, width, height, 0.82, 0.02, 0.02, 0.02)
    if category.percent > 0 then
        self:drawRect(x + 1, y + 1, math.floor((width - 2) * category.percent / 100),
            height - 2, 0.76, 0.12, 0.58, 0.18)
    end
    self:drawRectBorder(x, y, width, height, 0.58, 0.5, 0.5, 0.5)
    local textY = y + math.floor((height - getTextManager():getFontHeight(UIFont.Small)) / 2)
    local target = category.total * 10
    local text = compactValue(category.totalProgress) .. " / " .. tostring(target) ..
        " (" .. string.format("%.1f%%", category.percent) .. ")"
    self:drawTextCentre(text, x + width / 2, textY, 1, 1, 1, 1, UIFont.Small)
end

function View:drawRow(y, item, alt)
    if item.height and item.height <= 0 then return y end
    local data = item.item
    local reservedScrollWidth = scrollGutter(self)
    local rowWidth = self:getWidth()
    local contentWidth = rowWidth - reservedScrollWidth
    local textY = y + math.floor((self.itemheight - getTextManager():getFontHeight(UIFont.Small)) / 2)
    if data.kind == "category" then
        local category = data.category
        local frameWidth = contentWidth
        local levelX = skillRight(frameWidth)
        local progressX = progressLeft(frameWidth)
        self:drawRect(0, y, rowWidth, self.itemheight - 1, 0.45, 0.12, 0.12, 0.12)
        self:drawRect(0, y + self.itemheight - 1, rowWidth, 1, 0.4, 0.55, 0.55, 0.55)
        local icon = self.owner.collapsed[category.id] and TREE_COLLAPSED or TREE_EXPANDED
        if icon then self:drawTextureScaledAspect(icon, 6,
            y + math.floor((self.itemheight - SKILL_ICON_SIZE) / 2),
            SKILL_ICON_SIZE, SKILL_ICON_SIZE, 1, 1, 1, 1) end
        self:drawText(data.name, 30, textY, 1, 1, 1, 1, UIFont.Small)
        self:drawTextCentre(tostring(category.mastered) .. " / " .. tostring(category.total),
            levelX + math.floor((progressX - levelX) / 2), textY,
            category.mastered == category.total and 0.35 or 1,
            category.mastered == category.total and 1 or 1,
            category.mastered == category.total and 0.45 or 1, 1, UIFont.Small)
        local padding = Layout.columnPadding()
        local barHeight = Layout.progressBarHeight()
        drawCategoryProgress(self, progressX + padding,
            y + math.floor((self.itemheight - barHeight) / 2),
            contentWidth - progressX - padding * 2, barHeight, category)
        return y + self.itemheight
    end

    local skill = data.skill
    if item.index % 2 == 0 then self:drawRect(0, y, rowWidth, self.itemheight - 1, 0.18, 0.12, 0.12, 0.12) end
    self:drawRect(0, y + self.itemheight - 1, rowWidth, 1, 0.3, 0.5, 0.5, 0.5)
    local r, g, b = skill.complete and 0.35 or 1, skill.complete and 1 or 1, skill.complete and 0.45 or 1
    local nameR, nameG, nameB = boostColor(skill.xpBoost)
    local icon = skillIcon(skill.id)
    if icon then self:drawTextureScaledAspect(icon, 6,
        y + math.floor((self.itemheight - SKILL_ICON_SIZE) / 2),
        SKILL_ICON_SIZE, SKILL_ICON_SIZE, 1, 1, 1, 1) end
    self:drawText(skill.name, icon and 30 or 6, textY, nameR, nameG, nameB, 1, UIFont.Small)
    local frameWidth = contentWidth
    local levelX = skillRight(frameWidth)
    local progressX = progressLeft(frameWidth)
    self:drawTextCentre(tostring(skill.level) .. " / 10",
        levelX + math.floor((progressX - levelX) / 2), textY, r, g, b, 1, UIFont.Small)
    local padding = Layout.columnPadding()
    local barHeight = Layout.progressBarHeight()
    drawSegments(self, progressX + padding,
        y + math.floor((self.itemheight - barHeight) / 2),
        contentWidth - progressX - padding * 2, barHeight, skill)
    return y + self.itemheight
end

function View:refresh(player)
    if not self.list then return end
    local snapshot = Data.getSnapshot(player)
    self.snapshot = snapshot
    local scrollY = self.list:getYScroll()
    local selected = self.list.items[self.list.selected]
    local selectedId = selected and selected.item and selected.item.id or nil
    self.list:clear()
    for _, row in ipairs(snapshot.rows) do
        local tooltip
        if row.kind == "skill" then
            local skill = row.skill
            tooltip = skill.name .. "\n" .. L.text("UI_TGSRR_Tracker_Level", "Level") ..
                ": " .. tostring(skill.level) .. " / 10"
            if not skill.complete and skill.requiredXp then
                tooltip = tooltip .. "\n" .. L.text("UI_TGSRR_Tracker_XP", "XP") .. ": " ..
                    tostring(math.floor(skill.currentXp or 0)) ..
                    " / " .. tostring(math.floor(skill.requiredXp))
            end
        end
        local item = self.list:addItem(row.name or (row.skill and row.skill.name) or "", row, tooltip)
        item.height = row.kind == "skill" and self.collapsed[row.skill.categoryId] and 0 or rowHeight()
        if row.id == selectedId and item.height > 0 then self.list.selected = item.itemindex end
    end
    self.list:setYScroll(scrollY)
end

function View:setCategoryCollapsed(categoryId, collapsed)
    local selectedItem = self.list.items[self.list.selected]
    local selectedWasHidden = false
    local categoryIndex = nil

    for index, item in ipairs(self.list.items) do
        local row = item.item
        if row.kind == "category" and row.category.id == categoryId then
            categoryIndex = index
        elseif row.kind == "skill" and row.skill.categoryId == categoryId then
            item.height = collapsed and 0 or rowHeight()
            if collapsed and selectedItem == item then selectedWasHidden = true end
        end
    end

    if selectedWasHidden and categoryIndex then self.list.selected = categoryIndex end
end

function View:onRowClicked(row)
    if not row or row.kind ~= "category" then return end
    local id = row.category.id
    self.collapsed[id] = not self.collapsed[id]
    saveCollapsedCategories(self.collapsed)
    self:setCategoryCollapsed(id, self.collapsed[id])
end

function View:update()
    ISPanel.update(self)
    if self:getIsVisible() and Data.isDirty() then
        self:refresh(getSpecificPlayer(0) or getPlayer())
    end
end

function View:onShow()
    self:setVisible(true)
    Data.markDirty()
    self:refresh(getSpecificPlayer(0) or getPlayer())
end

function View:onHide() self:setVisible(false) end

function View:onResize(width, height)
    self:setWidth(width)
    self:setHeight(height)
    if self.list then
        local listY = listTop()
        self.list:setWidth(width - MARGIN * 2)
        self.list:setHeight(height - listY - footerHeight() - MARGIN * 2)
    end
end

function View:new(x, y, width, height)
    local o = ISPanel.new(self, x, y, width, height)
    o.background = false
    o.collapsed = loadCollapsedCategories()
    return o
end

return View
