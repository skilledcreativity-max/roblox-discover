import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials!")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. Fetch live games from Rolimons using a real browser header
url = "https://api.rolimons.com/games/v1/gamelist"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

res = requests.get(url, headers=headers, timeout=30)
if res.status_code != 200:
    raise Exception(f"Rolimons returned status code {res.status_code}: {res.text[:200]}")

data = res.json()
games_dict = data.get("games", {})
print(f"Fetched {len(games_dict)} games from Rolimons.")

# 2. Get existing playing numbers from database (up to 10,000 rows)
old_players = {}
try:
    existing = supabase.table("games").select("universe_id, playing").limit(10000).execute()
    for row in (existing.data or []):
        old_players[row["universe_id"]] = row.get("playing") or 0
except Exception as e:
    print(f"Could not load previous numbers, starting fresh: {e}")

# 3. Calculate growth and prepare rows
games_to_save = []

for place_id_str, info in games_dict.items():
    try:
        universe_id = int(place_id_str)
        name = info[0] if len(info) > 0 else "Unknown"
        current_ccu = info[1] if len(info) > 1 else 0
        icon_url = info[2] if len(info) > 2 else ""

        # Growth calculation
        last_ccu = old_players.get(universe_id, 0)
        growth = 0
        if last_ccu > 0:
            growth = round(((current_ccu - last_ccu) / last_ccu) * 100)

        games_to_save.append({
            "universe_id": universe_id,
            "name": name,
            "genre": "Roblox Experience",
            "icon_url": icon_url,
            "playing": current_ccu,
            "growth": growth
        })
    except Exception:
        continue

# 4. Save to Supabase in batches of 500
chunk_size = 500
print(f"Saving {len(games_to_save)} games to database...")

for i in range(0, len(games_to_save), chunk_size):
    chunk = games_to_save[i:i + chunk_size]
    supabase.table("games").upsert(chunk).execute()
    print(f"Saved batch {i // chunk_size + 1}...")

print("All games and growth percentages saved successfully!")
