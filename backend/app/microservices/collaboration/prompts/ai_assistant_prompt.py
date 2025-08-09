"""
AI assistant prompts for medical collaboration
"""

from typing import List, Dict, Any, Optional


def get_ai_assistant_prompt(
    conversation_history: List[str],
    medical_context: Dict[str, Any],
    query: str,
    suggestion_type: str = "general"
) -> str:
    """
    Generate AI assistant prompt based on context and query type
    """
    base_prompt = """You are an AI medical assistant helping healthcare professionals during their collaboration.
You have access to the conversation history and medical context. Provide helpful, accurate, and evidence-based suggestions.

IMPORTANT GUIDELINES:
1. Always maintain patient confidentiality
2. Provide evidence-based recommendations
3. Cite relevant medical guidelines when applicable
4. Acknowledge uncertainty when present
5. Suggest consulting specialists when appropriate
6. Never provide definitive diagnoses - only suggestions for consideration

"""
    
    # Add conversation context
    if conversation_history:
        base_prompt += "\nRECENT CONVERSATION:\n"
        for i, message in enumerate(conversation_history[-10:], 1):
            base_prompt += f"{i}. {message}\n"
    
    # Add medical context
    if medical_context:
        base_prompt += "\nMEDICAL CONTEXT:\n"
        if "patient_age" in medical_context:
            base_prompt += f"- Patient Age: {medical_context['patient_age']}\n"
        if "patient_gender" in medical_context:
            base_prompt += f"- Patient Gender: {medical_context['patient_gender']}\n"
        if "chief_complaint" in medical_context:
            base_prompt += f"- Chief Complaint: {medical_context['chief_complaint']}\n"
        if "symptoms" in medical_context:
            base_prompt += f"- Symptoms: {', '.join(medical_context['symptoms'])}\n"
        if "medical_history" in medical_context:
            base_prompt += f"- Medical History: {', '.join(medical_context['medical_history'])}\n"
        if "current_medications" in medical_context:
            base_prompt += f"- Current Medications: {', '.join(medical_context['current_medications'])}\n"
        if "allergies" in medical_context:
            base_prompt += f"- Allergies: {', '.join(medical_context['allergies'])}\n"
        if "vital_signs" in medical_context:
            base_prompt += "- Vital Signs:\n"
            for vital, value in medical_context["vital_signs"].items():
                base_prompt += f"  - {vital}: {value}\n"
    
    # Add specific query
    base_prompt += f"\nQUERY: {query}\n"
    
    # Add suggestion type specific instructions
    if suggestion_type == "diagnostic":
        base_prompt += """
Please provide diagnostic suggestions considering:
1. Differential diagnoses based on presented symptoms
2. Recommended diagnostic tests or procedures
3. Red flags or urgent conditions to rule out
4. Additional history questions to clarify diagnosis
"""
    elif suggestion_type == "treatment":
        base_prompt += """
Please provide treatment suggestions considering:
1. Evidence-based treatment options
2. Medication recommendations with dosing (if applicable)
3. Non-pharmacological interventions
4. Contraindications and precautions
5. Follow-up recommendations
"""
    elif suggestion_type == "referral":
        base_prompt += """
Please suggest appropriate referrals considering:
1. Which specialists would be most appropriate
2. Urgency of referral (routine, urgent, emergent)
3. Key information to include in referral
4. Expected timeline for consultation
"""
    elif suggestion_type == "investigation":
        base_prompt += """
Please suggest investigations considering:
1. Most appropriate tests based on clinical presentation
2. Order of testing (most informative first)
3. Cost-effectiveness of investigations
4. Expected findings and their interpretation
"""
    else:  # general
        base_prompt += """
Please provide helpful suggestions based on the conversation and medical context.
Focus on practical, actionable recommendations that would assist the healthcare team.
"""
    
    return base_prompt


def get_diagnostic_suggestion_prompt(
    symptoms: List[str],
    patient_info: Dict[str, Any],
    additional_context: Optional[str] = None
) -> str:
    """
    Generate prompt for diagnostic suggestions
    """
    prompt = f"""As a medical AI assistant, analyze the following patient presentation and suggest possible diagnoses:

PATIENT INFORMATION:
- Age: {patient_info.get('age', 'Unknown')}
- Gender: {patient_info.get('gender', 'Unknown')}
- Chief Complaint: {patient_info.get('chief_complaint', 'Not specified')}

SYMPTOMS:
{chr(10).join(f'- {symptom}' for symptom in symptoms)}

"""
    
    if additional_context:
        prompt += f"ADDITIONAL CONTEXT:\n{additional_context}\n\n"
    
    prompt += """Please provide:
1. Top 3-5 differential diagnoses with brief rationale
2. Red flags or emergency conditions to rule out
3. Recommended initial investigations
4. Key history questions to narrow differential

Format your response clearly with sections for each component."""
    
    return prompt


def get_treatment_suggestion_prompt(
    diagnosis: str,
    patient_info: Dict[str, Any],
    contraindications: Optional[List[str]] = None
) -> str:
    """
    Generate prompt for treatment suggestions
    """
    prompt = f"""As a medical AI assistant, suggest treatment options for the following:

DIAGNOSIS: {diagnosis}

PATIENT INFORMATION:
- Age: {patient_info.get('age', 'Unknown')}
- Gender: {patient_info.get('gender', 'Unknown')}
- Weight: {patient_info.get('weight', 'Unknown')}
- Allergies: {', '.join(patient_info.get('allergies', ['None reported']))}
- Current Medications: {', '.join(patient_info.get('current_medications', ['None']))}

"""
    
    if contraindications:
        prompt += f"CONTRAINDICATIONS TO CONSIDER:\n"
        prompt += chr(10).join(f'- {item}' for item in contraindications)
        prompt += "\n\n"
    
    prompt += """Please provide:
1. First-line treatment recommendations
2. Alternative treatment options
3. Dosing information where applicable
4. Duration of treatment
5. Monitoring requirements
6. Patient education points
7. Follow-up recommendations

Include both pharmacological and non-pharmacological interventions where appropriate."""
    
    return prompt


def get_summary_generation_prompt(
    conversation_messages: List[Dict[str, str]],
    room_type: str,
    duration_minutes: int
) -> str:
    """
    Generate prompt for conversation summary
    """
    prompt = f"""Summarize the following medical {room_type} consultation that lasted {duration_minutes} minutes:

CONVERSATION:
"""
    
    for msg in conversation_messages:
        prompt += f"{msg['sender']}: {msg['content']}\n"
    
    prompt += """

Please provide a structured summary including:

1. PARTICIPANTS AND ROLES
   - List all participants and their roles

2. CHIEF COMPLAINT/REASON FOR CONSULTATION
   - Main reason for the consultation

3. KEY DISCUSSION POINTS
   - Important topics discussed
   - Clinical findings shared
   - Diagnostic considerations

4. DECISIONS MADE
   - Diagnostic plan
   - Treatment decisions
   - Referrals agreed upon

5. ACTION ITEMS
   - Specific tasks assigned
   - Follow-up plans
   - Pending items

6. NEXT STEPS
   - Immediate actions required
   - Timeline for follow-up

Keep the summary concise but comprehensive, focusing on clinically relevant information."""
    
    return prompt


def get_action_item_extraction_prompt(
    conversation_messages: List[Dict[str, str]]
) -> str:
    """
    Generate prompt for extracting action items from conversation
    """
    prompt = """Extract all action items and tasks from the following medical consultation conversation:

CONVERSATION:
"""
    
    for msg in conversation_messages:
        prompt += f"{msg['sender']}: {msg['content']}\n"
    
    prompt += """

Please identify and list all action items in the following format:

For each action item provide:
- TASK: Clear description of what needs to be done
- ASSIGNED TO: Who is responsible (if mentioned)
- DEADLINE: When it should be completed (if mentioned)
- PRIORITY: High/Medium/Low (based on clinical urgency)
- CATEGORY: Diagnostic/Treatment/Follow-up/Administrative/Other

Focus on:
1. Tests or investigations to be ordered
2. Medications to be prescribed or adjusted
3. Referrals to be made
4. Follow-up appointments to schedule
5. Patient education to be provided
6. Documentation to be completed
7. Communication tasks (calling patients, other providers, etc.)

List items in order of priority."""
    
    return prompt


def get_medical_context_prompt(
    query: str,
    specialty: Optional[str] = None
) -> str:
    """
    Generate prompt for medical context queries
    """
    base = "You are a medical AI assistant. "
    
    if specialty:
        base += f"Provide information from the perspective of a {specialty} specialist. "
    
    base += f"""
Query: {query}

Provide accurate, evidence-based medical information. Include:
1. Current medical understanding
2. Relevant guidelines or protocols
3. Important considerations
4. When to seek specialist input

Always note that this is for educational purposes and not a substitute for clinical judgment."""
    
    return base