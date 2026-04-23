import math
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
import streamlit as st

# =========================================================
# PAGE
# =========================================================
st.set_page_config(
    page_title="CJ Elite MLB HR Board",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #050912 0%, #08101d 100%);
            color: #f8fafc;
        }
        .block-container {
            max-width: 1650px;
            padding-top: 1rem;
            padding-bottom: 2rem;
        }
        .hero-card {
            background: linear-gradient(135deg, rgba(65,24,21,.95), rgba(21,27,45,.95));
            border: 1px solid rgba(251,146,60,.35);
            border-radius: 22px;
            padding: 22px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,.28);
            margin-bottom: 18px;
        }
        .game-card {
            background: linear-gradient(145deg, #111827, #0a1020);
            border-radius: 18px;
            padding: 16px;
            min-height: 190px;
            box-shadow: 0 8px 24px rgba(0,0,0,.20);
            margin-bottom: 14px;
        }
        .detail-card {
            background: linear-gradient(145deg, #111827, #0b1220);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 16px;
            padding: 14px 18px;
            margin-bottom: 14px;
        }
        .status-bar {
            background: linear-gradient(90deg, rgba(11,111,67,.85), rgba(16,79,102,.65));
            border: 1px solid rgba(74,222,128,.25);
            border-radius: 14px;
            padding: 11px 14px;
            color: #d1fae5;
            font-weight: 700;
            margin: 12px 0 14px 0;
        }
        .chip-green, .chip-red, .chip-neutral {
            display: inline-block;
            padding: 11px 15px;
            border-radius: 14px;
            margin: 0 8px 8px 0;
            font-weight: 700;
            font-size: 14px;
        }
        .chip-green {
            background: #052e1a;
            color: #86efac;
            border: 1px solid #14532d;
        }
        .chip-red {
            background: #2b0a0a;
            color: #fca5a5;
            border: 1px solid #7f1d1d;
        }
        .chip-neutral {
            background: #111827;
            color: #d1d5db;
            border: 1px solid #374151;
        }
        .hr-table-wrap {
            overflow-x: auto;
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 16px;
            margin-top: 10px;
        }
        table.hr-table {
            width: 100%;
            border-collapse: collapse;
            background: #0b1220;
            color: white;
            font-size: 14px;
        }
        table.hr-table th {
            background: #111827;
            color: #f8fafc;
            padding: 11px 12px;
            border-bottom: 1px solid #1f2937;
            text-align: left;
            white-space: nowrap;
        }
        table.hr-table td {
            padding: 10px 12px;
            border-bottom: 1px solid rgba(255,255,255,.06);
            white-space: nowrap;
        }
        .grade-aplus { background:#166534; color:white; font-weight:700; }
        .grade-a { background:#15803d; color:white; font-weight:700; }
        .grade-aminus { background:#16a34a; color:white; font-weight:700; }
        .grade-bplus { background:#1d4ed8; color:white; font-weight:700; }
        .grade-b { background:#2563eb; color:white; font-weight:700; }
        .grade-c { background:#6d28d9; color:white; font-weight:700; }

        .rf-hot { color:#86efac; font-weight:700; }
        .rf-good { color:#93c5fd; font-weight:700; }
        .rf-average { color:#fde68a; font-weight:700; }
        .rf-slump { color:#fca5a5; font-weight:700; }

        .pow-high { background: rgba(34,197,94,.34); }
        .pow-mid { background: rgba(34,197,94,.20); }
        .pow-low { background: rgba(34,197,94,.08); }

        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, #111827, #0f172a);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 16px;
            padding: 10px;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 14px;
            overflow: hidden;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔥 CJ Elite MLB Home Run Board")
st.caption("Fixed for batters.csv with no team column")

# =========================================================
# HELPERS
# =========================================================
def find_col(df: pd.DataFrame, names: list[str]) -> Optional[str]:
    cols = {str(c).strip().lower(): c for c in df.columns}
    for name in names:
        key = name.lower().strip()
        if key in cols:
            return cols[key]
    for name in names:
        key = name.lower().strip()
        for c in df.columns:
            if key in str(c).lower():
                return c
    return None


def req_col(df: pd.DataFrame, names: list[str], label: str) -> str:
    col = find_col(df, names)
    if col is None:
        st.error(f"Missing {label}. Found columns: {list(df.columns)}")
        st.stop()
    return col


def safe_float(x, default=0.0) -> float:
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def pct_to_dec(x, default=0.0) -> float:
    try:
        if pd.isna(x):
            return default
        v = float(x)
        return v / 100 if v > 1 else v
    except Exception:
        return default


def clamp(x: float, low: float, high: float) -> float:
    return max(low, min(high, x))


def logistic(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def scale01(x: float, low: float, high: float) -> float:
    if high <= low:
        return 0.5
    return clamp((x - low) / (high - low), 0.0, 1.0)


def norm_text(x) -> str:
    return " ".join(str(x).strip().lower().replace(",", "").split())


def first_last_name(x) -> str:
    text = str(x).strip()
    if "," in text:
        parts = [p.strip() for p in text.split(",", 1)]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}".strip()
    return text


def make_name_keys(x) -> set[str]:
    raw = str(x).strip()
    return {norm_text(raw), norm_text(first_last_name(raw))}


def prob_to_fair_american(prob: float):
    if prob <= 0 or prob >= 1:
        return None
    if prob >= 0.5:
        return int(round(-(prob / (1 - prob)) * 100))
    return int(round(((1 - prob) / prob) * 100))


def estimate_plate_appearances(lineup_spot) -> float:
    try:
        s = int(float(lineup_spot))
    except Exception:
        return 4.2
    pa_map = {
        1: 4.85, 2: 4.75, 3: 4.65, 4: 4.55, 5: 4.45,
        6: 4.30, 7: 4.15, 8: 4.00, 9: 3.85
    }
    return pa_map.get(s, 4.2)


def rbi_lineup_boost(lineup_spot) -> float:
    try:
        s = int(float(lineup_spot))
    except Exception:
        return 1.0
    boost_map = {
        1: 0.86, 2: 0.95, 3: 1.10, 4: 1.16, 5: 1.08,
        6: 1.00, 7: 0.93, 8: 0.88, 9: 0.82
    }
    return boost_map.get(s, 1.0)


def platoon_boost(batter_hand, pitcher_hand) -> float:
    bh = str(batter_hand).strip().upper()
    ph = str(pitcher_hand).strip().upper()
    if bh in ["L", "R"] and ph in ["L", "R"]:
        return 1.03 if bh != ph else 0.98
    return 1.00


def normalize_team(val: str) -> str:
    v = norm_text(val)
    mapping = {
        "new york yankees": "nyy", "yankees": "nyy", "nyy": "nyy",
        "boston red sox": "bos", "red sox": "bos", "bos": "bos",
        "los angeles dodgers": "lad", "dodgers": "lad", "lad": "lad",
        "new york mets": "nym", "mets": "nym", "nym": "nym",
        "atlanta braves": "atl", "braves": "atl", "atl": "atl",
        "philadelphia phillies": "phi", "phillies": "phi", "phi": "phi",
        "chicago cubs": "chc", "cubs": "chc", "chc": "chc",
        "chicago white sox": "cws", "white sox": "cws", "cws": "cws",
        "houston astros": "hou", "astros": "hou", "hou": "hou",
        "texas rangers": "tex", "rangers": "tex", "tex": "tex",
        "san francisco giants": "sf", "giants": "sf", "sf": "sf",
        "san diego padres": "sd", "padres": "sd", "sd": "sd",
        "milwaukee brewers": "mil", "brewers": "mil", "mil": "mil",
        "detroit tigers": "det", "tigers": "det", "det": "det",
        "minnesota twins": "min", "twins": "min", "min": "min",
        "pittsburgh pirates": "pit", "pirates": "pit", "pit": "pit",
        "washington nationals": "wsh", "nationals": "wsh", "wsh": "wsh", "nats": "wsh",
        "arizona diamondbacks": "ari", "diamondbacks": "ari", "dbacks": "ari", "ari": "ari",
        "colorado rockies": "col", "rockies": "col", "col": "col",
        "cleveland guardians": "cle", "guardians": "cle", "cle": "cle",
        "kansas city royals": "kc", "royals": "kc", "kc": "kc",
        "toronto blue jays": "tor", "blue jays": "tor", "tor": "tor",
        "seattle mariners": "sea", "mariners": "sea", "sea": "sea",
        "tampa bay rays": "tb", "rays": "tb", "tb": "tb",
        "miami marlins": "mia", "marlins": "mia", "mia": "mia",
        "cincinnati reds": "cin", "reds": "cin", "cin": "cin",
        "baltimore orioles": "bal", "orioles": "bal", "bal": "bal",
        "los angeles angels": "laa", "angels": "laa", "laa": "laa",
        "oakland athletics": "oak", "athletics": "oak", "a's": "oak", "oak": "oak",
    }
    return mapping.get(v, v)


def weather_bucket(hr_mult: float) -> str:
    if hr_mult >= 1.03:
        return "Favorable"
    if hr_mult <= 0.97:
        return "Unfavorable"
    return "Neutral"


def grade_class(g: str) -> str:
    return {
        "A+": "grade-aplus",
        "A": "grade-a",
        "A-": "grade-aminus",
        "B+": "grade-bplus",
        "B": "grade-b",
        "C": "grade-c",
    }.get(g, "grade-c")


def form_class(f: str) -> str:
    return {
        "Hot": "rf-hot",
        "Good": "rf-good",
        "Average": "rf-average",
        "Slump": "rf-slump",
    }.get(f, "rf-average")


def value_bg_class(v: float) -> str:
    if v >= 0.80:
        return "pow-high"
    if v >= 0.55:
        return "pow-mid"
    return "pow-low"


# =========================================================
# WEATHER
# =========================================================
def park_weather_location(park_name: str):
    park_map = {
        "chase field": ("Phoenix", "AZ"),
        "truist park": ("Atlanta", "GA"),
        "oriole park at camden yards": ("Baltimore", "MD"),
        "fenway park": ("Boston", "MA"),
        "wrigley field": ("Chicago", "IL"),
        "guaranteed rate field": ("Chicago", "IL"),
        "great american ball park": ("Cincinnati", "OH"),
        "progressive field": ("Cleveland", "OH"),
        "coors field": ("Denver", "CO"),
        "comerica park": ("Detroit", "MI"),
        "minute maid park": ("Houston", "TX"),
        "kauffman stadium": ("Kansas City", "MO"),
        "angel stadium": ("Anaheim", "CA"),
        "dodger stadium": ("Los Angeles", "CA"),
        "loandepot park": ("Miami", "FL"),
        "american family field": ("Milwaukee", "WI"),
        "target field": ("Minneapolis", "MN"),
        "citi field": ("Queens", "NY"),
        "yankee stadium": ("Bronx", "NY"),
        "sutter health park": ("West Sacramento", "CA"),
        "citizens bank park": ("Philadelphia", "PA"),
        "pnc park": ("Pittsburgh", "PA"),
        "petco park": ("San Diego", "CA"),
        "oracle park": ("San Francisco", "CA"),
        "t-mobile park": ("Seattle", "WA"),
        "busch stadium": ("St. Louis", "MO"),
        "george m. steinbrenner field": ("Tampa", "FL"),
        "globe life field": ("Arlington", "TX"),
        "rogers centre": ("Toronto", "ON"),
        "nationals park": ("Washington", "DC"),
    }
    return park_map.get(str(park_name).strip().lower(), ("", ""))


@st.cache_data(ttl=1800)
def get_weather_for_city(city: str, state: str = ""):
    if not city:
        return {
            "temp_f": 70,
            "wind_mph": 8,
            "humidity": 50,
            "desc": "",
            "wind_dir_16": "",
            "wind_dir_deg": 180,
        }

    query = f"{city},{state}" if state else city
    url = "https://wttr.in/{}?format=j1".format(query.replace(" ", "%20"))
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        current = data["current_condition"][0]
        return {
            "temp_f": safe_float(current.get("temp_F"), 70),
            "wind_mph": safe_float(current.get("windspeedMiles"), 8),
            "humidity": safe_float(current.get("humidity"), 50),
            "desc": current.get("weatherDesc", [{}])[0].get("value", ""),
            "wind_dir_16": current.get("winddir16Point", ""),
            "wind_dir_deg": safe_float(current.get("winddirDegree"), 180),
        }
    except Exception:
        return {
            "temp_f": 70,
            "wind_mph": 8,
            "humidity": 50,
            "desc": "",
            "wind_dir_16": "",
            "wind_dir_deg": 180,
        }


def angle_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def get_park_outfield_bearing(park_name: str) -> float:
    bearings = {
        "chase field": 20, "truist park": 30, "oriole park at camden yards": 45,
        "fenway park": 50, "wrigley field": 35, "guaranteed rate field": 20,
        "great american ball park": 15, "progressive field": 40, "coors field": 20,
        "comerica park": 25, "minute maid park": 35, "kauffman stadium": 30,
        "angel stadium": 25, "dodger stadium": 35, "loandepot park": 25,
        "american family field": 30, "target field": 40, "citi field": 20,
        "yankee stadium": 30, "sutter health park": 25, "citizens bank park": 20,
        "pnc park": 35, "petco park": 25, "oracle park": 35, "t-mobile park": 25,
        "busch stadium": 25, "george m. steinbrenner field": 25, "globe life field": 20,
        "rogers centre": 25, "nationals park": 25,
    }
    return bearings.get(str(park_name).strip().lower(), 25)


def estimate_wind_direction_impact(wind_dir_deg: float, wind_mph: float, park_name: str):
    out_bearing = get_park_outfield_bearing(park_name)
    out_diff = angle_diff(wind_dir_deg, out_bearing)
    in_diff = angle_diff(wind_dir_deg, (out_bearing + 180) % 360)
    out_factor = max(0.0, 1 - (out_diff / 90))
    in_factor = max(0.0, 1 - (in_diff / 90))

    hr_dir_mult = 1 + (wind_mph * 0.010 * out_factor) - (wind_mph * 0.012 * in_factor)
    run_dir_mult = 1 + (wind_mph * 0.006 * out_factor) - (wind_mph * 0.007 * in_factor)

    return {
        "hr_dir_mult": clamp(hr_dir_mult, 0.82, 1.20),
        "run_dir_mult": clamp(run_dir_mult, 0.88, 1.14),
        "wind_out_score": round(out_factor, 3),
        "wind_in_score": round(in_factor, 3),
    }


def estimate_weather_multipliers(temp_f, wind_mph, humidity, desc="", wind_dir_deg=180, park_name=""):
    desc_l = str(desc).lower()
    temp_run = 1.00 + ((temp_f - 70) * 0.0035)
    temp_hr = 1.00 + ((temp_f - 70) * 0.0050)
    humid_run = 1.00 + ((humidity - 50) * 0.0012)
    humid_hr = 1.00 + ((humidity - 50) * 0.0018)

    rain_penalty = 1.00
    if "rain" in desc_l or "shower" in desc_l or "storm" in desc_l:
        rain_penalty = 0.94
    if "snow" in desc_l:
        rain_penalty = 0.90

    wind_dir = estimate_wind_direction_impact(wind_dir_deg, wind_mph, park_name)

    run_mult = temp_run * humid_run * rain_penalty * wind_dir["run_dir_mult"]
    hr_mult = temp_hr * humid_hr * rain_penalty * wind_dir["hr_dir_mult"]

    return {
        "run_mult": clamp(run_mult, 0.88, 1.15),
        "hr_mult": clamp(hr_mult, 0.82, 1.24),
        "wind_out_score": wind_dir["wind_out_score"],
        "wind_in_score": wind_dir["wind_in_score"],
    }


# =========================================================
# MLB DATA
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
    for d in data.get("dates", []):
        for g in d.get("games", []):
            try:
                games.append(
                    {
                        "gamePk": g.get("gamePk"),
                        "away_team": g["teams"]["away"]["team"]["name"],
                        "home_team": g["teams"]["home"]["team"]["name"],
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
            if full_name:
                players.append(
                    {
                        "name": full_name,
                        "lineup_spot": idx,
                        "batter_hand": bats,
                    }
                )
        return players

    return {"away": extract_side("away"), "home": extract_side("home")}


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
        team_abbr = normalize_team(team["abbreviation"])
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
# LOAD CSV
# =========================================================
batters = pd.read_csv("batters.csv")
pitchers = pd.read_csv("pitchers.csv")
parks = pd.read_csv("parks.csv")

# build batter name from last_name, first_name if needed
bat_lastfirst = find_col(batters, ["last_name, first_name", "last_name_first_name"])
if bat_lastfirst:
    batters["_player_name"] = batters[bat_lastfirst].astype(str).apply(first_last_name)
else:
    bat_name_direct = find_col(batters, ["player_name", "name", "player"])
    if bat_name_direct is None:
        st.error(f"Could not find batter name column. Found columns: {list(batters.columns)}")
        st.stop()
    batters["_player_name"] = batters[bat_name_direct].astype(str)

pit_lastfirst = find_col(pitchers, ["last_name, first_name", "last_name_first_name"])
if pit_lastfirst:
    pitchers["_player_name"] = pitchers[pit_lastfirst].astype(str).apply(first_last_name)
else:
    pit_name_direct = find_col(pitchers, ["player_name", "name", "player"])
    if pit_name_direct is None:
        st.error(f"Could not find pitcher name column. Found columns: {list(pitchers.columns)}")
        st.stop()
    pitchers["_player_name"] = pitchers[pit_name_direct].astype(str)

# map columns
b_xba = find_col(batters, ["est_ba", "xba"])
b_xslg = find_col(batters, ["est_slg", "xslg"])
b_xwoba = find_col(batters, ["est_woba", "xwoba"])
b_pa = find_col(batters, ["pa"])
b_barrel = find_col(batters, ["barrel", "barrel_pct", "brl_percent"])
b_hardhit = find_col(batters, ["hard_hit", "hardhit", "hard_hit_pct", "hard_hit_percent"])
b_k = find_col(batters, ["k_percent", "k%", "strikeout_percent"])
b_bb = find_col(batters, ["bb_percent", "bb%", "walk_percent"])
b_fb = find_col(batters, ["fb_percent", "fly_ball_percent", "flyball"])

p_xba = find_col(pitchers, ["est_ba", "xba"])
p_xslg = find_col(pitchers, ["est_slg", "xslg"])
p_xwoba = find_col(pitchers, ["est_woba", "xwoba"])
p_barrel = find_col(pitchers, ["barrel", "barrel_pct", "brl_percent"])
p_hardhit = find_col(pitchers, ["hard_hit", "hardhit", "hard_hit_pct", "hard_hit_percent"])
p_k = find_col(pitchers, ["k_percent", "k%", "strikeout_percent"])
p_bb = find_col(pitchers, ["bb_percent", "bb%", "walk_percent"])
p_hr9 = find_col(pitchers, ["hr_per_9", "hr9", "hr/9"])

park_name_col = req_col(parks, ["park_name", "venue_name", "park", "venue"], "park name")
park_hr_col = find_col(parks, ["hr_factor", "hr", "home_run"])
park_hit_col = find_col(parks, ["hit_factor", "hit", "hits"])

# prep
batters = batters.copy()
pitchers = pitchers.copy()
parks = parks.copy()

batters["_keys"] = batters["_player_name"].astype(str).apply(make_name_keys)
pitchers["_keys"] = pitchers["_player_name"].astype(str).apply(make_name_keys)
parks["_park"] = parks[park_name_col].astype(str).str.strip().str.lower()

roster_map = get_mlb_roster_map()
batters["_team_norm"] = batters["_player_name"].astype(str).apply(lambda x: roster_map.get(norm_text(x), roster_map.get(norm_text(first_last_name(x)), "")))

# sidebar
with st.sidebar:
    st.title("⚾ Filters")
    show_unconfirmed = st.toggle("Show fallback hitters when lineups aren't posted", value=True)
    min_hr_prob = st.slider("Minimum HR %", 0.0, 40.0, 10.0, 0.5)
    min_model_score = st.slider("Minimum Hitter Model Score", 0.0, 100.0, 0.0, 0.5)
    min_grade = st.selectbox("Minimum HR Grade", ["All", "A+", "A", "A-", "B+", "B", "C"])
    search_name = st.text_input("Search Player")

# schedule + weather
games, games_err = get_today_schedule()
if not games:
    st.warning(f"Could not load today's schedule. {games_err if games_err else ''}")
    st.stop()

schedule_df = pd.DataFrame(games)

weather_map = {}
for game in games:
    city, state = park_weather_location(game["park"])
    wx = get_weather_for_city(city, state)
    wx_mult = estimate_weather_multipliers(
        wx["temp_f"], wx["wind_mph"], wx["humidity"], wx["desc"], wx["wind_dir_deg"], game["park"]
    )
    weather_map[game["gamePk"]] = {
        "temp_f": wx["temp_f"],
        "wind_mph": wx["wind_mph"],
        "desc": wx["desc"],
        "wind_dir_16": wx["wind_dir_16"],
        "run_mult": wx_mult["run_mult"],
        "hr_mult": wx_mult["hr_mult"],
        "wind_out_score": wx_mult["wind_out_score"],
        "wind_in_score": wx_mult["wind_in_score"],
    }

# matchups
auto_rows = []
lineup_status_rows = []

def get_park_factors(park_key):
    row = parks.loc[parks["_park"] == park_key]
    if row.empty:
        return {"hr_factor": 1.00, "hit_factor": 1.00}
    row = row.iloc[0]
    hr_raw = safe_float(row[park_hr_col], 1.00) if park_hr_col else 1.00
    hit_raw = safe_float(row[park_hit_col], 1.00) if park_hit_col else 1.00
    hr_factor = hr_raw / 100.0 if hr_raw > 3 else hr_raw
    hit_factor = hit_raw / 100.0 if hit_raw > 3 else hit_raw
    return {"hr_factor": hr_factor, "hit_factor": hit_factor}

for game in games:
    away_team = game["away_team"]
    home_team = game["home_team"]
    away_pitcher = game["away_pitcher"]
    home_pitcher = game["home_pitcher"]
    park = game["park"]
    game_pk = game["gamePk"]

    wx = weather_map.get(game_pk, {})
    lineups = get_game_lineups(game_pk)
    away_lineup = lineups.get("away", [])
    home_lineup = lineups.get("home", [])

    lineup_status_rows.append(
        {
            "Game": f"{away_team} @ {home_team}",
            "Away Lineup Posted": len(away_lineup) > 0,
            "Home Lineup Posted": len(home_lineup) > 0,
            "Park": park,
        }
    )

    common_weather = {
        "temp_f": wx.get("temp_f", 70),
        "wind_mph": wx.get("wind_mph", 8),
        "wind_dir_16": wx.get("wind_dir_16", ""),
        "conditions": wx.get("desc", ""),
        "run_weather_mult": wx.get("run_mult", 1.0),
        "hr_weather_mult": wx.get("hr_mult", 1.0),
        "wind_out_score": wx.get("wind_out_score", 0.0),
        "wind_in_score": wx.get("wind_in_score", 0.0),
        "matchup": f"{away_team} @ {home_team}",
        "game_time": game.get("game_time", ""),
    }

    if home_pitcher:
        if away_lineup:
            for hitter in away_lineup:
                auto_rows.append(
                    {
                        "batter": hitter["name"],
                        "pitcher": home_pitcher,
                        "park": park,
                        "team": away_team,
                        "pitcher_team": home_team,
                        "batter_hand": hitter.get("batter_hand", ""),
                        "pitcher_hand": "",
                        "lineup_spot": hitter.get("lineup_spot", None),
                        "lineup_source": "Final" if len(away_lineup) >= 8 else "RotoWire",
                        "game_status": "🟢 Scheduled",
                        **common_weather,
                    }
                )
        elif show_unconfirmed:
            away_norm = normalize_team(away_team)
            away_hitters = batters[batters["_team_norm"] == away_norm]
            for _, b_row in away_hitters.iterrows():
                auto_rows.append(
                    {
                        "batter": b_row["_player_name"],
                        "pitcher": home_pitcher,
                        "park": park,
                        "team": away_team,
                        "pitcher_team": home_team,
                        "batter_hand": "",
                        "pitcher_hand": "",
                        "lineup_spot": None,
                        "lineup_source": "Projected",
                        "game_status": "🟢 Scheduled",
                        **common_weather,
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
                        "team": home_team,
                        "pitcher_team": away_team,
                        "batter_hand": hitter.get("batter_hand", ""),
                        "pitcher_hand": "",
                        "lineup_spot": hitter.get("lineup_spot", None),
                        "lineup_source": "Final" if len(home_lineup) >= 8 else "RotoWire",
                        "game_status": "🟢 Scheduled",
                        **common_weather,
                    }
                )
        elif show_unconfirmed:
            home_norm = normalize_team(home_team)
            home_hitters = batters[batters["_team_norm"] == home_norm]
            for _, b_row in home_hitters.iterrows():
                auto_rows.append(
                    {
                        "batter": b_row["_player_name"],
                        "pitcher": away_pitcher,
                        "park": park,
                        "team": home_team,
                        "pitcher_team": away_team,
                        "batter_hand": "",
                        "pitcher_hand": "",
                        "lineup_spot": None,
                        "lineup_source": "Projected",
                        "game_status": "🟢 Scheduled",
                        **common_weather,
                    }
                )

matchups = pd.DataFrame(auto_rows)
if matchups.empty:
    st.error("No matchup rows built.")
    st.stop()

matchups["_batter"] = matchups["batter"].astype(str).map(norm_text)
matchups["_pitcher"] = matchups["pitcher"].astype(str).map(norm_text)
matchups["_park"] = matchups["park"].astype(str).str.strip().str.lower()

# model functions
def get_batter_metrics(row):
    pa_val = safe_float(row[b_pa], 250.0) if b_pa else 250.0
    recent_proxy = clamp(pa_val / 650.0, 0.20, 1.00)

    xslg = safe_float(row[b_xslg], 0.390) if b_xslg else 0.390
    barrel = pct_to_dec(row[b_barrel], 0.08) if b_barrel else 0.08
    hardhit = pct_to_dec(row[b_hardhit], 0.38) if b_hardhit else 0.38
    xba = safe_float(row[b_xba], 0.240) if b_xba else 0.240
    xwoba = safe_float(row[b_xwoba], 0.310) if b_xwoba else 0.310
    k_rate = pct_to_dec(row[b_k], 0.22) if b_k else 0.22
    bb_rate = pct_to_dec(row[b_bb], 0.08) if b_bb else 0.08

    recent_form_score = clamp(
        0.40 * scale01(xslg, 0.300, 0.750)
        + 0.30 * scale01(barrel, 0.02, 0.25)
        + 0.20 * scale01(hardhit, 0.20, 0.65)
        + 0.10 * recent_proxy,
        0.0,
        1.0,
    )

    return {
        "xba": xba,
        "xslg": xslg,
        "xwoba": xwoba,
        "barrel": barrel,
        "hardhit": hardhit,
        "k_rate": k_rate,
        "bb_rate": bb_rate,
        "recent_form_score": recent_form_score,
    }


def get_pitcher_metrics(row):
    return {
        "xba": safe_float(row[p_xba], 0.240) if p_xba else 0.240,
        "xslg": safe_float(row[p_xslg], 0.390) if p_xslg else 0.390,
        "xwoba": safe_float(row[p_xwoba], 0.310) if p_xwoba else 0.310,
        "barrel": pct_to_dec(row[p_barrel], 0.08) if p_barrel else 0.08,
        "hardhit": pct_to_dec(row[p_hardhit], 0.38) if p_hardhit else 0.38,
        "k_rate": pct_to_dec(row[p_k], 0.22) if p_k else 0.22,
        "bb_rate": pct_to_dec(row[p_bb], 0.08) if p_bb else 0.08,
        "hr9": safe_float(row[p_hr9], 1.05) if p_hr9 else 1.05,
    }


def calc_batter_board(batter_row, pitcher_row, matchup_row):
    b = get_batter_metrics(batter_row)
    p = get_pitcher_metrics(pitcher_row)
    park = get_park_factors(matchup_row["_park"])

    platoon = platoon_boost(matchup_row.get("batter_hand", ""), matchup_row.get("pitcher_hand", ""))
    hit_weather_mult = safe_float(matchup_row.get("run_weather_mult", 1.0), 1.0)
    hr_weather_mult = safe_float(matchup_row.get("hr_weather_mult", 1.0), 1.0)
    run_weather_mult = safe_float(matchup_row.get("run_weather_mult", 1.0), 1.0)
    plate_appearances = estimate_plate_appearances(matchup_row.get("lineup_spot", 5))
    team_total_mult = clamp(run_weather_mult, 0.88, 1.15)

    hit_score_raw = (
        1.9 * (b["xba"] - 0.240)
        + 0.9 * (b["xwoba"] - 0.310)
        + 0.5 * (b["hardhit"] - 0.38)
        - 0.9 * (b["k_rate"] - 0.22)
        - 1.3 * (p["k_rate"] - 0.22)
        - 1.0 * (p["xba"] - 0.240)
    )
    hit_prob_pa = logistic(-1.35 + hit_score_raw) * park["hit_factor"] * platoon * hit_weather_mult
    hit_prob_pa = clamp(hit_prob_pa, 0.025, 0.55)
    hit_prob = 1 - (1 - hit_prob_pa) ** plate_appearances
    hit_prob = clamp(hit_prob, 0.18, 0.88)

    hr_score_raw = (
        4.2 * (b["xslg"] - 0.390)
        + 2.6 * (b["barrel"] - 0.08)
        + 1.2 * (b["hardhit"] - 0.38)
        + 2.1 * (p["xslg"] - 0.390)
        + 1.4 * (p["barrel"] - 0.08)
        + 0.9 * (p["hr9"] - 1.05)
    )
    hr_prob_pa = logistic(-3.9 + hr_score_raw)
    hr_prob = 1 - (1 - hr_prob_pa) ** plate_appearances
    hr_prob *= park["hr_factor"]
    hr_prob *= hr_weather_mult
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
    tb_prob *= park["hit_factor"] * hit_weather_mult
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
    rbi_prob *= park["hit_factor"] * hit_weather_mult
    rbi_prob *= team_total_mult
    rbi_prob *= platoon
    rbi_prob *= rbi_lineup_boost(matchup_row.get("lineup_spot", 5))
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
        "weighted_score": weighted_score,
    }


def calc_hr_model(batter_row, pitcher_row, matchup_row):
    b = get_batter_metrics(batter_row)
    p = get_pitcher_metrics(pitcher_row)
    park = get_park_factors(matchup_row["_park"])

    lineup_value = estimate_plate_appearances(matchup_row.get("lineup_spot", None))
    platoon_mult = platoon_boost(matchup_row.get("batter_hand", ""), matchup_row.get("pitcher_hand", ""))
    hr_weather_mult = safe_float(matchup_row.get("hr_weather_mult", 1.0), 1.0)

    batter_power = clamp(
        0.35 * scale01(b["xslg"], 0.300, 0.750)
        + 0.30 * scale01(b["barrel"], 0.02, 0.25)
        + 0.20 * scale01(b["hardhit"], 0.20, 0.65)
        + 0.15 * b["recent_form_score"],
        0.0, 1.0
    )

    pitcher_vulnerability = clamp(
        0.35 * scale01(p["xslg"], 0.300, 0.650)
        + 0.25 * scale01(p["barrel"], 0.02, 0.18)
        + 0.20 * scale01(p["hardhit"], 0.20, 0.60)
        + 0.20 * scale01(p["hr9"], 0.3, 2.2),
        0.0, 1.0
    )

    context_score = clamp(
        0.30 * scale01(park["hr_factor"], 0.80, 1.25)
        + 0.30 * scale01(hr_weather_mult, 0.85, 1.20)
        + 0.20 * scale01(platoon_mult, 0.95, 1.05)
        + 0.20 * scale01(lineup_value, 3.8, 4.9),
        0.0, 1.0
    )

    power_match = clamp((0.55 * batter_power) + (0.45 * pitcher_vulnerability), 0.0, 1.0)
    raw_hr_score = 0.38 * batter_power + 0.27 * pitcher_vulnerability + 0.20 * context_score + 0.15 * power_match
    hr_probability = clamp(0.08 + (raw_hr_score * 0.18), 0.02, 0.30)

    return {
        "batter_power": batter_power,
        "pitcher_vulnerability": pitcher_vulnerability,
        "context_score": context_score,
        "power_match": power_match,
        "hr_probability": hr_probability,
        "recent_form_label": recent_form_label(b["recent_form_score"]),
        "fair_odds": prob_to_fair_american(hr_probability),
        "weather_note": weather_bucket(hr_weather_mult),
    }


hitter_rows = []
hr_rows = []
skipped = []

for _, mrow in matchups.iterrows():
    batter_match = batters[batters["_keys"].apply(lambda s: mrow["_batter"] in s)]
    pitcher_match = pitchers[pitchers["_keys"].apply(lambda s: mrow["_pitcher"] in s)]

    if batter_match.empty:
        skipped.append(f"Batter not found: {mrow['batter']}")
        continue
    if pitcher_match.empty:
        skipped.append(f"Pitcher not found: {mrow['pitcher']}")
        continue

    batter_row = batter_match.iloc[0]
    pitcher_row = pitcher_match.iloc[0]

    hit_calc = calc_batter_board(batter_row, pitcher_row, mrow)
    hr_calc = calc_hr_model(batter_row, pitcher_row, mrow)

    hitter_rows.append(
        {
            "Batter": mrow["batter"],
            "Pitcher": mrow["pitcher"],
            "Team": mrow.get("team", ""),
            "Park": mrow["park"],
            "Hit %": round(hit_calc["hit_prob"] * 100, 1),
            "HR %": round(hit_calc["hr_prob"] * 100, 1),
            "TB %": round(hit_calc["tb_prob"] * 100, 1),
            "RBI %": round(hit_calc["rbi_prob"] * 100, 1),
            "Hit Fair Odds": prob_to_fair_american(hit_calc["hit_prob"]),
            "HR Fair Odds": prob_to_fair_american(hit_calc["hr_prob"]),
            "TB Fair Odds": prob_to_fair_american(hit_calc["tb_prob"]),
            "RBI Fair Odds": prob_to_fair_american(hit_calc["rbi_prob"]),
            "Model Score": round(hit_calc["weighted_score"], 1),
            "Why": f'{hr_calc["weather_note"]} | Power {hr_calc["batter_power"]:.2f} | Vuln {hr_calc["pitcher_vulnerability"]:.2f} | Ctx {hr_calc["context_score"]:.2f}',
            "Matchup": mrow.get("matchup", ""),
        }
    )

    fair = hr_calc["fair_odds"]
    fair_str = f"{fair:+d}" if fair is not None else "N/A"

    hr_rows.append(
        {
            "Matchup": mrow.get("matchup", ""),
            "Game Time": mrow.get("game_time", ""),
            "Batter": mrow["batter"],
            "Batter Team": find_team(mrow["batter"]) or normalize_team(mrow.get("team", "")),
            "Grade": "C",
            "HR Probability Value": round(hr_calc["hr_probability"] * 100, 1),
            "HR Probability": f'{hr_calc["hr_probability"] * 100:.1f}% ({fair_str})',
            "Recent Form": hr_calc["recent_form_label"],
            "Pitcher": mrow["pitcher"],
            "Pitcher Team": normalize_team(mrow.get("pitcher_team", "")),
            "Batter Power": round(hr_calc["batter_power"], 2),
            "Pitcher Vulnerability": round(hr_calc["pitcher_vulnerability"], 2),
            "Context Score": round(hr_calc["context_score"], 2),
            "Power Match": round(hr_calc["power_match"], 2),
            "Power Match Flames": flame_match(hr_calc["power_match"]),
            "Game Status": mrow.get("game_status", "🟢 Scheduled"),
            "Lineup": mrow.get("lineup_source", "Projected"),
            "Order": int(mrow["lineup_spot"]) if pd.notna(mrow.get("lineup_spot")) else "—",
            "EV": "N/A",
            "HR Odds": "N/A",
            "Park": mrow["park"],
            "Weather": hr_calc["weather_note"],
            "Temp": round(safe_float(mrow.get("temp_f"), 70), 1),
            "Wind MPH": round(safe_float(mrow.get("wind_mph"), 8), 1),
            "Wind Dir": mrow.get("wind_dir_16", ""),
        }
    )

batters_df = pd.DataFrame(hitter_rows)
hr_df = pd.DataFrame(hr_rows)

if batters_df.empty or hr_df.empty:
    st.error("No rows scored.")
    st.stop()

# grades
q90 = hr_df["HR Probability Value"].quantile(0.90)
q75 = hr_df["HR Probability Value"].quantile(0.75)
q55 = hr_df["HR Probability Value"].quantile(0.55)
q35 = hr_df["HR Probability Value"].quantile(0.35)
q20 = hr_df["HR Probability Value"].quantile(0.20)

def hr_grade(x):
    if x >= q90:
        return "A+"
    if x >= q75:
        return "A"
    if x >= q55:
        return "A-"
    if x >= q35:
        return "B+"
    if x >= q20:
        return "B"
    return "C"

hr_df["Grade"] = hr_df["HR Probability Value"].apply(hr_grade)

if len(batters_df) >= 4:
    bq90 = batters_df["Model Score"].quantile(0.90)
    bq65 = batters_df["Model Score"].quantile(0.65)
    bq35 = batters_df["Model Score"].quantile(0.35)

    def hitter_grade(x):
        if x >= bq90:
            return "🔥 LOCK"
        if x >= bq65:
            return "✅ STRONG"
        if x >= bq35:
            return "⚠️ LEAN"
        return "❌ PASS"

    batters_df["Best Grade"] = batters_df["Model Score"].apply(hitter_grade)
else:
    batters_df["Best Grade"] = "✅ STRONG"

# pitcher board
pitcher_rows = []
for pitcher_name, grp in batters_df.groupby("Pitcher"):
    p_match = pitchers[pitchers["_keys"].apply(lambda s: norm_text(pitcher_name) in s)]
    if p_match.empty:
        continue

    p_row = p_match.iloc[0]
    opp_batters = []
    for _, batter_rec in grp.iterrows():
        b_match = batters[batters["_keys"].apply(lambda s: norm_text(batter_rec["Batter"]) in s)]
        if not b_match.empty:
            opp_batters.append(get_batter_metrics(b_match.iloc[0]))

    p = get_pitcher_metrics(p_row)
    if opp_batters:
        avg_opp_k = sum(x["k_rate"] for x in opp_batters) / len(opp_batters)
        avg_opp_bb = sum(x["bb_rate"] for x in opp_batters) / len(opp_batters)
        avg_opp_xwoba = sum(x["xwoba"] for x in opp_batters) / len(opp_batters)
    else:
        avg_opp_k, avg_opp_bb, avg_opp_xwoba = 0.22, 0.08, 0.310

    effective_k_rate = clamp(
        0.60 * p["k_rate"] + 0.40 * avg_opp_k
        - 0.16 * (avg_opp_bb - 0.08)
        - 0.10 * (avg_opp_xwoba - 0.310)
        - 0.10 * (p["bb_rate"] - 0.08)
        - 0.08 * (p["xwoba"] - 0.310),
        0.14, 0.38
    )

    batters_faced = clamp(
        24.0
        + 5.2 * (p["k_rate"] - 0.22)
        - 3.0 * (p["bb_rate"] - 0.08)
        - 1.6 * (avg_opp_xwoba - 0.310),
        20.5, 28.0
    )

    expected_ks = effective_k_rate * batters_faced

    def over_prob(exp_ks, line):
        std_dev = 1.7 + 0.05 * max(0.0, 6.0 - exp_ks)
        z = (exp_ks - line) / std_dev
        return 1 / (1 + math.exp(-1.7 * z))

    prob_45 = over_prob(expected_ks, 4.5)
    prob_55 = over_prob(expected_ks, 5.5)
    prob_65 = over_prob(expected_ks, 6.5)

    pitcher_rows.append(
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

pitchers_df = pd.DataFrame(pitcher_rows)

# game projections
game_projection_rows = []
for game in games:
    away_team = game["away_team"]
    home_team = game["home_team"]
    park_key = str(game["park"]).strip().lower()
    park = get_park_factors(park_key)
    wx = weather_map.get(game["gamePk"], {})
    run_mult = safe_float(wx.get("run_mult"), 1.0)

    away_runs = clamp(4.2 * run_mult * ((park["hit_factor"] * 0.65) + (park["hr_factor"] * 0.35)), 2.0, 9.5)
    home_runs = clamp(4.2 * run_mult * ((park["hit_factor"] * 0.65) + (park["hr_factor"] * 0.35)), 2.0, 9.5)

    run_diff = home_runs - away_runs
    home_win_prob = 1 / (1 + math.exp(-(run_diff * 0.55)))
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
            "Weather": weather_bucket(safe_float(wx.get("hr_mult"), 1.0)),
            "Game Time": game.get("game_time", ""),
        }
    )

game_proj_df = pd.DataFrame(game_projection_rows)

# best picks
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
            "Why": r["Why"],
        }
    )
best_picks_df = pd.DataFrame(best_pick_rows).sort_values("Model Score", ascending=False).reset_index(drop=True)

# filters
filtered_best = best_picks_df[best_picks_df["Model Score"] >= min_model_score].copy()
filtered_batters = batters_df[batters_df["Model Score"] >= min_model_score].copy()
filtered_hr = hr_df[hr_df["HR Probability Value"] >= min_hr_prob].copy()

if min_grade != "All":
    grade_order = {"A+": 0, "A": 1, "A-": 2, "B+": 3, "B": 4, "C": 5}
    threshold = grade_order[min_grade]
    filtered_hr = filtered_hr[filtered_hr["Grade"].map(grade_order).fillna(99) <= threshold]

if search_name:
    filtered_best = filtered_best[filtered_best["Player"].astype(str).str.contains(search_name, case=False, na=False)]
    filtered_batters = filtered_batters[filtered_batters["Batter"].astype(str).str.contains(search_name, case=False, na=False)]
    filtered_hr = filtered_hr[filtered_hr["Batter"].astype(str).str.contains(search_name, case=False, na=False)]

filtered_best = filtered_best.sort_values("Model Score", ascending=False).reset_index(drop=True)
filtered_batters = filtered_batters.sort_values("Model Score", ascending=False).reset_index(drop=True)
filtered_hr = filtered_hr.sort_values(["HR Probability Value", "Batter Power"], ascending=[False, False]).reset_index(drop=True)

# hr summary
game_hr_summary = (
    hr_df.groupby(["Matchup", "Park"], as_index=False)
    .agg(
        Expected_HRs=("HR Probability Value", lambda s: round(s.sum() / 100.0, 1)),
        Top_HR_Pct=("HR Probability Value", lambda s: round(s.max(), 1)),
        Avg_HR_Pct=("HR Probability Value", lambda s: round(s.mean(), 1)),
        Players=("Batter", "count"),
    )
    .sort_values("Expected_HRs", ascending=False)
    .reset_index(drop=True)
)

weather_rows = []
for game in games:
    wx = weather_map.get(game["gamePk"], {})
    hr_mult = safe_float(wx.get("hr_mult"), 1.0)
    wind = safe_float(wx.get("wind_mph"), 0.0)
    matchup = f"{game['away_team']} @ {game['home_team']}"
    pct = round((hr_mult - 1.0) * 100, 1)
    weather_rows.append(
        {
            "Matchup": matchup,
            "Impact": weather_bucket(hr_mult),
            "Pct": pct,
            "Wind": wind,
            "WindDir": wx.get("wind_dir_16", ""),
        }
    )
weather_impact_df = pd.DataFrame(weather_rows)

# top data
top_best = filtered_best.iloc[0] if not filtered_best.empty else best_picks_df.iloc[0]
top_hr = filtered_hr.iloc[0] if not filtered_hr.empty else hr_df.iloc[0]
top_k = pitchers_df.iloc[0] if not pitchers_df.empty else None

best_total_game = game_proj_df.iloc[(game_proj_df["Away Runs"] + game_proj_df["Home Runs"]).idxmax()] if not game_proj_df.empty else None
strongest_favorite = game_proj_df.iloc[game_proj_df[["Away Win %", "Home Win %"]].max(axis=1).idxmax()] if not game_proj_df.empty else None

total_projected_hrs = round(game_hr_summary["Expected_HRs"].sum(), 1) if not game_hr_summary.empty else 0.0
game_count = len(game_hr_summary)
avg_per_game = round(total_projected_hrs / game_count, 1) if game_count else 0.0

# html table
def build_hr_html_table(df: pd.DataFrame) -> str:
    show_cols = [
        "Batter", "Batter Team", "Grade", "HR Probability", "Recent Form",
        "Pitcher", "Pitcher Team", "Batter Power", "Pitcher Vulnerability",
        "Context Score", "Power Match", "Lineup", "Order", "EV", "HR Odds"
    ]

    html = ['<div class="hr-table-wrap"><table class="hr-table"><thead><tr>']
    for col in show_cols:
        html.append(f"<th>{col}</th>")
    html.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        html.append("<tr>")
        for col in show_cols:
            val = row[col]
            if col == "Grade":
                html.append(f'<td class="{grade_class(str(val))}">{val}</td>')
            elif col == "Recent Form":
                html.append(f'<td class="{form_class(str(val))}">● {val}</td>')
            elif col in ["Batter Power", "Pitcher Vulnerability", "Context Score", "Power Match"]:
                html.append(f'<td class="{value_bg_class(float(val))}">{val}</td>')
            else:
                html.append(f"<td>{val}</td>")
        html.append("</tr>")

    html.append("</tbody></table></div>")
    return "".join(html)

# tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏠 Dashboard",
    "💣 HR Board",
    "🔥 Best Hitters",
    "🎯 Best Pitchers",
    "🏟️ Games",
    "🛠️ Debug",
])

with tab1:
    st.subheader("📊 Today at a Glance")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Top Overall Pick", top_best["Player"])
    c2.metric("Top HR Pick", top_hr["Batter"])
    c3.metric("Top HR %", top_hr["HR Probability"])
    c4.metric("Top Pitcher K Spot", top_k["Pitcher"] if top_k is not None else "—")
    c5.metric("Top Winner", strongest_favorite["Projected Winner"] if strongest_favorite is not None else "—")

    if best_total_game is not None and strongest_favorite is not None:
        g1, g2 = st.columns(2)
        g1.metric("Highest Total Game", best_total_game["Matchup"], f'{round(best_total_game["Away Runs"] + best_total_game["Home Runs"], 2)} total runs')
        g2.metric("Strongest Favorite", strongest_favorite["Projected Winner"], f'{round(max(strongest_favorite["Away Win %"], strongest_favorite["Home Win %"]), 1)}% win chance')

    st.markdown(
        f"""
        <div class="hero-card">
            <div style="font-size:20px;">🔥 🔥 🔥</div>
            <div style="font-size:28px; font-weight:800; color:#fb923c;">{total_projected_hrs} Total Projected HRs</div>
            <div style="font-size:16px; color:#d1d5db;">Across {game_count} games • {avg_per_game} avg per game</div>
            <div style="font-size:14px; color:#9ca3af; margin-top:6px;">Based on comprehensive player matchup analysis</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("💣 Expected HRs By Game")
    if not game_hr_summary.empty:
        for start in range(0, min(len(game_hr_summary), 12), 4):
            cols = st.columns(4)
            chunk = game_hr_summary.iloc[start:start + 4]
            for i, (_, row) in enumerate(chunk.iterrows()):
                expected_hr = row["Expected_HRs"]
                if expected_hr >= 2.3:
                    border_color = "#f97316"
                    txt_color = "#fb923c"
                elif expected_hr >= 2.0:
                    border_color = "#22c55e"
                    txt_color = "#4ade80"
                else:
                    border_color = "#6b7280"
                    txt_color = "#d1d5db"

                with cols[i]:
                    st.markdown(
                        f"""
                        <div class="game-card" style="border:1px solid {border_color}; border-left:5px solid {border_color};">
                            <div style="font-weight:700; color:#f8fafc; margin-bottom:8px;">⚡ {row['Matchup']}</div>
                            <div style="font-size:30px; font-weight:800; color:{txt_color};">{row['Expected_HRs']} Expected HRs</div>
                            <div style="margin-top:10px; color:#d1d5db;">Top: {row['Top_HR_Pct']}% <span style="float:right;">Avg: {row['Avg_HR_Pct']}%</span></div>
                            <div style="margin-top:12px; color:#9ca3af; font-size:14px;">{row['Players']} projected players</div>
                            <div style="margin-top:8px; color:#6b7280; font-size:13px;">{row['Park']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    st.subheader("🌤️ Weather Impact on Home Runs")
    fav = weather_impact_df[weather_impact_df["Impact"] == "Favorable"]
    bad = weather_impact_df[weather_impact_df["Impact"] == "Unfavorable"]
    neu = weather_impact_df[weather_impact_df["Impact"] == "Neutral"]

    st.markdown("### 🟢 HR Favorable Games")
    if fav.empty:
        st.write("None")
    else:
        html = "".join([f'<span class="chip-green">● {r["Matchup"]} {r["Pct"]:+.1f}% {r["Wind"]}mph {r["WindDir"]}</span>' for _, r in fav.iterrows()])
        st.markdown(html, unsafe_allow_html=True)

    st.markdown("### 🔴 HR Unfavorable Games")
    if bad.empty:
        st.write("None")
    else:
        html = "".join([f'<span class="chip-red">● {r["Matchup"]} {r["Pct"]:+.1f}% {r["Wind"]}mph {r["WindDir"]}</span>' for _, r in bad.iterrows()])
        st.markdown(html, unsafe_allow_html=True)

    st.markdown("### ⚪ Neutral Impact Games")
    if neu.empty:
        st.write("None")
    else:
        html = "".join([f'<span class="chip-neutral">● {r["Matchup"]} neutral</span>' for _, r in neu.iterrows()])
        st.markdown(html, unsafe_allow_html=True)

with tab2:
    st.subheader("💣 MLB Home Run A.I. Board")
    matchup_options = sorted(filtered_hr["Matchup"].dropna().unique().tolist())
    selected_matchup = st.selectbox("Select matchup", matchup_options) if matchup_options else None

    if selected_matchup:
        selected_game_df = filtered_hr[filtered_hr["Matchup"] == selected_matchup].copy()
        selected_game_df = selected_game_df.sort_values("HR Probability Value", ascending=False)

        game_meta = game_proj_df[game_proj_df["Matchup"] == selected_matchup]
        if not game_meta.empty:
            gm = game_meta.iloc[0]
            st.markdown(
                f"""
                <div class="detail-card">
                    <div style="font-size:20px;font-weight:800;color:#f8fafc;">{selected_matchup}</div>
                    <div style="color:#9ca3af;margin-top:6px;">Projected Winner: {gm['Projected Winner']}</div>
                    <div style="color:#9ca3af;">Projected Runs: {gm['Away Runs']} - {gm['Home Runs']}</div>
                    <div style="color:#9ca3af;">Game Time: {gm['Game Time']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        lineup_text = "Final Lineups Available - Using official MLB starting lineups" if (selected_game_df["Lineup"] == "Final").any() else "Projected lineup currently in use"
        st.markdown(f'<div class="status-bar">🟢 {lineup_text}</div>', unsafe_allow_html=True)

        st.markdown(build_hr_html_table(selected_game_df.head(20)), unsafe_allow_html=True)

        if not selected_game_df.empty:
            r = selected_game_df.iloc[0]
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### Game Weather")
                st.write(f"Condition: {r.get('Weather', 'N/A')}")
                st.write(f"Temperature: {r.get('Temp', 'N/A')}°F")
                st.write(f"Park: {r.get('Park', 'N/A')}")
            with c2:
                st.markdown("### Wind Details")
                st.write(f"Wind Speed: {r.get('Wind MPH', 'N/A')} mph")
                st.write(f"Wind Direction: {r.get('Wind Dir', 'N/A')}")
                st.write(f"Wind Impact: {r.get('Weather', 'N/A')} for home runs")

    st.markdown("---")
    st.subheader("Full HR Board")
    st.markdown(build_hr_html_table(filtered_hr.head(60)), unsafe_allow_html=True)

with tab3:
    st.subheader("🔥 Best Rated Picks For The Day")
    st.dataframe(
        filtered_best.head(25)[["Player", "Pitcher", "Park", "Best Prop", "Best Prop %", "Fair Odds", "Model Score", "Grade", "Why"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("⚾ Best Batter Hit Chances")
    st.dataframe(
        filtered_batters.sort_values("Hit %", ascending=False).head(20)[["Batter", "Pitcher", "Park", "Hit %", "Hit Fair Odds", "Model Score", "Why"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("💣 Best Home Run Chances")
    st.dataframe(
        filtered_batters.sort_values("HR %", ascending=False).head(20)[["Batter", "Pitcher", "Park", "HR %", "HR Fair Odds", "Model Score", "Why"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("🏃 Best Total Bases Chances")
    st.dataframe(
        filtered_batters.sort_values("TB %", ascending=False).head(20)[["Batter", "Pitcher", "Park", "TB %", "TB Fair Odds", "Model Score", "Why"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("💰 Best RBI Chances")
    st.dataframe(
        filtered_batters.sort_values("RBI %", ascending=False).head(20)[["Batter", "Pitcher", "Park", "RBI %", "RBI Fair Odds", "Model Score", "Why"]],
        use_container_width=True,
        hide_index=True,
    )

with tab4:
    st.subheader("🎯 Best Pitcher Strikeout Chances")
    if pitchers_df.empty:
        st.info("No pitcher K board available yet.")
    else:
        st.dataframe(pitchers_df.head(25), use_container_width=True, hide_index=True)

with tab5:
    st.subheader("🏟️ Team Run Projections & Projected Winners")
    st.dataframe(game_proj_df, use_container_width=True, hide_index=True)

    st.subheader("📅 Today's MLB Games")
    st.dataframe(schedule_df, use_container_width=True, hide_index=True)

    with st.expander("Lineup Status"):
        st.dataframe(pd.DataFrame(lineup_status_rows), use_container_width=True, hide_index=True)

with tab6:
    st.subheader("Debug")
    st.write("Batters rows:", len(batters))
    st.write("Pitchers rows:", len(pitchers))
    st.write("Parks rows:", len(parks))
    st.write("Matchup rows:", len(matchups))
    st.write("Hitter rows:", len(batters_df))
    st.write("HR rows:", len(hr_df))

    st.subheader("Aaron Judge Debug")
    judge_batters = batters[batters["_player_name"].astype(str).str.contains("Aaron Judge|Judge, Aaron|A. Judge|Judge", case=False, na=False)]
    st.write("Aaron Judge in batters.csv:")
    st.dataframe(judge_batters, use_container_width=True)

    judge_matchups = matchups[matchups["batter"].astype(str).str.contains("Aaron Judge|Judge, Aaron|A. Judge|Judge", case=False, na=False)]
    st.write("Aaron Judge in matchup rows:")
    st.dataframe(judge_matchups, use_container_width=True)

    judge_hr = hr_df[hr_df["Batter"].astype(str).str.contains("Aaron Judge|Judge, Aaron|A. Judge|Judge", case=False, na=False)]
    st.write("Aaron Judge in HR board:")
    st.dataframe(judge_hr, use_container_width=True)

    if skipped:
        st.write("Skipped:")
        for item in skipped[:50]:
            st.write(item)
