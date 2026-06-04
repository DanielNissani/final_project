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
    margin: 10px 0 14px 0;
    direction: ltr;
    text-align: left;
}

.resp-card {
    border-radius: 10px;
    padding: 14px 18px 12px 18px;
    line-height: 1.75;
    color: #374151;
    font-size: 0.97em;
    margin-bottom: 8px;
    background: white;
    direction: ltr;
    text-align: left;
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

.done-chip {
    background: #d1fae5;
    color: #065f46;
    padding: 3px 11px;
    border-radius: 20px;
    font-size: 0.82em;
    font-weight: 600;
}

div[data-testid="stPills"] button {
    font-size: 0.97em !important;
    padding: 6px 18px !important;
}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SHEET_KEY = "1hoHJpX8M3763kI28bGOS0JH2CdTyWmB2Y-0pmhTYJHU"
WORKSHEET_NAME = "scores"

SCORE_OPTS = ["—", 1, 2, 3, 4, 5, 6, 7]  # leading "—" = unset sentinel
LABELS = ["A", "B", "C"]
BADGE_CLASS = {"A": "badge-A", "B": "badge-B", "C": "badge-C"}
RESP_CLASS  = {"A": "resp-A",  "B": "resp-B",  "C": "resp-C"}


def fmt_score(v):
    return "—" if v == "—" else str(v)


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
            "timestamp", "session_id", "story_id",
            "score_A", "score_B", "score_C",
            "condition_A", "condition_B", "condition_C",
        ])
    return ws


def save_responses(session_id, scores, label_maps):
    ws = get_worksheet()
    rows = []
    for i, story in enumerate(STORIES):
        lm = label_maps[i]
        s = scores[i]
        rows.append([
            datetime.now(timezone.utc).isoformat(),
            session_id,
            story["id"],
            s["A"], s["B"], s["C"],
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
    st.session_state.scores = [{"A": None, "B": None, "C": None} for _ in STORIES]


# ── HELPERS ───────────────────────────────────────────────────────────────────
def story_complete(story_idx):
    vals = list(st.session_state.scores[story_idx].values())
    return all(v is not None for v in vals)


# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="text-align:center;color:#312e81;margin-bottom:4px;">💬 הערכת תגובות אמפתיה</h1>',
    unsafe_allow_html=True,
)

st.markdown("""
<div class="heb" style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;
     padding:16px 22px;margin:14px 0 14px 0;line-height:1.9;">
לפניכם 5 סיפורים אישיים, ולכל סיפור שלוש תגובות (A, B, C).
<br><b>הוראות:</b> קראו כל תגובה ודרגו אותה בנפרד לפי מידת האמפתיות שלה בסולם 1–7: <b>1 = הכי פחות אמפתית &nbsp;·&nbsp; 7 = הכי אמפתית</b>.
<br><span style="color:#6b7280;font-size:0.9em;">אין דירוג נכון או שגוי, ואפשר לתת לשתי תגובות ציון זהה.</span>
</div>
""", unsafe_allow_html=True)

n_total = len(STORIES)
n_complete = sum(story_complete(i) for i in range(n_total))
st.progress(n_complete / n_total)
st.markdown(
    f'<p class="heb" style="font-size:0.9em;color:#6b7280;margin-top:-6px;">'
    f'הושלמו: {n_complete} מתוך {n_total} סיפורים</p>',
    unsafe_allow_html=True,
)

# ── ALREADY SUBMITTED ─────────────────────────────────────────────────────────
if st.session_state.submitted:
    st.success("✅ תודה רבה! התגובות שלך נשמרו.")
    st.balloons()
    st.stop()

st.divider()

# ── STORY SECTIONS ────────────────────────────────────────────────────────────
for i, story in enumerate(STORIES):
    lm = st.session_state.label_maps[i]
    done = story_complete(i)

    # Story header
    done_html = '<span class="done-chip">✓ הושלם</span>' if done else ""
    st.markdown(
        f'<div style="display:flex;justify-content:flex-end;align-items:center;gap:12px;margin-bottom:4px;">'
        f'{done_html}'
        f'<span style="font-size:1.35em;font-weight:700;color:#312e81;direction:rtl;">סיפור {i + 1}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Story text (English — LTR)
    st.markdown(f'<div class="story-box">{story["story"]}</div>', unsafe_allow_html=True)

    # Response cards — each followed by its own 1–7 empathy score slider
    for label in LABELS:
        condition_key = lm[label]
        response_text = story["responses"][condition_key]
        cur = st.session_state.get(f"score_{i}_{label}", "—")
        score_suffix = f" &nbsp;— ציון {cur}" if cur != "—" else ""

        st.markdown(
            f'<div class="resp-card {RESP_CLASS[label]}">'
            f'<div style="text-align:right;direction:rtl;margin-bottom:8px;">'
            f'<span class="badge {BADGE_CLASS[label]}">תשובה {label}{score_suffix}</span>'
            f'</div>'
            f'<div>{response_text}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="heb" style="font-size:0.85em;color:#6b7280;margin:2px 0 -2px 0;">'
            '1 = הכי פחות אמפתית &nbsp;·&nbsp; 7 = הכי אמפתית</div>',
            unsafe_allow_html=True,
        )
        sel = st.select_slider(
            f"score_{i}_{label}",
            options=SCORE_OPTS,
            value="—",
            format_func=fmt_score,
            key=f"score_{i}_{label}",
            label_visibility="collapsed",
        )
        st.session_state.scores[i][label] = None if sel == "—" else int(sel)

    st.divider()

# ── SUBMIT ────────────────────────────────────────────────────────────────────
n_complete_now = sum(story_complete(i) for i in range(n_total))
remaining = n_total - n_complete_now

if remaining > 0:
    st.markdown(
        f'<p class="heb" style="text-align:center;color:#b45309;font-size:0.95em;">'
        f'נותרו {remaining} סיפורים להשלמה</p>',
        unsafe_allow_html=True,
    )

if st.button("שלח", type="primary", use_container_width=True, disabled=(remaining > 0)):
    # Defensive final validation
    error = None
    for i, s in enumerate(st.session_state.scores):
        if any(v is None for v in [s["A"], s["B"], s["C"]]):
            error = f"סיפור {i+1}: יש לדרג את כל התגובות."
            break
    if error:
        st.error(error)
    else:
        try:
            save_responses(
                st.session_state.session_id,
                st.session_state.scores,
                st.session_state.label_maps,
            )
            st.session_state.submitted = True
            st.rerun()
        except Exception as e:
            st.error(f"שגיאה בשמירה. נסה שוב.\n\n`{e}`")
