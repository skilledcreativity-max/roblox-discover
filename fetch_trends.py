import os
import requests
from supabase import create_client, Client

# 1. Connect to Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
}

def fetch_and_save_games():
    print("Fetching top games from index...")
    url = "https://api.rolimons.com/games/v1/gamelist"
    
    res = requests.get(url, headers=HEADERS, timeout=20)
    data = res.json()
    
    if not data.get("success"):
        print("Failed to fetch game list.")
        return
        
    games_dict = data.get("games", {})
    print(f"Total available games: {len(games_dict)}")

    # Sort all games by active player count (CCU) descending
    # Format of each game entry: [name, player_count, thumbnail_url]
    sorted_games = sorted(
        games_dict.items(),
        key=lambda item: item[1][1] if len(item[1]) > 1 else 0,
        reverse=True
    )

    # Take the top 250 most active games
    top_games = sorted_games[:250]
    print(f"Processing top {len(top_games)} games...")

    games_rows = []
    snapshot_rows = []

    for place_id_str, info in top_games:
        try:
            place_id = int(place_id_str)
            name = info[0] if len(info) > 0 else "Unknown Game"
            playing = info[1] if len(info) > 1 else 0
            icon_url = info[2] if len(info) > 2 else ""

            games_rows.append({
                "universe_id": place_id,
                "name": name,
                "genre": "Roblox Experience",
                "creator_name": "Roblox Dev",
                "icon_url": icon_url
            })

            snapshot_rows.append({
                "universe_id": place_id,
                "playing": playing,
                "visits": 0,
                "upvotes": 0,
                "downvotes": 0
            })
        except Exception as e:
            continue

    # Batch save into Supabase
    print("Saving games to Supabase...")
    supabase.table("games").upsert(games_rows).execute()
    supabase.table("game_snapshots").insert(snapshot_rows).execute()
    print(f"Successfully saved {len(games_rows)} games into your database!")

if __name__ == "__main__":
    fetch_and_save_games()
