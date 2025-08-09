"""
Shared Prompts for All Doctors
Common prompts for handovers, reports, and medical guidelines
"""

# Medical practice guidelines that all doctors follow
MEDICAL_GUIDELINES = """
## Universal Medical Practice Guidelines:

1. **Patient Safety First**
   - Never provide definitive diagnosis without proper examination
   - Always recommend emergency care for red flag symptoms
   - Acknowledge limitations of remote consultation
   
2. **Evidence-Based Medicine**
   - Follow current clinical guidelines (ACC/AHA, WHO, etc.)
   - Use validated risk assessment tools
   - Base recommendations on peer-reviewed evidence
   
3. **Ethical Considerations**
   - Maintain patient confidentiality (HIPAA compliance)
   - Respect patient autonomy and preferences
   - Provide unbiased medical advice
   - Disclose any limitations or uncertainties
   
4. **Documentation Standards**
   - Clear and accurate medical documentation
   - Proper use of medical terminology
   - Include relevant negatives
   - Time-stamp all entries
"""

# Communication guidelines for all doctors
COMMUNICATION_GUIDELINES = """
## Professional Communication Standards:

1. **Language and Tone**
   - Professional yet compassionate
   - Avoid medical jargon when possible
   - Explain technical terms clearly
   - Cultural sensitivity in all interactions
   
2. **Active Listening**
   - Acknowledge patient concerns
   - Ask clarifying questions
   - Reflect understanding back
   - Show empathy appropriately
   
3. **Information Delivery**
   - Start with most important information
   - Use teach-back method
   - Provide written summaries when helpful
   - Ensure patient understanding
"""


def get_handover_prompt(from_doctor: str, to_doctor: str, case_info: dict, conversation_summary: str) -> str:
    """
    Generate handover prompt when switching between doctors
    
    Args:
        from_doctor: Doctor type handing over
        to_doctor: Doctor type receiving
        case_info: Current case information
        conversation_summary: Summary of conversation so far
    
    Returns:
        Formatted handover prompt
    """
    prompt = f"""You are receiving a patient handover from {from_doctor} to you as {to_doctor}.

## Patient Information:
- **Case ID**: {case_info.get('case_id', 'Not specified')}
- **Chief Complaint**: {case_info.get('chief_complaint', 'Not specified')}
- **Current Status**: {case_info.get('status', 'Active')}
- **Priority**: {case_info.get('priority', 'Medium')}

## Handover Summary:
{conversation_summary}

## Your Tasks:
1. Acknowledge the handover professionally
2. Review the case from your specialty perspective
3. Identify any additional assessments needed from your expertise
4. Continue care with your specialized focus
5. Maintain continuity while adding your unique insights

Please introduce yourself and begin your specialized assessment."""
    
    return prompt


def get_case_summary_prompt(conversations: list, case_info: dict) -> str:
    """
    Generate prompt for creating case summary
    
    Args:
        conversations: List of all conversations
        case_info: Case information
    
    Returns:
        Formatted summary prompt
    """
    prompt = f"""Create a concise medical case summary based on the following information:

## Case Details:
- **Chief Complaint**: {case_info.get('chief_complaint')}
- **Symptoms**: {', '.join(case_info.get('symptoms', []))}
- **Patient**: {case_info.get('patient_age', 'Unknown age')} {case_info.get('patient_gender', '')}
- **Medical History**: {case_info.get('past_medical_history', 'None reported')}

## Consultation History:
Total consultations: {len(conversations)}

Please provide:
1. **Clinical Presentation**: Brief overview of symptoms and timeline
2. **Key Findings**: Important discoveries from consultations
3. **Working Diagnosis**: Current diagnostic considerations
4. **Treatment Plan**: Recommended interventions
5. **Follow-up**: Next steps and monitoring

Keep the summary under 500 words and clinically focused."""
    
    return prompt


def get_report_generation_prompt(conversations: list, case_info: dict, report_sections: list) -> str:
    """
    Generate comprehensive medical report prompt
    
    Args:
        conversations: All conversation history
        case_info: Complete case information
        report_sections: Sections to include in report
    
    Returns:
        Formatted report generation prompt
    """
    # Format conversation history by doctor
    doctor_summaries = {}
    for conv in conversations:
        doctor = conv.get('doctor_type', 'Unknown')
        if doctor not in doctor_summaries:
            doctor_summaries[doctor] = []
        doctor_summaries[doctor].append({
            'message': conv.get('user_message', ''),
            'response': conv.get('doctor_response', ''),
            'timestamp': conv.get('created_at', '')
        })
    
    prompt = f"""Generate a comprehensive medical consultation report.

## Patient Information:
- **Case ID**: {case_info.get('case_id')}
- **Date**: {case_info.get('created_at')}
- **Demographics**: {case_info.get('patient_age', 'Unknown')} year old {case_info.get('patient_gender', 'patient')}

## Chief Complaint:
{case_info.get('chief_complaint')}

## History of Present Illness:
Symptoms: {', '.join(case_info.get('symptoms', []))}

## Past Medical History:
{case_info.get('past_medical_history', 'None reported')}

## Current Medications:
{case_info.get('current_medications', 'None reported')}

## Allergies:
{case_info.get('allergies', 'NKDA')}

## Consultations Summary:
{format_doctor_consultations(doctor_summaries)}

## Report Sections to Include:
{chr(10).join(f"- {section}" for section in report_sections)}

Please create a professional medical report with clear sections, clinical terminology, and actionable recommendations. Include contributions from all consulting physicians."""
    
    return prompt


def format_doctor_consultations(doctor_summaries: dict) -> str:
    """Format doctor consultations for report"""
    formatted = []
    for doctor, consultations in doctor_summaries.items():
        formatted.append(f"\n### {doctor.replace('_', ' ').title()}")
        formatted.append(f"Total interactions: {len(consultations)}")
        
        # Get key points from last few consultations
        recent = consultations[-3:] if len(consultations) > 3 else consultations
        for i, cons in enumerate(recent, 1):
            formatted.append(f"\nConsultation {i}:")
            formatted.append(f"Patient: {cons['message'][:100]}...")
            formatted.append(f"Doctor: {cons['response'][:200]}...")
    
    return '\n'.join(formatted)


# Image analysis prompt enhancement
def get_image_analysis_prompt(doctor_type: str, base_prompt: str) -> str:
    """
    Enhance doctor prompt for image analysis
    
    Args:
        doctor_type: Type of doctor analyzing
        base_prompt: Base doctor prompt
    
    Returns:
        Enhanced prompt for image analysis
    """
    image_prompt = base_prompt + """

## Medical Image Analysis:
You are now analyzing a medical image provided by the patient. Please:

1. **Describe Findings**: Objectively describe what you observe
2. **Clinical Correlation**: Relate findings to reported symptoms
3. **Differential Diagnosis**: Consider possible conditions
4. **Recommendations**: Suggest appropriate next steps
5. **Limitations**: Acknowledge any limitations of image quality or type

Remember:
- Be specific about anatomical locations
- Note any abnormalities or normal variants
- Recommend appropriate imaging follow-up if needed
- Advise in-person evaluation for definitive diagnosis
"""
    
    return image_prompt


# Audio transcription context prompt
def get_audio_context_prompt(transcribed_text: str) -> str:
    """
    Create context prompt for audio transcription
    
    Args:
        transcribed_text: Text from audio transcription
    
    Returns:
        Formatted context prompt
    """
    prompt = f"""The patient has provided an audio message that has been transcribed:

## Audio Transcript:
"{transcribed_text}"

Please consider:
1. The patient may have difficulty typing or prefers verbal communication
2. There might be emotional context in their voice (though not captured in text)
3. Some medical terms might be transcribed phonetically
4. Clarify any ambiguous terms mentioned

Respond to their verbal message with the same care as written text."""
    
    return prompt


# MCP integration prompt for case history
def get_mcp_context_prompt(related_cases: list) -> str:
    """
    Create prompt incorporating related case history from MCP
    
    Args:
        related_cases: List of related cases from MCP server
    
    Returns:
        Formatted context prompt
    """
    if not related_cases:
        return ""
    
    prompt = """

## Related Case History (from Medical Database):
The following similar cases were found in the patient's medical history:

"""
    
    for i, case in enumerate(related_cases[:3], 1):  # Limit to 3 most relevant
        prompt += f"""
### Related Case {i}:
- **Date**: {case.get('created_at', 'Unknown')}
- **Complaint**: {case.get('chief_complaint', 'Not specified')}
- **Diagnosis**: {case.get('diagnosis', 'Pending')}
- **Treatment**: {case.get('treatment_plan', 'Not specified')}
- **Outcome**: {case.get('outcome', 'Not documented')}
"""
    
    prompt += """
Consider these previous cases when formulating your current assessment and recommendations.
"""
    
    return prompt