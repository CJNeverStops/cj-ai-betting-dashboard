import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="CJ AI Dashboard V2", layout="wide")

st.title("🔥 CJNeverStops AI Betting Dashboard V2")
st.caption("Free model + matchup import + ranked picks board")

BATTERS_FILE = "batters.csv"
PITCHERS_FILE = "pitchers.csv"
PARKS_FILE = "parks.csv"
MATCHUPS_FILE = "today_matchups.csv"

@st.cache_data(ttl=3600)
def try_load_csv(path):
    try:
        return pd.read_csv(path), None
    except Exception as e:
        return pd.DataFrame(), str(e)

batters, batters_err = try_load_csv(BATTERS_FILE)
pitchers, pitchers_err = try_load_csv(PITCHERS_FILE)
parks, parks_err = try_load_csv(PARKS_FILE)
matchups, matchups_err = try_load_csv(MATCHUPS_FILE)

if batters.empty:
    st.error(f"Could not load batters.csv: {batters_err}")
    st.stop()
if pitchers.empty:
    st.error(f"Could not load pitchers.csv: {pitchers_err}")
    st.stop()
if parks.empty:
    st.error(f"Could not load parks.csv: {parks_err}")
    st.stop()
if matchups.empty:
    st.error(f"Could not load today_matchups.csv: {matchups_err}")
    st.stop()

def norm_text(s):
    return " ".join(str(s).strip().lower().replace(",", "").split())

def first_last_name(s):
    s = str(s).strip()
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}".strip().lower()
    return s.lower()

def make_name_keys(s):
    raw = str(s).strip()
    a = norm_text(raw)
    b = norm_text(first_last_name(raw))
    return {a, b}

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

def grade_edge(edge):
    if edge >= 0.07:
        return "🔥 LOCK"
    if edge >= 0.05:
        return "✅ STRONG"
    if edge >= 0.03:
        return "⚠️ LEAN"
    return "❌ PASS"

def confidence_score(edge, model_prob):
    score = 50 + (edge * 250) + (model_prob * 25)
    return max(1, min(99, round(score)))

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

with st.expander("CSV Debug Info"):
    st.write("Batters columns:", list(batters.columns))
    st.write("Pitchers columns:", list(pitchers.columns))
    st.write("Parks columns:", list(parks.columns))
    st.write("Matchups columns:", list(matchups.columns))
    st.write("Batters rows:", len(batters))
    st.write("Pitchers rows:", len(pitchers))
    st.write("Parks rows:", len(parks))
    st.write("Matchups rows:", len(matchups))

b_name = require_col(batters, ["player_name", "name", "player", "last_name, first_name"], "batter name column")
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

m_batter = require_col(matchups, ["batter", "hitter", "player"], "matchup batter column")
m_pitcher = require_col(matchups, ["pitcher"], "matchup pitcher column")
m_park = require_col(matchups, ["park", "venue", "park_name"], "matchup park column")
m_bhand = find_col(matchups, ["batter_hand", "stand", "bats"])
m_phand = find_col(matchups, ["pitcher_hand", "p_throws", "throws"])
m_prop = require_col(matchups, ["prop_type", "prop", "market"], "matchup prop type column")
m_odds = require_col(matchups, ["odds", "line_odds", "american_odds"], "matchup odds column")

m_team = find_col(matchups, ["team"])
m_game = find_col(matchups, ["game", "matchup"])
m_note = find_col(matchups, ["note", "notes"])
m_book = find_col(matchups, ["book", "sportsbook"])
m_line = find_col(matchups, ["line"])

batters = batters.copy()
pitchers = pitchers.copy()
parks = parks.copy()
matchups = matchups.copy()

batters["_name_keys"] = batters[b_name].astype(str).apply(make_name_keys)
pitchers["_name_keys"] = pitchers[p_name].astype(str).apply(make_name_keys)
parks["_park"] = parks[park_name_col].astype(str).str.strip().str.lower()
matchups["_batter"] = matchups[m_batter].astype(str).map(norm_text)
matchups["_pitcher"] = matchups[m_pitcher].astype(str).map(norm_text)
matchups["_park"] = matchups[m_park].astype(str).str.strip().str.lower()

def find_name_match(df, key):
    matches = df[df["_name_keys"].apply(lambda s: key in s)]
    if matches.empty:
        return pd.DataFrame()
    return matches

def get_batter_metrics(row):
    xba = safe_float(row[b_xba], 0.240) if b_xba else 0.240
    xslg = safe_float(row[b_xslg], 0.390) if b_xslg else 0.390
    xwoba = safe_float(row[b_xwoba], 0.310) if b_xwoba else 0.310
    barrel = pct_to_decimal(row[b_barrel], 0.08) if b_barrel else 0.08
    hardhit = pct_to_decimal(row[b_hardhit], 0.38) if b_hardhit else 0.38
    k_rate = pct_to_decimal(row[b_k], 0.22) if b_k else 0.22
    bb_rate = pct_to_decimal(row[b_bb], 0.08) if b_bb else 0.08
    return xba, xslg, xwoba, barrel, hardhit, k_rate, bb_rate

def get_pitcher_metrics(row):
    xba = safe_float(row[p_xba], 0.240) if p_xba else 0.240
    xslg = safe_float(row[p_xslg], 0.390) if p_xslg else 0.390
    xwoba = safe_float(row[p_xwoba], 0.310) if p_xwoba else 0.310
    barrel = pct_to_decimal(row[p_barrel], 0.08) if p_barrel else 0.08
    hardhit = pct_to_decimal(row[p_hardhit], 0.38) if p_hardhit else 0.38
    k_rate = pct_to_decimal(row[p_k], 0.22) if p_k else 0.22
    bb_rate = pct_to_decimal(row[p_bb], 0.08) if p_bb else 0.08
    return xba, xslg, xwoba, barrel, hardhit, k_rate, bb_rate

def get_park_factors(park_key):
    row = parks.loc[parks["_park"] == park_key]
    if row.empty:
        return 1.00, 1.00
    row = row.iloc[0]
    hr_factor = safe_float(row[park_hr_col], 1.00) if park_hr_col else 1.00
    hit_factor = safe_float(row[park_hit_col], 1.00) if park_hit_col else 1.00
    hr_factor = hr_factor / 100.0 if hr_factor > 3 else hr_factor
    hit_factor = hit_factor / 100.0 if hit_factor > 3 else hit_factor
    return hr_factor, hit_factor

def platoon_boost(batter_hand, pitcher_hand):
    batter_hand = str(batter_hand).strip().upper()
    pitcher_hand = str(pitcher_hand).strip().upper()
    if batter_hand in ["L", "R"] and pitcher_hand in ["L", "R"]:
        return 1.03 if batter_hand != pitcher_hand else 0.97
    return 1.00

def calculate_matchup(batter_row, pitcher_row, park_key, batter_hand, pitcher_hand, prop_type, odds, weather_boost=1.00):
    b_xba_v, b_xslg_v, b_xwoba_v, b_barrel_v, b_hardhit_v, b_k_v, b_bb_v = get_batter_metrics(batter_row)
    p_xba_v, p_xslg_v, p_xwoba_v, p_barrel_v, p_hardhit_v, p_k_v, p_bb_v = get_pitcher_metrics(pitcher_row)

    hr_factor, hit_factor = get_park_factors(park_key)
    platoon = platoon_boost(batter_hand, pitcher_hand)

    hit_score = (
        2.2 * (b_xba_v - 0.240)
        + 1.1 * (b_xwoba_v - 0.310)
        + 0.7 * (b_hardhit_v - 0.38)
        - 1.0 * (b_k_v - 0.22)
        - 1.8 * (p_k_v - 0.22)
        - 1.3 * (p_xba_v - 0.240)
    )
    hit_prob = logistic(-1.20 + hit_score) * hit_factor * platoon
    hit_prob = min(max(hit_prob, 0.03), 0.92)

    hr_score = (
        4.5 * (b_xslg_v - 0.390)
        + 2.4 * (b_barrel_v - 0.08)
        + 1.4 * (b_hardhit_v - 0.38)
        + 2.6 * (p_xslg_v - 0.390)
        + 1.5 * (p_barrel_v - 0.08)
        + 0.8 * (p_hardhit_v - 0.38)
    )
    hr_prob = logistic(-3.10 + hr_score) * hr_factor * weather_boost * platoon
    hr_prob = min(max(hr_prob, 0.005), 0.55)

    k_score = (
        3.0 * (p_k_v - 0.22)
        + 2.2 * (b_k_v - 0.22)
        - 0.8 * (b_bb_v - 0.08)
        - 0.5 * (p_bb_v - 0.08)
    )
    k_prob = logistic(-0.20 + k_score)
    k_prob = min(max(k_prob, 0.05), 0.80)

    prop_map = {
        "hit": hit_prob,
        "hits": hit_prob,
        "home run": hr_prob,
        "hr": hr_prob,
        "homerun": hr_prob,
        "strikeout": k_prob,
        "strikeouts": k_prob,
        "k": k_prob,
        "ks": k_prob,
    }

    prop_key = norm_text(prop_type)
    model_prob = prop_map.get(prop_key, hit_prob)

    book_prob = implied_prob(odds)
    edge = model_prob - book_prob

    return {
        "model_prob": model_prob,
        "book_prob": book_prob,
        "edge": edge,
        "grade": grade_edge(edge),
        "confidence": confidence_score(edge, model_prob),
        "hit_prob": hit_prob,
        "hr_prob": hr_prob,
        "k_prob": k_prob,
        "hr_factor": hr_factor,
        "hit_factor": hit_factor,
        "platoon_boost": platoon,
    }

results = []
skipped = []

for _, row in matchups.iterrows():
    batter_key = row["_batter"]
    pitcher_key = row["_pitcher"]
    park_key = row["_park"]

    batter_match = find_name_match(batters, batter_key)
    pitcher_match = find_name_match(pitchers, pitcher_key)

    if batter_match.empty:
        skipped.append(f"Batter not found: {row[m_batter]}")
        continue
    if pitcher_match.empty:
        skipped.append(f"Pitcher not found: {row[m_pitcher]}")
        continue

    batter_row = batter_match.iloc[0]
    pitcher_row = pitcher_match.iloc[0]

    batter_hand = row[m_bhand] if m_bhand else "Auto/Unknown"
    pitcher_hand = row[m_phand] if m_phand else "Auto/Unknown"
    prop_type = row[m_prop]
    odds = safe_float(row[m_odds], None)

    if odds is None:
        skipped.append(f"Bad odds for {row[m_batter]} vs {row[m_pitcher]}")
        continue

    calc = calculate_matchup(
        batter_row=batter_row,
        pitcher_row=pitcher_row,
        park_key=park_key,
        batter_hand=batter_hand,
        pitcher_hand=pitcher_hand,
        prop_type=prop_type,
        odds=int(odds),
    )

    results.append({
        "Batter": row[m_batter],
        "Pitcher": row[m_pitcher],
        "Park": row[m_park],
        "Prop": prop_type,
        "Odds": int(odds),
        "Model %": round(calc["model_prob"] * 100, 1),
        "Book %": round(calc["book_prob"] * 100, 1),
        "Edge %": round(calc["edge"] * 100, 1),
        "Grade": calc["grade"],
        "Confidence": calc["confidence"],
        "Hit %": round(calc["hit_prob"] * 100, 1),
        "HR %": round(calc["hr_prob"] * 100, 1),
        "K %": round(calc["k_prob"] * 100, 1),
    })

results_df = pd.DataFrame(results)

if results_df.empty:
    st.error("No valid matchup rows were processed.")
    st.write("Most likely cause: name mismatch between today_matchups.csv and batters/pitchers files.")
    if skipped:
        st.write("Skipped rows:")
        st.write(skipped)
    st.stop()

results_df = results_df.sort_values(by=["Edge %", "Confidence"], ascending=[False, False]).reset_index(drop=True)

top = results_df.iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Lock of the Day", top["Batter"])
c2.metric("Best Prop", top["Prop"])
c3.metric("Top Edge", f"{top['Edge %']}%")
c4.metric("Confidence", top["Confidence"])

st.subheader("🔥 Top 10 AI Picks")
st.dataframe(results_df.head(10), use_container_width=True)

st.subheader("📊 Full Ranked Board")
st.dataframe(results_df, use_container_width=True)

if skipped:
    with st.expander("Skipped Rows / Name Mismatch Debug"):
        for item in skipped:
            st.write(item)
