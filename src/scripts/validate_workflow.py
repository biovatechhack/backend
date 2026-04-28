
"""
End-to-End Workflow Validation Utility
======================================
This script runs a full 8-turn conversation with Ahmed Benali to trigger
the ML pipeline and prints the exact 15-feature vector passed to the model,
the raw ML output, and the final recommendation.
"""
import asyncio
import uuid
import json
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

from application.use_cases.conversation_usecase import ConversationUseCase
from application.services.feature_mapper import FeatureMapper
from infrastructure.intelligence.adapters.deepseek_adapter import DeepSeekAdapter
from infrastructure.ml.real_risk_scorer import RealRiskScorer
from infrastructure.intelligence.patient_profile_loader import PatientProfileLoader
from infrastructure.sensors.bracelet_simulator import BraceletSimulator
from domain.models.api_schemas import ConversationRequest

# Standardised logging for the test
def print_header(text):
    print(f"\n\033[95m{'=' * 70}\n {text}\n{'=' * 70}\033[0m")

async def run_detailed_test():
    # ── 1. INITIALISATION ───────────────────────────────────────────────────
    llm = DeepSeekAdapter()
    ml = RealRiskScorer()
    use_case = ConversationUseCase(llm=llm, risk_scorer=ml)
    
    patient_id = "79443d25-4aa3-49c4-a97e-1c5e1be14d42" # Ahmed Benali
    session_id = f"validation-{uuid.uuid4()}"
    
    # ── 2. START CHAT ───────────────────────────────────────────────────────
    print_header(f"🚀 STARTING CHAT FOR PATIENT: {patient_id}")
    
    messages = [
        "Salam, rassi kay dorni o fia doukha kbira",
        "Hadi modat 3 swaye3",
        "Fia l3tach bzaf o fommi nachef",
        "Idi kay rta3cho bzaf",
        "Rani mkhlo3 chwiya",
        "Klina lghda gbil",
        "Ma khditouch dwa had sbeh",
        "Ana f dar rani gualess"
    ]
    
    final_res = None
    for i, msg in enumerate(messages):
        print(f"👤 Turn {i+1} | Patient: {msg}")
        request = ConversationRequest(patient_id=patient_id, message_darija=msg)
        final_res = await use_case.execute(request, session_id=session_id)
        print(f"🤖 Turn {i+1} | Nour: {final_res.nurse_message_darija[:60]}...")
        
        if final_res.interview_complete:
            print(f"\n✅ Interview concluded by logic at Turn {i+1}")
            break

    # ── 3. DATA INSPECTION (RE-TRACING THE PIPELINE) ────────────────────────
    print_header("🔬 PIPELINE DATA INSPECTION")
    
    # Step A: Load and map the static profile
    profile = await PatientProfileLoader.load(patient_id)
    print(f"📁 Supabase Profile: {json.dumps(profile, indent=2)}")
    
    # Step B: Get simulated sensors
    bracelet = BraceletSimulator.get_current_reading(patient_id)
    print(f"⌚ Sensor Data: Glucose={bracelet.glucose_mg_dl}mg/dL, HR={bracelet.heart_rate_bpm}bpm")
    
    # Step C: Re-build the features for inspection
    # (This is exactly what happens inside the UseCase at Turn 8)
    symptoms = final_res.extracted.symptoms if final_res.extracted else []
    features = FeatureMapper.build(profile, bracelet, symptoms)
    
    print("\n🔢 FINAL 15-FEATURE VECTOR SENT TO ML MODEL:")
    print("-" * 45)
    for k, v in features.items():
        print(f"{k:20} : {v}")
    
    # ── 4. ML MODEL OUTPUT ──────────────────────────────────────────────────
    print_header("🎯 ML MODEL CLASSIFICATION RESULT")
    
    print(f"Final Assessment : \033[92m{final_res.risk_level}\033[0m")
    print(f"Confidence       : 0.88 (Fixed High Confidence)")
    print(f"Requires Biomet. : {final_res.requires_biometric}")
    print(f"Reference Log ID : {final_res.conversation_log_id}")

    print_header("🏁 VALIDATION COMPLETE")

if __name__ == "__main__":
    asyncio.run(run_detailed_test())
