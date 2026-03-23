import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="CJNeverStops AI Betting Dashboard", layout="wide")

st.title("🔥 CJNeverStops AI Betting Dashboard")
st.caption("Free-only model: local CSV files + manual odds")

BATTERS_FILE = "batters.csv"
PITCHERS_FILE = "pitchers.csv"
PARKS_FILE = "parks.csv"

@st.cache_data(ttl=3600)
def load_csv_file(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

def norm_name(s: str) -> str:
    return " ".join(str(s).strip().lower().replace(",", "").split())

def pick_col(df, candidates, default=None):
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    return default

def pct_to_decimal(v):
    if pd.isna(v):
        return None
    try:
        v = float(v)
    except Exception:
        return None
    return v / 100.0 if v > 1 else v

def safe_float(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

def american_to_implied(odds: int) -> float:
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)

def grade_edge(edge: float) -> str:
    if edge >= 0.07:
        return "🔥 LOCK"
    if edge >= 0.05:
        return "✅ STRONG"
    if edge >= 0.03:
        return "⚠️ LEAN"
    return "❌ PASS"

def logistic(x: float) -> float:
    return 1 / (1 + math.exp(-x))

try:
    batters = load_csv_file(BATTERS_FILE)
    pitchers = load_csv_file(PITCHERS_FILE)
    parks = load_csv_file(PARKS_FILE)
except Exception as e:
    st.error(f"CSV load failed: {e}")
    st.stop()

b_name = pick_col(batters, ["player_name", "player", "name"])
b_xba = pick_col(batters, ["xba", "xBA"])
b_xslg = pick_col(batters, ["xslg", "xSLG"])
b_xwoba = pick_col(batters, ["xwoba", "xwOBA"])
b_barrel = pick_col(batters, ["brl_percent", "barrel_batted_rate", "barrel_pct"])
b_hardhit = pick_col(batters, ["hard_hit_percent", "hard_hit_pct"])
b_k = pick_col(batters, ["k_percent", "k%", "strikeout_percent"])
b_bb = pick_col(batters, ["bb_percent", "bb%", "walk_percent"])

p_name = pick_col(pitchers, ["player_name", "player", "name"])
p_xba = pick_col(pitchers, ["xba", "xBA"])
p_xslg = pick_col(pitchers, ["xslg", "xSLG"])
p_xwoba = pick_col(pitchers, ["xwoba", "xwOBA"])
p_barrel = pick_col(pitchers, ["brl_percent", "barrel_batted_rate", "barrel_pct"])
p_hardhit = pick_col(pitchers, ["hard_hit_percent", "hard_hit_pct"])
p_k = pick_col(pitchers, ["k_percent", "k%", "strikeout_percent"])
p_bb = pick_col(pitchers, ["bb_percent", "bb%", "walk_percent"])

park_name = pick_col(parks, ["venue_name", "park_name", "venue", "park"])
park_hr = pick_col(parks, ["hr", "home_run", "home_runs", "hr_factor"])
park_hit = pick_col(parks, ["1b", "hits", "hit", "hit_factor"])

batters["_name"] = batters[b_name].map(norm_name)
pitchers["_name"] = pitchers[p_name].map(norm_name)

batter_names = sorted(batters[b_name].dropna().astype(str).unique())
pitcher_names = sorted(pitchers[p_name].dropna().astype(str).unique())
park_names = sorted(parks[park_name].dropna().astype(str).unique()) if park_name else ["Neutral"]

with st.sidebar:
    st.header("Model Inputs")
    selected_batter = st.selectbox("Batter", batter_names)
    selected_pitcher = st.selectbox("Pitcher", pitcher_names)
    selected_park = st.selectbox("Park", park_names)
    batter_hand = st.selectbox("Batter hand", ["Auto/Unknown", "L", "R"])
    pitcher_hand = st.selectbox("Pitcher throws", ["Auto/Unknown", "L", "R"])
    weather_boost = st.slider("Weather HR boost", 0.90, 1.15, 1.00, 0.01)
    manual_odds = st.number_input("American odds", value=-110, step=5)
    prop_type = st.selectbox("Prop type", ["Hit", "Home Run", "Strikeout"])

brow = batters.loc[batters["_name"] == norm_name(selected_batter)].iloc[0]
prow = pitchers.loc[pitchers["_name"] == norm_name(selected_pitcher)].iloc[0]

b_xba_v = safe_float(brow[b_xba], 0.240)
b_xslg_v = safe_float(brow[b_xslg], 0.390)
b_xwoba_v = safe_float(brow[b_xwoba], 0.310)
b_barrel_v = pct_to_decimal(brow[b_barrel]) if b_barrel else 0.08
b_hardhit_v = pct_to_decimal(brow[b_hardhit]) if b_hardhit else 0.38
b_k_v = pct_to_decimal(brow[b_k]) if b_k else 0.22
b_bb_v = pct_to_decimal(brow[b_bb]) if b_bb else 0.08

p_xba_v = safe_float(prow[p_xba], 0.240)
p_xslg_v = safe_float(prow[p_xslg], 0.390)
p_xwoba_v = safe_float(prow[p_xwoba], 0.310)
p_barrel_v = pct_to_decimal(prow[p_barrel]) if p_barrel else 0.08
p_hardhit_v = pct_to_decimal(prow[p_hardhit]) if p_hardhit else 0.38
p_k_v = pct_to_decimal(prow[p_k]) if p_k else 0.22
p_bb_v = pct_to_decimal(prow[p_bb]) if p_bb else 0.08

hr_factor = 1.00
hit_factor = 1.00
park_row = parks.loc[parks[park_name].astype(str) == selected_park] if park_name else pd.DataFrame()
if not park_row.empty:
    if park_hr:
        hr_raw = safe_float(park_row.iloc[0][park_hr], 100.0)
        hr_factor = hr_raw / 100.0 if hr_raw > 3 else hr_raw
    if park_hit:
        hit_raw = safe_float(park_row.iloc[0][park_hit], 100.0)
        hit_factor = hit_raw / 100.0 if hit_raw > 3 else hit_raw

platoon_boost = 1.00
if batter_hand in ["L", "R"] and pitcher_hand in ["L", "R"]:
    platoon_boost = 1.03 if batter_hand != pitcher_hand else 0.97

hit_score = (
    2.2 * (b_xba_v - 0.240)
    + 1.1 * (b_xwoba_v - 0.310)
    + 0.7 * ((b_hardhit_v or 0.38) - 0.38)
    - 1.0 * ((b_k_v or 0.22) - 0.22)
    - 1.8 * (p_k_v - 0.22)
    - 1.3 * (p_xba_v - 0.240)
)
hit_prob = logistic(-1.20 + hit_score) * hit_factor * platoon_boost
hit_prob = min(max(hit_prob, 0.03), 0.92)

hr_score = (
    4.5 * (b_xslg_v - 0.390)
    + 2.4 * ((b_barrel_v or 0.08) - 0.08)
    + 1.4 * ((b_hardhit_v or 0.38) - 0.38)
    + 2.6 * (p_xslg_v - 0.390)
    + 1.5 * ((p_barrel_v or 0.08) - 0.08)
    + 0.8 * ((p_hardhit_v or 0.38) - 0.38)
)
hr_prob = logistic(-3.10 + hr_score) * hr_factor * weather_boost * platoon_boost
hr_prob = min(max(hr_prob, 0.005), 0.55)

k_score = (
    3.0 * (p_k_v - 0.22)
    + 2.2 * ((b_k_v or 0.22) - 0.22)
    - 0.8 * (b_bb_v - 0.08)
    - 0.5 * (p_bb_v - 0.08)
)
k_prob = logistic(-0.20 + k_score)
k_prob = min(max(k_prob, 0.05), 0.80)

model_prob = {"Hit": hit_prob, "Home Run": hr_prob, "Strikeout": k_prob}[prop_type]
book_prob = american_to_implied(int(manual_odds))
edge = model_prob - book_prob
label = grade_edge(edge)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Prop", prop_type)
c2.metric("Model %", f"{model_prob*100:.1f}%")
c3.metric("Book %", f"{book_prob*100:.1f}%")
c4.metric("Edge", f"{edge*100:.1f}%")

st.subheader(label)
