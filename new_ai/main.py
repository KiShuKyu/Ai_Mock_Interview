import json
import os
import sys

from dotenv import load_dotenv

from pipeline import ResumeAnalyzer
from scorer import compute_ats_score

load_dotenv()

LABELS = {
    "contactScore":        "Contact Info          (max  10)",
    "keywordDensityScore": "Keyword Density       (max  25)",
    "skillsDepthScore":    "Skills Depth          (max  15)",
    "projectQualityScore": "Project Quality       (max  25)",
    "educationScore":      "Education             (max  10)",
    "penaltyScore":        "Penalties             (min -15)",
    "finalScore":          "─── FINAL SCORE       (max 100)",
}


def print_ats(ats: dict, title: str = "ATS Score Breakdown"):
    print("\n" + "═" * 62)
    print(title)
    print("═" * 62)
    for key, val in ats.items():
        label = LABELS.get(key, key)
        if key == "penaltyScore":
            bar = "▓" * abs(val)
            print(f"  {label:<44} {val:>4}  {bar}")
        elif key == "finalScore":
            bar = "█" * (val // 5)
            print(f"\n  {label:<44} {val:>4}  {bar}")
        else:
            bar = "█" * val
            print(f"  {label:<44} {val:>4}  {bar}")


def main():
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        print("Error: CEREBRAS_API_KEY not set in .env")
        sys.exit(1)

    analyzer = ResumeAnalyzer(api_key=api_key)

    try:
        result = analyzer.analyze()
    except ValueError as e:
        print(f"\nPipeline error: {e}")
        sys.exit(1)

    output = result.to_dict()

    # OUTPUT 1 — ATS score breakdown (terminal) 
    print_ats(output["atsBreakdown"], "OUTPUT 1 — ATS Score Breakdown")

    # OUTPUT 2 — resume.json (file) 
    resume_file = "resume.json"
    with open(resume_file, "w") as f:
        json.dump(output["resume"], f, indent=2)
    print(f"\n✓ OUTPUT 2 — Structured resume saved to {resume_file}")

    # OUTPUT 3 — fixes only, if ATS < 65 (terminal) 
    if "improvedSkills" in output:
        print("\n" + "═" * 62)
        print("OUTPUT 3 — Improvement Plan  (ATS was below 65)")
        print("═" * 62)

        print("\n  ▸ IMPROVED SKILLS")
        improved_skills = output.get("improvedSkills", {})
        for category, items in improved_skills.items():
            if items:
                label = category.replace("programmingLanguages", "Languages") \
                                .replace("frameworksAndLibraries", "Frameworks") \
                                .replace("databases", "Databases") \
                                .replace("coursework", "Coursework")
                print(f"    {label}: {', '.join(items)}")

        print("\n  ▸ IMPROVED PROJECTS")
        for p in output.get("improvedProjects", []):
            print(f"\n    [{p.get('name', '—')}]")
            print(f"    {p.get('description', '')}")
            techs = p.get("technologies", [])
            if techs:
                print(f"    Stack: {', '.join(techs)}")

        print("\n  ▸ KEYWORDS TO ADD")
        for kw in output.get("addedKeywords", []):
            print(f"    + {kw}")

        print("\n  ▸ STRUCTURAL FIXES")
        for fix in output.get("structuralFixes", []):
            print(f"    • {fix}")

        # Re-score the improved resume to show projected ATS gain
        improved_resume = {**output["resume"],
                           "skills":   output["improvedSkills"],
                           "projects": output["improvedProjects"]}
        new_ats = compute_ats_score(improved_resume)
        print_ats(new_ats, "  ▸ PROJECTED ATS After Fixes")

        est = output.get("newEstimatedATS", 0)
        if est:
            print(f"\n  LLM estimated new ATS: {est}/100")


if __name__ == "__main__":
    main()