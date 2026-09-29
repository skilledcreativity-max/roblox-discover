import os
import requests
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

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
    sorted_games = sorted(
        games_dict.items(),
        key=lambda item: item[1][1] if len(item[1]) > 1 else 0,
        reverse=True
    )

    top_games = sorted_games[:1000]
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
        except Exception:
            continue

    # Batch save in chunks of 500
    chunk_size = 500
    for i in range(0, len(games_rows), chunk_size):
        supabase.table("games").upsert(games_rows[i:i + chunk_size]).execute()
        supabase.table("game_snapshots").insert(snapshot_rows[i:i + chunk_size]).execute()

    print(f"Successfully saved {len(games_rows)} games into your database!")

    # Auto-prune snapshots older than 14 days to keep DB fast and free forever
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        supabase.table("game_snapshots").delete().lt("recorded_at", cutoff).execute()
        print("Pruning check: cleaned snapshots older than 14 days.")
    except Exception as e:
        print(f"Notice during pruning: {e}")

if __name__ == "__main__":
    fetch_and_save_games()
