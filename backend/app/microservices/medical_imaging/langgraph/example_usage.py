"""
Example usage of LangGraph Medical Imaging Workflow
"""

import asyncio
import json
from datetime import datetime

from app.microservices.medical_imaging.services.ai_services.providers.provider_manager import UnifiedProviderManager
from .workflow import MedicalImagingWorkflow


async def example_progress_callback(progress_info: dict):
    """Example progress callback function"""
    print(f"Progress Update: {json.dumps(progress_info, indent=2)}")


async def run_example():
    """Example of running the medical imaging workflow"""
    
    # Initialize provider manager
    provider_manager = UnifiedProviderManager()
    
    # Create workflow
    workflow = MedicalImagingWorkflow(provider_manager)
    
    # Example patient info
    patient_info = {
        "patient_id": "P12345",
        "age": "45",
        "gender": "male",
        "symptoms": ["cough", "fever", "shortness of breath"],
        "clinical_history": "Recent flu-like symptoms for 1 week",
        "study_type": "Chest X-Ray"
    }
    
    # Example image data (would be base64 encoded in real usage)
    image_data = "base64_encoded_image_data_here"
    
    # Run workflow
    result = await workflow.run(
        image_data=image_data,
        patient_info=patient_info,
        case_id=f"case_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        user_id="doctor123",
        progress_callback=example_progress_callback
    )
    
    # Print results
    print("\n=== WORKFLOW RESULTS ===")
    print(f"Case ID: {result.get('case_id')}")
    print(f"Processing Time: {result.get('processing_time', 0):.2f} seconds")
    print(f"Findings Count: {len(result.get('findings', []))}")
    print(f"Literature References: {len(result.get('literature_references', []))}")
    print(f"Quality Score: {result.get('quality_score', 0):.2f}")
    print(f"Severity: {result.get('severity', 'unknown')}")
    
    # Print key findings
    if result.get('key_findings'):
        print("\nKey Findings:")
        for i, finding in enumerate(result['key_findings'], 1):
            print(f"  {i}. {finding}")
    
    # Print recommendations
    if result.get('recommendations'):
        print("\nRecommendations:")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    # Check for errors
    if result.get('error'):
        print(f"\nError occurred: {result['error']}")
    
    # Print workflow metadata
    print(f"\nWorkflow Metadata: {json.dumps(result.get('workflow_metadata', {}), indent=2)}")
    
    # Visualize workflow
    print("\n=== WORKFLOW VISUALIZATION ===")
    visualization = workflow.visualize_workflow()
    print(visualization)


def main():
    """Main entry point"""
    asyncio.run(run_example())


if __name__ == "__main__":
    main()