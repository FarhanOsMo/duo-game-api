-- export_game_data.lua
-- Run in Roblox Studio (Edit mode): View > Command Bar, paste this whole file, press Enter.
-- Read-only: it requires the game's data ModuleScripts and prints each one as JSON to the
-- Output window between "===== data/<name>.json =====" and "===== end <name>.json =====".
-- Turn off timestamps in the Output window (... menu > Show Timestamps) before copying.

local HttpService = game:GetService("HttpService")

-- Output file -> accepted ModuleScript names (compared lowercase, letters/digits only).
local FILES = {
	{ "monsters",         { "monsters", "monsterdata", "monster" } },
	{ "abilities",        { "abilities", "abilitydata", "ability", "moves", "movedata" } },
	{ "items",            { "items", "itemdata", "item" } },
	{ "elements",         { "elements", "elementdata", "element", "types", "typedata" } },
	{ "essences",         { "essences", "essencedata", "essence" } },
	{ "personalities",    { "personalities", "personalitydata", "personality", "natures" } },
	{ "status_effects",   { "statuseffects", "statuseffectdata", "statuseffect", "statuses" } },
	{ "rarities",         { "rarities", "raritydata", "rarity" } },
	{ "encounter_tables", { "encountertables", "encountertabledata", "encountertable", "encounters" } },
	{ "encounter_areas",  { "encounterareas", "encounterareadata", "encounterarea", "areas" } },
}
-- config.json = { game = <game config module>, battle = <battle config module> }
local CONFIG_PARTS = {
	{ "game",   { "gameconfig", "gamesettings", "gameconstants" } },
	{ "battle", { "battleconfig", "battlesettings", "battleconstants" } },
}

local SEARCH_ROOTS = { "ReplicatedStorage", "ServerStorage", "ServerScriptService", "ReplicatedFirst", "StarterPlayer" }

local function norm(s)
	return (string.lower(s):gsub("[^%w]", ""))
end

local modules = {}
for _, rootName in ipairs(SEARCH_ROOTS) do
	local root = game:FindFirstChild(rootName)
	if root then
		for _, inst in ipairs(root:GetDescendants()) do
			if inst:IsA("ModuleScript") then
				table.insert(modules, inst)
			end
		end
	end
end

local function findModule(names)
	for _, wanted in ipairs(names) do
		local hits = {}
		for _, m in ipairs(modules) do
			if norm(m.Name) == wanted then
				table.insert(hits, m)
			end
		end
		if #hits > 0 then
			if #hits > 1 then
				local paths = {}
				for _, h in ipairs(hits) do table.insert(paths, h:GetFullName()) end
				warn("[export] several modules named '" .. wanted .. "', using the first: " .. table.concat(paths, ", "))
			end
			return hits[1]
		end
	end
	return nil
end

-- Make a module's value JSON-safe: drop functions/NaN, stringify Roblox types, string-key mixed tables.
local function clean(v, seen)
	local t = typeof(v)
	if t == "table" then
		if seen[v] then return nil end
		seen[v] = true
		local count, maxIndex = 0, 0
		for k in pairs(v) do
			count += 1
			if type(k) == "number" and k >= 1 and k % 1 == 0 and k > maxIndex then maxIndex = k end
		end
		local out = {}
		if count > 0 and count == maxIndex then
			for i = 1, maxIndex do out[i] = clean(v[i], seen) end
		else
			for k, val in pairs(v) do
				local c = clean(val, seen)
				if c ~= nil then out[tostring(k)] = c end
			end
		end
		seen[v] = nil
		return out
	elseif t == "number" then
		if v ~= v or v == math.huge or v == -math.huge then return nil end
		return v
	elseif t == "string" or t == "boolean" then
		return v
	elseif t == "function" or t == "thread" or t == "nil" then
		return nil
	elseif t == "Instance" then
		return v:GetFullName()
	else
		return tostring(v)
	end
end

local function load(m)
	local ok, result = pcall(require, m)
	if not ok then
		warn("[export] require failed for " .. m:GetFullName() .. ": " .. tostring(result))
		return nil
	end
	return clean(result, {})
end

local function emit(name, value)
	local ok, json = pcall(HttpService.JSONEncode, HttpService, value)
	if not ok then
		warn("[export] JSONEncode failed for " .. name .. ": " .. tostring(json))
		return false
	end
	print("===== data/" .. name .. ".json =====")
	print(json)
	print("===== end " .. name .. ".json =====")
	return true
end

local missing = {}

for _, entry in ipairs(FILES) do
	local name, names = entry[1], entry[2]
	local m = findModule(names)
	if not m then
		table.insert(missing, name)
	else
		local value = load(m)
		if value == nil or not emit(name, value) then table.insert(missing, name) end
	end
end

-- config: one combined module with game/battle keys, or separate GameConfig + BattleConfig.
local config = nil
local combined = findModule({ "config", "configs", "gameconfig" })
if combined then
	local value = load(combined)
	if type(value) == "table" and value.game ~= nil and value.battle ~= nil then
		config = { game = value.game, battle = value.battle }
	end
end
if not config then
	config = {}
	for _, part in ipairs(CONFIG_PARTS) do
		local m = findModule(part[2])
		local value = m and load(m)
		if value == nil then
			table.insert(missing, "config." .. part[1])
		else
			config[part[1]] = value
		end
	end
end
if config.game ~= nil and config.battle ~= nil then
	if not emit("config", config) then table.insert(missing, "config") end
end

if #missing == 0 then
	print("[export] done: 11 files exported")
else
	warn("[export] could not export: " .. table.concat(missing, ", "))
	warn("[export] ModuleScripts found (send this list to fix the name mapping):")
	for _, m in ipairs(modules) do
		print("  " .. m:GetFullName())
	end
end
