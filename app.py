


try:
    st.set_page_config(
        page_title="Six String Boot Camp",
        page_icon="🎸",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
except Exception:
    pass

# CUSTOM CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        text-align: center;
        padding: 2.5rem 0;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 20px;
        margin-bottom: 2rem;
        border: 1px solid rgba(233, 69, 96, 0.2);
    }
</style>
""", unsafe_allow_html=True)

    /* FIXED: Added a dot before main-header */
    .main-header {
        text-align: center;
        padding: 2.5rem 0;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 20px;
        margin-bottom: 2rem;
        border: 1px solid rgba(233, 69, 96, 0.2);
    }

    .main-header h1 {
        color: #e94560;
        font-size: 3.2rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -2px;
        text-shadow: 0 0 30px rgba(233, 69, 96, 0.3);
    }

    .main-header p {
        color: #a0a0a0;
        font-size: 1.15rem;
        margin-top: 0.5rem;
        font-weight: 300;
    }

    .tool-card {
        background: linear-gradient(145deg, #16213e, #0f3460);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(233, 69, 96, 0.1);
        transition: all 0.3s ease;
        height: 100%;
    }

    .tool-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 12px 32px rgba(233, 69, 96, 0.2);
        border-color: rgba(233, 69, 96, 0.3);
    }

    .stButton>button {
        background: linear-gradient(90deg, #e94560, #ff6b6b) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }

    .stButton>button:hover {
        transform: scale(1.03) !important;
        box-shadow: 0 6px 20px rgba(233, 69, 96, 0.4) !important;
    }

    .lesson-card {
        background: linear-gradient(145deg, #16213e, #1a1a2e);
        border-left: 4px solid #e94560;
        border-radius: 0 14px 14px 0;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }

    .lesson-card:hover {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border-left-width: 6px;
    }

    .lesson-card.free {
        border-left-color: #4ade80;
    }

    .song-card {
        background: linear-gradient(145deg, #16213e, #0f3460);
        border-radius: 14px;
        padding: 1.25rem;
        border: 1px solid rgba(15, 52, 96, 0.5);
        transition: all 0.3s ease;
        height: 100%;
    }

    .song-card:hover {
        border-color: rgba(233, 69, 96, 0.3);
        transform: translateY(-4px);
    }

    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.4rem;
    }

    .badge-beginner { background: rgba(74, 222, 128, 0.15); color: #4ade80; }
    .badge-intermediate { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }
    .badge-advanced { background: rgba(233, 69, 96, 0.15); color: #e94560; }
    .badge-rock { background: rgba(139, 92, 246, 0.15); color: #a78bfa; }
    .badge-pop { background: rgba(236, 72, 153, 0.15); color: #f472b6; }
    .badge-folk { background: rgba(34, 197, 94, 0.15); color: #4ade80; }

def generate_fretboard_svg(highlight_notes, title=None, fret_spacing=40, string_spacing=20, highlight_color="#e94560"):
    # Initialize your SVG base container string here
    # Example starting tag: svg = '<svg width="300" height="150" ...>'
    svg = "" 

    for note_info in highlight_notes:
        string_idx = note_info.get("string", 0)
        fret = note_info.get("fret", 0)
        note_name = note_info.get("note", "")
        finger = note_info.get("finger", "")

        # Offset notes so open/muted strings reside to the left of the nut
        x = (fret + 0.5) * fret_spacing if fret > 0 else 25 
        y = 12 + string_idx * string_spacing

        if fret == 0:
            svg += f'<circle cx="{x}" cy="{y}" r="11" fill="none" stroke="{highlight_color}" stroke-width="2.5"/>'
            svg += f'<text x="{x}" y="{y+4}" text-anchor="middle" fill="{highlight_color}" font-size="10" font-weight="bold" font-family="Inter, sans-serif">{note_name}</text>'
        elif fret == -1:
            svg += f'<text x="{x}" y="{y+5}" text-anchor="middle" fill="#888" font-size="14" font-weight="bold" font-family="Inter, sans-serif">✕</text>'
        else:
            svg += f'<circle cx="{x}" cy="{y}" r="13" fill="{highlight_color}" opacity="0.95"/>'
            svg += f'<text x="{x}" y="{y+4}" text-anchor="middle" fill="white" font-size="10" font-weight="bold" font-family="Inter, sans-serif">{note_name}</text>'
            if finger:
                svg += f'<text x="{x}" y="{y+22}" text-anchor="middle" fill="#e94560" font-size="9" font-family="Inter, sans-serif">{finger}</text>'

    # Fixed label collision by shifting text x-axis position back to x="8"
    string_labels = ["e", "B", "G", "D", "A", "E"]
    for i, label in enumerate(string_labels):
        y = 12 + i * string_spacing
        svg += f'<text x="8" y="{y+4}" text-anchor="middle" fill="#888" font-size="11" font-weight="600" font-family="Inter, sans-serif">{label}</text>'

    svg += '</svg>'

    if title:
        return f'<div class="fretboard-container"><p style="color: #e94560; font-weight: 600; margin-bottom: 0.5rem; font-size: 1.1rem;">{title}</p>{svg}</div>'
    return f'<div class="fretboard-container">{svg}</div>'


# ============================================
# DATA structures cleaned of bad spaces
# 
CHORD_SHAPES = {
    "C Major": {
        "ascii": "e|--0--|\nB|--1--|\nG|--0--|\nD|--2--|\nA|--3--|\nE|--x--|",
        "svg_notes": [
            {"string": 0, "fret": 0, "note": "E"},
            {"string": 1, "fret": 1, "note": "C", "finger": "1"},
            {"string": 2, "fret": 0, "note": "G"},
            {"string": 3, "fret": 2, "note": "E", "finger": "2"},
            {"string": 4, "fret": 3, "note": "C", "finger": "3"},
            {"string": 5, "fret": -1, "note": "X"}
        ]
    },
    "G Major": {
        "ascii": "e|--3--|\nB|--0--|\nG|--0--|\nD|--0--|\nA|--2--|\nE|--3--|",
        "svg_notes": [
            {"string": 0, "fret": 3, "note": "G", "finger": "4"},
            {"string": 1, "fret": 0, "note": "B"},
            {"string": 2, "fret": 0, "note": "G"},
            {"string": 3, "fret": 0, "note": "D"},
            {"string": 4, "fret": 2, "note": "B", "finger": "2"},
            {"string": 5, "fret": 3, "note": "G", "finger": "3"}
        ]
    },
    "D Major": {
        "ascii": "e|--2--|\nB|--3--|\nG|--2--|\nD|--0--|\nA|--x--|\nE|--x--|",
        "svg_notes": [
            {"string": 0, "fret": 2, "note": "F#", "finger": "2"},
            {"string": 1, "fret": 3, "note": "D", "finger": "3"},
            {"string": 2, "fret": 2, "note": "A", "finger": "1"},
            {"string": 3, "fret": 0, "note": "D"},
            {"string": 4, "fret": -1, "note": "X"},
            {"string": 5, "fret": -1, "note": "X"}
        ]
    },
    "A Major": {
        "ascii": "e|--0--|\nB|--2--|\nG|--2--|\nD|--2--|\nA|--0--|\nE|--x--|",
        "svg_notes": [
            {"string": 0, "fret": 0, "note": "E"},
            {"string": 1, "fret": 2, "note": "C#", "finger": "2"},
            {"string": 2, "fret": 2, "note": "A", "finger": "3"},
            {"string": 3, "fret": 2, "note": "E", "finger": "1"},
            {"string": 4, "fret": 0, "note": "A"},
            {"string": 5, "fret": -1, "note": "X"}
        ]
    }
}
def generate_fretboard_svg(highlight_notes, title=None, fret_spacing=40, string_spacing=20, highlight_color="#e94560"):
    # Initialize your SVG base container string here
    # Example starting tag: svg = '<svg width="300" height="150" ...>'
    svg = "" 

    for note_info in highlight_notes:
        string_idx = note_info.get("string", 0)
        fret = note_info.get("fret", 0)
        note_name = note_info.get("note", "")
        finger = note_info.get("finger", "")

        # Offset notes so open/muted strings reside to the left of the nut
        x = (fret + 0.5) * fret_spacing if fret > 0 else 25 
        y = 12 + string_idx * string_spacing

        if fret == 0:
            svg += f'<circle cx="{x}" cy="{y}" r="11" fill="none" stroke="{highlight_color}" stroke-width="2.5"/>'
            svg += f'<text x="{x}" y="{y+4}" text-anchor="middle" fill="{highlight_color}" font-size="10" font-weight="bold" font-family="Inter, sans-serif">{note_name}</text>'
        elif fret == -1:
            svg += f'<text x="{x}" y="{y+5}" text-anchor="middle" fill="#888" font-size="14" font-weight="bold" font-family="Inter, sans-serif">✕</text>'
        else:
            svg += f'<circle cx="{x}" cy="{y}" r="13" fill="{highlight_color}" opacity="0.95"/>'
            svg += f'<text x="{x}" y="{y+4}" text-anchor="middle" fill="white" font-size="10" font-weight="bold" font-family="Inter, sans-serif">{note_name}</text>'
            if finger:
                svg += f'<text x="{x}" y="{y+22}" text-anchor="middle" fill="#e94560" font-size="9" font-family="Inter, sans-serif">{finger}</text>'

    # Fixed label collision by shifting text x-axis position back to x="8"
    string_labels = ["e", "B", "G", "D", "A", "E"]
    for i, label in enumerate(string_labels):
        y = 12 + i * string_spacing
        svg += f'<text x="8" y="{y+4}" text-anchor="middle" fill="#888" font-size="11" font-weight="600" font-family="Inter, sans-serif">{label}</text>'

    svg += '</svg>'

    if title:
        return f'<div class="fretboard-container"><p style="color: #e94560; font-weight: 600; margin-bottom: 0.5rem; font-size: 1.1rem;">{title}</p>{svg}</div>'
    return f'<div class="fretboard-container">{svg}</div>'


# ============================================
# DATA structures cleaned of bad spaces
# 
CHORD_SHAPES = {
    "C Major": {
        "ascii": "e|--0--|\nB|--1--|\nG|--0--|\nD|--2--|\nA|--3--|\nE|--x--|",
        "svg_notes": [
            {"string": 0, "fret": 0, "note": "E"},
            {"string": 1, "fret": 1, "note": "C", "finger": "1"},
            {"string": 2, "fret": 0, "note": "G"},
            {"string": 3, "fret": 2, "note": "E", "finger": "2"},
            {"string": 4, "fret": 3, "note": "C", "finger": "3"},
            {"string": 5, "fret": -1, "note": "X"}
        ]
    },
    "G Major": {
        "ascii": "e|--3--|\nB|--0--|\nG|--0--|\nD|--0--|\nA|--2--|\nE|--3--|",
        "svg_notes": [
            {"string": 0, "fret": 3, "note": "G", "finger": "4"},
            {"string": 1, "fret": 0, "note": "B"},
            {"string": 2, "fret": 0, "note": "G"},
            {"string": 3, "fret": 0, "note": "D"},
            {"string": 4, "fret": 2, "note": "B", "finger": "2"},
            {"string": 5, "fret": 3, "note": "G", "finger": "3"}
        ]
    },
    "D Major": {
        "ascii": "e|--2--|\nB|--3--|\nG|--2--|\nD|--0--|\nA|--x--|\nE|--x--|",
        "svg_notes": [
            {"string": 0, "fret": 2, "note": "F#", "finger": "2"},
            {"string": 1, "fret": 3, "note": "D", "finger": "3"},
            {"string": 2, "fret": 2, "note": "A", "finger": "1"},
            {"string": 3, "fret": 0, "note": "D"},
            {"string": 4, "fret": -1, "note": "X"},
            {"string": 5, "fret": -1, "note": "X"}
        ]
    },
    "A Major": {
        "ascii": "e|--0--|\nB|--2--|\nG|--2--|\nD|--2--|\nA|--0--|\nE|--x--|",
        "svg_notes": [
            {"string": 0, "fret": 0, "note": "E"},
            {"string": 1, "fret": 2, "note": "C#", "finger": "2"},
            {"string": 2, "fret": 2, "note": "A", "finger": "3"},
            {"string": 3, "fret": 2, "note": "E", "finger": "1"},
            {"string": 4, "fret": 0, "note": "A"},
            {"string": 5, "fret": -1, "note": "X"}
        ]
    }
}
