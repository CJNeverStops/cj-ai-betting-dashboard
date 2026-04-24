import math
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="CJ MLB A.I. Model", layout="wide")

# =========================
# STYLE
# =========================
st.markdown("""
<style>
.stApp { background:#070b14; color:white; }
.block-container { max-width:1800px; padding-top:1rem; }
.hero {
    background:linear-gradient(135deg,#3b171b,#111827);
    border:1px solid rgba(249,115,22,.35);
    border-radius:24px;
    padding:24px;
    margin-bottom:18px;
}
.hero h1 { font-size:44px; font-weight:900; margin:0; }
.hero p { color:#cbd5e1; margin-top:8px; }
.table-wrap { overflow-x:auto; border:1px solid #1f2937; border-radius:18px; }
.ai-table { width:100%; border-collapse:collapse; background:#0b1220; color:white; font-size:14px; }
.ai-table th { background:#111827; padding:11px; text-align:left; white-space:nowrap; }
.ai-table td { padding:10px; border-bottom:1px solid rgba(255,255,255,.08); white-space:nowrap; }
.reason { white-space:normal; min-width:420px; color:#cbd5e1; font-size:13px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>🔥 CJ MLB A.I. Live Model</h1>
<p>HR • Hits • Strikeouts • Total Bases • RBIs • Lasers • Winner Probability • Weather • Hot/Slump Form</p>
</div>
""", unsafe_allow_html=True)

# =========================
# HELPERS
# =========================
def scale01(x, low, high):
    try:
        x = float(x)
    except Exception:
        x = low
    if high <= low:
        return 0.5
    return max(0.0, min(1.0, (x - low) / (high - low)))

def clamp(x, low, high):
    return max(low, min(high, x))

def safe_float(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default

def pct(x, default):
    v = safe_float(x, default)
    return v / 100 if v > 1 else v

def norm(x):
    return " ".join(str(x).lower().replace(",", "").strip().split())

def first_last(x):
    x = str(x).strip()
    if "," in x:
        last, first = [p.strip() for p in x.split(",", 1)]
        return f"{first} {last}".strip()
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

    c = find_col(df, ["last_name, first_name", "last_name_first_name"])
    if c:
        return df[c].astype(str).apply(first_last)

    first = find_col(df, ["first_name"])
    last = find_col(df, ["last_name"])
    if first and last:
        return (df[first].astype(str).str.strip() + " " + df[last].astype(str).str.strip()).str.strip()

    st.error(f"Could not find player name column. Found: {list(df.columns)}")
    st.stop()

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
    return hits.iloc[0] if not hits.empty else None

def fair_odds(prob):
    if prob <= 0 or prob >= 1:
        return "N/A"
    if prob >= 0.5:
        return int(round(-(prob / (1 - prob)) * 100))
    return int(round(((1 - prob) / prob) * 100))

def normalize_team(t):
    t = norm(t)
    teams = {
        "new york yankees":"NYY","yankees":"NYY","nyy":"NYY",
        "boston red sox":"BOS","red sox":"BOS","bos":"BOS",
        "los angeles dodgers":"LAD","dodgers":"LAD","lad":"LAD",
        "new york mets":"NYM","mets":"NYM","nym":"NYM",
        "atlanta braves":"ATL","braves":"ATL","atl":"ATL",
        "philadelphia phillies":"PHI","phillies":"PHI","phi":"PHI",
        "chicago cubs":"CHC","cubs":"CHC","chc":"CHC",
        "chicago white sox":"CWS","white sox":"CWS","cws":"CWS",
        "houston astros":"HOU","astros":"HOU","hou":"HOU",
        "texas rangers":"TEX","rangers":"TEX","tex":"TEX",
        "san francisco giants":"SF","giants":"SF","sf":"SF",
        "san diego padres":"SD","padres":"SD","sd":"SD",
        "milwaukee brewers":"MIL","brewers":"MIL","mil":"MIL",
        "detroit tigers":"DET","tigers":"DET","det":"DET",
        "minnesota twins":"MIN","twins":"MIN","min":"MIN",
        "pittsburgh pirates":"PIT","pirates":"PIT","pit":"PIT",
        "washington nationals":"WSH","nationals":"WSH","wsh":"WSH",
        "arizona diamondbacks":"ARI","diamondbacks":"ARI","ari":"ARI",
        "colorado rockies":"COL","rockies":"COL","col":"COL",
        "cleveland guardians":"CLE","guardians":"CLE","cle":"CLE",
        "kansas city royals":"KC","royals":"KC","kc":"KC",
        "toronto blue jays":"TOR","blue jays":"TOR","tor":"TOR",
        "seattle mariners":"SEA","mariners":"SEA","sea":"SEA",
        "tampa bay rays":"TB","rays":"TB","tb":"TB",
        "miami marlins":"MIA","marlins":"MIA","mia":"MIA",
        "cincinnati reds":"CIN","reds":"CIN","cin":"CIN",
        "baltimore orioles":"BAL","orioles":"BAL","bal":"BAL",
        "los angeles angels":"LAA","angels":"LAA","laa":"LAA",
        "oakland athletics":"OAK","athletics":"OAK","oak":"OAK",
        "athletics":"OAK",
    }
    return teams.get(t, str(t).upper()[:3])

# =========================
# LOAD CSV FILES
# =========================
try:
    batters = pd.read_csv("batters.csv")
    pitchers = pd.read_csv("pitchers.csv")
    parks = pd.read_csv("parks.csv")
except Exception as e:
    st.error(f"CSV load error: {e}")
    st.stop()

batters["_player_name"] = build_name(batters)
pitchers["_player_name"] = build_name(pitchers)

# columns
b_xslg = find_col(batters, ["est_slg", "xslg", "slg"])
b_xwoba = find_col(batters, ["est_woba", "xwoba", "woba"])
b_xba = find_col(batters, ["est_ba", "xba", "ba"])
b_barrel = find_col(batters, ["barrel", "barrel_pct", "brl"])
b_hard = find_col(batters, ["hard_hit", "hardhit", "hard_hit_pct"])
b_k = find_col(batters, ["k_percent", "k%", "strikeout"])
b_pa = find_col(batters, ["pa"])

p_xslg = find_col(pitchers, ["est_slg", "xslg", "slg"])
p_xwoba = find_col(pitchers, ["est_woba", "xwoba", "woba"])
p_xba = find_col(pitchers, ["est_ba", "xba", "ba"])
p_barrel = find_col(pitchers, ["barrel", "barrel_pct", "brl"])
p_hard = find_col(pitchers, ["hard_hit", "hardhit", "hard_hit_pct"])
p_k = find_col(pitchers, ["k_percent", "k%", "strikeout"])
p_hr9 = find_col(pitchers, ["hr_per_9", "hr9", "hr/9"])

park_col = find_col(parks, ["park_name", "venue_name", "park", "venue"])
park_hr_col = find_col(parks, ["hr_factor", "home_run", "hr"])
park_hit_col = find_col(parks, ["hit_factor", "hits", "hit"])
parks["_park"] = parks[park_col].astype(str).str.lower().str.strip() if park_col else ""

# =========================
# API DATA
# =========================
@st.cache_data(ttl=1800)
def get_schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher,team"
    try:
        data = requests.get(url, timeout=20).json()
    except Exception:
        return []

    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            try:
                games.append({
                    "gamePk": g["gamePk"],
                    "away": g["teams"]["away"]["team"]["name"],
                    "home": g["teams"]["home"]["team"]["name"],
                    "away_p": g["teams"]["away"].get("probablePitcher", {}).get("fullName", ""),
                    "home_p": g["teams"]["home"].get("probablePitcher", {}).get("fullName", ""),
                    "park": g["venue"]["name"],
                    "time": g.get("gameDate", "")
                })
            except Exception:
                pass
    return games

@st.cache_data(ttl=900)
def get_lineups(game_pk):
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    try:
        data = requests.get(url, timeout=20).json()
    except Exception:
        return {"away": [], "home": []}

    def side(which):
        box = data.get("liveData", {}).get("boxscore", {}).get("teams", {}).get(which, {})
        order = box.get("battingOrder", []) or []
        players = box.get("players", {}) or {}
        out = []
        for idx, pid in enumerate(order, 1):
            p = players.get(f"ID{pid}", {})
            name = p.get("person", {}).get("fullName", "")
            hand = p.get("batSide", {}).get("code", "")
            if name:
                out.append({"name": name, "order": idx, "hand": hand})
        return out

    return {"away": side("away"), "home": side("home")}

@st.cache_data(ttl=86400)
def roster_map():
    out = {}
    try:
        teams = requests.get("https://statsapi.mlb.com/api/v1/teams?sportId=1", timeout=20).json().get("teams", [])
    except Exception:
        return out

    for t in teams:
        tid = t.get("id")
        abbr = normalize_team(t.get("abbreviation", ""))
        try:
            roster = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{tid}/roster", timeout=20).json().get("roster", [])
            for p in roster:
                name = p["person"]["fullName"]
                out[norm(name)] = abbr
                out[norm(first_last(name))] = abbr
        except Exception:
            pass
    return out

games = get_schedule()
schedule_df = pd.DataFrame(games)
team_map = roster_map()
batters["_team"] = batters["_player_name"].apply(lambda x: team_map.get(norm(x), ""))

# =========================
# WEATHER
# =========================
def park_city(park):
    p = norm(park)
    mapping = {
        "yankee stadium": ("Bronx", "NY"),
        "fenway park": ("Boston", "MA"),
        "wrigley field": ("Chicago", "IL"),
        "dodger stadium": ("Los Angeles", "CA"),
        "coors field": ("Denver", "CO"),
        "citizens bank park": ("Philadelphia", "PA"),
        "great american ball park": ("Cincinnati", "OH"),
        "oriole park at camden yards": ("Baltimore", "MD"),
        "truist park": ("Atlanta", "GA"),
        "citi field": ("Queens", "NY"),
        "globe life field": ("Arlington", "TX"),
        "oracle park": ("San Francisco", "CA"),
        "petco park": ("San Diego", "CA"),
        "pnc park": ("Pittsburgh", "PA"),
        "nationals park": ("Washington", "DC"),
        "target field": ("Minneapolis", "MN"),
        "comerica park": ("Detroit", "MI"),
        "busch stadium": ("St. Louis", "MO"),
        "kauffman stadium": ("Kansas City", "MO"),
        "t-mobile park": ("Seattle", "WA"),
        "progressive field": ("Cleveland", "OH"),
        "chase field": ("Phoenix", "AZ"),
    }
    return mapping.get(p, ("", ""))

@st.cache_data(ttl=1800)
def get_weather(city, state):
    if not city:
        return {"temp": 70, "wind": 7, "desc": "Unknown", "impact": "Neutral", "mult": 1.0}
    try:
        q = f"{city},{state}".replace(" ", "%20")
        data = requests.get(f"https://wttr.in/{q}?format=j1", timeout=15).json()
        cur = data["current_condition"][0]
        temp = safe_float(cur.get("temp_F"), 70)
        wind = safe_float(cur.get("windspeedMiles"), 7)
        desc = cur.get("weatherDesc", [{}])[0].get("value", "Clear")
    except Exception:
        temp, wind, desc = 70, 7, "Unknown"

    raw = 1.0 + ((temp - 70) * .004) + (wind * .004)
    if "rain" in desc.lower() or "storm" in desc.lower():
        raw -= .06

    mult = clamp(raw, .88, 1.18)
    impact = "Good" if mult >= 1.04 else "Bad" if mult <= .97 else "Neutral"
    return {"temp": temp, "wind": wind, "desc": desc, "impact": impact, "mult": mult}

# =========================
# MODEL
# =========================
def park_factor(park, kind="hr"):
    if not park_col:
        return 1.0
    r = parks[parks["_park"] == str(park).lower().strip()]
    if r.empty:
        return 1.0
    col = park_hr_col if kind == "hr" else park_hit_col
    if not col:
        return 1.0
    v = safe_float(r.iloc[0][col], 1.0)
    return v / 100 if v > 3 else v

def batter_metrics(row):
    xslg = safe_float(row[b_xslg], .390) if b_xslg else .390
    xwoba = safe_float(row[b_xwoba], .310) if b_xwoba else .310
    xba = safe_float(row[b_xba], .245) if b_xba else .245
    barrel = pct(row[b_barrel], .08) if b_barrel else .08
    hard = pct(row[b_hard], .38) if b_hard else .38
    k_rate = pct(row[b_k], .22) if b_k else .22
    pa = safe_float(row[b_pa], 250) if b_pa else 250

    power = clamp(
        .34 * scale01(xslg, .300, .750) +
        .24 * scale01(barrel, .02, .25) +
        .18 * scale01(hard, .20, .65) +
        .14 * scale01(xwoba, .250, .460) +
        .10 * scale01(pa, 50, 650),
        0, 1
    )

    contact = clamp(
        .38 * scale01(xba, .190, .330) +
        .28 * scale01(xwoba, .250, .460) +
        .20 * (1 - scale01(k_rate, .12, .34)) +
        .14 * scale01(hard, .20, .65),
        0, 1
    )

    laser = clamp(
        .50 * scale01(hard, .20, .65) +
        .30 * scale01(barrel, .02, .25) +
        .20 * scale01(xslg, .300, .750),
        0, 1
    )

    form = "Hot" if power >= .72 or contact >= .72 else "Good" if power >= .50 or contact >= .50 else "Slump"
    return {"power": power, "contact": contact, "laser": laser, "form": form}

def pitcher_metrics(row):
    xslg = safe_float(row[p_xslg], .390) if p_xslg else .390
    xwoba = safe_float(row[p_xwoba], .310) if p_xwoba else .310
    xba = safe_float(row[p_xba], .245) if p_xba else .245
    barrel = pct(row[p_barrel], .08) if p_barrel else .08
    hard = pct(row[p_hard], .38) if p_hard else .38
    k_rate = pct(row[p_k], .22) if p_k else .22
    hr9 = safe_float(row[p_hr9], 1.05) if p_hr9 else 1.05

    vuln = clamp(
        .28 * scale01(xslg, .300, .650) +
        .22 * scale01(xwoba, .250, .430) +
        .18 * scale01(barrel, .02, .18) +
        .14 * scale01(hard, .20, .60) +
        .18 * scale01(hr9, .30, 2.20),
        0, 1
    )

    hit_vuln = clamp(
        .40 * scale01(xba, .190, .330) +
        .30 * scale01(xwoba, .250, .430) +
        .20 * scale01(hard, .20, .60) +
        .10 * (1 - scale01(k_rate, .15, .35)),
        0, 1
    )

    return {"vuln": vuln, "hit_vuln": hit_vuln, "k_rate": k_rate}

def grade(prob):
    if prob >= 24: return "A+"
    if prob >= 20: return "A"
    if prob >= 17: return "A-"
    if prob >= 14: return "B"
    if prob >= 10: return "C"
    return "D"

def score_player(batter_name, pitcher_name, team, opp, park, matchup, weather, order="—", lineup="Projected"):
    b = find_player(batters, batter_name)
    p = find_player(pitchers, pitcher_name)
    if b is None or p is None:
        return None

    bm = batter_metrics(b)
    pm = pitcher_metrics(p)
    hr_pf = park_factor(park, "hr")
    hit_pf = park_factor(park, "hit")
    wx = weather.get("mult", 1.0)

    hr_raw = (.38 * bm["power"]) + (.27 * pm["vuln"]) + (.15 * bm["laser"]) + (.10 * scale01(hr_pf, .80, 1.25)) + (.10 * scale01(wx, .90, 1.18))
    hr_prob = clamp(.06 + hr_raw * .22, .015, .34)

    hit_raw = (.45 * bm["contact"]) + (.30 * pm["hit_vuln"]) + (.15 * scale01(hit_pf, .85, 1.18)) + (.10 * scale01(wx, .90, 1.12))
    hit_prob = clamp(.28 + hit_raw * .44, .18, .82)

    tb_raw = (.38 * bm["power"]) + (.30 * bm["contact"]) + (.20 * pm["vuln"]) + (.12 * scale01(hit_pf, .85, 1.18))
    tb_prob = clamp(.20 + tb_raw * .48, .10, .76)

    order_num = order if isinstance(order, int) else 5
    rbi_raw = (.40 * bm["power"]) + (.24 * pm["vuln"]) + (.18 * (1 - scale01(order_num, 1, 9))) + (.18 * scale01(wx, .90, 1.12))
    rbi_prob = clamp(.12 + rbi_raw * .42, .06, .62)

    laser_prob = clamp(.15 + bm["laser"] * .58 + pm["vuln"] * .12, .10, .82)

    reasons = [
        f"{bm['form']} hitter",
        f"{weather['impact']} weather",
        f"{weather['temp']}°F",
        f"{weather['wind']} mph wind"
    ]
    if bm["power"] >= .70: reasons.append("strong power")
    if bm["contact"] >= .65: reasons.append("strong contact")
    if bm["laser"] >= .70: reasons.append("high hard-hit/laser")
    if pm["vuln"] >= .60: reasons.append("pitcher vulnerable")

    return {
        "Matchup": matchup,
        "Player": "Aaron Judge" if player_match(batter_name, "Aaron Judge") else batter_name,
        "Team": normalize_team(team),
        "Pitcher": pitcher_name,
        "Opp": normalize_team(opp),
        "Lineup": lineup,
        "Order": order,
        "Form": bm["form"],
        "Weather": weather["impact"],
        "HR %": round(hr_prob * 100, 1),
        "Hit %": round(hit_prob * 100, 1),
        "TB %": round(tb_prob * 100, 1),
        "RBI %": round(rbi_prob * 100, 1),
        "Laser %": round(laser_prob * 100, 1),
        "Grade": grade(round(hr_prob * 100, 1)),
        "HR Fair Odds": fair_odds(hr_prob),
        "Power": round(bm["power"], 2),
        "Contact": round(bm["contact"], 2),
        "Pitcher Vuln": round(pm["vuln"], 2),
        "Reasons": " • ".join(reasons),
    }

# =========================
# BUILD PLAYER MODEL
# =========================
rows = []

for g in games:
    matchup = f'{g["away"]} @ {g["home"]}'
    city, state = park_city(g["park"])
    weather = get_weather(city, state)
    lu = get_lineups(g["gamePk"])

    if g["home_p"]:
        if lu["away"]:
            for h in lu["away"]:
                r = score_player(h["name"], g["home_p"], g["away"], g["home"], g["park"], matchup, weather, h["order"], "Final")
                if r: rows.append(r)
        else:
            team = normalize_team(g["away"])
            for _, b in batters[batters["_team"] == team].iterrows():
                r = score_player(b["_player_name"], g["home_p"], g["away"], g["home"], g["park"], matchup, weather)
                if r: rows.append(r)

    if g["away_p"]:
        if lu["home"]:
            for h in lu["home"]:
                r = score_player(h["name"], g["away_p"], g["home"], g["away"], g["park"], matchup, weather, h["order"], "Final")
                if r: rows.append(r)
        else:
            team = normalize_team(g["home"])
            for _, b in batters[batters["_team"] == team].iterrows():
                r = score_player(b["_player_name"], g["away_p"], g["home"], g["away"], g["park"], matchup, weather)
                if r: rows.append(r)

    # Judge safety injection
    if normalize_team(g["away"]) == "NYY" and g["home_p"]:
        r = score_player("Aaron Judge", g["home_p"], g["away"], g["home"], g["park"], matchup, weather)
        if r and not any(player_match(x["Player"], "Aaron Judge") and x["Matchup"] == matchup for x in rows):
            rows.append(r)

    if normalize_team(g["home"]) == "NYY" and g["away_p"]:
        r = score_player("Aaron Judge", g["away_p"], g["home"], g["away"], g["park"], matchup, weather)
        if r and not any(player_match(x["Player"], "Aaron Judge") and x["Matchup"] == matchup for x in rows):
            rows.append(r)

df = pd.DataFrame(rows)

if df.empty:
    st.error("No model rows created. Check lineups, probable pitchers, and CSV names.")
    st.stop()

# =========================
# PITCHER STRIKEOUT MODEL
# =========================
pitcher_rows = []

for g in games:
    for p_name, opp in [(g["away_p"], g["home"]), (g["home_p"], g["away"])]:
        p = find_player(pitchers, p_name)
        if p is None:
            continue
        pm = pitcher_metrics(p)
        proj_ks = clamp(4.2 + (pm["k_rate"] - .22) * 18, 2.5, 9.5)

        def over_prob(line):
            return clamp(1 / (1 + math.exp(-(proj_ks - line))), .05, .92)

        pitcher_rows.append({
            "Pitcher": p_name,
            "Opponent": normalize_team(opp),
            "Projected Ks": round(proj_ks, 1),
            "Over 4.5 K%": round(over_prob(4.5) * 100, 1),
            "Over 5.5 K%": round(over_prob(5.5) * 100, 1),
            "Over 6.5 K%": round(over_prob(6.5) * 100, 1),
            "Reason": "High K profile" if pm["k_rate"] >= .26 else "Average K profile" if pm["k_rate"] >= .21 else "Low K profile"
        })

pitcher_df = pd.DataFrame(pitcher_rows)

# =========================
# WINNER MODEL
# =========================
winner_rows = []

for matchup, grp in df.groupby("Matchup"):
    teams = grp["Team"].dropna().unique().tolist()
    if len(teams) < 2:
        continue

    scores = {}
    for t in teams:
        tg = grp[grp["Team"] == t]
        scores[t] = (
            tg["Hit %"].mean() * .30 +
            tg["TB %"].mean() * .25 +
            tg["RBI %"].mean() * .20 +
            tg["HR %"].mean() * .25
        )

    t1, t2 = teams[0], teams[1]
    s1, s2 = scores[t1], scores[t2]
    p1 = clamp(.50 + ((s1 - s2) / 100), .35, .65)
    p2 = 1 - p1

    winner_rows.append({
        "Matchup": matchup,
        "Projected Winner": t1 if p1 >= p2 else t2,
        f"{t1} Win %": round(p1 * 100, 1),
        f"{t2} Win %": round(p2 * 100, 1),
        "Reason": "Better combined HR/contact/RBI profile from listed lineup"
    })

winner_df = pd.DataFrame(winner_rows)

# =========================
# FILTERS
# =========================
with st.sidebar:
    st.header("Filters")
    search = st.text_input("Search Player")
    min_hr = st.slider("Minimum HR %", 0.0, 40.0, 0.0, 0.5)
    sort_by = st.selectbox("Sort By", ["HR %", "Hit %", "TB %", "RBI %", "Laser %"])

filtered = df[df["HR %"] >= min_hr].copy()
if search:
    filtered = filtered[filtered["Player"].str.contains(search, case=False, na=False)]
filtered = filtered.sort_values(sort_by, ascending=False)

# =========================
# TABLE RENDER
# =========================
def grade_color(g):
    return {"A+":"#166534","A":"#15803d","A-":"#16a34a","B":"#2563eb","C":"#6d28d9","D":"#7f1d1d"}.get(g, "#6d28d9")

def render_table(data):
    cols = ["Player", "Team", "Grade", "HR %", "Hit %", "TB %", "RBI %", "Laser %", "Form", "Weather", "Pitcher", "Opp", "Lineup", "Order", "HR Fair Odds", "Reasons"]

    html = "<div class='table-wrap'><table class='ai-table'><thead><tr>"
    for c in cols:
        html += f"<th>{c}</th>"
    html += "</tr></thead><tbody>"

    for _, r in data.iterrows():
        html += "<tr>"
        for c in cols:
            v = r.get(c, "")
            style = ""

            if c == "Grade":
                style = f"background:{grade_color(v)};font-weight:900;text-align:center;"
            elif c in ["HR %", "Hit %", "TB %", "RBI %", "Laser %"]:
                fv = safe_float(v)
                if fv >= 60:
                    style = "background:rgba(34,197,94,.30);"
                elif fv >= 35:
                    style = "background:rgba(234,179,8,.18);"
                else:
                    style = "background:rgba(239,68,68,.16);"
            elif c == "Form":
                style = "color:#86efac;font-weight:900;" if v == "Hot" else "color:#93c5fd;font-weight:900;" if v == "Good" else "color:#fca5a5;font-weight:900;"
            elif c == "Weather":
                style = "color:#86efac;font-weight:900;" if v == "Good" else "color:#fca5a5;font-weight:900;" if v == "Bad" else "color:#fde68a;font-weight:900;"
            elif c == "Reasons":
                style = "white-space:normal;color:#cbd5e1;font-size:13px;min-width:420px;"

            html += f"<td style='{style}'>{v}</td>"
        html += "</tr>"

    html += "</tbody></table></div>"
    return html

# =========================
# UI
# =========================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔥 Best Picks", "📋 Full Player Model", "🎯 Strikeouts", "🏆 Winner Probability", "🛠️ Debug"])

with tab1:
    st.subheader("🔥 Best A.I. Rated Plays")
    st.markdown(render_table(filtered.head(35)), unsafe_allow_html=True)

with tab2:
    st.subheader("📋 Full Live Lineup Player Model")
    st.markdown(render_table(filtered), unsafe_allow_html=True)

with tab3:
    st.subheader("🎯 Pitcher Strikeout Model")
    st.dataframe(pitcher_df, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("🏆 Matchup Winner Probability")
    st.dataframe(winner_df, use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Debug")
    st.write("Games loaded:", len(games))
    st.write("Players scored:", len(df))
    st.write("Batters CSV rows:", len(batters))
    st.write("Pitchers CSV rows:", len(pitchers))
    st.write("Schedule:")
    st.dataframe(schedule_df, use_container_width=True)

    st.write("Aaron Judge check:")
    st.dataframe(df[df["Player"].str.contains("Judge", case=False, na=False)], use_container_width=True)
