import math, time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="AON BETS HR MODEL ⚾️ 💣", layout="wide")

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
.table-wrap { overflow-x:auto; border:1px solid #1f2937; border-radius:16px; margin-bottom:18px; }
.ai-table { width:100%; border-collapse:collapse; background:#0b1220; color:white; font-size:13px; }
.ai-table th { background:#111827; padding:9px; text-align:left; white-space:nowrap; }
.ai-table td { padding:8px; border-bottom:1px solid rgba(255,255,255,.08); white-space:nowrap; }
.note { background:#0b1220; border:1px solid #1f2937; border-radius:14px; padding:12px; color:#cbd5e1; }
.card { background:#0b1220; border:1px solid #1f2937; border-radius:18px; padding:16px; margin-bottom:14px; }
.card h2 { margin-top:0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class='hero'>
<h1>🔥 AON BETS HR MODEL ⚾️ 💣</h1>
<p>Top HR Pick • Best Batter vs Pitcher Matchup • Daily HR Tracker • Dynamic Parlays • Strikeouts</p>
</div>
""", unsafe_allow_html=True)

def clamp(x,a,b): return max(a,min(b,x))

def safe_float(x,d=0.0):
    try:
        if pd.isna(x): return d
        return float(x)
    except:
        return d

def scale01(x,a,b):
    try:
        x=float(x)
        if a==b: return .5
        return clamp((x-a)/(b-a),0,1)
    except:
        return .5

def norm(x):
    return " ".join(str(x).lower().replace(",","").strip().split())

def first_last(x):
    x=str(x).strip()
    if "," in x:
        last,first=[p.strip() for p in x.split(",",1)]
        return f"{first} {last}"
    return x

def find_col(df,names):
    if df is None or df.empty:
        return None
    cols={str(c).lower().strip():c for c in df.columns}
    for n in names:
        if n.lower() in cols:
            return cols[n.lower()]
    for n in names:
        for c in df.columns:
            if n.lower() in str(c).lower():
                return c
    return None

def make_name(df):
    c=find_col(df,["last_name, first_name","last_name_first_name"])
    if c: return df[c].astype(str).apply(first_last)
    c=find_col(df,["player_name","name","player","pitcher_name"])
    if c: return df[c].astype(str).apply(first_last)
    st.error(f"Could not find player name column. Found: {list(df.columns)}")
    st.stop()

def normalize_team(t):
    t=norm(t)
    m={
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
    return m.get(t,str(t).upper()[:3])

def player_match(a,b):
    a=norm(first_last(a))
    b=norm(first_last(b))
    if a==b: return True
    ap=a.split(); bp=b.split()
    return len(ap)>=2 and len(bp)>=2 and ap[-1]==bp[-1] and ap[0][0]==bp[0][0]

def find_player(df,name):
    if not name or df.empty:
        return None
    hits=df[df["_name"].apply(lambda x: player_match(x,name))]
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

def color_grade(g):
    return {
        "S+":"#7f1d1d","S":"#166534","A+":"#15803d",
        "A":"#2563eb","B":"#6d28d9","C":"#92400e","D":"#374151"
    }.get(g,"#374151")

def is_game_available_for_parlays(status):
    s = str(status).lower().strip()
    bad = ["in progress","live","final","game over","completed early","delayed","suspended","postponed","cancelled"]
    return not any(x in s for x in bad)

STADIUM_DATA={
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
}

def stadium_info(park):
    for k,v in STADIUM_DATA.items():
        if norm(k)==norm(park):
            return v
    return ("","",1.00)

def park_note(factor):
    if factor >= 1.15: return "🔥 HR park boost"
    if factor <= 0.92: return "❄️ pitcher-friendly park"
    return "⚖️ neutral park"

@st.cache_data(ttl=1800)
def get_weather(city,state):
    if not city:
        return {"temp":"N/A","wind":"N/A","dir":"N/A","factor":1.0,"note":"⚖️ weather neutral"}
    try:
        q=f"{city},{state}".replace(" ","%20")
        data=requests.get(f"https://wttr.in/{q}?format=j1",timeout=15).json()
        cur=data["current_condition"][0]
        temp=safe_float(cur.get("temp_F"),70)
        wind=safe_float(cur.get("windspeedMiles"),7)
        direction=cur.get("winddir16Point","N/A")
    except:
        return {"temp":"N/A","wind":"N/A","dir":"N/A","factor":1.0,"note":"⚖️ weather neutral"}

    factor=1.0
    note="⚖️ weather neutral"
    if temp >= 80:
        factor += .05
        note="🔥 warm air boost"
    elif temp <= 55:
        factor -= .05
        note="❄️ cold air downgrade"
    if wind >= 10:
        factor += .04
        note += f" • wind {direction} {wind}mph"
    return {"temp":temp,"wind":wind,"dir":direction,"factor":factor,"note":note}

@st.cache_data(ttl=300)
def get_schedule():
    today=time.strftime("%Y-%m-%d")
    url=f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher,team"
    try:
        data=requests.get(url,timeout=20).json()
    except:
        return []
    games=[]
    for d in data.get("dates",[]):
        for g in d.get("games",[]):
            games.append({
                "gamePk":g.get("gamePk"),
                "away":g["teams"]["away"]["team"]["name"],
                "home":g["teams"]["home"]["team"]["name"],
                "away_p":g["teams"]["away"].get("probablePitcher",{}).get("fullName",""),
                "home_p":g["teams"]["home"].get("probablePitcher",{}).get("fullName",""),
                "away_p_id":g["teams"]["away"].get("probablePitcher",{}).get("id",None),
                "home_p_id":g["teams"]["home"].get("probablePitcher",{}).get("id",None),
                "park":g.get("venue",{}).get("name",""),
                "status":g.get("status",{}).get("detailedState","")
            })
    return games

@st.cache_data(ttl=300)
def get_lineups(game_pk):
    try:
        data=requests.get(f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live",timeout=20).json()
    except:
        return {"away":[],"home":[]}

    def side(which):
        box=data.get("liveData",{}).get("boxscore",{}).get("teams",{}).get(which,{})
        order=box.get("battingOrder",[]) or []
        players=box.get("players",{}) or {}
        out=[]
        for idx,pid in enumerate(order,1):
            p=players.get(f"ID{pid}",{})
            name=p.get("person",{}).get("fullName","")
            if name:
                out.append({"name":name,"order":idx})
        return out

    return {"away":side("away"),"home":side("home")}

@st.cache_data(ttl=300)
def hr_tracker_for_game(game_pk):
    try:
        data=requests.get(f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live",timeout=20).json()
    except:
        return {}

    out={}
    box=data.get("liveData",{}).get("boxscore",{}).get("teams",{})
    for side in ["away","home"]:
        players=box.get(side,{}).get("players",{}) or {}
        for _,p in players.items():
            name=p.get("person",{}).get("fullName","")
            batting=p.get("stats",{}).get("batting",{})
            hrs=safe_float(batting.get("homeRuns",0),0)
            if name:
                out[norm(name)] = int(hrs)
    return out

@st.cache_data(ttl=86400)
def build_roster():
    out=[]
    try:
        teams=requests.get("https://statsapi.mlb.com/api/v1/teams?sportId=1",timeout=20).json().get("teams",[])
    except:
        return pd.DataFrame(columns=["name","team","_norm"])
    for t in teams:
        team=normalize_team(t.get("name",""))
        tid=t.get("id")
        try:
            roster=requests.get(f"https://statsapi.mlb.com/api/v1/teams/{tid}/roster",timeout=20).json().get("roster",[])
        except:
            roster=[]
        for p in roster:
            name=p.get("person",{}).get("fullName","")
            if name:
                out.append({"name":name,"team":team,"_norm":norm(name)})
    return pd.DataFrame(out)

@st.cache_data(ttl=1800)
def pitcher_live(pid):
    if not pid:
        return {"k_rate":.22,"k9":8.0,"era":4.20,"whip":1.30,"hr9":1.10,"hand":"R"}

    try:
        season=time.strftime("%Y")
        bio=requests.get(f"https://statsapi.mlb.com/api/v1/people/{pid}",timeout=20).json()
        person=bio.get("people",[{}])[0]
        hand=person.get("pitchHand",{}).get("code","R")

        url=f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=season&group=pitching&season={season}"
        data=requests.get(url,timeout=20).json()
        splits=data.get("stats",[{}])[0].get("splits",[])
        if not splits:
            return {"k_rate":.22,"k9":8.0,"era":4.20,"whip":1.30,"hr9":1.10,"hand":hand}

        s=splits[0].get("stat",{})
        ip=safe_float(s.get("inningsPitched",0))
        so=safe_float(s.get("strikeOuts",0))
        bf=safe_float(s.get("battersFaced",0))
        hr=safe_float(s.get("homeRuns",0))

        return {
            "k_rate":so/bf if bf>0 else .22,
            "k9":(so/ip)*9 if ip>0 else 8.0,
            "era":safe_float(s.get("era",4.20)),
            "whip":safe_float(s.get("whip",1.30)),
            "hr9":(hr/ip)*9 if ip>0 else 1.10,
            "hand":hand
        }
    except:
        return {"k_rate":.22,"k9":8.0,"era":4.20,"whip":1.30,"hr9":1.10,"hand":"R"}

try:
    batters=pd.read_csv("batters.csv")
except Exception as e:
    st.error(f"batters.csv load error: {e}")
    st.stop()

batters["_name"]=make_name(batters)
roster=build_roster()

b_team=find_col(batters,["team","player_team","bat_team","team_name","club","team_abbrev","team_abbr"])
if b_team:
    batters["_team"]=batters[b_team].astype(str).apply(normalize_team)
else:
    lookup=dict(zip(roster["_norm"],roster["team"])) if not roster.empty else {}
    batters["_team"]=batters["_name"].apply(lambda x: lookup.get(norm(x),"N/A"))

b_pa=find_col(batters,["pa"])
b_bip=find_col(batters,["bip"])
b_ba=find_col(batters,["ba"])
b_est_ba=find_col(batters,["est_ba","xba"])
b_slg=find_col(batters,["slg"])
b_est_slg=find_col(batters,["est_slg","xslg"])
b_woba=find_col(batters,["woba"])
b_est_woba=find_col(batters,["est_woba","xwoba"])
b_barrel=find_col(batters,["barrel","barrel_pct","brl"])
b_hard=find_col(batters,["hard_hit","hardhit","hard_hit_pct"])
b_iso=find_col(batters,["iso"])
b_recent=find_col(batters,["last7_slg","last7","last14","recent","recent_form"])

def pitcher_risk(live):
    return clamp(
        .45*scale01(live.get("hr9",1.1),.3,2.2)
        + .30*scale01(live.get("era",4.2),2.5,6.0)
        + .25*scale01(live.get("whip",1.3),.9,1.7),
        0,1
    )

def batter_metrics(row):
    pa=safe_float(row[b_pa],250) if b_pa else 250
    bip=safe_float(row[b_bip],150) if b_bip else 150
    ba=safe_float(row[b_ba],.245) if b_ba else .245
    est_ba=safe_float(row[b_est_ba],ba) if b_est_ba else ba
    slg=safe_float(row[b_slg],.400) if b_slg else .400
    est_slg=safe_float(row[b_est_slg],slg) if b_est_slg else slg
    woba=safe_float(row[b_woba],.310) if b_woba else .310
    est_woba=safe_float(row[b_est_woba],woba) if b_est_woba else woba
    iso=safe_float(row[b_iso],est_slg-est_ba) if b_iso else est_slg-est_ba
    barrel=safe_float(row[b_barrel],None) if b_barrel else None
    hard=safe_float(row[b_hard],None) if b_hard else None

    if barrel is not None and barrel>1: barrel/=100
    if hard is not None and hard>1: hard/=100

    power=clamp(
        .42*scale01(est_slg,.300,.700)
        + .28*scale01(est_woba,.250,.450)
        + .18*scale01(iso,.080,.350)
        + .12*scale01(pa,50,650),
        0,1
    )
    if barrel is not None:
        power=clamp(power*.82+scale01(barrel,.02,.22)*.18,0,1)
    if hard is not None:
        power=clamp(power*.88+scale01(hard,.25,.60)*.12,0,1)

    contact=clamp(.50*scale01(est_ba,.190,.330)+.35*scale01(est_woba,.250,.450)+.15*scale01(bip,40,500),0,1)
    laser=clamp(.55*scale01(est_slg,.300,.700)+.30*scale01(est_woba,.250,.450)+.15*(scale01(hard,.25,.60) if hard is not None else .50),0,1)

    if b_recent:
        recent=safe_float(row[b_recent],None)
        form_score=scale01(recent,.180,.360) if recent not in [None,0] else power*.55+contact*.25+laser*.20
    else:
        form_score=power*.55+contact*.25+laser*.20

    form="🔥 Hot" if form_score>=.70 or power>=.78 or laser>=.78 else "✅ Good" if form_score>=.50 or power>=.58 or laser>=.58 else "⚠️ Neutral" if form_score>=.35 else "❄️ Cold"

    return {
        "Power":round(power,2),
        "Contact":round(contact,2),
        "Laser":round(laser,2),
        "Form Score":round(form_score,2),
        "Form":form,
        "estSLG":round(est_slg,3),
        "estwOBA":round(est_woba,3),
        "estBA":round(est_ba,3),
        "ISO":round(iso,3)
    }

def auto_matchup_edge(m, live, park_edge, weather_edge, lineup_edge):
    pitcher_hr = pitcher_risk(live)
    pitcher_k = scale01(live.get("k_rate",.22),.16,.34)

    raw = (
        .34*m["Power"]
        + .18*m["Laser"]
        + .13*m["Form Score"]
        + .18*pitcher_hr
        + .07*park_edge
        + .05*weather_edge
        + .05*lineup_edge
        - .10*pitcher_k
    )

    edge = clamp(raw,0,1)
    note = (
        f"auto edge from batter power + pitcher HR risk + K risk; "
        f"pitcher hand {live.get('hand','R')} • K risk {round(pitcher_k,2)}"
    )
    return edge, note

def hr_tracker_label(player_name, game_pk, game_status):
    tracker = hr_tracker_for_game(game_pk)
    hrs = tracker.get(norm(player_name), 0)
    s = str(game_status).lower()

    if hrs >= 1:
        return f"✅ HR ({hrs})"

    if "final" in s or "game over" in s or "completed" in s:
        return "❌ No HR"

    if "in progress" in s or "live" in s:
        return "⏳ Live - 0 HR"

    return "🕒 Pending"

def score_row(player_name, team, matchup, pitcher_name, pitcher_id, park, game_status, game_pk, order="—", lineup="Projected"):
    b=find_player(batters,player_name)
    if b is None:
        return None

    m=batter_metrics(b)
    live=pitcher_live(pitcher_id)
    pr=pitcher_risk(live)

    city,state,park_factor=stadium_info(park)
    weather=get_weather(city,state)

    park_edge=scale01(park_factor,.82,1.30)
    weather_edge=scale01(weather["factor"],.88,1.18)
    lineup_edge=1-scale01(order,1,9) if isinstance(order,int) else .50
    me,me_note=auto_matchup_edge(m,live,park_edge,weather_edge,lineup_edge)

    dinger_score=round(clamp(
        10*m["Power"]
        + 6*m["Laser"]
        + 5*m["Contact"]
        + 4*m["Form Score"]
        + 7*me
        + 4*pr
        + 3*park_edge
        + 3*weather_edge
        + 2*lineup_edge,
        0,42
    ),1)

    hr_prob=clamp(
        .035 + (
            .26*m["Power"]
            + .17*m["Laser"]
            + .11*m["Form Score"]
            + .20*me
            + .13*pr
            + .07*park_edge
            + .04*weather_edge
            + .02*lineup_edge
        )*.34,
        .010,.40
    )

    hit_prob=clamp(.28 + m["Contact"]*.42, .18, .82)
    tb_prob=clamp(.20 + (m["Power"]*.43 + m["Contact"]*.22 + m["Laser"]*.20 + me*.15)*.48, .10, .76)
    rbi_prob=clamp(.12 + (m["Power"]*.43 + m["Laser"]*.17 + pr*.25 + me*.15)*.42, .06, .62)
    laser_prob=clamp(.15 + m["Laser"]*.62 + me*.08, .10, .82)

    tracker = hr_tracker_label(player_name, game_pk, game_status)

    reasons=(
        f"{m['Form']} • Auto Matchup Edge {round(me,2)} ({me_note}) • "
        f"Matchup: {matchup} vs {pitcher_name} • "
        f"Game Status: {game_status} • HR Tracker: {tracker} • "
        f"Pitcher Risk {round(pr,2)} HR/9 {round(live['hr9'],2)} ERA {live['era']} WHIP {live['whip']} • "
        f"Park: {park} {park_note(park_factor)} ({park_factor}) • "
        f"Weather: {weather['note']} {weather['temp']}°F wind {weather['wind']}mph {weather['dir']} • "
        f"Power {m['Power']} • Laser {m['Laser']} • estSLG {m['estSLG']} • ISO {m['ISO']}"
    )

    return {
        "Player":player_name,
        "Team":team,
        "Matchup":matchup,
        "Pitcher":pitcher_name,
        "Park":park,
        "Game Status":game_status,
        "HR Tracker":tracker,
        "Parlay Eligible":"Yes" if is_game_available_for_parlays(game_status) else "No",
        "Lineup":lineup,
        "Order":order,
        "Dinger Score":dinger_score,
        "Grade":grade_score(dinger_score),
        "Badge":badge_score(dinger_score),
        "HR %":round(hr_prob*100,1),
        "Hit %":round(hit_prob*100,1),
        "TB %":round(tb_prob*100,1),
        "RBI %":round(rbi_prob*100,1),
        "Laser %":round(laser_prob*100,1),
        "Form":m["Form"],
        "Auto Matchup Edge":round(me,2),
        "Pitcher Risk":round(pr,2),
        "Park Edge":round(park_edge,2),
        "Weather Edge":round(weather_edge,2),
        "Power":m["Power"],
        "Laser":m["Laser"],
        "Reasons":reasons
    }

games_all=get_schedule()

VISIBLE_BAD_STATUSES=["postponed","cancelled"]
games=[
    g for g in games_all
    if not any(x in str(g.get("status","")).lower() for x in VISIBLE_BAD_STATUSES)
]

rows=[]
for g in games:
    matchup=f'{g["away"]} @ {g["home"]}'
    status=g.get("status","")
    game_pk=g.get("gamePk")
    lu=get_lineups(game_pk)

    if g["home_p"]:
        if lu["away"]:
            for h in lu["away"]:
                r=score_row(h["name"], normalize_team(g["away"]), matchup, g["home_p"], g["home_p_id"], g["park"], status, game_pk, h["order"], "Final")
                if r: rows.append(r)
        else:
            for _,b in batters[batters["_team"]==normalize_team(g["away"])].iterrows():
                r=score_row(b["_name"], normalize_team(g["away"]), matchup, g["home_p"], g["home_p_id"], g["park"], status, game_pk)
                if r: rows.append(r)

    if g["away_p"]:
        if lu["home"]:
            for h in lu["home"]:
                r=score_row(h["name"], normalize_team(g["home"]), matchup, g["away_p"], g["away_p_id"], g["park"], status, game_pk, h["order"], "Final")
                if r: rows.append(r)
        else:
            for _,b in batters[batters["_team"]==normalize_team(g["home"])].iterrows():
                r=score_row(b["_name"], normalize_team(g["home"]), matchup, g["away_p"], g["away_p_id"], g["park"], status, game_pk)
                if r: rows.append(r)

df=pd.DataFrame(rows)
if df.empty:
    st.warning("No game rows created. Probable pitchers/lineups may not be posted yet.")
    st.stop()

df=df.sort_values("Dinger Score", ascending=False).reset_index(drop=True)

parlay_pool=df[df["Parlay Eligible"]=="Yes"].copy()
parlay_pool=parlay_pool.sort_values("Dinger Score", ascending=False).reset_index(drop=True)

top_hr_pick = parlay_pool.head(1) if not parlay_pool.empty else df.head(1)
best_matchup_pick = parlay_pool.sort_values("Auto Matchup Edge", ascending=False).head(1) if not parlay_pool.empty else df.sort_values("Auto Matchup Edge", ascending=False).head(1)

k_rows=[]
for g in games:
    if not is_game_available_for_parlays(g.get("status","")):
        continue

    for name,pid,opp in [(g["away_p"],g["away_p_id"],g["home"]),(g["home_p"],g["home_p_id"],g["away"])]:
        if not name: continue
        live=pitcher_live(pid)
        proj_ks=clamp(3.8+(live["k_rate"]-.20)*18+(live["k9"]-8.0)*.35,2.0,10.5)

        def over_prob(line):
            return clamp(1/(1+math.exp(-(proj_ks-line))),.05,.92)

        k45=round(over_prob(4.5)*100,1)
        k55=round(over_prob(5.5)*100,1)
        k65=round(over_prob(6.5)*100,1)
        best=max(k45,k55,k65)

        k_rows.append({
            "Pitcher":name,
            "Opponent":normalize_team(opp),
            "Projected Ks":round(proj_ks,1),
            "Live K%":round(live["k_rate"]*100,1),
            "K/9":round(live["k9"],1),
            "ERA":live["era"],
            "WHIP":live["whip"],
            "Over 4.5 K%":k45,
            "Over 5.5 K%":k55,
            "Over 6.5 K%":k65,
            "Best K%":best,
            "Grade":"A+" if best>=75 else "A" if best>=65 else "A-" if best>=58 else "B" if best>=50 else "C",
            "Pick Explanation":f"{name} projects for {round(proj_ks,1)} Ks using live K%, K/9, ERA, and WHIP."
        })

k_df=pd.DataFrame(k_rows).sort_values("Best K%", ascending=False) if k_rows else pd.DataFrame()

def tier_parlays(data, col, label, name_col="Player"):
    if data is None or data.empty:
        return pd.DataFrame()
    pool=data.sort_values(col, ascending=False).head(15).reset_index(drop=True)
    out=[]
    for i in range(0,15,3):
        c=pool.iloc[i:i+3]
        if len(c)<3: continue
        out.append({
            "Parlay":f"{label} 3-Leg #{len(out)+1}",
            "Leg 1":f"{c.iloc[0][name_col]} ({c.iloc[0][col]}%)",
            "Leg 2":f"{c.iloc[1][name_col]} ({c.iloc[1][col]}%)",
            "Leg 3":f"{c.iloc[2][name_col]} ({c.iloc[2][col]}%)",
            "Avg Model %":round(c[col].mean(),1),
            "Model Combo Confidence":round((c[col]/100).prod()*100,2),
            "Notes":f"Dynamic parlay: only games not started yet; group {i+1}-{i+3}"
        })
    return pd.DataFrame(out)

def smart_hr_parlays(data):
    if data is None or data.empty:
        return pd.DataFrame()

    pool=data.sort_values("Dinger Score", ascending=False).head(40).reset_index(drop=True)
    elite=pool[pool["Grade"].isin(["S+","S"])]
    strong=pool[pool["Grade"].isin(["A+","A"])]
    value=pool[pool["Grade"].isin(["B","C"])]

    parlays=[]
    used=set()

    for i in range(5):
        legs=[]
        for group in [elite,strong,value]:
            for _,r in group.iterrows():
                if r["Player"] in used: continue
                if any(l["Matchup"]==r["Matchup"] for l in legs): continue
                legs.append(r)
                used.add(r["Player"])
                break

        if len(legs)<3:
            rem=pool[~pool["Player"].isin(used)]
            for _,r in rem.iterrows():
                if len(legs)>=3: break
                if any(l["Matchup"]==r["Matchup"] for l in legs): continue
                legs.append(r)
                used.add(r["Player"])

        if len(legs)==3:
            avg=round(sum(safe_float(l["HR %"]) for l in legs)/3,1)
            combo=round((safe_float(legs[0]["HR %"])/100)*(safe_float(legs[1]["HR %"])/100)*(safe_float(legs[2]["HR %"])/100)*100,2)
            parlays.append({
                "Parlay":f"Smart HR 3-Leg #{i+1}",
                "Leg 1 Anchor":f"{legs[0]['Player']} | {legs[0]['Grade']} | {legs[0]['HR %']}%",
                "Leg 2 Support":f"{legs[1]['Player']} | {legs[1]['Grade']} | {legs[1]['HR %']}%",
                "Leg 3 Value":f"{legs[2]['Player']} | {legs[2]['Grade']} | {legs[2]['HR %']}%",
                "Avg HR %":avg,
                "Model Combo Confidence":combo,
                "Strategy":"Dynamic: only games not started; 1 anchor + 1 support + 1 value; different games"
            })

    return pd.DataFrame(parlays)

parlay_hr=smart_hr_parlays(parlay_pool)
parlay_hit=tier_parlays(parlay_pool,"Hit %","Hit")
parlay_tb=tier_parlays(parlay_pool,"TB %","TB")
parlay_rbi=tier_parlays(parlay_pool,"RBI %","RBI")
parlay_laser=tier_parlays(parlay_pool,"Laser %","Laser")
parlay_k=tier_parlays(k_df,"Best K%","K","Pitcher") if not k_df.empty else pd.DataFrame()

mobile_cols=["Player","Team","Grade","Badge","HR %","Dinger Score","Auto Matchup Edge","Pitcher","Park","Game Status","HR Tracker","Parlay Eligible","Lineup","Order"]
full_cols=["Player","Team","Matchup","Pitcher","Park","Game Status","HR Tracker","Parlay Eligible","Lineup","Order","Dinger Score","Grade","Badge","HR %","Hit %","TB %","RBI %","Laser %","Form","Auto Matchup Edge","Pitcher Risk","Park Edge","Weather Edge","Power","Laser"]
breakdown_cols=["Player","Team","Matchup","Pitcher","Park","Game Status","HR Tracker","Parlay Eligible","Dinger Score","HR %","Auto Matchup Edge","Reasons"]

def render(data, cols=None):
    if data is None or data.empty:
        return "<div class='note'>No data available.</div>"

    if cols is None:
        cols=list(data.columns)
    else:
        cols=[c for c in cols if c in data.columns]

    html="<div class='table-wrap'><table class='ai-table'><tr>"
    for c in cols:
        html+=f"<th>{c}</th>"
    html+="</tr>"

    for _,r in data.iterrows():
        html+="<tr>"
        for c in cols:
            v=r.get(c,"")
            style=""
            if c=="Grade":
                style=f"background:{color_grade(v)};font-weight:900;text-align:center;"
            elif c=="Dinger Score":
                style="background:rgba(34,197,94,.38);font-weight:900;" if safe_float(v)>=28 else "background:rgba(59,130,246,.28);font-weight:900;" if safe_float(v)>=24 else "background:rgba(234,179,8,.22);font-weight:900;"
            elif c=="Parlay Eligible":
                style="background:rgba(34,197,94,.25);font-weight:900;" if str(v)=="Yes" else "background:rgba(239,68,68,.22);font-weight:900;"
            elif c=="HR Tracker":
                style="background:rgba(34,197,94,.25);font-weight:900;" if "✅" in str(v) else "background:rgba(239,68,68,.18);font-weight:900;" if "❌" in str(v) else "background:rgba(234,179,8,.16);font-weight:900;"
            elif "%" in c or c in ["Avg Model %","Model Combo Confidence","Avg HR %"]:
                style="background:rgba(34,197,94,.25);" if safe_float(v)>=60 else "background:rgba(234,179,8,.18);" if safe_float(v)>=35 else "background:rgba(239,68,68,.15);"
            elif c=="Form":
                val=str(v)
                style="color:#86efac;font-weight:900;" if "Hot" in val else "color:#93c5fd;font-weight:900;" if "Good" in val else "color:#fde68a;font-weight:900;" if "Neutral" in val else "color:#fca5a5;font-weight:900;"
            elif c in ["Reasons","Pick Explanation","Notes","Strategy"]:
                style="white-space:normal;min-width:520px;color:#cbd5e1;"
            elif c in ["Leg 1 Anchor","Leg 2 Support","Leg 3 Value","Leg 1","Leg 2","Leg 3"]:
                style="font-weight:800;color:#e5e7eb;"
            html+=f"<td style='{style}'>{v}</td>"
        html+="</tr>"

    html+="</table></div>"
    return html

def pick_card(title, data):
    if data is None or data.empty:
        return f"<div class='card'><h2>{title}</h2><p>No pick available.</p></div>"
    r=data.iloc[0]
    return f"""
    <div class='card'>
        <h2>{title}</h2>
        <h3>{r['Player']} — {r['Team']}</h3>
        <p><b>HR %:</b> {r['HR %']}% | <b>Dinger Score:</b> {r['Dinger Score']} | <b>Grade:</b> {r['Grade']} {r['Badge']}</p>
        <p><b>Matchup:</b> {r['Matchup']} vs {r['Pitcher']}</p>
        <p><b>Auto Matchup Edge:</b> {r['Auto Matchup Edge']} | <b>Park:</b> {r['Park']} | <b>Tracker:</b> {r['HR Tracker']}</p>
    </div>
    """

tab0,tab1,tab2,tab3,tab4,tab5,tab6=st.tabs(["🏆 Slate Picks","📱 Mobile HR","📋 Full HR","🎯 Strikeouts","🧾 Dynamic Parlays","🔎 Breakdown","🛠 Debug"])

with tab0:
    st.subheader("🏆 Top Picks of the Slate")
    st.markdown(pick_card("💣 Top HR Pick of the Slate", top_hr_pick), unsafe_allow_html=True)
    st.markdown(pick_card("⚔️ Best Batter vs Pitcher Matchup", best_matchup_pick), unsafe_allow_html=True)
    st.markdown("### 📌 Top 10 HR Tracker Board")
    st.markdown(render(df.head(10), ["Player","Team","HR %","Dinger Score","Grade","Pitcher","Park","Game Status","HR Tracker","Auto Matchup Edge"]), unsafe_allow_html=True)

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
    st.subheader("🧾 Dynamic Parlays")
    st.markdown("<div class='note'>These parlays only use players from games that have not started. When a game starts or finishes, it gets removed from the parlay pool on refresh.</div>", unsafe_allow_html=True)
    st.markdown("### 💣 Smart HR Parlays")
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
    st.subheader("🔎 Pick Breakdown / Reasons")
    st.markdown(render(df.head(80), breakdown_cols), unsafe_allow_html=True)

with tab6:
    st.write("Players scored:",len(df))
    st.write("Dynamic parlay pool players:",len(parlay_pool))
    st.write("Pitchers scored:",len(k_df))
    st.write("Games loaded:",len(games_all))
    st.write("Active/upcoming games shown:",len(games))
    st.write("Batters CSV rows:",len(batters))
    st.write("Game statuses:")
    st.dataframe(pd.DataFrame(games_all)[["away","home","park","status"]] if games_all else pd.DataFrame(), use_container_width=True)
    st.write("Detected columns:")
    st.json({
        "pa":b_pa,
        "bip":b_bip,
        "ba":b_ba,
        "est_ba":b_est_ba,
        "slg":b_slg,
        "est_slg":b_est_slg,
        "woba":b_woba,
        "est_woba":b_est_woba,
        "barrel":b_barrel,
        "hard_hit":b_hard,
        "iso":b_iso,
        "recent":b_recent,
        "team":b_team
    })
