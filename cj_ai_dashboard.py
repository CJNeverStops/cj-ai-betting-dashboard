import math
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="CJ HR AI Board", layout="wide")
st.title("🔥 CJ HR AI Board")

# ---------------- CORE FIX ----------------
def scale01(x, low, high):
    try:
        x = float(x)
    except:
        x = low
    if high <= low:
        return 0.5
    return max(0.0, min(1.0, (x - low) / (high - low)))

# ---------------- HELPERS ----------------
def safe_float(x, d=0.0):
    try:
        if pd.isna(x):
            return d
        return float(x)
    except:
        return d

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def norm(x):
    return " ".join(str(x).lower().replace(",", "").strip().split())

def first_last(x):
    if "," in str(x):
        last, first = x.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return x

def player_match(a, b):
    a = norm(first_last(a))
    b = norm(first_last(b))
    if a == b:
        return True
    ap = a.split()
    bp = b.split()
    return len(ap) >= 2 and len(bp) >= 2 and ap[-1] == bp[-1]

# ---------------- LOAD ----------------
batters = pd.read_csv("batters.csv")
pitchers = pd.read_csv("pitchers.csv")

batters["_player_name"] = (
    batters.get("player_name")
    or batters.get("name")
    or (batters["first_name"] + " " + batters["last_name"])
).astype(str)

pitchers["_player_name"] = (
    pitchers.get("player_name")
    or pitchers.get("name")
    or (pitchers["first_name"] + " " + pitchers["last_name"])
).astype(str)

def find_player(df, name):
    matches = df[df["_player_name"].apply(lambda x: player_match(x, name))]
    return matches.iloc[0] if not matches.empty else None

# ---------------- MODEL ----------------
def hitter_power(row):
    xslg = safe_float(row.get("xslg", row.get("slg", .390)))
    barrel = safe_float(row.get("barrel", .08))
    hard = safe_float(row.get("hard_hit", .38))
    return clamp(
        .4 * scale01(xslg, .300, .750) +
        .3 * scale01(barrel, .02, .25) +
        .3 * scale01(hard, .20, .65),
        0, 1
    )

def pitcher_vuln(row):
    xslg = safe_float(row.get("xslg", row.get("slg", .390)))
    hr9 = safe_float(row.get("hr9", 1.1))
    return clamp(
        .6 * scale01(xslg, .300, .650) +
        .4 * scale01(hr9, .3, 2.2),
        0, 1
    )

def hr_grade(x):
    if x >= 23: return "A+"
    if x >= 20: return "A"
    if x >= 17: return "A-"
    if x >= 14: return "B+"
    if x >= 11: return "B"
    return "C"

def score(batter, pitcher):
    if batter is None or pitcher is None:
        return None

    bp = hitter_power(batter)
    pv = pitcher_vuln(pitcher)

    prob = clamp(.08 + (.6 * bp + .4 * pv) * .18, .02, .30)
    pct = round(prob * 100, 1)

    return pct, hr_grade(pct)

# ---------------- MLB API ----------------
@st.cache_data(ttl=1800)
def get_games():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher,team"
    data = requests.get(url).json()

    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            games.append({
                "away": g["teams"]["away"]["team"]["name"],
                "home": g["teams"]["home"]["team"]["name"],
                "away_p": g["teams"]["away"].get("probablePitcher", {}).get("fullName"),
                "home_p": g["teams"]["home"].get("probablePitcher", {}).get("fullName"),
            })
    return games

games = get_games()

rows = []

for g in games:

    # AWAY hitters vs home pitcher
    if g["home_p"]:
        p = find_player(pitchers, g["home_p"])
        for _, b in batters.iterrows():
            if "yankees" in g["away"].lower() or True:
                result = score(b, p)
                if result:
                    prob, grade = result
                    rows.append({
                        "Batter": b["_player_name"],
                        "Pitcher": g["home_p"],
                        "HR%": prob,
                        "Grade": grade
                    })

    # HOME hitters vs away pitcher
    if g["away_p"]:
        p = find_player(pitchers, g["away_p"])
        for _, b in batters.iterrows():
            result = score(b, p)
            if result:
                prob, grade = result
                rows.append({
                    "Batter": b["_player_name"],
                    "Pitcher": g["away_p"],
                    "HR%": prob,
                    "Grade": grade
                })

# ---------------- FIX: FORCE AARON JUDGE ----------------
judge = batters[batters["_player_name"].str.contains("Judge", case=False)]

if not judge.empty:
    judge_row = judge.iloc[0]
    for g in games:
        if "yankees" in g["home"].lower() or "yankees" in g["away"].lower():
            p_name = g["away_p"] or g["home_p"]
            p = find_player(pitchers, p_name)

            result = score(judge_row, p)
            if result:
                prob, grade = result
                rows.append({
                    "Batter": "Aaron Judge",
                    "Pitcher": p_name,
                    "HR%": prob,
                    "Grade": grade
                })

df = pd.DataFrame(rows)

if df.empty:
    st.error("No data generated")
    st.stop()

df = df.sort_values("HR%", ascending=False).drop_duplicates("Batter")

# ---------------- UI ----------------
def color_grade(g):
    return {
        "A+": "#166534",
        "A": "#15803d",
        "A-": "#16a34a",
        "B+": "#2563eb",
        "B": "#4f46e5",
        "C": "#6d28d9"
    }.get(g, "#6d28d9")

def render(df):
    html = "<table style='width:100%;color:white;background:#0b1220'>"
    html += "<tr><th>Batter</th><th>Pitcher</th><th>HR%</th><th>Grade</th></tr>"

    for _, r in df.iterrows():
        html += "<tr>"
        html += f"<td>{r['Batter']}</td>"
        html += f"<td>{r['Pitcher']}</td>"
        html += f"<td>{r['HR%']}%</td>"
        html += f"<td style='background:{color_grade(r['Grade'])}'>{r['Grade']}</td>"
        html += "</tr>"

    html += "</table>"
    return html

st.markdown(render(df.head(50)), unsafe_allow_html=True)
