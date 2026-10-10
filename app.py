"""Six-String Bootcamp — interactive guitar training app.

Run:  python -m streamlit run app.py
Local data: saved_songs.json, gigs.json (created next to this file)
Secrets (.streamlit/secrets.toml, never commit):
    ELEVENLABS_API_KEY = "..."   # optional — Sgt. Martin's live voice
    ELEVENLABS_VOICE_ID = "..."  # optional — your chosen ElevenLabs voice
    github_token = "..."  # community wall write access (fine-grained PAT, Contents: read+write)
"""
import os
import re
import json
import base64
import time
import uuid
import html as htmlmod
from urllib.parse import quote_plus

import streamlit as st
import streamlit.components.v1 as components

try:
    import requests
except ImportError:
    requests = None

st.set_page_config(
    page_title="Six-String Bootcamp",
    page_icon="assets/app-icon.png",
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
/* Compact sticky section nav: one short pill row, pinned to the top on phones
   so sections are always one tap away and content starts on the same screen. */
div[data-testid="stPills"] {
    position: sticky; top: 0; z-index: 999;
    background: #0e1117; padding: 6px 0; margin: 0 -1rem;
}
div[data-testid="stPills"] button { white-space: nowrap; }
/* Phones: shrink section banners so the header + first content share one screen. */
@media (max-width: 768px) {
    .hero { padding: 0.9rem 0.5rem; margin-bottom: 0.8rem; border-radius: 14px; }
    .hero h1 { font-size: 1.55rem; }
    .hero p { font-size: 0.9rem; margin-top: 0.25rem; }
}
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


CHORD_RE = re.compile(
    r"^[A-G][#b]?(?:m(?!aj)|maj|min|dim|aug|sus[24]?|add\d*|\d+)*(?:/[A-G][#b]?)?$",
    re.IGNORECASE)


def is_chord_line(line):
    """A line is a chord line if every token looks like a chord symbol."""
    s = line.strip()
    if not s:
        return False
    if any(c in s for c in ",.!?;:\"'()"):
        return False
    toks = s.split()
    return bool(toks) and all(CHORD_RE.match(tok) for tok in toks)


def convert_chord_sheet(text):
    """Turn a chords-over-lyrics paste (or inline [Am] text) into [C] inline format.

    Standard chord-site layout:
        G               C                 D
        Amazing grace, how sweet the sound
    becomes:
        [G]Amazing [C]grace, how [D]sweet the sound
    """
    if re.search(r"\[[A-G][#b]?(?:m|7|maj|min|sus|add|dim|aug)", text):
        return text.strip()  # already inline format
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if is_chord_line(line) and nxt.strip() and not is_chord_line(nxt):
            lyric = nxt.rstrip("\n")
            inserts = []
            for m in re.finditer(r"\S+", line):
                pos = min(m.start(), len(lyric))
                inserts.append((pos, f"[{m.group(0)}]"))
            for pos, tag in sorted(inserts, reverse=True):
                lyric = lyric[:pos] + tag + lyric[pos:]
            out.append(lyric)
            i += 2
        elif is_chord_line(line):
            out.append(" ".join(f"[{tok}]" for tok in line.split()))
            i += 1
        else:
            out.append(line)
            i += 1
    return "\n".join(out).strip()


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
    ("Your First Song", 29, "Every Rose Has Its Thorn — G, C, D, Em. A real song in lesson one. Show someone tonight."),
    ("Tuning, Fretboard & Ears", 29, "Tune by ear, map the fretboard, learn octaves, train your ears with the voice-matching drill."),
    ("Finger Exercises + Pentatonic Position 1", 29, "The 1-2-3-4 drill, then your first pentatonic box."),
    ("Three-Chord Songbook + Position 2", 29, "More songs in the pocket, second pentatonic position."),
    ("Strumming That Sings + Position 3", 29, "Patterns that make it sound like the record."),
    ("The A Family & Minor Chords + Position 4", 29, "Sad songs, more colors, fourth box."),
    ("Clean Chord Changes + Position 5", 29, "Kill the pause. All five boxes on the board."),
    ("Power Chords + Connecting the Boxes", 39, "Rock rhythm and your first real improv."),
    ("Barre Chords: E-Shape", 39, "One shape, twelve chords. The fretboard opens up."),
    ("Barre Chords: A-Shape", 39, "The second barre family — full fretboard freedom."),
    ("Soloing With Purpose", 39, "Phrasing and intent across all five positions."),
    ("Music Theory + Your First 10 Songs", 49, "Sharps/flats, majors/minors, chromatic scale, circle of fifths, capo — then the capstone setlist."),
]
MEMBERSHIP = [
    ("Monthly", 19, "All 12 courses, new lessons weekly, cancel anytime."),
    ("Annual", 149, "Everything in Monthly, two months free, priority Q&A."),
    ("Lifetime", 399, "Pay once. Every course, every future update, forever."),
]

# ----------------------------------------------------------------------------
# Lesson notes — Erik's own teaching, dictated Oct 2026. Shown as previews.
# ----------------------------------------------------------------------------
LESSON_CONTENT = {
    1: [
        ("Welcome to Six String Bootcamp",
         "Before we go any further, I want to congratulate you and encourage you \u2014 and I want "
         "you to see some things I've set up that might catch your attention.\n\n"
         "I've got badges for you. When you pass these practice lessons, you get a badge, and it'll "
         "display automatically on your Six String Bootcamp social media \u2014 live, visible for "
         "everyone to see your progress.\n\n"
         "And this is not your normal social media site. This is for my students. Once you enroll, "
         "you're automatically a member. You get to choose whether your stuff is public or private "
         "\u2014 hopefully public \u2014 so everyone can see your badges. You can communicate with "
         "other students, see how they're enjoying learning guitar, share stuff, help each other out.\n\n"
         "And once you pass the practices, we give you an NFT. If you're not familiar with blockchain "
         "or cryptocurrency \u2014 an NFT is a special way to catalog your experience and your "
         "achievements. In my opinion, it becomes a piece of art on the blockchain.\n\n"
         "So welcome to the new world \u2014 with me, you, and AI. We can get a lot accomplished. "
         "And hopefully, you'll become a master guitarist."),
        ("How you'll be graded",
         "As you go through Six String Bootcamp, you'll be doing practices, and my AI instructor is "
         "going to grade you. Here's what it's grading: are you chording properly? Is every finger "
         "pressing every string it's supposed to press \u2014 and is every string sounding the way "
         "it's supposed to sound?\n\n"
         "Take the E minor I just taught you. Two fingers touching two strings \u2014 but all six "
         "strings ring. That's what we're looking for.\n\n"
         "And listen: we don't want you playing hard. Don't hit the strings. Just press the two "
         "strings. Keep your palm and your wrist completely away from the fretboard \u2014 not "
         "touching any other string. Start from the sixth string on top and strum straight down. We "
         "should hear every string ring open except the two you pressed. That's what you'll be graded "
         "on \u2014 and that's what's going to move you to the next lesson.\n\n"
         "When you come back for the next lesson, you'll go to the practice window. You'll practice "
         "what you learned \u2014 or whatever the AI tells you to. You don't have to run the whole "
         "session. Just the hot spots, so we can see you are indeed practicing, and you are indeed "
         "getting it."),
        ("Grabbing the chord",
         "You've seen it on TV, maybe in person \u2014 guitar players twisting around, moving their "
         "body, ducking their head. A lot of that is not for show. You have to move your wrist, move "
         "your elbow \u2014 stick it out, tuck it in \u2014 hump your back, move your head, move "
         "your other arm. I call it grabbing the chord.\n\n"
         "Here's why: to fret a chord clean, you have to touch every string you're supposed to touch, "
         "and nothing you're not supposed to. If your palm hits a string, it'll muffle it or make it "
         "ring wrong. So you move your body around until your fingers can land properly \u2014 and "
         "by properly, I mean the tip of your finger, exactly on the string. Not the whole finger. "
         "The tip. And press hard.\n\n"
         "It's going to hurt at first. It's going to feel like the worst thing in the world. That's "
         "normal.\n\n"
         "As a beginner, you are not supposed to know how to make these chords yet. Your brain and "
         "your fingers have never done this in your life. It takes a while to build that brain-hand "
         "coordination. So don't be discouraged when you can't chord something I teach you. Just do "
         "what I'm telling you, keep practicing, and it'll come together. I promise \u2014 but you "
         "have to get through the pain. It takes a lot of practice to play guitar.\n\n"
         "I wish I could take my brain, pluck it out, and hand it to you so it would just work. I've "
         "been playing 40 years and I'm still learning. I'm not a master \u2014 I'm someone who "
         "wants to share what I've learned. And I know these are the proper fundamentals, because "
         "I've studied it, researched it, and put it to bed. This is the fundamentals. Do what I say, "
         "and you will get it, and you will be able to play.\n\n"
         "So practice, practice, practice."),
    ],
    2: [
        ("Things you'll hear a lot",
         "Before we play a note, let's get our words straight \u2014 because you're going to hear "
         "these every single lesson.\n\n"
         "The guitar has frets, fingers, a nut, a bridge, a headstock, and tuning knobs. The nut is "
         "at the top \u2014 that's where the fretboard starts. The bridge is at the bottom \u2014 "
         "that's where the strings come to an end. The headstock is the head of the guitar, and "
         "that's where the tuning knobs live.\n\n"
         "Now the strings. We count from the bottom up. String one is the high E \u2014 the "
         "skinniest string, closest to the floor. String two is B, string three is G, string four is "
         "D, string five is A, and string six at the very top is the low E \u2014 the fattest one. "
         "Notice something? The first and the sixth string are both E when you play them open. Same "
         "note, different octave. Remember that \u2014 it matters later.\n\n"
         "Frets start at the top near the nut. This fret is one, then two, three, four, five, six, "
         "seven, eight, nine, ten, eleven, twelve \u2014 and so on down the neck.\n\n"
         "Your hand: you've got your pointer finger \u2014 that's your first finger \u2014 your "
         "bird finger, your ring finger, your pinky, and your thumb. So when I say \u201cpointer on "
         "the fifth string, second fret,\u201d you know exactly what I mean.\n\n"
         "Let's prove it. Pointer \u2014 first finger \u2014 on the fifth string, second fret. "
         "Bird finger on the fourth string, second fret. Strum it. That's an E minor open chord. You "
         "just played your first chord."),
        ("Where your fingers actually go",
         "One thing to focus on right from the start: finger placement.\n\n"
         "I mentioned frets. Look at the guitar neck \u2014 you'll see metal bars. Those are the "
         "fret bars. What's in between them is the actual fret \u2014 the space.\n\n"
         "So if I say \u201cpointer finger and bird finger, on strings five and four, in fret "
         "two\u201d \u2014 your fingers go inside of fret two. Not on the fret bar, not to the "
         "left or right of it \u2014 in the middle, in between the two bars. The first fret is the "
         "space right beside the nut. The next space over is the second fret \u2014 that space "
         "between the first two fret bars. That's where your fingers go.\n\n"
         "Anytime I tell you to place a finger somewhere, even if it seems awkward \u2014 and it "
         "will, I promise you \u2014 it has to go there. Fix your body, fix your hands, and make "
         "those fingers go into that position."),
    ],
    3: [
        ("The 1-2-3-4 exercise",
         "While we're on the frets, here's the finger exercise I want you to learn.\n\n"
         "You've got four fingers. Place all four on any four frets \u2014 we're starting on the "
         "sixth string. That's your exercise. Take the tips of your fingers and go one, two, three, "
         "four \u2014 then back: four, three, two, one. One finger per fret, pressing each one "
         "clean.\n\n"
         "Wherever you start, that's your one through four. Fret one, fret five, fret ten \u2014 "
         "doesn't matter. Say you start on the tenth fret: tenth is your one, eleventh is your two, "
         "twelfth is your three, thirteenth is your four. Then back: thirteen, twelve, eleven, ten. "
         "Down and back, down and back.\n\n"
         "Once you can run the sixth string fluently \u2014 one-two-three-four, four-three-two-one, "
         "over and over \u2014 then when you feel comfortable, like you're getting it: go one, two, "
         "three, four, and drop down to the fifth string. One, two, three, four. And so on, string by "
         "string."),
        ("When you're ready",
         "While you're doing these exercises \u2014 and doing them right \u2014 take as much time "
         "as you need. You don't have to go fast. Just one, two, three, four, four, three, two, one. "
         "And before you know it, you'll be blazing through it.\n\n"
         "Here's your benchmark: sixth string, one-two-three-four, all the way down to the first "
         "string, one-two-three-four \u2014 then back up to the sixth string, four-three-two-one on "
         "every string. Once you're at that level \u2014 and it should come pretty quick if you're "
         "practicing \u2014 then we get to go above and beyond.\n\n"
         "We're going to have some fun with the pentatonic scale."),
    ],
}

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
    """Inline instructor tip — no portrait (Sgt. Martin lives in his bubble).
    Honors the instructor toggle."""
    if not st.session_state.get("instructor_on", True):
        return
    st.markdown(f'<div class="sgt-speech">{message}</div>', unsafe_allow_html=True)
    if voice_text:
        audio = sgt_speak(voice_text)
        if audio:
            st.audio(audio, format="audio/mp3")

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

_TUNER_STRINGS = [["E", 82.41], ["A", 110.00], ["D", 146.83],
                  ["G", 196.00], ["B", 246.94], ["e", 329.63]]
_TUNER_THICK = [5, 4.5, 4, 3, 2.2, 1.6]


def _tuner_html(p):
    """String-by-string tuner panel. Tap a string to hear its reference pitch;
    the mic grades it: green + check when in tune, red + arrows otherwise."""
    rows = []
    for i, (nm, fr) in enumerate(_TUNER_STRINGS):
        rows.append(
            f'<div class="{p}-srow" data-i="{i}" style="display:flex;align-items:center;gap:10px;'
            f'padding:7px 10px;border-radius:10px;cursor:pointer;border:2px solid transparent;">'
            f'<span style="width:22px;font-weight:800;color:#fff;font-size:15px;">{nm}</span>'
            f'<div style="flex:1;height:{_TUNER_THICK[i]}px;background:#3a3a52;border-radius:3px;"></div>'
            f'<span style="color:#8a8a9e;font-size:11px;">{fr:.2f} Hz</span></div>'
        )
    return (
        '<div style="text-align:center;padding:10px 6px;">'
        '<div style="font-size:12px;color:#8a8a9e;margin-bottom:6px;">tap a string to hear its pitch</div>'
        + "".join(rows) +
        f'<div id="{p}Note" style="font-size:2.6rem;font-weight:800;color:#e94560;margin-top:8px;">&ndash;</div>'
        f'<div id="{p}Status" style="font-size:1.05rem;font-weight:800;min-height:1.5em;"></div>'
        f'<div id="{p}Cents" style="color:#a0a0a0;font-size:12px;margin-bottom:6px;min-height:1.2em;">select a string, then press START</div>'
        f'<div style="width:92%;height:10px;background:#16213e;border-radius:6px;margin:0 auto;position:relative;overflow:hidden;">'
        f'<div id="{p}Needle" style="position:absolute;top:0;bottom:0;left:50%;width:4px;background:#e94560;border-radius:2px;"></div></div>'
        f'<div style="margin-top:10px;display:flex;gap:10px;justify-content:center;align-items:center;">'
        f'<button id="{p}Btn" style="background:#e94560;color:#fff;border:none;border-radius:10px;padding:10px 26px;font-size:1rem;font-weight:700;cursor:pointer;">START</button>'
        f'<label style="color:#8a8a9e;font-size:12px;cursor:pointer;"><input type="checkbox" id="{p}Auto" checked style="vertical-align:middle;"> auto-advance</label>'
        f'</div>'
        f'<div style="color:#5a5a72;font-size:11px;margin-top:8px;">needs microphone access</div>'
        f'</div>'
    )


def _tuner_js(p, S, DOC, WIN, RAF, NAV, declare):
    """JS for the string tuner. p: id prefix. S: JS expr for the state object.
    DOC/WIN/RAF/NAV: JS exprs for document/window/rAF/navigator in this context."""
    js = r'''
DECLARE
(function(){
try{
var NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
var STR=[["E",82.41],["A",110.00],["D",146.83],["G",196.00],["B",246.94],["e",329.63]];
var nEl=__DOC__.getElementById('__P__Note'),sEl=__DOC__.getElementById('__P__Status'),
    cEl=__DOC__.getElementById('__P__Cents'),ndl=__DOC__.getElementById('__P__Needle'),
    btn=__DOC__.getElementById('__P__Btn'),auto=__DOC__.getElementById('__P__Auto');
var rows=__DOC__.querySelectorAll('.__P__-srow');
function acor(buf,sr){
  var SIZE=buf.length,rms=0,i;
  for(i=0;i<SIZE;i++)rms+=buf[i]*buf[i];
  if(Math.sqrt(rms/SIZE)<0.01)return -1;
  var r1=0,r2=SIZE-1,b=buf.slice(0);
  for(i=0;i<SIZE/2;i++)if(Math.abs(b[i])<0.2){b[i]=0;r1=i;}
  for(i=1;i<SIZE/2;i++)if(Math.abs(b[SIZE-i])<0.2){b[SIZE-i]=0;r2=SIZE-i;}
  var b2=b.slice(r1,r2);SIZE=b2.length;
  var c=new Array(SIZE).fill(0);
  for(i=0;i<SIZE;i++)for(var j=0;j<SIZE-i;j++)c[i]+=b2[j]*b2[j+i];
  var dd=0;while(dd<SIZE-1&&c[dd]>c[dd+1])dd++;
  var maxv=-1,maxp=-1;
  for(i=dd;i<SIZE;i++)if(c[i]>maxv){maxv=c[i];maxp=i;}
  var T0=maxp;
  if(T0>0&&T0<SIZE-1){
    var x1=c[T0-1],x2=c[T0],x3=c[T0+1],aa=(x1+x3-2*x2)/2,bb=(x3-x1)/2;
    if(aa)T0=T0-bb/(2*aa);
  }
  return sr/T0;
}
function paintRow(){
  rows.forEach(function(r){r.style.borderColor='transparent';r.style.background='transparent';});
  var r=rows[__S__.sel];
  if(r)r.style.background='#1f1f33';
}
function playRef(i){
  try{
    var AC=__WIN__.AudioContext||__WIN__.webkitAudioContext;
    __S__.refCtx=__S__.refCtx||new AC();
    var ctx=__S__.refCtx;
    if(ctx.resume)ctx.resume();
    var o=ctx.createOscillator(),g=ctx.createGain();
    o.type='triangle';o.frequency.value=STR[i][1];
    var t=ctx.currentTime;
    g.gain.setValueAtTime(0.0001,t);
    g.gain.exponentialRampToValueAtTime(0.5,t+0.02);
    g.gain.exponentialRampToValueAtTime(0.0001,t+1.4);
    o.connect(g);g.connect(ctx.destination);
    o.start(t);o.stop(t+1.5);
  }catch(e){}
}
function sel(i,silent){
  __S__.sel=i;__S__.okSince=0;
  paintRow();
  if(!silent)playRef(i);
  cEl.textContent='now tune the '+STR[i][0]+' string';
}
function tick(){
  if(!__S__.running||!__S__.an)return;
  __S__.an.getFloatTimeDomainData(__S__.buf);
  var f=acor(__S__.buf,__S__.ctx.sampleRate);
  var target=STR[__S__.sel][1];
  if(f>40&&f<1200){
    var cents=Math.round(1200*Math.log2(f/target));
    var nn=Math.round(12*Math.log2(f/440))+69;
    nEl.textContent=NAMES[nn%12];
    ndl.style.left=(50+Math.max(-50,Math.min(50,cents)))+'%';
    var r=rows[__S__.sel];
    if(Math.abs(cents)<=6){
      nEl.style.color='#4ade80';ndl.style.background='#4ade80';
      sEl.textContent='\u2713 IN TUNE';sEl.style.color='#4ade80';
      cEl.textContent=STR[__S__.sel][0]+' string \u00b7 '+cents+'\u00a2';
      if(r)r.style.borderColor='#4ade80';
      var now=Date.now();
      if(!__S__.okSince)__S__.okSince=now;
      if(auto.checked&&now-__S__.okSince>1200&&__S__.sel<5){sel(__S__.sel+1);}
    }else{
      __S__.okSince=0;
      nEl.style.color='#e94560';ndl.style.background='#e94560';
      var up=cents<0;
      sEl.textContent=up?'\u2191 TUNE UP':'\u2193 TUNE DOWN';
      sEl.style.color='#e94560';
      cEl.textContent=STR[__S__.sel][0]+' string \u00b7 '+(cents>0?'+':'')+cents+'\u00a2 '+(up?'(tighten the peg)':'(loosen the peg)');
      if(r)r.style.borderColor='#e94560';
    }
  }else{
    __S__.okSince=0;
    nEl.textContent='\u2013';sEl.textContent='';
    cEl.textContent='listening\u2026 play the '+STR[__S__.sel][0]+' string';
  }
  __RAF__(tick);
}
btn.onclick=async function(){
  if(__S__.running){
    __S__.running=false;
    if(__S__.stream)__S__.stream.getTracks().forEach(function(t){t.stop();});
    if(__S__.ctx)__S__.ctx.close();
    __S__.stream=null;__S__.ctx=null;__S__.an=null;__S__.okSince=0;
    btn.textContent='START';btn.style.background='#e94560';
    sEl.textContent='';
    cEl.textContent='select a string, then press START';
    paintRow();
    return;
  }
  try{
    __S__.stream=await __NAV__.mediaDevices.getUserMedia({audio:true});
    __S__.ctx=new (__WIN__.AudioContext||__WIN__.webkitAudioContext)();
    var src=__S__.ctx.createMediaStreamSource(__S__.stream);
    __S__.an=__S__.ctx.createAnalyser();
    __S__.an.fftSize=2048;src.connect(__S__.an);
    __S__.buf=new Float32Array(__S__.an.fftSize);
    __S__.running=true;__S__.okSince=0;
    btn.textContent='STOP';btn.style.background='#4ade80';
    __RAF__(tick);
  }catch(e){cEl.textContent='microphone blocked \u2014 allow access and retry';}
};
rows.forEach(function(r){
  r.onclick=function(){sel(parseInt(r.getAttribute('data-i'),10));};
});
sel(0,true);
}catch(e){}
})();
'''
    return (js.replace("DECLARE", declare)
              .replace("__P__", p).replace("__S__", S)
              .replace("__DOC__", DOC).replace("__WIN__", WIN)
              .replace("__RAF__", RAF).replace("__NAV__", NAV))


TUNER_HTML = (
    _tuner_html("t")
    + "<script>"
    + _tuner_js("t", "TSTATE", "document", "window",
                "requestAnimationFrame", "navigator",
                "var TSTATE={running:false,sel:0,stream:null,ctx:null,an:null,"
                "buf:null,okSince:0,refCtx:null};")
    + "</script>"
)



EAR_TRAINER_HTML = """
<div style="text-align:center;padding:8px;">
  <div style="color:#a0a0a0;font-size:0.9rem;margin-bottom:6px;">Hear it &nbsp;&rarr;&nbsp; sing it back &nbsp;&rarr;&nbsp; get scored</div>
  <div id="eTarget" style="font-size:2.4rem;font-weight:700;color:#e94560;">&ndash;</div>
  <div id="eHeard" style="font-size:1.05rem;color:#a0a0a0;min-height:1.7em;">press PLAY NOTE, then sing</div>
  <div id="eVerdict" style="font-size:1.35rem;font-weight:700;min-height:1.9em;"></div>
  <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:4px;">
    <button id="ePlay" style="background:#e94560;color:#fff;border:none;border-radius:10px;padding:10px 18px;font-size:0.95rem;font-weight:700;cursor:pointer;">&#9654; PLAY NOTE</button>
    <button id="eRetry" style="background:#16213e;color:#f0f0f5;border:1px solid rgba(233,69,96,.4);border-radius:10px;padding:10px 18px;font-size:0.95rem;font-weight:700;cursor:pointer;">&#128260; TRY AGAIN</button>
    <button id="eNew" style="background:#16213e;color:#f0f0f5;border:1px solid rgba(233,69,96,.4);border-radius:10px;padding:10px 18px;font-size:0.95rem;font-weight:700;cursor:pointer;">&#127922; NEW NOTE</button>
    <button id="eMic" style="background:#16213e;color:#f0f0f5;border:1px solid rgba(233,69,96,.4);border-radius:10px;padding:10px 18px;font-size:0.95rem;font-weight:700;cursor:pointer;">&#127908; MIC: OFF</button>
  </div>
  <div id="eAtt" style="color:#5a5a72;font-size:0.85rem;margin-top:8px;">attempt 1</div>
  <div id="eStats" style="color:#5a5a72;font-size:0.85rem;margin-top:8px;">rounds: 0 &middot; nailed: 0</div>
  <div style="color:#5a5a72;font-size:0.78rem;margin-top:4px;">needs microphone access &middot; works on localhost / HTTPS</div>
</div>
<script>
const ENOTES=[["A3",220.00],["C4",261.63],["D4",293.66],["E4",329.63],["G4",392.00],["A4",440.00]];
let eTarget=null, eMicOn=false, eRounds=0, eNailed=0, eScored=false, eStream=null, eCtx=null, eAttempt=1;
const eT=document.getElementById('eTarget'), eH=document.getElementById('eHeard'),
      eV=document.getElementById('eVerdict'), eS=document.getElementById('eStats'),
      eA=document.getElementById('eAtt');
function eAutoCorrelate(buf,sr){
  let SIZE=buf.length, rms=0, i;
  for(i=0;i<SIZE;i++) rms+=buf[i]*buf[i];
  if(Math.sqrt(rms/SIZE)<0.015) return -1;
  let r1=0, r2=SIZE-1;
  const b=buf.slice(0);
  for(i=0;i<SIZE/2;i++) if(Math.abs(b[i])<0.2){b[i]=0;r1=i;}
  for(i=1;i<SIZE/2;i++) if(Math.abs(b[SIZE-i])<0.2){b[SIZE-i]=0;r2=SIZE-i;}
  const b2=b.slice(r1,r2); SIZE=b2.length;
  const c=new Array(SIZE).fill(0);
  for(i=0;i<SIZE;i++) for(let j=0;j<SIZE-i;j++) c[i]+=b2[j]*b2[j+i];
  let d=0; while(d<SIZE-1 && c[d]>c[d+1]) d++;
  let maxv=-1, maxp=-1;
  for(i=d;i<SIZE;i++) if(c[i]>maxv){maxv=c[i];maxp=i;}
  let T0=maxp;
  if(T0>0&&T0<SIZE-1){
    const x1=c[T0-1],x2=c[T0],x3=c[T0+1],aa=(x1+x3-2*x2)/2,bb=(x3-x1)/2;
    if(aa) T0=T0-bb/(2*aa);
  }
  return sr/T0;
}
function ePick(){
  eTarget=ENOTES[Math.floor(Math.random()*ENOTES.length)];
  eScored=false;
  eAttempt=1; eA.textContent='attempt 1';
  eT.textContent=eTarget[0];
  eV.textContent=''; eV.style.color='';
  eH.textContent='sing it back\u2026';
}
document.getElementById('eNew').addEventListener('click', ePick);
function ePlayNote(){
  if(!eTarget) ePick();
  try{
    const AC=window.AudioContext||window.webkitAudioContext;
    const ctx=new AC(), o=ctx.createOscillator(), g=ctx.createGain();
    o.type='sine'; o.frequency.value=eTarget[1];
    const tm=ctx.currentTime;
    g.gain.setValueAtTime(0.0001,tm);
    g.gain.exponentialRampToValueAtTime(0.5,tm+0.05);
    g.gain.exponentialRampToValueAtTime(0.0001,tm+1.4);
    o.connect(g); g.connect(ctx.destination);
    o.start(tm); o.stop(tm+1.5);
    eH.textContent=eMicOn?'listen\u2026 now sing it back':'\u2026 then tap MIC so I can grade you';
  }catch(err){ eH.textContent='audio blocked by browser'; }
}
document.getElementById('ePlay').addEventListener('click', ePlayNote);
document.getElementById('eRetry').addEventListener('click', ()=>{
  eAttempt++;
  eA.textContent='attempt '+eAttempt;
  eV.textContent=''; eV.style.color='';
  eScored=false;
  ePlayNote();
});
document.getElementById('eMic').addEventListener('click', async (ev)=>{
  const btn=ev.currentTarget;
  if(eMicOn){ eMicOn=false; btn.innerHTML='&#127908; MIC: OFF'; btn.style.background='#16213e'; btn.style.color='#f0f0f5';
    if(eStream){eStream.getTracks().forEach(x=>x.stop());} return; }
  try{
    eStream=await navigator.mediaDevices.getUserMedia({audio:true});
    eCtx=new (window.AudioContext||window.webkitAudioContext)();
    const src=eCtx.createMediaStreamSource(eStream), an=eCtx.createAnalyser();
    an.fftSize=2048; src.connect(an);
    const buf=new Float32Array(an.fftSize);
    eMicOn=true; btn.innerHTML='&#127908; MIC: ON'; btn.style.background='#4ade80'; btn.style.color='#0d0d1a';
    if(!eTarget) ePick();
    (function tick(){
      if(!eMicOn) return;
      an.getFloatTimeDomainData(buf);
      const f=eAutoCorrelate(buf,eCtx.sampleRate);
      if(f>60&&f<1000&&eTarget){
        const cents=Math.round(1200*Math.log2(f/eTarget[1]));
        const dir=cents>0?'sharp (too high)':(cents<0?'flat (too low)':'in tune');
        eH.textContent='you: '+Math.round(f)+' Hz \u00b7 '+(cents>0?'+':'')+cents+'\u00a2 '+dir;
        const a=Math.abs(cents);
        if(a<=20){
          eV.textContent='\\uD83C\\uDF96\\uFE0F NAILED IT! (attempt '+eAttempt+')'; eV.style.color='#4ade80';
          if(!eScored){ eScored=true; eRounds++; eNailed++; eS.textContent='rounds: '+eRounds+' \u00b7 nailed: '+eNailed; }
        } else if(a<=50){
          eV.textContent='close \u2014 a touch '+(cents>0?'lower':'higher'); eV.style.color='#fbbf24';
        } else {
          eV.textContent='keep going \u2014 listen again'; eV.style.color='#e94560';
        }
      }
      requestAnimationFrame(tick);
    })();
  }catch(err){ eH.textContent='microphone blocked \u2014 allow access and retry'; }
});
ePick();
</script>
"""


def metronome():
    components.html(METRONOME_HTML, height=300, scrolling=False)


def tuner():
    components.html(TUNER_HTML, height=470, scrolling=False)


# ----------------------------------------------------------------------------
# Practice dialogue — AI check-ins. v1: lessons 1-3 (single-note mic grading).
# ----------------------------------------------------------------------------
PRACTICES = {
    1: {
        "title": "E minor \u2014 string by string",
        "intro": "Two fingers, six strings ringing. Pick each string one at a time, top to bottom. I'm listening.",
        "steps": [
            ("Pick the 6th string, open.", 40),
            ("5th string, 2nd fret \u2014 pointer finger.", 47),
            ("4th string, 2nd fret \u2014 bird finger.", 52),
            ("3rd string, open.", 55),
            ("2nd string, open.", 59),
            ("1st string, open.", 64),
        ],
    },
    2: {
        "title": "Tuning check \u2014 open strings",
        "intro": "If these six aren't right, nothing else will be. Pick each open string, top to bottom.",
        "steps": [
            ("6th string, open.", 40),
            ("5th string, open.", 45),
            ("4th string, open.", 50),
            ("3rd string, open.", 55),
            ("2nd string, open.", 59),
            ("1st string, open.", 64),
        ],
    },
    3: {
        "title": "1-2-3-4 on the 6th string",
        "intro": "Fret five is your one. Tips of your fingers \u2014 go.",
        "steps": [
            ("6th string, 5th fret.", 45),
            ("6th string, 6th fret.", 46),
            ("6th string, 7th fret.", 47),
            ("6th string, 8th fret.", 48),
            ("Back down \u2014 8th fret.", 48),
            ("7th fret.", 47),
            ("6th fret.", 46),
            ("5th fret.", 45),
        ],
    },
}

PRACTICE_HTML = """
<div style="text-align:center;padding:10px;max-width:560px;margin:0 auto;">
  <div style="color:#a0a0a0;font-size:0.9rem;">__INTRO__</div>
  <div id="pStep" style="color:#5a5a72;font-size:0.85rem;margin-top:10px;"></div>
  <div id="pPrompt" style="font-size:1.5rem;font-weight:700;color:#f0f0f5;margin:8px 0;min-height:2.2em;"></div>
  <div id="pHeard" style="font-size:1.05rem;color:#a0a0a0;min-height:1.7em;"></div>
  <div id="pFeed" style="font-size:1.15rem;font-weight:600;min-height:1.8em;margin:4px 0;"></div>
  <div style="width:90%;height:8px;background:#16213e;border-radius:6px;margin:8px auto;overflow:hidden;">
    <div id="pBar" style="height:100%;width:0%;background:#4ade80;border-radius:6px;transition:width .2s;"></div>
  </div>
  <button id="pStart" style="margin-top:6px;background:#e94560;color:#fff;border:none;border-radius:10px;
    padding:12px 30px;font-size:1rem;font-weight:700;cursor:pointer;">START PRACTICE</button>
  <div style="color:#5a5a72;font-size:0.78rem;margin-top:8px;">needs microphone access &middot; works on localhost / HTTPS</div>
</div>
<script>
const PSTEPS=__STEPS__;
const NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
function midiName(m){return NAMES[m%12]+(Math.floor(m/12)-1);}
function midiFreq(m){return 440*Math.pow(2,(m-69)/12);}
const PRAISE=["Good.","Clean.","That's it.","Nailed.","Just like that."];
let pIdx=0, pHold=0, pWrong=0, pWrongNote=-1, pStepT=0, pDone=false, pStartT=0, pTimerOn=false;
const pStep=document.getElementById('pStep'), pPrompt=document.getElementById('pPrompt'),
      pHeard=document.getElementById('pHeard'), pFeed=document.getElementById('pFeed'),
      pBar=document.getElementById('pBar'), pStart=document.getElementById('pStart');
function pAutoCorrelate(buf,sr){
  let SIZE=buf.length, rms=0, i;
  for(i=0;i<SIZE;i++) rms+=buf[i]*buf[i];
  if(Math.sqrt(rms/SIZE)<0.015) return -1;
  let r1=0, r2=SIZE-1;
  const b=buf.slice(0);
  for(i=0;i<SIZE/2;i++) if(Math.abs(b[i])<0.2){b[i]=0;r1=i;}
  for(i=1;i<SIZE/2;i++) if(Math.abs(b[SIZE-i])<0.2){b[SIZE-i]=0;r2=SIZE-i;}
  const b2=b.slice(r1,r2); SIZE=b2.length;
  const c=new Array(SIZE).fill(0);
  for(i=0;i<SIZE;i++) for(let j=0;j<SIZE-i;j++) c[i]+=b2[j]*b2[j+i];
  let d=0; while(d<SIZE-1 && c[d]>c[d+1]) d++;
  let maxv=-1, maxp=-1;
  for(i=d;i<SIZE;i++) if(c[i]>maxv){maxv=c[i];maxp=i;}
  let T0=maxp;
  if(T0>0&&T0<SIZE-1){
    const x1=c[T0-1],x2=c[T0],x3=c[T0+1],aa=(x1+x3-2*x2)/2,bb=(x3-x1)/2;
    if(aa) T0=T0-bb/(2*aa);
  }
  return sr/T0;
}
function pShowStep(){
  const s=PSTEPS[pIdx];
  pStep.textContent='Step '+(pIdx+1)+' of '+PSTEPS.length;
  pPrompt.textContent=s.prompt;
  pHeard.textContent='listening\u2026';
  pFeed.textContent=''; pFeed.style.color='';
  pBar.style.width='0%';
  pHold=0; pWrong=0; pWrongNote=-1; pStepT=Date.now();
}
function pFinish(){
  pDone=true; pTimerOn=false;
  const secs=Math.round((Date.now()-pStartT)/1000);
  pStep.textContent='Complete';
  pPrompt.textContent='\\uD83C\\uDF96\\uFE0F PRACTICE PASSED';
  pPrompt.style.color='#4ade80';
  pHeard.textContent=PSTEPS.length+' for '+PSTEPS.length+' \u00b7 '+secs+' seconds';
  pFeed.textContent='Claim your badge below \u2014 then it\u2019s on to the next lesson.';
  pFeed.style.color='#4ade80';
  pBar.style.width='100%';
  pStart.style.display='none';
}
pStart.addEventListener('click', async ()=>{
  pStart.style.display='none';
  try{
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});
    const ctx=new (window.AudioContext||window.webkitAudioContext)();
    const src=ctx.createMediaStreamSource(stream), an=ctx.createAnalyser();
    an.fftSize=2048; src.connect(an);
    const buf=new Float32Array(an.fftSize);
    pIdx=0; pStartT=Date.now(); pTimerOn=true;
    pShowStep();
    (function tick(){
      if(!pTimerOn||pDone) return;
      an.getFloatTimeDomainData(buf);
      const f=pAutoCorrelate(buf,ctx.sampleRate);
      const target=midiFreq(PSTEPS[pIdx].midi);
      if(f>50&&f<1200){
        const cents=Math.round(1200*Math.log2(f/target));
        const near=Math.round(12*Math.log2(f/440))+69;
        pHeard.textContent='I hear: '+midiName(near)+' ('+(cents>0?'+':'')+cents+'\u00a2)';
        if(Math.abs(cents)<=25){
          pHold++; pWrong=0;
          pBar.style.width=Math.min(100,(pHold/45*100))+'%';
          pFeed.textContent='hold it\u2026'; pFeed.style.color='#a0a0a0';
          if(pHold>=45){
            pFeed.textContent=PRAISE[Math.floor(Math.random()*PRAISE.length)];
            pFeed.style.color='#4ade80';
            pIdx++;
            if(pIdx>=PSTEPS.length){ pFinish(); return; }
            setTimeout(()=>{ if(pTimerOn&&!pDone) pShowStep(); }, 700);
            pTimerOn=false;
            setTimeout(()=>{ pTimerOn=true; (function resume(){ if(pTimerOn&&!pDone) requestAnimationFrame(tick); })(); }, 750);
            return;
          }
        } else {
          pHold=0; pBar.style.width='0%';
          if(near===pWrongNote){ pWrong++; } else { pWrongNote=near; pWrong=1; }
          if(pWrong>=50){
            pFeed.textContent='I hear '+midiName(near)+' \u2014 fix your fingers and try again.';
            pFeed.style.color='#fbbf24';
          }
        }
      } else {
        pHeard.textContent='listening\u2026 play the note';
      }
      if(Date.now()-pStepT>45000){
        pFeed.textContent='Take a breath. Reset your hand \u2014 '+PSTEPS[pIdx].prompt;
        pFeed.style.color='#fbbf24';
        pStepT=Date.now(); pHold=0; pWrong=0;
      }
      requestAnimationFrame(tick);
    })();
  }catch(err){
    pHeard.textContent='microphone blocked \u2014 allow access and retry';
    pStart.style.display='';
  }
});
</script>
"""


def practice_dialogue(lesson_no):
    pr = PRACTICES[lesson_no]
    import json as _json
    steps = _json.dumps([{"prompt": p, "midi": m} for p, m in pr["steps"]])
    html = PRACTICE_HTML.replace("__STEPS__", steps).replace("__INTRO__", pr["intro"])
    components.html(html, height=560, scrolling=False)


def ear_trainer():
    components.html(EAR_TRAINER_HTML, height=520, scrolling=False)


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
            st.markdown("**🎼 Chord sheet** — Songsterr only carries tabs, so chord "
                        "sheets come from you: grab one from any chord site, paste it, "
                        "and it's converted automatically.")
            web_q = quote_plus(f"{title} {artist} guitar chords")
            st.link_button("🔍 Find chords on the web",
                           f"https://www.google.com/search?q={web_q}")
            pasted = st.text_area("Paste chord sheet", key=f"cs_{sid}", height=140,
                                  placeholder="Paste chords-over-lyrics or [Am]-style chords here…",
                                  label_visibility="collapsed")
            if st.button("💾 Save chord sheet", key=f"csave_{sid}"):
                if not pasted.strip():
                    st.warning("Paste a chord sheet first.")
                else:
                    sheet = convert_chord_sheet(pasted)
                    url = TAB_URL.format(sid)
                    entry = next((e for e in saved if e.get("url") == url), None)
                    if entry is None:
                        entry = {"title": title, "artist": artist,
                                 "source": "Songsterr", "url": url,
                                 "chordsheet": "", "tab": ""}
                        saved.append(entry)
                    entry["chordsheet"] = sheet
                    save_json(SAVED_PATH, saved)
                    st.success(f"Chord sheet saved for “{title}”. Open it under Saved → Lyrics + Chords.")

# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
def page_home():
    st.markdown('<div class="hero"><h1>🎸 SIX-STRING BOOTCAMP</h1>'
                '<p>Interactive guitar training · lyrics with chords · gig-ready setlists</p></div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1a1a2e 0%,#3a1f1f 100%);'
        'border:2px solid #e94560;border-radius:12px;padding:14px 16px;'
        'margin:4px 0 12px;text-align:center;">'
        '<div style="font-size:1.2rem;font-weight:800;color:#ffd700;">🎖️ VETERANS DISCOUNT</div>'
        '<div style="color:#ffffff;font-size:1.05rem;margin-top:4px;">Veterans save '
        '<b>20%</b> on Courses &amp; Membership.</div>'
        '<div style="color:#a0a0a0;font-size:0.8rem;margin-top:2px;">Thank you for your '
        'service. Discount applied at checkout.</div></div>',
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
        ("🧰", "Tools", "Metronome, tuner, and ear trainer — free forever."),
        ("🎸", "Gear", "The starter guitar Erik recommends, and what's next."),
        ("🏆", "Collection", "Your badges and NFTs. Proof of progress."),
        ("💬", "Social", "Six-String Social — profiles, the wall, gigs & jobs."),
    ]
    cols = st.columns(2)
    for i, (icon, name, desc) in enumerate(grid):
        with cols[i % 2]:
            if st.button(f"{icon} {name}\n{desc}", key=f"home_{name}", use_container_width=True):
                _goto(name)
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
                '<p>Twelve lessons. Song first. Play something tonight.</p></div>',
                unsafe_allow_html=True)
    sgt_card("<b>Twelve courses stand between you and the guitarist you were "
             "born to be.</b> Take them in order, recruit — no skipping leg day.")
    if st.session_state.get("practice"):
        lesson = st.session_state["practice"]
        pr = PRACTICES[lesson]
        if st.button("\u2190 Back to courses"):
            st.session_state["practice"] = None
            st.session_state["_jump"] = True
            st.rerun()
        st.markdown(f"### \U0001f941 Practice: {htmlmod.escape(pr['title'])}")
        st.caption("The AI is listening. Hold each note steady until it passes you.")
        practice_dialogue(lesson)
        st.markdown("---")
        badges = st.session_state.setdefault("badges", [])
        if lesson in badges:
            st.success("\U0001f3c5 Badge earned — it's on your Collection wall.")
        else:
            if st.button("\U0001f3c5 Claim my badge", key=f"badge_{lesson}"):
                badges.append(lesson)
                st.balloons()
                st.success("\U0001f3c5 Badge earned! Check your Collection.")
                _announce_badge(lesson, pr.get("title", ""))
        return
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
        notes = LESSON_CONTENT.get(idx + 1)
        if notes:
            with st.expander("📖 Erik's lesson notes (preview)"):
                for title, body in notes:
                    st.markdown(f"**{title}**")
                    st.markdown(body)
        if idx + 1 in PRACTICES:
            if st.button(f"\U0001f941 Practice: {PRACTICES[idx + 1]['title']}", key=f"prac_{idx}"):
                st.session_state["practice"] = idx + 1
                st.session_state["_jump"] = True
                st.rerun()
    st.caption("Lesson notes are Erik's own teaching — full video lessons + AI check-ins at launch.")


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


GEAR_URL = "https://www.Guitarcenter.com/Cort/AD810-OP-Dreadnought-Acoustic-Guitar-1500000270316.gc"


def page_gear():
    st.markdown('<div class="hero"><h1>🎸 GEAR I RECOMMEND</h1>'
                '<p>What Erik actually tells beginners to buy.</p></div>',
                unsafe_allow_html=True)
    sgt_card("<b>A bad guitar fights you.</b> This one doesn't. A hundred bucks, "
             "gig bag, picks — recruit, that's the best money in this course.")
    st.markdown("""<div class="course-card"><h4>Cort AD810 Dreadnought Pack</h4>
    <div>Spruce top, mahogany body, open-pore finish. Sounds great, very playable — """
    """the starter guitar Erik recommends to every beginner. Pack includes gig bag, picks, and strap.</div>
    <div style="margin-top:0.4rem;"><span class="badge badge-free">ERIK'S PICK</span>
    <span class="course-price">~$100</span></div></div>""", unsafe_allow_html=True)
    st.markdown(f"""<a href="{GEAR_URL}" target="_blank" rel="noopener" style="display:inline-block;
    background:#e94560;color:#fff;font-weight:700;padding:12px 28px;border-radius:10px;
    text-decoration:none;">&#128269; Check today's price</a>""", unsafe_allow_html=True)
    st.caption("Affiliate links activate at launch — then every guitar bought here supports the school.")
    st.markdown("**Lesson 1 needs:** just the guitar. Capo and extras come later — saved for lesson 12 on purpose.")


def page_collection():
    st.markdown('<div class="hero"><h1>🏆 MY COLLECTION</h1>'
                '<p>Badges for the wall. NFTs for forever.</p></div>',
                unsafe_allow_html=True)
    sgt_card("<b>Twelve lessons, twelve trophies.</b> Pass the AI check-in, take the badge. "
             "Your wall of proof starts here.")
    st.markdown("Pass a lesson's AI practice check and two things happen: a **badge** appears on your "
                "community wall for everyone to see, and an **NFT** — a piece of art on the blockchain "
                "cataloging your achievement — lands in your collection. No wallets to set up, no crypto "
                "to buy. It just shows up.")
    badges = st.session_state.get("badges", [])
    cols = st.columns(4)
    for i in range(12):
        earned = (i + 1) in badges
        with cols[i % 4]:
            st.markdown(f"""<div class="course-card" style="text-align:center;{'opacity:0.55;' if not earned else ''}">
            <div style="font-size:2rem;">{"\U0001f3c5" if earned else "🔒"}</div><div>Lesson {i + 1}</div>
            <div style="font-size:0.75rem;color:{'#4ade80' if earned else '#5a5a72'};">{"earned" if earned else "locked"}</div></div>""",
                        unsafe_allow_html=True)
    st.caption("Badges + NFT collection unlock at launch.")


def page_tools():
    st.markdown('<div class="hero"><h1>🧰 TOOLS</h1>'
                '<p>Free forever. Tune up, lock in.</p></div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tool-card" id="tool-metronome"><h3 style="color:#e94560;">⏱️ Metronome</h3>',
                    unsafe_allow_html=True)
        metronome()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tool-card" id="tool-tuner"><h3 style="color:#e94560;">🎛️ Tuner</h3>',
                    unsafe_allow_html=True)
        tuner()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="tool-card" id="tool-ear"><h3 style="color:#e94560;">👂 Ear Trainer</h3>'
                '<p style="color:#a0a0a0;">Hear the note. Sing it back. Get scored. '
                'Match your voice to the pitch — this is how ears are built.</p>',
                unsafe_allow_html=True)
    ear_trainer()
    st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Community wall — shared through the repo at community/wall.json
# ----------------------------------------------------------------------------
WALL_REPO = "erikmartin-dev/Six-String-Bootcamp"
WALL_PATH = "community/wall.json"
WALL_RAW = f"https://raw.githubusercontent.com/{WALL_REPO}/main/{WALL_PATH}"
WALL_API = f"https://api.github.com/repos/{WALL_REPO}/contents/{WALL_PATH}"
WALL_LOCAL = os.path.join(DATA_DIR, "wall.json")
WALL_HEADERS = {"Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"}

PROFILES_PATH = "community/profiles.json"
BOARD_PATH = "community/board.json"
PHOTOS_DIR = "community/photos"

STICKERS = ["\U0001f918", "\U0001f3b8", "\U0001f525", "\U0001f44f", "\U0001f62e", "\U00002764\ufe0f"]
AVATAR_EMOJI = ["\U0001f3b8", "\U0001f918", "\U0001f941", "\U0001f3a4", "\U0001f3b9",
                "\U0001f3ba", "\U0001f3bb", "\U0001f3a7", "🎵", "\U0001f525",
                "\U000026a1", "\U0001f920", "\U0001f985", "\U0001f43a", "\U0001f335"]
SKILL_LEVELS = ["Just starting", "Beginner", "Intermediate", "Advanced", "Gigging musician"]
BOARD_KINDS = ["\U0001f918 Jam", "\U0001f3a4 Gig", "\U0001f4bc Job"]


def _repo_api(path):
    return f"https://api.github.com/repos/{WALL_REPO}/contents/{path}"


def _repo_raw(path):
    return f"https://raw.githubusercontent.com/{WALL_REPO}/main/{path}"


def repo_load_json(path, default):
    """Load a JSON doc from the repo (fresh with token, else public raw)."""
    tok = _wall_token()
    if tok and requests is not None:
        try:
            h = {**WALL_HEADERS, "Authorization": "Bearer " + tok}
            cur = requests.get(_repo_api(path), headers=h, timeout=10).json()
            if cur.get("content"):
                return json.loads(base64.b64decode(cur["content"]).decode("utf-8", "replace"))
        except Exception:
            pass
    if requests is not None:
        try:
            r = requests.get(_repo_raw(path), timeout=8)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return default


def repo_save_json(path, data, message):
    """Save a JSON doc to the repo (creates it if missing). Returns True on success."""
    tok = _wall_token()
    if not tok or requests is None:
        return False
    try:
        h = {**WALL_HEADERS, "Authorization": "Bearer " + tok}
        cur = requests.get(_repo_api(path), headers=h, timeout=10).json()
        body = {"message": message,
                "content": base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()}
        if cur.get("sha"):
            body["sha"] = cur["sha"]
        r = requests.put(_repo_api(path), headers=h, json=body, timeout=15)
        return r.status_code in (200, 201)
    except Exception:
        return False


def photo_upload(file):
    """Downscale and upload a photo to the repo. Returns the raw URL or None."""
    tok = _wall_token()
    if not tok or requests is None:
        return None
    try:
        from PIL import Image
        import io
        img = Image.open(file).convert("RGB")
        img.thumbnail((1200, 1200))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=82)
        data = buf.getvalue()
        if not data or len(data) > 2500000:
            return None
        name = f"{uuid.uuid4().hex[:12]}.jpg"
        h = {**WALL_HEADERS, "Authorization": "Bearer " + tok}
        body = {"message": f"Community photo {name}",
                "content": base64.b64encode(data).decode()}
        r = requests.put(_repo_api(f"{PHOTOS_DIR}/{name}"), headers=h, json=body, timeout=30)
        if r.status_code in (200, 201):
            return _repo_raw(f"{PHOTOS_DIR}/{name}")
    except Exception:
        pass
    return None


def _wall_update_post(post_id, fn):
    """Apply fn(post) to one wall post, remote or local. Returns True on success."""
    def bump(psts):
        for p in psts:
            if p.get("id") == post_id:
                fn(p)
                return True
        return False
    if _wall_token():
        return _wall_remote_update(bump)
    data = load_json(WALL_LOCAL, {"posts": []})
    if not bump(data.get("posts", [])):
        return False
    try:
        save_json(WALL_LOCAL, data)
        return True
    except Exception:
        return False


def _profiles():
    return repo_load_json(PROFILES_PATH, {"profiles": {}}).get("profiles", {})


def _is_pro(name, profiles):
    return profiles.get(name, {}).get("role") == "pro"


def _flair(name, profiles):
    prof = profiles.get(name, {})
    if prof.get("role") == "pro":
        return " \u2705 PRO"
    if prof.get("tier") == "member":
        return " \u2b50 MEMBER"
    return ""


def _badges_for(name, posts):
    out = []
    for p in posts:
        if p.get("name") == name:
            for b in p.get("badges", []):
                if b not in out:
                    out.append(b)
    return sorted(out)



def _wall_token():
    return (_secret("github_token") or "").strip()


def wall_load():
    """Returns (posts, readable). Fresh API read with a token (no CDN cache);
    public raw read otherwise; local file as a last resort."""
    tok = _wall_token()
    if tok and requests is not None:
        try:
            h = {**WALL_HEADERS, "Authorization": "Bearer " + tok}
            cur = requests.get(WALL_API, headers=h, timeout=10).json()
            if cur.get("content"):
                data = json.loads(base64.b64decode(cur["content"]).decode("utf-8", "replace"))
                if isinstance(data, dict) and isinstance(data.get("posts"), list):
                    return data["posts"], True
        except Exception:
            pass
    if requests is not None:
        try:
            r = requests.get(WALL_RAW, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and isinstance(data.get("posts"), list):
                    return data["posts"], True
        except Exception:
            pass
    return load_json(WALL_LOCAL, {"posts": []}).get("posts", []), False


def _wall_remote_update(fn):
    """Load the shared wall, apply fn(posts), write back. Returns True on success."""
    tok = _wall_token()
    if not (tok and requests is not None):
        return False
    try:
        h = {**WALL_HEADERS, "Authorization": "Bearer " + tok}
        cur = requests.get(WALL_API, headers=h, timeout=10).json()
        sha = cur.get("sha")
        if not sha:
            return False
        try:
            data = json.loads(base64.b64decode(cur.get("content") or "").decode("utf-8", "replace"))
        except Exception:
            data = {}
        posts = data.get("posts", []) if isinstance(data, dict) else []
        fn(posts)
        body = {"message": "Community wall update", "sha": sha,
                "content": base64.b64encode(
                    json.dumps({"posts": posts}, indent=2, ensure_ascii=False).encode()).decode()}
        r = requests.put(WALL_API, headers=h, json=body, timeout=15)
        return r.status_code in (200, 201)
    except Exception:
        return False


def wall_publish(post):
    """Append a post. Returns True on success."""
    if _wall_token():
        local = load_json(WALL_LOCAL, {"posts": []}).get("posts", [])

        def add(psts):
            ids = {p.get("id") for p in psts}
            for lp in local:  # migrate any device-only posts
                if lp.get("id") not in ids:
                    psts.append(lp)
            psts.append(post)

        if _wall_remote_update(add):
            save_json(WALL_LOCAL, {"posts": []})
            return True
        return False
    posts = load_json(WALL_LOCAL, {"posts": []}).get("posts", [])
    posts.append(post)
    try:
        save_json(WALL_LOCAL, {"posts": posts})
        return True
    except Exception:
        return False


def wall_like(post_id):
    """Bump a post's like count. Returns True on success."""
    def bump(psts):
        for p in psts:
            if p.get("id") == post_id:
                p["likes"] = int(p.get("likes", 0) or 0) + 1
                return True
        return False

    if _wall_token():
        return _wall_remote_update(bump)
    data = load_json(WALL_LOCAL, {"posts": []})
    if not bump(data.get("posts", [])):
        return False  # shared post, wall not connected
    try:
        save_json(WALL_LOCAL, data)
        return True
    except Exception:
        return False


def _ago(ts):
    try:
        d = time.time() - float(ts)
    except Exception:
        return ""
    if d < 60:
        return "just now"
    if d < 3600:
        return f"{int(d // 60)}m ago"
    if d < 86400:
        return f"{int(d // 3600)}h ago"
    if d < 86400 * 7:
        return f"{int(d // 86400)}d ago"
    return time.strftime("%b %d, %Y", time.localtime(float(ts)))



def _profile_card(name, prof, posts, members):
    c1, c2 = st.columns([1, 4])
    with c1:
        if prof.get("photo"):
            st.image(prof["photo"], width=72)
        else:
            st.markdown(f"<div style='font-size:52px;line-height:1'>{prof.get('avatar', '\U0001f3b8')}</div>",
                        unsafe_allow_html=True)
    with c2:
        if prof.get("role") == "pro":
            flair = " \u2705 PRO"
        elif prof.get("tier") == "member":
            flair = " \u2b50 MEMBER"
        else:
            flair = ""
        st.markdown(f"**{name}**{flair}")
        if prof.get("role") == "pro" and prof.get("creds"):
            st.caption("\U0001f3a4 " + prof["creds"])
        bits = [b for b in (prof.get("level"), prof.get("city"), prof.get("genres")) if b]
        if bits:
            st.caption(" \u00b7 ".join(bits))
        if prof.get("bio"):
            st.write(prof["bio"])
        badges = _badges_for(name, posts)
        if badges:
            st.caption(" ".join(f"\U0001f3c5 L{b}" for b in badges))
        fc = follower_count(name, members)
        if fc:
            st.caption(f"\U0001f465 {fc} follower{'s' if fc != 1 else ''}")
        me = st.session_state.get("member")
        if me and name.lower() != me["name"].lower():
            fl = [x.lower() for x in members.get(_email_hash(me["email"]), {}).get("following", [])]
            is_f = name.lower() in fl
            if st.button("\u2796 Unfollow" if is_f else "\u2795 Follow", key=f"fol_{name}"):
                res = member_follow(name)
                if res in ("followed", "unfollowed"):
                    st.rerun()
                else:
                    st.warning("Couldn't update \u2014 try again in a bit.")


def _wall_tab():
    posts, _readable = wall_load()
    can_share = bool(_wall_token())
    liked = st.session_state.setdefault("wall_liked", [])
    stuck = st.session_state.setdefault("wall_stuck", [])
    profiles = _profiles()
    announce = st.checkbox("\U0001f4e2 Announce my badges on the wall automatically",
                           value=st.session_state.get("announce_badges", True))
    st.session_state["announce_badges"] = announce

    st.markdown("### Shout it out")
    name = st.text_input("Your name", value=st.session_state.get("wall_name", ""),
                        placeholder="e.g. Erik", max_chars=30)
    text = st.text_area("What's happening?",
                        placeholder="Nailed my first clean G to C change today\u2026",
                        max_chars=500, height=90)
    photo = st.file_uploader("Add a photo (optional)", type=["jpg", "jpeg", "png"])
    my_badges = sorted(st.session_state.get("badges", []))
    if my_badges:
        st.caption("Your badges ride along on your post: " +
                   " ".join(f"\U0001f3c5 L{b}" for b in my_badges))
    if st.button("\U0001f4e3 Post to the wall", type="primary"):
        if not (name or "").strip():
            st.warning("Give yourself a name first.")
        elif not (text or "").strip():
            st.warning("Write something first.")
        else:
            st.session_state["wall_name"] = name.strip()[:30]
            post = {"id": uuid.uuid4().hex[:12], "name": name.strip()[:30],
                    "text": text.strip()[:500], "badges": my_badges,
                    "ts": time.time(), "likes": 0, "stickers": {}, "replies": []}
            if photo is not None:
                if not can_share:
                    st.warning("Photos need the shared wall connection \u2014 posting without it.")
                else:
                    with st.spinner("Uploading photo\u2026"):
                        url = photo_upload(photo)
                    if url:
                        post["photo"] = url
                    else:
                        st.warning("Photo didn't upload \u2014 posting without it.")
            if wall_publish(post):
                if can_share:
                    st.session_state.setdefault("wall_just_posted", []).append(post)
                    st.success("You're on the wall! \U0001f3b8")
                else:
                    st.success("Posted \u2014 it stays on this device until the shared wall is connected.")
                st.rerun()
            else:
                st.error("Couldn't reach the wall \u2014 check your connection and try again.")

    if not can_share:
        st.info("\U0001f4e1 You're reading the public wall. Your posts stay on this device until "
                "the shared wall is connected (one-time setup, two minutes).")

    st.markdown("### The wall")
    show = st.radio("Show", ["All posts", "\U0001f3c5 Badge posts", "\U0001f465 Following"], horizontal=True)
    mine = load_json(WALL_LOCAL, {"posts": []}).get("posts", [])
    just = st.session_state.get("wall_just_posted", [])
    seen = {p.get("id") for p in posts} | {p.get("id") for p in mine}
    extra = [p for p in just if p.get("id") not in seen]
    if len(extra) != len(just):
        st.session_state["wall_just_posted"] = extra
    feed = sorted(mine + extra + posts, key=lambda p: p.get("ts", 0), reverse=True)
    if show == "\U0001f3c5 Badge posts":
        feed = [p for p in feed if p.get("badges")]
    elif show == "\U0001f465 Following":
        me = st.session_state.get("member")
        if not me:
            st.info("Log in on the \U0001f511 Join tab to follow other pickers.")
            feed = []
        else:
            members = repo_load_json(MEMBERS_PATH, {"members": {}}).get("members", {})
            following = {x.lower() for x in
                         members.get(_email_hash(me["email"]), {}).get("following", [])}
            feed = [p for p in feed if p.get("name", "").lower() in following]
    if not feed:
        st.caption("The wall is quiet\u2026 be the first to post. \U0001f3b8")
    for p in feed:
        pid = p.get("id", "")
        nm = htmlmod.escape(str(p.get("name", "Recruit"))[:30])
        tx = htmlmod.escape(str(p.get("text", ""))[:500]).replace("\n", "<br>")
        av = profiles.get(p.get("name"), {}).get("avatar", "\U0001f3b8")
        chips = " ".join(
            f"<span class='badge badge-free'>\U0001f3c5 L{b}</span>"
            for b in (p.get("badges") or [])[:12])
        chiprow = f"<div style='margin-top:0.3rem;'>{chips}</div>" if chips else ""
        imgrow = (f"<div><img src='{p['photo']}' style='max-width:100%;border-radius:8px;"
                  f"margin:0.35rem 0;'></div>" if p.get("photo") else "")
        st.markdown(
            f"<div class='tool-card' style='margin-bottom:0.15rem;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:baseline;'>"
            f"<b style='color:#e94560;'>{av} {nm}{_flair(p.get('name', ''), profiles)}</b>"
            f"<span style='color:#8a8a9e;font-size:0.8rem;'>{_ago(p.get('ts', 0))}</span></div>"
            f"<div style='margin:0.35rem 0;'>{tx}</div>{imgrow}{chiprow}</div>",
            unsafe_allow_html=True)
        c_like, c_rest = st.columns([1, 5])
        likes = int(p.get("likes", 0) or 0)
        with c_like:
            if pid in liked:
                st.button(f"\U0001f525 {likes}", key=f"wall_liked_{pid}", disabled=True)
            elif st.button(f"\U0001f525 {likes}", key=f"wall_like_{pid}"):
                if wall_like(pid):
                    liked.append(pid)
                    st.rerun()
                else:
                    st.warning("Couldn't send the like \u2014 try again in a bit.")
        with c_rest:
            scols = st.columns(len(STICKERS))
            for i, s in enumerate(STICKERS):
                n = int((p.get("stickers") or {}).get(s, 0))
                if scols[i].button(f"{s} {n}", key=f"st{pid}{i}"):
                    key = pid + s
                    if key in stuck:
                        st.toast("Already gave that sticker.")
                    elif _wall_update_post(pid, lambda post, e=s: post.setdefault("stickers", {}).update(
                            {e: int(post.get("stickers", {}).get(e, 0)) + 1})):
                        stuck.append(key)
                        st.rerun()
                    else:
                        st.warning("Couldn't send the sticker \u2014 try again in a bit.")
        replies = p.get("replies", []) or []
        with st.expander(f"💬 Replies ({len(replies)})"):
            for r in sorted(replies, key=lambda x: x.get("ts", 0)):
                rnm = htmlmod.escape(str(r.get("name", "?"))[:30])
                rtx = htmlmod.escape(str(r.get("text", ""))[:300]).replace("\n", "<br>")
                st.markdown(
                    f"<b>{rnm}</b>{_flair(r.get('name', ''), profiles)} "
                    f"<span style='color:#8a8a9e;font-size:0.8rem;'>{_ago(r.get('ts', 0))}</span>"
                    f"<br>{rtx}", unsafe_allow_html=True)
            rn = st.text_input("Your name", value=st.session_state.get("wall_name", ""),
                               key=f"rn_{pid}", max_chars=30)
            rt = st.text_input("Write a reply\u2026", key=f"rt_{pid}", max_chars=300)
            if st.button("Reply", key=f"rp_{pid}"):
                if not (rn or "").strip() or not (rt or "").strip():
                    st.warning("Name and reply needed.")
                else:
                    reply = {"id": uuid.uuid4().hex[:12], "name": rn.strip()[:30],
                             "text": rt.strip()[:300], "ts": time.time()}
                    if _wall_update_post(pid, lambda post, rp=reply: post.setdefault("replies", []).append(rp)):
                        st.session_state["wall_name"] = rn.strip()[:30]
                        st.rerun()
                    else:
                        st.warning("Couldn't send the reply \u2014 try again in a bit.")
        st.divider()


def _profiles_tab():
    st.markdown("#### Your profile")
    st.caption("18+ only \u2014 pick a name, an avatar, and tell the crew who you are.")
    can_share = bool(_wall_token())
    with st.form("profile_form"):
        nm = st.text_input("Display name (use the same name you post with)", max_chars=30,
                            value=st.session_state.get("member", {}).get("name", ""))
        c1, c2 = st.columns(2)
        with c1:
            av = st.selectbox("Avatar", AVATAR_EMOJI)
        with c2:
            ph = st.file_uploader("Or upload a profile photo", type=["jpg", "jpeg", "png"])
        bio = st.text_area("Bio", max_chars=200, placeholder="Rhythm player, into blues and classic rock\u2026")
        c3, c4 = st.columns(2)
        with c3:
            lvl = st.selectbox("Skill level", SKILL_LEVELS)
        with c4:
            city = st.text_input("City (for gigs and jam buddies)", max_chars=40)
        genres = st.text_input("Favorite genres", max_chars=80, placeholder="blues, rock, country")
        is_pro = st.checkbox("I'm a professional musician")
        creds = st.text_input("Pro credentials (shown on your \u2705 PRO flair)",
                              placeholder="Touring guitarist, 20 years\u2026", max_chars=80)
        age_ok = st.checkbox("I confirm I'm 18 or older")
        st.caption("Member tier: Free \U0001f193 \u2014 paid memberships with exclusive stickers \u0026 flair are coming soon.")
        save = st.form_submit_button("Save profile", use_container_width=True)
    if save:
        if not nm.strip():
            st.warning("Pick a display name first.")
        elif not age_ok:
            st.warning("This community is 18+ \u2014 please confirm your age.")
        elif not can_share:
            st.warning("Profiles need the shared wall connection.")
        else:
            prof = {"avatar": av, "bio": bio.strip(), "level": lvl,
                    "city": city.strip(), "genres": genres.strip(),
                    "role": "pro" if is_pro else "student",
                    "creds": creds.strip()[:80] if is_pro else "",
                    "tier": "free", "ts": time.time()}
            if ph is not None:
                with st.spinner("Uploading photo\u2026"):
                    url = photo_upload(ph)
                if url:
                    prof["photo"] = url
                else:
                    st.warning("Photo didn't upload \u2014 saving without it.")
            data = repo_load_json(PROFILES_PATH, {"profiles": {}})
            data.setdefault("profiles", {})[nm.strip()[:30]] = prof
            if repo_save_json(PROFILES_PATH, data, f"Profile: {nm.strip()[:30]}"):
                st.success("Profile live! \U0001f918")
                st.rerun()
            else:
                st.error("Couldn't save \u2014 try again.")
    st.markdown("### Members")
    posts, _ = wall_load()
    profiles = _profiles()
    if not profiles:
        st.info("No profiles yet \u2014 be the first. \U0001f918")
    members = repo_load_json(MEMBERS_PATH, {"members": {}}).get("members", {})
    for name, prof in sorted(profiles.items()):
        _profile_card(name, prof, posts, members)
        st.divider()


def _board_tab():
    st.markdown("#### The musician board")
    st.caption("Find jam buddies, post gigs, hire players \u2014 the whole musician community.")
    can_share = bool(_wall_token())
    with st.form("board_form", clear_on_submit=True):
        nm = st.text_input("Your display name", max_chars=30)
        c1, c2 = st.columns(2)
        with c1:
            kind = st.selectbox("Post type", BOARD_KINDS)
        with c2:
            city = st.text_input("City", max_chars=40)
        headline = st.text_input("Headline", max_chars=80,
                                 placeholder="Need a lead guitarist for Saturday night\u2026")
        details = st.text_area("Details", max_chars=400,
                               placeholder="Venue, pay, setlist, how to reach you\u2026")
        go = st.form_submit_button("Post it \U0001f4cc", use_container_width=True)
    if go:
        if not nm.strip() or not headline.strip() or not details.strip():
            st.warning("Name, headline, and details \u2014 fill those in.")
        elif not can_share:
            st.warning("The board needs the shared wall connection.")
        else:
            data = repo_load_json(BOARD_PATH, {"posts": []})
            data.setdefault("posts", []).append({
                "id": uuid.uuid4().hex[:12], "name": nm.strip()[:30], "kind": kind,
                "city": city.strip(), "headline": headline.strip()[:80],
                "details": details.strip()[:400], "ts": time.time()})
            if repo_save_json(BOARD_PATH, data, f"Board post: {nm.strip()[:30]}"):
                st.success("You're on the board! \U0001f4cc")
                st.rerun()
            else:
                st.error("Couldn't save \u2014 try again.")
    st.markdown("### On the board")
    filt = st.radio("Show", ["All"] + BOARD_KINDS, horizontal=True)
    posts = repo_load_json(BOARD_PATH, {"posts": []}).get("posts", [])
    posts = sorted(posts, key=lambda x: x.get("ts", 0), reverse=True)
    if filt != "All":
        posts = [x for x in posts if x.get("kind") == filt]
    if not posts:
        st.info("Nothing here yet \u2014 put the first pin in the map. \U0001f4cd")
    for x in posts:
        when = _ago(x.get("ts", 0))
        loc = htmlmod.escape(str(x.get("city", ""))[:40])
        st.markdown(
            f"<div class='tool-card' style='margin-bottom:0.4rem;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:baseline;'>"
            f"<b style='color:#e94560;'>{x.get('kind', '')} {htmlmod.escape(str(x.get('headline', ''))[:80])}</b>"
            f"<span style='color:#8a8a9e;font-size:0.8rem;'>{when}</span></div>"
            f"<div style='color:#8a8a9e;font-size:0.85rem;margin:0.15rem 0;'>"
            f"{htmlmod.escape(str(x.get('name', '?'))[:30])}" + (f" \u00b7 {loc}" if loc else "") + "</div>"
            f"<div style='margin:0.35rem 0;'>{htmlmod.escape(str(x.get('details', ''))[:400]).replace(chr(10), '<br>')}</div>"
            f"</div>",
            unsafe_allow_html=True)



MEMBERS_PATH = "community/members.json"


def _member_key():
    try:
        from cryptography.fernet import Fernet  # noqa: F401
    except Exception:
        return None
    return (_secret("member_key") or "").strip()


def _email_hash(email):
    import hashlib
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


def _email_valid(email):
    import re as _re
    return bool(_re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (email or "").strip()))


def _username_valid(username):
    import re as _re
    return bool(_re.match(r"^[a-zA-Z0-9_]{3,20}$", (username or "").strip()))


def _username_taken(username):
    un = username.strip().lower()
    data = repo_load_json(MEMBERS_PATH, {"members": {}})
    return any(m.get("name", "").lower() == un for m in data.get("members", {}).values())


def member_signup(email, username, push_consent):
    """Register a member. Returns ok|exists|taken|nokey|badkey|savefail."""
    key = _member_key()
    if not key:
        return "nokey"
    try:
        from cryptography.fernet import Fernet
        f = Fernet(key.encode())
    except Exception:
        return "badkey"
    email = email.strip().lower()
    eh = _email_hash(email)
    data = repo_load_json(MEMBERS_PATH, {"members": {}})
    members = data.setdefault("members", {})
    if eh in members:
        return "exists"
    if _username_taken(username):
        return "taken"
    members[eh] = {"email_enc": f.encrypt(email.encode()).decode(),
                   "name": username.strip()[:30],
                   "plan": "free",
                   "following": [],
                   "push": bool(push_consent),
                   "push_ts": time.time() if push_consent else 0,
                   "ts": time.time()}
    return "ok" if repo_save_json(MEMBERS_PATH, data, f"New member: {username.strip()[:30]}") else "savefail"


def member_follow(target):
    """Toggle follow on another member. Returns followed|unfollowed|nologin|nouser|self|savefail."""
    me = st.session_state.get("member")
    if not me:
        return "nologin"
    data = repo_load_json(MEMBERS_PATH, {"members": {}})
    members = data.get("members", {})
    mine = members.get(_email_hash(me["email"]))
    if not mine:
        return "nouser"
    t = target.strip()
    if t.lower() == me["name"].lower():
        return "self"
    fl = mine.setdefault("following", [])
    low = [x.lower() for x in fl]
    if t.lower() in low:
        mine["following"] = [x for x in fl if x.lower() != t.lower()]
        action = "unfollowed"
    else:
        fl.append(t[:30])
        action = "followed"
    return action if repo_save_json(MEMBERS_PATH, data, f"{me['name']} {action} {t[:30]}") else "savefail"


def follower_count(username, members):
    un = username.strip().lower()
    return sum(1 for m in members.values()
               if un in [x.lower() for x in m.get("following", [])])


def member_lookup(email):
    data = repo_load_json(MEMBERS_PATH, {"members": {}})
    return data.get("members", {}).get(_email_hash(email))


def _login_as(rec, email):
    st.session_state["member"] = {"name": rec.get("name"),
                                  "email": email.strip().lower(),
                                  "push": bool(rec.get("push"))}
    st.session_state["wall_name"] = rec.get("name")


def _join_tab():
    st.markdown("#### Become a member")
    st.caption("One email and you're in \u2014 a persistent identity across the wall, profiles, and board.")
    if not _member_key():
        st.info("\U0001f511 Membership signup is being connected \u2014 check back soon.")
        return
    if st.session_state.get("member"):
        m = st.session_state["member"]
        st.success(f"You're in as **{htmlmod.escape(m['name'])}** \u2705")
        st.caption("\U0001f514 Push notifications: " +
                   ("ON \u2014 we'll switch them on with the app backend." if m.get("push")
                    else "OFF \u2014 change your mind anytime by rejoining."))
        if st.button("Log out"):
            st.session_state.pop("member", None)
            st.rerun()
        return
    with st.form("join_form"):
        email = st.text_input("Email", placeholder="you@example.com", max_chars=80)
        name = st.text_input("Username", max_chars=20,
                             placeholder="pick_a_name")
        st.caption("3\u201320 characters, letters/numbers/underscores \u2014 this is your identity everywhere on the site.")
        push = st.checkbox("Yes \u2014 send me push notifications (replies, gigs, new lessons)", value=True)
        age_ok = st.checkbox("I confirm I'm 18 or older")
        go = st.form_submit_button("Join the crew \U0001f918", use_container_width=True)
    if go:
        if not _email_valid(email):
            st.warning("That email doesn't look right.")
        elif not _username_valid(name):
            st.warning("Username needs 3\u201320 characters: letters, numbers, underscores.")
        elif not age_ok:
            st.warning("This community is 18+ \u2014 please confirm your age.")
        else:
            res = member_signup(email, name, push)
            if res == "taken":
                st.warning("That username's taken \u2014 try another.")
            elif res in ("ok", "exists"):
                rec = member_lookup(email) or {"name": name.strip()[:30], "push": push}
                _login_as(rec, email)
                st.success("Welcome to the crew! \U0001f918 You're logged in." if res == "ok"
                           else f"Welcome back, **{htmlmod.escape(rec.get('name', ''))}**! You're logged in.")
                st.rerun()
            elif res == "nokey":
                st.error("Membership isn't connected yet \u2014 try again shortly.")
            else:
                st.error("Couldn't save \u2014 try again in a bit.")
    with st.expander("Already a member? Log in"):
        lemail = st.text_input("Your email", key="login_email", max_chars=80)
        if st.button("Log in", key="login_go"):
            rec = member_lookup(lemail)
            if rec:
                _login_as(rec, lemail)
                st.success(f"Welcome back, **{htmlmod.escape(rec.get('name', ''))}**!")
                st.rerun()
            else:
                st.warning("No member found with that email \u2014 join above. \U0001f446")
    st.caption("\U0001f514 Push notifications aren't live yet \u2014 your consent is saved now and honored when the app backend launches.")

def _announce_badge(lesson, title):
    """Auto-post a badge announcement to the community wall."""
    if not st.session_state.get("announce_badges", True):
        return
    name = (st.session_state.get("wall_name") or "").strip()
    if not name:
        st.info("\U0001f4a1 Set your name on the Community wall and your future badges will announce themselves there. \U0001f4e2")
        return
    post = {"id": uuid.uuid4().hex[:12], "name": name,
            "text": f"Just earned the Lesson {lesson} badge\u2014{title}! \U0001f3c5 Who's next? \U0001f3b8",
            "badges": [lesson], "ts": time.time(), "likes": 0, "stickers": {}, "replies": []}
    if wall_publish(post):
        if _wall_token():
            st.session_state.setdefault("wall_just_posted", []).append(post)
        st.success("\U0001f4e2 Announced on the Community wall!")
    else:
        st.warning("Badge claimed, but the wall announcement didn't go through.")


FORUMS_PATH = "community/forums.json"
DEFAULT_FORUMS = [
    {"id": "beginner-questions", "icon": "\u2753", "name": "Beginner Questions",
     "desc": "No dumb questions. Ask anything."},
    {"id": "gear-talk", "icon": "\U0001f3b8", "name": "Gear Talk",
     "desc": "Guitars, amps, pedals, strings."},
    {"id": "songwriting", "icon": "🎵", "name": "Songwriting & Riffs",
     "desc": "Riffs, lyrics, arrangements."},
    {"id": "show-off", "icon": "\U0001f3aa", "name": "Show Off",
     "desc": "Post your playing. Earn your applause."},
    {"id": "theory", "icon": "\U0001f4da", "name": "Theory & Technique",
     "desc": "Scales, chords, and why they work."},
]


def _forums_data():
    data = repo_load_json(FORUMS_PATH, {"forums": {}})
    forums = data.get("forums") or {}
    if not forums:
        forums = {f["id"]: dict(f, posts=[]) for f in DEFAULT_FORUMS}
    return data, forums


def _forum_update(fn, message="Forum update"):
    if not _wall_token():
        return False
    data, forums = _forums_data()
    fn(forums)
    data["forums"] = forums
    return repo_save_json(FORUMS_PATH, data, message)


def _find_post(forums, fid, pid):
    for p in forums.get(fid, {}).get("posts", []):
        if p.get("id") == pid:
            return p
    return None


def _find_comment(post, cid):
    for c in post.get("comments", []):
        if c.get("id") == cid:
            return c, None
        for r in c.get("replies", []):
            if r.get("id") == cid:
                return r, c
    return None, None


def _score(item):
    v = item.get("votes", {})
    return int(v.get("up", 0)) - int(v.get("down", 0))


def _hot(item):
    age_h = max(0.0, (time.time() - float(item.get("ts", 0))) / 3600.0)
    return _score(item) / ((age_h + 2.0) ** 1.5)


def _forum_vote(fid, pid, cid, kind):
    votes = st.session_state.setdefault("forum_votes", {})
    key = f"{fid}|{pid}|{cid or ''}"
    cur = votes.get(key, 0)
    new = 0 if (kind == "up" and cur == 1) or (kind == "down" and cur == -1) else (1 if kind == "up" else -1)
    du = (1 if new == 1 else 0) - (1 if cur == 1 else 0)
    dd = (1 if new == -1 else 0) - (1 if cur == -1 else 0)

    def fn(forums):
        post = _find_post(forums, fid, pid)
        if not post:
            return
        target = post
        if cid:
            target, _par = _find_comment(post, cid)
            if not target:
                return
        v = target.setdefault("votes", {"up": 0, "down": 0})
        v["up"] = max(0, int(v.get("up", 0)) + du)
        v["down"] = max(0, int(v.get("down", 0)) + dd)

    if _forum_update(fn):
        votes[key] = new
        return True
    return False


def _vote_row(fid, pid, cid, item, key_prefix):
    s = _score(item)
    cur = st.session_state.get("forum_votes", {}).get(f"{fid}|{pid}|{cid or ''}", 0)
    c1, c2, c3, _sp = st.columns([1, 1, 1, 7])
    if c1.button("\u25b2" if cur == 1 else "\u25b3", key=f"{key_prefix}_up"):
        if _forum_vote(fid, pid, cid, "up"):
            st.rerun()
        else:
            st.warning("Couldn't vote \u2014 try again in a bit.")
    c2.markdown(f"<div style='text-align:center;font-weight:bold;padding-top:0.4rem;'>{s}</div>",
                unsafe_allow_html=True)
    if c3.button("\u25bc" if cur == -1 else "\u25bd", key=f"{key_prefix}_dn"):
        if _forum_vote(fid, pid, cid, "down"):
            st.rerun()
        else:
            st.warning("Couldn't vote \u2014 try again in a bit.")


def _forum_tab():
    nav = st.session_state.setdefault("forum_nav", {"forum": None, "post": None})
    _data, forums = _forums_data()
    if nav.get("post"):
        _forum_post_view(forums, nav["forum"], nav["post"])
    elif nav.get("forum"):
        _forum_posts_view(forums, nav["forum"])
    else:
        _forum_list_view(forums)


def _forum_list_view(forums):
    st.markdown("#### Forums")
    st.caption("Pick your corner \u2014 or start the discussion.")
    for fid, f in forums.items():
        n = len(f.get("posts", []))
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(f"### {f.get('icon', '💬')} {htmlmod.escape(f.get('name', fid))}")
            st.caption(f.get("desc", ""))
            st.caption(f"💬 {n} post{'s' if n != 1 else ''}")
        with c2:
            st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)
            if st.button("Enter \u2192", key=f"fenter_{fid}"):
                st.session_state["forum_nav"] = {"forum": fid, "post": None}
                st.rerun()
        st.divider()


def _forum_posts_view(forums, fid):
    f = forums.get(fid, {})
    if st.button("\u2190 All forums"):
        st.session_state["forum_nav"] = {"forum": None, "post": None}
        st.rerun()
    st.markdown(f"### {f.get('icon', '💬')} {htmlmod.escape(f.get('name', fid))}")
    st.caption(f.get("desc", ""))
    can_share = bool(_wall_token())
    with st.expander("\u270f\ufe0f New post", expanded=False):
        title = st.text_input("Title", max_chars=120, key=f"npt_{fid}")
        body = st.text_area("Body", max_chars=2000, key=f"npb_{fid}")
        photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"], key=f"npp_{fid}")
        nm = st.text_input("Your name", value=st.session_state.get("wall_name", ""),
                           max_chars=30, key=f"npn_{fid}")
        if st.button("Post", key=f"nps_{fid}"):
            if not (title or "").strip() or not (body or "").strip() or not (nm or "").strip():
                st.warning("Title, body, and name \u2014 fill those in.")
            elif not can_share:
                st.warning("The forum needs the shared wall connection.")
            else:
                post = {"id": uuid.uuid4().hex[:12], "title": title.strip()[:120],
                        "body": body.strip()[:2000], "name": nm.strip()[:30],
                        "ts": time.time(), "votes": {"up": 1, "down": 0}, "comments": []}
                if photo is not None:
                    with st.spinner("Uploading photo\u2026"):
                        url = photo_upload(photo)
                    if url:
                        post["photo"] = url
                    else:
                        st.warning("Photo didn't upload \u2014 posting without it.")
                def fn(fr, _p=post):
                    fr.get(fid, {}).setdefault("posts", []).append(_p)
                if _forum_update(fn, f"Forum post in {fid}"):
                    st.session_state["wall_name"] = nm.strip()[:30]
                    st.success("Posted! \U0001f3b8")
                    st.rerun()
                else:
                    st.error("Couldn't post \u2014 try again.")
    sort = st.radio("Sort", ["\U0001f525 Hot", "\U0001f195 New", "\U0001f3c6 Top"],
                    horizontal=True, key=f"sort_{fid}")
    posts = list(f.get("posts", []))
    if sort == "\U0001f525 Hot":
        posts.sort(key=_hot, reverse=True)
    elif sort == "\U0001f195 New":
        posts.sort(key=lambda p: p.get("ts", 0), reverse=True)
    else:
        posts.sort(key=_score, reverse=True)
    if not posts:
        st.info("Nothing here yet \u2014 start the discussion. \U0001f3b8")
    profiles = _profiles()
    for p in posts:
        cc = len(p.get("comments", []))
        flair = _flair(p.get("name", ""), profiles)
        st.markdown(
            f"<div class='tool-card' style='margin-bottom:0.15rem;'>"
            f"<div style='display:flex;gap:0.6rem;align-items:baseline;'>"
            f"<b style='color:#e94560;font-size:1.05rem;'>{_score(p)}</b>"
            f"<div><b>{htmlmod.escape(p.get('title', '')[:120])}</b>"
            f"<div style='color:#8a8a9e;font-size:0.8rem;'>"
            f"{htmlmod.escape(p.get('name', '?')[:30])}{flair} \u00b7 {_ago(p.get('ts', 0))} \u00b7 "
            f"💬 {cc}</div></div></div></div>",
            unsafe_allow_html=True)
        if st.button("Open \u2192", key=f"open_{fid}_{p.get('id')}"):
            st.session_state["forum_nav"] = {"forum": fid, "post": p.get("id")}
            st.rerun()


def _comment_view(forums, fid, pid, c, profiles, depth):
    cid = c.get("id")
    flair = _flair(c.get("name", ""), profiles)
    wrap = ("<div style='margin-left:1.1rem;border-left:2px solid #3a3a4a;"
            "padding-left:0.6rem;margin-top:0.4rem;'>" if depth else "<div style='margin-top:0.4rem;'>")
    st.markdown(
        f"{wrap}<b>{htmlmod.escape(c.get('name', '?')[:30])}</b>{flair} "
        f"<span style='color:#8a8a9e;font-size:0.8rem;'>{_ago(c.get('ts', 0))}</span><br>"
        f"{htmlmod.escape(c.get('text', '')[:1000]).replace(chr(10), '<br>')}</div>",
        unsafe_allow_html=True)
    _vote_row(fid, pid, cid, c, f"cv_{cid}")
    if depth == 0:
        with st.expander("\u21a9\ufe0f Reply", expanded=False):
            rnm = st.text_input("Your name", value=st.session_state.get("wall_name", ""),
                                max_chars=30, key=f"rn_{cid}")
            rtx = st.text_input("Write a reply\u2026", max_chars=500, key=f"rt_{cid}")
            if st.button("Reply", key=f"rs_{cid}"):
                if not (rnm or "").strip() or not (rtx or "").strip():
                    st.warning("Name and reply needed.")
                elif not _wall_token():
                    st.warning("The forum needs the shared wall connection.")
                else:
                    r = {"id": uuid.uuid4().hex[:12], "name": rnm.strip()[:30],
                         "text": rtx.strip()[:500], "ts": time.time(),
                         "votes": {"up": 0, "down": 0}, "replies": []}
                    def fn(fr, _r=r):
                        post = _find_post(fr, fid, pid)
                        if post:
                            tgt, _par = _find_comment(post, cid)
                            if tgt:
                                tgt.setdefault("replies", []).append(_r)
                    if _forum_update(fn, "Forum reply"):
                        st.session_state["wall_name"] = rnm.strip()[:30]
                        st.rerun()
                    else:
                        st.error("Couldn't post \u2014 try again.")
    for r in sorted(c.get("replies", []), key=_score, reverse=True):
        _comment_view(forums, fid, pid, r, profiles, depth + 1)


def _forum_post_view(forums, fid, pid):
    p = _find_post(forums, fid, pid)
    if not p:
        st.warning("Post not found.")
        if st.button("\u2190 Back"):
            st.session_state["forum_nav"] = {"forum": fid, "post": None}
            st.rerun()
        return
    if st.button(f"\u2190 {htmlmod.escape(forums.get(fid, {}).get('name', 'Forum'))}"):
        st.session_state["forum_nav"] = {"forum": fid, "post": None}
        st.rerun()
    profiles = _profiles()
    flair = _flair(p.get("name", ""), profiles)
    st.markdown(f"## {htmlmod.escape(p.get('title', '')[:120])}")
    st.caption(f"{htmlmod.escape(p.get('name', '?')[:30])}{flair} \u00b7 {_ago(p.get('ts', 0))}")
    _vote_row(fid, pid, None, p, f"pv_{pid}")
    st.write(p.get("body", "")[:2000])
    if p.get("photo"):
        st.image(p["photo"])
    st.markdown("### 💬 Comments")
    cnm = st.text_input("Your name", value=st.session_state.get("wall_name", ""),
                        max_chars=30, key=f"cn_{pid}")
    ctxt = st.text_area("Add a comment", max_chars=1000, key=f"ct_{pid}")
    if st.button("Comment", key=f"cs_{pid}"):
        if not (cnm or "").strip() or not (ctxt or "").strip():
            st.warning("Name and comment needed.")
        elif not _wall_token():
            st.warning("The forum needs the shared wall connection.")
        else:
            c = {"id": uuid.uuid4().hex[:12], "name": cnm.strip()[:30],
                 "text": ctxt.strip()[:1000], "ts": time.time(),
                 "votes": {"up": 0, "down": 0}, "replies": []}
            def fn(fr, _c=c):
                post = _find_post(fr, fid, pid)
                if post:
                    post.setdefault("comments", []).append(_c)
            if _forum_update(fn, "Forum comment"):
                st.session_state["wall_name"] = cnm.strip()[:30]
                st.rerun()
            else:
                st.error("Couldn't post \u2014 try again.")
    for c in sorted(p.get("comments", []), key=_score, reverse=True):
        _comment_view(forums, fid, pid, c, profiles, depth=0)
        st.divider()

def page_community():
    st.markdown('<div class="hero"><h1>\U0001f918 SIX-STRING SOCIAL</h1>'
                '<p>Profiles, the wall, gigs, jobs \u0026 jam buddies \u2014 your guitar crew.</p></div>',
                unsafe_allow_html=True)
    t1, t2, t3, t4, t5 = st.tabs(["💬 Wall", "\U0001f5e8\ufe0f Forum", "\U0001f511 Join", "\U0001f464 Profiles", "\U0001f3b8 Board"])
    with t1:
        _wall_tab()
    with t2:
        _forum_tab()
    with t3:
        _join_tab()
    with t4:
        _profiles_tab()
    with t5:
        _board_tab()
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------


def sgt_bubble():
    """Floating utility widget: tuner + social mini-feed + Sgt. Martin tutor.
    Gmail-style persistent panel. Tuner state lives on the parent window so
    the mic survives Streamlit reruns and can always be stopped."""
    if not st.session_state.get("instructor_on", True):
        return
    _thw = _tuner_html("wt")
    _tjw = _tuner_js("wt", "P._sgtT2", "d", "P.window", "P.requestAnimationFrame",
                     "P.navigator",
                     "P._sgtT2=P._sgtT2||{running:false,sel:0,stream:null,ctx:null,an:null,buf:null,okSince:0,refCtx:null};")
    html = """<script>
(function() {
var d = window.parent.document;
var P = window.parent;
if (d.getElementById('sgt-root')) return;
var PORTRAIT = "https://raw.githubusercontent.com/erikmartin-dev/Six-String-Bootcamp/main/assets/sgt-martin/portrait.webp";
var TALKING = "https://raw.githubusercontent.com/erikmartin-dev/Six-String-Bootcamp/main/assets/sgt-martin/talking.mp4";
var WALL_URL = "https://raw.githubusercontent.com/erikmartin-dev/Six-String-Bootcamp/main/community/wall.json";

var KB = [
{k:['hello','hey','howdy','morning','evening'], a:"Recruit! Sgt. Martin reporting. Ask me about tuning, chords, practice \u2014 anything guitar. What is the mission?"},
{k:['tune','tuning','tuner'], a:"Standard tuning, low to high: E \u2013 A \u2013 D \u2013 G \u2013 B \u2013 e. This widget has a tuner built in \u2014 hit the Tuner tab and get every string dead center."},
{k:['string names','strings named','note names','names of the strings'], a:"Low to high: E, A, D, G, B, e. The old-timers say: 'Eddie Ate Dynamite, Good Bye Eddie.' Say it until it is reflex."},
{k:['e minor','first chord','easy chord','em chord'], a:"Your first chord: E minor. Pointer finger, 5th string 2nd fret. Bird finger, 4th string 2nd fret. Strum all six. That is Lesson 1 \u2014 go earn the badge."},
{k:['finger names','fingers called','which finger'], a:"Pointer finger, bird finger, ring finger, pinky \u2014 and the thumb rides behind the neck. Say it like you mean it, recruit."},
{k:['grabbing the chord','grab the chord'], a:"Grabbing the chord: do not place fingers one at a time like you are defusing a bomb. Move your whole hand as a unit and grab the shape at once. Slow is smooth, smooth is fast."},
{k:['practice','how long','routine','how often'], a:"Twenty-five focused minutes beats two distracted hours. Tune up, drill one thing, play one song. Every day you show up, the fingers get smarter."},
{k:['pentatonic'], a:"The pentatonic scale \u2014 five notes that sound good over everything. We build it one position per lesson, then connect the boxes and solo with purpose. It is the spine of the whole course."},
{k:['barre'], a:"Barre chords: your pointer finger becomes a capo. E-shape first, A-shape after. They hurt for two weeks, then they are yours forever. Lessons 9 and 10."},
{k:['capo'], a:"A capo clamps across the fretboard and moves everything up \u2014 play G-shape chords but sound in A. Full briefing in Lesson 12."},
{k:['power chord','powerchord'], a:"Power chords: pointer finger plus ring finger, two strings, all attitude. The backbone of rock. Lesson 8."},
{k:['strum','strumming'], a:"Strumming that sings: loose wrist, brush the strings, accents on the beat. Lesson 5 turns metronome prisoners into groove players."},
{k:['solo','lead guitar'], a:"Soloing with purpose: it is not how many notes, it is which ones and when. Pentatonic positions plus phrasing. Lesson 11."},
{k:['gear','which guitar','starter guitar','buy a guitar'], a:"Erik's pick: the Cort starter pack \u2014 around a hundred bucks with a gig bag and picks, sounds great, plays easy. Check the Gear tab."},
{k:['course','lessons','curriculum','learn guitar'], a:"Twelve lessons, song-first: you play a real song in Lesson 1, then we backfill tuning, technique, and theory. Pentatonic all the way through. Hit Courses to enlist."},
{k:['badge'], a:"Badges are proof of progress \u2014 pass the practice, claim the badge, and it auto-posts to Six-String Social for the world to see. Collect all twelve."},
{k:['forum','social','community'], a:"Six-String Social: the wall, five forums, profiles, and the gig board \u2014 and the Social tab of this very widget keeps the wall one tap away."},
{k:['gig','setlist'], a:"The Gigs tab builds your setlists. The Social board's gig section finds you players and venues. Play out as soon as you can \u2014 nothing teaches like a crowd."},
{k:['metronome'], a:"The metronome is your drill sergeant's drum. Tools tab \u2014 start slow, lock in, then speed up. If you cannot play it slow, you cannot play it fast."},
{k:['ear trainer','pitch','singing'], a:"Ear Trainer in the Tools tab: hear the note, sing it back, get scored. Five minutes a day and your ears start doing the work for you."},
{k:['thank'], a:"Do not thank me \u2014 thank your calluses. Now get back to the fretboard."},
{k:['who are you','your name','sgt martin'], a:"Sgt. Martin. AI tutor, guitar division. I run the drills; Erik wrote the playbook."},
{k:['hard','difficult','giving up','frustrat','i suck','too hard'], a:"Every guitarist sounded terrible at first \u2014 every single one. The ones who got good are the ones who did not quit in week three. Keep going."},
{k:['callus','fingers hurt','finger pain','sore fingers'], a:"Sore fingertips are tuition \u2014 they harden in a week or two. Short sessions, press just behind the fret, never play through sharp pain."},
{k:['tablature','tabs','read music','sheet music'], a:"Tabs live in the Songs tab \u2014 the lines are your strings, the numbers are frets. Chords ride above the lyrics; tablature gets its own button."}
];
var FALLBACK = "That is above my pay grade, recruit. Post it in the Beginner Questions forum \u2014 the community will square you away.";

var css = "#sgt-bubble{position:fixed;right:18px;bottom:18px;width:64px;height:64px;border-radius:50%;"
+"border:3px solid #e94560;cursor:pointer;z-index:99999;overflow:hidden;background:#16213e;"
+"box-shadow:0 4px 18px rgba(233,69,96,.45);animation:sgt-pulse 2.4s infinite;padding:0;}"
+"#sgt-bubble img{width:100%;height:100%;object-fit:cover;display:block;}"
+"@keyframes sgt-pulse{0%,100%{box-shadow:0 4px 18px rgba(233,69,96,.45);}50%{box-shadow:0 4px 28px rgba(233,69,96,.85);}}"
+"#sgt-panel{position:fixed;right:18px;bottom:94px;width:340px;max-width:calc(100vw - 36px);height:480px;"
+"max-height:calc(100vh - 130px);background:#141422;border:1px solid #2a2a3e;border-radius:16px;z-index:99999;"
+"display:none;flex-direction:column;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,.6);font-family:Inter,sans-serif;}"
+"#sgt-head{display:flex;align-items:center;gap:10px;padding:10px 12px;background:#1a1a2e;border-bottom:1px solid #2a2a3e;}"
+"#sgt-head img{width:40px;height:40px;border-radius:50%;object-fit:cover;border:2px solid #e94560;}"
+"#sgt-head b{color:#fff;font-size:14px;display:block;}"
+"#sgt-head span{color:#8a8a9e;font-size:11px;display:block;}"
+"#sgt-x{margin-left:auto;background:none;border:none;color:#8a8a9e;font-size:16px;cursor:pointer;}"
+"#sgt-tabs{display:flex;border-bottom:1px solid #2a2a3e;}"
+"#sgt-tabs button{flex:1;background:none;border:none;color:#8a8a9e;padding:10px 4px;font-size:12.5px;cursor:pointer;border-bottom:2px solid transparent;}"
+"#sgt-tabs button.on{color:#e94560;border-bottom-color:#e94560;font-weight:bold;}"
+".sgt-body{display:none;flex-direction:column;flex:1;min-height:0;overflow:hidden;}"
+"#sgt-msgs{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;}"
+".sgt-msg{max-width:85%;padding:8px 12px;border-radius:14px;font-size:13.5px;line-height:1.45;color:#eee;}"
+".sgt-user{align-self:flex-end;background:#e94560;border-bottom-right-radius:4px;}"
+".sgt-bot{align-self:flex-start;background:#1f1f33;border-bottom-left-radius:4px;}"
+".sgt-typing span{width:7px;height:7px;background:#8a8a9e;border-radius:50%;display:inline-block;margin-right:4px;animation:sgt-blink 1.2s infinite;}"
+".sgt-typing span:nth-child(2){animation-delay:.2s;}.sgt-typing span:nth-child(3){animation-delay:.4s;}"
+"@keyframes sgt-blink{0%,100%{opacity:.3;}50%{opacity:1;}}"
+"#sgt-chips{display:flex;gap:6px;padding:0 12px 8px;flex-wrap:wrap;}"
+"#sgt-chips button{background:#1f1f33;border:1px solid #2a2a3e;color:#e94560;border-radius:20px;padding:5px 10px;font-size:12px;cursor:pointer;}"
+"#sgt-inputrow{display:flex;gap:8px;padding:10px 12px;border-top:1px solid #2a2a3e;}"
+"#sgt-in{flex:1;background:#1f1f33;border:1px solid #2a2a3e;border-radius:20px;padding:8px 14px;color:#fff;font-size:13px;outline:none;}"
+"#sgt-send{background:#e94560;border:none;border-radius:50%;width:36px;height:36px;color:#fff;font-size:15px;cursor:pointer;}"
+"#sgt-social-feed{flex:1;overflow-y:auto;padding:4px 14px;}"
+"#sgt-social-foot{display:flex;align-items:center;gap:10px;padding:10px 14px;border-top:1px solid #2a2a3e;}"
+"#sgt-refresh{background:#1f1f33;border:1px solid #2a2a3e;color:#e94560;border-radius:20px;padding:6px 12px;font-size:12px;cursor:pointer;}"
+"#sgt-open{margin-left:auto;color:#e94560;font-size:12.5px;text-decoration:none;}";
var root = d.createElement('div');
root.id = 'sgt-root';
root.innerHTML = '<style>' + css + '</style>'
 + '<div id="sgt-bubble" title="Tuner \u00b7 Social \u00b7 Sgt. Martin"><img src="' + PORTRAIT + '"></div>'
 + '<div id="sgt-panel">'
 + '<div id="sgt-head"><img src="' + PORTRAIT + '"><div><b>SIX-STRING</b><span>tuner \u00b7 social \u00b7 AI tutor</span></div><button id="sgt-x">\u2715</button></div>'
 + '<div id="sgt-tabs">'
 + '<button id="sgt-tab-tuner" class="on">🎵 Tuner</button>'
 + '<button id="sgt-tab-social">💬 Social</button>'
 + '<button id="sgt-tab-martin">🤖 Martin</button>'
 + '</div>'
+ '<div id="sgt-body-tuner" class="sgt-body" style="display:flex;overflow-y:auto;">' + %%TUNERHTML%% + '</div>'
 + '<div id="sgt-body-social" class="sgt-body">'
 + '<div id="sgt-social-feed"></div>'
 + '<div id="sgt-social-foot"><button id="sgt-refresh">🔄 Refresh</button>'
 + '<a id="sgt-open" href="?view=social">Open Six-String Social \u2192</a></div>'
 + '</div>'
 + '<div id="sgt-body-martin" class="sgt-body">'
 + '<div id="sgt-msgs"></div><div id="sgt-chips"></div>'
 + '<div id="sgt-inputrow"><input id="sgt-in" placeholder="Ask about guitar..." autocomplete="off">'
 + '<button id="sgt-send">\u27a4</button></div>'
 + '</div>'
 + '</div>';
d.body.appendChild(root);
/* ---------- tabs ---------- */
var socialLoaded = false, martinGreeted = false;
function showTab(which) {
  ['tuner','social','martin'].forEach(function(t) {
    d.getElementById('sgt-body-'+t).style.display = (t === which ? 'flex' : 'none');
    var tab = d.getElementById('sgt-tab-'+t);
    if (tab) { if (t === which) tab.classList.add('on'); else tab.classList.remove('on'); }
  });
  if (which === 'social' && !socialLoaded) { socialLoaded = true; loadSocial(); }
  if (which === 'martin' && !martinGreeted) {
    martinGreeted = true;
    addMsg('bot', "Recruit! Sgt. Martin here \u2014 AI tutor, guitar division. Ask me about tuning, chords, practice, anything. What is the mission?");
  }
}
d.getElementById('sgt-tab-tuner').onclick = function(){ showTab('tuner'); };
d.getElementById('sgt-tab-social').onclick = function(){ showTab('social'); };
d.getElementById('sgt-tab-martin').onclick = function(){ showTab('martin'); };
%%TUNERJS%%
/* ---------- social mini-feed ---------- */
function esc(s){ return String(s == null ? '' : s).replace(/</g, '&lt;'); }
function loadSocial() {
  var box = d.getElementById('sgt-social-feed');
  box.innerHTML = '<div style="color:#8a8a9e;font-size:12px;padding:12px 0;">loading\u2026</div>';
  P.fetch(WALL_URL + '?t=' + Date.now()).then(function(r){ return r.json(); }).then(function(data) {
    var posts = (data.posts || []).slice().sort(function(a,b){ return (b.ts||0)-(a.ts||0); }).slice(0, 5);
    if (!posts.length) { box.innerHTML = '<div style="color:#8a8a9e;font-size:12px;padding:12px 0;">Quiet in here\u2026</div>'; return; }
    box.innerHTML = posts.map(function(p) {
      var when = new Date((p.ts||0)*1000).toLocaleDateString(undefined, {month:'short', day:'numeric'});
      return '<div style="padding:9px 0;border-bottom:1px solid #2a2a3e;">'
        + '<div style="font-size:12px;color:#e94560;font-weight:bold;">' + esc((p.name||'?').slice(0,20))
        + ' <span style="color:#8a8a9e;font-weight:normal;">\u00b7 ' + when + '</span></div>'
        + '<div style="font-size:12.5px;color:#ddd;margin-top:2px;">' + esc((p.text||'').slice(0,110)) + '</div></div>';
    }).join('');
  }).catch(function(){ box.innerHTML = '<div style="color:#8a8a9e;font-size:12px;padding:12px 0;">could not load</div>'; });
}
d.getElementById('sgt-refresh').onclick = function(){ loadSocial(); };
/* ---------- martin chat ---------- */
var msgs = d.getElementById('sgt-msgs');
function addMsg(who, text) {
  var div = d.createElement('div');
  div.className = 'sgt-msg sgt-' + who;
  div.textContent = text;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}
function sgtReply(q) {
  var ql = q.toLowerCase(), best = null, bestScore = 0;
  KB.forEach(function(item) {
    var s = 0;
    item.k.forEach(function(kw) {
      try { if (ql.match(new RegExp('\\b' + kw + 's?\\b'))) s++; } catch(e) {}
    });
    if (s > bestScore) { bestScore = s; best = item; }
  });
  return best ? best.a : FALLBACK;
}
function setTalking(on) {
  var b = d.getElementById('sgt-bubble');
  if (on) {
    b.innerHTML = '<video autoplay muted loop playsinline style="width:100%;height:100%;object-fit:cover;display:block;">'
      + '<source src="' + TALKING + '" type="video/mp4"></video>';
  } else {
    b.innerHTML = '<img src="' + PORTRAIT + '">';
  }
}
function send(preset) {
  var inp = d.getElementById('sgt-in');
  var q = (preset !== undefined ? preset : inp.value).trim();
  if (!q) return;
  addMsg('user', q);
  inp.value = '';
  var t = d.createElement('div');
  t.className = 'sgt-msg sgt-bot sgt-typing';
  t.innerHTML = '<span></span><span></span><span></span>';
  msgs.appendChild(t);
  msgs.scrollTop = msgs.scrollHeight;
  setTalking(true);
  setTimeout(function() {
    if (t.parentNode) t.parentNode.removeChild(t);
    setTalking(false);
    addMsg('bot', sgtReply(q));
  }, 900 + Math.random()*900);
}
d.getElementById('sgt-bubble').onclick = function() {
  var p = d.getElementById('sgt-panel');
  var open = p.style.display === 'none' || !p.style.display;
  p.style.display = open ? 'flex' : 'none';
};
d.getElementById('sgt-x').onclick = function() { d.getElementById('sgt-panel').style.display = 'none'; };
d.getElementById('sgt-send').onclick = function() { send(); };
d.getElementById('sgt-in').addEventListener('keydown', function(e) { if (e.key === 'Enter') send(); });
[["Tune my guitar","how do i tune my guitar"],["Teach me Em","teach me e minor"],["Practice tips","practice tips"]].forEach(function(c) {
  var b = d.createElement('button');
  b.textContent = c[0];
  b.onclick = function() { showTab('martin'); send(c[1]); };
  d.getElementById('sgt-chips').appendChild(b);
});
})();
</script>"""
    html = html.replace("%%TUNERHTML%%", json.dumps(_thw)).replace("%%TUNERJS%%", _tjw)
    components.html(html, height=0, scrolling=False)
# Standalone Six-String Social mode. social.py sets SIXSTRING_SOCIAL=1 and then
# imports this module: same community data, its own front door, no bootcamp chrome.
# ----------------------------------------------------------------------------
if os.environ.get("SIXSTRING_SOCIAL") == "1":
    page_community()
    sgt_bubble()
    st.stop()


# Router — top button nav, no sidebar. No entrance gate: the app opens
# straight onto the nav + Home.
# ----------------------------------------------------------------------------
NAV = [
    ("🏠", "Home"), ("🎵", "Songs"), ("🔍", "Find Songs"), ("💾", "Saved"),
    ("🎤", "Gigs"), ("📚", "Learn"), ("🎓", "Courses"), ("💳", "Membership"),
    ("🧰", "Tools"), ("🎸", "Gear"), ("🏆", "Collection"),
    ("💬", "Social"),
]
PAGES = {
    "Home": page_home, "Songs": page_songs, "Find Songs": find_songs_page,
    "Saved": page_saved, "Gigs": page_gigs, "Learn": page_learn,
    "Courses": page_courses, "Membership": page_membership, "Tools": page_tools,
    "Gear": page_gear, "Collection": page_collection,
    "Social": page_community,
}

def _goto(page):
    """Navigate like a new page: switch section and jump to its top."""
    st.session_state["page"] = page
    st.session_state["_jump"] = True


# Deep links for one-tap home-screen shortcuts: ?view=tuner|metronome|ear
_DEEP_LINKS = {"tuner": ("Tools", "tool-tuner"), "metronome": ("Tools", "tool-metronome"),
               "ear": ("Tools", "tool-ear"), "tools": ("Tools", None),
               "community": ("Social", None), "social": ("Social", None)}
if "page" not in st.session_state:
    st.session_state["page"] = "Home"
    try:
        _view = str(st.query_params.get("view", "")).strip().lower()
    except Exception:
        _view = ""
    if _view in _DEEP_LINKS:
        st.session_state["page"], st.session_state["_scroll_to"] = _DEEP_LINKS[_view]

# Compact single-row pill nav (sticky on phones): one short row instead of two
# tall button rows, so each section's header + content start on the same
# screen. The pill row scrolls horizontally; the active section is highlighted.
_NAV_ICON = {name: icon for icon, name in NAV}
_PILL_LABELS = [f"{icon} {name}" for icon, name in NAV]
_PILL_TO_PAGE = {f"{icon} {name}": name for icon, name in NAV}

_current_page = st.session_state["page"]
# Keep the pill selection in sync when navigation happens somewhere other
# than the pills (home cards, deep links): set the widget state BEFORE it
# instantiates. The _pills_for tracker tells an external nav apart from the
# user tapping a pill (in which case we must NOT overwrite their tap).
if st.session_state.get("_pills_for") != _current_page:
    st.session_state["nav_pills"] = f"{_NAV_ICON.get(_current_page, '')} {_current_page}".strip()
    st.session_state["_pills_for"] = _current_page
_choice = st.pills("Browse sections", options=_PILL_LABELS, key="nav_pills",
                   label_visibility="collapsed", selection_mode="single",
                   default=_PILL_LABELS[0])
if _choice:
    _chosen_page = _PILL_TO_PAGE.get(_choice)
    if _chosen_page and _chosen_page != _current_page:
        st.session_state["page"] = _chosen_page
        st.session_state["_pills_for"] = _chosen_page
        st.session_state["_jump"] = True
        # No st.rerun(): the pill tap already triggered this rerun.

if st.session_state.pop("_jump", False):
    # Jump to the top of the new section so a tap feels like a new page.
    # Scroll EVERY candidate container: Streamlit's actual scroller varies by
    # version, and scrolling only the first match silently no-ops when that
    # element isn't the scroller (users were left staring at the bottom of
    # the new page). The scroll repeats on short delays because the old
    # scroll offset can be restored after the rerun, undoing a single early
    # scroll. The page name is embedded so the iframe remounts and the script
    # re-runs on every navigation.
    _nav_token = str(st.session_state.get("page", "home")).replace("*/", "")
    components.html(
        "<script>(function(){/*nav:" + _nav_token + "*/"
        "var d=window.parent.document;"
        "var sels=['[data-testid=\"stAppViewContainer\"]',"
        "'[data-testid=\"stMain\"]','section.main','.main'];"
        "function go(){"
        "for(var i=0;i<sels.length;i++){"
        "var els=d.querySelectorAll(sels[i]);"
        "for(var j=0;j<els.length;j++){"
        "try{if(els[j].scrollTo){els[j].scrollTo(0,0);}else{els[j].scrollTop=0;}}catch(e){}}}"
        "try{window.parent.scrollTo(0,0);}catch(e){}"
        "try{d.documentElement.scrollTop=0;d.body.scrollTop=0;}catch(e){}"
        "}"
        "go();setTimeout(go,600);setTimeout(go,1500);"
        "})();</script>",
        height=0, scrolling=False)

PAGES.get(st.session_state["page"], page_home)()
sgt_bubble()

_scroll_target = st.session_state.pop("_scroll_to", None)
if _scroll_target:
    # Deep link: land directly on the requested tool.
    components.html(
        "<script>(function(){var d=window.parent.document;"
        f"var el=d.getElementById('{_scroll_target}');"
        "if(el){el.scrollIntoView({block:'start'});}})();</script>",
        height=0, scrolling=False)

st.markdown("---")
st.caption("Six-String Bootcamp · Practice daily, recruit.")
