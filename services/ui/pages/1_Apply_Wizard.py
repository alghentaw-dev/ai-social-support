import datetime as dt
import streamlit as st
from ui_lib.state.session import ensure
from ui_lib.utils import valid_eid
from ui_lib.clients import orchestrator as orch
from ui_lib.workflows.apply import upload_extract_attach

def page():
    ensure()
    st.header("Step 1 – Applicant Information & Dependents")

    # Inputs (mirrors your current fields)
    col1, col2 = st.columns(2)
    with col1:
        eid = st.text_input("Emirates ID *", value="784198765432101", max_chars=20)
        first_name = st.text_input("First name *", value="Mohammed")
        father_name = st.text_input("Father name", value="Ali")
        mother_name = st.text_input("Mother name", value="")
        last_name  = st.text_input("Last name", value="Ali")
        dob = st.date_input("Date of birth *", value=dt.date(1992,1,1),
                            min_value=dt.date(1900,1,1), max_value=dt.date.today())
    with col2:
        nationality = st.text_input("Nationality *", value="Syria")
        gender = st.selectbox("Gender", ["", "M", "F"], index=1)
        address = st.text_area("Address", value="Dubai")
        marital_status = st.selectbox("Marital status",
                                      ["", "single", "married", "divorced", "widowed", "other"], index=2)
        region_emirate = st.text_input("Region / Emirate", value="Dubai")

    st.subheader("Economic profile")
    col1, col2 = st.columns(2)
    with col1:
        declared_monthly_income = st.number_input("Declared monthly income (AED) *", min_value=0.0, value=12000.0, step=500.0)
        employment_status = st.selectbox("Employment status *", ["employed","unemployed","self-employed","student","retired"], index=0)
    with col2:
        housing_type = st.selectbox("Housing type *", ["own","rent","other"], index=1)
        household_size = st.number_input("Household size (including applicant) *", min_value=1, value=3, step=1)

    # Dependents (simplified from current code; keep your loop pattern if needed)
    dep_count = st.number_input("Number of dependents (excluding applicant)", min_value=0, value=1, step=1)
    dependents = []
    for i in range(dep_count):
        with st.expander(f"Dependent {i+1}", expanded=(i==0)):
            dep_full_name = st.text_input(f"Full name (Dependent {i+1})", key=f"dep_name_{i}", value="Omar Ali" if i==0 else "")
            dep_relationship = st.selectbox(f"Relationship (Dependent {i+1})", ["spouse","child","parent","sibling","other"], index=1 if i==0 else 0, key=f"dep_rel_{i}")
            dep_dob = st.date_input(f"Date of birth (Dependent {i+1})", value=dt.date(2019,1,1) if i==0 else dt.date(1993,5,10), key=f"dep_dob_{i}")
            dep_nationality = st.text_input(f"Nationality (Dependent {i+1})", value=nationality, key=f"dep_nat_{i}")
            dep_gender = st.selectbox(f"Gender (Dependent {i+1})", ["", "M", "F"], index=1 if i==0 else 0, key=f"dep_gender_{i}")
            dep_is_student = st.checkbox(f"Is student? (Dependent {i+1})", value=(i==0), key=f"dep_student_{i}")
            dep_special = st.checkbox(f"Has special needs? (Dependent {i+1})", value=False, key=f"dep_sn_{i}")
            dependents.append({
                "emirates_id": None,
                "name": {"first_name": dep_full_name, "father_name": None, "mother_name": None, "last_name": None},
                "relationship": dep_relationship,
                "dob": dep_dob.isoformat(),
                "nationality": dep_nationality,
                "gender": dep_gender or None,
                "is_student": dep_is_student,
                "has_special_needs": dep_special,
            })

    if st.button("Save & create draft application ➜", type="primary"):
        errors = []
        if not eid: errors.append("Emirates ID is required.")
        elif not valid_eid(eid): errors.append("Emirates ID must be 15–18 digits.")
        if not first_name: errors.append("First name is required.")
        if not nationality: errors.append("Nationality is required.")
        if declared_monthly_income <= 0: errors.append("Declared monthly income must be > 0.")
        if errors:
            for e in errors: st.error(e)
            st.stop()

        applicant = {
            "emirates_id": eid,
            "name": {"first_name": first_name, "father_name": father_name or None, "mother_name": mother_name or None,
                     "last_name": last_name or None, "full_ar": None, "full_en": f"{first_name} {last_name}".strip() or None},
            "dob": dob.isoformat(), "nationality": nationality, "gender": gender or None,
            "address": address or None, "marital_status": marital_status or None, "region_emirate": region_emirate or None,
        }
        form = {"applicant_eid": eid, "declared_monthly_income": declared_monthly_income, "employment_status": employment_status,
                "housing_type": housing_type, "household_size": int(household_size), "dependents": dependents}

        draft = orch.create_draft(applicant, form)
        st.session_state.update({"applicant": applicant, "form": form, "application_id": draft.get("application_id"), "step": 2})
        st.success(f"Draft created: application_id = {draft.get('application_id')}, EID = {draft.get('applicant_eid')}")

    st.markdown("---")
    st.header("Step 2 – Upload Documents & Run Extraction")

    app_id = st.session_state.get("application_id"); applicant = st.session_state.get("applicant")
    if not app_id or not applicant:
        st.warning("No draft application found. Please complete Step 1 first.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        eid_file   = st.file_uploader("Emirates ID (image/PDF)", type=["png","jpg","jpeg","pdf"], key="eid_file")
        resume     = st.file_uploader("Resume (PDF/DOCX)", type=["pdf","docx"], key="resume_file")
        bank       = st.file_uploader("Bank statement (CSV/XLSX)", type=["csv","xlsx","xls"], key="bank_file")
    with col2:
        assets     = st.file_uploader("Assets & Liabilities (CSV/XLSX)", type=["csv","xlsx","xls"], key="assets_file")
        credit     = st.file_uploader("Credit report (CSV/XLSX)", type=["csv","xlsx","xls"], key="credit_file")

    if st.button("Upload, extract & attach ➜", type="primary"):
        files_with_types = []
        if bank:   files_with_types.append(("bank", bank))
        if eid_file: files_with_types.append(("eid", eid_file))
        if assets: files_with_types.append(("assets_liabilities", assets))
        if credit: files_with_types.append(("credit_report", credit))
        if resume: files_with_types.append(("resume", resume))
        if not files_with_types:
            st.error("Please upload at least one document before continuing."); st.stop()

        with st.spinner("Processing..."):
            documents, extracts, attach = upload_extract_attach(app_id, applicant, files_with_types, st.session_state["form"])
        st.session_state.update({"documents": documents, "extracts": extracts})
        st.success(f"Attached {attach.get('attached', 0)} extracts to application {app_id}. Go to Review & Chat page.")

page()
