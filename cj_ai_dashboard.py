import math
import time
import unicodedata
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="AON WORLD BETS HR MODEL ⚾️💣", layout="wide")

REFRESH_SECONDS = 300
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > REFRESH_SECONDS:
    st.session_state.last_refresh = time.time()
    st.rerun()

st.markdown("""
<style>
.stApp { background:#050914; color:white; }
.block-container { padding:.75rem; max-width:100%; }
.hero { background:linear-gradient(135deg,#3b171b,#111827); padding:18px; border-radius:18px; margin-bottom:16px; }
.hero h1 { font-size:26px; margin:0; }
.hero p { font-size:13px; color:#cbd5e1; margin-top:6px; }
.table-wrap { overflow-x:auto; border:1px solid #1f2937; border-radius:16px; margin-bottom:18px; max-width:100%; }
.ai-table { width:100%; border-collapse:collapse; background:#0b1220; color:white; font-size:12px; table-layout:auto; }
.ai-table th { background:#111827; padding:7px; text-align:left; white-space:nowrap; }
.ai-table td { padding:7px; border-bottom:1px solid rgba(255,255,255,.08); white-space:nowrap; }
@media (max-width: 700px) {
    .hero h1 { font-size:20px; }
    .hero p { font-size:11px; }
    .ai-table { font-size:11px; }
    .ai-table th, .ai-table td { padding:6px; }
    .card { padding:12px; }
    .card h2 { font-size:18px; }
    .card h3 { font-size:16px; }
}
.note { background:#0b1220; border:1px solid #1f2937; border-radius:14px; padding:12px; color:#cbd5e1; }
.card { background:#0b1220; border:1px solid #1f2937; border-radius:18px; padding:16px; margin-bottom:14px; }
.card h2 { margin-top:0; }

.dinger-board { background:#090f1a; border:1px solid #263244; border-radius:18px; padding:8px; margin-bottom:18px; }
.dinger-row { display:grid; grid-template-columns: 34px 1.55fr 88px 68px 90px 88px; gap:8px; align-items:center; padding:10px 8px; border-bottom:1px solid rgba(255,255,255,.08); }
.dinger-row:last-child { border-bottom:none; }
.dinger-rank { color:#fef08a; font-weight:900; text-align:center; font-size:14px; }
.dinger-name { font-size:14px; font-weight:900; color:#f8fafc; line-height:1.1; }
.dinger-sub { font-size:10px; color:#cbd5e1; text-transform:uppercase; letter-spacing:.06em; margin-top:3px; }
.dinger-pill { display:inline-block; padding:3px 7px; border-radius:999px; font-size:10px; font-weight:900; margin-left:5px; }
.dinger-pill-good { background:rgba(34,197,94,.22); color:#86efac; }
.dinger-pill-mid { background:rgba(234,179,8,.22); color:#fde68a; }
.dinger-pill-bad { background:rgba(239,68,68,.22); color:#fca5a5; }
.dinger-num { text-align:right; font-weight:900; color:#22c55e; font-size:14px; }
.dinger-small { text-align:right; font-size:11px; color:#cbd5e1; line-height:1.15; }
.dinger-note { font-size:10px; color:#94a3b8; white-space:normal; line-height:1.2; }
@media (max-width:700px) {
  .dinger-row { grid-template-columns: 28px 1.4fr 62px 54px 58px 70px; gap:5px; padding:8px 5px; }
  .dinger-name { font-size:12px; }
  .dinger-sub, .dinger-note { font-size:9px; }
  .dinger-num { font-size:12px; }
  .dinger-small { font-size:9px; }
}


.tier-board { background:#f8fafc; color:#111827; border:1px solid #cbd5e1; border-radius:16px; overflow:hidden; margin-bottom:18px; font-family:Arial, sans-serif; }
.tier-head { display:grid; grid-template-columns:42px 1.45fr 48px 46px 62px 62px 70px 78px; gap:6px; padding:9px 8px; background:#e5e7eb; font-weight:900; font-size:11px; color:#374151; text-transform:uppercase; }
.tier-title { background:#e5e7eb; color:#374151; font-size:22px; font-weight:900; padding:8px 12px; border-top:1px solid #d1d5db; border-bottom:1px solid #d1d5db; letter-spacing:.04em; }
.tier-row { display:grid; grid-template-columns:42px 1.45fr 48px 46px 62px 62px 70px 78px; gap:6px; align-items:center; padding:9px 8px; border-bottom:1px solid #e5e7eb; font-size:13px; }
.tier-row-elite { background:#fee2e2; }
.tier-row-very { background:#f3e8ff; }
.tier-row-good { background:#ffffff; }
.tier-row-watch { background:#f8fafc; }
.tier-rank { color:#9ca3af; font-weight:800; text-align:center; }
.tier-player { font-weight:900; color:#111827; }
.tier-sub { display:block; font-size:10px; color:#6b7280; text-transform:uppercase; letter-spacing:.04em; }
.tier-pill { display:inline-block; padding:2px 6px; border-radius:999px; font-size:10px; font-weight:900; color:#fff; }
.tier-pill-s { background:#166534; }
.tier-pill-a { background:#2563eb; }
.tier-pill-b { background:#7c3aed; }
.tier-pill-c { background:#92400e; }
.tier-score { font-weight:900; color:#7f1d1d; text-align:center; }
.tier-cell { text-align:center; font-weight:800; color:#374151; }
.tier-weather-good { background:#bbf7d0; color:#14532d; border-radius:6px; padding:3px 4px; font-weight:900; font-size:10px; text-align:center; }
.tier-weather-mid { background:#fde68a; color:#78350f; border-radius:6px; padding:3px 4px; font-weight:900; font-size:10px; text-align:center; }
.tier-weather-bad { background:#fecaca; color:#7f1d1d; border-radius:6px; padding:3px 4px; font-weight:900; font-size:10px; text-align:center; }
@media (max-width:700px) {
  .tier-head, .tier-row { grid-template-columns:28px 1.35fr 34px 38px 48px 48px 54px 58px; gap:4px; padding:7px 5px; font-size:10px; }
  .tier-title { font-size:16px; padding:7px 8px; }
  .tier-player { font-size:12px; }
  .tier-sub { font-size:8px; }
  .tier-pill { font-size:8px; padding:2px 4px; }
  .tier-weather-good, .tier-weather-mid, .tier-weather-bad { font-size:8px; padding:2px 3px; }
}


.target-card-wrap { display:flex; flex-direction:column; gap:8px; margin:8px 0 18px 0; }
.target-card { background:#101827; border:1px solid rgba(255,255,255,.08); border-radius:14px; padding:10px 12px; display:grid; grid-template-columns:34px 1.4fr 70px 70px 70px 95px; gap:8px; align-items:center; color:#f8fafc; }
.target-rank { color:#fde68a; font-weight:900; font-size:14px; text-align:center; }
.target-name { font-size:15px; font-weight:900; line-height:1.1; }
.target-sub { font-size:10px; color:#cbd5e1; margin-top:4px; text-transform:uppercase; letter-spacing:.05em; }
.target-pill { display:inline-block; border-radius:999px; padding:2px 7px; font-size:10px; font-weight:900; margin-left:5px; }
.target-pill-s { background:#22c55e; color:#052e16; }
.target-pill-a { background:#3b82f6; color:#eff6ff; }
.target-pill-b { background:#a855f7; color:white; }
.target-pill-c { background:#f59e0b; color:#451a03; }
.target-num { text-align:right; font-weight:900; color:#22c55e; font-size:14px; }
.target-label { display:block; color:#94a3b8; font-size:9px; font-weight:800; margin-top:2px; }
.target-weather-good { background:rgba(34,197,94,.20); color:#86efac; border-radius:8px; padding:5px; text-align:center; font-weight:900; font-size:10px; }
.target-weather-mid { background:rgba(234,179,8,.20); color:#fde68a; border-radius:8px; padding:5px; text-align:center; font-weight:900; font-size:10px; }
.target-weather-bad { background:rgba(239,68,68,.20); color:#fca5a5; border-radius:8px; padding:5px; text-align:center; font-weight:900; font-size:10px; }
@media (max-width:700px) {
  .target-card { grid-template-columns:26px 1.5fr 52px 42px 45px 62px; gap:5px; padding:8px 7px; }
  .target-name { font-size:12px; }
  .target-sub { font-size:8px; }
  .target-num { font-size:11px; }
  .target-label { font-size:7px; }
  .target-weather-good,.target-weather-mid,.target-weather-bad { font-size:8px; padding:4px 3px; }
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class='hero'>
<h1>🔥 AON WORLD BETS HR MODEL ⚾️💣</h1>
<p>All MLB Players Injected • Season HR For Everyone • Best K Pitcher • Best 8 Hits • HR Combos 2-6 Legs • Dynamic Parlays</p>
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
        if isinstance(x, str):
            x = x.replace("%", "").strip()
            if x == "":
                return d
        return float(x)
    except Exception:
        return d

def scale01(x, a, b):
    try:
        x = float(x)
        if a == b:
            return 0.5
        return clamp((x - a) / (b - a), 0, 1)
    except Exception:
        return 0.5

def norm(x):
    s = str(x).lower().replace(",", " ").replace(".", " ").strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    parts = [p for p in s.split() if p not in ["jr", "sr", "ii", "iii", "iv"]]
    return " ".join(parts)

def first_last(x):
    x = str(x).strip()
    if "," in x:
        last, first = [p.strip() for p in x.split(",", 1)]
        return f"{first} {last}"
    return x

def find_col(df, names):
    if df is None or df.empty:
        return None
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
    c = find_col(df, ["last_name, first_name", "last_name_first_name"])
    if c:
        return df[c].astype(str).apply(first_last)
    c = find_col(df, ["player_name", "name", "player", "pitcher_name"])
    if c:
        return df[c].astype(str).apply(first_last)
    st.error(f"Could not find player name column. Found: {list(df.columns)}")
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
        "athletics":"OAK",
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
    if not name or df.empty:
        return None
    hits = df[df["_name"].apply(lambda x: player_match(x, name))]
    return hits.iloc[0] if not hits.empty else None

def grade_score(s):
    if s >= 36: return "S+"
    if s >= 32: return "S"
    if s >= 28: return "A+"
    if s >= 24: return "A"
    if s >= 20: return "B"
    if s >= 16: return "C"
    return "D"

def badge_score(s):
    if s >= 36: return "☢️ Nuclear"
    if s >= 32: return "🔥 Elite"
    if s >= 28: return "💎 Great"
    if s >= 24: return "✅ Good"
    if s >= 20: return "🟡 Solid"
    if s >= 16: return "⚪ Lean"
    return "🔻 Fade"

def bet_badge(row):
    grade = str(row.get("Grade", ""))
    hrp = safe_float(row.get("HR %", 0))
    matchup = safe_float(row.get("Auto Matchup Edge", 0))
    weather = str(row.get("Weather Alert", ""))

    if grade in ["S+", "S"] or (hrp >= 24 and matchup >= 0.60):
        return "🔥 Strong Bet"
    if grade in ["A+", "A"] or (hrp >= 20 and matchup >= 0.52):
        return "✅ Good Bet"
    if grade == "B":
        return "🟡 Lean"
    if "cold" in weather.lower() or "downgrade" in weather.lower():
        return "⚠️ Weather Risk"
    return "⚪ Watchlist"

def color_grade(g):
    return {
        "S+":"#7f1d1d", "S":"#166534", "A+":"#15803d",
        "A":"#2563eb", "B":"#6d28d9", "C":"#92400e", "D":"#374151"
    }.get(g, "#374151")

def is_game_available_for_parlays(status):
    s = str(status).lower().strip()
    bad = ["in progress", "live", "final", "game over", "completed early", "postponed", "cancelled"]
    return not any(x in s for x in bad)

# =========================
# PARK + WEATHER
# =========================
STADIUM_DATA = {
    "Yankee Stadium":("Bronx","NY",1.18),
    "Citizens Bank Park":("Philadelphia","PA",1.20),
    "Great American Ball Park":("Cincinnati","OH",1.25),
    "Coors Field":("Denver","CO",1.30),
    "Dodger Stadium":("Los Angeles","CA",1.05),
    "Truist Park":("Atlanta","GA",1.06),
    "Fenway Park":("Boston","MA",1.03),
    "Citi Field":("Queens","NY",0.96),
    "Oracle Park":("San Francisco","CA",0.82),
    "Petco Park":("San Diego","CA",0.93),
    "T-Mobile Park":("Seattle","WA",0.91),
    "Kauffman Stadium":("Kansas City","MO",0.88),
    "Wrigley Field":("Chicago","IL",1.00),
    "Guaranteed Rate Field":("Chicago","IL",1.12),
    "Oriole Park at Camden Yards":("Baltimore","MD",1.02),
    "Rogers Centre":("Toronto","ON",1.05),
    "Tropicana Field":("St. Petersburg","FL",0.92),
    "Progressive Field":("Cleveland","OH",0.97),
    "Comerica Park":("Detroit","MI",0.90),
    "Target Field":("Minneapolis","MN",0.98),
    "Minute Maid Park":("Houston","TX",1.04),
    "Angel Stadium":("Anaheim","CA",0.96),
    "Globe Life Field":("Arlington","TX",1.00),
    "loanDepot park":("Miami","FL",0.92),
    "Nationals Park":("Washington","DC",1.02),
    "American Family Field":("Milwaukee","WI",1.08),
    "PNC Park":("Pittsburgh","PA",0.93),
    "Busch Stadium":("St. Louis","MO",0.95),
    "Chase Field":("Phoenix","AZ",1.03),
    "Sutter Health Park":("West Sacramento","CA",1.04),
}

def stadium_info(park):
    for k, v in STADIUM_DATA.items():
        if norm(k) == norm(park):
            return v
    return ("", "", 1.00)

def park_note(factor):
    if factor >= 1.15:
        return "🔥 HR park boost"
    if factor <= 0.92:
        return "❄️ pitcher-friendly park"
    return "⚖️ neutral park"

@st.cache_data(ttl=1800)
def get_weather(city, state):
    if not city:
        return {"temp":"N/A","wind":"N/A","dir":"N/A","factor":1.0,"note":"⚖️ weather neutral"}
    try:
        q = f"{city},{state}".replace(" ", "%20")
        data = requests.get(f"https://wttr.in/{q}?format=j1", timeout=15).json()
        cur = data["current_condition"][0]
        temp = safe_float(cur.get("temp_F"), 70)
        wind = safe_float(cur.get("windspeedMiles"), 7)
        direction = cur.get("winddir16Point", "N/A")
    except Exception:
        return {"temp":"N/A","wind":"N/A","dir":"N/A","factor":1.0,"note":"⚖️ weather neutral"}

    factor = 1.0
    note = "⚖️ weather neutral"
    if temp >= 80:
        factor += .10
        note = "🔥 warm air boost"
    elif temp <= 55:
        factor -= .08
        note = "❄️ cold air downgrade"
    if wind >= 10:
        factor += .08
        note += f" • wind {direction} {wind}mph"
    return {"temp":temp,"wind":wind,"dir":direction,"factor":factor,"note":note}

# =========================
# MLB API
# =========================
@st.cache_data(ttl=300)
def get_schedule():
    today = time.strftime("%Y-%m-%d")
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
                "status": g.get("status", {}).get("detailedState", "")
            })
    return games

@st.cache_data(ttl=300)
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
                out.append({"name": name, "id": pid, "order": idx})
        return out

    return {"away": side("away"), "home": side("home")}

@st.cache_data(ttl=86400)
def build_roster():
    out = []
    try:
        teams = requests.get("https://statsapi.mlb.com/api/v1/teams?sportId=1", timeout=20).json().get("teams", [])
    except Exception:
        return pd.DataFrame(columns=["name","team","_norm"])
    for t in teams:
        team = normalize_team(t.get("name", ""))
        tid = t.get("id")
        try:
            roster = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{tid}/roster", timeout=20).json().get("roster", [])
        except Exception:
            roster = []
        for p in roster:
            name = p.get("person", {}).get("fullName", "")
            if name:
                out.append({"name": name, "team": team, "_norm": norm(name), "player_id": p.get("person", {}).get("id", None)})
    return pd.DataFrame(out)

@st.cache_data(ttl=1800)
def pitcher_live(pid):
    if not pid:
        return {"k_rate":.22,"k9":8.0,"era":4.20,"whip":1.30,"hr9":1.10,"hand":"R"}
    try:
        season = time.strftime("%Y")
        bio = requests.get(f"https://statsapi.mlb.com/api/v1/people/{pid}", timeout=20).json()
        person = bio.get("people", [{}])[0]
        hand = person.get("pitchHand", {}).get("code", "R")

        url = f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=season&group=pitching&season={season}"
        data = requests.get(url, timeout=20).json()
        splits = data.get("stats", [{}])[0].get("splits", [])
        if not splits:
            return {"k_rate":.22,"k9":8.0,"era":4.20,"whip":1.30,"hr9":1.10,"hand":hand}

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
            "hand": hand
        }
    except Exception:
        return {"k_rate":.22,"k9":8.0,"era":4.20,"whip":1.30,"hr9":1.10,"hand":"R"}


@st.cache_data(ttl=1800)
def hitter_live_season(pid):
    """
    Pull exact current season hitter totals by MLB player ID.
    This fixes Season HR showing 0 when CSV/name merge misses a player.
    """
    if not pid:
        return {"season_hr": None}

    try:
        season = time.strftime("%Y")
        url = f"https://statsapi.mlb.com/api/v1/people/{int(float(pid))}/stats?stats=season&group=hitting&season={season}"
        data = requests.get(url, timeout=20).json()
        splits = data.get("stats", [{}])[0].get("splits", [])
        if not splits:
            return {"season_hr": None}

        stat = splits[0].get("stat", {})
        return {
            "season_hr": int(safe_float(stat.get("homeRuns", 0), 0)),
            "pa": safe_float(stat.get("plateAppearances", 0), 0),
            "slg": safe_float(stat.get("slg", stat.get("sluggingPercentage", 0)), 0),
            "avg": safe_float(stat.get("avg", 0), 0)
        }
    except Exception:
        return {"season_hr": None}


@st.cache_data(ttl=3600)
def get_all_mlb_hitters():
    """
    Pull all MLB hitters with season totals. This replaces the old get_hr_leaders system.
    Everyone gets season_hr.
    """
    season = time.strftime("%Y")
    url = f"https://statsapi.mlb.com/api/v1/stats?stats=season&group=hitting&season={season}&sportIds=1&limit=5000"
    try:
        data = requests.get(url, timeout=25).json()
        splits = data.get("stats", [{}])[0].get("splits", [])
    except Exception:
        return pd.DataFrame()

    rows = []
    for s in splits:
        player = s.get("player", {}) or {}
        team = s.get("team", {}) or {}
        stat = s.get("stat", {}) or {}

        name = player.get("fullName", "")
        player_id = player.get("id", None)
        team_name = team.get("name", "")
        if not name:
            continue

        avg = safe_float(stat.get("avg"), .240)
        slg = safe_float(stat.get("slg", stat.get("sluggingPercentage", .400)), .400)
        ops = safe_float(stat.get("ops", stat.get("onBasePlusSlugging", .700)), .700)
        obp = safe_float(stat.get("obp", .310), .310)
        pa = safe_float(stat.get("plateAppearances", 200), 200)
        hr = safe_float(stat.get("homeRuns", 0), 0)

        rows.append({
            "_name": name,
            "player_id": player_id,
            "_team": normalize_team(team_name),
            "season_hr": int(hr),
            "pa": pa,
            "bip": safe_float(stat.get("atBats", 150), 150),
            "ba": avg,
            "est_ba": avg,
            "slg": slg,
            "est_slg": slg,
            "woba": (ops / 2) if ops else (obp + slg) / 2,
            "est_woba": (ops / 2) if ops else (obp + slg) / 2,
            "iso": max(0, slg - avg),
            "recent_form": .250,
            "barrel": clamp(.070 + hr * .003, .070, .220),
            "hard_hit": clamp(.380 + hr * .005, .380, .600),
            "mlb_api_injected": True
        })
    return pd.DataFrame(rows)

# =========================
# LOAD + INJECT DATA
# =========================
try:
    batters = pd.read_csv("batters.csv")
except Exception as e:
    st.error(f"batters.csv load error: {e}")
    st.stop()

batters["_name"] = make_name(batters)
batters["mlb_api_injected"] = False

roster = build_roster()
roster_id_lookup = dict(zip(roster["_norm"], roster["player_id"])) if not roster.empty and "player_id" in roster.columns else {}

b_team_start = find_col(batters, ["team","player_team","bat_team","team_name","club","team_abbrev","team_abbr"])
if b_team_start:
    batters["_team"] = batters[b_team_start].astype(str).apply(normalize_team)
else:
    lookup = dict(zip(roster["_norm"], roster["team"])) if not roster.empty else {}
    batters["_team"] = batters["_name"].apply(lambda x: lookup.get(norm(x), "N/A"))

mlb_players = get_all_mlb_hitters()
mlb_injected_count = 0

if not mlb_players.empty:
    # Inject missing MLB players. Prefer player_id matching when available, then normalized name.
    existing_names = set(batters["_name"].astype(str).apply(norm))

    existing_ids = set()
    existing_id_col = find_col(batters, ["player_id", "id", "mlb_id"])
    if existing_id_col:
        existing_ids = set(batters[existing_id_col].astype(str))

    if "player_id" in mlb_players.columns and existing_ids:
        missing_players = mlb_players[
            ~mlb_players["player_id"].astype(str).isin(existing_ids)
            & ~mlb_players["_name"].astype(str).apply(norm).isin(existing_names)
        ].copy()
    else:
        missing_players = mlb_players[
            ~mlb_players["_name"].astype(str).apply(norm).isin(existing_names)
        ].copy()

    mlb_injected_count = len(missing_players)
    if not missing_players.empty:
        batters = pd.concat([batters, missing_players], ignore_index=True, sort=False)

    # Add/update season_hr for EVERY player.
    hr_lookup_name = dict(zip(mlb_players["_name"].astype(str).apply(norm), mlb_players["season_hr"]))
    team_lookup_name = dict(zip(mlb_players["_name"].astype(str).apply(norm), mlb_players["_team"]))

    hr_lookup_id = {}
    team_lookup_id = {}
    if "player_id" in mlb_players.columns:
        hr_lookup_id = dict(zip(mlb_players["player_id"].astype(str), mlb_players["season_hr"]))
        team_lookup_id = dict(zip(mlb_players["player_id"].astype(str), mlb_players["_team"]))

    id_col = find_col(batters, ["player_id", "id", "mlb_id"])

    def lookup_season_hr(r):
        current = safe_float(r.get("season_hr", 0), 0)

        if id_col:
            pid = str(r.get(id_col, ""))
            if pid in hr_lookup_id:
                return hr_lookup_id[pid]

        nm = norm(r.get("_name", ""))
        if nm in hr_lookup_name:
            return hr_lookup_name[nm]

        # Soft last-name fallback for rare accent/suffix mismatches.
        parts = nm.split()
        if len(parts) >= 2:
            first_initial = parts[0][0]
            last = parts[-1]
            candidates = mlb_players[mlb_players["_name"].astype(str).apply(lambda x: len(norm(x).split()) >= 2 and norm(x).split()[-1] == last and norm(x).split()[0][0] == first_initial)]
            if len(candidates) == 1:
                return safe_float(candidates.iloc[0].get("season_hr", current), current)

        return current

    def lookup_team(r):
        cur = r.get("_team", "N/A")
        if str(cur) != "N/A":
            return cur

        if id_col:
            pid = str(r.get(id_col, ""))
            if pid in team_lookup_id:
                return team_lookup_id[pid]

        nm = norm(r.get("_name", ""))
        return team_lookup_name.get(nm, "N/A")

    batters["season_hr"] = batters.apply(lookup_season_hr, axis=1)
    batters["_team"] = batters.apply(lookup_team, axis=1)
else:
    if "season_hr" not in batters.columns:
        batters["season_hr"] = 0

# Re-detect columns after injection
b_team = find_col(batters, ["team","player_team","bat_team","team_name","club","team_abbrev","team_abbr","_team"])
b_pa = find_col(batters, ["pa"])
b_bip = find_col(batters, ["bip"])
b_ba = find_col(batters, ["ba"])
b_est_ba = find_col(batters, ["est_ba","xba"])
b_slg = find_col(batters, ["slg"])
b_est_slg = find_col(batters, ["est_slg","xslg"])
b_woba = find_col(batters, ["woba"])
b_est_woba = find_col(batters, ["est_woba","xwoba"])
b_barrel = find_col(batters, ["barrel","barrel_pct","brl"])
b_hard = find_col(batters, ["hard_hit","hardhit","hard_hit_pct"])
b_iso = find_col(batters, ["iso"])
b_recent = find_col(batters, ["last7_slg","last7","last14","recent","recent_form"])
b_season_hr = find_col(batters, ["season_hr","home_runs","hr"])

# =========================
# MODEL
# =========================
def pitcher_risk(live):
    return clamp(
        .45 * scale01(live.get("hr9", 1.1), .3, 2.2)
        + .30 * scale01(live.get("era", 4.2), 2.5, 6.0)
        + .25 * scale01(live.get("whip", 1.3), .9, 1.7),
        0, 1
    )

def batter_metrics(row):
    pa = safe_float(row[b_pa], 250) if b_pa else 250
    bip = safe_float(row[b_bip], 150) if b_bip else 150
    ba = safe_float(row[b_ba], .245) if b_ba else .245
    est_ba = safe_float(row[b_est_ba], ba) if b_est_ba else ba
    slg = safe_float(row[b_slg], .400) if b_slg else .400
    est_slg = safe_float(row[b_est_slg], slg) if b_est_slg else slg
    woba = safe_float(row[b_woba], .310) if b_woba else .310
    est_woba = safe_float(row[b_est_woba], woba) if b_est_woba else woba
    iso = safe_float(row[b_iso], est_slg - est_ba) if b_iso else est_slg - est_ba
    barrel = safe_float(row[b_barrel], None) if b_barrel else None
    hard = safe_float(row[b_hard], None) if b_hard else None
    season_hr = safe_float(row[b_season_hr], 0) if b_season_hr else 0
    injected = bool(row.get("mlb_api_injected", False))

    if barrel is not None and barrel > 1:
        barrel /= 100
    if hard is not None and hard > 1:
        hard /= 100

    power = clamp(
        .42 * scale01(est_slg, .300, .700)
        + .28 * scale01(est_woba, .250, .450)
        + .18 * scale01(iso, .080, .350)
        + .12 * scale01(pa, 50, 650),
        0, 1
    )

    if barrel is not None:
        power = clamp(power * .82 + scale01(barrel, .02, .22) * .18, 0, 1)
    if hard is not None:
        power = clamp(power * .88 + scale01(hard, .25, .60) * .12, 0, 1)

    if season_hr > 0:
        hr_boost = scale01(season_hr, 3, 25)
        power = clamp(power * .80 + hr_boost * .20, 0, 1)

    contact = clamp(.50 * scale01(est_ba, .190, .330) + .35 * scale01(est_woba, .250, .450) + .15 * scale01(bip, 40, 500), 0, 1)
    laser = clamp(.55 * scale01(est_slg, .300, .700) + .30 * scale01(est_woba, .250, .450) + .15 * (scale01(hard, .25, .60) if hard is not None else .50), 0, 1)

    if b_recent:
        recent = safe_float(row[b_recent], None)
        form_score = scale01(recent, .180, .360) if recent not in [None, 0] else power * .55 + contact * .25 + laser * .20
    else:
        form_score = power * .55 + contact * .25 + laser * .20

    if season_hr > 0:
        form_score = clamp(form_score * .88 + scale01(season_hr, 3, 25) * .12, 0, 1)

    form = "🔥 Hot" if form_score >= .70 or power >= .78 or laser >= .78 else "✅ Good" if form_score >= .50 or power >= .58 or laser >= .58 else "⚠️ Neutral" if form_score >= .35 else "❄️ Cold"
    source = "MLB API Injected" if injected else "batters.csv + MLB season HR"

    return {
        "Power": round(power, 2),
        "Contact": round(contact, 2),
        "Laser": round(laser, 2),
        "Form Score": round(form_score, 2),
        "Form": form,
        "estSLG": round(est_slg, 3),
        "estwOBA": round(est_woba, 3),
        "estBA": round(est_ba, 3),
        "ISO": round(iso, 3),
        "Season HR": int(season_hr) if season_hr else 0,
        "Data Source": source
    }

def auto_matchup_edge(m, live, park_edge, weather_edge, lineup_edge):
    pitcher_hr = pitcher_risk(live)
    pitcher_k = scale01(live.get("k_rate", .22), .16, .34)

    raw = (
        .34 * m["Power"]
        + .18 * m["Laser"]
        + .13 * m["Form Score"]
        + .18 * pitcher_hr
        + .07 * park_edge
        + .05 * weather_edge
        + .05 * lineup_edge
        - .10 * pitcher_k
    )

    edge = clamp(raw, 0, 1)
    note = f"auto edge from batter power + pitcher HR risk + K risk; pitcher hand {live.get('hand','R')} • K risk {round(pitcher_k,2)}"
    return edge, note

def score_row(player_name, team, matchup, pitcher_name, pitcher_id, park, game_status, game_pk, order="—", lineup="Projected", batter_id=None):
    b = find_player(batters, player_name)
    if b is None:
        return None

    m = batter_metrics(b)

    # Exact MLB season HR override by player ID.
    # Priority: lineup ID -> CSV player_id -> MLB roster ID -> name-merge fallback already in m.
    if batter_id is None:
        id_col = find_col(pd.DataFrame([b]), ["player_id", "id", "mlb_id"])
        if id_col:
            batter_id = b.get(id_col, None)
    if batter_id is None:
        batter_id = roster_id_lookup.get(norm(player_name), None)

    live_batter = hitter_live_season(batter_id)
    if live_batter.get("season_hr") is not None:
        m["Season HR"] = int(live_batter["season_hr"])

    live = pitcher_live(pitcher_id)
    pr = pitcher_risk(live)

    city, state, park_factor = stadium_info(park)
    weather = get_weather(city, state)

    park_edge = scale01(park_factor, .82, 1.30)
    weather_edge = scale01(weather["factor"], .88, 1.18)
    lineup_edge = 1 - scale01(order, 1, 9) if isinstance(order, int) else .50
    me, me_note = auto_matchup_edge(m, live, park_edge, weather_edge, lineup_edge)

    dinger_score = round(clamp(
        10 * m["Power"]
        + 6 * m["Laser"]
        + 5 * m["Contact"]
        + 4 * m["Form Score"]
        + 7 * me
        + 4 * pr
        + 3 * park_edge
        + 3 * weather_edge
        + 2 * lineup_edge,
        0, 42
    ), 1)

    hr_prob = clamp(
        .035 + (
            .26 * m["Power"]
            + .17 * m["Laser"]
            + .11 * m["Form Score"]
            + .20 * me
            + .13 * pr
            + .07 * park_edge
            + .04 * weather_edge
            + .02 * lineup_edge
        ) * .34,
        .010, .40
    )

    hit_prob = clamp(.28 + m["Contact"] * .42, .18, .82)
    tb_prob = clamp(.20 + (m["Power"] * .43 + m["Contact"] * .22 + m["Laser"] * .20 + me * .15) * .48, .10, .76)
    rbi_prob = clamp(.12 + (m["Power"] * .43 + m["Laser"] * .17 + pr * .25 + me * .15) * .42, .06, .62)
    laser_prob = clamp(.15 + m["Laser"] * .62 + me * .08, .10, .82)

    reasons = (
        f"{m['Form']} • Auto Matchup Edge {round(me,2)} ({me_note}) • "
        f"Matchup: {matchup} vs {pitcher_name} • "
        f"Game Status: {game_status} • "
        f"Pitcher Risk {round(pr,2)} HR/9 {round(live['hr9'],2)} ERA {live['era']} WHIP {live['whip']} • "
        f"Park: {park} {park_note(park_factor)} ({park_factor}) • "
        f"Weather: {weather['note']} {weather['temp']}°F wind {weather['wind']}mph {weather['dir']} • "
        f"Power {m['Power']} • Laser {m['Laser']} • estSLG {m['estSLG']} • ISO {m['ISO']} • "
        f"Season HR {m['Season HR']} • Source {m['Data Source']}"
    )

    return {
        "Player": player_name,
        "Team": team,
        "Matchup": matchup,
        "Pitcher": pitcher_name,
        "Park": park,
        "Game Status": game_status,
        "Parlay Eligible": "Yes" if is_game_available_for_parlays(game_status) else "No",
        "Lineup": lineup,
        "Order": order,
        "Dinger Score": dinger_score,
        "Grade": grade_score(dinger_score),
        "Badge": badge_score(dinger_score),
        "HR %": round(hr_prob * 100, 1),
        "Hit %": round(hit_prob * 100, 1),
        "TB %": round(tb_prob * 100, 1),
        "RBI %": round(rbi_prob * 100, 1),
        "Laser %": round(laser_prob * 100, 1),
        "Form": m["Form"],
        "Form Score": m["Form Score"],
        "Auto Matchup Edge": round(me, 2),
        "Pitcher Risk": round(pr, 2),
        "Park Edge": round(park_edge, 2),
        "Weather Edge": round(weather_edge, 2),
        "Weather Alert": weather["note"],
        "Game Weather": f"{weather['temp']}°F / {weather['wind']}mph {weather['dir']}",
        "Power": m["Power"],
        "Laser": m["Laser"],
        "Season HR": m["Season HR"],
        "Data Source": m["Data Source"],
        "Reasons": reasons
    }

# =========================
# BUILD GAME ROWS
# =========================
games_all = get_schedule()
VISIBLE_BAD_STATUSES = ["final", "game over", "completed early", "postponed", "cancelled"]
games = [g for g in games_all if not any(x in str(g.get("status","")).lower() for x in VISIBLE_BAD_STATUSES)]

rows = []
for g in games:
    matchup = f'{g["away"]} @ {g["home"]}'
    status = g.get("status", "")
    game_pk = g.get("gamePk")
    lu = get_lineups(game_pk)

    if g["home_p"]:
        if lu["away"]:
            for h in lu["away"]:
                r = score_row(h["name"], normalize_team(g["away"]), matchup, g["home_p"], g["home_p_id"], g["park"], status, game_pk, h["order"], "Final", h.get("id"))
                if r: rows.append(r)
        else:
            for _, b in batters[batters["_team"] == normalize_team(g["away"])].iterrows():
                r = score_row(b["_name"], normalize_team(g["away"]), matchup, g["home_p"], g["home_p_id"], g["park"], status, game_pk, batter_id=b.get("player_id", None))
                if r: rows.append(r)

    if g["away_p"]:
        if lu["home"]:
            for h in lu["home"]:
                r = score_row(h["name"], normalize_team(g["home"]), matchup, g["away_p"], g["away_p_id"], g["park"], status, game_pk, h["order"], "Final", h.get("id"))
                if r: rows.append(r)
        else:
            for _, b in batters[batters["_team"] == normalize_team(g["home"])].iterrows():
                r = score_row(b["_name"], normalize_team(g["home"]), matchup, g["away_p"], g["away_p_id"], g["park"], status, game_pk, batter_id=b.get("player_id", None))
                if r: rows.append(r)

df = pd.DataFrame(rows)
if df.empty:
    st.warning("No game rows created. Probable pitchers/lineups may not be posted yet.")
    st.stop()

df = df.sort_values("Dinger Score", ascending=False).reset_index(drop=True)
parlay_pool = df[df["Parlay Eligible"] == "Yes"].copy().sort_values("Dinger Score", ascending=False).reset_index(drop=True)

top_hr_pick = parlay_pool.head(1) if not parlay_pool.empty else df.head(1)
best_matchup_pick = parlay_pool.sort_values("Auto Matchup Edge", ascending=False).head(1) if not parlay_pool.empty else df.sort_values("Auto Matchup Edge", ascending=False).head(1)
top_mlb_api = df[df["Data Source"].astype(str).str.contains("MLB API", na=False)].sort_values("Dinger Score", ascending=False).head(20)

# =========================
# STRIKEOUT MODEL
# =========================
k_rows = []
for g in games:
    if not is_game_available_for_parlays(g.get("status","")):
        continue

    for name, pid, opp in [(g["away_p"], g["away_p_id"], g["home"]), (g["home_p"], g["home_p_id"], g["away"])]:
        if not name:
            continue
        live = pitcher_live(pid)
        proj_ks = clamp(3.8 + (live["k_rate"] - .20) * 18 + (live["k9"] - 8.0) * .35, 2.0, 10.5)

        def over_prob(line):
            return clamp(1 / (1 + math.exp(-(proj_ks - line))), .05, .92)

        k45 = round(over_prob(4.5) * 100, 1)
        k55 = round(over_prob(5.5) * 100, 1)
        k65 = round(over_prob(6.5) * 100, 1)
        best = max(k45, k55, k65)

        k_rows.append({
            "Pitcher": name,
            "Opponent": normalize_team(opp),
            "Projected Ks": round(proj_ks, 1),
            "Live K%": round(live["k_rate"] * 100, 1),
            "K/9": round(live["k9"], 1),
            "ERA": live["era"],
            "WHIP": live["whip"],
            "Over 4.5 K%": k45,
            "Over 5.5 K%": k55,
            "Over 6.5 K%": k65,
            "Best K%": best,
            "Grade": "A+" if best >= 75 else "A" if best >= 65 else "A-" if best >= 58 else "B" if best >= 50 else "C",
            "Pick Explanation": f"{name} projects for {round(proj_ks,1)} Ks using live K%, K/9, ERA, and WHIP."
        })

k_df = pd.DataFrame(k_rows).sort_values("Best K%", ascending=False) if k_rows else pd.DataFrame()

# =========================
# PARLAYS
# =========================
def tier_parlays(data, col, label, name_col="Player"):
    if data is None or data.empty:
        return pd.DataFrame()
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
            "Avg Model %": round(c[col].mean(), 1),
            "Model Combo Confidence": round((c[col] / 100).prod() * 100, 2),
            "Notes": f"Dynamic parlay: only games not started yet; group {i+1}-{i+3}"
        })
    return pd.DataFrame(out)

def smart_hr_parlays(data):
    if data is None or data.empty:
        return pd.DataFrame()

    pool = data.sort_values("Dinger Score", ascending=False).head(40).reset_index(drop=True)
    elite = pool[pool["Grade"].isin(["S+","S"])]
    strong = pool[pool["Grade"].isin(["A+","A"])]
    value = pool[pool["Grade"].isin(["B","C"])]

    parlays = []
    used = set()

    for i in range(5):
        legs = []
        for group in [elite, strong, value]:
            for _, r in group.iterrows():
                if r["Player"] in used:
                    continue
                if any(l["Matchup"] == r["Matchup"] for l in legs):
                    continue
                legs.append(r)
                used.add(r["Player"])
                break

        if len(legs) < 3:
            rem = pool[~pool["Player"].isin(used)]
            for _, r in rem.iterrows():
                if len(legs) >= 3:
                    break
                if any(l["Matchup"] == r["Matchup"] for l in legs):
                    continue
                legs.append(r)
                used.add(r["Player"])

        if len(legs) == 3:
            avg = round(sum(safe_float(l["HR %"]) for l in legs) / 3, 1)
            combo = round((safe_float(legs[0]["HR %"]) / 100) * (safe_float(legs[1]["HR %"]) / 100) * (safe_float(legs[2]["HR %"]) / 100) * 100, 2)
            parlays.append({
                "Parlay": f"Smart HR 3-Leg #{i+1}",
                "Leg 1 Anchor": f"{legs[0]['Player']} | {legs[0]['Grade']} | {legs[0]['HR %']}%",
                "Leg 2 Support": f"{legs[1]['Player']} | {legs[1]['Grade']} | {legs[1]['HR %']}%",
                "Leg 3 Value": f"{legs[2]['Player']} | {legs[2]['Grade']} | {legs[2]['HR %']}%",
                "Avg HR %": avg,
                "Model Combo Confidence": combo,
                "Strategy": "Dynamic: only games not started; 1 anchor + 1 support + 1 value; different games"
            })

    return pd.DataFrame(parlays)

def build_rotating_hr_combos(pool):
    if pool is None or pool.empty:
        return []
    generator_pool = pool.copy()
    generator_pool["Combo Score"] = (
        generator_pool["HR %"].apply(safe_float) * 0.45
        + generator_pool["Dinger Score"].apply(safe_float) * 0.30
        + generator_pool["Auto Matchup Edge"].apply(safe_float) * 25 * 0.25
        + generator_pool["Season HR"].apply(safe_float) * 0.10
    )
    generator_pool = generator_pool.sort_values("Combo Score", ascending=False).reset_index(drop=True)

    combos = []
    used_sets = set()
    for start in range(0, min(len(generator_pool), 30)):
        selected = []
        used_matchups = set()
        pool_rotated = pd.concat([generator_pool.iloc[start:], generator_pool.iloc[:start]]).reset_index(drop=True)

        for _, r in pool_rotated.iterrows():
            if len(selected) >= 3:
                break
            if r["Matchup"] in used_matchups:
                continue
            selected.append(r)
            used_matchups.add(r["Matchup"])

        if len(selected) < 3:
            for _, r in pool_rotated.iterrows():
                if len(selected) >= 3:
                    break
                if r["Player"] not in [x["Player"] for x in selected]:
                    selected.append(r)

        if len(selected) == 3:
            names = tuple(sorted([x["Player"] for x in selected]))
            if names not in used_sets:
                used_sets.add(names)
                combos.append(pd.DataFrame(selected))
    return combos


def build_hr_combos_by_legs(pool, legs=3, max_combos=6):
    """
    Builds rotating HR combos by leg count.
    Uses HR %, Dinger Score, Matchup Edge, Season HR, and avoids same-game overlap when possible.
    """
    if pool is None or pool.empty:
        return []

    generator_pool = pool.copy()
    generator_pool["Combo Score"] = (
        generator_pool["HR %"].apply(safe_float) * 0.45
        + generator_pool["Dinger Score"].apply(safe_float) * 0.30
        + generator_pool["Auto Matchup Edge"].apply(safe_float) * 25 * 0.25
        + generator_pool["Season HR"].apply(safe_float) * 0.10
    )
    generator_pool = generator_pool.sort_values("Combo Score", ascending=False).reset_index(drop=True)

    combos = []
    used_sets = set()

    for start in range(0, min(len(generator_pool), 50)):
        selected = []
        used_matchups = set()
        pool_rotated = pd.concat([generator_pool.iloc[start:], generator_pool.iloc[:start]]).reset_index(drop=True)

        for _, r in pool_rotated.iterrows():
            if len(selected) >= legs:
                break
            if r["Matchup"] in used_matchups:
                continue
            selected.append(r)
            used_matchups.add(r["Matchup"])

        if len(selected) < legs:
            for _, r in pool_rotated.iterrows():
                if len(selected) >= legs:
                    break
                if r["Player"] not in [x["Player"] for x in selected]:
                    selected.append(r)

        if len(selected) == legs:
            names = tuple(sorted([x["Player"] for x in selected]))
            if names not in used_sets:
                used_sets.add(names)
                combos.append(pd.DataFrame(selected))

        if len(combos) >= max_combos:
            break

    return combos

def combo_confidence(combo_df):
    if combo_df is None or combo_df.empty:
        return 0
    return round((combo_df["HR %"].apply(safe_float) / 100).prod() * 100, 4)

def combo_summary_table(combos, leg_label):
    rows = []
    for i, c in enumerate(combos, 1):
        row = {
            "Combo": f"{leg_label} Combo #{i}",
            "Model Combo Confidence": combo_confidence(c),
            "Avg HR %": round(c["HR %"].apply(safe_float).mean(), 1),
            "Avg Dinger Score": round(c["Dinger Score"].apply(safe_float).mean(), 1),
        }
        for j, (_, r) in enumerate(c.iterrows(), 1):
            row[f"Leg {j}"] = f"{r['Player']} ({r['HR %']}%)"
        rows.append(row)
    return pd.DataFrame(rows)

parlay_hr = smart_hr_parlays(parlay_pool)
parlay_hit = tier_parlays(parlay_pool, "Hit %", "Hit")
parlay_tb = tier_parlays(parlay_pool, "TB %", "TB")
parlay_rbi = tier_parlays(parlay_pool, "RBI %", "RBI")
parlay_laser = tier_parlays(parlay_pool, "Laser %", "Laser")
parlay_k = tier_parlays(k_df, "Best K%", "K", "Pitcher") if not k_df.empty else pd.DataFrame()

# =========================
# DISPLAY
# =========================
mobile_cols = ["Player","Team","Grade","Badge","HR %","Dinger Score","Auto Matchup Edge","Pitcher","Park","Game Weather","Weather Alert","Game Status","Parlay Eligible","Lineup","Order","Season HR","Data Source"]
full_cols = ["Player","Team","Matchup","Pitcher","Park","Game Weather","Weather Alert","Game Status","Parlay Eligible","Lineup","Order","Dinger Score","Grade","Badge","HR %","Hit %","TB %","RBI %","Laser %","Form","Auto Matchup Edge","Pitcher Risk","Park Edge","Weather Edge","Power","Laser","Season HR","Data Source"]
breakdown_cols = ["Player","Team","Matchup","Pitcher","Park","Game Weather","Weather Alert","Game Status","Parlay Eligible","Dinger Score","HR %","Auto Matchup Edge","Season HR","Data Source","Reasons"]

def render(data, cols=None):
    if data is None or data.empty:
        return "<div class='note'>No data available.</div>"

    if cols is None:
        cols = list(data.columns)
    else:
        cols = [c for c in cols if c in data.columns]

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
                style = "background:rgba(34,197,94,.38);font-weight:900;" if safe_float(v) >= 28 else "background:rgba(59,130,246,.28);font-weight:900;" if safe_float(v) >= 24 else "background:rgba(234,179,8,.22);font-weight:900;"
            elif c == "Parlay Eligible":
                style = "background:rgba(34,197,94,.25);font-weight:900;" if str(v) == "Yes" else "background:rgba(239,68,68,.22);font-weight:900;"
            elif c == "Data Source":
                style = "background:rgba(168,85,247,.25);font-weight:900;" if "MLB API" in str(v) else ""
            elif c == "Weather Alert":
                val = str(v)
                if "warm" in val or "boost" in val or "wind" in val:
                    style = "background:rgba(34,197,94,.25);font-weight:900;"
                elif "cold" in val or "downgrade" in val:
                    style = "background:rgba(239,68,68,.22);font-weight:900;"
                else:
                    style = "background:rgba(234,179,8,.16);font-weight:900;"
            elif c == "Bet Badge":
                val = str(v)
                if "Strong" in val:
                    style = "background:rgba(34,197,94,.32);font-weight:900;"
                elif "Good" in val:
                    style = "background:rgba(34,197,94,.22);font-weight:900;"
                elif "Lean" in val:
                    style = "background:rgba(234,179,8,.22);font-weight:900;"
                elif "Risk" in val:
                    style = "background:rgba(239,68,68,.22);font-weight:900;"
                else:
                    style = "background:rgba(148,163,184,.18);font-weight:900;"
            elif "%" in c or c in ["Avg Model %","Model Combo Confidence","Avg HR %"]:
                style = "background:rgba(34,197,94,.25);" if safe_float(v) >= 60 else "background:rgba(234,179,8,.18);" if safe_float(v) >= 35 else "background:rgba(239,68,68,.15);"
            elif c == "Form":
                val = str(v)
                style = "color:#86efac;font-weight:900;" if "Hot" in val else "color:#93c5fd;font-weight:900;" if "Good" in val else "color:#fde68a;font-weight:900;" if "Neutral" in val else "color:#fca5a5;font-weight:900;"
            elif c in ["Reasons","Pick Explanation","Notes","Strategy","Brief Note"]:
                style = "white-space:normal;min-width:520px;color:#cbd5e1;"
            elif c in ["Leg 1 Anchor","Leg 2 Support","Leg 3 Value","Leg 1","Leg 2","Leg 3"]:
                style = "font-weight:800;color:#e5e7eb;"
            html += f"<td style='{style}'>{v}</td>"
        html += "</tr>"

    html += "</table></div>"
    return html

def pick_card(title, data):
    if data is None or data.empty:
        return f"<div class='card'><h2>{title}</h2><p>No pick available.</p></div>"
    r = data.iloc[0]
    return f"""
    <div class='card'>
        <h2>{title}</h2>
        <h3>{r['Player']} — {r['Team']}</h3>
        <p><b>HR %:</b> {r['HR %']}% | <b>Dinger Score:</b> {r['Dinger Score']} | <b>Grade:</b> {r['Grade']} {r['Badge']}</p>
        <p><b>Matchup:</b> {r['Matchup']} vs {r['Pitcher']}</p>
        <p><b>Auto Matchup Edge:</b> {r['Auto Matchup Edge']} | <b>Park:</b> {r['Park']} | <b>Season HR:</b> {r.get('Season HR',0)}</p>
    </div>
    """


def render_dinger_board(data):
    if data is None or data.empty:
        return "<div class='note'>No dinger targets available.</div>"

    html = "<div class='dinger-board'>"
    for _, r in data.iterrows():
        rank = r.get("Dinger Rank", "")
        player = r.get("Player", "")
        team = r.get("Team", "")
        hand = ""
        grade = r.get("Grade", "")
        badge = r.get("Bet Badge", r.get("Badge", ""))
        hrp = r.get("HR %", "")
        season_hr = r.get("Season HR", 0)
        pitcher = r.get("Pitcher", "")
        weather = str(r.get("Weather Alert", ""))
        weather_short = "GOOD" if ("warm" in weather.lower() or "boost" in weather.lower() or "wind" in weather.lower()) else "BAD" if ("cold" in weather.lower() or "downgrade" in weather.lower()) else "NEUTRAL"
        pill_class = "dinger-pill-good" if weather_short == "GOOD" else "dinger-pill-bad" if weather_short == "BAD" else "dinger-pill-mid"
        note = r.get("Brief Note", "")

        html += f"""
        <div class='dinger-row'>
          <div class='dinger-rank'>{rank}</div>
          <div>
            <div class='dinger-name'>{player} <span class='dinger-pill {pill_class}'>{grade}</span></div>
            <div class='dinger-sub'>{team} • {badge}</div>
          </div>
          <div class='dinger-num'>{hrp}%<div class='dinger-sub'>MODEL</div></div>
          <div class='dinger-small'>{season_hr}<br>SEASON HR</div>
          <div class='dinger-small'><span class='dinger-pill {pill_class}'>{weather_short}</span><br>{r.get("Game Weather","")}</div>
          <div class='dinger-note'>{note}<br><b>vs {pitcher}</b></div>
        </div>
        """
    html += "</div>"
    return html


def tier_label_from_score(score):
    score = safe_float(score)
    if score >= 80:
        return "ELITE (≥80)"
    if score >= 70:
        return "VERY GOOD (70–79.9)"
    if score >= 60:
        return "GOOD (60–69.9)"
    if score >= 50:
        return "WORTH WATCHING (50–59.9)"
    return "LONG SHOT (<50)"

def tier_row_class(score):
    score = safe_float(score)
    if score >= 80:
        return "tier-row-elite"
    if score >= 70:
        return "tier-row-very"
    if score >= 60:
        return "tier-row-good"
    return "tier-row-watch"

def grade_pill_class(grade):
    grade = str(grade)
    if grade in ["S+", "S"]:
        return "tier-pill-s"
    if grade in ["A+", "A"]:
        return "tier-pill-a"
    if grade == "B":
        return "tier-pill-b"
    return "tier-pill-c"

def weather_class(alert):
    alert = str(alert).lower()
    if "warm" in alert or "boost" in alert or "wind" in alert:
        return "tier-weather-good"
    if "cold" in alert or "downgrade" in alert:
        return "tier-weather-bad"
    return "tier-weather-mid"

def render_ranked_tier_board(data):
    if data is None or data.empty:
        return "<div class='note'>No ranked dinger targets available.</div>"

    display = data.copy()
    html = "<div class='tier-board'>"
    html += "<div class='tier-head'><div>#</div><div>Player</div><div>TM</div><div>H</div><div>PWR</div><div>HR</div><div>CB</div><div>Weather</div></div>"

    tier_order = ["ELITE (≥80)", "VERY GOOD (70–79.9)", "GOOD (60–69.9)", "WORTH WATCHING (50–59.9)", "LONG SHOT (<50)"]

    for tier in tier_order:
        group = display[display["Tier Label"] == tier]
        if group.empty:
            continue

        html += f"<div class='tier-title'>—— {tier} ——</div>"

        for _, r in group.iterrows():
            score = safe_float(r.get("TRUE DINGER SCORE 100", 0))
            cls = tier_row_class(score)
            grade = r.get("Grade", "")
            pill_cls = grade_pill_class(grade)
            weather_cls = weather_class(r.get("Weather Alert", ""))
            player = r.get("Player", "")
            team = r.get("Team", "")
            hand = ""
            rank = r.get("Dinger Rank", "")
            pwr = r.get("Power", "")
            hr = r.get("Season HR", "")
            cb = r.get("Park Edge", "")
            hrp = r.get("HR %", "")
            bet = r.get("Bet Badge", "")
            weather = r.get("Game Weather", "")

            html += f"""
            <div class='tier-row {cls}'>
                <div class='tier-rank'>{rank}</div>
                <div class='tier-player'>{player} <span class='tier-pill {pill_cls}'>{grade}</span><span class='tier-sub'>{team} • {bet}</span></div>
                <div class='tier-cell'>{team}</div>
                <div class='tier-cell'>{hand}</div>
                <div class='tier-score'>{round(safe_float(pwr)*100)}</div>
                <div class='tier-score'>{hr}</div>
                <div class='tier-cell'>x{round(safe_float(cb),2)}</div>
                <div class='{weather_cls}'>{round(safe_float(hrp),1)}%<br>{weather}</div>
            </div>
            """
    html += "</div>"
    return html


def weather_badge_class(alert):
    alert = str(alert).lower()
    if "warm" in alert or "boost" in alert or "wind" in alert:
        return "target-weather-good", "GOOD"
    if "cold" in alert or "downgrade" in alert:
        return "target-weather-bad", "BAD"
    return "target-weather-mid", "NEUTRAL"

def grade_target_class(grade):
    grade = str(grade)
    if grade in ["S+", "S"]:
        return "target-pill-s"
    if grade in ["A+", "A"]:
        return "target-pill-a"
    if grade == "B":
        return "target-pill-b"
    return "target-pill-c"

def render_target_cards(data):
    if data is None or data.empty:
        return "<div class='note'>No dinger targets available.</div>"

    html = "<div class='target-card-wrap'>"

    for _, r in data.iterrows():
        rank = r.get("Dinger Rank", "")
        player = r.get("Player", "")
        team = r.get("Team", "")
        grade = r.get("Grade", "")
        bet = r.get("Bet Badge", r.get("Badge", ""))
        hrp = r.get("HR %", "")
        season_hr = r.get("Season HR", 0)
        power = round(safe_float(r.get("Power", 0)) * 100)
        park = round(safe_float(r.get("Park Edge", 0)), 2)
        weather = r.get("Game Weather", "")
        wcls, wlabel = weather_badge_class(r.get("Weather Alert", ""))
        gpill = grade_target_class(grade)
        pitcher = r.get("Pitcher", "")

        html += f"""
        <div class='target-card'>
            <div class='target-rank'>{rank}</div>
            <div>
                <div class='target-name'>{player} <span class='target-pill {gpill}'>{grade}</span></div>
                <div class='target-sub'>{team} • {bet} • vs {pitcher}</div>
            </div>
            <div class='target-num'>{hrp}%<span class='target-label'>MODEL</span></div>
            <div class='target-num'>{season_hr}<span class='target-label'>HR</span></div>
            <div class='target-num'>{power}<span class='target-label'>PWR</span></div>
            <div class='{wcls}'>{wlabel}<br>{weather}<br>x{park}</div>
        </div>
        """
    html += "</div>"
    return html

tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🏆 Slate Picks","📱 Mobile HR","📋 Full HR","🎯 Strikeouts","🧾 Dynamic Parlays","🔎 Breakdown","🛠 Debug"])

with tab0:
    st.subheader("🏆 Top Picks of the Slate")
    st.markdown(pick_card("💣 Top HR Pick of the Slate", top_hr_pick), unsafe_allow_html=True)

    best_k_pitcher = k_df.head(1) if not k_df.empty else pd.DataFrame()
    if not best_k_pitcher.empty:
        k = best_k_pitcher.iloc[0]
        st.markdown(f"""
        <div class='card'>
            <h2>🎯 Best Pitcher for K's</h2>
            <h3>{k['Pitcher']} vs {k['Opponent']}</h3>
            <p><b>Best K%:</b> {k['Best K%']}% | <b>Projected Ks:</b> {k['Projected Ks']} | <b>Grade:</b> {k['Grade']}</p>
            <p><b>K/9:</b> {k['K/9']} | <b>ERA:</b> {k['ERA']} | <b>WHIP:</b> {k['WHIP']}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("<div class='card'><h2>🎯 Best Pitcher for K's</h2><p>No K picks available.</p></div>", unsafe_allow_html=True)

    st.markdown("### ✅ Best 10 Players for Hits")
    best_hits_10 = parlay_pool.sort_values("Hit %", ascending=False).head(10) if not parlay_pool.empty else df.sort_values("Hit %", ascending=False).head(10)
    st.markdown(render(best_hits_10, ["Player","Team","Hit %","Grade","Pitcher","Park","Game Status","Lineup","Order","Season HR","Data Source"]), unsafe_allow_html=True)

    st.markdown("### 📌 Top 10 HR Board — Full Merged List")
    st.markdown(render(df.head(10), ["Player","Team","HR %","Dinger Score","Grade","Pitcher","Park","Game Status","Auto Matchup Edge","Season HR","Data Source"]), unsafe_allow_html=True)

    st.markdown("### 👑 Injected MLB Players in Today’s Matchups")
    st.markdown(render(top_mlb_api, ["Player","Team","HR %","Dinger Score","Grade","Pitcher","Park","Game Status","Season HR","Data Source"]), unsafe_allow_html=True)

with tab1:
    st.subheader("📱 Mobile-Friendly Best HR Plays")
    st.caption(f"Active/upcoming games shown: {len(games)} | Dynamic parlay pool players: {len(parlay_pool)} | Auto refresh: 5 min")
    st.markdown(render(df.head(40), mobile_cols), unsafe_allow_html=True)

with tab2:
    st.subheader("📋 Full AON BETS HR MODEL")
    st.markdown(render(df, full_cols), unsafe_allow_html=True)

with tab3:
    st.subheader("🎯 Live Pitcher Strikeout Model")
    st.markdown(render(k_df, ["Pitcher","Opponent","Projected Ks","Best K%","Grade","K/9","ERA","WHIP"]), unsafe_allow_html=True)

with tab4:
    st.subheader("🧾 Dynamic Parlays + Daily Dinger List")

    st.markdown("<div class='note'>Top dinger targets are now ranked heavily by Power, Recent Form, Park, Weather, Matchup Edge, and Pitcher HR weakness.</div>", unsafe_allow_html=True)

    st.markdown("### 📝 Top 25 Most Likely To Go Yard")

    dinger_list = parlay_pool.copy() if not parlay_pool.empty else df.copy()

    if not dinger_list.empty:
        dinger_list["TRUE DINGER SCORE"] = (
            dinger_list["Power"].apply(safe_float) * 0.35
            + dinger_list.get("Form Score", pd.Series([0.5] * len(dinger_list))).apply(safe_float) * 0.20
            + dinger_list["Park Edge"].apply(safe_float) * 0.15
            + dinger_list["Weather Edge"].apply(safe_float) * 0.15
            + dinger_list["Auto Matchup Edge"].apply(safe_float) * 0.10
            + dinger_list["Pitcher Risk"].apply(safe_float) * 0.05
        )
        dinger_list["TRUE DINGER SCORE 100"] = (dinger_list["TRUE DINGER SCORE"] * 100).round(1)

        dinger_list = dinger_list.sort_values("TRUE DINGER SCORE", ascending=False).reset_index(drop=True)
        dinger_list["Dinger Rank"] = range(1, len(dinger_list) + 1)
        dinger_list["Bet Badge"] = dinger_list.apply(bet_badge, axis=1)
        dinger_list["Tier Label"] = dinger_list["TRUE DINGER SCORE 100"].apply(tier_label_from_score)

        def dinger_note_row(r):
            return (
                f"Power {r['Power']} • "
                f"Form {round(safe_float(r.get('Form Score',0.5)),2)} • "
                f"Park {r['Park Edge']} • "
                f"Weather {r['Weather Edge']} • "
                f"PitcherRisk {r['Pitcher Risk']}"
            )

        dinger_list["Brief Note"] = dinger_list.apply(dinger_note_row, axis=1)

        st.markdown(render(dinger_list.head(25), ["Dinger Rank","Player","Team","Bet Badge","Badge","HR %","TRUE DINGER SCORE 100","Dinger Score","Grade","Season HR","Game Weather","Weather Alert","Pitcher","Pitcher Risk","Auto Matchup Edge","Power","Form Score","Park Edge","Weather Edge"]), unsafe_allow_html=True)

    st.markdown("### 🏆 Best 3-Leg HR Parlay by Tier")

    def tiered_best_3_leg(pool):
        if pool is None or pool.empty:
            return pd.DataFrame()

        tier_order = ["S+", "S", "A+", "A", "B", "C", "D"]
        selected = []
        used_players = set()
        used_matchups = set()

        for tier in tier_order:
            tier_pool = pool[pool["Grade"] == tier].copy()
            if tier_pool.empty:
                continue

            tier_pool["Tier Combo Score"] = (
                tier_pool["HR %"].apply(safe_float) * 0.30
                + tier_pool["Power"].apply(safe_float) * 25 * 0.25
                + tier_pool.get("Form Score", pd.Series([0.5] * len(tier_pool))).apply(safe_float) * 25 * 0.15
                + tier_pool["Park Edge"].apply(safe_float) * 25 * 0.10
                + tier_pool["Weather Edge"].apply(safe_float) * 25 * 0.10
                + tier_pool["Auto Matchup Edge"].apply(safe_float) * 25 * 0.07
                + tier_pool["Pitcher Risk"].apply(safe_float) * 25 * 0.03
            )

            tier_pool = tier_pool.sort_values("Tier Combo Score", ascending=False)

            for _, r in tier_pool.iterrows():
                if len(selected) >= 3:
                    break
                if r["Player"] in used_players:
                    continue
                if r["Matchup"] in used_matchups:
                    continue

                selected.append(r)
                used_players.add(r["Player"])
                used_matchups.add(r["Matchup"])
                break

            if len(selected) >= 3:
                break

        if len(selected) < 3:
            fallback = pool.copy()
            fallback["Tier Combo Score"] = (
                fallback["HR %"].apply(safe_float) * 0.30
                + fallback["Power"].apply(safe_float) * 25 * 0.25
                + fallback.get("Form Score", pd.Series([0.5] * len(fallback))).apply(safe_float) * 25 * 0.15
                + fallback["Park Edge"].apply(safe_float) * 25 * 0.10
                + fallback["Weather Edge"].apply(safe_float) * 25 * 0.10
                + fallback["Auto Matchup Edge"].apply(safe_float) * 25 * 0.07
                + fallback["Pitcher Risk"].apply(safe_float) * 25 * 0.03
            )
            fallback = fallback.sort_values("Tier Combo Score", ascending=False)

            for _, r in fallback.iterrows():
                if len(selected) >= 3:
                    break
                if r["Player"] in used_players:
                    continue

                selected.append(r)
                used_players.add(r["Player"])

        return pd.DataFrame(selected)

    tier_3 = tiered_best_3_leg(parlay_pool)

    if len(tier_3) == 3:
        tier_combo_conf = round(
            (tier_3["HR %"].apply(safe_float) / 100).prod() * 100,
            4
        )

        st.success(f"Best Tiered 3-Leg HR Parlay | Combo Confidence: {tier_combo_conf}%")

        st.markdown(render(
            tier_3,
            ["Player","Team","Grade","Badge","HR %","Dinger Score","Pitcher","Pitcher Risk","Park","Game Weather","Weather Alert","Game Status","Auto Matchup Edge","Season HR","Data Source","Tier Combo Score"]
        ), unsafe_allow_html=True)
    else:
        st.warning("Not enough eligible players to build a tiered 3-leg HR parlay.")

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
    st.subheader("🔎 Pick Breakdown / Reasons")
    st.markdown(render(df.head(80), breakdown_cols), unsafe_allow_html=True)

with tab6:
    st.write("Players scored:", len(df))
    st.write("Dynamic parlay pool players:", len(parlay_pool))
    st.write("Pitchers scored:", len(k_df))
    st.write("Games loaded:", len(games_all))
    st.write("Upcoming/non-final games shown:", len(games))
    st.write("Original batters.csv rows + injected MLB players:", len(batters))
    st.write("All MLB hitters pulled:", len(mlb_players))
    st.write("Season HR fix:", "Uses MLB player ID live season hitting stats when available")
    st.write("Missing MLB players injected:", mlb_injected_count)
    st.write("Game statuses:")
    st.dataframe(pd.DataFrame(games_all)[["away","home","park","status"]] if games_all else pd.DataFrame(), use_container_width=True)
    st.write("Detected columns:")
    st.json({
        "pa": b_pa,
        "bip": b_bip,
        "ba": b_ba,
        "est_ba": b_est_ba,
        "slg": b_slg,
        "est_slg": b_est_slg,
        "woba": b_woba,
        "est_woba": b_est_woba,
        "barrel": b_barrel,
        "hard_hit": b_hard,
        "iso": b_iso,
        "recent": b_recent,
        "season_hr": b_season_hr,
        "team": b_team
    })
