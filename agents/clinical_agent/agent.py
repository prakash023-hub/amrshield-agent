"""
AMRShield - Clinical Recommendation Agent
Powered by Gemini 2.5 Flash via Google Cloud Agent Builder / Vertex AI
"""

import os
import json
import sys
from google import genai
from google.genai import types

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from agents.clinical_agent.tools import (
    calculate_crcl,
    lookup_aware_tier,
    check_drug_interactions,
    query_local_antibiogram,
)
from mcp_tools.phoenix_integration import ensure_phoenix_tracing, get_current_trace_id

# ─────────────────────────────────────────────
# Google GenAI Client (new SDK, ADC auth)
# ─────────────────────────────────────────────

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "project-d52ffa3b-95bb-4dfb-af0")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

CLINICAL_MODEL = "publishers/google/models/gemini-2.5-flash"

# ─────────────────────────────────────────────
# Tool Definitions (new SDK format)
# ─────────────────────────────────────────────

CLINICAL_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="calculate_crcl",
            description="Calculate creatinine clearance using Cockcroft-Gault equation for renal dosing",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "age": types.Schema(type=types.Type.NUMBER, description="Patient age in years"),
                    "weight": types.Schema(type=types.Type.NUMBER, description="Patient weight in kg"),
                    "serum_creatinine": types.Schema(type=types.Type.NUMBER, description="Serum creatinine in mg/dL"),
                    "sex": types.Schema(type=types.Type.STRING, description="Patient biological sex: male or female"),
                },
                required=["age", "weight", "serum_creatinine", "sex"],
            ),
        ),
        types.FunctionDeclaration(
            name="lookup_aware_tier",
            description="Look up the WHO AWaRe classification for an antibiotic",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "antibiotic_name": types.Schema(type=types.Type.STRING, description="Generic antibiotic name"),
                },
                required=["antibiotic_name"],
            ),
        ),
        types.FunctionDeclaration(
            name="check_drug_interactions",
            description="Check for clinically significant drug-drug interactions",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "antibiotic": types.Schema(type=types.Type.STRING, description="Proposed antibiotic"),
                    "current_medications": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="List of current patient medications",
                    ),
                },
                required=["antibiotic", "current_medications"],
            ),
        ),
        types.FunctionDeclaration(
            name="query_local_antibiogram",
            description="Query local hospital antibiogram for pathogen susceptibility patterns",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "pathogen": types.Schema(type=types.Type.STRING, description="Pathogen name"),
                    "infection_site": types.Schema(type=types.Type.STRING, description="Site of infection"),
                },
                required=["pathogen"],
            ),
        ),
    ])
]

# ─────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────

CLINICAL_SYSTEM_PROMPT = """You are AMRShield's Clinical Recommendation Agent — an expert antibiotic stewardship AI assistant.

Your role:
- Analyze patient cases and recommend the most appropriate antibiotic therapy
- Always apply WHO AWaRe classification (prefer Access tier when appropriate)
- Always consider renal function (CrCl) for dose adjustments
- Always check for drug interactions
- Always consult local antibiogram data for empirical therapy
- Provide evidence-based reasoning with guideline citations (IDSA, WHO, CDC NHSN)

Output format — always return a structured recommendation:
{
  "antibiotic": "<generic name>",
  "dose": "<dose and units>",
  "route": "<IV/PO/IM>",
  "frequency": "<frequency>",
  "duration_days": <number>,
  "aware_tier": "<Access/Watch/Reserve>",
  "drug_class": "<class>",
  "rationale": "<evidence-based reasoning>",
  "monitoring": ["<monitoring parameters>"],
  "alternatives": ["<alternative antibiotics if first-line fails>"],
  "confidence_score": <0.0-1.0>,
  "guideline_reference": "<source>"
}

For MRSA use vancomycin/linezolid/daptomycin per site. For ESBL use carbapenem. For Pseudomonas use anti-pseudomonal beta-lactam.
Always state IV vs PO and duration per IDSA/WHO AWaRe. Include renal adjustment note if CrCl <60.

IMPORTANT: You are a decision SUPPORT tool. A licensed physician must review and approve all recommendations.
Never claim 100% certainty. Flag complex cases for specialist review.
"""

# ─────────────────────────────────────────────
# Tool Dispatcher
# ─────────────────────────────────────────────

TOOL_MAP = {
    "calculate_crcl": calculate_crcl,
    "lookup_aware_tier": lookup_aware_tier,
    "check_drug_interactions": check_drug_interactions,
    "query_local_antibiogram": query_local_antibiogram,
}


def dispatch_tool(function_name: str, function_args: dict) -> str:
    """Execute a tool call and return stringified result."""
    if function_name not in TOOL_MAP:
        return json.dumps({"error": f"Unknown tool: {function_name}"})
    try:
        result = TOOL_MAP[function_name](**function_args)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─────────────────────────────────────────────
# Main Agent Function
# ─────────────────────────────────────────────

def run_clinical_agent(patient_profile: dict) -> dict:
    """
    Run the Clinical Recommendation Agent for a patient case.
    Uses google.genai SDK with Vertex AI ADC authentication.
    """
    ensure_phoenix_tracing()
    case_prompt = f"""
Please evaluate this antibiotic stewardship case and provide a recommendation:

PATIENT PROFILE:
- Age: {patient_profile.get('age')} years | Sex: {patient_profile.get('sex')}
- Weight: {patient_profile.get('weight')} kg
- Serum Creatinine: {patient_profile.get('serum_creatinine')} mg/dL
- Allergies: {', '.join(patient_profile.get('allergies', ['None known']))}
- Current Medications: {', '.join(patient_profile.get('current_medications', ['None']))}

CLINICAL PRESENTATION:
- Diagnosis: {patient_profile.get('diagnosis')}
- Infection Site: {patient_profile.get('infection_site')}
- Suspected Pathogen: {patient_profile.get('suspected_pathogen', 'Unknown')}
- Culture Results: {json.dumps(patient_profile.get('culture_results', {})) or 'Pending'}

Please:
1. Calculate the patient's CrCl
2. Query the local antibiogram for susceptibility data
3. Check drug interactions for your recommended antibiotic
4. Look up the AWaRe tier
5. Provide your structured recommendation as JSON
"""

    config = types.GenerateContentConfig(
        system_instruction=CLINICAL_SYSTEM_PROMPT,
        tools=CLINICAL_TOOLS,
    )

    messages = [types.Content(role="user", parts=[types.Part(text=case_prompt)])]

    # Agentic loop — handle multi-step tool calls
    for iteration in range(5):
        response = client.models.generate_content(
            model=CLINICAL_MODEL,
            contents=messages,
            config=config,
        )

        candidate = response.candidates[0]
        has_function_calls = any(
            p.function_call for p in candidate.content.parts if p.function_call
        )

        if not has_function_calls:
            final_text = "".join(p.text for p in candidate.content.parts if p.text)
            try:
                import re
                json_match = re.search(r"\{[\s\S]*\}", final_text)
                recommendation = json.loads(json_match.group()) if json_match else {"raw_response": final_text}
            except Exception:
                recommendation = {"raw_response": final_text}

            recommendation["trace_id"] = get_current_trace_id(
                fallback=f"TRACE-{patient_profile.get('patient_id', 'ANON')}-{iteration}"
            )
            recommendation["patient_id"] = patient_profile.get("patient_id", "ANON")

            from agents.clinical_agent.physician_ready import enrich_for_physician
            recommendation = enrich_for_physician(recommendation, patient_profile)
            return recommendation

        # Execute tool calls
        messages.append(candidate.content)
        tool_results = []

        for part in candidate.content.parts:
            if part.function_call:
                fc = part.function_call
                result_str = dispatch_tool(fc.name, dict(fc.args))
                tool_results.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": result_str},
                        )
                    )
                )

        messages.append(types.Content(role="user", parts=tool_results))

    return {"error": "Agent exceeded max iterations", "patient_id": patient_profile.get("patient_id")}


if __name__ == "__main__":
    # Test case
    test_patient = {
        "patient_id": "TEST-001",
        "age": 68,
        "sex": "female",
        "weight": 58,
        "serum_creatinine": 1.8,
        "diagnosis": "Urinary Tract Infection",
        "infection_site": "UTI",
        "suspected_pathogen": "E. coli",
        "allergies": ["penicillin"],
        "current_medications": ["metformin", "amlodipine", "warfarin"],
        "culture_results": {}
    }
    
    print("Running clinical agent test...")
    result = run_clinical_agent(test_patient)
    print(json.dumps(result, indent=2))
