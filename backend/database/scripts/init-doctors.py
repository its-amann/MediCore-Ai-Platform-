"""
Initialize AI Doctors in Neo4j Database
This script creates the AI doctors needed for the Medical AI system
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from neo4j import GraphDatabase

# Doctor data
DOCTORS = [
    {
        "doctor_id": str(uuid.uuid4()),
        "name": "Dr. Cardiac AI",
        "specialty": "CARDIOLOGIST",
        "qualifications": ["MD in Cardiology", "AI Medical Specialist", "Board Certified"],
        "experience_years": 15,
        "ai_model": "specialized-cardio-v1",
        "description": "AI specialist in cardiovascular diseases, hypertension, and heart conditions",
        "availability": "24/7",
        "response_time": "immediate",
        "languages": ["English", "Spanish", "French"],
        "specialties": ["Heart Disease", "Hypertension", "Arrhythmia", "Heart Failure"],
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "doctor_id": str(uuid.uuid4()),
        "name": "Dr. BP Monitor AI",
        "specialty": "BP_SPECIALIST",
        "qualifications": ["MD in Internal Medicine", "Hypertension Specialist", "AI Medical Expert"],
        "experience_years": 12,
        "ai_model": "specialized-bp-v1",
        "description": "AI specialist focused on blood pressure management and hypertension treatment",
        "availability": "24/7",
        "response_time": "immediate",
        "languages": ["English", "Spanish", "French"],
        "specialties": ["Hypertension", "Blood Pressure Management", "Lifestyle Medicine"],
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "doctor_id": str(uuid.uuid4()),
        "name": "Dr. General AI",
        "specialty": "GENERAL_CONSULTANT",
        "qualifications": ["MD in General Medicine", "Family Medicine", "AI Medical Consultant"],
        "experience_years": 20,
        "ai_model": "general-medicine-v1",
        "description": "AI general practitioner for comprehensive health consultations",
        "availability": "24/7",
        "response_time": "immediate",
        "languages": ["English", "Spanish", "French", "Hindi", "Mandarin"],
        "specialties": ["General Medicine", "Preventive Care", "Chronic Disease Management"],
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "doctor_id": str(uuid.uuid4()),
        "name": "Dr. Emergency AI",
        "specialty": "EMERGENCY_SPECIALIST",
        "qualifications": ["MD in Emergency Medicine", "Trauma Specialist", "AI Critical Care"],
        "experience_years": 18,
        "ai_model": "emergency-care-v1",
        "description": "AI specialist for emergency medical situations and urgent care",
        "availability": "24/7",
        "response_time": "immediate",
        "languages": ["English", "Spanish", "French"],
        "specialties": ["Emergency Medicine", "Trauma Care", "Acute Conditions"],
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "doctor_id": str(uuid.uuid4()),
        "name": "Dr. Wellness AI",
        "specialty": "WELLNESS_SPECIALIST",
        "qualifications": ["MD in Preventive Medicine", "Lifestyle Medicine", "AI Wellness Expert"],
        "experience_years": 10,
        "ai_model": "wellness-prevention-v1",
        "description": "AI specialist in preventive medicine and lifestyle optimization",
        "availability": "24/7",
        "response_time": "immediate",
        "languages": ["English", "Spanish", "French"],
        "specialties": ["Preventive Medicine", "Nutrition", "Exercise Medicine", "Stress Management"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
]

def create_doctors(driver):
    """Create doctor nodes in Neo4j"""
    with driver.session() as session:
        for doctor in DOCTORS:
            # Convert arrays to JSON strings for Neo4j
            doc_data = doctor.copy()
            doc_data['qualifications'] = json.dumps(doctor['qualifications'])
            doc_data['languages'] = json.dumps(doctor['languages'])
            doc_data['specialties'] = json.dumps(doctor['specialties'])
            
            query = """
            MERGE (d:Doctor {doctor_id: $doctor_id})
            SET d = $doctor_data
            RETURN d
            """
            
            result = session.run(query, doctor_id=doctor['doctor_id'], doctor_data=doc_data)
            record = result.single()
            if record:
                print(f"[OK] Created doctor: {doctor['name']} ({doctor['specialty']})")
            else:
                print(f"[FAIL] Failed to create doctor: {doctor['name']}")

def verify_doctors(driver):
    """Verify doctors were created"""
    with driver.session() as session:
        query = """
        MATCH (d:Doctor)
        RETURN d.name as name, d.specialty as specialty
        ORDER BY d.specialty
        """
        
        result = session.run(query)
        doctors = list(result)
        
        print(f"\n[INFO] Found {len(doctors)} doctors in database:")
        for doc in doctors:
            print(f"  - {doc['name']} ({doc['specialty']})")
        
        return len(doctors)

def main():
    """Main function"""
    # Neo4j connection details
    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = "medical123"
    
    print("="*60)
    print("INITIALIZING AI DOCTORS IN NEO4J")
    print("="*60)
    
    # Create driver
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    try:
        # Create doctors
        print("\nCreating AI doctors...")
        create_doctors(driver)
        
        # Verify
        count = verify_doctors(driver)
        
        if count >= 3:
            print(f"\n[OK] Successfully initialized {count} AI doctors!")
        else:
            print(f"\n[WARN] Only {count} doctors found. Expected at least 3.")
            
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
    finally:
        driver.close()
        print("\n" + "="*60)

if __name__ == "__main__":
    main()