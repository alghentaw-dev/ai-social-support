import streamlit as st
from ui_lib.state.session import ensure

def _sidebar_status():
    st.header("Current draft (wizard)")
    from_stream = st.session_state
    st.write(f"Step: **{from_stream.get('step', 1)}**")
    st.write(f"Application ID: `{from_stream.get('application_id')}`")
    eid = (from_stream.get('applicant') or {}).get('emirates_id', '')
    st.write(f"Applicant EID: `{eid}`")

def main():
    st.set_page_config(page_title="AI Social Support – Application UI", layout="wide")
    ensure()
    st.title("AI Social Support – Application Portal")
    with st.sidebar:
        _sidebar_status()
        st.markdown("---")
        st.caption("Switch pages from the left sidebar menu (Streamlit multipage).")

if __name__ == "__main__":
    main()
