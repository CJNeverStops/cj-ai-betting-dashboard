import math
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="CJ Daily MLB AI Board", layout="wide")

st.title("🔥 CJNeverStops Daily MLB AI Board")
st.caption("Auto teams + auto lineups + probable pitchers + daily ranked picks")

with st.expander("How to Read the Model", expanded=True):
    st.markdown(
        """
### Model Score Guide
- **70+** = elite spot
- **65–69** = top play
- **55–64** = good play
- **45–54** = fringe play
- **under 45** = pass

### Grade Key
- **🔥 LOCK** = 65+
- **✅ STRONG** = 55–64
- **⚠️ LEAN** = 45–54
- **❌ PASS** = under 45

### What goes into Model Score
- **Hit %** = 40%
- **TB %** = 30%
- **RBI %** = 20%
- **HR %** = 10%

Think of it as a matchup strength score, not a guaranteed winner.
"""
    )

BATTERS_FILE = "batters.csv"
PITCHERS_FILE = "pitchers.csv"
PARKS_FILE = "parks.csv"


@st.cache_data(ttl=3600)
def try_load_csv(path: str):
    try:
        return pd.read_csv(path), None
    except Exception as e:
        return pd.DataFrame(), str(e)


def norm_text(s) -> str:
    return " ".join(str(s).strip().lower().replace(",", "").split())


def first_last_name(s) -> str:
    s = str(s).strip()
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}".strip()
    return s


def make_name_keys(s):
    raw = str(s).strip()
    return {
        norm_text(raw),
        norm_text(first_last_name(raw)),
    }


def safe_float(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def pct_to_decimal(v, default=None):
    try:
        if pd.isna(v):
            return default
        v = float(v)
        return v / 100.0 if v > 1 else v
    except Exception:
        return default


def logistic(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def find_col(df: pd.DataFrame, candidates):
    lower_map = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        cand_l = str(cand).strip().lower()
        if cand_l in lower_map:
            return lower_map[cand_l]
    for cand in candidates:
        cand_l = str(cand).strip().lower()
        for col in df.columns:
            if cand_l in str(col).strip().lower():
                return col
    return None


def require_col(df: pd.DataFrame, candidates, label: str):
    col = find_col(df, candidates)
    if col is None:
        st.error(f"Missing {label}. Found columns: {list(df.columns)}")
        st.stop()
    return col


def scale_park_factor(v, default=1.0):
    x = safe_float(v, default)
    return x / 100.0 if x > 3 else x


def grade_from_score(score: float) -> str:
    if score >= 65:
        return "🔥 LOCK"
    if score >= 55:
        return "✅ STRONG"
    if score >= 45:
        return "⚠️ LEAN"
    return "❌ PASS"


def team_abbrev_map():
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


def get_team_match_values(team_name: str):
    vals = {norm_text(team_name)}
    abbr = team_abbrev_map().get(norm_text(team_name), "")
    if abbr:
        vals.add(abbr.lower())
    return vals


def find_name_match(df: pd.DataFrame, key: str):
    return df[df["_keys"].apply(lambda s: key in s)]


def platoon_boost(batter_hand, pitcher_hand) -> float:
    bh = str(batter_hand).strip().upper()
    ph = str(pitcher_hand).strip().upper()
    if bh in ["L", "R"] and ph in ["L", "R"]:
        return 1.03 if bh != ph else 0.97
    return 1.00


def lineup_boost(spot) -> float:
    try:
        s = int(float(spot))
    except Exception:
        return 1.00
    boosts = {
        1: 1.05,
        2: 1.06,
        3: 1.08,
        4: 1.10,
        5: 1.06,
        6: 1.02,
        7: 0.98,
        8: 0.95,
        9: 0.93,
    }
    return boosts.get(s, 1.00)


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
            full_key = norm_text(name)
            rev_key = norm_text(first_last_name(name))
            player_team[full_key] = team_abbr
            player_team[rev_key] = team_abbr

    return player_team


# Load files
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

# Map columns
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

# Clean data
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

# Sidebar
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

# Schedule
games, games_err = get_today_schedule()

st.subheader("📅 Today's MLB Games")
if not games:
    st.warning(f"Could not load today's schedule. {games_err if games_err else ''}")
    st.stop()

schedule_df = pd.DataFrame(games)
st.dataframe(schedule_df, use_container_width=True)

# Build slate
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

# Model helpers
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


def calc_batter_board(batter_row, pitcher_row, park_key, batter_hand, pitcher_hand, lineup_spot, weather_boost, team_total):
    b = get_batter_metrics(batter_row)
    p = get_pitcher_metrics(pitcher_row)
    park = get_park_factors(park_key)

    platoon = platoon_boost(batter_hand, pitcher_hand)
    lineup_mult = lineup_boost(lineup_spot)
    weather_mult = safe_float(weather_boost, 1.00)
    team_total_v = safe_float(team_total, 4.2)
    team_total_mult = min(max(team_total_v / 4.2, 0.85), 1.20)

    # Per-PA hit signal
    hit_score_raw = (
        2.2 * (b["xba"] - 0.240)
        + 1.1 * (b["xwoba"] - 0.310)
        + 0.7 * (b["hardhit"] - 0.38)
        - 1.0 * (b["k_rate"] - 0.22)
        - 1.8 * (p["k_rate"] - 0.22)
        - 1.3 * (p["xba"] - 0.240)
    )
    hit_prob_pa = logistic(-1.20 + hit_score_raw) * park["hit_factor"] * platoon
    hit_prob_pa = min(max(hit_prob_pa, 0.03), 0.75)

    # Convert to game-level probability for 1+ hit
    estimated_pa = min(max(3.4 * lineup_mult, 3.2), 5.0)
    hit_prob = 1 - (1 - hit_prob_pa) ** estimated_pa
    hit_prob = min(max(hit_prob, 0.10), 0.95)

    hr_score_raw = (
        4.5 * (b["xslg"] - 0.390)
        + 2.4 * (b["barrel"] - 0.08)
        + 1.4 * (b["hardhit"] - 0.38)
        + 2.6 * (p["xslg"] - 0.390)
        + 1.5 * (p["barrel"] - 0.08)
        + 0.8 * (p["hardhit"] - 0.38)
    )
    hr_prob = logistic(-3.10 + hr_score_raw) * park["hr_factor"] * weather_mult * platoon * lineup_mult
    hr_prob = min(max(hr_prob, 0.005), 0.55)

    tb_score_raw = (
        3.0 * (b["xslg"] - 0.390)
        + 1.4 * (b["xba"] - 0.240)
        + 1.5 * (b["hardhit"] - 0.38)
        + 1.2 * (b["barrel"] - 0.08)
        + 1.5 * (p["xslg"] - 0.390)
    )
    tb_prob = logistic(-0.95 + tb_score_raw) * park["hit_factor"] * park["hr_factor"] * platoon * lineup_mult
    tb_prob = min(max(tb_prob, 0.03), 0.90)

    rbi_score_raw = (
        2.1 * (b["xwoba"] - 0.310)
        + 2.0 * (b["xslg"] - 0.390)
        + 1.2 * (b["hardhit"] - 0.38)
        + 1.0 * (p["xwoba"] - 0.310)
    )
    rbi_prob = logistic(-1.55 + rbi_score_raw) * park["hit_factor"] * platoon * lineup_mult * team_total_mult
    rbi_prob = min(max(rbi_prob, 0.02), 0.85)

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
        "lineup_mult": lineup_mult,
        "hr_factor": park["hr_factor"],
        "hit_factor": park["hit_factor"],
        "weighted_score": weighted_score,
    }


def project_pitcher_ks(pitcher_row, opp_batters):
    p = get_pitcher_metrics(pitcher_row)

    if opp_batters:
        avg_b_k = sum(x["k_rate"] for x in opp_batters) / len(opp_batters)
    else:
        avg_b_k = 0.22

    base_k_rate = (p["k_rate"] + avg_b_k) / 2
    batters_faced = 24
    expected_ks = base_k_rate * batters_faced

    return expected_ks


def prob_over_k_line(expected_ks, line):
    std_dev = 1.8
    z = (expected_ks - line) / std_dev
    return 1 / (1 + math.exp(-1.7 * z))


# Build batter board
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

    hit_fair = prob_to_fair_american(calc["hit_prob"])
    hr_fair = prob_to_fair_american(calc["hr_prob"])
    tb_fair = prob_to_fair_american(calc["tb_prob"])
    rbi_fair = prob_to_fair_american(calc["rbi_prob"])

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
            "Hit Fair Odds": hit_fair,
            "HR Fair Odds": hr_fair,
            "TB Fair Odds": tb_fair,
            "RBI Fair Odds": rbi_fair,
            "Platoon": round(calc["platoon"], 2),
            "HR Park": round(calc["hr_factor"], 2),
            "Hit Park": round(calc["hit_factor"], 2),
            "Model Score": round(calc["weighted_score"], 1),
            "Best Grade": grade_from_score(calc["weighted_score"]),
        }
    )

batters_df = pd.DataFrame(rows)

if batters_df.empty:
    st.error("No valid matchup rows were processed.")
    if skipped:
        st.write(skipped)
    st.stop()

# Best picks
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

# Pitcher K board with multiple lines
pitcher_board = []
for pitcher_name, grp in batters_df.groupby("Pitcher"):
    p_match = find_name_match(pitchers, norm_text(pitcher_name))
    if p_match.empty:
        continue

    p_row = p_match.iloc[0]

    opp_batters = []
    for _, r in grp.iterrows():
        bm = find_name_match(batters, norm_text(r["Batter"]))
        if not bm.empty:
            opp_batters.append(get_batter_metrics(bm.iloc[0]))

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
        }
    )

pitchers_df = pd.DataFrame(pitcher_board)
if not pitchers_df.empty:
    pitchers_df = pitchers_df.sort_values("Proj Ks", ascending=False).reset_index(drop=True)

top_pick = best_picks_df.iloc[0]
top_k = pitchers_df.iloc[0] if not pitchers_df.empty else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Best Overall Pick", top_pick["Player"])
c2.metric("Best Prop", top_pick["Best Prop"])
c3.metric("Top Score", f"{top_pick['Model Score']}")
c4.metric("Top Pitcher K Spot", top_k["Pitcher"] if top_k is not None else "—")

# Hitter odds checker
st.subheader("💰 Hitter Quick Odds Checker")

checker_cols = st.columns(4)
checker_player = checker_cols[0].selectbox("Player", best_picks_df["Player"].tolist())
checker_prop = checker_cols[1].selectbox("Prop", ["Hit", "Home Run", "Total Bases", "RBI"])
checker_odds_text = checker_cols[2].text_input("Book Odds", value="+150")
run_check = checker_cols[3].button("Check Hitter Edge")

player_row = batters_df[batters_df["Batter"] == checker_player].iloc[0]

prop_to_prob = {
    "Hit": player_row["Hit %"] / 100,
    "Home Run": player_row["HR %"] / 100,
    "Total Bases": player_row["TB %"] / 100,
    "RBI": player_row["RBI %"] / 100,
}
prop_to_fair = {
    "Hit": player_row["Hit Fair Odds"],
    "Home Run": player_row["HR Fair Odds"],
    "Total Bases": player_row["TB Fair Odds"],
    "RBI": player_row["RBI Fair Odds"],
}

if run_check:
    try:
        user_odds = int(checker_odds_text.strip())
        implied = implied_prob_from_american(user_odds) * 100
        model_pct = prop_to_prob[checker_prop] * 100
        edge_pct = model_pct - implied

        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric("Model %", f"{model_pct:.1f}%")
        cc2.metric("Book Implied %", f"{implied:.1f}%")
        cc3.metric("Edge %", f"{edge_pct:.1f}%")
        cc4.metric("Fair Odds", str(prop_to_fair[checker_prop]))

        st.write(f"**Verdict:** {edge_grade(edge_pct)}")
    except Exception:
        st.warning("Enter odds like +150 or -120")

# Pitcher odds checker
st.subheader("🎯 Pitcher K Odds Checker")

if not pitchers_df.empty:
    p_cols = st.columns(4)
    pitcher_name_check = p_cols[0].selectbox("Pitcher", pitchers_df["Pitcher"].tolist())
    k_line_check = p_cols[1].selectbox("K Line", ["Over 4.5", "Over 5.5", "Over 6.5"])
    pitcher_odds_text = p_cols[2].text_input("Pitcher Book Odds", value="-110")
    run_pitcher_check = p_cols[3].button("Check Pitcher Edge")

    p_row = pitchers_df[pitchers_df["Pitcher"] == pitcher_name_check].iloc[0]

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

    if run_pitcher_check:
        try:
            user_odds = int(pitcher_odds_text.strip())
            implied = implied_prob_from_american(user_odds) * 100
            model_pct = line_to_prob[k_line_check]
            edge_pct = model_pct - implied

            pc1, pc2, pc3, pc4 = st.columns(4)
            pc1.metric("Model %", f"{model_pct:.1f}%")
            pc2.metric("Book Implied %", f"{implied:.1f}%")
            pc3.metric("Edge %", f"{edge_pct:.1f}%")
            pc4.metric("Fair Odds", str(line_to_fair[k_line_check]))

            st.write(f"**Verdict:** {edge_grade(edge_pct)}")
        except Exception:
            st.warning("Enter odds like +150 or -120")

# Main boards
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
    st.dataframe(pitchers_df.head(15), use_container_width=True)

st.subheader("⚾ Best Batter Hit Chances")
st.dataframe(
    batters_df.sort_values("Hit %", ascending=False).head(15),
    use_container_width=True,
)

st.subheader("💣 Best Home Run Chances")
st.dataframe(
    batters_df.sort_values("HR %", ascending=False).head(15),
    use_container_width=True,
)

st.subheader("🏃 Best Total Bases Chances")
st.dataframe(
    batters_df.sort_values("TB %", ascending=False).head(15),
    use_container_width=True,
)

st.subheader("💰 Best RBI Chances")
st.dataframe(
    batters_df.sort_values("RBI %", ascending=False).head(15),
    use_container_width=True,
)

st.subheader("🧠 Why These Picks (Top 5 Breakdown)")
top5 = best_picks_df.head(5)

for _, r in top5.iterrows():
    batter_row = batters[batters["_keys"].apply(lambda s: norm_text(r["Player"]) in s)].iloc[0]
    pitcher_row = pitchers[pitchers["_keys"].apply(lambda s: norm_text(r["Pitcher"]) in s)].iloc[0]

    b = get_batter_metrics(batter_row)
    p = get_pitcher_metrics(pitcher_row)

    st.markdown(f"### 🔥 {r['Player']} ({r['Best Prop']})")
    st.write(f"""
**Matchup:** vs {r['Pitcher']}  
**Park:** {r['Park']}

**Why the model likes this:**
- Batter xBA: {round(b['xba'], 3)}
- Batter xSLG: {round(b['xslg'], 3)}
- Barrel Rate: {round(b['barrel'] * 100, 1)}%
- Hard Hit %: {round(b['hardhit'] * 100, 1)}%

- Pitcher xBA allowed: {round(p['xba'], 3)}
- Pitcher xSLG allowed: {round(p['xslg'], 3)}
- Pitcher K%: {round(p['k_rate'] * 100, 1)}%

**Best Prop %:** {r['Best Prop %']}  
**Fair Odds:** {r['Fair Odds']}  
**Model Score:** {r['Model Score']}  
**Grade:** {r['Grade']}
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
