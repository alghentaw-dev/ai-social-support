
from typing import Dict, Any, List, Tuple

def normalize_skills(skills: List[str] | None) -> List[str]:
    if not skills:
        return []
    return sorted({s.strip().lower() for s in skills if s and isinstance(s, str)})

def score_role(candidate_skills: List[str], core: List[str], nice: List[str]) -> Tuple[float, Dict[str, Any]]:
    # simple overlap heuristic
    cand = set(candidate_skills)
    core_set = set(s.lower() for s in core)
    nice_set = set(s.lower() for s in nice)

    core_hits = len(cand & core_set)
    nice_hits = len(cand & nice_set)

    # weight core more than nice-to-have
    score = 0.75 * (core_hits / max(1, len(core_set))) + 0.25 * (nice_hits / max(1, len(nice_set)))
    explain = {
        "core_total": len(core_set),
        "core_hits": core_hits,
        "nice_total": len(nice_set),
        "nice_hits": nice_hits,
    }
    return float(round(score, 4)), explain

def compute_skill_gaps(candidate_skills: List[str], core: List[str]) -> List[str]:
    cand = set(candidate_skills)
    return [s for s in core if s.lower() not in cand]

def severity_for_gap(skill: str) -> str:
    # trivial mapping; extend with domain logic later
    critical = {"python", "sql", "apis", "fastapi", "excel", "statistics"}
    return "high" if skill.lower() in critical else "medium"
