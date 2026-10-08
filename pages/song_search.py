"""
Six-String Bootcamp — Song Search
=================================
Internet song library powered by the Songsterr API (no key needed).

USE:
  Standalone:  streamlit run song_search.py
  In your app: drop this file into a `pages/` folder next to app.py and
               Streamlit adds it to the sidebar nav automatically.

Requires: streamlit, requests  (pip install streamlit requests)
"""
import streamlit as st
import requests

API_SEARCH = "https://www.songsterr.com/api/songs"
API_META = "https://www.songsterr.com/api/meta/{}"
TAB_URL = "https://www.songsterr.com/a/wsa/tab-s{}"  # slug canonicalized server-side
TIMEOUT = 12

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
STANDARD = [64, 59, 55, 50, 45, 40]  # e B G D A E (1st -> 6th string)


def tuning_label(tuning):
    """[64,59,55,50,45,40] -> 'E A D G B E (standard)' (low to high)."""
    if not tuning:
        return "—"
    names = [NAMES[m % 12] for m in reversed(tuning)]
    label = " ".join(names)
    if list(tuning) == STANDARD:
        label += " (standard)"
    return label


def is_guitar(instrument):
    return instrument and "guitar" in instrument.lower()


@st.cache_data(ttl=3600, show_spinner=False)
def search_songs(query):
    r = requests.get(API_SEARCH, params={"pattern": query}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=3600, show_spinner=False)
def song_meta(song_id):
    r = requests.get(API_META.format(song_id), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


# ---------------- UI ----------------
st.set_page_config(page_title="Song Search — Six-String Bootcamp", page_icon="🎵")
st.title("🎵 Song Search")
st.caption("Live internet song library — pick a song, see its guitar tracks and tuning, open the full interactive tab.")

query = st.text_input("Search songs or artists", placeholder="e.g. wonderwall, metallica, hallelujah")
go = st.button("Search", type="primary")

if go and query.strip():
    try:
        with st.spinner("Searching..."):
            results = search_songs(query.strip())
    except Exception as e:
        st.error(f"Search failed: {e}")
        results = None

    if results is not None:
        if not results:
            st.info("No songs found — try a different spelling.")
        st.caption(f"{len(results)} result(s)")
        for s in results:
            sid = s.get("songId")
            title = s.get("title", "?")
            artist = s.get("artist", "?")
            badges = []
            if s.get("hasChords"):
                badges.append("🎼 chords")
            if s.get("hasPlayer"):
                badges.append("▶ interactive tab")
            label = f"**{artist} — {title}**"
            if badges:
                label += "  ·  " + "  ·  ".join(badges)

            with st.expander(label):
                try:
                    with st.spinner("Loading tracks..."):
                        meta = song_meta(sid)
                except Exception as e:
                    st.error(f"Couldn't load details: {e}")
                    continue

                tracks = meta.get("tracks", []) or []
                guitars = [t for t in tracks if is_guitar(t.get("instrument"))]
                others = [t for t in tracks if not is_guitar(t.get("instrument"))]

                if guitars:
                    st.subheader("🎸 Guitar tracks")
                    for t in guitars:
                        cols = st.columns([3, 2, 1])
                        cols[0].write(f"**{t.get('instrument')}**")
                        cols[1].write(tuning_label(t.get("tuning")))
                        capo = t.get("capo")
                        cols[2].write(f"capo {capo}" if capo else "")
                if others:
                    with st.expander(f"Other instruments ({len(others)})"):
                        for t in others:
                            st.write(f"{t.get('instrument')} — {tuning_label(t.get('tuning'))}")

                views = meta.get("views")
                if views:
                    st.caption(f"👁 {views:,} views on Songsterr")

                st.link_button("Open interactive tab ↗", TAB_URL.format(sid))
elif go:
    st.warning("Type a song or artist first.")
