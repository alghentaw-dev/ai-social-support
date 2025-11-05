import streamlit as st

DEFAULTS = {
    "step": 1,
    "mode": "Apply (Wizard)",
    "applicant": None,
    "form": None,
    "application_id": None,
    "documents": None,
    "extracts": None,
    "validation_report": None,
}

def ensure():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

def set_redirect_to_review():
    st.session_state["mode"] = "Review & Chat"
