import os
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="CJNeverStops AI Betting Dashboard", layout="wide")

st.title("🔥 CJNeverStops AI Betting Dashboard")

# ---------------- SETTINGS ----------------
ODDS_API_KEY = st.secrets.get("ODDS_API_KEY", os.getenv("ODDS_API_KEY", ""))

# ---------------- HELPERS ----------------
def implied_prob(odds):
    if odds is None:
        return None
    if odds > 0:
        return 100 / (odds + 100)
    return -odds / (-odds + 100)

def model_prob():
    return 0.30  # placeholder until real stat model is wired in

def get_odds():
    if not ODDS_API_KEY:
        return [], "Missing ODDS_API_KEY"

    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "player_home_runs,player_hits,player_strikeouts",
        "oddsFormat": "american",
    }

    try:
        resp = requests.get(url, params=params, timeout=20)
        data = resp.json()
    except Exception as e:
        return [], f"Request failed: {e}"

    if resp.status_code != 200:
        return [], f"API error {resp.status_code}: {data}"

    if not isinstance(data, list):
        return [], f"Unexpected API response: {data}"

    return data, None

# ---------------- LOAD DATA ----------------
odds_data, error = get_odds()

if error:
    st.error(error)
    st.stop()

picks = []

for game in odds_data:
    bookmakers = game.get("bookmakers", [])
    for book in bookmakers:
        markets = book.get("markets", [])
        for market in markets:
            outcomes = market.get("outcomes", [])
            for outcome in outcomes:
                player = outcome.get("description") or outcome.get("name") or "Unknown"
                odds = outcome.get("price")

                if odds is None:
                    continue

                model = model_prob()
                book_prob = implied_prob(odds)

                if book_prob is None:
                    continue

                edge = model - book_prob

                picks.append(
                    {
                        "Game": f"{game.get('home_team', '')} vs {game.get('away_team', '')}",
                        "Book": book.get("title", "Unknown"),
                        "Market": market.get("key", "Unknown"),
                        "Player": player,
                        "Odds": odds,
                        "Model %": round(model * 100, 2),
                        "Book %": round(book_prob * 100, 2),
                        "Edge %": round(edge * 100, 2),
                        "Play": "🔥 BET" if edge > 0.05 else "PASS",
                    }
                )

df = pd.DataFrame(picks)

if df.empty:
    st.warning("No prop data returned. This usually means the API key, plan, or market selection needs adjustment.")
    st.stop()

df = df.sort_values(by="Edge %", ascending=False)

top = df.iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("Top Edge", f"{top['Edge %']}%")
c2.metric("Best Player", top["Player"])
c3.metric("Best Market", top["Market"])

st.subheader("💰 Top AI Picks")
st.dataframe(df.head(20), use_container_width=True)

st.subheader("📊 All Props")
st.dataframe(df, use_container_width=True)
ODDS_API_KEY
get_odds()
requests to odds api
