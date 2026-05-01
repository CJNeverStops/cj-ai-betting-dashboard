import math, time
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="CJ MLB Next Level AI", layout="wide")

REFRESH_SECONDS = 300
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > REFRESH_SECONDS:
    st.session_state.last_refresh = time.time()
    st.rerun()

st.markdown("""
<style>
.stApp{background:#050914;color:white}.hero{background:linear-gradient(135deg,#3b171b,#111827);padding:24px;border-radius:22px;margin-bottom:20px}
.table-wrap{overflow-x:auto;border:1px solid #1f2937;border-radius:18px;margin-bottom:22px}.ai-table{width:100%;border-collapse:collapse;background:#0b1220;color:white;font-size:14px}
.ai-table th{background:#111827;padding:11px;text-align:left;white-space:nowrap}.ai-table td{padding:10px;border-bottom:1px solid rgba(255,255,255,.08);white-space:nowrap}
.note{background:#0b1220;border:1px solid #1f2937;border-radius:14px;padding:14px;color:#cbd5e1}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class='hero'>
<h1>🔥 CJ MLB NEXT LEVEL HR AI</h1>
<p>Weather • Wind Direction • Park HR Factor • Pitch Mix • Odds Edge • Backtest Log • Auto Refresh</p>
</div>
""", unsafe_allow_html=True)

def clamp(x,a,b): return max(a,min(b,x))
def safe_float(x,d=0.0):
    try:
        if pd.isna(x): return d
        return float(x)
    except: return d

def scale01(x,a,b):
    try:
        x=float(x)
        if a==b: return .5
        return clamp((x-a)/(b-a),0,1)
    except: return .5

def norm(x): return " ".join(str(x).lower().replace(",","").strip().split())

def first_last(x):
    x=str(x).strip()
    if "," in x:
        last,first=[p.strip() for p in x.split(",",1)]
        return f"{first} {last}"
    return x

def find_col(df,names):
    cols={str(c).lower().strip():c for c in df.columns}
    for n in names:
        if n.lower() in cols: return cols[n.lower()]
    for n in names:
        for c in df.columns:
            if n.lower() in str(c).lower(): return c
    return None

def make_name(df):
    c=find_col(df,["last_name, first_name","last_name_first_name"])
    if c: return df[c].astype(str).apply(first_last)
    c=find_col(df,["player_name","name","player"])
    if c: return df[c].astype(str).apply(first_last)
    f=find_col(df,["first_name","first"])
    l=find_col(df,["last_name","last"])
    if f and l: return (df[f].astype(str).str.strip()+" "+df[l].astype(str).str.strip()).str.strip()
    st.error(f"Could not find player name column. Found: {list(df.columns)}")
    st.stop()

def normalize_team(t):
    t=norm(t)
    m={
        "arizona diamondbacks":"ARI","diamondbacks":"ARI","ari":"ARI","atlanta braves":"ATL","braves":"ATL","atl":"ATL",
        "baltimore orioles":"BAL","orioles":"BAL","bal":"BAL","boston red sox":"BOS","red sox":"BOS","bos":"BOS",
        "chicago cubs":"CHC","cubs":"CHC","chc":"CHC","chicago white sox":"CWS","white sox":"CWS","cws":"CWS",
        "cincinnati reds":"CIN","reds":"CIN","cin":"CIN","cleveland guardians":"CLE","guardians":"CLE","cle":"CLE",
        "colorado rockies":"COL","rockies":"COL","col":"COL","detroit tigers":"DET","tigers":"DET","det":"DET",
        "houston astros":"HOU","astros":"HOU","hou":"HOU","kansas city royals":"KC","royals":"KC","kc":"KC",
        "los angeles angels":"LAA","angels":"LAA","laa":"LAA","los angeles dodgers":"LAD","dodgers":"LAD","lad":"LAD",
        "miami marlins":"MIA","marlins":"MIA","mia":"MIA","milwaukee brewers":"MIL","brewers":"MIL","mil":"MIL",
        "minnesota twins":"MIN","twins":"MIN","min":"MIN","new york mets":"NYM","mets":"NYM","nym":"NYM",
        "new york yankees":"NYY","yankees":"NYY","nyy":"NYY","oakland athletics":"OAK","athletics":"OAK","oak":"OAK",
        "philadelphia phillies":"PHI","phillies":"PHI","phi":"PHI","pittsburgh pirates":"PIT","pirates":"PIT","pit":"PIT",
        "san diego padres":"SD","padres":"SD","sd":"SD","san francisco giants":"SF","giants":"SF","sf":"SF",
        "seattle mariners":"SEA","mariners":"SEA","sea":"SEA","st louis cardinals":"STL","st. louis cardinals":"STL","cardinals":"STL","stl":"STL",
        "tampa bay rays":"TB","rays":"TB","tb":"TB","texas rangers":"TEX","rangers":"TEX","tex":"TEX",
        "toronto blue jays":"TOR","blue jays":"TOR","tor":"TOR","washington nationals":"WSH","nationals":"WSH","wsh":"WSH"
    }
    return m.get(t,str(t).upper()[:3])

def player_match(a,b):
    a=norm(first_last(a)); b=norm(first_last(b))
    if a==b: return True
    ap=a.split(); bp=b.split()
    return len(ap)>=2 and len(bp)>=2 and ap[-1]==bp[-1] and ap[0][0]==bp[0][0]

def find_player(df,name):
    if not name or df.empty: return None
    hits=df[df["_name"].apply(lambda x: player_match(x,name))]
    return hits.iloc[0] if not hits.empty else None

def fair_odds(p):
    if p<=0 or p>=1: return "N/A"
    if p>=.5: return int(round(-(p/(1-p))*100))
    return int(round(((1-p)/p)*100))

def implied_prob_from_american(odds):
    try: odds=float(odds)
    except: return None
    if odds<0: return abs(odds)/(abs(odds)+100)
    return 100/(odds+100)

def grade_score(s):
    if s>=30: return "A+"
    if s>=26: return "A"
    if s>=22: return "A-"
    if s>=18: return "B"
    if s>=15: return "C"
    return "D"

def badge_score(s):
    if s>=30: return "🔥 Nuclear"
    if s>=26: return "🔥 Elite"
    if s>=22: return "💎 Great"
    if s>=18: return "✅ Good"
    if s>=15: return "🟡 Solid"
    return "⚪ Lean"

def val_or_na(v,d=2):
    if v is None: return "N/A"
    try: return round(float(v),d)
    except: return "N/A"

# ================= CSV LOAD =================
try:
    batters=pd.read_csv("batters.csv")
except Exception as e:
    st.error(f"batters.csv load error: {e}")
    st.stop()

try:
    pitchers=pd.read_csv("pitchers.csv")
except:
    pitchers=pd.DataFrame()

try:
    odds_df=pd.read_csv("odds.csv")
except:
    odds_df=pd.DataFrame()

batters["_name"]=make_name(batters)
if not pitchers.empty: pitchers["_name"]=make_name(pitchers)

# Baseball Savant columns
b_pa=find_col(batters,["pa"])
b_bip=find_col(batters,["bip"])
b_ba=find_col(batters,["ba"])
b_est_ba=find_col(batters,["est_ba","xba"])
b_slg=find_col(batters,["slg"])
b_est_slg=find_col(batters,["est_slg","xslg"])
b_woba=find_col(batters,["woba"])
b_est_woba=find_col(batters,["est_woba","xwoba"])
b_team=find_col(batters,["team","player_team","bat_team","batter_team","team_name","club","team_abbrev","team_abbr"])

# Advanced optional columns
b_barrel=find_col(batters,["barrel","barrel_pct","brl"])
b_hard=find_col(batters,["hard_hit","hardhit","hard_hit_pct"])
b_k=find_col(batters,["k_percent","k%","strikeout"])
b_iso=find_col(batters,["iso"])
b_recent=find_col(batters,["last7","last14","recent","recent_form","last7_slg"])
b_ab_since_hr=find_col(batters,["ab_since_hr","abs_since_hr","pa_since_hr"])
b_v_rhp=find_col(batters,["xslg_vs_rhp","slg_vs_rhp","vs_rhp_slg","rhp_slg"])
b_v_lhp=find_col(batters,["xslg_vs_lhp","slg_vs_lhp","vs_lhp_slg","lhp_slg"])
b_fastball=find_col(batters,["xslg_vs_fastball","fastball_xslg","xslg_fastball","fb_xslg"])
b_breaking=find_col(batters,["xslg_vs_breaking","breaking_xslg","xslg_breaking","brk_xslg"])
b_offspeed=find_col(batters,["xslg_vs_offspeed","offspeed_xslg","xslg_offspeed"])

p_hand=find_col(pitchers,["throws","p_throws","pitcher_hand","hand"]) if not pitchers.empty else None
p_fb_pct=find_col(pitchers,["fastball_pct","fb_pct","four_seam_pct","fastball_usage"]) if not pitchers.empty else None
p_brk_pct=find_col(pitchers,["breaking_pct","breaking_ball_pct","brk_pct","slider_pct","curve_pct"]) if not pitchers.empty else None
p_off_pct=find_col(pitchers,["offspeed_pct","changeup_pct","splitter_pct"]) if not pitchers.empty else None

# ================= STADIUM SYSTEM =================
STADIUMS={
"Yankee Stadium":{"city":"Bronx","state":"NY","hr":1.18,"dome":False,"wind_out":["S","SW","SE","W"],"wind_in":["N","NE","NW","E"]},
"Fenway Park":{"city":"Boston","state":"MA","hr":1.03,"dome":False,"wind_out":["W","SW","S"],"wind_in":["E","NE","N"]},
"Rogers Centre":{"city":"Toronto","state":"ON","hr":1.05,"dome":True,"wind_out":[],"wind_in":[]},
"Oriole Park at Camden Yards":{"city":"Baltimore","state":"MD","hr":1.02,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Tropicana Field":{"city":"St. Petersburg","state":"FL","hr":0.92,"dome":True,"wind_out":[],"wind_in":[]},
"Progressive Field":{"city":"Cleveland","state":"OH","hr":0.97,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Comerica Park":{"city":"Detroit","state":"MI","hr":0.90,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Kauffman Stadium":{"city":"Kansas City","state":"MO","hr":0.88,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Target Field":{"city":"Minneapolis","state":"MN","hr":0.98,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Guaranteed Rate Field":{"city":"Chicago","state":"IL","hr":1.12,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Minute Maid Park":{"city":"Houston","state":"TX","hr":1.04,"dome":True,"wind_out":[],"wind_in":[]},
"Angel Stadium":{"city":"Anaheim","state":"CA","hr":0.96,"dome":False,"wind_out":["W","SW","S"],"wind_in":["E","NE","N"]},
"Oakland Coliseum":{"city":"Oakland","state":"CA","hr":0.86,"dome":False,"wind_out":["W","SW"],"wind_in":["E","NE"]},
"T-Mobile Park":{"city":"Seattle","state":"WA","hr":0.91,"dome":True,"wind_out":[],"wind_in":[]},
"Globe Life Field":{"city":"Arlington","state":"TX","hr":1.00,"dome":True,"wind_out":[],"wind_in":[]},
"Citi Field":{"city":"Queens","state":"NY","hr":0.96,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Truist Park":{"city":"Atlanta","state":"GA","hr":1.06,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"loanDepot park":{"city":"Miami","state":"FL","hr":0.92,"dome":True,"wind_out":[],"wind_in":[]},
"Citizens Bank Park":{"city":"Philadelphia","state":"PA","hr":1.20,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Nationals Park":{"city":"Washington","state":"DC","hr":1.02,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Wrigley Field":{"city":"Chicago","state":"IL","hr":1.00,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Great American Ball Park":{"city":"Cincinnati","state":"OH","hr":1.25,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"American Family Field":{"city":"Milwaukee","state":"WI","hr":1.08,"dome":True,"wind_out":[],"wind_in":[]},
"PNC Park":{"city":"Pittsburgh","state":"PA","hr":0.93,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Busch Stadium":{"city":"St. Louis","state":"MO","hr":0.95,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Chase Field":{"city":"Phoenix","state":"AZ","hr":1.03,"dome":True,"wind_out":[],"wind_in":[]},
"Coors Field":{"city":"Denver","state":"CO","hr":1.30,"dome":False,"wind_out":["S","SW","W"],"wind_in":["N","NE","E"]},
"Dodger Stadium":{"city":"Los Angeles","state":"CA","hr":1.05,"dome":False,"wind_out":["W","SW","S"],"wind_in":["E","NE","N"]},
"Petco Park":{"city":"San Diego","state":"CA","hr":0.93,"dome":False,"wind_out":["W","SW"],"wind_in":["E","NE"]},
"Oracle Park":{"city":"San Francisco","state":"CA","hr":0.82,"dome":False,"wind_out":["W","SW"],"wind_in":["E","NE"]},
}

def stadium_info(park):
    if park in STADIUMS: return STADIUMS[park]
    for k,v in STADIUMS.items():
        if norm(k)==norm(park): return v
    return {"city":"","state":"","hr":1.0,"dome":False,"wind_out":[],"wind_in":[]}

@st.cache_data(ttl=1800)
def get_weather(city,state):
    if not city:
        return {"temp":"N/A","wind":"N/A","wind_dir":"N/A","desc":"Unknown","impact":"Neutral","weather_edge":.50,"mult":1.0}
    try:
        q=f"{city},{state}".replace(" ","%20")
        data=requests.get(f"https://wttr.in/{q}?format=j1",timeout=15).json()
        cur=data["current_condition"][0]
        temp=safe_float(cur.get("temp_F"),70)
        wind=safe_float(cur.get("windspeedMiles"),7)
        wind_dir=cur.get("winddir16Point","N/A")
        desc=cur.get("weatherDesc",[{}])[0].get("value","Clear")
    except:
        return {"temp":"N/A","wind":"N/A","wind_dir":"N/A","desc":"Unknown","impact":"Neutral","weather_edge":.50,"mult":1.0}
    raw=1.0+((temp-70)*.004)+(wind*.002)
    if "rain" in str(desc).lower() or "storm" in str(desc).lower(): raw-=.06
    mult=clamp(raw,.88,1.18)
    impact="Good" if mult>=1.04 else "Bad" if mult<=.97 else "Neutral"
    return {"temp":temp,"wind":wind,"wind_dir":wind_dir,"desc":desc,"impact":impact,"weather_edge":scale01(mult,.88,1.18),"mult":mult}

def adjusted_weather_edge(weather, stadium):
    if stadium.get("dome"):
        return .55, "Dome/roof neutral"
    edge=weather.get("weather_edge",.50)
    wind=weather.get("wind","N/A")
    wd=str(weather.get("wind_dir","N/A"))
    note=f"{weather.get('impact')} weather"
    if isinstance(wind,(int,float)) and wind>=10:
        if wd in stadium.get("wind_out",[]):
            edge=clamp(edge+.16,0,1); note="Wind boost/out"
        elif wd in stadium.get("wind_in",[]):
            edge=clamp(edge-.14,0,1); note="Wind downgrade/in"
    return edge,note

# ================= API =================
@st.cache_data(ttl=300)
def get_schedule():
    today=datetime.now().strftime("%Y-%m-%d")
    url=f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher,team"
    try: data=requests.get(url,timeout=20).json()
    except: return []
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
                "time":g.get("gameDate",""),
                "status":g.get("status",{}).get("detailedState","")
            })
    return games

@st.cache_data(ttl=300)
def get_lineups(game_pk):
    try: data=requests.get(f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live",timeout=20).json()
    except: return {"away":[],"home":[]}
    def side(which):
        box=data.get("liveData",{}).get("boxscore",{}).get("teams",{}).get(which,{})
        order=box.get("battingOrder",[]) or []
        players=box.get("players",{}) or {}
        out=[]
        for idx,pid in enumerate(order,1):
            p=players.get(f"ID{pid}",{})
            name=p.get("person",{}).get("fullName","")
            if name: out.append({"name":name,"order":idx})
        return out
    return {"away":side("away"),"home":side("home")}

@st.cache_data(ttl=86400)
def build_roster():
    out=[]
    try: teams=requests.get("https://statsapi.mlb.com/api/v1/teams?sportId=1",timeout=20).json().get("teams",[])
    except: return pd.DataFrame(columns=["name","team"])
    for t in teams:
        tid=t.get("id"); team=normalize_team(t.get("name",""))
        try: roster=requests.get(f"https://statsapi.mlb.com/api/v1/teams/{tid}/roster",timeout=20).json().get("roster",[])
        except: roster=[]
        for p in roster:
            name=p.get("person",{}).get("fullName","")
            if name: out.append({"name":name,"team":team,"_norm":norm(name)})
    return pd.DataFrame(out)

@st.cache_data(ttl=1800)
def pitcher_live(pid):
    if not pid: return {"k_rate":.22,"k9":8.0,"era":4.20,"whip":1.30,"hr9":1.10}
    try:
        season=datetime.now().year
        data=requests.get(f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=season&group=pitching&season={season}",timeout=20).json()
        splits=data.get("stats",[{}])[0].get("splits",[])
        if not splits: return {"k_rate":.22,"k9":8.0,"era":4.20,"whip":1.30,"hr9":1.10}
        s=splits[0].get("stat",{})
        ip=safe_float(s.get("inningsPitched",0)); so=safe_float(s.get("strikeOuts",0)); bf=safe_float(s.get("battersFaced",0)); hr=safe_float(s.get("homeRuns",0))
        return {"k_rate":so/bf if bf>0 else .22,"k9":(so/ip)*9 if ip>0 else 8.0,"era":safe_float(s.get("era",4.20)),"whip":safe_float(s.get("whip",1.30)),"hr9":(hr/ip)*9 if ip>0 else 1.10}
    except:
        return {"k_rate":.22,"k9":8.0,"era":4.20,"whip":1.30,"hr9":1.10}

# setup teams
games_all=get_schedule()
FINAL_STATUSES=["final","game over","completed early"]
games=[g for g in games_all if str(g.get("status","")).lower() not in FINAL_STATUSES]
roster=build_roster()
if b_team:
    batters["_team"]=batters[b_team].astype(str).apply(normalize_team)
else:
    lookup=dict(zip(roster["_norm"],roster["team"])) if not roster.empty else {}
    batters["_team"]=batters["_name"].apply(lambda x:lookup.get(norm(x),""))

# ================= MODEL =================
def batter_metrics(row):
    pa=safe_float(row[b_pa],250) if b_pa else 250
    bip=safe_float(row[b_bip],150) if b_bip else 150
    ba=safe_float(row[b_ba],.245) if b_ba else .245
    est_ba=safe_float(row[b_est_ba],ba) if b_est_ba else ba
    slg=safe_float(row[b_slg],.400) if b_slg else .400
    est_slg=safe_float(row[b_est_slg],slg) if b_est_slg else slg
    woba=safe_float(row[b_woba],.310) if b_woba else .310
    est_woba=safe_float(row[b_est_woba],woba) if b_est_woba else woba
    barrel=safe_float(row[b_barrel],None) if b_barrel else None
    hard=safe_float(row[b_hard],None) if b_hard else None
    k_rate=safe_float(row[b_k],None) if b_k else None
    iso=safe_float(row[b_iso],est_slg-est_ba) if b_iso else est_slg-est_ba
    if barrel is not None and barrel>1: barrel/=100
    if hard is not None and hard>1: hard/=100
    if k_rate is not None and k_rate>1: k_rate/=100

    power=clamp(.42*scale01(est_slg,.300,.700)+.28*scale01(est_woba,.250,.450)+.18*scale01(iso,.080,.350)+.12*scale01(pa,50,650),0,1)
    if barrel is not None: power=clamp(power*.82+scale01(barrel,.02,.22)*.18,0,1)
    if hard is not None: power=clamp(power*.88+scale01(hard,.25,.60)*.12,0,1)
    contact=clamp(.50*scale01(est_ba,.190,.330)+.35*scale01(est_woba,.250,.450)+.15*scale01(bip,40,500),0,1)
    laser=clamp(.55*scale01(est_slg,.300,.700)+.30*scale01(est_woba,.250,.450)+.15*(scale01(hard,.25,.60) if hard is not None else .50),0,1)

    if b_recent:
        rr=safe_float(row[b_recent],None)
        form_score=scale01(rr,.180,.360) if rr not in [None,0] else power*.55+contact*.25+laser*.20
    else:
        form_score=power*.55+contact*.25+laser*.20
    form="🔥 Hot" if form_score>=.70 or power>=.78 or laser>=.78 else "✅ Good" if form_score>=.50 or power>=.58 or laser>=.58 else "⚠️ Neutral" if form_score>=.35 else "❄️ Cold"
    k_penalty=scale01(k_rate,.18,.35) if k_rate is not None else None
    ab_since=safe_float(row[b_ab_since_hr],None) if b_ab_since_hr else None
    ab_score=1-scale01(ab_since,0,45) if ab_since is not None else None
    return {"power":power,"contact":contact,"laser":laser,"form_score":form_score,"form":form,"k_penalty":k_penalty,"ab_since_hr":ab_since,"ab_since_score":ab_score,"est_slg":est_slg,"est_woba":est_woba,"est_ba":est_ba,"iso":iso}

def pitcher_risk(live):
    return clamp(.45*scale01(live.get("hr9",1.1),.3,2.2)+.30*scale01(live.get("era",4.2),2.5,6.0)+.25*scale01(live.get("whip",1.3),.9,1.7),0,1)

def pitch_type_edge(row,pitcher_name):
    vals=[]
    if b_fastball: vals.append(safe_float(row[b_fastball],.400))
    if b_breaking: vals.append(safe_float(row[b_breaking],.380))
    if b_offspeed: vals.append(safe_float(row[b_offspeed],.360))
    if not vals: return None
    return scale01(sum(vals)/len(vals),.280,.650)

def split_edge(row):
    vals=[]
    if b_v_rhp: vals.append(safe_float(row[b_v_rhp],None))
    if b_v_lhp: vals.append(safe_float(row[b_v_lhp],None))
    vals=[v for v in vals if v is not None]
    if not vals: return None
    return scale01(sum(vals)/len(vals),.300,.700)

def odds_edge_for(player, model_prob):
    if odds_df.empty: return "N/A","N/A","N/A"
    pc=find_col(odds_df,["player","player_name","name"])
    oc=find_col(odds_df,["hr_odds","odds","american_odds"])
    if not pc or not oc: return "N/A","N/A","N/A"
    hit=odds_df[odds_df[pc].astype(str).apply(lambda x: player_match(x,player))]
    if hit.empty: return "N/A","N/A","N/A"
    odds=hit.iloc[0][oc]
    imp=implied_prob_from_american(odds)
    if imp is None: return odds,"N/A","N/A"
    edge=(model_prob-imp)*100
    return odds,round(imp*100,1),round(edge,1)

def score_player(batter_name,pitcher_name,pitcher_id,team,opp,matchup,park,weather,order="—",lineup="Projected"):
    b=find_player(batters,batter_name)
    if b is None: return None
    live=pitcher_live(pitcher_id)
    bm=batter_metrics(b)
    pr=pitcher_risk(live)
    pe=pitch_type_edge(b,pitcher_name)
    se=split_edge(b)
    lineup_edge=1-scale01(order,1,9) if isinstance(order,int) else None

    stadium=stadium_info(park)
    park_edge=scale01(stadium.get("hr",1.0),.82,1.30)
    weather_edge,weather_note=adjusted_weather_edge(weather,stadium)

    pe_s=pe if pe is not None else .50
    se_s=se if se is not None else .50
    lineup_s=lineup_edge if lineup_edge is not None else .50
    k_s=bm["k_penalty"] if bm["k_penalty"] is not None else .35
    ab_s=bm["ab_since_score"] if bm["ab_since_score"] is not None else .50

    d_score=round(clamp(12*bm["power"]+6*pr+4*bm["contact"]+4*bm["laser"]+3*bm["form_score"]+3*pe_s+3*park_edge+3*weather_edge+2*se_s+2*lineup_s+1.5*ab_s-2.5*k_s,0,42),1)
    hr_prob=clamp(.035+(.30*bm["power"]+.18*pr+.14*bm["laser"]+.10*bm["form_score"]+.10*pe_s+.10*park_edge+.08*weather_edge+.05*se_s+.04*lineup_s-.04*k_s)*.34,.010,.40)
    hit_prob=clamp(.28+(.55*bm["contact"]+.25*bm["form_score"]+.20*(1-pr))*.42,.18,.82)
    tb_prob=clamp(.20+(.43*bm["power"]+.28*bm["contact"]+.20*pr+.09*park_edge)*.48,.10,.76)
    rbi_prob=clamp(.12+(.45*bm["power"]+.25*pr+.20*lineup_s+.10*park_edge)*.42,.06,.62)
    laser_prob=clamp(.15+bm["laser"]*.62+pr*.10+pe_s*.10,.10,.82)
    odds,book_imp,edge=odds_edge_for(batter_name,hr_prob)

    reasons=f"{bm['form']} • estSLG {round(bm['est_slg'],3)} • estwOBA {round(bm['est_woba'],3)} • ISO {round(bm['iso'],3)} • Pitcher HR Risk {round(pr,2)} • Pitch Edge {val_or_na(pe)} • Split Edge {val_or_na(se)} • Park {park} HR {stadium.get('hr')} • Weather {weather_note} {weather.get('temp')}°F wind {weather.get('wind')} {weather.get('wind_dir')} • Lineup Edge {val_or_na(lineup_edge)} • K Risk {val_or_na(bm['k_penalty'])} • AB Since HR {val_or_na(bm['ab_since_hr'],0)}"

    return {"Player":batter_name,"Team":normalize_team(team),"Matchup":matchup,"Park":park,"Pitcher":pitcher_name,"Opp":normalize_team(opp),"Lineup":lineup,"Order":order,"Dinger Score":d_score,"Dinger Badge":badge_score(d_score),"Grade":grade_score(d_score),"HR %":round(hr_prob*100,1),"Hit %":round(hit_prob*100,1),"TB %":round(tb_prob*100,1),"RBI %":round(rbi_prob*100,1),"Laser %":round(laser_prob*100,1),"Form":bm["form"],"HR Fair Odds":fair_odds(hr_prob),"Book HR Odds":odds,"Book Implied %":book_imp,"Edge %":edge,"Pitch Edge":val_or_na(pe),"Split Edge":val_or_na(se),"Park Edge":round(park_edge,2),"Weather Edge":round(weather_edge,2),"Lineup Edge":val_or_na(lineup_edge),"K Risk":val_or_na(bm["k_penalty"]),"AB Since HR":val_or_na(bm["ab_since_hr"],0),"Reasons":reasons}

# build rows
rows=[]
for g in games:
    matchup=f'{g["away"]} @ {g["home"]}'
    stinfo=stadium_info(g["park"])
    weather=get_weather(stinfo["city"],stinfo["state"])
    lu=get_lineups(g["gamePk"])

    if g["home_p"]:
        hitters=lu["away"]
        if hitters:
            for h in hitters:
                r=score_player(h["name"],g["home_p"],g["home_p_id"],g["away"],g["home"],matchup,g["park"],weather,h["order"],"Final")
                if r: rows.append(r)
        else:
            for _,b in batters[batters["_team"]==normalize_team(g["away"])].iterrows():
                r=score_player(b["_name"],g["home_p"],g["home_p_id"],g["away"],g["home"],matchup,g["park"],weather)
                if r: rows.append(r)
    if g["away_p"]:
        hitters=lu["home"]
        if hitters:
            for h in hitters:
                r=score_player(h["name"],g["away_p"],g["away_p_id"],g["home"],g["away"],matchup,g["park"],weather,h["order"],"Final")
                if r: rows.append(r)
        else:
            for _,b in batters[batters["_team"]==normalize_team(g["home"])].iterrows():
                r=score_player(b["_name"],g["away_p"],g["away_p_id"],g["home"],g["away"],matchup,g["park"],weather)
                if r: rows.append(r)

df=pd.DataFrame(rows)
if df.empty:
    st.warning("No active/upcoming player rows created. All games may be final, or lineups/pitchers are missing.")
    st.stop()
df=df.sort_values("Dinger Score",ascending=False).reset_index(drop=True)

# Strikeouts
k_rows=[]
for g in games:
    for name,pid,opp in [(g["away_p"],g["away_p_id"],g["home"]),(g["home_p"],g["home_p_id"],g["away"])]:
        if not name: continue
        live=pitcher_live(pid)
        proj=clamp(3.8+(live["k_rate"]-.20)*18+(live["k9"]-8.0)*.35,2.0,10.5)
        def over(line): return clamp(1/(1+math.exp(-(proj-line))),.05,.92)
        k45=round(over(4.5)*100,1); k55=round(over(5.5)*100,1); k65=round(over(6.5)*100,1); best=max(k45,k55,k65)
        k_rows.append({"Pitcher":name,"Opponent":normalize_team(opp),"Projected Ks":round(proj,1),"Live K%":round(live["k_rate"]*100,1),"K/9":round(live["k9"],1),"ERA":live["era"],"WHIP":live["whip"],"Over 4.5 K%":k45,"Over 5.5 K%":k55,"Over 6.5 K%":k65,"Best K%":best,"Grade":"A+" if best>=75 else "A" if best>=65 else "A-" if best>=58 else "B" if best>=50 else "C","Pick Explanation":f"{name} projects for {round(proj,1)} Ks using live K%, K/9, ERA, and WHIP."})
k_df=pd.DataFrame(k_rows).sort_values("Best K%",ascending=False) if k_rows else pd.DataFrame()

# Parlays
def tier_parlays(data,col,label,name_col="Player"):
    pool=data.sort_values(col,ascending=False).head(15).reset_index(drop=True)
    out=[]
    for i in range(0,15,3):
        c=pool.iloc[i:i+3]
        if len(c)<3: continue
        out.append({"Parlay":f"{label} 3-Leg #{len(out)+1}","Leg 1":f"{c.iloc[0][name_col]} ({c.iloc[0][col]}%)","Leg 2":f"{c.iloc[1][name_col]} ({c.iloc[1][col]}%)","Leg 3":f"{c.iloc[2][name_col]} ({c.iloc[2][col]}%)","Avg Model %":round(c[col].mean(),1),"Model Combo Confidence":round((c[col]/100).prod()*100,2),"Notes":f"Tier #{len(out)+1}: ranked group {i+1}-{i+3}, no repeated top-player overlap"})
    return pd.DataFrame(out)

parlay_hr=tier_parlays(df,"HR %","HR")
parlay_hit=tier_parlays(df,"Hit %","Hit")
parlay_tb=tier_parlays(df,"TB %","TB")
parlay_rbi=tier_parlays(df,"RBI %","RBI")
parlay_laser=tier_parlays(df,"Laser %","Laser")
parlay_k=tier_parlays(k_df,"Best K%","K","Pitcher") if not k_df.empty else pd.DataFrame()

# Backtest export
backtest_cols=["Player","Team","Matchup","Park","Pitcher","Dinger Score","HR %","Dinger Badge","Grade","Book HR Odds","Book Implied %","Edge %","Reasons"]
backtest=df[backtest_cols].copy()
backtest.insert(0,"Date",datetime.now().strftime("%Y-%m-%d"))
backtest["Result"]=""

# UI render
def color_grade(g):
    return {"A+":"#166534","A":"#15803d","A-":"#16a34a","B":"#2563eb","C":"#6d28d9","D":"#7f1d1d"}.get(g,"#374151")

def render(data):
    if data is None or data.empty: return "<div class='note'>No data available.</div>"
    cols=list(data.columns)
    html="<div class='table-wrap'><table class='ai-table'><tr>"
    for c in cols: html+=f"<th>{c}</th>"
    html+="</tr>"
    for _,r in data.iterrows():
        html+="<tr>"
        for c in cols:
            v=r.get(c,""); style=""
            if c=="Grade": style=f"background:{color_grade(v)};font-weight:900;text-align:center;"
            elif c=="Dinger Score": style="background:rgba(34,197,94,.38);font-weight:900;" if safe_float(v)>=26 else "background:rgba(59,130,246,.28);font-weight:900;" if safe_float(v)>=22 else "background:rgba(234,179,8,.22);font-weight:900;"
            elif "%" in c or c in ["Avg Model %","Model Combo Confidence"]: style="background:rgba(34,197,94,.25);" if safe_float(v)>=60 else "background:rgba(234,179,8,.18);" if safe_float(v)>=35 else "background:rgba(239,68,68,.15);"
            elif c=="Form":
                val=str(v); style="color:#86efac;font-weight:900;" if "Hot" in val else "color:#93c5fd;font-weight:900;" if "Good" in val else "color:#fde68a;font-weight:900;" if "Neutral" in val else "color:#fca5a5;font-weight:900;"
            elif c in ["Reasons","Pick Explanation","Notes"]: style="white-space:normal;min-width:560px;color:#cbd5e1;"
            html+=f"<td style='{style}'>{v}</td>"
        html+="</tr>"
    html+="</table></div>"
    return html

tab1,tab2,tab3,tab4,tab5,tab6=st.tabs(["🔥 Best HR Plays","📋 All Players","🎯 Strikeouts","🧾 Parlays","📈 Backtest","🛠 Debug"])

with tab1:
    st.subheader("Best HR Rated Plays")
    st.caption(f"Active/upcoming games: {len(games)} | Finished removed: {len(games_all)-len(games)} | Auto refresh: 5 min")
    st.markdown(render(df.head(40)),unsafe_allow_html=True)

with tab2:
    st.subheader("Full Player Model")
    st.markdown(render(df),unsafe_allow_html=True)

with tab3:
    st.subheader("Live Pitcher Strikeout Model")
    st.markdown(render(k_df),unsafe_allow_html=True)

with tab4:
    st.subheader("Top 5 Tiered 3-Leg Parlays")
    for title,data in [("💣 HR Parlays",parlay_hr),("✅ Hit Parlays",parlay_hit),("🧱 Total Bases Parlays",parlay_tb),("🏃 RBI Parlays",parlay_rbi),("🚀 Laser Parlays",parlay_laser),("🎯 Strikeout Parlays",parlay_k)]:
        st.markdown(f"### {title}")
        st.markdown(render(data),unsafe_allow_html=True)

with tab5:
    st.subheader("Backtest Log Export")
    st.markdown("<div class='note'>Download this after locking picks. Later add Result = HR / No HR / Hit / Loss to track what actually works.</div>",unsafe_allow_html=True)
    st.dataframe(backtest,use_container_width=True)
    st.download_button("Download backtest CSV",backtest.to_csv(index=False).encode("utf-8"),file_name=f"cj_backtest_{datetime.now().strftime('%Y-%m-%d')}.csv",mime="text/csv")

with tab6:
    st.write("All games loaded:",len(games_all))
    st.write("Active/upcoming games used:",len(games))
    st.write("Finished games removed:",len(games_all)-len(games))
    st.write("Players scored:",len(df))
    st.write("Batters CSV rows:",len(batters))
    st.write("Odds file loaded:",not odds_df.empty)
    st.write("Detected columns:")
    st.json({"core":{"pa":b_pa,"bip":b_bip,"ba":b_ba,"est_ba":b_est_ba,"slg":b_slg,"est_slg":b_est_slg,"woba":b_woba,"est_woba":b_est_woba,"team":b_team},"advanced":{"barrel":b_barrel,"hard_hit":b_hard,"k_percent":b_k,"iso":b_iso,"recent":b_recent,"ab_since_hr":b_ab_since_hr,"vs_rhp":b_v_rhp,"vs_lhp":b_v_lhp,"fastball":b_fastball,"breaking":b_breaking,"offspeed":b_offspeed}})
    st.write("Game statuses:")
    st.dataframe(pd.DataFrame(games_all)[["away","home","park","status"]] if games_all else pd.DataFrame(),use_container_width=True)
    st.write("Stadium system:")
    st.dataframe(pd.DataFrame([{"Park":k,**v} for k,v in STADIUMS.items()]),use_container_width=True)
