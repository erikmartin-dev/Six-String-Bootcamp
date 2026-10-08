"""Six-String Bootcamp — interactive guitar training app.

Run:  streamlit run app.py
Pages: put song_search.py in pages/ (auto-discovered by Streamlit)
Secrets (.streamlit/secrets.toml, never commit):
    ELEVENLABS_API_KEY = "..."   # optional — enables Sgt. Martin's live voice
    ELEVENLABS_VOICE_ID = "..."  # optional — your chosen ElevenLabs voice
"""
import os
import base64

import streamlit as st
import streamlit.components.v1 as components

try:
    import requests
except ImportError:  # requests optional; only needed for ElevenLabs voice
    requests = None


st.set_page_config(
    page_title="Six String Boot Camp",
    page_icon="🎸",
    layout="wide",
    initial_sidebar_state="expanded",
)

ASSETS = "assets/sgt-martin"
SGT = {
    "portrait": f"{ASSETS}/portrait.webp",
    "idle": f"{ASSETS}/idle.mp4",
    "talking": f"{ASSETS}/talking.mp4",
    "praise": f"{ASSETS}/praise.mp4",
    "solo": f"{ASSETS}/solo.mp4",
    "intro_voice": f"{ASSETS}/intro-voice.mp3",
    "welcome_speech": f"{ASSETS}/welcome-speech.mp3",
}

# ----------------------------------------------------------------------------
# Theme
# ----------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main-header {
    text-align: center; padding: 2.5rem 0;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 20px; margin-bottom: 2rem;
    border: 1px solid rgba(233, 69, 96, 0.2);
}
.main-header h1 {
    color: #e94560; font-size: 3.2rem; font-weight: 700; margin: 0;
    letter-spacing: -2px; text-shadow: 0 0 30px rgba(233, 69, 96, 0.3);
}
.main-header p { color: #a0a0a0; font-size: 1.15rem; margin-top: 0.5rem; font-weight: 300; }
.tool-card {
    background: linear-gradient(145deg, #16213e, #0f3460);
    border-radius: 16px; padding: 1.5rem;
    border: 1px solid rgba(233, 69, 96, 0.1); height: 100%;
}
.stButton>button {
    background: linear-gradient(90deg, #e94560, #ff6b6b) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    padding: 0.75rem 2rem !important; font-weight: 600 !important; font-size: 0.95rem !important;
    width: 100% !important;
}
.lesson-card {
    background: linear-gradient(145deg, #16213e, #1a1a2e);
    border-left: 4px solid #e94560; border-radius: 0 14px 14px 0;
    padding: 1.5rem; margin: 1rem 0;
}
.lesson-card.free { border-left-color: #4ade80; }
.song-card {
    background: linear-gradient(145deg, #16213e, #0f3460);
    border-radius: 14px; padding: 1.25rem;
    border: 1px solid rgba(15, 52, 96, 0.5); height: 100%;
}
.badge {
    display: inline-block; padding: 0.2rem 0.6rem; border-radius: 6px;
    font-size: 0.75rem; font-weight: 600; margin-right: 0.4rem;
}
.badge-beginner { background: rgba(74, 222, 128, 0.15); color: #4ade80; }
.badge-intermediate { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }
.badge-advanced { background: rgba(233, 69, 96, 0.15); color: #e94560; }
.badge-rock { background: rgba(139, 92, 246, 0.15); color: #a78bfa; }
.badge-pop { background: rgba(236, 72, 153, 0.15); color: #f472b6; }
.badge-folk { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.sgt-speech {
    background: #16213e; border: 1px solid rgba(233,69,96,.4);
    border-left: 4px solid #e94560; border-radius: 0 12px 12px 0;
    padding: 1rem 1.25rem; margin: 0.75rem 0; color: #f0f0f5; font-size: 1.02rem;
}
.sgt-speech b { color: #e94560; }
.sgt-name {
    text-align: center; color: #e94560; font-weight: 700;
    letter-spacing: 1px; margin: 0.4rem 0 0; font-size: 0.95rem;
}
.sgt-rank { text-align: center; color: #a0a0a0; font-size: 0.8rem; margin-bottom: 0.5rem; }
.fretboard-container { margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Chord diagrams (static SVG renderer)
# ----------------------------------------------------------------------------
def generate_fretboard_svg(highlight_notes, title=None, fret_spacing=40,
                           string_spacing=20, highlight_color="#e94560"):
    """Render a small static chord diagram. highlight_notes: list of dicts
    with keys string (0=high e .. 5=low E), fret, note, finger. fret=-1 muted."""
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
        return (f'<div class="fretboard-container"><p style="color:#e94560;font-weight:600;'
                f'margin-bottom:0.5rem;font-size:1.1rem;">{title}</p>{svg}</div>')
    return f'<div class="fretboard-container">{svg}</div>'


CHORD_SHAPES = {
    "C Major": {"svg_notes": [
        {"string": 0, "fret": 0, "note": "E"},
        {"string": 1, "fret": 1, "note": "C", "finger": "1"},
        {"string": 2, "fret": 0, "note": "G"},
        {"string": 3, "fret": 2, "note": "E", "finger": "2"},
        {"string": 4, "fret": 3, "note": "C", "finger": "3"},
        {"string": 5, "fret": -1, "note": "X"}]},
    "G Major": {"svg_notes": [
        {"string": 0, "fret": 3, "note": "G", "finger": "4"},
        {"string": 1, "fret": 0, "note": "B"},
        {"string": 2, "fret": 0, "note": "G"},
        {"string": 3, "fret": 0, "note": "D"},
        {"string": 4, "fret": 2, "note": "B", "finger": "2"},
        {"string": 5, "fret": 3, "note": "G", "finger": "3"}]},
    "D Major": {"svg_notes": [
        {"string": 0, "fret": 2, "note": "F#", "finger": "2"},
        {"string": 1, "fret": 3, "note": "D", "finger": "3"},
        {"string": 2, "fret": 2, "note": "A", "finger": "1"},
        {"string": 3, "fret": 0, "note": "D"},
        {"string": 4, "fret": -1, "note": "X"},
        {"string": 5, "fret": -1, "note": "X"}]},
    "A Major": {"svg_notes": [
        {"string": 0, "fret": 0, "note": "E"},
        {"string": 1, "fret": 2, "note": "C#", "finger": "2"},
        {"string": 2, "fret": 2, "note": "A", "finger": "3"},
        {"string": 3, "fret": 2, "note": "E", "finger": "1"},
        {"string": 4, "fret": 0, "note": "A"},
        {"string": 5, "fret": -1, "note": "X"}]},
    "E Major": {"svg_notes": [
        {"string": 0, "fret": 0, "note": "E"},
        {"string": 1, "fret": 0, "note": "B"},
        {"string": 2, "fret": 1, "note": "G#", "finger": "1"},
        {"string": 3, "fret": 2, "note": "E", "finger": "2"},
        {"string": 4, "fret": 2, "note": "B", "finger": "3"},
        {"string": 5, "fret": 0, "note": "E"}]},
    "A Minor": {"svg_notes": [
        {"string": 0, "fret": 0, "note": "E"},
        {"string": 1, "fret": 1, "note": "C", "finger": "1"},
        {"string": 2, "fret": 2, "note": "A", "finger": "2"},
        {"string": 3, "fret": 2, "note": "E", "finger": "3"},
        {"string": 4, "fret": 0, "note": "A"},
        {"string": 5, "fret": -1, "note": "X"}]},
    "E Minor": {"svg_notes": [
        {"string": 0, "fret": 0, "note": "E"},
        {"string": 1, "fret": 0, "note": "B"},
        {"string": 2, "fret": 0, "note": "G"},
        {"string": 3, "fret": 2, "note": "E", "finger": "2"},
        {"string": 4, "fret": 2, "note": "B", "finger": "3"},
        {"string": 5, "fret": 0, "note": "E"}]},
}

# ----------------------------------------------------------------------------
# Sgt. Martin — instructor engine
# ----------------------------------------------------------------------------
def _secret(name):
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def sgt_speak(text):
    """Speak text in Sgt. Martin's voice via ElevenLabs (if configured).
    Returns audio bytes or None. Results are cached per text."""
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
            timeout=30,
        )
        r.raise_for_status()
        cache[text] = r.content
        return r.content
    except Exception:
        return None


def sgt_panel(state="idle", message=None, voice_text=None):
    """Render the instructor panel in the sidebar.
    state: idle | talking | praise. message: speech-bubble text (HTML allowed).
    voice_text: if given and ElevenLabs is configured, plays it in his voice."""
    clip = SGT.get(state, SGT["idle"])
    with st.sidebar:
        if os.path.exists(clip):
            st.video(clip)
        elif os.path.exists(SGT["portrait"]):
            st.image(SGT["portrait"])
        st.markdown('<p class="sgt-name">SGT. MARTIN</p>', unsafe_allow_html=True)
        st.markdown('<p class="sgt-rank">GUITAR INSTRUCTOR · SIX-STRING BOOTCAMP</p>',
                    unsafe_allow_html=True)
        if message:
            st.markdown(f'<div class="sgt-speech">{message}</div>', unsafe_allow_html=True)
        if voice_text:
            audio = sgt_speak(voice_text)
            if audio:
                st.audio(audio, format="audio/mp3")


def sgt_intro():
    """First-visit intro: solo, speech, enlist. Returns True once enlisted."""
    if st.session_state.get("enlisted"):
        return True
    st.markdown('<div class="main-header"><h1>🎸 SIX-STRING BOOTCAMP</h1>'
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
        else:
            sgt_voice = sgt_speak(
                "Listen up, recruit! I'm Sergeant Martin, and this is Six String Bootcamp. "
                "Twelve courses stand between you and the guitarist you were born to be. "
                "Tune up, stretch those fingers, and report to the fretboard!")
            if sgt_voice:
                st.audio(sgt_voice, format="audio/mp3")
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
  <div style="margin-top:10px;display:flex;gap:8px;justify-content:center;">
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
    const x1=c[T0-1],x2=c[T0],x3=c[T0+1], a=(x1+x3-2*x2)/2, b2c=(x3-x1)/2;
    if(a) T0=T0-b2c/(2*a);
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
        with open("fretboard.html", encoding="utf-8") as f:
            components.html(f.read(), height=620, scrolling=False)
    except FileNotFoundError:
        st.warning("fretboard.html not found next to app.py — add it to enable the Fretboard Lab.")


# ----------------------------------------------------------------------------
# App
# ----------------------------------------------------------------------------
if not sgt_intro():
    st.stop()

sgt_panel("idle", "<b>Sgt. Martin</b> is on duty. Pick a section, recruit.")

st.markdown('<div class="main-header"><h1>🎸 SIX-STRING BOOTCAMP</h1>'
            '<p>Interactive guitar training · AI instructor · free tools</p></div>',
            unsafe_allow_html=True)

tab_board, tab_chords, tab_songs, tab_tools = st.tabs(
    ["🎸 Fretboard Lab", "📚 Chord Library", "🎵 Song Search", "🧰 Tools"])

with tab_board:
    sgt_panel("talking",
              "<b>Listen up!</b> Tap any string on the fretboard — the note lights up "
              "and sounds. Greenhorns start with the chord buttons below the board.")
    fretboard_lab()

with tab_chords:
    sgt_panel("talking",
              "<b>Chord wall, recruit.</b> Seven essential shapes. Drill one until "
              "your fingers stop complaining — then hit <b>Nailed it!</b>")
    cols = st.columns(3)
    for i, (name, chord) in enumerate(CHORD_SHAPES.items()):
        with cols[i % 3]:
            st.markdown(generate_fretboard_svg(chord["svg_notes"], title=name),
                        unsafe_allow_html=True)
    if st.button("🎖️ NAILED IT!"):
        sgt_panel("praise", "<b>Outstanding!</b> Clean changes, no buzz. "
                             "That's how a guitarist is made.")
        st.balloons()

with tab_songs:
    sgt_panel("talking",
              "<b>Song library.</b> The full internet search lives on the "
              "<b>Song Search</b> page in the sidebar — type any song, get its "
              "guitar tracks, tuning, and the interactive tab.")
    st.info("Open **Song Search** in the sidebar (pages/song_search.py) for the live "
            "Songsterr-powered library.")

with tab_tools:
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

st.markdown("---")
st.caption("Six-String Bootcamp · Sgt. Martin reporting · Practice daily, recruit.")
