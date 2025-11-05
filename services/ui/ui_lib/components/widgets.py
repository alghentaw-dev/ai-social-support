# ui_lib/components/widgets.py
from typing import Any, Mapping
import streamlit as st

__all__ = ["facts_block", "kv_table"]

def facts_block(facts: Mapping[str, Any] | None):
    """Compact, readable block for nested facts."""
    facts = facts or {}
    with st.container(border=True):
        if not facts:
            st.caption("No facts available.")
            return
        for k, v in facts.items():
            if isinstance(v, (dict, list)):
                st.markdown(f"**{k}**")
                st.json(v)
            else:
                st.markdown(f"- **{k}:** `{v}`")

def kv_table(items: Mapping[str, Any] | None):
    """Optional: simple key/value list."""
    items = items or {}
    for k, v in items.items():
        st.markdown(f"- **{k}:** {v}")
