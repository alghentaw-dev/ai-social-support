def valid_eid(eid: str) -> bool:
    return eid.isdigit() and 15 <= len(eid) <= 18

def applicant_to_eid_raw(applicant: dict) -> dict:
    return {
        "name_ar": "",
        "name_en": (applicant.get("name") or {}).get("full_en") or "",
        "dob": applicant.get("dob"),
        "nationality": applicant.get("nationality"),
        "gender": applicant.get("gender") or "M",
        "issue_date": "2023-01-01",
        "expiry_date": "2026-01-01",
        "residency_type": "resident",
        "occupation": "",
        "issue_emirate": applicant.get("region_emirate") or "Dubai",
        "employer": "",
        "eid_number": applicant.get("emirates_id"),
    }
