import streamlit as st
from ui_lib.state.session import ensure
from ui_lib.clients import orchestrator as orch
from ui_lib.components.widgets import facts_block
from ui_lib.components.chat import render_chat

@st.cache_data(ttl=30)
def _fetch_apps():
    return orch.list_applications(limit=100, offset=0)

def page():
    ensure()
    st.header("Applications – Review & LLM Chat")

    try:
        apps = _fetch_apps()
    except Exception as ex:
        st.error(f"Failed to load applications: {ex}")
        st.stop()

    items = apps.get("items", [])
    if not items:
        st.info("No applications found yet. Create one from the wizard first.")
        st.stop()

    options, eid_by_label = [], {}
    for app in items:
        applicant = app.get("applicant", {})
        name = (applicant.get("name") or {}).get("first_name","") + " " + (applicant.get("name") or {}).get("last_name","")
        eid = applicant.get("emirates_id","UNKNOWN")
        status = (app.get("status") or {}).get("state","draft")
        label = f"{eid} – {name.strip() or 'N/A'} – {status}"
        options.append(label); eid_by_label[label] = eid

    selected_label = st.selectbox("Select application", options)
    eid = eid_by_label[selected_label]

    try:
        details = orch.get_details(eid)
    except Exception as ex:
        st.error(f"Failed to load application details: {ex}")
        st.stop()

    app_doc = details.get("application", {}); extracts = details.get("extracts", [])
    left, right = st.columns([1, 2])

    with left:
        st.subheader("Application information")
        applicant = app_doc.get("applicant", {}); form = app_doc.get("form", {}); status = app_doc.get("status", {})
        st.markdown(f"**Application ID:** `{app_doc.get('application_id', '')}`")
        st.markdown(f"**Status:** `{status.get('state','draft')}`")

        with st.expander("Applicant", expanded=True):
            nm = applicant.get("name") or {}
            st.markdown(f"- **EID:** {applicant.get('emirates_id','')}")
            st.markdown(f"- **Name:** {nm.get('first_name','')} {nm.get('last_name','')}".strip())
            st.markdown(f"- **DOB:** {applicant.get('dob','')}")
            st.markdown(f"- **Nationality:** {applicant.get('nationality','')}")
            st.markdown(f"- **Address:** {applicant.get('address','')}")
            st.markdown(f"- **Marital status:** {applicant.get('marital_status','')}")

        with st.expander("Form & household", expanded=True):
            st.markdown(f"- **Declared monthly income:** {form.get('declared_monthly_income','')} AED")
            st.markdown(f"- **Employment status:** {form.get('employment_status','')}")
            st.markdown(f"- **Housing type:** {form.get('housing_type','')}")
            st.markdown(f"- **Household size:** {form.get('household_size','')}")
            deps = form.get("dependents") or []
            st.markdown(f"- **Dependents:** {len(deps)}")
            for i, dep in enumerate(deps, start=1):
                dname = (dep.get('name') or {}).get('first_name', 'Dependent')
                st.markdown(f"  - {i}. {dname} – {dep.get('relationship','')}")

        st.subheader("Documents & extracts")
        if not extracts:
            st.caption("No extracts found yet.")
        else:
            by_type = {}
            for er in extracts:
                by_type.setdefault(er.get("doc_type","unknown"), []).append(er)
            for doc_type, ers in by_type.items():
                with st.expander(f"{doc_type} ({len(ers)} file(s))", expanded=True):
                    for i, er in enumerate(ers, start=1):
                        st.markdown(f"**Document {i}:** `{er.get('doc_id')}`")
                        facts_block(er.get("facts", {}))

    with right:
        render_chat(eid, app_doc, extracts)

page()
