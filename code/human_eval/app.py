import random
import uuid
from datetime import datetime, timezone

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

from stories import STORIES

# requires streamlit >= 1.32
st.set_page_config(
    page_title="הערכת תגובות אמפתיה",
    page_icon="💬",
    layout="centered",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f7f8fa; }

.heb {
    direction: rtl;
    text-align: right;
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
}

.story-box {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 18px 24px;
    line-height: 1.85;
    color: #1e3a8a;
    font-size: 1em;
    margin: 10px 0 18px 0;
}

.resp-card {
    border-radius: 10px;
    padding: 14px 18px 12px 18px;
    line-height: 1.75;
    color: #374151;
    font-size: 0.97em;
    margin-bottom: 4px;
    background: white;
}
.resp-A { border-left: 5px solid #22c55e; }
.resp-B { border-left: 5px solid #3b82f6; }
.resp-C { border-left: 5px solid #f59e0b; }

.badge {
    display: inline-block;
    padding: 3px 13px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.88em;
    margin-bottom: 8px;
}
.badge-A { background: #dcfce7; color: #15803d; }
.badge-B { background: #dbeafe; color: #1d4ed8; }
.badge-C { background: #fef9c3; color: #a16207; }

.rank-hint {
    font-size: 0.82em;
    color: #9ca3af;
    margin-top: 6px;
    direction: rtl;
    text-align: right;
}

.done-chip {
    background: #d1fae5;
    color: #065f46;
    padding: 3px 11px;
    border-radius: 20px;
    font-size: 0.82em;
    font-weight: 600;
}
.todo-chip {
    background: #fef3c7;
    color: #92400e;
    padding: 3px 11px;
    border-radius: 20px;
    font-size: 0.82em;
}

/* enlarge pills slightly */
div[data-testid="stPills"] button {
    font-size: 0.97em !important;
    padding: 6px 16px !important;
}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SHEET_KEY = "1hoHJpX8M3763kI28bGOS0JH2CdTyWmB2Y-0pmhTYJHU"
WORKSHEET_NAME = "responses"

RANK_LABELS = {1: "🥇 1 — הכי טוב / Best", 2: "🥈 2", 3: "🥉 3 — הכי פחות טוב / Worst"}
LABELS = ["A", "B", "C"]
BADGE_CLASS = {"A": "badge-A", "B": "badge-B", "C": "badge-C"}
RESP_CLASS = {"A": "resp-A", "B": "resp-B", "C": "resp-C"}

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


def save_responses(session_id, evaluator_name, rankings, label_maps):
    ws = get_worksheet()
    rows = []
    for i, story in enumerate(STORIES):
        lm = label_maps[i]
        r = rankings[i]
        rows.append([
            datetime.now(timezone.utc).isoformat(),
            session_id, evaluator_name, story["id"],
            r["A"], r["B"], r["C"],
            lm["A"], lm["B"], lm["C"],
        ])
    ws.append_rows(rows, value_input_option="RAW")


# ── SESSION INIT ──────────────────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.session_id = str(uuid.uuid4())[:8]
    st.session_state.submitted = False
    st.session_state.label_maps = [
        dict(zip(LABELS, random.sample(["H", "B", "F"], 3)))
        for _ in STORIES
    ]
    st.session_state.rankings = [{"A": None, "B": None, "C": None} for _ in STORIES]


# ── HELPERS ───────────────────────────────────────────────────────────────────
def available_ranks(story_idx, for_label):
    used = {
        st.session_state.rankings[story_idx][l]
        for l in LABELS
        if l != for_label and st.session_state.rankings[story_idx][l] is not None
    }
    return [r for r in [1, 2, 3] if r not in used]


def story_complete(story_idx):
    vals = list(st.session_state.rankings[story_idx].values())
    return all(v is not None for v in vals) and len(set(vals)) == 3


# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="text-align:center;color:#312e81;margin-bottom:2px;">💬 הערכת תגובות אמפתיה</h1>'
    '<p style="text-align:center;color:#6b7280;margin-top:0;">Empathy Response Evaluation</p>',
    unsafe_allow_html=True,
)

st.markdown("""
<div class="heb" style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:14px 20px;margin:14px 0 6px 0;">
<b>הוראות:</b> לכל סיפור מוצגות שלוש תגובות (A, B, C).
דרגו כל תגובה: <b>1 = הכי טובה &nbsp;·&nbsp; 3 = הכי פחות טובה</b>.
כל תגובה חייבת לקבל דירוג <em>שונה</em> — לא ניתן להקצות אותו דירוג פעמיים.
</div>
<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:14px 20px;margin-bottom:14px;">
<b>Instructions:</b> For each story, rank the three responses (A, B, C):
<b>1 = best &nbsp;·&nbsp; 3 = worst</b>.
Each response must receive a <em>unique</em> rank — the same rank cannot be used twice in one story.
</div>
""", unsafe_allow_html=True)

# progress bar
n_complete = sum(story_complete(i) for i in range(len(STORIES)))
n_total = len(STORIES)
st.progress(
    n_complete / n_total,
    text=f"הושלמו / Completed: {n_complete} / {n_total}",
)

# ── ALREADY SUBMITTED ─────────────────────────────────────────────────────────
if st.session_state.submitted:
    st.success("✅ תודה רבה! התגובות שלך נשמרו. / Thank you! Your responses have been saved.")
    st.balloons()
    st.stop()

# ── EVALUATOR NAME ────────────────────────────────────────────────────────────
st.divider()
evaluator_name = st.text_input(
    "שם (אופציונלי) / Name (optional)",
    placeholder="e.g. Participant 1",
)
st.divider()

# ── STORY SECTIONS ────────────────────────────────────────────────────────────
for i, story in enumerate(STORIES):
    lm = st.session_state.label_maps[i]
    done = story_complete(i)

    # Story header row
    h_col, s_col = st.columns([5, 1])
    with h_col:
        st.subheader(f"סיפור {i + 1} / Story {i + 1}")
    with s_col:
        chip = '<span class="done-chip">✓ הושלם</span>' if done else '<span class="todo-chip">● ממתין</span>'
        st.markdown(f'<div style="padding-top:14px;text-align:right;">{chip}</div>', unsafe_allow_html=True)

    # Story text
    st.markdown(f'<div class="story-box">{story["story"]}</div>', unsafe_allow_html=True)

    # Responses
    for label in LABELS:
        condition_key = lm[label]
        response_text = story["responses"][condition_key]

        opts = available_ranks(i, label)
        current = st.session_state.rankings[i][label]

        # Render response card
        st.markdown(
            f'<div class="resp-card {RESP_CLASS[label]}">'
            f'<span class="badge {BADGE_CLASS[label]}">תשובה {label} / Response {label}</span>'
            f'<div>{response_text}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Rank pills — only ranks not taken by other labels are shown
        st.caption("דירוג / Rank:")
        sel = st.pills(
            f"rank_{i}_{label}",
            options=opts,
            format_func=lambda x: RANK_LABELS[x],
            selection_mode="single",
            key=f"rank_{i}_{label}",
            label_visibility="collapsed",
        )

        # Update rankings immediately so next label sees this choice
        st.session_state.rankings[i][label] = sel

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    st.divider()

# ── SUBMIT ────────────────────────────────────────────────────────────────────
remaining = n_total - sum(story_complete(i) for i in range(n_total))
if remaining > 0:
    st.markdown(
        f'<p class="heb" style="text-align:center;color:#b45309;">'
        f'נותרו {remaining} סיפורים להשלמה / {remaining} stories remaining'
        f'</p>',
        unsafe_allow_html=True,
    )

all_done = remaining == 0
if st.button("שלח / Submit", type="primary", use_container_width=True, disabled=not all_done):
    # Final validation (defensive)
    error = None
    for i, r in enumerate(st.session_state.rankings):
        vals = [r["A"], r["B"], r["C"]]
        if any(v is None for v in vals):
            error = f"סיפור {i+1}: יש למלא את כל הדירוגים. / Story {i+1}: all ranks required."
            break
        if len(set(vals)) != 3:
            error = f"סיפור {i+1}: כל דירוג חייב להיות שונה. / Story {i+1}: ranks must be unique."
            break
    if error:
        st.error(error)
    else:
        try:
            save_responses(
                st.session_state.session_id,
                evaluator_name,
                st.session_state.rankings,
                st.session_state.label_maps,
            )
            st.session_state.submitted = True
            st.rerun()
        except Exception as e:
            st.error(f"שגיאה בשמירה. נסה שוב. / Save error. Please retry.\n\n`{e}`")
