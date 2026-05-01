import math, time
from datetime import datetime
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
<h1>🔥 AON BETS HR MODEL ⚾️ 💣</h1>
<p>Calibrated Dinger Score • HR Projections • Team Auto-Mapping • Tiered Parlays • Auto Refresh</p>
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
    c=find_col(df,["player_name","name","player"])
    if c: return df[c].astype(str).apply(first_last)
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
        "S+":"#7f1d1d",
        "S":"#166534",
        "A+":"#15803d",
        "A":"#2563eb",
        "B":"#6d28d9",
        "C":"#92400e",
        "D":"#374151"
    }.get(g,"#374151")

@st.cache_data(ttl=86400)
def build_roster():
    out = []
    try:
        teams = requests.get("https://statsapi.mlb.com/api/v1/teams?sportId=1", timeout=20).json().get("teams", [])
    except Exception:
        return pd.DataFrame(columns=["name", "team", "_norm"])

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
                out.append({"name": name, "team": team, "_norm": norm(name)})

    return pd.DataFrame(out)

try:
    batters = pd.read_csv("batters.csv")
except Exception as e:
    st.error(f"batters.csv load error: {e}")
    st.stop()

batters["_name"] = make_name(batters)

roster = build_roster()

b_team = find_col(batters, ["team","player_team","bat_team","team_name","club","team_abbrev","team_abbr"])

if b_team:
    batters["_team"] = batters[b_team].astype(str).apply(normalize_team)
else:
    lookup = dict(zip(roster["_norm"], roster["team"])) if not roster.empty else {}
    batters["_team"] = batters["_name"].apply(lambda x: lookup.get(norm(x), "N/A"))

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

    if barrel is not None and barrel > 1: barrel /= 100
    if hard is not None and hard > 1: hard /= 100

    power = clamp(
        .42*scale01(est_slg,.300,.700)
        + .28*scale01(est_woba,.250,.450)
        + .18*scale01(iso,.080,.350)
        + .12*scale01(pa,50,650),
        0,1
    )

    if barrel is not None:
        power = clamp(power*.82 + scale01(barrel,.02,.22)*.18,0,1)

    if hard is not None:
        power = clamp(power*.88 + scale01(hard,.25,.60)*.12,0,1)

    contact = clamp(
        .50*scale01(est_ba,.190,.330)
        + .35*scale01(est_woba,.250,.450)
        + .15*scale01(bip,40,500),
        0,1
    )

    laser = clamp(
        .55*scale01(est_slg,.300,.700)
        + .30*scale01(est_woba,.250,.450)
        + .15*(scale01(hard,.25,.60) if hard is not None else .50),
        0,1
    )

    if b_recent:
        recent = safe_float(row[b_recent], None)
        form_score = scale01(recent,.180,.360) if recent not in [None,0] else power*.55 + contact*.25 + laser*.20
    else:
        form_score = power*.55 + contact*.25 + laser*.20

    form = "🔥 Hot" if form_score >= .70 or power >= .78 or laser >= .78 else \
           "✅ Good" if form_score >= .50 or power >= .58 or laser >= .58 else \
           "⚠️ Neutral" if form_score >= .35 else "❄️ Cold"

    dinger_score = round(clamp(
        14*power
        + 8*laser
        + 7*contact
        + 5*form_score,
        0,42
    ),1)

    hr_prob = clamp(.035 + (.42*power + .25*laser + .18*form_score + .15*contact)*.32, .010, .40)

    return {
        "Power": round(power,2),
        "Contact": round(contact,2),
        "Laser": round(laser,2),
        "Form Score": round(form_score,2),
        "Form": form,
        "Dinger Score": dinger_score,
        "HR %": round(hr_prob*100,1),
        "Hit %": round(clamp(.28 + contact*.42, .18, .82)*100,1),
        "TB %": round(clamp(.20 + (power*.55 + contact*.25 + laser*.20)*.48, .10, .76)*100,1),
        "RBI %": round(clamp(.12 + (power*.65 + laser*.20 + form_score*.15)*.42, .06, .62)*100,1),
        "Laser %": round(clamp(.15 + laser*.62, .10, .82)*100,1),
        "estSLG": round(est_slg,3),
        "estwOBA": round(est_woba,3),
        "estBA": round(est_ba,3),
        "ISO": round(iso,3),
    }

rows=[]
for _, r in batters.iterrows():
    m = batter_metrics(r)
    s = m["Dinger Score"]

    rows.append({
        "Player": r["_name"],
        "Team": r["_team"],
        "Dinger Score": s,
        "Grade": grade_score(s),
        "Badge": badge_score(s),
        "HR %": m["HR %"],
        "Hit %": m["Hit %"],
        "TB %": m["TB %"],
        "RBI %": m["RBI %"],
        "Laser %": m["Laser %"],
        "Form": m["Form"],
        "Power": m["Power"],
        "Contact": m["Contact"],
        "Laser": m["Laser"],
        "estSLG": m["estSLG"],
        "estwOBA": m["estwOBA"],
        "estBA": m["estBA"],
        "ISO": m["ISO"],
        "Reasons": f"{m['Form']} • Power {m['Power']} • Laser {m['Laser']} • estSLG {m['estSLG']} • estwOBA {m['estwOBA']} • ISO {m['ISO']}"
    })

df = pd.DataFrame(rows).sort_values("Dinger Score", ascending=False).reset_index(drop=True)

def tier_parlays(data, col, label):
    pool = data.sort_values(col, ascending=False).head(15).reset_index(drop=True)
    out = []
    for i in range(0,15,3):
        c = pool.iloc[i:i+3]
        if len(c) < 3: continue
        out.append({
            "Parlay": f"{label} 3-Leg #{len(out)+1}",
            "Leg 1": f"{c.iloc[0]['Player']} ({c.iloc[0][col]}%)",
            "Leg 2": f"{c.iloc[1]['Player']} ({c.iloc[1][col]}%)",
            "Leg 3": f"{c.iloc[2]['Player']} ({c.iloc[2][col]}%)",
            "Avg Model %": round(c[col].mean(),1),
            "Model Combo Confidence": round((c[col]/100).prod()*100,2),
            "Notes": f"Tier #{len(out)+1}: ranked group {i+1}-{i+3}, no repeated top-player overlap"
        })
    return pd.DataFrame(out)

parlay_hr = tier_parlays(df,"HR %","HR")
parlay_hit = tier_parlays(df,"Hit %","Hit")
parlay_tb = tier_parlays(df,"TB %","TB")
parlay_rbi = tier_parlays(df,"RBI %","RBI")
parlay_laser = tier_parlays(df,"Laser %","Laser")

def render(data):
    if data is None or data.empty:
        return "<div class='note'>No data available.</div>"

    cols=list(data.columns)
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
            elif "%" in c or c in ["Avg Model %","Model Combo Confidence"]:
                style="background:rgba(34,197,94,.25);" if safe_float(v)>=60 else "background:rgba(234,179,8,.18);" if safe_float(v)>=35 else "background:rgba(239,68,68,.15);"
            elif c=="Form":
                val=str(v)
                style="color:#86efac;font-weight:900;" if "Hot" in val else "color:#93c5fd;font-weight:900;" if "Good" in val else "color:#fde68a;font-weight:900;" if "Neutral" in val else "color:#fca5a5;font-weight:900;"
            elif c in ["Reasons","Notes"]:
                style="white-space:normal;min-width:520px;color:#cbd5e1;"
            html+=f"<td style='{style}'>{v}</td>"
        html+="</tr>"

    html+="</table></div>"
    return html

tab1,tab2,tab3,tab4 = st.tabs(["🔥 Best HR Plays","📋 Full Model","🧾 Parlays","🛠 Debug"])

with tab1:
    st.subheader("🔥 Best HR Rated Plays")
    st.markdown(render(df.head(40)), unsafe_allow_html=True)

with tab2:
    st.subheader("📋 Full AON BETS HR MODEL")
    st.markdown(render(df), unsafe_allow_html=True)

with tab3:
    st.subheader("🧾 Top 5 Tiered 3-Leg Parlays")
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

with tab4:
    st.write("App Name: AON BETS HR MODEL ⚾️ 💣")
    st.write("Players scored:", len(df))
    st.write("Batters CSV rows:", len(batters))
    st.write("MLB API roster rows:", len(roster))
    st.write("Detected team column:", b_team if b_team else "None — using MLB roster API")
    st.write("Players still N/A team:", int((batters["_team"] == "N/A").sum()))
    st.write("Team counts:")
    st.dataframe(batters["_team"].value_counts(dropna=False).reset_index(), use_container_width=True)
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
        "team": b_team
    })
