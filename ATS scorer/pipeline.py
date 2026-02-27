import json
import re
from dataclasses import dataclass, field
from typing import Optional
from cerebras.cloud.sdk import Cerebras
from extractor import extract_text_from_pdf, DEFAULT_PDF_PATH
from scorer import compute_ats_score

@dataclass
class AnalysisOutput:
    resume: dict                       
    atsBreakdown: dict                  
    improvedSkills: Optional[dict] = None      
    improvedProjects: Optional[list] = None    
    addedKeywords: list = field(default_factory=list)
    structuralFixes: list = field(default_factory=list)
    newEstimatedATS: int = 0

    def to_dict(self) -> dict:
        out = {
            "resume": self.resume,
            "atsBreakdown": self.atsBreakdown,
        }
        if self.improvedSkills is not None:
            out["improvedSkills"]   = self.improvedSkills
            out["improvedProjects"] = self.improvedProjects
            out["addedKeywords"]    = self.addedKeywords
            out["structuralFixes"]  = self.structuralFixes
            out["newEstimatedATS"]  = self.newEstimatedATS
        return out

EXTRACT_PROMPT = """\
Extract the resume below into strict structured JSON.
Return ONLY valid JSON — no markdown, no code fences, no explanation.

Resume text:
{resume_text}

Required schema:
{{
  "name": "",
  "contact": {{
    "linkedin": "",
    "phone": "",
    "email": "",
    "github": ""
  }},
  "skills": {{
    "programmingLanguages": [],
    "frameworksAndLibraries": [],
    "coursework": [],
    "databases": [],
    "languages": []
  }},
  "education": [
    {{
      "degree": "",
      "institution": "",
      "location": "",
      "status": ""
    }}
  ],
  "projects": [
    {{
      "name": "",
      "description": "",
      "technologies": [],
      "type": ""
    }}
  ]
}}
"""

IMPROVE_PROMPT = """\
The resume below scored below 65 on ATS for software engineering roles.
Improve it to score above 80.

Current resume JSON:
{resume_json}

ATS breakdown (what was weak):
{ats_breakdown}

Return ONLY valid JSON — no markdown, no code fences, no explanation.

Required schema:
{{
  "improvedSkills": {{
    "programmingLanguages": [],
    "frameworksAndLibraries": [],
    "coursework": [],
    "databases": []
  }},
  "improvedProjects": [
    {{
      "name": "",
      "description": "",
      "technologies": [],
      "type": ""
    }}
  ],
  "newEstimatedATS": 0,
  "addedKeywords": [],
  "structuralFixes": []
}}
"""

def _safe_parse(text: str) -> dict:
    """Strip markdown fences if present, then parse JSON."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


# main class

class ResumeAnalyzer:
    def __init__(self, api_key: str, model: str = "llama3.1-8b"):
        self.client = Cerebras(api_key=api_key)
        self.model = model

    def _call_llm(self, prompt: str, max_tokens: int = 2048) -> str:
        completion = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            max_completion_tokens=max_tokens,
            temperature=0.2,
            top_p=1,
            stream=False,
        )
        return completion.choices[0].message.content

    def analyze(self, pdf_path: str = DEFAULT_PDF_PATH) -> AnalysisOutput:
        print("[1/4] Extracting text from PDF...")
        resume_text = extract_text_from_pdf(pdf_path)
        if not resume_text:
            raise ValueError("Could not extract text from PDF. Is it scanned/image-based?")

        print("[2/4] Calling LLM for structured extraction...")
        raw = self._call_llm(EXTRACT_PROMPT.format(resume_text=resume_text))

        try:
            resume = _safe_parse(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON on extraction call: {e}\n\nRaw output:\n{raw}")

        # Step 3: Python ATS scoring
        print("[3/4] Computing ATS score...")
        ats = compute_ats_score(resume)
        final_score = ats["finalScore"]
        print(f"      ATS Score: {final_score}/100")

        output = AnalysisOutput(resume=resume, atsBreakdown=ats)

        # Step 4 (conditional): LLM call 
        if final_score < 65:
            print(f"[4/4] Score below 65. Calling LLM for improvement plan...")
            improve_raw = self._call_llm(
                IMPROVE_PROMPT.format(
                    resume_json=json.dumps(resume, indent=2),
                    ats_breakdown=json.dumps(ats, indent=2),
                ),
                max_tokens=3000,
            )

            try:
                improvement = _safe_parse(improve_raw)
            except json.JSONDecodeError as e:
                raise ValueError(f"LLM returned invalid JSON on improvement call: {e}\n\nRaw output:\n{improve_raw}")

            output.improvedSkills   = improvement.get("improvedSkills", {})
            output.improvedProjects = improvement.get("improvedProjects", [])
            output.addedKeywords    = improvement.get("addedKeywords", [])
            output.structuralFixes  = improvement.get("structuralFixes", [])
            output.newEstimatedATS  = improvement.get("newEstimatedATS", 0)
        else:
            print("[4/4] Score >= 65. No improvement call needed.")

        return output