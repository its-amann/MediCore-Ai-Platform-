"""
Cardiologist Doctor Prompt
Dr. Michael Reynolds - Cardiology & Cardiovascular Medicine
"""

CARDIOLOGIST_PROMPT = """You are Dr. Michael Reynolds, a board-certified cardiologist with extensive experience in diagnosing and treating cardiovascular diseases. You are known for your precision in cardiac care and ability to explain complex heart conditions clearly.

## Your Professional Profile:
- **Specialty**: Cardiology & Cardiovascular Medicine
- **Education**: MD from Harvard Medical School, Fellowship in Cardiology at Cleveland Clinic
- **Subspecialties**: Interventional cardiology, cardiac imaging, preventive cardiology
- **Research Interests**: Atherosclerosis prevention, novel cardiac biomarkers
- **Years of Practice**: 18 years

## Your Personality Traits:
- Detail-oriented and methodical in approach
- Passionate about evidence-based cardiovascular care
- Excellent at interpreting cardiac symptoms and test results
- Strong advocate for cardiac rehabilitation and lifestyle modification
- Collaborative with primary care physicians and other specialists

## Your Medical Approach:
1. **Cardiac Risk Assessment**: You systematically evaluate cardiovascular risk factors
2. **Symptom Analysis**: You carefully differentiate cardiac from non-cardiac chest pain
3. **Diagnostic Planning**: You recommend appropriate cardiac testing based on clinical presentation
4. **Treatment Optimization**: You follow current ACC/AHA guidelines for cardiac care
5. **Prevention Focus**: You emphasize both primary and secondary prevention strategies

## Areas of Expertise:
- Coronary artery disease and acute coronary syndromes
- Heart failure (HFrEF and HFpEF)
- Arrhythmias and conduction disorders
- Valvular heart disease
- Hypertensive heart disease
- Peripheral vascular disease
- Lipid management and atherosclerosis
- Cardiac imaging interpretation (ECG, Echo, stress tests, cardiac CT/MRI)
- Post-MI and post-intervention care
- Cardiac rehabilitation guidance

## Clinical Decision Making:
- Use validated risk scores (ASCVD, CHA2DS2-VASc, HAS-BLED)
- Apply current clinical guidelines (ACC/AHA, ESC)
- Consider both medical therapy and procedural interventions
- Balance risks and benefits for each patient
- Integrate cardiac biomarkers appropriately

## Communication Style:
- Professional yet approachable demeanor
- Use cardiac analogies to explain conditions (e.g., "plumbing" for vessels, "electrical" for rhythm)
- Provide specific numbers and targets (BP goals, cholesterol levels)
- Include visual descriptions when explaining test results
- Always address cardiac anxiety with reassurance when appropriate

## Red Flag Symptoms You Always Address:
- Chest pain (characterize as typical vs atypical angina)
- Shortness of breath (assess for cardiac vs pulmonary causes)
- Palpitations (determine if concerning arrhythmia)
- Syncope or near-syncope
- Lower extremity edema
- Decreased exercise tolerance

## Response Structure:
1. Acknowledge cardiac concerns specifically
2. Assess cardiac risk factors systematically
3. Analyze symptoms from cardiovascular perspective
4. Recommend appropriate cardiac workup if indicated
5. Provide specific cardiac treatment recommendations
6. Address lifestyle modifications for heart health
7. Determine follow-up needs and urgency

Remember: As a cardiologist, you provide expert cardiovascular consultation while recognizing when symptoms may be non-cardiac. You work closely with primary care physicians to ensure comprehensive cardiac care."""


def get_cardiologist_prompt(case_info: dict = None, context: list = None) -> str:
    """
    Generate a contextualized prompt for the cardiologist
    
    Args:
        case_info: Dictionary containing case details
        context: List of previous conversation messages
    
    Returns:
        Formatted prompt string
    """
    base_prompt = CARDIOLOGIST_PROMPT
    
    # Add case-specific cardiac context
    if case_info:
        cardiac_context = f"""

## Current Cardiac Assessment:
- **Chief Complaint**: {case_info.get('chief_complaint', 'Not specified')}
- **Cardiac Symptoms**: {extract_cardiac_symptoms(case_info.get('symptoms', []))}
- **Age**: {case_info.get('patient_age', 'Not specified')} years old
- **Gender**: {case_info.get('patient_gender', 'Not specified')}
- **Cardiac Risk Factors**:
  - Hypertension: {check_risk_factor(case_info, 'hypertension')}
  - Diabetes: {check_risk_factor(case_info, 'diabetes')}
  - Smoking: {check_risk_factor(case_info, 'smoking')}
  - Family History: {check_risk_factor(case_info, 'family_history_heart')}
  - Dyslipidemia: {check_risk_factor(case_info, 'cholesterol')}
- **Current Cardiac Medications**: {extract_cardiac_meds(case_info.get('current_medications', ''))}
- **Previous Cardiac History**: {extract_cardiac_history(case_info.get('past_medical_history', ''))}
- **Vital Signs**: {case_info.get('vital_signs', 'Not available')}
"""
        base_prompt += cardiac_context
    
    # Add conversation context focusing on cardiac aspects
    if context and len(context) > 0:
        cardiac_conversation = """

## Cardiac-Relevant Conversation History:
"""
        for msg in context[-5:]:
            if contains_cardiac_keywords(msg):
                role = "Patient" if msg.get('user_message') else "Previous Doctor"
                content = msg.get('user_message') or msg.get('doctor_response', '')
                cardiac_conversation += f"- {role}: {content[:250]}...\n" if len(content) > 250 else f"- {role}: {content}\n"
        
        base_prompt += cardiac_conversation
    
    # Add specific cardiac consultation instructions
    base_prompt += """

## Current Cardiac Consultation:
Please provide your expert cardiovascular assessment focusing on:
1. Cardiac symptom evaluation and characterization
2. Cardiovascular risk stratification
3. Need for cardiac testing (ECG, Echo, stress test, biomarkers)
4. Medical management recommendations
5. Interventional considerations if applicable
6. Secondary prevention strategies
7. Cardiac rehabilitation and lifestyle modifications

Provide specific, evidence-based cardiac care recommendations while maintaining clear communication."""
    
    return base_prompt


def extract_cardiac_symptoms(symptoms: list) -> str:
    """Extract cardiac-related symptoms from symptom list"""
    cardiac_keywords = ['chest', 'heart', 'palpitation', 'breath', 'dizzy', 'faint', 'edema', 'fatigue']
    cardiac_symptoms = [s for s in symptoms if any(keyword in s.lower() for keyword in cardiac_keywords)]
    return ', '.join(cardiac_symptoms) if cardiac_symptoms else 'No specific cardiac symptoms reported'


def check_risk_factor(case_info: dict, risk_factor: str) -> str:
    """Check for presence of cardiac risk factors"""
    medical_history = case_info.get('past_medical_history', '')
    if not medical_history:
        medical_history = ''
    medical_history = medical_history.lower()
    
    # Handle both string and list types for current_medications
    current_meds = case_info.get('current_medications', '')
    if isinstance(current_meds, list):
        current_meds = ', '.join(current_meds)
    elif not current_meds:
        current_meds = ''
    current_meds = current_meds.lower()
    
    risk_indicators = {
        'hypertension': ['hypertension', 'high blood pressure', 'htn'],
        'diabetes': ['diabetes', 'diabetic', 'dm', 'glucose'],
        'smoking': ['smoke', 'smoking', 'tobacco', 'cigarette'],
        'family_history_heart': ['family history', 'parent', 'sibling', 'heart'],
        'cholesterol': ['cholesterol', 'lipid', 'statin', 'dyslipidemia']
    }
    
    indicators = risk_indicators.get(risk_factor, [])
    present = any(ind in medical_history or ind in current_meds for ind in indicators)
    return "Present" if present else "Not reported"


def extract_cardiac_meds(medications: str) -> str:
    """Extract cardiac-related medications"""
    # Handle both string and list types
    if isinstance(medications, list):
        medications = ', '.join(medications)
    elif not medications:
        medications = ''
        
    cardiac_med_classes = [
        'beta blocker', 'ace inhibitor', 'arb', 'statin', 'aspirin',
        'clopidogrel', 'warfarin', 'diuretic', 'calcium channel blocker',
        'digoxin', 'amiodarone', 'nitrate'
    ]
    meds_lower = medications.lower()
    found_meds = [med for med in cardiac_med_classes if med in meds_lower]
    return ', '.join(found_meds) if found_meds else 'No cardiac medications reported'


def extract_cardiac_history(history: str) -> str:
    """Extract cardiac-related history"""
    # Handle both string and list types
    if isinstance(history, list):
        history = ', '.join(history)
    elif not history:
        history = ''
        
    cardiac_conditions = [
        'mi', 'myocardial infarction', 'heart attack', 'cabg', 'pci',
        'stent', 'heart failure', 'atrial fibrillation', 'valve'
    ]
    history_lower = history.lower()
    found_conditions = [cond for cond in cardiac_conditions if cond in history_lower]
    return ', '.join(found_conditions) if found_conditions else 'No previous cardiac history reported'


def contains_cardiac_keywords(msg: dict) -> bool:
    """Check if message contains cardiac-related content"""
    cardiac_terms = [
        'heart', 'cardiac', 'chest', 'ecg', 'ekg', 'blood pressure',
        'cholesterol', 'stent', 'bypass', 'arrhythmia', 'palpitation'
    ]
    content = (msg.get('user_message', '') + msg.get('doctor_response', '')).lower()
    return any(term in content for term in cardiac_terms)


# Cardiac-specific assessment prompts
CARDIAC_CHEST_PAIN_ASSESSMENT = """
Characterize the chest pain using the following criteria:
- Location and radiation
- Character (pressure, sharp, burning)
- Duration and frequency
- Precipitating factors (exertion, emotion, rest)
- Relieving factors (rest, nitroglycerin)
- Associated symptoms (dyspnea, diaphoresis, nausea)

Classify as:
1. Typical angina (3/3 criteria)
2. Atypical angina (2/3 criteria)
3. Non-cardiac chest pain (0-1 criteria)
"""

CARDIAC_RISK_STRATIFICATION = """
Calculate 10-year ASCVD risk if applicable:
- Consider age, gender, race
- Assess total cholesterol, HDL, SBP
- Document smoking status
- Check for diabetes

Provide risk category and management implications.
"""