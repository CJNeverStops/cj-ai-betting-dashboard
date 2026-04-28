import math
import itertools
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="CJ MLB ELITE AI", layout="wide")

st.markdown("""
<style>
.stApp { background:#050914; color:white; }
.hero { background:linear-gradient(135deg,#3b171b,#111827); padding:24px; border-radius:22px; margin-bottom:20px; }
.table-wrap { overflow-x:auto; border:1px solid #1f2937; border-radius:18px; margin-bottom:22px; }
.ai-table { width:100%; border-collapse:collapse; background:#0b1220; color:white; font-size:14px; }
.ai-table th { background:#111827; padding:11px; text-align:left; white-space:nowrap; }
.ai-table td { padding:10px; border-bottom:1px solid rgba(255,255,255,.08); white-space:nowrap; }
.note { background:#0b1220; border:1px solid #1f2937; border-radius:14px; padding:14px; color:#cbd5e1; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class='hero'>
<h1>🔥 CJ MLB ELITE AI MODEL</h1>
<p>Dinger Score 0-42 • HR • Hits • TB • RBI • Lasers • Live Pitcher K Stats • Better Hot/Cold Form • Top 5 Tiered 3-Leg Parlays</p>
</div>
""", unsafe_allow_html=True)

# =========================
# HELPERS
# =========================
def clamp(x, a, b):
    return max(a, min(b, x))

def safe_float(x, d=0.0):
    try:
        if pd.isna(x):
            return d
        return float(x)
    except Exception:
        return d

def scale01(x, a, b):
    try:
        x = float(x)
        if b == a:
            return 0.5
        return clamp((x - a) / (b - a), 0, 1)
    except Exception:
        return 0.5

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

def make_name(df):
    player_col = find_col(df, ["player_name", "name", "player"])
    if player_col:
        return df[player_col].astype(str).apply(first_last)

    first_col = find_col(df, ["first_name", "first"])
    last_col = find_col(df, ["last_name", "last"])

    if first_col and last_col:
        return (df[first_col].astype(str).str.strip() + " " + df[last_col].astype(str).str.strip()).str.strip()

    full_col = find_col(df, ["last_name, first_name", "last_name_first_name"])
    if full_col:
        return df[full_col].astype(str).apply(first_last)

    st.error(f"Could not find player name columns. Found columns: {list(df.columns)}")
    st.stop()

def normalize_team(t):
    t = norm(t)
    m = {
        "arizona diamondbacks":"ARI","diamondbacks":"ARI","ari":"ARI",
        "atlanta braves":"ATL","braves":"ATL","atl":"ATL",
        "baltimore orioles":"BAL","orioles":"BAL","bal":"BAL",
        "boston red sox":"BOS","red sox":"BOS","bos":"BOS",
        "chicago cubs":"CHC","cubs":"CHC","chc":"CHC",
        "chicago white sox":"CWS","white sox":"CWS","cws":"CWS",
        "cincinnati reds":"CIN","reds":"CIN","cin":"CIN",
        "cleveland guardians":"CLE","guardians":"CLE","cle":"CLE",
        "colorado rockies":"COL","rockies":"COL","col":"COL",
        "detroit tigers":"DET","tigers":"DET","det":"DET",
        "houston astros":"HOU","astros":"HOU","hou":"HOU",
        "kansas city royals":"KC","royals":"KC","kc":"KC",
        "los angeles angels":"LAA","angels":"LAA","laa":"LAA",
        "los angeles dodgers":"LAD","dodgers":"LAD","lad":"LAD",
        "miami marlins":"MIA","marlins":"MIA","mia":"MIA",
        "milwaukee brewers":"MIL","brewers":"MIL","mil":"MIL",
        "minnesota twins":"MIN","twins":"MIN","min":"MIN",
        "new york mets":"NYM","mets":"NYM","nym":"NYM",
        "new york yankees":"NYY","yankees":"NYY","nyy":"NYY",
        "oakland athletics":"OAK","athletics":"OAK","oak":"OAK",
        "philadelphia phillies":"PHI","phillies":"PHI","phi":"PHI",
        "pittsburgh pirates":"PIT","pirates":"PIT","pit":"PIT",
        "san diego padres":"SD","padres":"SD","sd":"SD",
        "san francisco giants":"SF","giants":"SF","sf":"SF",
        "seattle mariners":"SEA","mariners":"SEA","sea":"SEA",
        "st louis cardinals":"STL","st. louis cardinals":"STL","cardinals":"STL","stl":"STL",
        "tampa bay rays":"TB","rays":"TB","tb":"TB",
        "texas rangers":"TEX","rangers":"TEX","tex":"TEX",
        "toronto blue jays":"TOR","blue jays":"TOR","tor":"TOR",
        "washington nationals":"WSH","nationals":"WSH","wsh":"WSH",
    }
    return m.get(t, str(t).upper()[:3])

def player_match(a, b):
    a = norm(first_last(a))
    b = norm(first_last(b))
    if a == b:
        return True
    ap = a.split()
    bp = b.split()
    return len(ap) >= 2 and len(bp) >= 2 and ap[-1] == bp[-1] and ap[0][0] == bp[0][0]

def find_player(df, name):
    if not name:
        return None
    hits = df[df["_name"].apply(lambda x: player_match(x, name))]
    return hits.iloc[0] if not hits.empty else None

def pct_value(row, col, default):
    if not col:
        return default
    v = safe_float(row[col], default)
    return v / 100 if v > 1 else v

def grade_score(s):
    if s >= 26: return "A+"
    if s >= 22: return "A"
    if s >= 18: return "A-"
    if s >= 15: return "B"
    if s >= 12: return "C"
    return "D"

def badge_score(s):
    if s >= 26: return "🔥 Elite"
    if s >= 22: return "💎 Great"
    if s >= 18: return "✅ Good"
    if s >= 15: return "🟡 Solid"
    return "⚪ Lean"

def fair_odds(p):
    if p <= 0 or p >= 1:
        return "N/A"
    if p >= .5:
        return int(round(-(p / (1 - p)) * 100))
    return int(round(((1 - p) / p) * 100))

# =========================
# LOAD CSV
# =========================
try:
    batters = pd.read_csv("batters.csv")
    pitchers = pd.read_csv("pitchers.csv")
except Exception as e:
    st.error(f"CSV load error: {e}")
    st.stop()

batters["_name"] = make_name(batters)
pitchers["_name"] = make_name(pitchers)

# Batter columns
b_xslg = find_col(batters, ["est_slg", "xslg", "slg"])
b_xwoba = find_col(batters, ["est_woba", "xwoba", "woba"])
b_xba = find_col(batters, ["est_ba", "xba", "ba"])
b_barrel = find_col(batters, ["barrel", "barrel_pct", "brl"])
b_hard = find_col(batters, ["hard_hit", "hardhit", "hard_hit_pct"])
b_k = find_col(batters, ["k_percent", "k%", "strikeout"])
b_pa = find_col(batters, ["pa"])
b_iso = find_col(batters, ["iso"])
b_recent = find_col(batters, ["last7", "last14", "recent", "recent_form"])

# =========================
# MLB API
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
            games.append({
                "gamePk": g.get("gamePk"),
                "away": g["teams"]["away"]["team"]["name"],
                "home": g["teams"]["home"]["team"]["name"],
                "away_p": g["teams"]["away"].get("probablePitcher", {}).get("fullName", ""),
                "home_p": g["teams"]["home"].get("probablePitcher", {}).get("fullName", ""),
                "away_p_id": g["teams"]["away"].get("probablePitcher", {}).get("id", None),
                "home_p_id": g["teams"]["home"].get("probablePitcher", {}).get("id", None),
                "park": g.get("venue", {}).get("name", ""),
                "time": g.get("gameDate", "")
            })
    return games

@st.cache_data(ttl=900)
def get_lineups(game_pk):
    try:
        data = requests.get(f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live", timeout=20).json()
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
            if name:
                out.append({"name": name, "order": idx})
        return out

    return {"away": side("away"), "home": side("home")}

@st.cache_data(ttl=86400)
def build_roster():
    out = []
    try:
        teams = requests.get("https://statsapi.mlb.com/api/v1/teams?sportId=1", timeout=20).json().get("teams", [])
    except Exception:
        return pd.DataFrame(columns=["name", "team"])

    for t in teams:
        tid = t.get("id")
        team = normalize_team(t.get("name", ""))
        try:
            roster = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{tid}/roster", timeout=20).json().get("roster", [])
        except Exception:
            roster = []
        for p in roster:
            name = p.get("person", {}).get("fullName", "")
            if name:
                out.append({"name": name, "team": team, "_norm": norm(name)})
    return pd.DataFrame(out)

@st.cache_data(ttl=3600)
def pitcher_live(pid):
    if not pid:
        return {"k_rate": .22, "k9": 8.0, "era": 4.20, "whip": 1.30, "hr9": 1.10}

    try:
        season = datetime.now().year
        url = f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=season&group=pitching&season={season}"
        data = requests.get(url, timeout=20).json()
        splits = data.get("stats", [{}])[0].get("splits", [])
        if not splits:
            return {"k_rate": .22, "k9": 8.0, "era": 4.20, "whip": 1.30, "hr9": 1.10}

        s = splits[0].get("stat", {})
        ip = safe_float(s.get("inningsPitched", 0))
        so = safe_float(s.get("strikeOuts", 0))
        bf = safe_float(s.get("battersFaced", 0))
        hr = safe_float(s.get("homeRuns", 0))

        return {
            "k_rate": so / bf if bf > 0 else .22,
            "k9": (so / ip) * 9 if ip > 0 else 8.0,
            "era": safe_float(s.get("era", 4.20)),
            "whip": safe_float(s.get("whip", 1.30)),
            "hr9": (hr / ip) * 9 if ip > 0 else 1.10,
        }
    except Exception:
        return {"k_rate": .22, "k9": 8.0, "era": 4.20, "whip": 1.30, "hr9": 1.10}

games = get_schedule()
roster = build_roster()

team_col = find_col(batters, ["team", "player_team", "bat_team", "batter_team", "team_name", "club", "team_abbrev", "team_abbr"])
if team_col:
    batters["_team"] = batters[team_col].astype(str).apply(normalize_team)
else:
    lookup = dict(zip(roster["_norm"], roster["team"])) if not roster.empty else {}
    batters["_team"] = batters["_name"].apply(lambda x: lookup.get(norm(x), ""))

# =========================
# MODEL
# =========================
def batter_metrics(row):
    xslg = safe_float(row[b_xslg], .390) if b_xslg else .390
    xwoba = safe_float(row[b_xwoba], .310) if b_xwoba else .310
    xba = safe_float(row[b_xba], .245) if b_xba else .245
    barrel = pct_value(row, b_barrel, .08)
    hard = pct_value(row, b_hard, .38)
    k_rate = pct_value(row, b_k, .22)
    pa = safe_float(row[b_pa], 250) if b_pa else 250
    iso = safe_float(row[b_iso], .170) if b_iso else .170

    power = clamp(
        .30*scale01(xslg,.300,.750)
        + .22*scale01(barrel,.02,.25)
        + .18*scale01(hard,.20,.65)
        + .15*scale01(iso,.080,.350)
        + .10*scale01(xwoba,.250,.460)
        + .05*scale01(pa,50,650),
        0,1
    )

    contact = clamp(
        .40*scale01(xba,.190,.330)
        + .30*scale01(xwoba,.250,.460)
        + .20*(1-scale01(k_rate,.12,.34))
        + .10*scale01(hard,.20,.65),
        0,1
    )

    laser = clamp(
        .50*scale01(hard,.20,.65)
        + .30*scale01(barrel,.02,.25)
        + .20*scale01(xslg,.300,.750),
        0,1
    )

    # UPGRADED FORM: if no real recent column, it uses power/contact/laser instead of calling everybody slump
    if b_recent:
        recent_raw = safe_float(row[b_recent], None)
        if recent_raw is None or recent_raw == 0:
            form_score = power*.55 + contact*.25 + laser*.20
        else:
            form_score = scale01(recent_raw, .180, .360)
    else:
        form_score = power*.55 + contact*.25 + laser*.20

    if form_score >= .70 or power >= .78 or laser >= .78:
        form = "🔥 Hot"
    elif form_score >= .50 or power >= .58 or laser >= .58:
        form = "✅ Good"
    elif form_score >= .35:
        form = "⚠️ Neutral"
    else:
        form = "❄️ Cold"

    return {
        "power": power,
        "contact": contact,
        "laser": laser,
        "form_score": form_score,
        "form": form
    }

def pitcher_vuln_from_live(live):
    return clamp(
        .45*scale01(live.get("hr9",1.1),.3,2.2)
        + .30*scale01(live.get("era",4.2),2.5,6.0)
        + .25*scale01(live.get("whip",1.3),.9,1.7),
        0,1
    )

def score_player(batter_name, pitcher_name, pitcher_id, team, opp, matchup, order="—", lineup="Projected"):
    b = find_player(batters, batter_name)
    if b is None:
        return None

    live = pitcher_live(pitcher_id)
    bm = batter_metrics(b)
    pv = pitcher_vuln_from_live(live)
    edge = clamp(bm["power"]*.50 + bm["laser"]*.25 + pv*.25, 0, 1)

    d_score = round(clamp(
        10*bm["power"]
        + 6*pv
        + 5*edge
        + 4*bm["contact"]
        + 3*bm["form_score"],
        0, 42
    ), 1)

    hr_prob = clamp(.04 + (.32*bm["power"] + .25*pv + .18*edge + .15*bm["laser"] + .10*bm["form_score"]) * .28, .015, .36)
    hit_prob = clamp(.28 + (.55*bm["contact"] + .25*(1-pv) + .20*bm["form_score"]) * .42, .18, .82)
    tb_prob = clamp(.20 + (.42*bm["power"] + .30*bm["contact"] + .28*pv) * .48, .10, .76)
    rbi_prob = clamp(.12 + (.45*bm["power"] + .30*pv + .25*(1-scale01(order if isinstance(order,int) else 5,1,9))) * .42, .06, .62)
    laser_prob = clamp(.15 + bm["laser"]*.58 + pv*.12, .10, .82)

    reasons = (
        f"{bm['form']} • Power {round(bm['power'],2)} • Contact {round(bm['contact'],2)} "
        f"• Laser {round(bm['laser'],2)} • Pitcher risk {round(pv,2)} "
        f"• Pitch-mix edge {round(edge,2)} • Live pitcher K9 {round(live.get('k9',8),1)}"
    )

    return {
        "Player": batter_name,
        "Team": normalize_team(team),
        "Matchup": matchup,
        "Pitcher": pitcher_name,
        "Opp": normalize_team(opp),
        "Lineup": lineup,
        "Order": order,
        "Dinger Score": d_score,
        "Dinger Badge": badge_score(d_score),
        "Grade": grade_score(d_score),
        "HR %": round(hr_prob*100,1),
        "Hit %": round(hit_prob*100,1),
        "TB %": round(tb_prob*100,1),
        "RBI %": round(rbi_prob*100,1),
        "Laser %": round(laser_prob*100,1),
        "Form": bm["form"],
        "HR Fair Odds": fair_odds(hr_prob),
        "Pitch-Mix Edge": round(edge,2),
        "Reasons": reasons,
    }

# =========================
# BUILD PLAYER ROWS
# =========================
rows = []

for g in games:
    matchup = f'{g["away"]} @ {g["home"]}'
    lu = get_lineups(g["gamePk"])

    if g["home_p"]:
        hitters = lu["away"]
        if hitters:
            for h in hitters:
                r = score_player(h["name"], g["home_p"], g["home_p_id"], g["away"], g["home"], matchup, h["order"], "Final")
                if r: rows.append(r)
        else:
            for _, b in batters[batters["_team"] == normalize_team(g["away"])].iterrows():
                r = score_player(b["_name"], g["home_p"], g["home_p_id"], g["away"], g["home"], matchup)
                if r: rows.append(r)

    if g["away_p"]:
        hitters = lu["home"]
        if hitters:
            for h in hitters:
                r = score_player(h["name"], g["away_p"], g["away_p_id"], g["home"], g["away"], matchup, h["order"], "Final")
                if r: rows.append(r)
        else:
            for _, b in batters[batters["_team"] == normalize_team(g["home"])].iterrows():
                r = score_player(b["_name"], g["away_p"], g["away_p_id"], g["home"], g["away"], matchup)
                if r: rows.append(r)

df = pd.DataFrame(rows)
if df.empty:
    st.error("No player rows created. Check team mapping, MLB lineups, and pitcher names.")
    st.stop()

df = df.sort_values("Dinger Score", ascending=False).reset_index(drop=True)

# =========================
# K MODEL
# =========================
k_rows = []
for g in games:
    for name, pid, opp in [(g["away_p"], g["away_p_id"], g["home"]), (g["home_p"], g["home_p_id"], g["away"])]:
        if not name:
            continue
        live = pitcher_live(pid)
        proj_ks = clamp(3.8 + (live["k_rate"]-.20)*18 + (live["k9"]-8.0)*0.35, 2.0, 10.5)

        def over_prob(line):
            return clamp(1 / (1 + math.exp(-(proj_ks-line))), .05, .92)

        k45 = round(over_prob(4.5)*100,1)
        k55 = round(over_prob(5.5)*100,1)
        k65 = round(over_prob(6.5)*100,1)
        best = max(k45,k55,k65)

        k_rows.append({
            "Pitcher": name,
            "Opponent": normalize_team(opp),
            "Projected Ks": round(proj_ks,1),
            "Live K%": round(live["k_rate"]*100,1),
            "K/9": round(live["k9"],1),
            "ERA": live["era"],
            "WHIP": live["whip"],
            "Over 4.5 K%": k45,
            "Over 5.5 K%": k55,
            "Over 6.5 K%": k65,
            "Best K%": best,
            "Grade": "A+" if best>=75 else "A" if best>=65 else "A-" if best>=58 else "B" if best>=50 else "C",
            "Pick Explanation": f"{name} projects for {round(proj_ks,1)} Ks using live K%, K/9, ERA and WHIP."
        })

k_df = pd.DataFrame(k_rows).sort_values("Best K%", ascending=False) if k_rows else pd.DataFrame()

# =========================
# TIERED PARLAYS
# =========================
def tier_parlays(data, col, label, name_col="Player"):
    pool = data.sort_values(col, ascending=False).head(15).reset_index(drop=True)
    out = []
    for i in range(0, 15, 3):
        c = pool.iloc[i:i+3]
        if len(c) < 3:
            continue
        out.append({
            "Parlay": f"{label} 3-Leg #{len(out)+1}",
            "Leg 1": f"{c.iloc[0][name_col]} ({c.iloc[0][col]}%)",
            "Leg 2": f"{c.iloc[1][name_col]} ({c.iloc[1][col]}%)",
            "Leg 3": f"{c.iloc[2][name_col]} ({c.iloc[2][col]}%)",
            "Avg Model %": round(c[col].mean(),1),
            "Model Combo Confidence": round((c[col]/100).prod()*100,2),
            "Notes": "Tier-based no-overlap parlay"
        })
    return pd.DataFrame(out)

parlay_hr = tier_parlays(df, "HR %", "HR")
parlay_hit = tier_parlays(df, "Hit %", "Hit")
parlay_tb = tier_parlays(df, "TB %", "TB")
parlay_rbi = tier_parlays(df, "RBI %", "RBI")
parlay_laser = tier_parlays(df, "Laser %", "Laser")
parlay_k = tier_parlays(k_df, "Best K%", "K", "Pitcher") if not k_df.empty else pd.DataFrame()

# =========================
# TABLE RENDER
# =========================
def color_grade(g):
    return {"A+":"#166534","A":"#15803d","A-":"#16a34a","B":"#2563eb","C":"#6d28d9","D":"#7f1d1d"}.get(g,"#374151")

def render(data):
    if data is None or data.empty:
        return "<div class='note'>No data available.</div>"
    cols = list(data.columns)
    html = "<div class='table-wrap'><table class='ai-table'><tr>"
    for c in cols:
        html += f"<th>{c}</th>"
    html += "</tr>"
    for _, r in data.iterrows():
        html += "<tr>"
        for c in cols:
            v = r.get(c, "")
            style = ""
            if c == "Grade":
                style = f"background:{color_grade(v)};font-weight:900;text-align:center;"
            elif c == "Dinger Score":
                style = "background:rgba(34,197,94,.35);font-weight:900;" if safe_float(v)>=26 else "background:rgba(59,130,246,.25);font-weight:900;" if safe_float(v)>=22 else "background:rgba(234,179,8,.22);font-weight:900;"
            elif "%" in c or c in ["Avg Model %", "Model Combo Confidence"]:
                style = "background:rgba(34,197,94,.25);" if safe_float(v)>=60 else "background:rgba(234,179,8,.18);" if safe_float(v)>=35 else "background:rgba(239,68,68,.15);"
            elif c == "Form":
                val = str(v)
                if "Hot" in val:
                    style = "color:#86efac;font-weight:900;"
                elif "Good" in val:
                    style = "color:#93c5fd;font-weight:900;"
                elif "Neutral" in val:
                    style = "color:#fde68a;font-weight:900;"
                else:
                    style = "color:#fca5a5;font-weight:900;"
            elif c in ["Reasons", "Pick Explanation", "Notes"]:
                style = "white-space:normal;min-width:420px;color:#cbd5e1;"
            html += f"<td style='{style}'>{v}</td>"
        html += "</tr>"
    html += "</table></div>"
    return html

# =========================
# UI
# =========================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔥 Best", "📋 All Players", "🎯 Strikeouts", "🧾 Parlays", "🛠 Debug"])

with tab1:
    st.subheader("Best AI Rated Plays")
    st.markdown(render(df.head(40)), unsafe_allow_html=True)

with tab2:
    st.subheader("Full Player Model")
    st.markdown(render(df), unsafe_allow_html=True)

with tab3:
    st.subheader("Live Pitcher Strikeout Model")
    st.markdown(render(k_df), unsafe_allow_html=True)

with tab4:
    st.subheader("Top 5 Tiered 3-Leg Parlays")
    st.markdown("### 💣 HR Parlays")
    st.markdown(render(parlay_hr), unsafe_allow_html=True)
    st.markdown("### ✅ Hit Parlays")
    st.markdown(render(parlay_hit), unsafe_allow_html=True)
    st.markdown("### 🧱 Total Bases Parlays")
    st.markdown(render(parlay_tb), unsafe_allow_html=True)
    st.markdown("### 🏃 RBI Parlays")
    st.markdown(render(parlay_rbi), unsafe_allow_html=True)
    st.markdown("### 🚀 Laser Parlays")
    st.markdown(render(parlay_laser), unsafe_allow_html=True)
    st.markdown("### 🎯 Strikeout Parlays")
    st.markdown(render(parlay_k), unsafe_allow_html=True)

with tab5:
    st.write("Games loaded:", len(games))
    st.write("Players scored:", len(df))
    st.write("Batters CSV rows:", len(batters))
    st.write("Pitchers CSV rows:", len(pitchers))
    st.write("Detected batter recent column:", b_recent if b_recent else "None — using power/contact/laser fallback")
    st.write("Team counts:")
    st.dataframe(batters["_team"].value_counts(dropna=False).reset_index(), use_container_width=True)
