"""
Blood Pressure Specialist Doctor Prompt
Dr. Priya Patel - Hypertension & Blood Pressure Management
"""

BP_SPECIALIST_PROMPT = """You are Dr. Priya Patel, a renowned specialist in hypertension and blood pressure disorders. With your extensive experience in managing complex hypertension cases, you are known for your systematic approach and patient education excellence.

## Your Professional Profile:
- **Specialty**: Hypertension & Blood Pressure Management
- **Education**: MD from Stanford, Fellowship in Nephrology and Hypertension at Johns Hopkins
- **Special Focus**: Resistant hypertension, secondary hypertension, white coat syndrome
- **Research**: Blood pressure variability, chronotherapy in hypertension
- **Years of Practice**: 16 years

## Your Personality Traits:
- Methodical and detail-oriented in BP assessment
- Passionate educator who empowers patients in self-monitoring
- Data-driven approach to BP management
- Emphasizes lifestyle modifications alongside medications
- Collaborative with other specialists for comprehensive care

## Your Medical Approach:
1. **Accurate BP Assessment**: You ensure proper measurement technique and consider multiple readings
2. **Pattern Recognition**: You analyze BP trends, variability, and circadian patterns
3. **Secondary Causes**: You systematically evaluate for secondary hypertension
4. **Individualized Treatment**: You tailor therapy based on patient characteristics and comorbidities
5. **Monitoring Protocols**: You establish clear home monitoring and follow-up plans

## Areas of Expertise:
- Primary hypertension diagnosis and staging
- Secondary hypertension workup and management
- Resistant and refractory hypertension
- Hypertensive emergencies and urgencies
- White coat and masked hypertension
- Blood pressure variability assessment
- Medication selection and optimization
- Non-pharmacological interventions
- Home blood pressure monitoring protocols
- Pregnancy-related hypertension
- Pediatric hypertension

## Clinical Guidelines You Follow:
- ACC/AHA Hypertension Guidelines
- ESC/ESH Guidelines for comparison
- KDIGO Guidelines for CKD patients
- Specific protocols for special populations

## BP Classification Expertise:
- Normal: <120/80 mmHg
- Elevated: 120-129/<80 mmHg
- Stage 1 HTN: 130-139/80-89 mmHg
- Stage 2 HTN: ≥140/90 mmHg
- Hypertensive Crisis: >180/120 mmHg

## Communication Style:
- Clear explanation of BP numbers and their significance
- Visual aids and analogies for patient understanding
- Emphasis on partnership in BP management
- Practical advice for home monitoring
- Motivational approach to lifestyle changes
- Cultural sensitivity in dietary recommendations

## Key Areas You Always Address:
- Proper BP measurement technique
- Home vs office BP discrepancies
- Medication adherence and timing
- Lifestyle factors (DASH diet, sodium, exercise, weight, alcohol)
- BP goals based on individual risk
- Side effects management
- When to seek urgent care

## Response Structure:
1. Review and validate BP readings
2. Assess BP patterns and variability
3. Evaluate for target organ damage
4. Screen for secondary causes if indicated
5. Optimize current treatment regimen
6. Provide specific lifestyle recommendations
7. Establish monitoring plan and goals
8. Address barriers to BP control

Remember: As a hypertension specialist, you help patients understand that BP control is a marathon, not a sprint. You provide comprehensive, evidence-based care while making BP management practical and achievable."""


def get_bp_specialist_prompt(case_info: dict = None, context: list = None) -> str:
    """
    Generate a contextualized prompt for the BP specialist
    
    Args:
        case_info: Dictionary containing case details
        context: List of previous conversation messages
    
    Returns:
        Formatted prompt string
    """
    base_prompt = BP_SPECIALIST_PROMPT
    
    # Add case-specific BP context
    if case_info:
        bp_context = f"""

## Current Blood Pressure Assessment:
- **Chief Complaint**: {case_info.get('chief_complaint', 'Not specified')}
- **BP-Related Symptoms**: {extract_bp_symptoms(case_info.get('symptoms', []))}
- **Age**: {case_info.get('patient_age', 'Not specified')} years old
- **Gender**: {case_info.get('patient_gender', 'Not specified')}
- **Most Recent BP Readings**: {extract_bp_readings(case_info)}
- **BP Medication History**: {extract_bp_medications(case_info.get('current_medications', ''))}
- **Cardiovascular Risk Factors**: {assess_cv_risk_factors(case_info)}
- **Lifestyle Factors**:
  - Salt intake: {case_info.get('salt_intake', 'Not assessed')}
  - Exercise: {case_info.get('exercise_pattern', 'Not assessed')}
  - Alcohol: {case_info.get('alcohol_use', 'Not assessed')}
  - Stress level: {case_info.get('stress_level', 'Not assessed')}
- **Comorbidities**: {extract_bp_comorbidities(case_info)}
- **Family History of HTN**: {check_family_htn(case_info)}
"""
        base_prompt += bp_context
    
    # Add BP-focused conversation context
    if context and len(context) > 0:
        bp_conversation = """

## Blood Pressure Discussion History:
"""
        for msg in context[-5:]:
            if contains_bp_keywords(msg):
                role = "Patient" if msg.get('user_message') else "Previous Doctor"
                content = msg.get('user_message') or msg.get('doctor_response', '')
                bp_conversation += f"- {role}: {content[:250]}...\n" if len(content) > 250 else f"- {role}: {content}\n"
        
        base_prompt += bp_conversation
    
    # Add specific BP consultation instructions
    base_prompt += """

## Current Hypertension Consultation:
Please provide your expert blood pressure assessment focusing on:
1. Validation of BP readings and measurement technique
2. Classification of hypertension stage and urgency
3. Assessment for secondary hypertension if indicated
4. Medication optimization (class, dose, timing)
5. Specific lifestyle modification recommendations
6. Home BP monitoring protocol
7. Target BP goals based on individual factors
8. Follow-up plan and red flags to watch for

Provide practical, actionable advice while educating about the importance of BP control."""
    
    return base_prompt


def extract_bp_symptoms(symptoms: list) -> str:
    """Extract BP-related symptoms"""
    bp_keywords = ['headache', 'dizzy', 'vision', 'chest', 'fatigue', 'nose bleed', 'flushing', 'anxiety']
    bp_symptoms = [s for s in symptoms if any(keyword in s.lower() for keyword in bp_keywords)]
    return ', '.join(bp_symptoms) if bp_symptoms else 'No specific BP-related symptoms reported'


def extract_bp_readings(case_info: dict) -> str:
    """Extract any BP readings from case info"""
    # Check various possible fields for BP data
    bp_data = []
    if 'vital_signs' in case_info:
        if isinstance(case_info['vital_signs'], dict) and 'bp' in case_info['vital_signs']:
            bp_data.append(f"BP: {case_info['vital_signs']['bp']}")
        elif isinstance(case_info['vital_signs'], str) and 'bp' in case_info['vital_signs'].lower():
            bp_data.append(case_info['vital_signs'])
    if 'blood_pressure' in case_info:
        bp_data.append(f"BP: {case_info['blood_pressure']}")
    if 'recent_bp_readings' in case_info:
        bp_data.extend(case_info['recent_bp_readings'])
    
    return '; '.join(bp_data) if bp_data else 'No BP readings provided'


def extract_bp_medications(medications: str) -> str:
    """Extract BP medications and their classes"""
    # Handle both string and list types
    if isinstance(medications, list):
        medications = ', '.join(medications)
    elif not medications:
        medications = ''
        
    bp_med_classes = {
        'ace inhibitor': ['lisinopril', 'enalapril', 'ramipril', 'captopril', 'perindopril'],
        'arb': ['losartan', 'valsartan', 'telmisartan', 'irbesartan', 'candesartan'],
        'beta blocker': ['metoprolol', 'atenolol', 'carvedilol', 'bisoprolol', 'propranolol'],
        'ccb': ['amlodipine', 'diltiazem', 'verapamil', 'nifedipine', 'felodipine'],
        'diuretic': ['hydrochlorothiazide', 'hctz', 'furosemide', 'spironolactone', 'chlorthalidone'],
        'alpha blocker': ['doxazosin', 'prazosin', 'terazosin'],
        'central acting': ['clonidine', 'methyldopa'],
        'vasodilator': ['hydralazine', 'minoxidil']
    }
    
    meds_lower = medications.lower()
    found_meds = []
    for med_class, drugs in bp_med_classes.items():
        for drug in drugs:
            if drug in meds_lower:
                found_meds.append(f"{drug} ({med_class})")
    
    return ', '.join(found_meds) if found_meds else 'No BP medications reported'


def assess_cv_risk_factors(case_info: dict) -> str:
    """Assess cardiovascular risk factors relevant to BP management"""
    risk_factors = []
    
    # Age risk
    age = case_info.get('patient_age', 0)
    gender = case_info.get('patient_gender', '').lower()
    if (gender == 'male' and age >= 45) or (gender == 'female' and age >= 55):
        risk_factors.append('Age')
    
    # Check medical history
    history = case_info.get('past_medical_history', '') or ''
    # Handle both string and list types for current_medications
    current_meds = case_info.get('current_medications', '')
    if isinstance(current_meds, list):
        current_meds = ', '.join(current_meds)
    elif not current_meds:
        current_meds = ''
    
    history = (history + ' ' + current_meds).lower()
    
    if 'diabetes' in history or 'glucose' in history:
        risk_factors.append('Diabetes')
    if 'kidney' in history or 'ckd' in history or 'renal' in history:
        risk_factors.append('CKD')
    if 'smoke' in history or 'tobacco' in history:
        risk_factors.append('Smoking')
    if 'cholesterol' in history or 'lipid' in history:
        risk_factors.append('Dyslipidemia')
    
    return ', '.join(risk_factors) if risk_factors else 'No identified CV risk factors'


def extract_bp_comorbidities(case_info: dict) -> str:
    """Extract comorbidities relevant to BP management"""
    relevant_conditions = [
        'diabetes', 'ckd', 'chronic kidney disease', 'heart failure',
        'coronary artery disease', 'cad', 'stroke', 'tia', 'peripheral artery disease'
    ]
    
    history = case_info.get('past_medical_history', '')
    if not history:
        history = ''
    history = history.lower()
    found_conditions = [cond for cond in relevant_conditions if cond in history]
    
    return ', '.join(set(found_conditions)) if found_conditions else 'No relevant comorbidities reported'


def check_family_htn(case_info: dict) -> str:
    """Check for family history of hypertension"""
    history = case_info.get('past_medical_history', '')
    if not history:
        history = ''
    history = history.lower()
    family_keywords = ['family', 'mother', 'father', 'parent', 'sibling']
    htn_keywords = ['hypertension', 'high blood pressure', 'htn']
    
    has_family = any(fam in history for fam in family_keywords)
    has_htn = any(htn in history for htn in htn_keywords)
    
    return "Positive family history" if (has_family and has_htn) else "Not reported"


def contains_bp_keywords(msg: dict) -> bool:
    """Check if message contains BP-related content"""
    bp_terms = [
        'blood pressure', 'bp', 'hypertension', 'htn', 'systolic', 'diastolic',
        'mmhg', 'antihypertensive', 'ace inhibitor', 'beta blocker'
    ]
    content = (msg.get('user_message', '') + msg.get('doctor_response', '')).lower()
    return any(term in content for term in bp_terms)


# BP-specific assessment prompts
BP_MEASUREMENT_VALIDATION = """
Validate BP measurement technique:
1. Proper cuff size used?
2. Patient position (seated, feet flat, back supported)?
3. Arm position (heart level)?
4. Rest period before measurement?
5. Multiple readings taken?
6. Both arms checked?
7. Home vs office readings comparison?
"""

SECONDARY_HTN_SCREENING = """
Screen for secondary hypertension causes:
- Onset <30 years or >55 years
- Sudden onset or worsening
- Resistant to 3+ medications
- Associated symptoms (flushing, sweating, headaches)
- Abnormal exam findings
- Electrolyte abnormalities

Consider workup for:
- Renal causes
- Endocrine causes
- Vascular causes
- Medications/substances
"""

BP_MEDICATION_OPTIMIZATION = """
Optimize BP medication regimen:
1. Assess current medication effectiveness
2. Check for side effects
3. Consider combination therapy
4. Optimize dosing and timing
5. Address adherence barriers
6. Consider fixed-dose combinations
7. Account for compelling indications
"""