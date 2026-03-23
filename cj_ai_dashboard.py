import requests
from datetime import datetime

def get_today_schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher"

    res = requests.get(url)
    data = res.json()

    games = []

    for date in data.get("dates", []):
        for g in date.get("games", []):
            try:
                home = g["teams"]["home"]["team"]["name"]
                away = g["teams"]["away"]["team"]["name"]

                home_pitcher = g["teams"]["home"].get("probablePitcher", {}).get("fullName", "")
                away_pitcher = g["teams"]["away"].get("probablePitcher", {}).get("fullName", "")

                venue = g["venue"]["name"]

                games.append({
                    "away_team": away,
                    "home_team": home,
                    "away_pitcher": away_pitcher,
                    "home_pitcher": home_pitcher,
                    "park": venue
                })
            except:
                pass

    return pd.DataFrame(games)
