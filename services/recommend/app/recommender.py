
from typing import Dict, Any, List
from .models import ResumeFacts, RoleSuggestion, SkillGap, ProgramSuggestion, RecommendationResponse
from .rules import normalize_skills, score_role, compute_skill_gaps, severity_for_gap
from .taxonomy import role_names, role_by_name

def compute_role_scores(facts: ResumeFacts, tax: Dict[str, Any], top_k: int = 5) -> List[RoleSuggestion]:
    skills = normalize_skills((facts.skills or []) + (facts.languages or []))
    suggestions: List[RoleSuggestion] = []
    for role in tax.get("roles", []):
        core = role.get("core_skills", [])
        nice = role.get("nice_to_have", [])
        score, explain = score_role(skills, core, nice)
        why = f"Matched {explain['core_hits']}/{explain['core_total']} core and {explain['nice_hits']}/{explain['nice_total']} nice-to-have skills."
        suggestions.append(RoleSuggestion(role=role["name"], match_score=score, why=why))
    suggestions.sort(key=lambda r: r.match_score, reverse=True)
    return suggestions[:top_k]

def compute_gaps_for_role(facts: ResumeFacts, tax: Dict[str, Any], role_name: str) -> List[SkillGap]:
    role = role_by_name(tax, role_name)
    if not role:
        return []
    skills = normalize_skills((facts.skills or []) + (facts.languages or []))
    missing = compute_skill_gaps(skills, role.get("core_skills", []))
    gaps: List[SkillGap] = []
    for m in missing:
        trainings = [p.get("name") for p in role.get("programs", []) if m in (p.get("skills_focus", []) or [])]
        gaps.append(SkillGap(skill=m, severity=severity_for_gap(m), reason="Core skill not evidenced", suggested_trainings=trainings))
    return gaps

def recommend_programs(facts: ResumeFacts, tax: Dict[str, Any], roles: List[RoleSuggestion]) -> List[ProgramSuggestion]:
    progs: List[ProgramSuggestion] = []
    for r in roles[:3]:
        role = role_by_name(tax, r.role)
        if not role:
            continue
        for p in role.get("programs", []):
            progs.append(ProgramSuggestion(
                name=p.get("name"),
                provider=p.get("provider", "Unknown"),
                duration_weeks=p.get("duration_weeks"),
                link=p.get("link"),
                why=f"Supports target role: {r.role}",
            ))
    # de-dup by name+provider
    seen = set()
    uniq = []
    for p in progs:
        key = (p.name, p.provider)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return uniq[:10]

def next_steps_from_rules(facts: ResumeFacts, top_roles: List[RoleSuggestion]) -> List[str]:
    steps = ["Refine CV to highlight measurable outcomes (STAR bullets).", "Add links to portfolio/GitHub where relevant."]
    if facts.recent_job_gap_days and facts.recent_job_gap_days > 90:
        steps.append("Prepare a concise explanation for recent gap and highlight upskilling during that period.")
    if top_roles:
        steps.append(f"Tailor your CV for the top role: {top_roles[0].role}.")
    return steps

def build_recommendations(facts: ResumeFacts, tax: Dict[str, Any], top_k_roles: int = 5) -> RecommendationResponse:
    role_suggestions = compute_role_scores(facts, tax, top_k=top_k_roles)
    skill_gaps: List[SkillGap] = []
    if role_suggestions:
        # compute gaps for the top role
        skill_gaps = compute_gaps_for_role(facts, tax, role_suggestions[0].role)
    programs = recommend_programs(facts, tax, role_suggestions)
    steps = next_steps_from_rules(facts, role_suggestions)
    confidence = role_suggestions[0].match_score if role_suggestions else 0.5
    explanation = "Scores are computed from overlap of your skills with role core/nice-to-have skills."
    return RecommendationResponse(
        target_roles=role_suggestions,
        skill_gaps=skill_gaps,
        recommended_programs=programs,
        next_steps=steps,
        confidence=float(round(confidence, 3)),
        explanation=explanation,
    )
