import math
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="CJ Daily MLB AI Board", layout="wide")

st.title("🔥 CJNeverStops Daily MLB AI Board")
st.caption("Daily MLB projections for hitters and pitchers with fair odds and edge checkers")

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

Use it as an overall matchup-strength score, then compare your model price to the book.
"""
    )

BATTERS_FILE = "batters.csv"
PITCHERS_FILE = "pitchers.csv"
PARKS_FILE = "parks.csv"


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


def scale_park_factor(value, default: float = 1.0) -> float:
    x = safe_float(value, default)
    return x / 100.0 if x > 3 else x


def grade_from_score(score: float) -> str:
    if score >= 65:
        return "🔥 LOCK"
    if score >= 55:
        return "✅ STRONG"
    if score >= 45:
        return "⚠️ LEAN"
    return "❌ PASS"


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


def platoon_boost(batter_hand, pitcher_hand) -> float:
    bh = str(batter_hand).strip().upper()
    ph = str(pitcher_hand).strip().upper()
    if bh in ["L", "R"] and ph in ["L", "R"]:
        return 1.03 if bh != ph else 0.97
    return 1.00


def lineup_boost(lineup_spot) -> float:
    try:
        s = int(float(lineup_spot))
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


def rbi_lineup_boost(lineup_spot) -> float:
    try:
        s = int(float(lineup_spot))
    except Exception:
        return 1.00
    boost_map = {
        1: 0.88,
        2: 0.96,
        3: 1.12,
        4: 1.18,
        5: 1.10,
        6: 1.00,
        7: 0.92,
        8: 0.86,
        9: 0.80,
    }
    return boost_map.get(s, 1.00)


def estimate_plate_appearances(lineup_spot) -> float:
    try:
        s = int(float(lineup_spot))
    except Exception:
        return 4.2
    pa_map = {
        1: 4.9,
        2: 4.8,
        3: 4.7,
        4: 4.6,
        5: 4.5,
        6: 4.3,
        7: 4.2,
        8: 4.0,
        9: 3.8,
    }
    return pa_map.get(s, 4.2)


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


def get_batter_metrics(row, b_xba, b_xslg, b_xwoba, b_barrel, b_hardhit, b_k, b_bb):
    return {
        "xba": safe_float(row[b_xba], 0.240) if b_xba else 0.240,
        "xslg": safe_float(row[b_xslg], 0.390) if b_xslg else 0.390,
        "xwoba": safe_float(row[b_xwoba], 0.310) if b_xwoba else 0.310,
        "barrel": pct_to_decimal(row[b_barrel], 0.08) if b_barrel else 0.08,
        "hardhit": pct_to_decimal(row[b_hardhit], 0.38) if b_hardhit else 0.38,
        "k_rate": pct_to_decimal(row[b_k], 0.22) if b_k else 0.22,
        "bb_rate": pct_to_decimal(row[b_bb], 0.08) if b_bb else 0.08,
    }


def get_pitcher_metrics(row, p_xba, p_xslg, p_xwoba, p_barrel, p_hardhit, p_k, p_bb):
    return {
        "xba": safe_float(row[p_xba], 0.240) if p_xba else 0.240,
        "xslg": safe_float(row[p_xslg], 0.390) if p_xslg else 0.390,
        "xwoba": safe_float(row[p_xwoba], 0.310) if p_xwoba else 0.310,
        "barrel": pct_to_decimal(row[p_barrel], 0.08) if p_barrel else 0.08,
        "hardhit": pct_to_decimal(row[p_hardhit], 0.38) if p_hardhit else 0.38,
        "k_rate": pct_to_decimal(row[p_k], 0.22) if p_k else 0.22,
        "bb_rate": pct_to_decimal(row[p_bb], 0.08) if p_bb else 0.08,
    }


def get_park_factors(parks_df, park_key, park_hr_col, park_hit_col):
    row = parks_df.loc[parks_df["_park"] == park_key]
    if row.empty:
        return {"hr_factor": 1.00, "hit_factor": 1.00}
    row = row.iloc[0]
    return {
        "hr_factor": scale_park_factor(row[park_hr_col], 1.00) if park_hr_col else 1.00,
        "hit_factor": scale_park_factor(row[park_hit_col], 1.00) if park_hit_col else 1.00,
    }


def pitcher_hr_tendency(p):
    return ((p["xslg"] - 0.390) * 2.2) + ((p["barrel"] - 0.08) * 3.5)


def calc_batter_board(batter_row, pitcher_row, parks_df, park_key, batter_hand, pitcher_hand, lineup_spot, weather_boost, team_total,
                      b_xba, b_xslg, b_xwoba, b_barrel, b_hardhit, b_k, b_bb,
                      p_xba, p_xslg, p_xwoba, p_barrel, p_hardhit, p_k, p_bb,
                      park_hr_col, park_hit_col):
    b = get_batter_metrics(batter_row, b_xba, b_xslg, b_xwoba, b_barrel, b_hardhit, b_k, b_bb)
    p = get_pitcher_metrics(pitcher_row, p_xba, p_xslg, p_xwoba, p_barrel, p_hardhit, p_k, p_bb)
    park = get_park_factors(parks_df, park_key, park_hr_col, park_hit_col)

    platoon = platoon_boost(batter_hand, pitcher_hand)
    lineup_mult = lineup_boost(lineup_spot)
    weather_mult = safe_float(weather_boost, 1.00)
    team_total_v = safe_float(team_total, 4.2)
    team_total_mult = max(0.85, min(1.20, team_total_v / 4.2))
    plate_appearances = estimate_plate_appearances(lineup_spot)

    hit_score_raw = (
        2.2 * (b["xba"] - 0.240)
        + 1.1 * (b["xwoba"] - 0.310)
        + 0.7 * (b["hardhit"] - 0.38)
        - 1.0 * (b["k_rate"] - 0.22)
        - 1.8 * (p["k_rate"] - 0.22)
        - 1.3 * (p["xba"] - 0.240)
    )
    hit_prob_pa = logistic(-1.20 + hit_score_raw) * park["hit_factor"] * platoon
    hit_prob_pa = max(0.03, min(0.75, hit_prob_pa))
    hit_prob = 1 - (1 - hit_prob_pa) ** plate_appearances
    hit_prob = max(0.10, min(0.95, hit_prob))

    hr_score_raw = (
        5.2 * (b["xslg"] - 0.390)
        + 3.0 * (b["barrel"] - 0.08)
        + 1.6 * (b["hardhit"] - 0.38)
        + 2.8 * (p["xslg"] - 0.390)
        + 2.0 * (p["barrel"] - 0.08)
        + pitcher_hr_tendency(p)
    )
    hr_prob_pa = logistic(-3.25 + hr_score_raw)
    hr_prob = 1 - (1 - hr_prob_pa) ** plate_appearances
    hr_prob *= park["hr_factor"]
    hr_prob *= weather_mult
    hr_prob *= platoon
    hr_prob = max(0.01, min(0.60, hr_prob))

    tb_score_raw = (
        3.4 * (b["xslg"] - 0.390)
        + 1.8 * (b["xba"] - 0.240)
        + 1.8 * (b["hardhit"] - 0.38)
        + 1.5 * (b["barrel"] - 0.08)
        + 1.9 * (p["xslg"] - 0.390)
        + 0.8 * (p["xba"] - 0.240)
    )
    tb_prob_pa = logistic(-1.45 + tb_score_raw)
    tb_prob_pa = max(0.03, min(0.65, tb_prob_pa))
    tb_prob = 1 - (1 - tb_prob_pa) ** (plate_appearances * 0.92)
    tb_prob *= park["hit_factor"]
    tb_prob *= (park["hr_factor"] ** 0.35)
    tb_prob *= platoon
    tb_prob = max(0.05, min(0.92, tb_prob))

    rbi_score_raw = (
        2.3 * (b["xwoba"] - 0.310)
        + 2.4 * (b["xslg"] - 0.390)
        + 1.3 * (b["hardhit"] - 0.38)
        + 1.1 * (p["xwoba"] - 0.310)
    )
    rbi_prob_pa = logistic(-2.10 + rbi_score_raw)
    rbi_prob_pa = max(0.02, min(0.45, rbi_prob_pa))
    rbi_prob = 1 - (1 - rbi_prob_pa) ** (plate_appearances * 0.95)
    rbi_prob *= park["hit_factor"]
    rbi_prob *= team_total_mult
    rbi_prob *= platoon
    rbi_prob *= rbi_lineup_boost(lineup_spot)
    rbi_prob = max(0.03, min(0.88, rbi_prob))

    weighted_score = (hit_prob * 0.40 + tb_prob * 0.30 + rbi_prob * 0.20 + hr_prob * 0.10) * 100

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


def project_pitcher_ks(pitcher_row, opp_batters, p_xba, p_xslg, p_xwoba, p_barrel, p_hardhit, p_k, p_bb):
    p = get_pitcher_metrics(pitcher_row, p_xba, p_xslg, p_xwoba, p_barrel, p_hardhit, p_k, p_bb)
    if opp_batters:
        avg_opp_k = sum(x["k_rate"] for x in opp_batters) / len(opp_batters)
    else:
        avg_opp_k = 0.22

    base_k_rate = (p["k_rate"] + avg_opp_k) / 2

    lineup_size = len(opp_batters)
    batters_faced = 24.0
    if lineup_size >= 9:
        batters_faced = 25.0
    elif lineup_size <= 6:
        batters_faced = 22.5

    return base_k_rate * batters_faced


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
        batter_row, pitcher_row, parks, row["_park"], row.get("batter_hand", ""), row.get("pitcher_hand", ""),
        row.get("lineup_spot", 5), row.get("weather_boost", weather_boost_default), row.get("team_total", team_total_default),
        b_xba, b_xslg, b_xwoba, b_barrel, b_hardhit, b_k, b_bb,
        p_xba, p_xslg, p_xwoba, p_barrel, p_hardhit, p_k, p_bb,
        park_hr_col, park_hit_col
    )

    rows.append({
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
        "Best Grade": grade_from_score(calc["weighted_score"]),
    })

batters_df = pd.DataFrame(rows)
if batters_df.empty:
    st.error("No valid matchup rows were processed.")
    if skipped:
        st.write(skipped)
    st.stop()

# Best picks board
best_pick_rows = []
for _, r in batters_df.iterrows():
    prop_options = [
        ("Hit", r["Hit %"], r["Hit Fair Odds"]),
        ("Home Run", r["HR %"], r["HR Fair Odds"]),
        ("Total Bases", r["TB %"], r["TB Fair Odds"]),
        ("RBI", r["RBI %"], r["RBI Fair Odds"]),
    ]
    best_prop, best_prob, best_fair = sorted(prop_options, key=lambda x: x[1], reverse=True)[0]
    best_pick_rows.append({
        "Player": r["Batter"],
        "Pitcher": r["Pitcher"],
        "Park": r["Park"],
        "Best Prop": best_prop,
        "Best Prop %": best_prob,
        "Fair Odds": best_fair,
        "Model Score": r["Model Score"],
        "Grade": r["Best Grade"],
    })

best_picks_df = pd.DataFrame(best_pick_rows).sort_values("Model Score", ascending=False).reset_index(drop=True)

# Pitcher K board
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
            opp_batters.append(get_batter_metrics(b_match.iloc[0], b_xba, b_xslg, b_xwoba, b_barrel, b_hardhit, b_k, b_bb))

    expected_ks = project_pitcher_ks(p_row, opp_batters, p_xba, p_xslg, p_xwoba, p_barrel, p_hardhit, p_k, p_bb)
    prob_45 = prob_over_k_line(expected_ks, 4.5)
    prob_55 = prob_over_k_line(expected_ks, 5.5)
    prob_65 = prob_over_k_line(expected_ks, 6.5)

    pitcher_board.append({
        "Pitcher": pitcher_name,
        "Opponent": grp["Team"].iloc[0] if "Team" in grp.columns else "",
        "Proj Ks": round(expected_ks, 2),
        "Over 4.5 %": round(prob_45 * 100, 1),
        "Over 4.5 Fair": prob_to_fair_american(prob_45),
        "Over 5.5 %": round(prob_55 * 100, 1),
        "Over 5.5 Fair": prob_to_fair_american(prob_55),
        "Over 6.5 %": round(prob_65 * 100, 1),
        "Over 6.5 Fair": prob_to_fair_american(prob_65),
    })

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

        hc1, hc2, hc3, hc4 = st.columns(4)
        hc1.metric("Model %", f"{model_pct:.1f}%")
        hc2.metric("Book Implied %", f"{implied:.1f}%")
        hc3.metric("Edge %", f"{edge_pct:.1f}%")
        hc4.metric("Fair Odds", str(prop_to_fair[checker_prop]))
        st.write(f"**Verdict:** {edge_grade(edge_pct)}")
    except Exception:
        st.warning("Enter odds like +150 or -120")

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
st.dataframe(batters_df.sort_values("Hit %", ascending=False).head(15), use_container_width=True)

st.subheader("💣 Best Home Run Chances")
st.dataframe(batters_df.sort_values("HR %", ascending=False).head(15), use_container_width=True)

st.subheader("🏃 Best Total Bases Chances")
st.dataframe(batters_df.sort_values("TB %", ascending=False).head(15), use_container_width=True)

st.subheader("💰 Best RBI Chances")
st.dataframe(batters_df.sort_values("RBI %", ascending=False).head(15), use_container_width=True)

st.subheader("🧠 Why These Picks (Top 5 Breakdown)")
top5 = best_picks_df.head(5)

for _, rec in top5.iterrows():
    batter_row = batters[batters["_keys"].apply(lambda s: norm_text(rec["Player"]) in s)].iloc[0]
    pitcher_row = pitchers[pitchers["_keys"].apply(lambda s: norm_text(rec["Pitcher"]) in s)].iloc[0]

    b = get_batter_metrics(batter_row, b_xba, b_xslg, b_xwoba, b_barrel, b_hardhit, b_k, b_bb)
    p = get_pitcher_metrics(pitcher_row, p_xba, p_xslg, p_xwoba, p_barrel, p_hardhit, p_k, p_bb)

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
