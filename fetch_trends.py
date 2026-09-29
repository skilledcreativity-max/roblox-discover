import os
import requests
import uuid
from supabase import create_client, Client

# 1. Connect to Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Get top games from Roblox Explore API
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_trending_universe_ids():
    session_id = str(uuid.uuid4())
    sort_categories = ["top-trending", "top-playing-now", "up-and-coming", "top-revisited"]
    universe_ids = set()

    for sort_id in sort_categories:
        try:
            url = f"https://apis.roblox.com/explore-api/v1/get-sort-content?sessionId={session_id}&sortId={sort_id}&device=computer&country=all"
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                entries = data.get("content", {}).get("entries", [])
                for entry in entries:
                    uid = entry.get("universeId")
                    if uid:
                        universe_ids.add(uid)
                print(f"Fetched {len(entries)} games from sort: {sort_id}")
        except Exception as e:
            print(f"Error fetching sort {sort_id}: {e}")

    return list(universe_ids)

# 3. Batch fetch detailed game info (visits, creator, playing, genre)
def fetch_game_details(universe_ids):
    chunk_size = 50
    details = []

    for i in range(0, len(universe_ids), chunk_size):
        chunk = universe_ids[i:i + chunk_size]
        ids_str = ",".join(str(x) for x in chunk)
        
        # Details endpoint
        games_url = f"https://games.roblox.com/v1/games?universeIds={ids_str}"
        # Votes endpoint
        votes_url = f"https://games.roblox.com/v1/games/votes?universeIds={ids_str}"
        # Icons endpoint
        icons_url = f"https://thumbnails.roblox.com/v1/games/icons?universeIds={ids_str}&size=150x150&format=Png&isCircular=false"

        try:
            g_res = requests.get(games_url, headers=HEADERS, timeout=10).json()
            v_res = requests.get(votes_url, headers=HEADERS, timeout=10).json()
            i_res = requests.get(icons_url, headers=HEADERS, timeout=10).json()

            votes_map = {item["id"]: item for item in v_res.get("data", [])}
            icons_map = {item["targetId"]: item.get("imageUrl") for item in i_res.get("data", [])}

            for game in g_res.get("data", []):
                uid = game.get("id")
                vote = votes_map.get(uid, {})
                icon = icons_map.get(uid, "")

                details.append({
                    "universe_id": uid,
                    "name": game.get("name", "Unknown"),
                    "genre": game.get("genre", "All"),
                    "creator_name": game.get("creator", {}).get("name", "Unknown"),
                    "icon_url": icon,
                    "playing": game.get("playing", 0),
                    "visits": game.get("visits", 0),
                    "upvotes": vote.get("upVotes", 0),
                    "downvotes": vote.get("downVotes", 0)
                })
        except Exception as e:
            print(f"Error fetching chunk {i}: {e}")

    return details

# 4. Save to Supabase
def main():
    print("Finding trending universe IDs...")
    universe_ids = get_trending_universe_ids()
    print(f"Total unique games found: {len(universe_ids)}")

    if not universe_ids:
        print("No games retrieved.")
        return

    print("Fetching metrics & votes...")
    games_data = fetch_game_details(universe_ids)

    # Upsert games info
    games_rows = [{
        "universe_id": g["universe_id"],
        "name": g["name"],
        "genre": g["genre"],
        "creator_name": g["creator_name"],
        "icon_url": g["icon_url"]
    } for g in games_data]

    # Snapshots for trend tracking
    snapshot_rows = [{
        "universe_id": g["universe_id"],
        "playing": g["playing"],
        "visits": g["visits"],
        "upvotes": g["upvotes"],
        "downvotes": g["downvotes"]
    } for g in games_data]

    print("Uploading to Supabase...")
    supabase.table("games").upsert(games_rows).execute()
    supabase.table("game_snapshots").insert(snapshot_rows).execute()
    print(f"Successfully tracked {len(games_data)} games!")

if __name__ == "__main__":
    main()
