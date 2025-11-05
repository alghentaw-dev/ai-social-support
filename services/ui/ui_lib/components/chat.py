# ui_lib/components/chat.py
from __future__ import annotations
import streamlit as st
from ui_lib.clients import orchestrator as orch

__all__ = ["render_chat"]

def render_chat(eid: str, app_doc: dict | None, extracts: list[dict] | None):
    """Simple chat pane with quick prompts and history."""
    st.subheader("LLM chat")

    # Reset
    col_reset, col_refresh = st.columns(2)
    with col_reset:
        if st.button("🧹 Reset Chat History", key=f"reset_{eid}"):
            try:
                orch.reset_chat(eid)
                st.success("Chat history cleared.")
                st.rerun()
            except Exception as ex:
                st.error(f"Failed to reset chat: {ex}")

    with col_refresh:
        if st.button("🔄 Refresh History", key=f"refresh_{eid}"):
            st.rerun()

    # Load history
    try:
        history = orch.chat_history(eid)
    except Exception as ex:
        st.error(f"Failed to load chat history: {ex}")
        history = []

    # Quick prompts
    with st.container():
        st.caption("💡 Quick prompts")
        prompts = {
            "📊 Financial Summary": "Provide a concise financial summary based on the applicant’s bank, assets, and credit report facts.",
            "👨‍👩‍👧 Household Overview": "Summarize the applicant’s family size, dependents, and employment situation.",
            "🏠 Housing & Liabilities": "Explain the applicant’s housing type and financial liabilities impact.",
            "💳 Credit & Risk Profile": "Summarize credit utilization, score band, and any signs of risk.",
            "✅ Eligibility Insights": "Based on all extracted facts, summarize if the applicant seems financially stable and eligible for social support (no final decision).",
        }
        cols = st.columns(len(prompts))
        for i, (label, msg) in enumerate(prompts.items()):
            if cols[i].button(label, key=f"qp_{eid}_{i}"):
                try:
                    orch.chat(eid, msg, reset=False)
                    st.rerun()
                except Exception as ex:
                    st.error(f"Failed to send prompt: {ex}")

    # Render history
    for role, msg in history:
        with st.chat_message(role):
            st.markdown(msg)

    # Input
    user_text = st.chat_input("Ask something about this application…")
    if user_text:
        try:
            orch.chat(eid, user_text, reset=False)
            st.rerun()
        except Exception as ex:
            st.error(f"Failed to send message: {ex}")
