import random
import uuid
from datetime import datetime, timezone

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

from stories import STORIES

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Empathy Response Evaluation / הערכת תגובות אמפתיה",
    page_icon="💬",
    layout="centered",
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SHEET_KEY = "1hoHJpX8M3763kI28bGOS0JH2CdTyWmB2Y-0pmhTYJHU"
WORKSHEET_NAME = "responses"
RANK_OPTIONS = ["", "1 — הכי טוב / Best", "2", "3 — הכי פחות טוב / Worst"]


# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_worksheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_KEY)
    try:
        ws = sheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(WORKSHEET_NAME, rows=500, cols=20)
        ws.append_row([
            "timestamp", "session_id", "evaluator_name",
            "story_id",
            "rank_A", "rank_B", "rank_C",
            "cond_A", "cond_B", "cond_C",
        ])
    return ws


def save_responses(session_id: str, evaluator_name: str, rankings: list[dict], label_maps: list[dict]):
    ws = get_worksheet()
    rows = []
    for i, story in enumerate(STORIES):
        lm = label_maps[i]
        r = rankings[i]
        rows.append([
            datetime.now(timezone.utc).isoformat(),
            session_id,
            evaluator_name,
            story["id"],
            r["A"], r["B"], r["C"],
            lm["A"], lm["B"], lm["C"],
        ])
    ws.append_rows(rows, value_input_option="RAW")


# ── SESSION INIT ──────────────────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.session_id = str(uuid.uuid4())[:8]
    st.session_state.submitted = False
    # Per-story randomized mapping: which condition (H/B/F) is behind label A/B/C
    st.session_state.label_maps = [
        dict(zip(["A", "B", "C"], random.sample(["H", "B", "F"], 3)))
        for _ in STORIES
    ]
    # Default rank selections: empty per story per label
    st.session_state.rankings = [{"A": "", "B": "", "C": ""} for _ in STORIES]


# ── HEADER ────────────────────────────────────────────────────────────────────
st.title("הערכת תגובות אמפתיה / Empathy Response Evaluation")
st.markdown("""
**עברית:** בכל שאלה מוצגת סיפור ושלוש תגובות (A, B, C). דרגו אותן מ-1 (הכי טובה) עד 3 (הכי פחות טובה).
**English:** For each story, three responses are shown (A, B, C). Rank them from 1 (best) to 3 (worst).

> **חשוב / Important:** Give a different rank to each response — no two responses can share the same rank.
""")
st.divider()

# ── ALREADY SUBMITTED ─────────────────────────────────────────────────────────
if st.session_state.submitted:
    st.success("תודה רבה! התגובות שלך נשמרו. / Thank you! Your responses have been saved.")
    st.stop()

# ── EVALUATOR NAME ────────────────────────────────────────────────────────────
evaluator_name = st.text_input(
    "שם (אופציונלי) / Name (optional)",
    placeholder="e.g. Participant 1",
)

st.divider()

# ── STORY SECTIONS ────────────────────────────────────────────────────────────
for i, story in enumerate(STORIES):
    lm = st.session_state.label_maps[i]

    st.subheader(f"סיפור {i + 1} / Story {i + 1}")
    with st.container(border=True):
        st.markdown(f"**{story['story']}**")

    for label in ["A", "B", "C"]:
        condition_key = lm[label]
        response_text = story["responses"][condition_key]
        with st.expander(f"תשובה {label} / Response {label}", expanded=True):
            st.write(response_text)

    cols = st.columns(3)
    for j, label in enumerate(["A", "B", "C"]):
        with cols[j]:
            current = st.session_state.rankings[i][label]
            choice = st.selectbox(
                f"דירוג {label} / Rank {label}",
                options=RANK_OPTIONS,
                index=RANK_OPTIONS.index(current) if current in RANK_OPTIONS else 0,
                key=f"rank_{i}_{label}",
            )
            st.session_state.rankings[i][label] = choice

    st.divider()

# ── VALIDATION & SUBMIT ───────────────────────────────────────────────────────
def parse_rank(val: str) -> int | None:
    if not val:
        return None
    return int(val.split(" ")[0])


def validate_rankings() -> tuple[bool, str]:
    for i, r in enumerate(st.session_state.rankings):
        values = [parse_rank(r["A"]), parse_rank(r["B"]), parse_rank(r["C"])]
        if any(v is None for v in values):
            return False, f"סיפור {i+1}: יש למלא את כל הדירוגים. / Story {i+1}: all ranks required."
        if len(set(values)) != 3:
            return False, f"סיפור {i+1}: כל דירוג חייב להיות שונה. / Story {i+1}: ranks must be unique."
    return True, ""


if st.button("שלח / Submit", type="primary", use_container_width=True):
    valid, error_msg = validate_rankings()
    if not valid:
        st.error(error_msg)
    else:
        numeric_rankings = [
            {label: parse_rank(st.session_state.rankings[i][label]) for label in ["A", "B", "C"]}
            for i in range(len(STORIES))
        ]
        try:
            save_responses(
                st.session_state.session_id,
                evaluator_name,
                numeric_rankings,
                st.session_state.label_maps,
            )
            st.session_state.submitted = True
            st.rerun()
        except Exception as e:
            st.error(f"שגיאה בשמירה. נסה שוב. / Save error. Please retry.\n\n`{e}`")
