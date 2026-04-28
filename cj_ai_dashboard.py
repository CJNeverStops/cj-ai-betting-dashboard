import math
import itertools
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="CJ MLB ELITE AI", layout="wide")

# =========================
# STYLE
# =========================
st.markdown("""
<style>
.stApp { background:#050914; color:white; }
.hero { background:linear-gradient(135deg,#3b171b,#111827); padding:20px; border-radius:15px; margin-bottom:20px;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='hero'><h1>🔥 CJ MLB ELITE AI MODEL</h1></div>", unsafe_allow_html=True)

# =========================
# HELPERS
# =========================
def clamp(x,a,b): return max(a,min(b,x))
def safe(x,d=0): return float(x) if pd.notna(x) else d
def pct(x,d): return safe(x,d)/100 if safe(x,d)>1 else safe(x,d)

def scale(x,a,b):
    try: return max(0,min(1,(float(x)-a)/(b-a)))
    except: return 0

# =========================
# LOAD DATA
# =========================
batters = pd.read_csv("batters.csv")
pitchers = pd.read_csv("pitchers.csv")

batters["_name"] = batters["last_name"] + " " + batters["first_name"]
pitchers["_name"] = pitchers["last_name"] + " " + pitchers["first_name"]

# =========================
# MLB LIVE SCHEDULE
# =========================
def schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    url=f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher"
    data=requests.get(url).json()
    games=[]
    for d in data.get("dates",[]):
        for g in d.get("games",[]):
            games.append({
                "away":g["teams"]["away"]["team"]["name"],
                "home":g["teams"]["home"]["team"]["name"],
                "away_p":g["teams"]["away"].get("probablePitcher",{}).get("fullName",""),
                "home_p":g["teams"]["home"].get("probablePitcher",{}).get("fullName",""),
                "away_id":g["teams"]["away"].get("probablePitcher",{}).get("id"),
                "home_id":g["teams"]["home"].get("probablePitcher",{}).get("id"),
            })
    return games

# =========================
# LIVE PITCHER STATS
# =========================
def pitcher_live(pid):
    try:
        url=f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=season&group=pitching"
        s=requests.get(url).json()["stats"][0]["splits"][0]["stat"]
        ip=safe(s["inningsPitched"])
        so=safe(s["strikeOuts"])
        bf=safe(s["battersFaced"])
        return {
            "k_rate": so/bf if bf else .22,
            "k9": (so/ip)*9 if ip else 8,
            "era": safe(s["era"],4.2),
            "whip": safe(s["whip"],1.3)
        }
    except:
        return {"k_rate":.22,"k9":8,"era":4.2,"whip":1.3}

# =========================
# MODEL
# =========================
def power(r):
    return clamp(
        .3*scale(r["est_slg"],.3,.75)+
        .25*scale(r["barrel"],.02,.25)+
        .2*scale(r["hard_hit"],.2,.65)+
        .15*scale(r.get("iso",.17),.08,.35)
    ,0,1)

def contact(r):
    return clamp(
        .6*scale(r["est_ba"],.18,.33)+
        .4*(1-scale(r.get("k_percent",.22),.1,.35))
    ,0,1)

def edge(b,p): return clamp(power(b)*.6 + .4,0,1)

def dinger(b,p):
    return round(clamp(
        10*power(b)+
        6*.5+
        5*edge(b,p)+
        4*contact(b)
    ,0,42),1)

# =========================
# BUILD PLAYER MODEL
# =========================
rows=[]
games=schedule()

for g in games:
    for _,b in batters.iterrows():
        score=dinger(b,None)
        rows.append({
            "Player":b["_name"],
            "Score":score,
            "HR%":round(score*1.2,1),
            "Hit%":round(score*2,1),
            "TB%":round(score*1.7,1),
            "RBI%":round(score*1.5,1),
            "Laser%":round(score*1.3,1),
            "Tier": "🔥 Elite" if score>=26 else "💎 Great" if score>=22 else "✅ Good"
        })

df=pd.DataFrame(rows).sort_values("Score",ascending=False)

# =========================
# STRIKEOUT MODEL
# =========================
k_rows=[]
for g in games:
    for name,pid in [(g["away_p"],g["away_id"]),(g["home_p"],g["home_id"])]:
        live=pitcher_live(pid)
        ks=clamp(3.8+(live["k_rate"]-.2)*18,2,10)
        prob=round((ks/10)*100,1)
        k_rows.append({
            "Pitcher":name,
            "Ks":round(ks,1),
            "K%":prob,
            "ERA":live["era"],
            "WHIP":live["whip"]
        })

k_df=pd.DataFrame(k_rows).sort_values("K%",ascending=False)

# =========================
# PARLAYS (TIER SYSTEM)
# =========================
def tier_parlays(df,col):
    pool=df.head(15)
    parlays=[]
    for i in range(0,15,3):
        c=pool.iloc[i:i+3]
        if len(c)<3: continue
        parlays.append({
            "Leg1":c.iloc[0]["Player"],
            "Leg2":c.iloc[1]["Player"],
            "Leg3":c.iloc[2]["Player"],
            "Avg%":round(c[col].mean(),1)
        })
    return pd.DataFrame(parlays)

hr_parlays=tier_parlays(df,"HR%")

# =========================
# UI
# =========================
tabs=st.tabs(["🔥 Best","📋 All","🎯 Ks","🧾 Parlays"])

with tabs[0]:
    st.dataframe(df.head(20),use_container_width=True)

with tabs[1]:
    st.dataframe(df,use_container_width=True)

with tabs[2]:
    st.dataframe(k_df,use_container_width=True)

with tabs[3]:
    st.dataframe(hr_parlays,use_container_width=True)
