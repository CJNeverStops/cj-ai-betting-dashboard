import math
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="CJ HR AI Board", layout="wide")
st.title("🔥 CJ HR AI Board")

# ================= FIX =================
def scale01(x, low, high):
    try:
        x = float(x)
    except:
        x = low
    if high <= low:
        return 0.5
    return max(0, min(1, (x - low) / (high - low)))

# ================= HELPERS =================
def safe_float(x, d=0.0):
    try:
        if pd.isna(x): return d
        return float(x)
    except:
        return d

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def norm(x):
    return " ".join(str(x).lower().replace(",", "").strip().split())

def first_last(x):
    x = str(x).strip()
    if "," in x:
        last, first = [p.strip() for p in x.split(",", 1)]
        return f"{first} {last}"
    return x

def find_col(df, names):
    cols = {str(c).lower().strip(): c for c in df.columns}
    for n in names:
        if n.lower() in cols:
            return cols[n.lower()]
    for n in names:
        for c in df.columns:
            if n.lower() in str(c).lower():
                return c
    return None

def build_name(df):
    c = find_col(df, ["player_name", "name"])
    if c: return df[c].astype(str)

    c = find_col(df, ["last_name, first_name"])
    if c: return df[c].astype(str).apply(first_last)

    st.error(f"❌ Missing player name column. Columns: {list(df.columns)}")
    st.stop()

def pct(x, d):
    v = safe_float(x, d)
    return v / 100 if v > 1 else v

def fair_odds(p):
    if p <= 0 or p >= 1: return "N/A"
    if p >= .5: return int(round(-(p / (1 - p)) * 100))
    return int(round(((1 - p) / p) * 100))

def player_match(a, b):
    a = norm(first_last(a))
    b = norm(first_last(b))
    if a == b:
        return True
    if len(a.split()) > 1 and len(b.split()) > 1:
        return a.split()[-1] == b.split()[-1]
    return False

def find_player(df, name):
    r = df[df["_player_name"].apply(lambda x: player_match(x, name))]
    return r.iloc[0] if not r.empty else None

# ================= LOAD DATA =================
batters = pd.read_csv("batters.csv")
pitchers = pd.read_csv("pitchers.csv")
parks = pd.read_csv("parks.csv")

batters["_player_name"] = build_name(batters)
pitchers["_player_name"] = build_name(pitchers)

b_xslg = find_col(batters, ["est_slg","xslg"])
b_barrel = find_col(batters, ["barrel"])
b_hard = find_col(batters, ["hard_hit"])

p_xslg = find_col(pitchers, ["est_slg","xslg"])
p_barrel = find_col(pitchers, ["barrel"])
p_hard = find_col(pitchers, ["hard_hit"])
p_hr9 = find_col(pitchers, ["hr_per_9","hr9"])

park_col = find_col(parks, ["park_name","venue"])
park_hr = find_col(parks, ["hr_factor"])

parks["_park"] = parks[park_col].astype(str).str.lower()

# ================= MLB API =================
def get_schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher"
    data = requests.get(url).json()

    games=[]
    for d in data.get("dates",[]):
        for g in d.get("games",[]):
            games.append({
                "away": g["teams"]["away"]["team"]["name"],
                "home": g["teams"]["home"]["team"]["name"],
                "away_p": g["teams"]["away"].get("probablePitcher",{}).get("fullName",""),
                "home_p": g["teams"]["home"].get("probablePitcher",{}).get("fullName",""),
                "park": g["venue"]["name"]
            })
    return games

games = get_schedule()

# ================= MODEL =================
def park_factor(park):
    r = parks[parks["_park"] == str(park).lower()]
    if r.empty: return 1
    v = safe_float(r.iloc[0][park_hr],1)
    return v/100 if v>3 else v

def hitter_power(b):
    return clamp(
        .4*scale01(safe_float(b[b_xslg],.4),.3,.75) +
        .3*scale01(pct(b[b_barrel],.08),.02,.25) +
        .3*scale01(pct(b[b_hard],.4),.2,.65),
        0,1)

def pitcher_vuln(p):
    return clamp(
        .4*scale01(safe_float(p[p_xslg],.4),.3,.65) +
        .3*scale01(pct(p[p_barrel],.08),.02,.18) +
        .3*scale01(safe_float(p[p_hr9],1),.3,2.2),
        0,1)

rows=[]

for g in games:
    if not g["home_p"]:
        continue

    p_row = find_player(pitchers, g["home_p"])
    if p_row is None:
        continue

    for _, b in batters.iterrows():
        bp = hitter_power(b)
        pv = pitcher_vuln(p_row)
        pf = park_factor(g["park"])

        prob = clamp(.08 + (.38*bp + .27*pv + .20*pf)*.18,.02,.30)

        rows.append({
            "Batter": b["_player_name"],
            "Matchup": f'{g["away"]} @ {g["home"]}',
            "HR%": round(prob*100,1),
            "Odds": fair_odds(prob)
        })

# ================= OUTPUT =================
hr_df = pd.DataFrame(rows)

if hr_df.empty:
    st.error("❌ No model output. Likely no pitchers matched.")
    st.stop()

hr_df = hr_df.sort_values("HR%", ascending=False)

st.dataframe(hr_df.head(75), use_container_width=True)
