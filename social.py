"""Six-String Social — standalone community app.

Same community data as the Bootcamp (shared community/*.json in this repo),
its own front door. Deploy as a separate Streamlit Cloud app with this file
as the entry point, and copy the app secrets (github_token, member_key) over.
"""
import os

os.environ["SIXSTRING_SOCIAL"] = "1"

import app  # noqa: F401  -- renders the social UI
