import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. Get previous numbers from database to compare
old_data = supabase.table("games").select("universe_id, playing").execute()
old_players = {row["universe_id"]: row["playing"] for row in (old_data.data or [])}

# 2. Get fresh numbers from Rolimons
url = "https://api.rolimons.com/games/v1/gamelist"
headers = {"User-Agent": "Mozilla/5.0"}
res = requests.get(url, headers=headers).json()
games_dict = res.get("games", {})

# 3. Prepare updated data
games_to_save = []

for place_id, info in games_dict.items():
    universe_id = int(place_id)
    name = info[0] if len(info) > 0 else "Unknown"
    current_ccu = info[1] if len(info) > 1 else 0
    icon_url = info[2] if len(info) > 2 else ""

    # Calculate growth percentage
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

# 4. Save to Supabase in batches of 500
chunk_size = 500
for i in range(0, len(games_to_save), chunk_size):
    chunk = games_to_save[i:i + chunk_size]
    supabase.table("games").upsert(chunk).execute()

print(f"Done! Updated {len(games_to_save)} games with live growth.")
