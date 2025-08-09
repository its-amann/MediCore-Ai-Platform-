"""
Analytics API Endpoints
Provides analytics and insights for medical data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
import logging

from app.core.analytics.analytics_service import AnalyticsService, AnalyticsTimeRange
from app.api.routes.auth import get_current_user, get_database as get_db_client
from app.core.database.models import User
from app.core.database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/dashboard")
async def get_dashboard_analytics(
    time_range: AnalyticsTimeRange = Query(
        AnalyticsTimeRange.LAST_30_DAYS,
        description="Time range for analytics data"
    ),
    current_user: User = Depends(get_current_user),
    db: Neo4jClient = Depends(get_db_client)
) -> Dict[str, Any]:
    """Get comprehensive dashboard analytics"""
    
    try:
        analytics_service = AnalyticsService(db)
        dashboard_stats = await analytics_service.get_dashboard_stats(time_range)
        
        return {
            "success": True,
            "data": dashboard_stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve analytics data"
        )

@router.get("/specialties/comparison")
async def get_specialty_comparison(
    time_range: AnalyticsTimeRange = Query(
        AnalyticsTimeRange.LAST_30_DAYS,
        description="Time range for comparison"
    ),
    current_user: User = Depends(get_current_user),
    db: Neo4jClient = Depends(get_db_client)
) -> Dict[str, Any]:
    """Compare performance across different AI doctor specialties"""
    
    try:
        analytics_service = AnalyticsService(db)
        comparison = await analytics_service.get_specialty_comparison(time_range)
        
        return {
            "success": True,
            "data": comparison
        }
        
    except Exception as e:
        logger.error(f"Failed to get specialty comparison: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve specialty comparison"
        )

@router.get("/cases/outcomes")
async def get_case_outcome_analysis(
    time_range: AnalyticsTimeRange = Query(
        AnalyticsTimeRange.LAST_30_DAYS,
        description="Time range for analysis"
    ),
    current_user: User = Depends(get_current_user),
    db: Neo4jClient = Depends(get_db_client)
) -> Dict[str, Any]:
    """Analyze case outcomes and resolution rates"""
    
    try:
        analytics_service = AnalyticsService(db)
        outcome_analysis = await analytics_service.get_case_outcome_analysis(time_range)
        
        return {
            "success": True,
            "data": outcome_analysis
        }
        
    except Exception as e:
        logger.error(f"Failed to get case outcome analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve case outcome analysis"
        )

@router.get("/export/summary")
async def export_analytics_summary(
    time_range: AnalyticsTimeRange = Query(
        AnalyticsTimeRange.LAST_30_DAYS,
        description="Time range for export"
    ),
    format: str = Query(
        "json",
        description="Export format (json, csv, pdf)",
        regex="^(json|csv|pdf)$"
    ),
    current_user: User = Depends(get_current_user),
    db: Neo4jClient = Depends(get_db_client)
) -> Dict[str, Any]:
    """Export analytics summary in various formats"""
    
    try:
        analytics_service = AnalyticsService(db)
        
        # Get all analytics data
        dashboard_stats = await analytics_service.get_dashboard_stats(time_range)
        specialty_comparison = await analytics_service.get_specialty_comparison(time_range)
        outcome_analysis = await analytics_service.get_case_outcome_analysis(time_range)
        
        # Combine all data
        export_data = {
            "generated_at": datetime.utcnow().isoformat(),
            "time_range": time_range.value,
            "dashboard_statistics": dashboard_stats,
            "specialty_comparison": specialty_comparison,
            "case_outcomes": outcome_analysis
        }
        
        if format == "json":
            return {
                "success": True,
                "data": export_data,
                "format": "json"
            }
            
        elif format == "csv":
            # Convert to CSV format
            # In production, this would use pandas or similar
            csv_data = _convert_to_csv(export_data)
            
            return {
                "success": True,
                "data": csv_data,
                "format": "csv",
                "content_type": "text/csv"
            }
            
        elif format == "pdf":
            # Generate PDF report
            from app.core.reports.report_generator import MedicalReportGenerator
            
            report_gen = MedicalReportGenerator()
            
            # Create analytics report
            analyses = []
            statistics = {
                "total_analyses": dashboard_stats.get("case_statistics", {}).get("total_cases", 0),
                "image_types": list(dashboard_stats.get("imaging_statistics", {}).get("images_by_type", {}).keys()),
                "avg_confidence": dashboard_stats.get("ai_performance", {}).get("overall", {}).get("average_confidence", 0),
                "urgency_distribution": dashboard_stats.get("consultation_statistics", {}).get("urgency_distribution", {}),
                "common_findings": [
                    (f["finding"], f["count"]) 
                    for f in dashboard_stats.get("imaging_statistics", {}).get("top_findings", [])
                ]
            }
            
            pdf_bytes = report_gen.generate_summary_report(
                analyses=analyses,
                statistics=statistics,
                period=f"Last {time_range.value}"
            )
            
            # Convert to base64 for API response
            import base64
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            
            return {
                "success": True,
                "data": pdf_base64,
                "format": "pdf",
                "content_type": "application/pdf"
            }
            
    except Exception as e:
        logger.error(f"Failed to export analytics summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export analytics summary: {str(e)}"
        )

def _convert_to_csv(data: Dict[str, Any]) -> str:
    """Convert analytics data to CSV format"""
    
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["Analytics Summary Report"])
    writer.writerow(["Generated at", data.get("generated_at", "")])
    writer.writerow(["Time Range", data.get("time_range", "")])
    writer.writerow([])
    
    # Case Statistics
    case_stats = data.get("dashboard_statistics", {}).get("case_statistics", {})
    writer.writerow(["Case Statistics"])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Cases", case_stats.get("total_cases", 0)])
    writer.writerow(["Total Consultations", case_stats.get("total_consultations", 0)])
    writer.writerow(["Total Images", case_stats.get("total_images", 0)])
    writer.writerow([])
    
    # AI Performance
    ai_perf = data.get("dashboard_statistics", {}).get("ai_performance", {}).get("overall", {})
    writer.writerow(["AI Performance"])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Consultations", ai_perf.get("total_consultations", 0)])
    writer.writerow(["Average Confidence", ai_perf.get("average_confidence", 0)])
    writer.writerow(["Average Response Time", ai_perf.get("average_response_time", 0)])
    writer.writerow([])
    
    # Specialty Comparison
    writer.writerow(["Specialty Performance"])
    writer.writerow(["Specialty", "Consultations", "Avg Confidence", "Avg Response Time"])
    
    specialties = data.get("specialty_comparison", {}).get("specialties", {})
    for specialty, metrics in specialties.items():
        writer.writerow([
            specialty,
            metrics.get("total_consultations", 0),
            metrics.get("average_confidence", 0),
            metrics.get("average_response_time", 0)
        ])
    
    return output.getvalue()

# Additional endpoints for specific analytics views

@router.get("/trends/conditions")
async def get_condition_trends(
    time_range: AnalyticsTimeRange = Query(AnalyticsTimeRange.LAST_30_DAYS),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Neo4jClient = Depends(get_db_client)
) -> Dict[str, Any]:
    """Get trending medical conditions"""
    
    try:
        analytics_service = AnalyticsService(db)
        dashboard_stats = await analytics_service.get_dashboard_stats(time_range)
        
        health_trends = dashboard_stats.get("health_trends", {})
        
        return {
            "success": True,
            "data": {
                "time_range": time_range.value,
                "top_conditions": health_trends.get("top_conditions", [])[:limit],
                "time_series": health_trends.get("time_series", {})
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get condition trends: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve condition trends"
        )

@router.get("/performance/response-times")
async def get_response_time_analytics(
    time_range: AnalyticsTimeRange = Query(AnalyticsTimeRange.LAST_7_DAYS),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    current_user: User = Depends(get_current_user),
    db: Neo4jClient = Depends(get_db_client)
) -> Dict[str, Any]:
    """Get response time analytics for AI doctors"""
    
    try:
        analytics_service = AnalyticsService(db)
        
        # Get performance metrics
        dashboard_stats = await analytics_service.get_dashboard_stats(time_range)
        ai_performance = dashboard_stats.get("ai_performance", {})
        
        # Filter by specialty if requested
        if specialty:
            specialty_data = ai_performance.get("by_specialty", {}).get(specialty)
            if not specialty_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No data found for specialty: {specialty}"
                )
            
            return {
                "success": True,
                "data": {
                    "time_range": time_range.value,
                    "specialty": specialty,
                    "metrics": specialty_data
                }
            }
        
        # Return all specialties
        return {
            "success": True,
            "data": {
                "time_range": time_range.value,
                "overall": ai_performance.get("overall", {}),
                "by_specialty": ai_performance.get("by_specialty", {})
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get response time analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve response time analytics"
        )

from datetime import datetime  # Add this import at the top