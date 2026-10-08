# 🎸 Six-String Bootcamp

An interactive app that teaches you the fundamentals of guitar. Chat with an
AI tutor, tune up, browse songs, and keep time — then go deeper with
structured courses.

## Features

- 🤖 **AI guitar tutor** — a conversational agent that teaches guitar
  fundamentals step by step
- 🎛️ **Free chromatic tuner** — tune up right in the app
- 🎵 **Song database** — browse songs to learn and practice
- ⏱️ **Metronome** — keep steady time while you practice
- 🎓 **12 structured courses** — buy once or join with a monthly membership

## Tech stack

- **App:** Python + Streamlit
- **AI tutor:** Anthropic / Google Generative AI, ElevenLabs (voice)
- **Audio:** Librosa, PyAudio
- **Payments:** Stripe · **Backend:** Firebase

## Getting started

### Prerequisites

- Python 3.9+
- A microphone (for the tuner)

### Installation

```bash
git clone https://github.com/erikmartin-dev/Six-String-Bootcamp.git
cd Six-String-Bootcamp
pip install -r requirements.txt
streamlit run app.py
```

### Configuration

The app needs API keys (AI provider, ElevenLabs, Stripe, Firebase).
Put them in `.streamlit/secrets.toml` (local) or your hosting provider's
secret manager. **Never commit API keys to the repo.**

## Project structure

```
├── app.py                  # Main Streamlit app
├── requirements.txt        # Python dependencies
├── .streamlit/config.toml  # Streamlit configuration
├── .devcontainer/          # Dev container setup
└── .github/workflows/      # CI workflows
```

## License

All rights reserved.
