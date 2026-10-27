-- roblox-client-example.lua
-- Calls the Duo Game Data API from Roblox Studio and prints a monster's stat block.
--
-- Caveats (read before using):
--   * Studio only. Live Roblox servers run in Roblox's data centres and cannot
--     reach "localhost" on your computer, so this works in a Studio session only.
--   * Enable HTTP first: Home > Game Settings > Security > Allow HTTP Requests.
--   * Run it on the server side (Command Bar, or a Script in ServerScriptService):
--     HttpService cannot make requests from LocalScripts.
--   * The API is a read-only companion tool. It holds its own copy of the game data
--     (see docs/DATA_SYNC.md) and can never change the game, saves or live servers.
--   * Start the API first: `docker compose up -d` or `uvicorn app.main:app`.

local HttpService = game:GetService("HttpService")

local URL = "http://localhost:8000/api/v1/monsters/mon_placeholder_a/stats?level=5"

-- pcall: a request can fail (API not running, HTTP disabled), and an unprotected
-- error would stop the calling script.
local ok, body = pcall(function()
	return HttpService:GetAsync(URL)
end)

if not ok then
	warn("[duo-game-api] request failed: " .. tostring(body))
	return
end

local result = HttpService:JSONDecode(body)
print(("[duo-game-api] %s at level %d:"):format(result.species, result.level))
for _, stat in ipairs({ "hp", "mp", "attack", "defense", "magic", "speed" }) do
	print(("  %-8s %d"):format(stat, result.stats[stat]))
end
