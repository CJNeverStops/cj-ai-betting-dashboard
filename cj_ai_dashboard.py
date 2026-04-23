import math
from datetime import datetime
import pandas as pd
import requests
import streamlit as st
st.set_page_config(page_title="CJ HR AI Board", layout="wide")
def scale01(x, low, high):
    try:
        x = float(x)
    except Exception:
        x = low
    if high <= low:
        return 0.5
    return max(0.0, min(1.0, (x - low) / (high - low)))
def scale01(x, low, high):
    try:
        x = float(x)
    except Exception:
        x = low

    if high <= low:
        return 0.5

    return max(0.0, min(1.0, (x - low) / (high - low)))
st.title("🔥 CJ HR AI Board")

# ---------------- HELPERS ----------------
def scale01(x, low, high):
    try:
        x = float(x)
    except Exception:
        x = low
    if high <= low:
        return 0.5
    return max(0.0, min(1.0, (x - low) / (high - low)))

def safe_float(x, d=0.0):
    try:
        if pd.isna(x):
            return d
        return float(x)
    except Exception:
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
    c = find_col(df, ["player_name", "name", "player"])
    if c:
        return df[c].astype(str)

    c = find_col(df, ["last_name, first_name"])
    if c:
        return df[c].astype(str).apply(first_last)

    first = find_col(df, ["first_name"])
    last = find_col(df, ["last_name"])
    if first and last:
        return (df[first].astype(str).str.strip() + " " + df[last].astype(str).str.strip()).str.strip()

    st.error(f"Could not find player name column. Columns: {list(df.columns)}")
    st.stop()

def pct(x, d):
    v = safe_float(x, d)
    return v / 100 if v > 1 else v

def fair_odds(p):
    if p <= 0 or p >= 1:
        return "N/A"
    if p >= .5:
        return int(round(-(p / (1 - p)) * 100))
    return int(round(((1 - p) / p) * 100))

def player_match(a, b):
    a = norm(first_last(a))
    b = norm(first_last(b))
    if a == b:
        return True

    ap = a.split()
    bp = b.split()

    if len(ap) >= 2 and len(bp) >= 2:
        return ap[-1] == bp[-1] and ap[0][0] == bp[0][0]

    return False

def find_player(df, name):
    if not name:
        return None
    hits = df[df["_player_name"].apply(lambda x: player_match(x, name))]
    if hits.empty:
        return None
    return hits.iloc[0]

def normalize_team(t):
    t = norm(t)
    m = {
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
        "washington nationals": "wsh", "nationals": "wsh", "wsh": "wsh",
        "arizona diamondbacks": "ari", "diamondbacks": "ari", "ari": "ari",
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
        "oakland athletics": "oak", "athletics": "oak", "oak": "oak",
        "athletics": "oak",
    }
    return m.get(t, t)

# ---------------- LOAD CSV ----------------
try:
    batters = pd.read_csv("batters.csv")
    pitchers = pd.read_csv("pitchers.csv")
    parks = pd.read_csv("parks.csv")
except Exception as e:
    st.error(f"CSV load error: {e}")
    st.stop()

batters["_player_name"] = build_name(batters)
pitchers["_player_name"] = build_name(pitchers)

b_xslg = find_col(batters, ["est_slg", "xslg", "slg"])
b_xwoba = find_col(batters, ["est_woba", "xwoba", "woba"])
b_xba = find_col(batters, ["est_ba", "xba", "ba"])
b_barrel = find_col(batters, ["barrel", "barrel_pct", "brl"])
b_hardhit = find_col(batters, ["hard_hit", "hardhit", "hard_hit_pct"])
b_pa = find_col(batters, ["pa"])

p_xslg = find_col(pitchers, ["est_slg", "xslg", "slg"])
p_xwoba = find_col(pitchers, ["est_woba", "xwoba", "woba"])
p_xba = find_col(pitchers, ["est_ba", "xba", "ba"])
p_barrel = find_col(pitchers, ["barrel", "barrel_pct", "brl"])
p_hardhit = find_col(pitchers, ["hard_hit", "hardhit", "hard_hit_pct"])
p_hr9 = find_col(pitchers, ["hr_per_9", "hr9", "hr/9"])

park_col = find_col(parks, ["park_name", "venue_name", "park", "venue"])
park_hr_col = find_col(parks, ["hr_factor", "home_run", "hr"])
park_hit_col = find_col(parks, ["hit_factor", "hits", "hit"])

if park_col:
    parks["_park"] = parks[park_col].astype(str).str.lower().str.strip()
else:
    parks["_park"] = ""

# ---------------- MLB API ----------------
@st.cache_data(ttl=1800)
def schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher,team"
    try:
        data = requests.get(url, timeout=20).json()
    except Exception:
        return []

    rows = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            try:
                rows.append({
                    "gamePk": g["gamePk"],
                    "away_team": g["teams"]["away"]["team"]["name"],
                    "home_team": g["teams"]["home"]["team"]["name"],
                    "away_pitcher": g["teams"]["away"].get("probablePitcher", {}).get("fullName", ""),
                    "home_pitcher": g["teams"]["home"].get("probablePitcher", {}).get("fullName", ""),
                    "park": g["venue"]["name"],
                    "game_time": g.get("gameDate", "")
                })
            except Exception:
                pass
    return rows

@st.cache_data(ttl=900)
def lineups(game_pk):
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    try:
        data = requests.get(url, timeout=20).json()
    except Exception:
        return {"away": [], "home": []}

    def side(which):
        out = []
        box = data.get("liveData", {}).get("boxscore", {}).get("teams", {}).get(which, {})
        order = box.get("battingOrder", []) or []
        players = box.get("players", {}) or {}

        for i, pid in enumerate(order, 1):
            p = players.get(f"ID{pid}", {})
            name = p.get("person", {}).get("fullName", "")
            hand = p.get("batSide", {}).get("code", "")
            if name:
                out.append({"name": name, "order": i, "hand": hand})
        return out

    return {"away": side("away"), "home": side("home")}

@st.cache_data(ttl=86400)
def roster_team_map():
    out = {}
    try:
        teams = requests.get("https://statsapi.mlb.com/api/v1/teams?sportId=1", timeout=20).json().get("teams", [])
    except Exception:
        return out

    for t in teams:
        abbr = normalize_team(t.get("abbreviation", ""))
        rid = t["id"]

        try:
            r = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{rid}/roster", timeout=20).json().get("roster", [])
            for p in r:
                name = p["person"]["fullName"]
                out[norm(name)] = abbr
                out[norm(first_last(name))] = abbr
        except Exception:
            pass

    return out

team_map = roster_team_map()
batters["_team"] = batters["_player_name"].apply(lambda x: team_map.get(norm(x), ""))

games = schedule()
schedule_df = pd.DataFrame(games)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("Filters")
    min_hr = st.slider("Minimum HR %", 0.0, 40.0, 0.0, 0.5)
    search = st.text_input("Search Player")

# ---------------- MODEL ----------------
def park_factor(park):
    if not park_col or not park_hr_col:
        return 1.0

    r = parks[parks["_park"] == str(park).lower().strip()]
    if r.empty:
        return 1.0

    v = safe_float(r.iloc[0][park_hr_col], 1.0)
    return v / 100 if v > 3 else v

def hitter_power(row):
    xslg = safe_float(row[b_xslg], .390) if b_xslg else .390
    barrel = pct(row[b_barrel], .08) if b_barrel else .08
    hard = pct(row[b_hardhit], .38) if b_hardhit else .38
    pa = safe_float(row[b_pa], 250) if b_pa else 250

    return clamp(
        .40 * scale01(xslg, .300, .750) +
        .30 * scale01(barrel, .02, .25) +
        .20 * scale01(hard, .20, .65) +
        .10 * scale01(pa, 50, 650),
        0, 1
    )

def pitcher_vuln(row):
    xslg = safe_float(row[p_xslg], .390) if p_xslg else .390
    barrel = pct(row[p_barrel], .08) if p_barrel else .08
    hard = pct(row[p_hardhit], .38) if p_hardhit else .38
    hr9 = safe_float(row[p_hr9], 1.05) if p_hr9 else 1.05

    return clamp(
        .35 * scale01(xslg, .300, .650) +
        .25 * scale01(barrel, .02, .18) +
        .20 * scale01(hard, .20, .60) +
        .20 * scale01(hr9, .30, 2.20),
        0, 1
    )

def hr_grade(x):
    if x >= 23: return "A+"
    if x >= 20: return "A"
    if x >= 17: return "A-"
    if x >= 14: return "B+"
    if x >= 11: return "B"
    return "C"

def score_row(batter_name, pitcher_name, team, opp, park, matchup, order="—", lineup="Projected"):
    b = find_player(batters, batter_name)
    p = find_player(pitchers, pitcher_name)

    if b is None or p is None:
        return None

    bp = hitter_power(b)
    pv = pitcher_vuln(p)
    pf = park_factor(park)

    context = clamp(.50 * scale01(pf, .80, 1.25) + .50 * .55, 0, 1)
    power_match = clamp(.55 * bp + .45 * pv, 0, 1)

    prob = clamp(.08 + (.38 * bp + .27 * pv + .20 * context + .15 * power_match) * .18, .02, .30)
    prob_pct = round(prob * 100, 1)
    fair = fair_odds(prob)

    return {
        "Matchup": matchup,
        "Batter": "Aaron Judge" if player_match(batter_name, "Aaron Judge") else batter_name,
        "Batter Team": normalize_team(team),
        "Grade": hr_grade(prob_pct),
        "HR Probability": f"{prob_pct}% ({fair:+d})" if isinstance(fair, int) else f"{prob_pct}% (N/A)",
        "HR Probability Value": prob_pct,
        "Recent Form": "Hot" if bp >= .72 else "Good" if bp >= .50 else "Average",
        "Pitcher": pitcher_name,
        "Pitcher Team": normalize_team(opp),
        "Batter Power": round(bp, 2),
        "Pitcher Vulnerability": round(pv, 2),
        "Context Score": round(context, 2),
        "Power Match": round(power_match, 2),
        "Game Status": "Scheduled",
        "Lineup": lineup,
        "Order": order,
        "EV": "N/A",
        "HR Odds": "N/A",
        "Park": park
    }

rows = []

for g in games:
    lu = lineups(g["gamePk"])
    matchup = f'{g["away_team"]} @ {g["home_team"]}'

    # Away hitters vs home pitcher
    if g["home_pitcher"]:
        if lu["away"]:
            for h in lu["away"]:
                r = score_row(h["name"], g["home_pitcher"], g["away_team"], g["home_team"], g["park"], matchup, h["order"], "Final")
                if r:
                    rows.append(r)
        else:
            team = normalize_team(g["away_team"])
            for _, b in batters[batters["_team"] == team].iterrows():
                r = score_row(b["_player_name"], g["home_pitcher"], g["away_team"], g["home_team"], g["park"], matchup)
                if r:
                    rows.append(r)

    # Home hitters vs away pitcher
    if g["away_pitcher"]:
        if lu["home"]:
            for h in lu["home"]:
                r = score_row(h["name"], g["away_pitcher"], g["home_team"], g["away_team"], g["park"], matchup, h["order"], "Final")
                if r:
                    rows.append(r)
        else:
            team = normalize_team(g["home_team"])
            for _, b in batters[batters["_team"] == team].iterrows():
                r = score_row(b["_player_name"], g["away_pitcher"], g["home_team"], g["away_team"], g["park"], matchup)
                if r:
                    rows.append(r)

    # Hard Judge injection only if Yankees play today
    if normalize_team(g["away_team"]) == "nyy" and g["home_pitcher"]:
        r = score_row("Aaron Judge", g["home_pitcher"], g["away_team"], g["home_team"], g["park"], matchup)
        if r and not any(player_match(x["Batter"], "Aaron Judge") for x in rows):
            rows.append(r)

    if normalize_team(g["home_team"]) == "nyy" and g["away_pitcher"]:
        r = score_row("Aaron Judge", g["away_pitcher"], g["home_team"], g["away_team"], g["park"], matchup)
        if r and not any(player_match(x["Batter"], "Aaron Judge") for x in rows):
            rows.append(r)

hr_df = pd.DataFrame(rows)

if hr_df.empty:
    st.error("No model rows created. Check if today has games and probable pitchers.")
    st.stop()

if search:
    hr_df = hr_df[hr_df["Batter"].str.contains(search, case=False, na=False)]

filtered = hr_df[hr_df["HR Probability Value"] >= min_hr].sort_values("HR Probability Value", ascending=False)

# ---------------- UI TABLE ----------------
def cell_class_grade(g):
    return {
        "A+": "#166534",
        "A": "#15803d",
        "A-": "#16a34a",
        "B+": "#2563eb",
        "B": "#4f46e5",
        "C": "#6d28d9"
    }.get(g, "#6d28d9")

def html_table(df):
    cols = [
        "Batter", "Batter Team", "Grade", "HR Probability", "Recent Form",
        "Pitcher", "Pitcher Team", "Batter Power", "Pitcher Vulnerability",
        "Context Score", "Power Match", "Game Status", "Lineup", "Order", "EV", "HR Odds"
    ]

    h = '<div style="overflow-x:auto;border:1px solid #1f2937;border-radius:18px">'
    h += '<table style="width:100%;border-collapse:collapse;background:#0b1220;color:white;font-size:14px">'
    h += "<tr>" + "".join([f"<th style='padding:11px;background:#111827;text-align:left;white-space:nowrap'>{c}</th>" for c in cols]) + "</tr>"

    for _, r in df.iterrows():
        h += "<tr>"
        for c in cols:
            v = r.get(c, "")
            style = "padding:10px;border-bottom:1px solid rgba(255,255,255,.08);white-space:nowrap;"

            if c == "Grade":
                style += f"background:{cell_class_grade(v)};font-weight:800;text-align:center;"
            if c in ["Batter Power", "Pitcher Vulnerability", "Context Score", "Power Match"]:
                style += "background:rgba(34,197,94,.20);"
            if c == "Recent Form":
                style += "font-weight:800;color:#86efac;"

            h += f"<td style='{style}'>{v}</td>"
        h += "</tr>"

    h += "</table></div>"
    return h

tab1, tab2, tab3 = st.tabs(["💣 HR Board", "🏟️ Games", "🛠️ Debug"])

with tab1:
    st.subheader("💣 MLB Home Run A.I. Board")
    st.markdown(html_table(filtered.head(100)), unsafe_allow_html=True)

with tab2:
    st.subheader("Today's Games")
    st.dataframe(schedule_df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Aaron Judge Debug")

    judge_csv = batters[batters["_player_name"].str.contains("Judge", case=False, na=False)]
    st.write("Judge in batters.csv")
    st.dataframe(judge_csv, use_container_width=True, hide_index=True)

    if not schedule_df.empty:
        yankees_games = schedule_df[
            schedule_df["away_team"].str.contains("Yankees", case=False, na=False) |
            schedule_df["home_team"].str.contains("Yankees", case=False, na=False)
        ]
    else:
        yankees_games = pd.DataFrame()

    st.write("Yankees games today")
    st.dataframe(yankees_games, use_container_width=True, hide_index=True)

    st.write("Judge in final model")
    st.dataframe(
        hr_df[hr_df["Batter"].str.contains("Judge", case=False, na=False)],
        use_container_width=True,
        hide_index=True
    )

    st.write("Filtered Judge")
    st.dataframe(
        filtered[filtered["Batter"].str.contains("Judge", case=False, na=False)],
        use_container_width=True,
        hide_index=True
    )

    if judge_csv.empty:
        st.error("Judge is not in batters.csv.")
    elif yankees_games.empty:
        st.warning("Judge is in batters.csv, but Yankees are not on today's schedule.")
    elif hr_df[hr_df["Batter"].str.contains("Judge", case=False, na=False)].empty:
        st.error("Yankees are on the slate, but Judge could not be scored. Most likely the opposing probable pitcher is missing or not matching pitchers.csv.")
    else:
        st.success("Judge is in the model. If you do not see him, lower Minimum HR % to 0 or search Judge.")
