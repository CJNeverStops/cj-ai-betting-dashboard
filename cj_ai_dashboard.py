import math
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="CJ Daily MLB AI Board", layout="wide")

st.title("🔥 CJNeverStops Daily MLB AI Board")
st.caption("Daily starters board: K chances, hit chances, HR chances, total bases, RBI, and best rated picks")

BATTERS_FILE = "batters.csv"
PITCHERS_FILE = "pitchers.csv"
PARKS_FILE = "parks.csv"
MATCHUPS_FILE = "today_matchups.csv"


@st.cache_data(ttl=3600)
def try_load(path):
    try:
        return pd.read_csv(path), None
    except Exception as e:
        return pd.DataFrame(), str(e)


@st.cache_data(ttl=1800)
def get_today_schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher"
    try:
        res = requests.get(url, timeout=20)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        return pd.DataFrame(), str(e)

    games = []
    for date in data.get("dates", []):
        for g in date.get("games", []):
            try:
                home = g["teams"]["home"]["team"]["name"]
                away = g["teams"]["away"]["team"]["name"]
                home_pitcher = g["teams"]["home"].get("probablePitcher", {}).get("fullName", "")
                away_pitcher = g["teams"]["away"].get("probablePitcher", {}).get("fullName", "")
                venue = g["venue"]["name"]

                games.append(
                    {
                        "away_team": away,
                        "home_team": home,
                        "away_pitcher": away_pitcher,
                        "home_pitcher": home_pitcher,
                        "park": venue,
                    }
                )
            except Exception:
                pass

    return pd.DataFrame(games), None


batters, batters_err = try_load(BATTERS_FILE)
pitchers, pitchers_err = try_load(PITCHERS_FILE)
parks, parks_err = try_load(PARKS_FILE)
manual_matchups, matchups_err = try_load(MATCHUPS_FILE)
schedule_df, schedule_err = get_today_schedule()

if batters.empty:
    st.error(f"Could not load batters.csv: {batters_err}")
    st.stop()

if pitchers.empty:
    st.error(f"Could not load pitchers.csv: {pitchers_err}")
    st.stop()

if parks.empty:
    st.error(f"Could not load parks.csv: {parks_err}")
    st.stop()


def norm_text(s):
    return " ".join(str(s).strip().lower().replace(",", "").split())


def first_last_name(s):
    s = str(s).strip()
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}".strip()
    return s


def make_name_keys(s):
    raw = str(s).strip()
    return {norm_text(raw), norm_text(first_last_name(raw))}


def logistic(x):
    return 1 / (1 + math.exp(-x))


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


def implied_prob(odds):
    odds = int(odds)
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)


def find_col(df, candidates):
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


def require_col(df, candidates, label):
    col = find_col(df, candidates)
    if col is None:
        st.error(f"Missing {label}. Found columns: {list(df.columns)}")
        st.stop()
    return col


def scale_park_factor(v, default=1.0):
    x = safe_float(v, default)
    return x / 100.0 if x > 3 else x


def grade_from_score(score):
    if score >= 80:
        return "🔥 LOCK"
    if score >= 70:
        return "✅ STRONG"
    if score >= 60:
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


def get_team_match_values(team_name):
    team_name_norm = norm_text(team_name)
    abbr = team_abbrev_map().get(team_name_norm, "")
    vals = {team_name_norm}
    if abbr:
        vals.add(abbr.lower())
    return vals


def find_name_match(df, key):
    return df[df["_keys"].apply(lambda s: key in s)]


def platoon_boost(batter_hand, pitcher_hand):
    bh = str(batter_hand).strip().upper()
    ph = str(pitcher_hand).strip().upper()
    if bh in ["L", "R"] and ph in ["L", "R"]:
        return 1.03 if bh != ph else 0.97
    return 1.00


def lineup_boost(spot):
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


b_name = require_col(batters, ["player_name", "name", "player", "last_name, first_name"], "batter name column")

# team column candidates, plus manual picker fallback
auto_team_col = find_col(batters, ["team", "team_name", "tm", "club", "team_abbr", "teamabbr"])

b_xba = find_col(batters, ["xba", "estimated_ba"])
b_xslg = find_col(batters, ["xslg", "estimated_slg"])
b_xwoba = find_col(batters, ["xwoba", "estimated_woba_using_speedangle"])
b_barrel = find_col(batters, ["brl_percent", "barrel_batted_rate", "barrel_pct", "barrel"])
b_hardhit = find_col(batters, ["hard_hit_percent", "hard_hit_pct", "hardhit"])
b_k = find_col(batters, ["k_percent", "strikeout_percent", "k%"])
b_bb = find_col(batters, ["bb_percent", "walk_percent", "bb%"])

p_name = require_col(pitchers, ["player_name", "name", "player", "last_name, first_name"], "pitcher name column")
p_xba = find_col(pitchers, ["xba", "estimated_ba"])
p_xslg = find_col(pitchers, ["xslg", "estimated_slg"])
p_xwoba = find_col(pitchers, ["xwoba", "estimated_woba_using_speedangle"])
p_barrel = find_col(pitchers, ["brl_percent", "barrel_batted_rate", "barrel_pct", "barrel"])
p_hardhit = find_col(pitchers, ["hard_hit_percent", "hard_hit_pct", "hardhit"])
p_k = find_col(pitchers, ["k_percent", "strikeout_percent", "k%"])
p_bb = find_col(pitchers, ["bb_percent", "walk_percent", "bb%"])

park_name_col = require_col(parks, ["park_name", "venue_name", "park", "venue"], "park name column")
park_hr_col = find_col(parks, ["hr_factor", "hr", "home_run", "home_runs"])
park_hit_col = find_col(parks, ["hit_factor", "hit", "hits", "1b"])

batters = batters.copy()
pitchers = pitchers.copy()
parks = parks.copy()

batters["_keys"] = batters[b_name].astype(str).apply(make_name_keys)
pitchers["_keys"] = pitchers[p_name].astype(str).apply(make_name_keys)
parks["_park"] = parks[park_name_col].astype(str).str.strip().str.lower()

with st.sidebar:
    st.header("Board Mode")
    auto_mode = st.toggle("Auto Build Slate From MLB Schedule", value=not schedule_df.empty)
    default_lineup_spot = st.slider("Default lineup spot (auto mode)", 1, 9, 5)
    default_team_total = st.slider("Default team total (auto mode)", 3.0, 6.5, 4.2, 0.1)
    default_weather_boost = st.slider("Default weather boost (auto mode)", 0.90, 1.15, 1.00, 0.01)

    st.header("Team Column")
    batter_team_col = st.selectbox(
        "Choose batter team column",
        options=["(none)"] + list(batters.columns),
        index=(["(none)"] + list(batters.columns)).index(auto_team_col) if auto_team_col in batters.columns else 0,
    )

st.subheader("📅 Today's MLB Games")
if schedule_df.empty:
    st.warning(f"Could not auto-load today's schedule. {schedule_err if schedule_err else ''}")
else:
    st.dataframe(schedule_df, use_container_width=True)

if batter_team_col != "(none)":
    batters["_team_norm"] = batters[batter_team_col].astype(str).map(norm_text)
else:
    batters["_team_norm"] = ""

if auto_mode and schedule_df.empty:
    auto_mode = False

if auto_mode:
    auto_rows = []

    if batter_team_col == "(none)":
        st.warning("Pick the correct team column in the sidebar so auto mode can match hitters to teams. Falling back to manual matchup file.")
        matchups = manual_matchups.copy()
    else:
        for _, game in schedule_df.iterrows():
            away_team = game["away_team"]
            home_team = game["home_team"]
            away_pitcher = game["away_pitcher"]
            home_pitcher = game["home_pitcher"]
            park = game["park"]

            away_team_vals = get_team_match_values(away_team)
            home_team_vals = get_team_match_values(home_team)

            away_hitters = batters[batters["_team_norm"].isin(away_team_vals)]
            home_hitters = batters[batters["_team_norm"].isin(home_team_vals)]

            if home_pitcher:
                for _, batter_row in away_hitters.iterrows():
                    auto_rows.append(
                        {
                            "batter": batter_row[b_name],
                            "pitcher": home_pitcher,
                            "park": park,
                            "batter_hand": "",
                            "pitcher_hand": "",
                            "lineup_spot": default_lineup_spot,
                            "team": away_team,
                            "opp_team": home_team,
                            "weather_boost": default_weather_boost,
                            "team_total": default_team_total,
                        }
                    )

            if away_pitcher:
                for _, batter_row in home_hitters.iterrows():
                    auto_rows.append(
                        {
                            "batter": batter_row[b_name],
                            "pitcher": away_pitcher,
                            "park": park,
                            "batter_hand": "",
                            "pitcher_hand": "",
                            "lineup_spot": default_lineup_spot,
                            "team": home_team,
                            "opp_team": away_team,
                            "weather_boost": default_weather_boost,
                            "team_total": default_team_total,
                        }
                    )

        matchups = pd.DataFrame(auto_rows)

        if matchups.empty and not manual_matchups.empty:
            st.warning("Auto mode built zero matchup rows. Using today_matchups.csv instead.")
            matchups = manual_matchups.copy()
else:
    matchups = manual_matchups.copy()

if matchups.empty:
    st.error("No matchup rows available. Use auto mode with a valid team column, or upload today_matchups.csv.")
    st.stop()

m_batter = require_col(matchups, ["batter", "hitter", "player"], "matchups batter column")
m_pitcher = require_col(matchups, ["pitcher"], "matchups pitcher column")
m_park = require_col(matchups, ["park", "venue", "park_name"], "matchups park column")
m_bhand = find_col(matchups, ["batter_hand", "stand", "bats"])
m_phand = find_col(matchups, ["pitcher_hand", "p_throws", "throws"])
m_lineup = find_col(matchups, ["lineup_spot", "batting_order", "order", "spot"])
m_team = find_col(matchups, ["team"])
m_opp = find_col(matchups, ["opp_team", "opponent", "opp"])
m_weather = find_col(matchups, ["weather_boost", "weather"])
m_team_total = find_col(matchups, ["team_total", "implied_total", "runs_total"])
m_hit_odds = find_col(matchups, ["hit_odds", "hits_odds"])
m_hr_odds = find_col(matchups, ["hr_odds", "home_run_odds"])
m_tb_odds = find_col(matchups, ["tb_odds", "total_bases_odds"])
m_rbi_odds = find_col(matchups, ["rbi_odds"])

matchups = matchups.copy()
matchups["_batter"] = matchups[m_batter].astype(str).map(norm_text)
matchups["_pitcher"] = matchups[m_pitcher].astype(str).map(norm_text)
matchups["_park"] = matchups[m_park].astype(str).str.strip().str.lower()

with st.expander("CSV / Slate Debug Info"):
    st.write("Batters columns:", list(batters.columns))
    st.write("Pitchers columns:", list(pitchers.columns))
    st.write("Parks columns:", list(parks.columns))
    st.write("Matchups columns:", list(matchups.columns))
    st.write("Chosen batter team column:", batter_team_col)
    st.write("Batters rows:", len(batters))
    st.write("Pitchers rows:", len(pitchers))
    st.write("Parks rows:", len(parks))
    st.write("Matchups rows:", len(matchups))

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

    hit_score = (
        2.2 * (b["xba"] - 0.240)
        + 1.1 * (b["xwoba"] - 0.310)
        + 0.7 * (b["hardhit"] - 0.38)
        - 1.0 * (b["k_rate"] - 0.22)
        - 1.8 * (p["k_rate"] - 0.22)
        - 1.3 * (p["xba"] - 0.240)
    )
    hit_prob = logistic(-1.20 + hit_score) * park["hit_factor"] * platoon * lineup_mult
    hit_prob = min(max(hit_prob, 0.03), 0.92)

    hr_score = (
        4.5 * (b["xslg"] - 0.390)
        + 2.4 * (b["barrel"] - 0.08)
        + 1.4 * (b["hardhit"] - 0.38)
        + 2.6 * (p["xslg"] - 0.390)
        + 1.5 * (p["barrel"] - 0.08)
        + 0.8 * (p["hardhit"] - 0.38)
    )
    hr_prob = logistic(-3.10 + hr_score) * park["hr_factor"] * weather_mult * platoon * lineup_mult
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

    return {
        "hit_prob": hit_prob,
        "hr_prob": hr_prob,
        "tb_prob": tb_prob,
        "rbi_prob": rbi_prob,
        "platoon": platoon,
        "lineup_mult": lineup_mult,
        "hr_factor": park["hr_factor"],
        "hit_factor": park["hit_factor"],
    }

rows = []
skipped = []

for _, row in matchups.iterrows():
    batter_match = find_name_match(batters, row["_batter"])
    pitcher_match = find_name_match(pitchers, row["_pitcher"])

    if batter_match.empty:
        skipped.append(f"Batter not found: {row[m_batter]}")
        continue
    if pitcher_match.empty:
        skipped.append(f"Pitcher not found: {row[m_pitcher]}")
        continue

    batter_row = batter_match.iloc[0]
    pitcher_row = pitcher_match.iloc[0]

    batter_hand = row[m_bhand] if m_bhand else ""
    pitcher_hand = row[m_phand] if m_phand else ""
    lineup_spot = row[m_lineup] if m_lineup else default_lineup_spot
    weather_boost = row[m_weather] if m_weather else default_weather_boost
    team_total = row[m_team_total] if m_team_total else default_team_total

    calc = calc_batter_board(
        batter_row=batter_row,
        pitcher_row=pitcher_row,
        park_key=row["_park"],
        batter_hand=batter_hand,
        pitcher_hand=pitcher_hand,
        lineup_spot=lineup_spot,
        weather_boost=weather_boost,
        team_total=team_total,
    )

    hit_odds = safe_float(row[m_hit_odds], None) if m_hit_odds else None
    hr_odds = safe_float(row[m_hr_odds], None) if m_hr_odds else None
    tb_odds = safe_float(row[m_tb_odds], None) if m_tb_odds else None
    rbi_odds = safe_float(row[m_rbi_odds], None) if m_rbi_odds else None

    hit_edge = calc["hit_prob"] - implied_prob(hit_odds) if hit_odds is not None else None
    hr_edge = calc["hr_prob"] - implied_prob(hr_odds) if hr_odds is not None else None
    tb_edge = calc["tb_prob"] - implied_prob(tb_odds) if tb_odds is not None else None
    rbi_edge = calc["rbi_prob"] - implied_prob(rbi_odds) if rbi_odds is not None else None

    best_score = max(
        calc["hit_prob"] * 100,
        calc["hr_prob"] * 100,
        calc["tb_prob"] * 100,
        calc["rbi_prob"] * 100,
    )

    rows.append(
        {
            "Batter": row[m_batter],
            "Pitcher": row[m_pitcher],
            "Team": row[m_team] if m_team else "",
            "Opp": row[m_opp] if m_opp else "",
            "Park": row[m_park],
            "Lineup": int(float(lineup_spot)) if str(lineup_spot) != "nan" else None,
            "Hit %": round(calc["hit_prob"] * 100, 1),
            "HR %": round(calc["hr_prob"] * 100, 1),
            "TB %": round(calc["tb_prob"] * 100, 1),
            "RBI %": round(calc["rbi_prob"] * 100, 1),
            "Hit Edge %": round(hit_edge * 100, 1) if hit_edge is not None else None,
            "HR Edge %": round(hr_edge * 100, 1) if hr_edge is not None else None,
            "TB Edge %": round(tb_edge * 100, 1) if tb_edge is not None else None,
            "RBI Edge %": round(rbi_edge * 100, 1) if rbi_edge is not None else None,
            "Platoon": round(calc["platoon"], 2),
            "HR Park": round(calc["hr_factor"], 2),
            "Hit Park": round(calc["hit_factor"], 2),
            "Best Score": round(best_score, 1),
            "Best Grade": grade_from_score(best_score),
        }
    )

batters_df = pd.DataFrame(rows)

if batters_df.empty:
    st.error("No valid matchup rows were processed.")
    if skipped:
        st.write(skipped)
    st.stop()

pitcher_board = []
for pitcher_name, grp in batters_df.groupby("Pitcher"):
    p_match = find_name_match(pitchers, norm_text(pitcher_name))
    if p_match.empty:
        continue
    p_row = p_match.iloc[0]
    p = get_pitcher_metrics(p_row)

    opp_batters = []
    for _, r in grp.iterrows():
        bm = find_name_match(batters, norm_text(r["Batter"]))
        if not bm.empty:
            opp_batters.append(get_batter_metrics(bm.iloc[0]))

    if opp_batters:
        avg_b_k = sum(x["k_rate"] for x in opp_batters) / len(opp_batters)
        avg_b_bb = sum(x["bb_rate"] for x in opp_batters) / len(opp_batters)
        avg_b_xba = sum(x["xba"] for x in opp_batters) / len(opp_batters)
    else:
        avg_b_k, avg_b_bb, avg_b_xba = 0.22, 0.08, 0.240

    k_score = (
        3.0 * (p["k_rate"] - 0.22)
        + 2.2 * (avg_b_k - 0.22)
        - 0.8 * (avg_b_bb - 0.08)
        - 1.1 * (avg_b_xba - 0.240)
    )
    k_prob = logistic(-0.10 + k_score)
    k_prob = min(max(k_prob, 0.05), 0.85)

    pitcher_board.append(
        {
            "Pitcher": pitcher_name,
            "Opponent": grp["Team"].iloc[0] if "Team" in grp.columns else "",
            "K Chance %": round(k_prob * 100, 1),
            "Avg Opp Hit %": round(grp["Hit %"].mean(), 1),
            "Avg Opp HR %": round(grp["HR %"].mean(), 1),
            "Avg Opp TB %": round(grp["TB %"].mean(), 1),
            "Grade": grade_from_score(k_prob * 100),
        }
    )

pitchers_df = pd.DataFrame(pitcher_board)
if not pitchers_df.empty:
    pitchers_df = pitchers_df.sort_values("K Chance %", ascending=False).reset_index(drop=True)

best_pick_rows = []
for _, r in batters_df.iterrows():
    options = [
        ("Hit", r["Hit %"], r["Hit Edge %"]),
        ("Home Run", r["HR %"], r["HR Edge %"]),
        ("Total Bases", r["TB %"], r["TB Edge %"]),
        ("RBI", r["RBI %"], r["RBI Edge %"]),
    ]

    ranked = sorted(options, key=lambda x: (x[2] if x[2] is not None else -999, x[1]), reverse=True)
    best_prop, best_prob, best_edge = ranked[0]
    score = best_prob if best_edge is None else best_prob + max(best_edge, 0)

    best_pick_rows.append(
        {
            "Player": r["Batter"],
            "Pitcher": r["Pitcher"],
            "Park": r["Park"],
            "Best Prop": best_prop,
            "Model %": best_prob,
            "Edge %": best_edge,
            "Score": round(score, 1),
            "Grade": grade_from_score(score),
        }
    )

best_picks_df = pd.DataFrame(best_pick_rows).sort_values("Score", ascending=False).reset_index(drop=True)

top_pick = best_picks_df.iloc[0]
top_k = pitchers_df.iloc[0] if not pitchers_df.empty else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Best Overall Pick", top_pick["Player"])
c2.metric("Best Prop", top_pick["Best Prop"])
c3.metric("Top Score", f"{top_pick['Score']}")
c4.metric("Top Pitcher K Spot", top_k["Pitcher"] if top_k is not None else "—")

st.subheader("🔥 Best Rated Picks For The Day")
st.dataframe(best_picks_df.head(15), use_container_width=True)

st.subheader("🎯 Best Pitcher Strikeout Chances")
if pitchers_df.empty:
    st.info("No pitcher K board available yet.")
else:
    st.dataframe(pitchers_df.head(15), use_container_width=True)

st.subheader("⚾ Best Batter Hit Chances")
st.dataframe(
    batters_df.sort_values(["Hit %", "Hit Edge %"], ascending=[False, False]).head(15),
    use_container_width=True,
)

st.subheader("💣 Best Home Run Chances")
st.dataframe(
    batters_df.sort_values(["HR %", "HR Edge %"], ascending=[False, False]).head(15),
    use_container_width=True,
)

st.subheader("🏃 Best Total Bases Chances")
st.dataframe(
    batters_df.sort_values(["TB %", "TB Edge %"], ascending=[False, False]).head(15),
    use_container_width=True,
)

st.subheader("💰 Best RBI Chances")
st.dataframe(
    batters_df.sort_values(["RBI %", "RBI Edge %"], ascending=[False, False]).head(15),
    use_container_width=True,
)

with st.expander("Full Batter Board"):
    st.dataframe(
        batters_df.sort_values(["Best Score", "Hit %"], ascending=[False, False]),
        use_container_width=True,
    )

if skipped:
    with st.expander("Skipped Rows / Name Debug"):
        for item in skipped:
            st.write(item)
