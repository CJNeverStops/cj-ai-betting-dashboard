import math
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
import requests
import streamlit as st

# =========================================================
# APP CONFIG
# =========================================================
st.set_page_config(
    page_title="CJ HR AI Board",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main {
        background-color: #0b1220;
        color: white;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }
    h1,h2,h3,h4 {
        color: #f8fafc;
    }
    .metric-card {
        background: linear-gradient(145deg, #111827, #0f172a);
        padding: 18px;
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 8px 24px rgba(0,0,0,0.25);
        margin-bottom: 12px;
        min-height: 170px;
    }
    .pill {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 700;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .pill-red { background: rgba(239,68,68,.18); color: #fecaca; }
    .pill-green { background: rgba(34,197,94,.18); color: #bbf7d0; }
    .pill-yellow { background: rgba(234,179,8,.18); color: #fde68a; }
    .pill-blue { background: rgba(59,130,246,.18); color: #bfdbfe; }
    .pill-purple { background: rgba(168,85,247,.18); color: #e9d5ff; }

    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        overflow: hidden;
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #111827, #0f172a);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 10px;
        border-radius: 16px;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("💣 CJNeverStops MLB Home Run A.I. Board")
st.caption("HR-focused board with batter power, pitcher vulnerability, context score, power match, weather, and app-style UI")

BATTERS_FILE = "batters.csv"
PITCHERS_FILE = "pitchers.csv"
PARKS_FILE = "parks.csv"

# =========================================================
# HELPERS
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


def make_name_keys(value) -> Set[str]:
    raw = str(value).strip()
    return {norm_text(raw), norm_text(first_last_name(raw))}


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


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def logistic(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def scale01(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.5
    return clamp((value - low) / (high - low), 0.0, 1.0)


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


def prob_to_fair_american(prob: float):
    if prob <= 0 or prob >= 1:
        return None
    if prob >= 0.5:
        return int(round(-(prob / (1 - prob)) * 100))
    return int(round(((1 - prob) / prob) * 100))


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


def render_grade_pill(grade: str):
    if grade == "A+":
        return '<span class="pill pill-green">A+</span>'
    if grade == "A":
        return '<span class="pill pill-green">A</span>'
    if grade == "A-":
        return '<span class="pill pill-green">A-</span>'
    if grade == "B+":
        return '<span class="pill pill-yellow">B+</span>'
    if grade == "B":
        return '<span class="pill pill-yellow">B</span>'
    if grade == "C":
        return '<span class="pill pill-blue">C</span>'
    return '<span class="pill pill-purple">N/A</span>'


def render_form_pill(label: str):
    if "Hot" in label:
        return '<span class="pill pill-green">🔥 Hot</span>'
    if "Good" in label:
        return '<span class="pill pill-blue">🟢 Good</span>'
    if "Average" in label:
        return '<span class="pill pill-yellow">🟡 Average</span>'
    return '<span class="pill pill-red">🔴 Slump</span>'


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
# MLB API
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

    valid_teams = team_abbrev_map()
    games = []
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
# LOAD DATA
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
# MAP COLUMNS
# =========================================================
b_name = require_col(batters, ["player_name", "name", "player", "last_name, first_name"], "batter name")
b_xba = find_col(batters, ["xba", "est_ba"])
b_xslg = find_col(batters, ["xslg", "est_slg"])
b_xwoba = find_col(batters, ["xwoba", "est_woba"])
b_barrel = find_col(batters, ["brl_percent", "barrel_batted_rate", "barrel_pct", "barrel"])
b_hardhit = find_col(batters, ["hard_hit_percent", "hard_hit_pct", "hardhit"])
b_k = find_col(batters, ["k_percent", "strikeout_percent", "k%"])
b_fb = find_col(batters, ["fb_percent", "fly_ball_percent", "flyball", "fly_ball"])
b_pa = find_col(batters, ["pa", "plate_appearances"])

p_name = require_col(pitchers, ["player_name", "name", "player", "last_name, first_name"], "pitcher name")
p_xba = find_col(pitchers, ["xba", "est_ba"])
p_xslg = find_col(pitchers, ["xslg", "est_slg"])
p_xwoba = find_col(pitchers, ["xwoba", "est_woba"])
p_barrel = find_col(pitchers, ["brl_percent", "barrel_batted_rate", "barrel_pct", "barrel"])
p_hardhit = find_col(pitchers, ["hard_hit_percent", "hard_hit_pct", "hardhit"])
p_k = find_col(pitchers, ["k_percent", "strikeout_percent", "k%"])
p_hr9 = find_col(pitchers, ["hr_per_9", "hr9", "hr/9"])

park_name_col = require_col(parks, ["park_name", "venue_name", "park", "venue"], "park name")
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
    return roster_map.get(norm_text(raw), roster_map.get(norm_text(first_last_name(raw)), ""))

batters["_team_auto"] = batters[b_name].astype(str).apply(find_team)
batters["_team_norm"] = batters["_team_auto"].map(norm_text)

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.title("💣 CJ HR Board")
    st.caption("Home run leaderboard")

    show_unconfirmed = st.toggle("Show fallback hitters when lineups aren't posted", value=True)

    team_col_pick = st.selectbox(
        "Batter team column",
        options=["_team_auto"] + [c for c in batters.columns if c != "_team_auto"],
        index=0,
    )

    min_hr_prob = st.slider("Minimum HR %", 0.0, 40.0, 10.0, 0.5)
    min_grade = st.selectbox("Minimum Grade", ["All", "A+", "A", "A-", "B+", "B", "C"])
    search_name = st.text_input("Search Batter")

if team_col_pick == "_team_auto":
    batters["_team_norm"] = batters["_team_auto"].map(norm_text)
else:
    batters["_team_norm"] = batters[team_col_pick].astype(str).map(norm_text)

# =========================================================
# SCHEDULE + WEATHER
# =========================================================
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

# =========================================================
# BUILD MATCHUPS
# =========================================================
auto_rows = []
lineup_status_rows = []

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
                        "lineup_spot": hitter.get("lineup_spot", None),
                        "lineup_source": "RotoWire",
                        "game_status": "🟢 Scheduled",
                        **common_weather,
                    }
                )
        elif show_unconfirmed:
            away_vals = get_team_match_values(away_team)
            away_hitters = batters[batters["_team_norm"].isin(away_vals)]
            for _, b_row in away_hitters.iterrows():
                auto_rows.append(
                    {
                        "batter": b_row[b_name],
                        "pitcher": home_pitcher,
                        "park": park,
                        "team": away_team,
                        "pitcher_team": home_team,
                        "batter_hand": "",
                        "lineup_spot": None,
                        "lineup_source": "Team Fallback",
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
                        "lineup_spot": hitter.get("lineup_spot", None),
                        "lineup_source": "RotoWire",
                        "game_status": "🟢 Scheduled",
                        **common_weather,
                    }
                )
        elif show_unconfirmed:
            home_vals = get_team_match_values(home_team)
            home_hitters = batters[batters["_team_norm"].isin(home_vals)]
            for _, b_row in home_hitters.iterrows():
                auto_rows.append(
                    {
                        "batter": b_row[b_name],
                        "pitcher": away_pitcher,
                        "park": park,
                        "team": home_team,
                        "pitcher_team": away_team,
                        "batter_hand": "",
                        "lineup_spot": None,
                        "lineup_source": "Team Fallback",
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

# =========================================================
# METRIC EXTRACTORS
# =========================================================
def get_batter_metrics(row):
    pa_val = safe_float(row[b_pa], 250.0) if b_pa else 250.0
    recent_proxy = clamp(pa_val / 650.0, 0.20, 1.00)

    xslg = safe_float(row[b_xslg], 0.390) if b_xslg else 0.390
    barrel = pct_to_decimal(row[b_barrel], 0.08) if b_barrel else 0.08
    hardhit = pct_to_decimal(row[b_hardhit], 0.38) if b_hardhit else 0.38
    fb = pct_to_decimal(row[b_fb], 0.35) if b_fb else 0.35
    xba = safe_float(row[b_xba], 0.240) if b_xba else 0.240
    xwoba = safe_float(row[b_xwoba], 0.310) if b_xwoba else 0.310
    k_rate = pct_to_decimal(row[b_k], 0.22) if b_k else 0.22

    recent_form_score = clamp(
        (
            0.40 * scale01(xslg, 0.300, 0.750)
            + 0.30 * scale01(barrel, 0.02, 0.25)
            + 0.20 * scale01(hardhit, 0.20, 0.65)
            + 0.10 * recent_proxy
        ),
        0.0,
        1.0,
    )

    return {
        "xba": xba,
        "xslg": xslg,
        "xwoba": xwoba,
        "barrel": barrel,
        "hardhit": hardhit,
        "fb": fb,
        "k_rate": k_rate,
        "recent_form_score": recent_form_score,
    }


def get_pitcher_metrics(row):
    return {
        "xba": safe_float(row[p_xba], 0.240) if p_xba else 0.240,
        "xslg": safe_float(row[p_xslg], 0.390) if p_xslg else 0.390,
        "xwoba": safe_float(row[p_xwoba], 0.310) if p_xwoba else 0.310,
        "barrel": pct_to_decimal(row[p_barrel], 0.08) if p_barrel else 0.08,
        "hardhit": pct_to_decimal(row[p_hardhit], 0.38) if p_hardhit else 0.38,
        "k_rate": pct_to_decimal(row[p_k], 0.22) if p_k else 0.22,
        "hr9": safe_float(row[p_hr9], 1.05) if p_hr9 else 1.05,
    }


def get_park_factors(park_key):
    row = parks.loc[parks["_park"] == park_key]
    if row.empty:
        return {"hr_factor": 1.00, "hit_factor": 1.00}
    row = row.iloc[0]
    return {
        "hr_factor": safe_float(row[park_hr_col], 1.00) / 100.0 if park_hr_col and safe_float(row[park_hr_col], 1.0) > 3 else safe_float(row[park_hr_col], 1.0) if park_hr_col else 1.0,
        "hit_factor": safe_float(row[park_hit_col], 1.00) / 100.0 if park_hit_col and safe_float(row[park_hit_col], 1.0) > 3 else safe_float(row[park_hit_col], 1.0) if park_hit_col else 1.0,
    }


# =========================================================
# HR MODEL COMPONENTS
# =========================================================
def recent_form_label(score: float) -> str:
    if score >= 0.75:
        return "Hot"
    if score >= 0.55:
        return "Good"
    if score >= 0.40:
        return "Average"
    return "Slump"


def hr_grade(prob: float) -> str:
    if prob >= 0.22:
        return "A+"
    if prob >= 0.20:
        return "A"
    if prob >= 0.18:
        return "A-"
    if prob >= 0.16:
        return "B+"
    if prob >= 0.14:
        return "B"
    return "C"


def flame_match(value: float) -> str:
    if value >= 0.82:
        return "🔥🔥🔥"
    if value >= 0.68:
        return "🔥🔥"
    if value >= 0.54:
        return "🔥"
    return "—"


def calc_hr_model(batter_row, pitcher_row, matchup_row):
    b = get_batter_metrics(batter_row)
    p = get_pitcher_metrics(pitcher_row)
    park = get_park_factors(matchup_row["_park"])

    lineup_spot = matchup_row.get("lineup_spot", None)
    lineup_value = estimate_plate_appearances(lineup_spot)
    platoon_mult = platoon_boost(matchup_row.get("batter_hand", ""), "")
    hr_weather_mult = safe_float(matchup_row.get("hr_weather_mult", 1.0), 1.0)

    batter_power = (
        0.35 * scale01(b["xslg"], 0.300, 0.750) +
        0.30 * scale01(b["barrel"], 0.02, 0.25) +
        0.20 * scale01(b["hardhit"], 0.20, 0.65) +
        0.15 * b["recent_form_score"]
    )
    batter_power = clamp(batter_power, 0.0, 1.0)

    pitcher_vulnerability = (
        0.35 * scale01(p["xslg"], 0.300, 0.650) +
        0.25 * scale01(p["barrel"], 0.02, 0.18) +
        0.20 * scale01(p["hardhit"], 0.20, 0.60) +
        0.20 * scale01(p["hr9"], 0.3, 2.2)
    )
    pitcher_vulnerability = clamp(pitcher_vulnerability, 0.0, 1.0)

    context_score = (
        0.30 * scale01(park["hr_factor"], 0.80, 1.25) +
        0.30 * scale01(hr_weather_mult, 0.85, 1.20) +
        0.20 * scale01(platoon_mult, 0.95, 1.05) +
        0.20 * scale01(lineup_value, 3.8, 4.9)
    )
    context_score = clamp(context_score, 0.0, 1.0)

    power_match = clamp((0.55 * batter_power) + (0.45 * pitcher_vulnerability), 0.0, 1.0)

    raw_hr_score = (
        0.38 * batter_power +
        0.27 * pitcher_vulnerability +
        0.20 * context_score +
        0.15 * power_match
    )

    hr_probability = 0.08 + (raw_hr_score * 0.18)
    hr_probability = clamp(hr_probability, 0.02, 0.30)

    return {
        "batter_power": batter_power,
        "pitcher_vulnerability": pitcher_vulnerability,
        "context_score": context_score,
        "power_match": power_match,
        "hr_probability": hr_probability,
        "recent_form_score": b["recent_form_score"],
        "recent_form_label": recent_form_label(b["recent_form_score"]),
        "grade": hr_grade(hr_probability),
        "fair_odds": prob_to_fair_american(hr_probability),
        "weather_note": weather_reason_label(1.0, hr_weather_mult, safe_float(matchup_row.get("wind_out_score"), 0.0), safe_float(matchup_row.get("wind_in_score"), 0.0)),
    }


def weather_reason_label(hit_wx: float, hr_wx: float, wind_out: float, wind_in: float):
    if hr_wx >= 1.08 or wind_out >= 0.60:
        return "Great hitting weather"
    if hr_wx <= 0.94 or wind_in >= 0.60:
        return "Tough hitting weather"
    if hr_wx >= 1.03:
        return "Helpful weather"
    return "Neutral weather"


# =========================================================
# BUILD HR BOARD
# =========================================================
hr_rows = []
skipped = []

for _, mrow in matchups.iterrows():
    batter_match = find_name_match(batters, mrow["_batter"])
    pitcher_match = find_name_match(pitchers, mrow["_pitcher"])

    if batter_match.empty:
        skipped.append(f"Batter not found: {mrow['batter']}")
        continue
    if pitcher_match.empty:
        skipped.append(f"Pitcher not found: {mrow['pitcher']}")
        continue

    batter_row = batter_match.iloc[0]
    pitcher_row = pitcher_match.iloc[0]

    calc = calc_hr_model(batter_row, pitcher_row, mrow)

    prob = calc["hr_probability"]
    fair = calc["fair_odds"]
    fair_str = f"{fair:+d}" if fair is not None else "N/A"

    hr_rows.append(
        {
            "Batter": mrow["batter"],
            "Batter Team": find_team(mrow["batter"]) or mrow.get("team", ""),
            "Grade": calc["grade"],
            "HR Probability Value": round(prob * 100, 1),
            "HR Probability": f'{prob * 100:.1f}% ({fair_str})',
            "Recent Form": calc["recent_form_label"],
            "Pitcher": mrow["pitcher"],
            "Pitcher Team": mrow.get("pitcher_team", ""),
            "Batter Power": round(calc["batter_power"], 2),
            "Pitcher Vulnerability": round(calc["pitcher_vulnerability"], 2),
            "Context Score": round(calc["context_score"], 2),
            "Power Match": round(calc["power_match"], 2),
            "Power Match Flames": flame_match(calc["power_match"]),
            "Game Status": mrow.get("game_status", "🟢 Scheduled"),
            "Lineup": mrow.get("lineup_source", "RotoWire"),
            "Order": int(mrow["lineup_spot"]) if pd.notna(mrow.get("lineup_spot")) else "—",
            "EV": "N/A",
            "HR Odds": "N/A",
            "Fair Odds": fair,
            "Park": mrow["park"],
            "Weather": calc["weather_note"],
            "Temp": round(safe_float(mrow.get("temp_f"), 70), 1),
            "Wind MPH": round(safe_float(mrow.get("wind_mph"), 8), 1),
            "Wind Dir": mrow.get("wind_dir_16", ""),
            "Why": f'{calc["weather_note"]} | Power {calc["batter_power"]:.2f} | Vuln {calc["pitcher_vulnerability"]:.2f} | Ctx {calc["context_score"]:.2f}',
        }
    )

hr_df = pd.DataFrame(hr_rows)
if hr_df.empty:
    st.error("No HR rows were built.")
    if skipped:
        st.write(skipped)
    st.stop()

# =========================================================
# FILTERS
# =========================================================
filtered_hr = hr_df.copy()
filtered_hr = filtered_hr[filtered_hr["HR Probability Value"] >= min_hr_prob]

if min_grade != "All":
    grade_order = {"A+": 0, "A": 1, "A-": 2, "B+": 3, "B": 4, "C": 5}
    threshold = grade_order[min_grade]
    filtered_hr = filtered_hr[filtered_hr["Grade"].map(grade_order).fillna(99) <= threshold]

if search_name:
    filtered_hr = filtered_hr[
        filtered_hr["Batter"].astype(str).str.contains(search_name, case=False, na=False)
    ]

filtered_hr = filtered_hr.sort_values(["HR Probability Value", "Batter Power"], ascending=[False, False]).reset_index(drop=True)

# =========================================================
# TOP DATA
# =========================================================
top_pick = filtered_hr.iloc[0] if not filtered_hr.empty else hr_df.iloc[0]
best_total_game = None
games_view = pd.DataFrame()
if games:
    game_projection_rows = []
    for game in games:
        wx = weather_map.get(game["gamePk"], {})
        game_projection_rows.append(
            {
                "Matchup": f'{game["away_team"]} @ {game["home_team"]}',
                "Park": game["park"],
                "Weather": weather_reason_label(1.0, safe_float(wx.get("hr_mult"), 1.0), safe_float(wx.get("wind_out_score"), 0.0), safe_float(wx.get("wind_in_score"), 0.0)),
                "Temp": round(safe_float(wx.get("temp_f"), 70), 1),
                "Wind": f'{round(safe_float(wx.get("wind_mph"), 8),1)} {wx.get("wind_dir_16","")}',
                "HR Weather Mult": round(safe_float(wx.get("hr_mult"), 1.0), 3),
            }
        )
    games_view = pd.DataFrame(game_projection_rows)

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🏠 Dashboard",
    "💣 HR Board",
    "🏟️ Games",
    "🛠️ Debug",
])

with tab1:
    st.subheader("📊 Today at a Glance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Top HR Pick", top_pick["Batter"])
    c2.metric("Top HR %", top_pick["HR Probability"])
    c3.metric("Top Grade", top_pick["Grade"])
    c4.metric("Best Match", top_pick["Pitcher"])

    st.subheader("🔥 Top HR Plays")
    cards = filtered_hr.head(3)
    cols = st.columns(3)
    for i, (_, row) in enumerate(cards.iterrows()):
        with cols[i]:
            st.markdown(
                f"""
                <div class="metric-card">
                    <h3>{row['Batter']}</h3>
                    {render_grade_pill(row['Grade'])}
                    {render_form_pill(row['Recent Form'])}
                    <p><strong>HR Probability:</strong> {row['HR Probability']}</p>
                    <p><strong>Pitcher:</strong> {row['Pitcher']}</p>
                    <p><strong>Batter Power:</strong> {row['Batter Power']}</p>
                    <p><strong>Pitcher Vulnerability:</strong> {row['Pitcher Vulnerability']}</p>
                    <p><strong>Context Score:</strong> {row['Context Score']}</p>
                    <p><strong>Power Match:</strong> {row['Power Match Flames']}</p>
                    <p><strong>Why:</strong> {row['Why']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.subheader("🧠 Why The Model Likes These")
    for _, row in filtered_hr.head(5).iterrows():
        st.markdown(f"### {row['Batter']} vs {row['Pitcher']}")
        st.write(
            f"""
**HR Probability:** {row['HR Probability']}  
**Grade:** {row['Grade']}  
**Recent Form:** {row['Recent Form']}  
**Batter Power:** {row['Batter Power']}  
**Pitcher Vulnerability:** {row['Pitcher Vulnerability']}  
**Context Score:** {row['Context Score']}  
**Power Match:** {row['Power Match Flames']} ({row['Power Match']})  
**Weather:** {row['Weather']}  
**Temp/Wind:** {row['Temp']}°F, {row['Wind MPH']} mph {row['Wind Dir']}  
**Park:** {row['Park']}  
"""
        )
        st.divider()

with tab2:
    st.subheader("💣 MLB Home Run A.I. Board")
    board = filtered_hr.copy()
    st.dataframe(
        board[
            [
                "Batter", "Batter Team", "Grade", "HR Probability", "Recent Form",
                "Pitcher", "Pitcher Team", "Batter Power", "Pitcher Vulnerability",
                "Context Score", "Power Match Flames", "Game Status", "Lineup",
                "Order", "EV", "HR Odds"
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

with tab3:
    st.subheader("🏟️ Today’s Games + HR Context")
    if not games_view.empty:
        st.dataframe(games_view, use_container_width=True, hide_index=True)
    st.subheader("📅 Schedule")
    st.dataframe(schedule_df, use_container_width=True, hide_index=True)
    with st.expander("Lineup Status"):
        st.dataframe(pd.DataFrame(lineup_status_rows), use_container_width=True, hide_index=True)

with tab4:
    st.write("Batters columns:", list(batters.columns))
    st.write("Pitchers columns:", list(pitchers.columns))
    st.write("Parks columns:", list(parks.columns))
    st.write("Chosen team column:", team_col_pick)
    st.write("Batters rows:", len(batters))
    st.write("Pitchers rows:", len(pitchers))
    st.write("Parks rows:", len(parks))
    st.write("Matchup rows:", len(matchups))
    st.write("HR rows:", len(hr_df))
    if skipped:
        st.write("Skipped:")
        for item in skipped:
            st.write(item)
          
