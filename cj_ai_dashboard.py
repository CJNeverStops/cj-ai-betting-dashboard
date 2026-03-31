import math
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
import requests
import streamlit as st

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(page_title="CJ Daily MLB AI Board", layout="wide")

st.title("🔥 CJNeverStops Daily MLB AI Board")
st.caption("Conservative MLB projection board with hitter props, pitcher Ks, team runs, winners, and sportsbook odds matching")

with st.expander("How to Read This Board", expanded=True):
    st.markdown(
        """
### What this is good for
- Ranking the **best spots on the slate**
- Comparing **your fair odds** vs the sportsbook
- Finding **stronger relative plays**

### What this is NOT
- A guarantee engine
- A perfect sportsbook clone
- A reason to bet every top-ranked play

### Grade guide
Grades are based on **relative ranking on today's slate**, not fake certainty:
- **🔥 LOCK** = top tier on today's board
- **✅ STRONG** = strong spot
- **⚠️ LEAN** = playable but weaker
- **❌ PASS** = weaker relative spot

### Model Score weights
- **Hit %** = 40%
- **TB %** = 30%
- **RBI %** = 20%
- **HR %** = 10%

### Best use
1. Find top-ranked spots
2. Compare fair odds to book odds
3. Bet only when the book price is better than your fair price
"""
    )

BATTERS_FILE = "batters.csv"
PITCHERS_FILE = "pitchers.csv"
PARKS_FILE = "parks.csv"

# Paste your The Odds API key here
ODDS_API_KEY = "PASTE_YOUR_KEY_HERE"
ODDS_REGIONS = "us"
PLAYER_PROP_MARKETS = [
    "batter_hits",
    "batter_home_runs",
    "batter_total_bases",
    "batter_rbis",
    "pitcher_strikeouts",
]

HITTER_MARKET_MAP = {
    "Hit": "batter_hits",
    "Home Run": "batter_home_runs",
    "Total Bases": "batter_total_bases",
    "RBI": "batter_rbis",
}

PITCHER_MARKET_MAP = {
    "Over 4.5": ("pitcher_strikeouts", 4.5),
    "Over 5.5": ("pitcher_strikeouts", 5.5),
    "Over 6.5": ("pitcher_strikeouts", 6.5),
}


# =========================================================
# GENERIC HELPERS
# =========================================================
@st.cache_data(ttl=3600)
def try_load_csv(path: str) -> Tuple[pd.DataFrame, Optional[str]]:
    try:
        return pd.read_csv(path), None
    except Exception as e:
        return pd.DataFrame(), str(e)


def norm_text(value) -> str:
    return " ".join(str(value).strip().lower().replace(",", "").split())


def first_last_name(value) -> str:
    text = str(value).strip()
    if "," in text:
        parts = [p.strip() for p in text.split(",", 1)]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}".strip()
    return text


def normalize_prop_player_name(name: str) -> str:
    return norm_text(first_last_name(name))


def make_name_keys(value) -> Set[str]:
    raw = str(value).strip()
    return {
        norm_text(raw),
        norm_text(first_last_name(raw)),
    }


def safe_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def pct_to_decimal(value, default: Optional[float] = None) -> Optional[float]:
    try:
        if pd.isna(value):
            return default
        v = float(value)
        return v / 100.0 if v > 1 else v
    except Exception:
        return default


def logistic(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    lower_map = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        key = str(cand).strip().lower()
        if key in lower_map:
            return lower_map[key]
    for cand in candidates:
        key = str(cand).strip().lower()
        for col in df.columns:
            if key in str(col).strip().lower():
                return col
    return None


def require_col(df: pd.DataFrame, candidates: List[str], label: str) -> str:
    col = find_col(df, candidates)
    if col is None:
        st.error(f"Missing {label}. Found columns: {list(df.columns)}")
        st.stop()
    return col


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def scale_park_factor(value, default: float = 1.0) -> float:
    x = safe_float(value, default)
    return x / 100.0 if x > 3 else x


def implied_prob_from_american(odds: int) -> float:
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)


def prob_to_fair_american(prob: float):
    if prob <= 0 or prob >= 1:
        return None
    if prob >= 0.5:
        return int(round(-(prob / (1 - prob)) * 100))
    return int(round(((1 - prob) / prob) * 100))


def edge_grade(edge_pct: float) -> str:
    if edge_pct >= 5:
        return "🔥 GREAT"
    if edge_pct >= 2:
        return "✅ GOOD"
    if edge_pct > 0:
        return "⚠️ SMALL"
    return "❌ NO EDGE"


def estimate_plate_appearances(lineup_spot) -> float:
    try:
        s = int(float(lineup_spot))
    except Exception:
        return 4.2
    pa_map = {
        1: 4.85,
        2: 4.75,
        3: 4.65,
        4: 4.55,
        5: 4.45,
        6: 4.30,
        7: 4.15,
        8: 4.00,
        9: 3.85,
    }
    return pa_map.get(s, 4.2)


def rbi_lineup_boost(lineup_spot) -> float:
    try:
        s = int(float(lineup_spot))
    except Exception:
        return 1.00
    boost_map = {
        1: 0.86,
        2: 0.95,
        3: 1.10,
        4: 1.16,
        5: 1.08,
        6: 1.00,
        7: 0.93,
        8: 0.88,
        9: 0.82,
    }
    return boost_map.get(s, 1.00)


def platoon_boost(batter_hand, pitcher_hand) -> float:
    bh = str(batter_hand).strip().upper()
    ph = str(pitcher_hand).strip().upper()
    if bh in ["L", "R"] and ph in ["L", "R"]:
        return 1.03 if bh != ph else 0.98
    return 1.00


def team_abbrev_map() -> Dict[str, str]:
    return {
        "arizona diamondbacks": "ARI",
        "atlanta braves": "ATL",
        "baltimore orioles": "BAL",
        "boston red sox": "BOS",
        "chicago cubs": "CHC",
        "chicago white sox": "CWS",
        "cincinnati reds": "CIN",
        "cleveland guardians": "CLE",
        "colorado rockies": "COL",
        "detroit tigers": "DET",
        "houston astros": "HOU",
        "kansas city royals": "KC",
        "los angeles angels": "LAA",
        "los angeles dodgers": "LAD",
        "miami marlins": "MIA",
        "milwaukee brewers": "MIL",
        "minnesota twins": "MIN",
        "new york mets": "NYM",
        "new york yankees": "NYY",
        "oakland athletics": "OAK",
        "athletics": "OAK",
        "philadelphia phillies": "PHI",
        "pittsburgh pirates": "PIT",
        "san diego padres": "SD",
        "san francisco giants": "SF",
        "seattle mariners": "SEA",
        "st. louis cardinals": "STL",
        "tampa bay rays": "TB",
        "texas rangers": "TEX",
        "toronto blue jays": "TOR",
        "washington nationals": "WSH",
    }


def get_team_match_values(team_name: str) -> Set[str]:
    vals = {norm_text(team_name)}
    abbr = team_abbrev_map().get(norm_text(team_name), "")
    if abbr:
        vals.add(abbr.lower())
    return vals


def find_name_match(df: pd.DataFrame, key: str):
    return df[df["_keys"].apply(lambda s: key in s)]


def apply_relative_grades(df: pd.DataFrame, score_col: str, out_col: str) -> pd.DataFrame:
    df = df.copy()
    if len(df) < 4:
        df[out_col] = "✅ STRONG"
        return df

    q90 = df[score_col].quantile(0.90)
    q65 = df[score_col].quantile(0.65)
    q35 = df[score_col].quantile(0.35)

    def _grade(x):
        if x >= q90:
            return "🔥 LOCK"
        if x >= q65:
            return "✅ STRONG"
        if x >= q35:
            return "⚠️ LEAN"
        return "❌ PASS"

    df[out_col] = df[score_col].apply(_grade)
    return df


def estimate_team_runs(team_total, weather_boost=1.0, park_hit_factor=1.0, park_hr_factor=1.0):
    base = safe_float(team_total, 4.2)
    weather = safe_float(weather_boost, 1.0)
    run_env = (park_hit_factor * 0.65) + (park_hr_factor * 0.35)
    runs = base * weather * run_env
    return clamp(runs, 2.0, 9.5)


def win_prob_from_run_diff(run_diff):
    return logistic(run_diff * 0.55)


# =========================================================
# MLB API HELPERS
# =========================================================
@st.cache_data(ttl=1800)
def get_today_schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher,team"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return [], str(e)

    games = []
    valid_teams = team_abbrev_map()
    for d in data.get("dates", []):
        for g in d.get("games", []):
            try:
                away_team = g["teams"]["away"]["team"]["name"]
                home_team = g["teams"]["home"]["team"]["name"]

                if norm_text(away_team) not in valid_teams or norm_text(home_team) not in valid_teams:
                    continue

                games.append(
                    {
                        "gamePk": g.get("gamePk"),
                        "away_team": away_team,
                        "home_team": home_team,
                        "away_pitcher": g["teams"]["away"].get("probablePitcher", {}).get("fullName", ""),
                        "home_pitcher": g["teams"]["home"].get("probablePitcher", {}).get("fullName", ""),
                        "park": g["venue"]["name"],
                        "game_time": g.get("gameDate", ""),
                    }
                )
            except Exception:
                pass
    return games, None


@st.cache_data(ttl=900)
def get_game_lineups(game_pk):
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {"away": [], "home": []}

    def extract_side(side_key):
        players = []
        team_box = data.get("liveData", {}).get("boxscore", {}).get("teams", {}).get(side_key, {})
        batting_order = team_box.get("battingOrder", []) or []
        team_players = team_box.get("players", {}) or {}

        for idx, pid in enumerate(batting_order, start=1):
            pid_key = f"ID{pid}"
            p = team_players.get(pid_key, {})
            person = p.get("person", {})
            full_name = person.get("fullName", "")
            bats = p.get("batSide", {}).get("code", "")
            position = p.get("position", {}).get("abbreviation", "")
            if full_name:
                players.append(
                    {
                        "name": full_name,
                        "lineup_spot": idx,
                        "batter_hand": bats,
                        "position": position,
                    }
                )
        return players

    return {
        "away": extract_side("away"),
        "home": extract_side("home"),
    }


@st.cache_data(ttl=86400)
def get_mlb_roster_map():
    teams_url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
    try:
        teams = requests.get(teams_url, timeout=20).json()["teams"]
    except Exception:
        return {}

    player_team = {}
    for team in teams:
        team_id = team["id"]
        team_abbr = team["abbreviation"]
        roster_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster"
        try:
            roster = requests.get(roster_url, timeout=20).json()["roster"]
        except Exception:
            continue

        for p in roster:
            name = p["person"]["fullName"]
            player_team[norm_text(name)] = team_abbr
            player_team[norm_text(first_last_name(name))] = team_abbr

    return player_team


# =========================================================
# ODDS API HELPERS
# =========================================================
@st.cache_data(ttl=300)
def get_odds_api_events():
    if not ODDS_API_KEY or ODDS_API_KEY == "a0fb1acf6e6147cf99f2dd2b20c1e265":
        return []

    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/events"
    params = {"apiKey": ODDS_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


@st.cache_data(ttl=180)
def get_odds_api_event_props(event_id: str):
    if not ODDS_API_KEY or ODDS_API_KEY == "PASTE_YOUR_KEY_HERE":
        return {}

    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/events/{event_id}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": ODDS_REGIONS,
        "markets": ",".join(PLAYER_PROP_MARKETS),
        "oddsFormat": "american",
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def build_odds_lookup():
    events = get_odds_api_events()
    odds_rows = []

    for event in events:
        event_id = event.get("id")
        if not event_id:
            continue

        event_odds = get_odds_api_event_props(event_id)
        bookmakers = event_odds.get("bookmakers", [])
        home_team = event_odds.get("home_team", "")
        away_team = event_odds.get("away_team", "")

        for book in bookmakers:
            book_title = book.get("title", "")
            for market in book.get("markets", []):
                market_key = market.get("key", "")
                for outcome in market.get("outcomes", []):
                    player_name = outcome.get("description", "")
                    over_under = outcome.get("name", "")
                    price = outcome.get("price")
                    point = outcome.get("point")

                    if not player_name or price is None:
                        continue

                    odds_rows.append(
                        {
                            "player_key": normalize_prop_player_name(player_name),
                            "player_name": player_name,
                            "market": market_key,
                            "side": over_under,
                            "line": point,
                            "price": price,
                            "bookmaker": book_title,
                            "home_team": home_team,
                            "away_team": away_team,
                        }
                    )

    empty_cols = [
        "player_key",
        "player_name",
        "market",
        "side",
        "line",
        "price",
        "bookmaker",
        "home_team",
        "away_team",
    ]

    if not odds_rows:
        return pd.DataFrame(columns=empty_cols)

    odds_df = pd.DataFrame(odds_rows)
    over_df = odds_df[odds_df["side"].astype(str).str.lower() == "over"].copy()

    if over_df.empty:
        return pd.DataFrame(columns=empty_cols)

    over_df["sort_price"] = over_df["price"].astype(float)
    over_df = over_df.sort_values("sort_price", ascending=False)

    best_odds = (
        over_df.groupby(["player_key", "market", "line"], as_index=False)
        .first()
        .drop(columns=["sort_price"])
    )
    return best_odds


# =========================================================
# LOAD FILES
# =========================================================
batters, batters_err = try_load_csv(BATTERS_FILE)
pitchers, pitchers_err = try_load_csv(PITCHERS_FILE)
parks, parks_err = try_load_csv(PARKS_FILE)

if batters.empty:
    st.error(f"Could not load batters.csv: {batters_err}")
    st.stop()

if pitchers.empty:
    st.error(f"Could not load pitchers.csv: {pitchers_err}")
    st.stop()

if parks.empty:
    st.error(f"Could not load parks.csv: {parks_err}")
    st.stop()

# =========================================================
# COLUMN MAPPING
# =========================================================
b_name = require_col(batters, ["player_name", "name", "player", "last_name, first_name"], "batter name column")
b_xba = find_col(batters, ["xba", "est_ba", "estimated_ba", "est ba", "est_ba"])
b_xslg = find_col(batters, ["xslg", "est_slg", "estimated_slg", "est slg", "est_slg"])
b_xwoba = find_col(batters, ["xwoba", "est_woba", "estimated_woba_using_speedangle", "est woba", "est_woba"])
b_barrel = find_col(batters, ["brl_percent", "barrel_batted_rate", "barrel_pct", "barrel"])
b_hardhit = find_col(batters, ["hard_hit_percent", "hard_hit_pct", "hardhit"])
b_k = find_col(batters, ["k_percent", "strikeout_percent", "k%"])
b_bb = find_col(batters, ["bb_percent", "walk_percent", "bb%"])

p_name = require_col(pitchers, ["player_name", "name", "player", "last_name, first_name"], "pitcher name column")
p_xba = find_col(pitchers, ["xba", "est_ba", "estimated_ba", "est ba", "est_ba"])
p_xslg = find_col(pitchers, ["xslg", "est_slg", "estimated_slg", "est slg", "est_slg"])
p_xwoba = find_col(pitchers, ["xwoba", "est_woba", "estimated_woba_using_speedangle", "est woba", "est_woba"])
p_barrel = find_col(pitchers, ["brl_percent", "barrel_batted_rate", "barrel_pct", "barrel"])
p_hardhit = find_col(pitchers, ["hard_hit_percent", "hard_hit_pct", "hardhit"])
p_k = find_col(pitchers, ["k_percent", "strikeout_percent", "k%"])
p_bb = find_col(pitchers, ["bb_percent", "walk_percent", "bb%"])

park_name_col = require_col(parks, ["park_name", "venue_name", "park", "venue"], "park name column")
park_hr_col = find_col(parks, ["hr_factor", "hr", "home_run", "home_runs"])
park_hit_col = find_col(parks, ["hit_factor", "hit", "hits", "1b"])

# =========================================================
# CLEAN DATA
# =========================================================
batters = batters.copy()
pitchers = pitchers.copy()
parks = parks.copy()

batters["_keys"] = batters[b_name].astype(str).apply(make_name_keys)
pitchers["_keys"] = pitchers[p_name].astype(str).apply(make_name_keys)
parks["_park"] = parks[park_name_col].astype(str).str.strip().str.lower()

roster_map = get_mlb_roster_map()

def find_team(name):
    raw = str(name).strip()
    key1 = norm_text(raw)
    key2 = norm_text(first_last_name(raw))
    return roster_map.get(key1, roster_map.get(key2, ""))

batters["_team_auto"] = batters[b_name].astype(str).apply(find_team)
batters["_team_norm"] = batters["_team_auto"].map(norm_text)

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.header("Auto Slate")
    weather_boost_default = st.slider("Default weather boost", 0.90, 1.15, 1.00, 0.01)
    team_total_default = st.slider("Default team total", 3.0, 6.5, 4.2, 0.1)
    show_unconfirmed = st.toggle("Show fallback team hitters when lineups aren't posted", value=True)
    team_col_pick = st.selectbox(
        "Batter team column",
        options=["_team_auto"] + [c for c in batters.columns if c != "_team_auto"],
        index=0,
    )

if team_col_pick == "_team_auto":
    batters["_team_norm"] = batters["_team_auto"].map(norm_text)
else:
    batters["_team_norm"] = batters[team_col_pick].astype(str).map(norm_text)

# =========================================================
# SCHEDULE + MATCHUPS
# =========================================================
games, games_err = get_today_schedule()

st.subheader("📅 Today's MLB Games")
if not games:
    st.warning(f"Could not load today's schedule. {games_err if games_err else ''}")
    st.stop()

schedule_df = pd.DataFrame(games)
st.dataframe(schedule_df, use_container_width=True)

auto_rows = []
skipped = []
lineup_status_rows = []

for game in games:
    away_team = game["away_team"]
    home_team = game["home_team"]
    away_pitcher = game["away_pitcher"]
    home_pitcher = game["home_pitcher"]
    park = game["park"]
    game_pk = game["gamePk"]

    lineups = get_game_lineups(game_pk)
    away_lineup = lineups.get("away", [])
    home_lineup = lineups.get("home", [])

    lineup_status_rows.append(
        {
            "Game": f"{away_team} @ {home_team}",
            "Away Lineup Posted": len(away_lineup) > 0,
            "Home Lineup Posted": len(home_lineup) > 0,
            "Away Pitcher": away_pitcher,
            "Home Pitcher": home_pitcher,
            "Park": park,
        }
    )

    if home_pitcher:
        if away_lineup:
            for hitter in away_lineup:
                auto_rows.append(
                    {
                        "batter": hitter["name"],
                        "pitcher": home_pitcher,
                        "park": park,
                        "batter_hand": hitter.get("batter_hand", ""),
                        "pitcher_hand": "",
                        "lineup_spot": hitter.get("lineup_spot", 5),
                        "team": away_team,
                        "opp_team": home_team,
                        "weather_boost": weather_boost_default,
                        "team_total": team_total_default,
                    }
                )
        elif show_unconfirmed:
            away_vals = get_team_match_values(away_team)
            away_hitters = batters[batters["_team_norm"].isin(away_vals)]
            for _, batter_row in away_hitters.iterrows():
                auto_rows.append(
                    {
                        "batter": batter_row[b_name],
                        "pitcher": home_pitcher,
                        "park": park,
                        "batter_hand": "",
                        "pitcher_hand": "",
                        "lineup_spot": 5,
                        "team": away_team,
                        "opp_team": home_team,
                        "weather_boost": weather_boost_default,
                        "team_total": team_total_default,
                    }
                )

    if away_pitcher:
        if home_lineup:
            for hitter in home_lineup:
                auto_rows.append(
                    {
                        "batter": hitter["name"],
                        "pitcher": away_pitcher,
                        "park": park,
                        "batter_hand": hitter.get("batter_hand", ""),
                        "pitcher_hand": "",
                        "lineup_spot": hitter.get("lineup_spot", 5),
                        "team": home_team,
                        "opp_team": away_team,
                        "weather_boost": weather_boost_default,
                        "team_total": team_total_default,
                    }
                )
        elif show_unconfirmed:
            home_vals = get_team_match_values(home_team)
            home_hitters = batters[batters["_team_norm"].isin(home_vals)]
            for _, batter_row in home_hitters.iterrows():
                auto_rows.append(
                    {
                        "batter": batter_row[b_name],
                        "pitcher": away_pitcher,
                        "park": park,
                        "batter_hand": "",
                        "pitcher_hand": "",
                        "lineup_spot": 5,
                        "team": home_team,
                        "opp_team": away_team,
                        "weather_boost": weather_boost_default,
                        "team_total": team_total_default,
                    }
                )

matchups = pd.DataFrame(auto_rows)

if matchups.empty:
    st.error("Auto slate built zero rows. Wait for lineups to post, or let the MLB roster auto team matching catch your hitters.")
    st.stop()

matchups["_batter"] = matchups["batter"].astype(str).map(norm_text)
matchups["_pitcher"] = matchups["pitcher"].astype(str).map(norm_text)
matchups["_park"] = matchups["park"].astype(str).str.strip().str.lower()

with st.expander("Lineup Status"):
    st.dataframe(pd.DataFrame(lineup_status_rows), use_container_width=True)

with st.expander("Debug Info"):
    st.write("Batters columns:", list(batters.columns))
    st.write("Pitchers columns:", list(pitchers.columns))
    st.write("Parks columns:", list(parks.columns))
    st.write("Chosen team column:", team_col_pick)
    st.write("Auto team matches:", int((batters["_team_auto"] != "").sum()))
    st.write("Batters rows:", len(batters))
    st.write("Pitchers rows:", len(pitchers))
    st.write("Parks rows:", len(parks))
    st.write("Auto matchup rows:", len(matchups))

# =========================================================
# ODDS DATA
# =========================================================
odds_df = build_odds_lookup()

if ODDS_API_KEY == "PASTE_YOUR_KEY_HERE":
    st.info("Add your The Odds API key at the top of the file to enable sportsbook prop matching.")
elif odds_df.empty:
    st.warning("No sportsbook props loaded yet. Check your Odds API key, request limits, or whether MLB player props are available right now.")

# =========================================================
# METRIC EXTRACTORS
# =========================================================
def get_batter_metrics(row):
    return {
        "xba": safe_float(row[b_xba], 0.240) if b_xba else 0.240,
        "xslg": safe_float(row[b_xslg], 0.390) if b_xslg else 0.390,
        "xwoba": safe_float(row[b_xwoba], 0.310) if b_xwoba else 0.310,
        "barrel": pct_to_decimal(row[b_barrel], 0.08) if b_barrel else 0.08,
        "hardhit": pct_to_decimal(row[b_hardhit], 0.38) if b_hardhit else 0.38,
        "k_rate": pct_to_decimal(row[b_k], 0.22) if b_k else 0.22,
        "bb_rate": pct_to_decimal(row[b_bb], 0.08) if b_bb else 0.08,
    }


def get_pitcher_metrics(row):
    return {
        "xba": safe_float(row[p_xba], 0.240) if p_xba else 0.240,
        "xslg": safe_float(row[p_xslg], 0.390) if p_xslg else 0.390,
        "xwoba": safe_float(row[p_xwoba], 0.310) if p_xwoba else 0.310,
        "barrel": pct_to_decimal(row[p_barrel], 0.08) if p_barrel else 0.08,
        "hardhit": pct_to_decimal(row[p_hardhit], 0.38) if p_hardhit else 0.38,
        "k_rate": pct_to_decimal(row[p_k], 0.22) if p_k else 0.22,
        "bb_rate": pct_to_decimal(row[p_bb], 0.08) if p_bb else 0.08,
    }


def get_park_factors(park_key):
    row = parks.loc[parks["_park"] == park_key]
    if row.empty:
        return {"hr_factor": 1.00, "hit_factor": 1.00}
    row = row.iloc[0]
    return {
        "hr_factor": scale_park_factor(row[park_hr_col], 1.00) if park_hr_col else 1.00,
        "hit_factor": scale_park_factor(row[park_hit_col], 1.00) if park_hit_col else 1.00,
    }


def pitcher_hr_tendency(p):
    return ((p["xslg"] - 0.390) * 2.2) + ((p["barrel"] - 0.08) * 3.5)


# =========================================================
# BATTER PROJECTION MODEL
# =========================================================
def calc_batter_board(batter_row, pitcher_row, park_key, batter_hand, pitcher_hand, lineup_spot, weather_boost, team_total):
    b = get_batter_metrics(batter_row)
    p = get_pitcher_metrics(pitcher_row)
    park = get_park_factors(park_key)

    platoon = platoon_boost(batter_hand, pitcher_hand)
    weather_mult = safe_float(weather_boost, 1.00)
    team_total_v = safe_float(team_total, 4.2)
    team_total_mult = clamp(team_total_v / 4.2, 0.88, 1.15)
    plate_appearances = estimate_plate_appearances(lineup_spot)

    hit_score_raw = (
        1.9 * (b["xba"] - 0.240)
        + 0.9 * (b["xwoba"] - 0.310)
        + 0.5 * (b["hardhit"] - 0.38)
        - 0.9 * (b["k_rate"] - 0.22)
        - 1.3 * (p["k_rate"] - 0.22)
        - 1.0 * (p["xba"] - 0.240)
    )
    hit_prob_pa = logistic(-1.35 + hit_score_raw) * park["hit_factor"] * platoon
    hit_prob_pa = clamp(hit_prob_pa, 0.025, 0.55)
    hit_prob = 1 - (1 - hit_prob_pa) ** plate_appearances
    hit_prob = clamp(hit_prob, 0.18, 0.88)

    hr_score_raw = (
        4.2 * (b["xslg"] - 0.390)
        + 2.6 * (b["barrel"] - 0.08)
        + 1.2 * (b["hardhit"] - 0.38)
        + 2.1 * (p["xslg"] - 0.390)
        + 1.4 * (p["barrel"] - 0.08)
        + 0.8 * pitcher_hr_tendency(p)
    )
    hr_prob_pa = logistic(-3.9 + hr_score_raw)
    hr_prob = 1 - (1 - hr_prob_pa) ** plate_appearances
    hr_prob *= park["hr_factor"]
    hr_prob *= weather_mult
    hr_prob *= platoon
    hr_prob = clamp(hr_prob, 0.01, 0.28)

    tb_score_raw = (
        2.6 * (b["xslg"] - 0.390)
        + 1.2 * (b["xba"] - 0.240)
        + 1.1 * (b["hardhit"] - 0.38)
        + 0.8 * (b["barrel"] - 0.08)
        + 1.4 * (p["xslg"] - 0.390)
        + 0.5 * (p["xba"] - 0.240)
    )
    tb_prob_pa = logistic(-2.2 + tb_score_raw)
    tb_prob_pa = clamp(tb_prob_pa, 0.02, 0.40)
    tb_prob = 1 - (1 - tb_prob_pa) ** (plate_appearances * 0.92)
    tb_prob *= park["hit_factor"]
    tb_prob *= (park["hr_factor"] ** 0.20)
    tb_prob *= platoon
    tb_prob = clamp(tb_prob, 0.10, 0.72)

    rbi_score_raw = (
        1.9 * (b["xwoba"] - 0.310)
        + 1.8 * (b["xslg"] - 0.390)
        + 0.8 * (b["hardhit"] - 0.38)
        + 0.8 * (p["xwoba"] - 0.310)
    )
    rbi_prob_pa = logistic(-2.55 + rbi_score_raw)
    rbi_prob_pa = clamp(rbi_prob_pa, 0.015, 0.28)
    rbi_prob = 1 - (1 - rbi_prob_pa) ** (plate_appearances * 0.95)
    rbi_prob *= park["hit_factor"]
    rbi_prob *= team_total_mult
    rbi_prob *= platoon
    rbi_prob *= rbi_lineup_boost(lineup_spot)
    rbi_prob = clamp(rbi_prob, 0.06, 0.58)

    weighted_score = (
        hit_prob * 0.40
        + tb_prob * 0.30
        + rbi_prob * 0.20
        + hr_prob * 0.10
    ) * 100

    return {
        "hit_prob": hit_prob,
        "hr_prob": hr_prob,
        "tb_prob": tb_prob,
        "rbi_prob": rbi_prob,
        "platoon": platoon,
        "hr_factor": park["hr_factor"],
        "hit_factor": park["hit_factor"],
        "weighted_score": weighted_score,
    }


# =========================================================
# PITCHER K MODEL
# =========================================================
def project_pitcher_ks(pitcher_row, opp_batters):
    p = get_pitcher_metrics(pitcher_row)

    if opp_batters:
        avg_opp_k = sum(x["k_rate"] for x in opp_batters) / len(opp_batters)
        avg_opp_bb = sum(x["bb_rate"] for x in opp_batters) / len(opp_batters)
        avg_opp_xwoba = sum(x["xwoba"] for x in opp_batters) / len(opp_batters)
    else:
        avg_opp_k = 0.22
        avg_opp_bb = 0.08
        avg_opp_xwoba = 0.310

    effective_k_rate = (
        0.60 * p["k_rate"]
        + 0.40 * avg_opp_k
        - 0.16 * (avg_opp_bb - 0.08)
        - 0.10 * (avg_opp_xwoba - 0.310)
        - 0.10 * (p["bb_rate"] - 0.08)
        - 0.08 * (p["xwoba"] - 0.310)
    )
    effective_k_rate = clamp(effective_k_rate, 0.14, 0.38)

    lineup_size = len(opp_batters)
    batters_faced = (
        24.0
        + 5.2 * (p["k_rate"] - 0.22)
        - 3.0 * (p["bb_rate"] - 0.08)
        - 1.6 * (avg_opp_xwoba - 0.310)
    )
    if lineup_size >= 9:
        batters_faced += 0.7
    elif lineup_size <= 6:
        batters_faced -= 1.0

    batters_faced = clamp(batters_faced, 20.5, 28.0)
    return effective_k_rate * batters_faced


def prob_over_k_line(expected_ks, line):
    std_dev = 1.7 + 0.05 * max(0.0, 6.0 - expected_ks)
    z = (expected_ks - line) / std_dev
    return 1 / (1 + math.exp(-1.7 * z))


# =========================================================
# BUILD BATTER BOARD
# =========================================================
rows = []

for _, row in matchups.iterrows():
    batter_match = find_name_match(batters, row["_batter"])
    pitcher_match = find_name_match(pitchers, row["_pitcher"])

    if batter_match.empty:
        skipped.append(f"Batter not found: {row['batter']}")
        continue
    if pitcher_match.empty:
        skipped.append(f"Pitcher not found: {row['pitcher']}")
        continue

    batter_row = batter_match.iloc[0]
    pitcher_row = pitcher_match.iloc[0]

    calc = calc_batter_board(
        batter_row=batter_row,
        pitcher_row=pitcher_row,
        park_key=row["_park"],
        batter_hand=row.get("batter_hand", ""),
        pitcher_hand=row.get("pitcher_hand", ""),
        lineup_spot=row.get("lineup_spot", 5),
        weather_boost=row.get("weather_boost", weather_boost_default),
        team_total=row.get("team_total", team_total_default),
    )

    rows.append(
        {
            "Batter": row["batter"],
            "Pitcher": row["pitcher"],
            "Team": row.get("team", ""),
            "Opp": row.get("opp_team", ""),
            "Park": row["park"],
            "Lineup": int(float(row.get("lineup_spot", 5))),
            "Hit %": round(calc["hit_prob"] * 100, 1),
            "HR %": round(calc["hr_prob"] * 100, 1),
            "TB %": round(calc["tb_prob"] * 100, 1),
            "RBI %": round(calc["rbi_prob"] * 100, 1),
            "Hit Fair Odds": prob_to_fair_american(calc["hit_prob"]),
            "HR Fair Odds": prob_to_fair_american(calc["hr_prob"]),
            "TB Fair Odds": prob_to_fair_american(calc["tb_prob"]),
            "RBI Fair Odds": prob_to_fair_american(calc["rbi_prob"]),
            "Platoon": round(calc["platoon"], 2),
            "HR Park": round(calc["hr_factor"], 2),
            "Hit Park": round(calc["hit_factor"], 2),
            "Model Score": round(calc["weighted_score"], 1),
        }
    )

batters_df = pd.DataFrame(rows)

if batters_df.empty:
    st.error("No valid matchup rows were processed.")
    if skipped:
        st.write(skipped)
    st.stop()

batters_df = apply_relative_grades(batters_df, "Model Score", "Best Grade")

# =========================================================
# TEAM RUNS + PROJECTED WINNER
# =========================================================
game_projection_rows = []

for game in games:
    away_team = game["away_team"]
    home_team = game["home_team"]
    park_key = str(game["park"]).strip().lower()
    park = get_park_factors(park_key)

    away_pitcher_match = find_name_match(pitchers, norm_text(game["home_pitcher"])) if game["home_pitcher"] else pd.DataFrame()
    home_pitcher_match = find_name_match(pitchers, norm_text(game["away_pitcher"])) if game["away_pitcher"] else pd.DataFrame()

    away_pitch_adj = 1.00
    home_pitch_adj = 1.00

    if not home_pitcher_match.empty:
        ap = get_pitcher_metrics(home_pitcher_match.iloc[0])
        away_pitch_adj = 1 + ((ap["xwoba"] - 0.310) * 1.8) - ((ap["k_rate"] - 0.22) * 0.9)
        away_pitch_adj = clamp(away_pitch_adj, 0.82, 1.18)

    if not away_pitcher_match.empty:
        hp = get_pitcher_metrics(away_pitcher_match.iloc[0])
        home_pitch_adj = 1 + ((hp["xwoba"] - 0.310) * 1.8) - ((hp["k_rate"] - 0.22) * 0.9)
        home_pitch_adj = clamp(home_pitch_adj, 0.82, 1.18)

    away_team_total = team_total_default * away_pitch_adj
    home_team_total = team_total_default * home_pitch_adj

    away_runs = estimate_team_runs(
        team_total=away_team_total,
        weather_boost=weather_boost_default,
        park_hit_factor=park["hit_factor"],
        park_hr_factor=park["hr_factor"],
    )
    home_runs = estimate_team_runs(
        team_total=home_team_total,
        weather_boost=weather_boost_default,
        park_hit_factor=park["hit_factor"],
        park_hr_factor=park["hr_factor"],
    )

    run_diff = home_runs - away_runs
    home_win_prob = win_prob_from_run_diff(run_diff)
    away_win_prob = 1 - home_win_prob
    projected_winner = home_team if home_win_prob >= away_win_prob else away_team

    game_projection_rows.append(
        {
            "Matchup": f"{away_team} @ {home_team}",
            "Away Team": away_team,
            "Home Team": home_team,
            "Away Runs": round(away_runs, 2),
            "Home Runs": round(home_runs, 2),
            "Away Win %": round(away_win_prob * 100, 1),
            "Home Win %": round(home_win_prob * 100, 1),
            "Projected Winner": projected_winner,
            "Park": game["park"],
        }
    )

game_proj_df = pd.DataFrame(game_projection_rows)

# =========================================================
# BEST PICKS BOARD
# =========================================================
best_pick_rows = []
for _, r in batters_df.iterrows():
    prop_options = [
        ("Hit", r["Hit %"], r["Hit Fair Odds"]),
        ("Home Run", r["HR %"], r["HR Fair Odds"]),
        ("Total Bases", r["TB %"], r["TB Fair Odds"]),
        ("RBI", r["RBI %"], r["RBI Fair Odds"]),
    ]
    best_prop, best_prob, best_fair = sorted(prop_options, key=lambda x: x[1], reverse=True)[0]

    best_pick_rows.append(
        {
            "Player": r["Batter"],
            "Pitcher": r["Pitcher"],
            "Park": r["Park"],
            "Best Prop": best_prop,
            "Best Prop %": best_prob,
            "Fair Odds": best_fair,
            "Model Score": r["Model Score"],
            "Grade": r["Best Grade"],
        }
    )

best_picks_df = pd.DataFrame(best_pick_rows).sort_values("Model Score", ascending=False).reset_index(drop=True)

# =========================================================
# PITCHER K BOARD
# =========================================================
pitcher_board = []

for pitcher_name, grp in batters_df.groupby("Pitcher"):
    p_match = find_name_match(pitchers, norm_text(pitcher_name))
    if p_match.empty:
        continue

    p_row = p_match.iloc[0]
    opp_batters = []
    for _, batter_rec in grp.iterrows():
        b_match = find_name_match(batters, norm_text(batter_rec["Batter"]))
        if not b_match.empty:
            opp_batters.append(get_batter_metrics(b_match.iloc[0]))

    expected_ks = project_pitcher_ks(p_row, opp_batters)
    prob_45 = prob_over_k_line(expected_ks, 4.5)
    prob_55 = prob_over_k_line(expected_ks, 5.5)
    prob_65 = prob_over_k_line(expected_ks, 6.5)

    pitcher_board.append(
        {
            "Pitcher": pitcher_name,
            "Opponent": grp["Team"].iloc[0] if "Team" in grp.columns else "",
            "Proj Ks": round(expected_ks, 2),
            "Over 4.5 %": round(prob_45 * 100, 1),
            "Over 4.5 Fair": prob_to_fair_american(prob_45),
            "Over 5.5 %": round(prob_55 * 100, 1),
            "Over 5.5 Fair": prob_to_fair_american(prob_55),
            "Over 6.5 %": round(prob_65 * 100, 1),
            "Over 6.5 Fair": prob_to_fair_american(prob_65),
            "K Score": round((prob_45 * 0.30 + prob_55 * 0.45 + prob_65 * 0.25) * 100, 1),
        }
    )

pitchers_df = pd.DataFrame(pitcher_board)
if not pitchers_df.empty:
    pitchers_df = apply_relative_grades(pitchers_df, "K Score", "Grade")
    pitchers_df = pitchers_df.sort_values("Proj Ks", ascending=False).reset_index(drop=True)

# =========================================================
# TOP CARDS
# =========================================================
top_pick = best_picks_df.iloc[0]
top_k = pitchers_df.iloc[0] if not pitchers_df.empty else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Best Overall Pick", top_pick["Player"])
c2.metric("Best Prop", top_pick["Best Prop"])
c3.metric("Top Score", f"{top_pick['Model Score']}")
c4.metric("Top Pitcher K Spot", top_k["Pitcher"] if top_k is not None else "—")

if not game_proj_df.empty:
    best_total_game = game_proj_df.iloc[(game_proj_df["Away Runs"] + game_proj_df["Home Runs"]).idxmax()]
    strongest_favorite = game_proj_df.iloc[
        game_proj_df[["Away Win %", "Home Win %"]].max(axis=1).idxmax()
    ]

    g1, g2 = st.columns(2)
    g1.metric(
        "Highest Total Game",
        best_total_game["Matchup"],
        f'{round(best_total_game["Away Runs"] + best_total_game["Home Runs"], 2)} total runs',
    )
    g2.metric(
        "Strongest Favorite",
        strongest_favorite["Projected Winner"],
        f'{round(max(strongest_favorite["Away Win %"], strongest_favorite["Home Win %"]), 1)}% win chance',
    )

# =========================================================
# TEAM RUNS + WINNERS TABLE
# =========================================================
st.subheader("🏟️ Team Run Projections & Projected Winners")
st.dataframe(game_proj_df, use_container_width=True)

# =========================================================
# AUTO EDGE TABLE FROM SPORTSBOOK ODDS
# =========================================================
st.subheader("🔗 Auto-Matched Sportsbook Edges")

auto_edge_rows = []

if not odds_df.empty and "player_key" in odds_df.columns:
    for _, r in batters_df.iterrows():
        player_key = normalize_prop_player_name(r["Batter"])

        prop_prob_map = {
            "Hit": r["Hit %"],
            "Home Run": r["HR %"],
            "Total Bases": r["TB %"],
            "RBI": r["RBI %"],
        }
        prop_fair_map = {
            "Hit": r["Hit Fair Odds"],
            "Home Run": r["HR Fair Odds"],
            "Total Bases": r["TB Fair Odds"],
            "RBI": r["RBI Fair Odds"],
        }
        target_line_map = {
            "Hit": 0.5,
            "Home Run": 0.5,
            "Total Bases": 1.5,
            "RBI": 0.5,
        }

        for prop_label, market_key in HITTER_MARKET_MAP.items():
            candidate = odds_df[
                (odds_df["player_key"] == player_key) &
                (odds_df["market"] == market_key)
            ].copy()

            if candidate.empty:
                continue

            target_line = target_line_map[prop_label]
            candidate["line_num"] = candidate["line"].apply(lambda x: safe_float(x, target_line))
            candidate["line_diff"] = (candidate["line_num"] - target_line).abs()
            candidate = candidate.sort_values(["line_diff", "price"], ascending=[True, False])

            best_book = candidate.iloc[0]
            book_odds = int(best_book["price"])
            implied = implied_prob_from_american(book_odds) * 100
            model_pct = float(prop_prob_map[prop_label])
            edge_pct = model_pct - implied

            auto_edge_rows.append(
                {
                    "Player": r["Batter"],
                    "Type": "Hitter",
                    "Market": prop_label,
                    "Line": best_book["line"],
                    "Sportsbook": best_book["bookmaker"],
                    "Book Odds": book_odds,
                    "Model %": round(model_pct, 1),
                    "Implied %": round(implied, 1),
                    "Edge %": round(edge_pct, 1),
                    "Fair Odds": prop_fair_map[prop_label],
                }
            )

    if not pitchers_df.empty:
        for _, p in pitchers_df.iterrows():
            player_key = normalize_prop_player_name(p["Pitcher"])

            for line_label, (market_key, target_line) in PITCHER_MARKET_MAP.items():
                candidate = odds_df[
                    (odds_df["player_key"] == player_key) &
                    (odds_df["market"] == market_key)
                ].copy()

                if candidate.empty:
                    continue

                candidate["line_num"] = candidate["line"].apply(lambda x: safe_float(x, target_line))
                candidate["line_diff"] = (candidate["line_num"] - target_line).abs()
                candidate = candidate.sort_values(["line_diff", "price"], ascending=[True, False])

                best_book = candidate.iloc[0]
                book_odds = int(best_book["price"])
                implied = implied_prob_from_american(book_odds) * 100

                line_prob_map = {
                    "Over 4.5": p["Over 4.5 %"],
                    "Over 5.5": p["Over 5.5 %"],
                    "Over 6.5": p["Over 6.5 %"],
                }
                line_fair_map = {
                    "Over 4.5": p["Over 4.5 Fair"],
                    "Over 5.5": p["Over 5.5 Fair"],
                    "Over 6.5": p["Over 6.5 Fair"],
                }

                model_pct = float(line_prob_map[line_label])
                edge_pct = model_pct - implied

                auto_edge_rows.append(
                    {
                        "Player": p["Pitcher"],
                        "Type": "Pitcher",
                        "Market": line_label,
                        "Line": best_book["line"],
                        "Sportsbook": best_book["bookmaker"],
                        "Book Odds": book_odds,
                        "Model %": round(model_pct, 1),
                        "Implied %": round(implied, 1),
                        "Edge %": round(edge_pct, 1),
                        "Fair Odds": line_fair_map[line_label],
                    }
                )

if auto_edge_rows:
    auto_edge_df = pd.DataFrame(auto_edge_rows).sort_values("Edge %", ascending=False).reset_index(drop=True)
    st.dataframe(auto_edge_df.head(40), use_container_width=True)
else:
    st.info("No sportsbook props matched yet.")

# =========================================================
# HITTER ODDS CHECKER
# =========================================================
st.subheader("💰 Hitter Quick Odds Checker")

checker_cols = st.columns(2)
checker_player = checker_cols[0].selectbox("Player", best_picks_df["Player"].tolist())
checker_prop = checker_cols[1].selectbox("Prop", ["Hit", "Home Run", "Total Bases", "RBI"])

player_row = batters_df[batters_df["Batter"] == checker_player].iloc[0]
player_key = normalize_prop_player_name(checker_player)
market_key = HITTER_MARKET_MAP[checker_prop]

if odds_df.empty or "player_key" not in odds_df.columns:
    st.info("No sportsbook hitter props loaded yet.")
else:
    available_player_odds = odds_df[
        (odds_df["player_key"] == player_key) &
        (odds_df["market"] == market_key)
    ].copy()

    if checker_prop == "Hit":
        target_line = 0.5
    elif checker_prop == "Home Run":
        target_line = 0.5
    elif checker_prop == "RBI":
        target_line = 0.5
    else:
        target_line = 1.5

    if not available_player_odds.empty:
        available_player_odds["line_num"] = available_player_odds["line"].apply(lambda x: safe_float(x, target_line))
        available_player_odds["line_diff"] = (available_player_odds["line_num"] - target_line).abs()
        available_player_odds = available_player_odds.sort_values(["line_diff", "price"], ascending=[True, False])
        best_book_row = available_player_odds.iloc[0]

        book_odds = int(best_book_row["price"])
        implied = implied_prob_from_american(book_odds) * 100

        prop_to_prob = {
            "Hit": player_row["Hit %"],
            "Home Run": player_row["HR %"],
            "Total Bases": player_row["TB %"],
            "RBI": player_row["RBI %"],
        }
        prop_to_fair = {
            "Hit": player_row["Hit Fair Odds"],
            "Home Run": player_row["HR Fair Odds"],
            "Total Bases": player_row["TB Fair Odds"],
            "RBI": player_row["RBI Fair Odds"],
        }

        model_pct = float(prop_to_prob[checker_prop])
        edge_pct = model_pct - implied

        hc1, hc2, hc3, hc4 = st.columns(4)
        hc1.metric("Sportsbook", str(best_book_row["bookmaker"]))
        hc2.metric("Book Odds", str(book_odds))
        hc3.metric("Model %", f"{model_pct:.1f}%")
        hc4.metric("Fair Odds", str(prop_to_fair[checker_prop]))

        st.write(f"**Book Implied %:** {implied:.1f}%")
        st.write(f"**Edge %:** {edge_pct:.1f}%")
        st.write(f"**Verdict:** {edge_grade(edge_pct)}")
    else:
        st.info("No matching sportsbook prop found for that hitter/market yet.")

# =========================================================
# PITCHER ODDS CHECKER
# =========================================================
st.subheader("🎯 Pitcher K Odds Checker")

if not pitchers_df.empty:
    p_cols = st.columns(2)
    pitcher_name_check = p_cols[0].selectbox("Pitcher", pitchers_df["Pitcher"].tolist())
    k_line_check = p_cols[1].selectbox("K Line", ["Over 4.5", "Over 5.5", "Over 6.5"])

    p_row = pitchers_df[pitchers_df["Pitcher"] == pitcher_name_check].iloc[0]
    player_key = normalize_prop_player_name(pitcher_name_check)
    market_key, target_line = PITCHER_MARKET_MAP[k_line_check]

    if odds_df.empty or "player_key" not in odds_df.columns:
        st.info("No sportsbook pitcher props loaded yet.")
    else:
        available_pitcher_odds = odds_df[
            (odds_df["player_key"] == player_key) &
            (odds_df["market"] == market_key)
        ].copy()

        if not available_pitcher_odds.empty:
            available_pitcher_odds["line_num"] = available_pitcher_odds["line"].apply(lambda x: safe_float(x, target_line))
            available_pitcher_odds["line_diff"] = (available_pitcher_odds["line_num"] - target_line).abs()
            available_pitcher_odds = available_pitcher_odds.sort_values(["line_diff", "price"], ascending=[True, False])
            best_book_row = available_pitcher_odds.iloc[0]

            book_odds = int(best_book_row["price"])
            implied = implied_prob_from_american(book_odds) * 100

            line_to_prob = {
                "Over 4.5": p_row["Over 4.5 %"],
                "Over 5.5": p_row["Over 5.5 %"],
                "Over 6.5": p_row["Over 6.5 %"],
            }
            line_to_fair = {
                "Over 4.5": p_row["Over 4.5 Fair"],
                "Over 5.5": p_row["Over 5.5 Fair"],
                "Over 6.5": p_row["Over 6.5 Fair"],
            }

            model_pct = float(line_to_prob[k_line_check])
            edge_pct = model_pct - implied

            pc1, pc2, pc3, pc4 = st.columns(4)
            pc1.metric("Sportsbook", str(best_book_row["bookmaker"]))
            pc2.metric("Book Odds", str(book_odds))
            pc3.metric("Model %", f"{model_pct:.1f}%")
            pc4.metric("Fair Odds", str(line_to_fair[k_line_check]))

            st.write(f"**Book Implied %:** {implied:.1f}%")
            st.write(f"**Edge %:** {edge_pct:.1f}%")
            st.write(f"**Verdict:** {edge_grade(edge_pct)}")
        else:
            st.info("No matching pitcher strikeout prop found yet.")

# =========================================================
# MAIN TABLES
# =========================================================
st.subheader("🔥 Best Rated Picks For The Day")
top_display = best_picks_df.head(15).copy()

def grade_badge(g):
    if g == "🔥 LOCK":
        return "🟥 🔥 LOCK"
    if g == "✅ STRONG":
        return "🟩 ✅ STRONG"
    if g == "⚠️ LEAN":
        return "🟨 ⚠️ LEAN"
    return "⬜ ❌ PASS"

top_display["Grade"] = top_display["Grade"].apply(grade_badge)
st.dataframe(top_display, use_container_width=True)

st.subheader("🎯 Best Pitcher Strikeout Chances")
if pitchers_df.empty:
    st.info("No pitcher K board available yet.")
else:
    pitchers_show = pitchers_df.copy()
    pitchers_show["Grade"] = pitchers_show["Grade"].apply(grade_badge)
    st.dataframe(pitchers_show.head(15), use_container_width=True)

st.subheader("⚾ Best Batter Hit Chances")
st.dataframe(batters_df.sort_values("Hit %", ascending=False).head(15), use_container_width=True)

st.subheader("💣 Best Home Run Chances")
st.dataframe(batters_df.sort_values("HR %", ascending=False).head(15), use_container_width=True)

st.subheader("🏃 Best Total Bases Chances")
st.dataframe(batters_df.sort_values("TB %", ascending=False).head(15), use_container_width=True)

st.subheader("💰 Best RBI Chances")
st.dataframe(batters_df.sort_values("RBI %", ascending=False).head(15), use_container_width=True)

# =========================================================
# WHY THESE PICKS
# =========================================================
st.subheader("🧠 Why These Picks (Top 5 Breakdown)")
top5 = best_picks_df.head(5)

for _, rec in top5.iterrows():
    batter_row = batters[batters["_keys"].apply(lambda s: norm_text(rec["Player"]) in s)].iloc[0]
    pitcher_row = pitchers[pitchers["_keys"].apply(lambda s: norm_text(rec["Pitcher"]) in s)].iloc[0]

    b = get_batter_metrics(batter_row)
    p = get_pitcher_metrics(pitcher_row)

    st.markdown(f"### 🔥 {rec['Player']} ({rec['Best Prop']})")
    st.write(f"""
**Matchup:** vs {rec['Pitcher']}  
**Park:** {rec['Park']}

**Why the model likes this:**
- Batter xBA: {round(b['xba'], 3)}
- Batter xSLG: {round(b['xslg'], 3)}
- Barrel Rate: {round(b['barrel'] * 100, 1)}%
- Hard Hit %: {round(b['hardhit'] * 100, 1)}%

- Pitcher xBA allowed: {round(p['xba'], 3)}
- Pitcher xSLG allowed: {round(p['xslg'], 3)}
- Pitcher K%: {round(p['k_rate'] * 100, 1)}%

**Best Prop %:** {rec['Best Prop %']}  
**Fair Odds:** {rec['Fair Odds']}  
**Model Score:** {rec['Model Score']}  
**Grade:** {rec['Grade']}
""")
    st.divider()

with st.expander("Full Batter Board"):
    st.dataframe(
        batters_df.sort_values(["Model Score", "Hit %"], ascending=[False, False]),
        use_container_width=True,
    )

if skipped:
    with st.expander("Skipped Rows / Name Debug"):
        for item in skipped:
            st.write(item)
