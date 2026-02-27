TIER_1_KEYWORDS = [
    "javascript", "typescript", "python", "java", "go", "c++",
    "react", "node", "express", "nextjs", "vue", "angular",
    "mongodb", "postgresql", "mysql", "redis", "sql",
    "rest", "api", "graphql", "websocket",
    "git", "github", "docker", "kubernetes", "aws", "gcp", "azure",
    "ci/cd", "linux", "agile", "scrum",
]

TIER_2_KEYWORDS = [
    "microservices", "system design", "load balancing", "caching",
    "authentication", "jwt", "oauth", "testing", "jest", "unit test",
    "deployment", "nginx", "redis", "kafka", "rabbitmq",
    "typescript", "oop", "solid", "design pattern",
]

REQUIRED_KEYWORDS = ["git", "github", "api", "javascript", "python", "java",
                     "react", "node", "typescript"]

METRIC_PATTERNS = [
    r"\d+[%]",         
    r"\d+\+",          
    r"\d+x\b",          
    r"\b\d{2,}\b",      
]


def compute_ats_score(resume: dict) -> dict:
    """
    Score a structured resume dict.
    Returns a breakdown dict with a finalScore (0–100).
    """
    contact_score    = _score_contact(resume.get("contact", {}))
    keyword_score    = _score_keyword_density(resume)
    skills_score     = _score_skills_depth(resume.get("skills", {}))
    project_score    = _score_project_quality(resume.get("projects", []))
    education_score  = _score_education(resume.get("education", []))
    penalty_score    = _compute_penalties(resume)

    raw = (contact_score + keyword_score + skills_score +
           project_score + education_score + penalty_score)

    final = max(0, min(100, raw))

    return {
        "contactScore":        contact_score,       
        "keywordDensityScore": keyword_score,      
        "skillsDepthScore":    skills_score,         
        "projectQualityScore": project_score,       
        "educationScore":      education_score,      
        "penaltyScore":        penalty_score,        
        "finalScore":          final,                
    }


def _score_contact(contact: dict) -> int:
    """Max 10. Missing github or linkedin = hard deduction."""
    score = 0
    if contact.get("email"):    score += 3
    if contact.get("phone"):    score += 2
    if contact.get("linkedin"): score += 3
    if contact.get("github"):   score += 2
    return score


def _score_keyword_density(resume: dict) -> int:
    """
    Max 25. Checks keyword hits in the full resume text.
    Penalises if below minimum threshold — a real ATS will reject
    a resume that doesn't hit enough role-relevant keywords.
    """
    full_text = str(resume).lower()

    tier1_hits = sum(1 for kw in TIER_1_KEYWORDS if kw in full_text)
    tier2_hits = sum(1 for kw in TIER_2_KEYWORDS if kw in full_text)

    if tier1_hits >= 18:   t1_score = 18
    elif tier1_hits >= 14: t1_score = 14
    elif tier1_hits >= 10: t1_score = 10
    elif tier1_hits >= 7:  t1_score = 7
    elif tier1_hits >= 4:  t1_score = 4
    else:                  t1_score = 1

    if tier2_hits >= 6:    t2_score = 7
    elif tier2_hits >= 4:  t2_score = 5
    elif tier2_hits >= 2:  t2_score = 3
    elif tier2_hits >= 1:  t2_score = 1
    else:                  t2_score = 0

    return min(25, t1_score + t2_score)


def _score_skills_depth(skills: dict) -> int:
    """
    Max 15. Rewards diversity across categories, NOT just raw count.
    A list of 20 frameworks but no DB/systems knowledge scores low.
    """
    score = 0
    langs      = skills.get("programmingLanguages", [])
    frameworks = skills.get("frameworksAndLibraries", [])
    databases  = skills.get("databases", [])
    coursework = skills.get("coursework", [])

    # Languages: need at least 2 to show versatility
    if len(langs) >= 4:    score += 4
    elif len(langs) >= 2:  score += 3
    elif len(langs) >= 1:  score += 1

    # Frameworks: need breadth (frontend + backend)
    fw_text = " ".join(frameworks).lower()
    has_frontend = any(f in fw_text for f in ["react", "vue", "angular", "nextjs", "tailwind"])
    has_backend  = any(f in fw_text for f in ["node", "express", "fastapi", "django", "flask", "spring"])
    if has_frontend and has_backend: score += 5
    elif has_frontend or has_backend: score += 3
    elif len(frameworks) >= 3: score += 1

    # Databases: at least 1 is expected
    if len(databases) >= 2:   score += 3
    elif len(databases) == 1: score += 2

    # Coursework / CS fundamentals
    cw_text = " ".join(coursework).lower()
    cs_fundamentals = ["oop", "data structure", "algorithm", "os", "dbms",
                       "networking", "linux", "git", "websocket"]
    hits = sum(1 for f in cs_fundamentals if f in cw_text)
    if hits >= 4:   score += 3
    elif hits >= 2: score += 2
    elif hits >= 1: score += 1

    return min(15, score)


def _score_project_quality(projects: list) -> int:
    """
    Max 25. This is where most resumes fail.
    Rewards: quantified metrics, tech depth, clear description length.
    Punishes: vague one-liners, no numbers, no tech stack listed.
    """
    import re

    if not projects:
        return 0

    score = 0
    count = len(projects)

    if count >= 3:   score += 6
    elif count == 2: score += 4
    elif count == 1: score += 2

    for p in projects[:4]:
        desc  = p.get("description", "")
        techs = p.get("technologies", [])
        p_score = 0

        if len(desc) > 150:   p_score += 2
        elif len(desc) > 60:  p_score += 1

        metric_hits = sum(1 for pat in METRIC_PATTERNS
                          if re.search(pat, desc))
        if metric_hits >= 3:   p_score += 4
        elif metric_hits >= 2: p_score += 3
        elif metric_hits >= 1: p_score += 2

        # Tech stack listed and has depth
        if len(techs) >= 5:    p_score += 2
        elif len(techs) >= 3:  p_score += 1

        score += p_score

    return min(25, score)


def _score_education(education: list) -> int:
    """Max 10."""
    if not education:
        return 2 
    edu = education[0]
    degree = edu.get("degree", "").lower()
    institution = edu.get("institution", "")

    score = 0
    if any(k in degree for k in ["bachelor", "b.tech", "b.e", "b.sc"]):
        score += 6
    elif any(k in degree for k in ["master", "m.tech", "m.sc", "mba"]):
        score += 8
    elif "diploma" in degree:
        score += 3

    if institution:
        score += 2  # has a named institution
    if edu.get("location"):
        score += 2

    return min(10, score)


def _compute_penalties(resume: dict) -> int:
    """
    Returns a NEGATIVE number (deductions). Capped at -15.
    These are the reasons real ATS systems auto-reject resumes.
    """
    penalty = 0
    full_text = str(resume).lower()

    # No work experience / internship at all — biggest red flag for ATS
    has_experience = any(k in full_text for k in
                         ["internship", "intern", "work experience",
                          "experience", "employed", "freelance", "contract"])
    if not has_experience:
        penalty -= 8 

    # Missing required keywords
    missing_required = [kw for kw in REQUIRED_KEYWORDS if kw not in full_text]
    if len(missing_required) >= 6:
        penalty -= 5
    elif len(missing_required) >= 3:
        penalty -= 3
    elif len(missing_required) >= 1:
        penalty -= 1

    # No github link — red flag for SE roles
    if not resume.get("contact", {}).get("github"):
        penalty -= 2

    return max(-15, penalty)