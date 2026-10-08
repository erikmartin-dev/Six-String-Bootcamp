"""Six-String Bootcamp — interactive guitar training app.

Run:  python -m streamlit run app.py
Local data: saved_songs.json, gigs.json (created next to this file)
Secrets (.streamlit/secrets.toml, never commit):
    ELEVENLABS_API_KEY = "..."   # optional — Sgt. Martin's live voice
    ELEVENLABS_VOICE_ID = "..."  # optional — your chosen ElevenLabs voice
"""
import os
import re
import json
import html as htmlmod

import streamlit as st
import streamlit.components.v1 as components

try:
    import requests
except ImportError:
    requests = None

st.set_page_config(
    page_title="Six-String Bootcamp",
    page_icon="🎸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_PATH = os.path.join(DATA_DIR, "saved_songs.json")
GIGS_PATH = os.path.join(DATA_DIR, "gigs.json")

ASSETS = os.path.join(DATA_DIR, "assets", "sgt-martin")
SGT = {
    "portrait": os.path.join(ASSETS, "portrait.webp"),
    "idle": os.path.join(ASSETS, "idle.mp4"),
    "talking": os.path.join(ASSETS, "talking.mp4"),
    "praise": os.path.join(ASSETS, "praise.mp4"),
    "solo": os.path.join(ASSETS, "solo.mp4"),
    "intro_voice": os.path.join(ASSETS, "intro-voice.mp3"),
    "welcome_speech": os.path.join(ASSETS, "welcome-speech.mp3"),
}

# ----------------------------------------------------------------------------
# Theme
# ----------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.hero {
    text-align: center; padding: 2rem 0;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 20px; margin-bottom: 1.25rem;
    border: 1px solid rgba(233, 69, 96, 0.2);
}
.hero h1 { color: #e94560; font-size: 2.6rem; font-weight: 700; margin: 0;
    letter-spacing: -1px; text-shadow: 0 0 30px rgba(233, 69, 96, 0.3); }
.hero p { color: #a0a0a0; font-size: 1.05rem; margin-top: 0.4rem; font-weight: 300; }
.navbtn button { font-size: 0.85rem !important; padding: 0.55rem 0.2rem !important; }
.tool-card {
    background: linear-gradient(145deg, #16213e, #0f3460);
    border-radius: 16px; padding: 1.25rem;
    border: 1px solid rgba(233, 69, 96, 0.1); height: 100%;
}
.course-card {
    background: linear-gradient(145deg, #16213e, #1a1a2e);
    border-radius: 14px; padding: 1.25rem; margin-bottom: 1rem;
    border: 1px solid rgba(233, 69, 96, 0.15);
}
.course-card h4 { color: #f0f0f5; margin: 0 0 0.3rem; }
.course-price { color: #4ade80; font-weight: 700; font-size: 1.2rem; }
.badge {
    display: inline-block; padding: 0.2rem 0.6rem; border-radius: 6px;
    font-size: 0.75rem; font-weight: 600; margin-right: 0.4rem;
}
.badge-paid { background: rgba(233, 69, 96, 0.15); color: #e94560; }
.badge-draft { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }
.badge-free { background: rgba(74, 222, 128, 0.15); color: #4ade80; }
.sgt-speech {
    background: #16213e; border: 1px solid rgba(233,69,96,.4);
    border-left: 4px solid #e94560; border-radius: 0 12px 12px 0;
    padding: 1rem 1.25rem; color: #f0f0f5; font-size: 1.02rem;
}
.sgt-speech b { color: #e94560; }
/* chord sheets: [C]lyrics -> chord above the word */
.cs-line { margin-bottom: 0.45rem; font-size: 1.08rem; line-height: 2.1; }
.cs-chunk { display: inline-block; vertical-align: bottom; }
.cs-chord { display: block; color: #e94560; font-weight: 700; font-size: 0.95em;
    min-height: 1.25em; white-space: pre; }
.cs-lyr { display: block; white-space: pre; color: #f0f0f5; }
pre.tabview {
    background: #0d0d1a; border: 1px solid rgba(233,69,96,.25); border-radius: 12px;
    padding: 1rem; overflow-x: auto; color: #c9c9d9;
    font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.85rem; line-height: 1.35;
}
.setlist-item {
    background: #16213e; border-radius: 10px; padding: 0.6rem 0.9rem; margin-bottom: 0.5rem;
    border: 1px solid rgba(233,69,96,.2); color: #f0f0f5;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Persistence
# ----------------------------------------------------------------------------
def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------------
# Chord sheets — [C]lyrics renders with the chord above the word
# ----------------------------------------------------------------------------
def chordsheet_html(text):
    out = []
    for line in (text or "").split("\n"):
        chunks = []
        for m in re.finditer(r"\[([^\]]+)\]([^\[]*)", line):
            chord, lyr = m.group(1), m.group(2)
            lyr = lyr if lyr else " "
            chunks.append(
                f'<span class="cs-chunk"><span class="cs-chord">'
                f'{htmlmod.escape(chord)}</span><span class="cs-lyr">'
                f'{htmlmod.escape(lyr)}</span></span>')
        head = re.split(r"\[[^\]]+\]", line, maxsplit=1)[0]
        if head and not line.startswith("["):
            chunks.insert(0,
                f'<span class="cs-chunk"><span class="cs-chord"> </span>'
                f'<span class="cs-lyr">{htmlmod.escape(head)}</span></span>')
        out.append('<div class="cs-line">' + "".join(chunks) + "</div>")
    return "".join(out)


def song_view(song, key_prefix):
    """Lyrics+chords default view with a dedicated Tablature toggle button."""
    view = st.session_state.get(key_prefix + "_view", "chords")
    b1, b2, _ = st.columns([1, 1, 3])
    if b1.button("🎼 Lyrics + Chords", key=key_prefix + "_vchords",
                 type="primary" if view == "chords" else "secondary"):
        st.session_state[key_prefix + "_view"] = "chords"
        st.rerun()
    if b2.button("🎸 Tablature", key=key_prefix + "_vtab",
                 type="primary" if view == "tab" else "secondary"):
        st.session_state[key_prefix + "_view"] = "tab"
        st.rerun()
    st.markdown("")
    if view == "tab":
        tab = (song.get("tab") or "").strip()
        if tab:
            st.markdown(f"<pre class='tabview'>{htmlmod.escape(tab)}</pre>",
                        unsafe_allow_html=True)
        else:
            st.info("No tablature saved for this song yet — the chord sheet above "
                    "has everything you need to strum it.")
    else:
        st.markdown(chordsheet_html(song.get("chordsheet", "")), unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Built-in songs (public-domain traditionals)
# ----------------------------------------------------------------------------
BUILTIN_SONGS = [
    {
        "title": "Amazing Grace", "artist": "Traditional", "key": "G",
        "chordsheet":
"[G]Amazing [C]grace, how [G]sweet the [Em]sound\n"
"That [G]saved a [D]wretch like [G]me\n"
"[G]I [C]once was [G]lost, but [Em]now am [G]found\n"
"Was [G]blind, but [D]now I [G]see",
        "tab":
"Starter melody — first phrase (standard tuning)\n"
"e|--3----7----5----3----0-------|\n"
"B|--3---------------------3----|\n"
"G|-----------------------------|\n"
"D|-----------------------------|\n"
"A|-----------------------------|\n"
"E|-----------------------------|",
    },
    {
        "title": "House of the Rising Sun", "artist": "Traditional", "key": "Am",
        "chordsheet":
"[Am]There [C]is a [D]house in [F]New Or[Am]leans\n"
"They [C]call the [E]Rising [E7]Sun\n"
"[Am]And it's [C]been the [D]ruin of [F]many a poor [Am]boy\n"
"And [E]God, I [Am]know, I'm [C]one",
        "tab":
"Classic fingerpicking pattern — one bar per chord (standard tuning)\n"
"   Am              C               D               F\n"
"e|--------0--------------|--------0--------------|--------2--------------|--------1--------------|\n"
"B|------1---1------------|------1---1------------|------3---3------------|------1---1------------|\n"
"G|----2-------2----------|----0-------0----------|----2-------2----------|----2-------2----------|\n"
"D|--2-----------2--------|--2-----------2--------|--0-----------0--------|--3-----------3--------|\n"
"A|0----------------------|3----------------------|-----------------------|-----------------------|\n"
"E|-----------------------|-----------------------|-----------------------|-----------------------|\n"
"   E\n"
"e|--------0--------------|\n"
"B|------0---0------------|\n"
"G|----1-------1----------|\n"
"D|--2-----------2--------|\n"
"A|--2--------------------|\n"
"E|0----------------------|",
    },
    {
        "title": "Scarborough Fair", "artist": "Traditional English ballad", "key": "Dm",
        "chordsheet":
"[Dm]Are you [F]going to [Dm]Scarborough [C]Fair?\n"
"[Dm]Parsley, [F]sage, rose[Dm]mary and [C]thyme\n"
"[Dm]Re[F]member [Dm]me to [C]one who lives [Dm]there\n"
"[Dm]She [F]once [Dm]was a [C]true love of [Dm]mine",
        "tab":
"Starter melody — first phrase (standard tuning)\n"
"e|--5----8----10---8----5----3--|\n"
"B|------------------------------|\n"
"G|------------------------------|\n"
"D|------------------------------|\n"
"A|------------------------------|\n"
"E|------------------------------|",
    },
]

# ----------------------------------------------------------------------------
# Courses (draft curriculum — filled in properly in the curriculum session)
# ----------------------------------------------------------------------------
COURSES = [
    ("Guitar Anatomy & Posture", 29, "Know every part of the guitar and hold it like a pro from day one."),
    ("Tuning & String Care", 29, "Tune by ear and with a tuner; change strings without fear."),
    ("First Chords: G, C, D, Em", 29, "The four chords behind a thousand songs."),
    ("Strumming Foundations", 29, "Down, up, and the patterns that make songs move."),
    ("The A Family: A, Am, E, Em, D", 29, "Five more essential shapes, clean every time."),
    ("Clean Chord Changes", 29, "Kill the buzz and the pause between chords."),
    ("Power Chords & Palm Muting", 29, "Your first taste of rock rhythm guitar."),
    ("Barre Chords: E-Shape", 39, "One shape, twelve chords. The fretboard opens up."),
    ("Barre Chords: A-Shape", 39, "The second barre family — no more capo crutch."),
    ("The Pentatonic Box", 39, "The five-note scale behind every great solo."),
    ("Rhythm & Timing Mastery", 39, "Play in the pocket with the metronome as your drummer."),
    ("Your First 10 Songs (Capstone)", 49, "Put it all together: ten full songs, start to finish."),
]
MEMBERSHIP = [
    ("Monthly", 19, "All 12 courses, new lessons weekly, cancel anytime."),
    ("Annual", 149, "Everything in Monthly, two months free, priority Q&A."),
    ("Lifetime", 399, "Pay once. Every course, every future update, forever."),
]

# ----------------------------------------------------------------------------
# Chord diagrams
# ----------------------------------------------------------------------------
def generate_fretboard_svg(highlight_notes, title=None, fret_spacing=40,
                           string_spacing=20, highlight_color="#e94560"):
    max_fret = max([n.get("fret", 0) for n in highlight_notes] + [1])
    width = (max_fret + 1.5) * fret_spacing + 30
    height = 5 * string_spacing + 40
    svg = (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           f'xmlns="http://www.w3.org/2000/svg">')
    for note_info in highlight_notes:
        string_idx = note_info.get("string", 0)
        fret = note_info.get("fret", 0)
        note_name = note_info.get("note", "")
        finger = note_info.get("finger", "")
        x = (fret + 0.5) * fret_spacing + 14 if fret > 0 else 25
        y = 14 + string_idx * string_spacing
        if fret == 0:
            svg += (f'<circle cx="{x}" cy="{y}" r="11" fill="none" '
                    f'stroke="{highlight_color}" stroke-width="2.5"/>')
            svg += (f'<text x="{x}" y="{y+4}" text-anchor="middle" fill="{highlight_color}" '
                    f'font-size="10" font-weight="bold" font-family="Inter, sans-serif">{note_name}</text>')
        elif fret == -1:
            svg += (f'<text x="{x}" y="{y+5}" text-anchor="middle" fill="#888" '
                    f'font-size="14" font-weight="bold" font-family="Inter, sans-serif">✕</text>')
        else:
            svg += (f'<circle cx="{x}" cy="{y}" r="13" fill="{highlight_color}" opacity="0.95"/>')
            svg += (f'<text x="{x}" y="{y+4}" text-anchor="middle" fill="white" '
                    f'font-size="10" font-weight="bold" font-family="Inter, sans-serif">{note_name}</text>')
            if finger:
                svg += (f'<text x="{x}" y="{y+22}" text-anchor="middle" fill="#e94560" '
                        f'font-size="9" font-family="Inter, sans-serif">{finger}</text>')
    for i, label in enumerate(["e", "B", "G", "D", "A", "E"]):
        y = 14 + i * string_spacing
        svg += (f'<text x="8" y="{y+4}" text-anchor="middle" fill="#888" '
                f'font-size="11" font-weight="600" font-family="Inter, sans-serif">{label}</text>')
    svg += '</svg>'
    if title:
        return (f'<div style="margin:1rem 0;"><p style="color:#e94560;font-weight:600;'
                f'margin-bottom:0.5rem;font-size:1.1rem;">{title}</p>{svg}</div>')
    return f'<div style="margin:1rem 0;">{svg}</div>'


CHORD_SHAPES = {
    "C Major": [
        {"string": 0, "fret": 0, "note": "E"},
        {"string": 1, "fret": 1, "note": "C", "finger": "1"},
        {"string": 2, "fret": 0, "note": "G"},
        {"string": 3, "fret": 2, "note": "E", "finger": "2"},
        {"string": 4, "fret": 3, "note": "C", "finger": "3"},
        {"string": 5, "fret": -1, "note": "X"}],
    "G Major": [
        {"string": 0, "fret": 3, "note": "G", "finger": "4"},
        {"string": 1, "fret": 0, "note": "B"},
        {"string": 2, "fret": 0, "note": "G"},
        {"string": 3, "fret": 0, "note": "D"},
        {"string": 4, "fret": 2, "note": "B", "finger": "2"},
        {"string": 5, "fret": 3, "note": "G", "finger": "3"}],
    "D Major": [
        {"string": 0, "fret": 2, "note": "F#", "finger": "2"},
        {"string": 1, "fret": 3, "note": "D", "finger": "3"},
        {"string": 2, "fret": 2, "note": "A", "finger": "1"},
        {"string": 3, "fret": 0, "note": "D"},
        {"string": 4, "fret": -1, "note": "X"},
        {"string": 5, "fret": -1, "note": "X"}],
    "A Major": [
        {"string": 0, "fret": 0, "note": "E"},
        {"string": 1, "fret": 2, "note": "C#", "finger": "2"},
        {"string": 2, "fret": 2, "note": "A", "finger": "3"},
        {"string": 3, "fret": 2, "note": "E", "finger": "1"},
        {"string": 4, "fret": 0, "note": "A"},
        {"string": 5, "fret": -1, "note": "X"}],
    "E Major": [
        {"string": 0, "fret": 0, "note": "E"},
        {"string": 1, "fret": 0, "note": "B"},
        {"string": 2, "fret": 1, "note": "G#", "finger": "1"},
        {"string": 3, "fret": 2, "note": "E", "finger": "2"},
        {"string": 4, "fret": 2, "note": "B", "finger": "3"},
        {"string": 5, "fret": 0, "note": "E"}],
    "A Minor": [
        {"string": 0, "fret": 0, "note": "E"},
        {"string": 1, "fret": 1, "note": "C", "finger": "1"},
        {"string": 2, "fret": 2, "note": "A", "finger": "2"},
        {"string": 3, "fret": 2, "note": "E", "finger": "3"},
        {"string": 4, "fret": 0, "note": "A"},
        {"string": 5, "fret": -1, "note": "X"}],
    "E Minor": [
        {"string": 0, "fret": 0, "note": "E"},
        {"string": 1, "fret": 0, "note": "B"},
        {"string": 2, "fret": 0, "note": "G"},
        {"string": 3, "fret": 2, "note": "E", "finger": "2"},
        {"string": 4, "fret": 2, "note": "B", "finger": "3"},
        {"string": 5, "fret": 0, "note": "E"}],
}

# ----------------------------------------------------------------------------
# Sgt. Martin
# ----------------------------------------------------------------------------
def _secret(name):
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def sgt_speak(text):
    key = _secret("ELEVENLABS_API_KEY")
    voice_id = _secret("ELEVENLABS_VOICE_ID")
    if not key or not voice_id or requests is None:
        return None
    cache = st.session_state.setdefault("sgt_voice_cache", {})
    if text in cache:
        return cache[text]
    try:
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_monolingual_v1"},
            timeout=30)
        r.raise_for_status()
        cache[text] = r.content
        return r.content
    except Exception:
        return None


def sgt_card(message, voice_text=None):
    """Inline instructor card (no sidebar). Honors the instructor toggle."""
    if not st.session_state.get("instructor_on", True):
        return
    c1, c2 = st.columns([1, 4])
    with c1:
        if os.path.exists(SGT["portrait"]):
            st.image(SGT["portrait"])
    with c2:
        st.markdown(f'<div class="sgt-speech">{message}</div>', unsafe_allow_html=True)
        if voice_text:
            audio = sgt_speak(voice_text)
            if audio:
                st.audio(audio, format="audio/mp3")


def sgt_intro():
    if st.session_state.get("enlisted"):
        return True
    st.markdown('<div class="hero"><h1>🎸 SIX-STRING BOOTCAMP</h1>'
                '<p>Your instructor is about to report for duty.</p></div>',
                unsafe_allow_html=True)
    col1, col2 = st.columns([3, 2])
    with col1:
        if os.path.exists(SGT["solo"]):
            st.video(SGT["solo"])
        st.caption("Sgt. Martin warming up. Sound on, recruit.")
    with col2:
        if os.path.exists(SGT["portrait"]):
            st.image(SGT["portrait"])
        if os.path.exists(SGT["welcome_speech"]):
            st.audio(SGT["welcome_speech"])
    st.markdown("")
    if st.button("REPORT FOR TRAINING, SERGEANT!", type="primary"):
        st.session_state["enlisted"] = True
        st.rerun()
    return False

# ----------------------------------------------------------------------------
# Tools: metronome + tuner (Web Audio, run fully in the browser)
# ----------------------------------------------------------------------------
METRONOME_HTML = """
<div style="text-align:center;padding:8px;">
  <div style="font-size:3rem;font-weight:700;color:#e94560;" id="bpmLabel">100</div>
  <div style="color:#a0a0a0;margin-bottom:8px;">BPM</div>
  <input id="bpm" type="range" min="40" max="208" value="100" style="width:90%;accent-color:#e94560;">
  <div style="margin-top:10px;">
    <button id="metroBtn" style="background:#e94560;color:#fff;border:none;border-radius:10px;
      padding:10px 26px;font-size:1rem;font-weight:700;cursor:pointer;">START</button>
  </div>
  <div id="beatDots" style="margin-top:10px;font-size:1.4rem;letter-spacing:6px;color:#5a5a72;">●●●●</div>
</div>
<script>
let mCtx=null, mTimer=null, mBeat=0;
const bpmEl=document.getElementById('bpm'), label=document.getElementById('bpmLabel'),
      btn=document.getElementById('metroBtn'), dots=document.getElementById('beatDots');
bpmEl.addEventListener('input',()=>{label.textContent=bpmEl.value; if(mTimer){stop();start();}});
function click(accent){
  mCtx=mCtx||new (window.AudioContext||window.webkitAudioContext)();
  const o=mCtx.createOscillator(), g=mCtx.createGain();
  o.frequency.value=accent?1320:880; o.type='square';
  g.gain.setValueAtTime(0.25,mCtx.currentTime);
  g.gain.exponentialRampToValueAtTime(0.001,mCtx.currentTime+0.06);
  o.connect(g); g.connect(mCtx.destination); o.start(); o.stop(mCtx.currentTime+0.07);
}
function start(){
  mBeat=0; const iv=60000/parseInt(bpmEl.value,10);
  mTimer=setInterval(()=>{
    click(mBeat%4===0);
    dots.innerHTML=[0,1,2,3].map(i=>'<span style="color:'+(i===mBeat%4?'#e94560':'#5a5a72')+'">●</span>').join('');
    mBeat++;
  },iv);
  btn.textContent='STOP'; btn.style.background='#5a5a72';
}
function stop(){ clearInterval(mTimer); mTimer=null; btn.textContent='START'; btn.style.background='#e94560'; }
btn.addEventListener('click',()=>{ mTimer?stop():start(); });
</script>
"""

TUNER_HTML = """
<div style="text-align:center;padding:8px;">
  <div id="tNote" style="font-size:3.2rem;font-weight:700;color:#e94560;">–</div>
  <div id="tCents" style="color:#a0a0a0;margin-bottom:6px;">press START and play a string</div>
  <div style="width:90%;height:10px;background:#16213e;border-radius:6px;margin:0 auto;position:relative;overflow:hidden;">
    <div id="tNeedle" style="position:absolute;top:0;bottom:0;left:50%;width:4px;background:#e94560;border-radius:2px;"></div>
  </div>
  <div style="display:flex;justify-content:space-between;width:90%;margin:4px auto 0;color:#5a5a72;font-size:0.8rem;">
    <span>-50¢</span><span>in tune</span><span>+50¢</span>
  </div>
  <button id="tBtn" style="margin-top:10px;background:#e94560;color:#fff;border:none;border-radius:10px;
    padding:10px 26px;font-size:1rem;font-weight:700;cursor:pointer;">START TUNER</button>
  <div style="color:#5a5a72;font-size:0.8rem;margin-top:8px;">needs microphone access · works on localhost / HTTPS</div>
</div>
<script>
const NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
let tRunning=false;
const nEl=document.getElementById('tNote'), cEl=document.getElementById('tCents'),
      needle=document.getElementById('tNeedle'), tBtn=document.getElementById('tBtn');
function autoCorrelate(buf,sr){
  let SIZE=buf.length, rms=0;
  for(let i=0;i<SIZE;i++) rms+=buf[i]*buf[i];
  if(Math.sqrt(rms/SIZE)<0.01) return -1;
  let r1=0,r2=SIZE-1;
  const b=buf.slice(0);
  for(let i=0;i<SIZE/2;i++) if(Math.abs(b[i])<0.2){b[i]=0;r1=i;}
  for(let i=1;i<SIZE/2;i++) if(Math.abs(b[SIZE-i])<0.2){b[SIZE-i]=0;r2=SIZE-i;}
  const b2=b.slice(r1,r2); SIZE=b2.length;
  const c=new Array(SIZE).fill(0);
  for(let i=0;i<SIZE;i++) for(let j=0;j<SIZE-i;j++) c[i]+=b2[j]*b2[j+i];
  let d=0; while(d<SIZE-1 && c[d]>c[d+1]) d++;
  let maxv=-1,maxp=-1;
  for(let i=d;i<SIZE;i++) if(c[i]>maxv){maxv=c[i];maxp=i;}
  let T0=maxp;
  if(T0>0&&T0<SIZE-1){
    const x1=c[T0-1],x2=c[T0],x3=c[T0+1], aa=(x1+x3-2*x2)/2, bb=(x3-x1)/2;
    if(aa) T0=T0-bb/(2*aa);
  }
  return sr/T0;
}
tBtn.addEventListener('click', async ()=>{
  if(tRunning) return;
  try{
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});
    const ctx=new (window.AudioContext||window.webkitAudioContext)();
    const src=ctx.createMediaStreamSource(stream), an=ctx.createAnalyser();
    an.fftSize=2048; src.connect(an);
    const buf=new Float32Array(an.fftSize);
    tRunning=true; tBtn.textContent='LISTENING…'; tBtn.style.background='#4ade80';
    (function tick(){
      an.getFloatTimeDomainData(buf);
      const f=autoCorrelate(buf,ctx.sampleRate);
      if(f>40&&f<1200){
        const n=Math.round(12*Math.log2(f/440))+69;
        const ref=440*Math.pow(2,(n-69)/12);
        const cents=Math.round(1200*Math.log2(f/ref));
        nEl.textContent=NAMES[n%12];
        nEl.style.color=Math.abs(cents)<6?'#4ade80':'#e94560';
        cEl.textContent=(cents>0?'+':'')+cents+'¢ '+(Math.abs(cents)<6?'— in tune':(cents<0?'— tune up':'— tune down'));
        needle.style.left=(50+Math.max(-50,Math.min(50,cents)))+'%';
      }
      if(tRunning) requestAnimationFrame(tick);
    })();
  }catch(e){ cEl.textContent='microphone blocked — allow access and retry'; }
});
</script>
"""


def metronome():
    components.html(METRONOME_HTML, height=300, scrolling=False)


def tuner():
    components.html(TUNER_HTML, height=380, scrolling=False)


def fretboard_lab():
    try:
        with open(os.path.join(DATA_DIR, "fretboard.html"), encoding="utf-8") as f:
            components.html(f.read(), height=620, scrolling=False)
    except FileNotFoundError:
        st.warning("fretboard.html not found next to app.py.")


# ----------------------------------------------------------------------------
# Song search (Songsterr API, no key needed)
# ----------------------------------------------------------------------------
API_SEARCH = "https://www.songsterr.com/api/songs"
API_META = "https://www.songsterr.com/api/meta/{}"
TAB_URL = "https://www.songsterr.com/a/wsa/tab-s{}"
NAMES12 = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
STANDARD = [64, 59, 55, 50, 45, 40]


def tuning_label(tuning):
    if not tuning:
        return "—"
    names = [NAMES12[m % 12] for m in reversed(tuning)]
    label = " ".join(names)
    if list(tuning) == STANDARD:
        label += " (standard)"
    return label


@st.cache_data(ttl=3600, show_spinner=False)
def search_songs(query):
    r = requests.get(API_SEARCH, params={"pattern": query}, timeout=12)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=3600, show_spinner=False)
def song_meta(song_id):
    r = requests.get(API_META.format(song_id), timeout=12)
    r.raise_for_status()
    return r.json()


def find_songs_page():
    st.markdown('<div class="hero"><h1>🔍 FIND SONGS</h1>'
                '<p>Live internet library — search any song, see its guitar tracks.</p></div>',
                unsafe_allow_html=True)
    if requests is None:
        st.error("The 'requests' package is required for song search.")
        return
    q = st.text_input("Search songs or artists", placeholder="e.g. wonderwall, metallica, hallelujah")
    if st.button("Search", type="primary"):
        st.session_state["song_results"] = q.strip()
    query = st.session_state.get("song_results", "")
    if not query:
        return
    try:
        with st.spinner("Searching..."):
            results = search_songs(query)
    except Exception as e:
        st.error(f"Search failed: {e}")
        return
    if not results:
        st.info("No songs found — try a different spelling.")
        return
    st.caption(f"{len(results)} result(s)")
    saved = load_json(SAVED_PATH, [])
    for s in results:
        sid = s.get("songId")
        title = s.get("title", "?")
        artist = s.get("artist", "?")
        with st.expander(f"{title} — {artist}"):
            try:
                meta = song_meta(sid)
                tracks = meta.get("tracks", [])
                guitars = [t for t in tracks
                           if t.get("instrument") and "guitar" in t["instrument"].lower()]
                if guitars:
                    for t in guitars:
                        st.write(f"🎸 {t.get('name', 'Guitar')} · "
                                 f"tuning: {tuning_label(t.get('tuning'))} · "
                                 f"capo: {t.get('capo', 0)}")
                else:
                    st.write("No isolated guitar track listed.")
            except Exception:
                st.write("Track details unavailable.")
            c1, c2 = st.columns(2)
            c1.link_button("Open Interactive Tab", TAB_URL.format(sid))
            if c2.button("💾 Save", key=f"save_{sid}"):
                saved.append({"title": title, "artist": artist,
                              "source": "Songsterr",
                              "url": TAB_URL.format(sid),
                              "chordsheet": "", "tab": ""})
                save_json(SAVED_PATH, saved)
                st.success(f"Saved “{title}”. Find it under Saved.")

# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
def page_home():
    st.markdown('<div class="hero"><h1>🎸 SIX-STRING BOOTCAMP</h1>'
                '<p>Interactive guitar training · lyrics with chords · gig-ready setlists</p></div>',
                unsafe_allow_html=True)
    sgt_card("<b>Welcome back, recruit.</b> Everything's up top now — pick a "
             "section and get to work. The fretboard doesn't practice itself.")
    on = st.checkbox("🎖️ Sgt. Martin instructor tips", value=st.session_state.get("instructor_on", True))
    st.session_state["instructor_on"] = on
    st.markdown("### Jump in")
    grid = [
        ("🎵", "Songs", "Lyrics with chords above the words, tablature on its own button."),
        ("🔍", "Find Songs", "Search the whole internet for tabs and guitar tracks."),
        ("💾", "Saved", "Your personal songbook, kept on this device."),
        ("🎤", "Gigs", "Build setlists for your shows."),
        ("📚", "Learn", "Fretboard lab and the chord wall."),
        ("🎓", "Courses", "Twelve paid courses, fundamentals first."),
        ("💳", "Membership", "One pass, everything included."),
        ("🧰", "Tools", "Metronome and tuner, free forever."),
    ]
    cols = st.columns(2)
    for i, (icon, name, desc) in enumerate(grid):
        with cols[i % 2]:
            if st.button(f"{icon} {name}\n{desc}", key=f"home_{name}", use_container_width=True):
                st.session_state["page"] = name
                st.rerun()


def page_songs():
    st.markdown('<div class="hero"><h1>🎵 SONGS</h1>'
                '<p>Chords ride above the lyrics. Tablature gets its own button.</p></div>',
                unsafe_allow_html=True)
    st.markdown("### Built-in songbook")
    titles = [s["title"] for s in BUILTIN_SONGS]
    pick = st.selectbox("Choose a song", titles)
    song = next(s for s in BUILTIN_SONGS if s["title"] == pick)
    st.caption(f"{song['artist']} · Key of {song['key']}")
    song_view(song, key_prefix=f"builtin_{pick}")
    if st.button("💾 Save to My Songs", key=f"keep_{pick}"):
        saved = load_json(SAVED_PATH, [])
        saved.append({**song, "source": "Built-in"})
        save_json(SAVED_PATH, saved)
        st.success(f"Saved “{pick}”.")
    st.markdown("---")
    st.markdown("### Paste your own")
    st.caption("Format: put the chord in [brackets] right where it changes — "
               "e.g. `[G]Hello [C]darkness`.")
    with st.form("paste_song"):
        pt = st.text_input("Title")
        pa = st.text_input("Artist (optional)")
        pcs = st.text_area("Lyrics with [chords]", height=150)
        ptab = st.text_area("Tablature (optional)", height=100)
        ok = st.form_submit_button("Preview & Save")
    if ok and pt.strip() and pcs.strip():
        song = {"title": pt.strip(), "artist": pa.strip() or "—",
                "source": "Pasted", "chordsheet": pcs, "tab": ptab}
        st.markdown("**Preview**")
        song_view(song, key_prefix="paste_preview")
        saved = load_json(SAVED_PATH, [])
        saved.append(song)
        save_json(SAVED_PATH, saved)
        st.success(f"Saved “{pt.strip()}”.")
    elif ok:
        st.warning("Give it a title and at least one line of lyrics.")


def page_saved():
    st.markdown('<div class="hero"><h1>💾 SAVED SONGS</h1>'
                '<p>Your songbook lives on this device.</p></div>',
                unsafe_allow_html=True)
    saved = load_json(SAVED_PATH, [])
    if not saved:
        st.info("Nothing saved yet. Grab songs from Songs or Find Songs.")
        return
    gigs = load_json(GIGS_PATH, [])
    for i, s in enumerate(saved):
        with st.expander(f"{s.get('title', '?')} — {s.get('artist', '?')}"):
            if s.get("url"):
                st.link_button("Open Tab", s["url"])
            if s.get("chordsheet"):
                song_view(s, key_prefix=f"saved_{i}")
            c1, c2 = st.columns(2)
            if gigs:
                gname = c1.selectbox("Add to gig", [g["name"] for g in gigs],
                                     key=f"agt_{i}")
                if c1.button("➕ Add", key=f"add_{i}"):
                    g = next(g for g in gigs if g["name"] == gname)
                    g.setdefault("setlist", []).append(s.get("title", "?"))
                    save_json(GIGS_PATH, gigs)
                    st.success(f"Added to {gname}.")
            if c2.button("🗑️ Remove", key=f"del_{i}"):
                saved.pop(i)
                save_json(SAVED_PATH, saved)
                st.rerun()


def page_gigs():
    st.markdown('<div class="hero"><h1>🎤 GIGS</h1>'
                '<p>Setlists for show night. In order. No surprises.</p></div>',
                unsafe_allow_html=True)
    gigs = load_json(GIGS_PATH, [])
    saved = load_json(SAVED_PATH, [])
    with st.form("new_gig"):
        gn = st.text_input("Gig name", placeholder="e.g. Rusty's Bar — Friday")
        gd = st.text_input("Date", placeholder="e.g. 2026-11-14")
        gv = st.text_input("Venue (optional)")
        if st.form_submit_button("Create Gig") and gn.strip():
            gigs.append({"name": gn.strip(), "date": gd.strip(),
                         "venue": gv.strip(), "setlist": []})
            save_json(GIGS_PATH, gigs)
            st.success(f"Gig “{gn.strip()}” created.")
            st.rerun()
    if not gigs:
        st.info("No gigs yet — create your first one above.")
        return
    pick = st.selectbox("Your gigs", [g["name"] for g in gigs])
    gi = next(i for i, g in enumerate(gigs) if g["name"] == pick)
    gig = gigs[gi]
    st.caption(f"{gig.get('date', '')} · {gig.get('venue', '')}".strip(" ·"))
    st.markdown("### Setlist")
    for si, title in enumerate(gig.get("setlist", [])):
        c1, c2, c3, c4 = st.columns([6, 1, 1, 1])
        c1.markdown(f"<div class='setlist-item'><b>{si+1}.</b> {htmlmod.escape(title)}</div>",
                    unsafe_allow_html=True)
        if c2.button("↑", key=f"up_{gi}_{si}") and si > 0:
            gig["setlist"][si-1], gig["setlist"][si] = gig["setlist"][si], gig["setlist"][si-1]
            save_json(GIGS_PATH, gigs); st.rerun()
        if c3.button("↓", key=f"dn_{gi}_{si}") and si < len(gig["setlist"])-1:
            gig["setlist"][si+1], gig["setlist"][si] = gig["setlist"][si], gig["setlist"][si+1]
            save_json(GIGS_PATH, gigs); st.rerun()
        if c4.button("✕", key=f"rm_{gi}_{si}"):
            gig["setlist"].pop(si)
            save_json(GIGS_PATH, gigs); st.rerun()
    if saved:
        add = st.selectbox("Add a saved song",
                           [s.get("title", "?") for s in saved], key=f"sadd_{gi}")
        if st.button("➕ Add to Setlist"):
            gig.setdefault("setlist", []).append(add)
            save_json(GIGS_PATH, gigs); st.rerun()
    else:
        st.info("Save some songs first, then build your setlist.")
    if st.button("🗑️ Delete Gig", key=f"gdel_{gi}"):
        gigs.pop(gi); save_json(GIGS_PATH, gigs); st.rerun()


def page_learn():
    st.markdown('<div class="hero"><h1>📚 LEARN</h1>'
                '<p>Fretboard lab and the chord wall.</p></div>',
                unsafe_allow_html=True)
    sgt_card("<b>Fundamentals win fights.</b> Ten minutes on the fretboard, "
             "then drill one chord shape until it's boring. Boring means learned.")
    st.markdown("### 🎸 Fretboard Lab")
    fretboard_lab()
    st.markdown("### Chord Wall")
    cols = st.columns(3)
    for i, (name, notes) in enumerate(CHORD_SHAPES.items()):
        with cols[i % 3]:
            st.markdown(generate_fretboard_svg(notes, title=name), unsafe_allow_html=True)
    if st.button("🎖️ NAILED IT!"):
        sgt_card("<b>Outstanding!</b> Clean changes, no buzz. That's how a guitarist is made.")
        st.balloons()


def page_courses():
    st.markdown('<div class="hero"><h1>🎓 COURSES</h1>'
                '<p>Twelve courses. Fundamentals first. <span class="badge badge-draft">DRAFT CURRICULUM</span></p></div>',
                unsafe_allow_html=True)
    sgt_card("<b>Twelve courses stand between you and the guitarist you were "
             "born to be.</b> Take them in order, recruit — no skipping leg day.")
    mine = st.session_state.setdefault("my_courses", [])
    for idx, (name, price, desc) in enumerate(COURSES):
        st.markdown(f"""<div class="course-card"><h4>Course {idx+1}: {htmlmod.escape(name)}</h4>
        <div>{htmlmod.escape(desc)}</div>
        <div style="margin-top:0.4rem;"><span class="badge badge-paid">PAID</span>
        <span class="course-price">${price}</span></div></div>""", unsafe_allow_html=True)
        if name in mine:
            st.success("On your list — checkout opens at launch.")
        elif st.button(f"Enroll — ${price}", key=f"enroll_{idx}"):
            mine.append(name)
            st.success(f"“{name}” is on your list. Checkout opens at launch.")
    st.caption("Full lesson content for each course is being written now.")


def page_membership():
    st.markdown('<div class="hero"><h1>💳 MEMBERSHIP</h1>'
                '<p>One pass. Every course. Every update.</p></div>',
                unsafe_allow_html=True)
    sgt_card("<b>Do the math, recruit.</b> Twelve courses individually would run "
             "you $400+. Membership is the smart money.")
    plan = st.session_state.get("my_plan")
    cols = st.columns(3)
    for i, (name, price, desc) in enumerate(MEMBERSHIP):
        with cols[i]:
            st.markdown(f"""<div class="course-card" style="text-align:center;">
            <h4>{name}</h4><div class="course-price">${price}</div>
            <div style="font-size:0.85rem;color:#a0a0a0;">{'/month' if name=='Monthly' else ('/year' if name=='Annual' else 'one-time')}</div>
            <div style="margin:0.6rem 0;">{desc}</div></div>""", unsafe_allow_html=True)
            if plan == name:
                st.success("Your plan — checkout opens at launch.")
            elif st.button(f"Choose {name}", key=f"plan_{i}", use_container_width=True):
                st.session_state["my_plan"] = name
                st.rerun()


def page_tools():
    st.markdown('<div class="hero"><h1>🧰 TOOLS</h1>'
                '<p>Free forever. Tune up, lock in.</p></div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tool-card"><h3 style="color:#e94560;">⏱️ Metronome</h3>',
                    unsafe_allow_html=True)
        metronome()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tool-card"><h3 style="color:#e94560;">🎛️ Tuner</h3>',
                    unsafe_allow_html=True)
        tuner()
        st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Router — top button nav, no sidebar
# ----------------------------------------------------------------------------
NAV = [
    ("🏠", "Home"), ("🎵", "Songs"), ("🔍", "Find Songs"), ("💾", "Saved"),
    ("🎤", "Gigs"), ("📚", "Learn"), ("🎓", "Courses"), ("💳", "Membership"),
    ("🧰", "Tools"),
]
PAGES = {
    "Home": page_home, "Songs": page_songs, "Find Songs": find_songs_page,
    "Saved": page_saved, "Gigs": page_gigs, "Learn": page_learn,
    "Courses": page_courses, "Membership": page_membership, "Tools": page_tools,
}

if not sgt_intro():
    st.stop()

if "page" not in st.session_state:
    st.session_state["page"] = "Home"

st.markdown('<div class="navbtn">', unsafe_allow_html=True)
row1, row2 = st.columns(5), st.columns(4)
for i, (icon, name) in enumerate(NAV):
    col = row1[i] if i < 5 else row2[i - 5]
    active = st.session_state["page"] == name
    with col:
        if st.button(f"{icon} {name}", key=f"nav_{name}", use_container_width=True,
                     type="primary" if active else "secondary"):
            st.session_state["page"] = name
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)
st.markdown("")

PAGES[st.session_state["page"]]()

st.markdown("---")
st.caption("Six-String Bootcamp · Practice daily, recruit.")
