"""
Knowledge Graph CLI - Command-line tool for validating and repairing the knowledge graph
"""

import asyncio
import logging
import sys
from typing import Optional
import click
from datetime import datetime
import json

from app.core.knowledge_graph import KnowledgeGraphService, GraphValidator
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Knowledge Graph Management CLI"""
    pass


@cli.command()
@click.option('--fix', is_flag=True, help='Automatically fix found issues')
@click.option('--detailed', is_flag=True, help='Include detailed information about each issue')
@click.option('--output', type=click.Path(), help='Save report to file')
async def validate(fix: bool, detailed: bool, output: Optional[str]):
    """Validate the knowledge graph structure and relationships"""
    click.echo("Starting knowledge graph validation...")
    
    # Initialize services
    kg_service = KnowledgeGraphService()
    validator = GraphValidator(kg_service)
    
    try:
        # Ensure indexes exist
        await kg_service.ensure_indexes()
        
        # Run validation
        report = await validator.run_full_validation(
            fix_issues=fix,
            detailed_report=detailed
        )
        
        # Display summary
        click.echo("\n" + "="*60)
        click.echo("VALIDATION REPORT")
        click.echo("="*60)
        click.echo(f"Timestamp: {report['timestamp']}")
        click.echo(f"\nStatistics:")
        for key, value in report['statistics'].items():
            click.echo(f"  {key}: {value}")
        
        # Display issues by type
        if report['issues_by_type']:
            click.echo(f"\nIssues Found:")
            for issue_type, issues in report['issues_by_type'].items():
                click.echo(f"  {issue_type}: {len(issues)} issues")
                if detailed and issues:
                    for issue in issues[:5]:  # Show first 5
                        click.echo(f"    - {json.dumps(issue, indent=2)}")
                    if len(issues) > 5:
                        click.echo(f"    ... and {len(issues) - 5} more")
        
        # Display fixes
        if report['fixes_applied']:
            click.echo(f"\nFixes Applied: {len(report['fixes_applied'])}")
            if detailed:
                for fix in report['fixes_applied'][:10]:
                    click.echo(f"  - Fixed {fix['type']}: {json.dumps(fix, indent=2)}")
        
        # Display recommendations
        if report['recommendations']:
            click.echo("\nRecommendations:")
            for rec in report['recommendations']:
                click.echo(f"  - {rec}")
        
        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(report, f, indent=2)
            click.echo(f"\nFull report saved to: {output}")
        
        click.echo("\nValidation completed!")
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    finally:
        await kg_service.close()


@cli.command()
@click.option('--user-id', help='User ID to analyze')
@click.option('--case-id', help='Specific case ID to analyze')
@click.option('--include-reports', is_flag=True, help='Include medical reports')
@click.option('--include-chats', is_flag=True, help='Include chat sessions')
@click.option('--include-messages', is_flag=True, help='Include chat messages (can be large)')
async def journey(user_id: Optional[str], case_id: Optional[str], 
                 include_reports: bool, include_chats: bool, include_messages: bool):
    """Analyze patient journey through the knowledge graph"""
    if not user_id:
        click.echo("User ID is required", err=True)
        sys.exit(1)
    
    click.echo(f"Analyzing patient journey for user: {user_id}")
    
    kg_service = KnowledgeGraphService()
    
    try:
        journey_data = await kg_service.get_patient_journey(
            user_id=user_id,
            case_id=case_id,
            include_reports=include_reports,
            include_chats=include_chats,
            include_messages=include_messages
        )
        
        # Display journey summary
        click.echo("\n" + "="*60)
        click.echo("PATIENT JOURNEY ANALYSIS")
        click.echo("="*60)
        click.echo(f"User ID: {journey_data['user_id']}")
        click.echo(f"User Created: {journey_data.get('user_created', 'Unknown')}")
        
        # Statistics
        stats = journey_data.get('statistics', {})
        click.echo(f"\nStatistics:")
        for key, value in stats.items():
            click.echo(f"  {key}: {value}")
        
        # Cases
        if journey_data.get('cases'):
            click.echo(f"\nCases:")
            for case in journey_data['cases']:
                click.echo(f"  - {case['case_id']}: {case['title']} ({case['status']})")
                click.echo(f"    Chief Complaint: {case.get('chief_complaint', 'N/A')}")
                click.echo(f"    Created: {case.get('created_at', 'Unknown')}")
        
        # Reports
        if include_reports and journey_data.get('reports'):
            click.echo(f"\nMedical Reports:")
            for report in journey_data['reports'][:5]:
                click.echo(f"  - {report['id']}: {report.get('studyType', 'Unknown')} ({report.get('status', 'Unknown')})")
        
        # Sessions
        if include_chats and journey_data.get('sessions'):
            click.echo(f"\nChat Sessions:")
            for session in journey_data['sessions'][:5]:
                click.echo(f"  - {session['session_id']}: {session.get('session_type', 'Unknown')} ({session.get('message_count', 0)} messages)")
        
        click.echo("\nJourney analysis completed!")
        
    except Exception as e:
        logger.error(f"Journey analysis failed: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    finally:
        await kg_service.close()


@cli.command()
async def repair():
    """Quick repair of common relationship issues"""
    click.echo("Starting quick repair of knowledge graph...")
    
    kg_service = KnowledgeGraphService()
    
    try:
        # Run validation with fixes enabled
        report = await kg_service.validate_relationships(fix_issues=True)
        
        # Display results
        click.echo("\n" + "="*60)
        click.echo("REPAIR RESULTS")
        click.echo("="*60)
        click.echo(f"Issues Found: {report['statistics']['total_issues']}")
        click.echo(f"Issues Fixed: {report['statistics']['total_fixed']}")
        
        # Details by type
        for issue_type, count in report['statistics'].items():
            if issue_type.startswith('orphan_') or issue_type == 'missing_bidirectional':
                click.echo(f"  {issue_type}: {count}")
        
        click.echo("\nRepair completed!")
        
    except Exception as e:
        logger.error(f"Repair failed: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    finally:
        await kg_service.close()


@cli.command()
@click.argument('case_id')
@click.option('--user-id', help='User ID for ownership verification')
async def case_info(case_id: str, user_id: Optional[str]):
    """Get complete information about a case"""
    click.echo(f"Fetching information for case: {case_id}")
    
    kg_service = KnowledgeGraphService()
    
    try:
        case_data = await kg_service.get_case_complete_data(
            case_id=case_id,
            user_id=user_id
        )
        
        if not case_data:
            click.echo("Case not found or access denied", err=True)
            sys.exit(1)
        
        # Display case information
        click.echo("\n" + "="*60)
        click.echo("CASE INFORMATION")
        click.echo("="*60)
        
        case = case_data['case']
        click.echo(f"Case ID: {case['case_id']}")
        click.echo(f"Title: {case.get('title', 'N/A')}")
        click.echo(f"Status: {case.get('status', 'Unknown')}")
        click.echo(f"Priority: {case.get('priority', 'Unknown')}")
        click.echo(f"Chief Complaint: {case.get('chief_complaint', 'N/A')}")
        click.echo(f"Created: {case.get('created_at', 'Unknown')}")
        
        # Statistics
        stats = case_data.get('statistics', {})
        click.echo(f"\nRelated Entities:")
        click.echo(f"  Medical Reports: {stats.get('report_count', 0)}")
        click.echo(f"  Chat Sessions: {stats.get('session_count', 0)}")
        click.echo(f"  Messages: {stats.get('message_count', 0)}")
        
        # Reports
        if case_data.get('reports'):
            click.echo(f"\nMedical Reports:")
            for report in case_data['reports']:
                click.echo(f"  - {report['id']}: {report.get('studyType', 'Unknown')} ({report.get('createdAt', 'Unknown')})")
        
        # Sessions
        if case_data.get('chat_sessions'):
            click.echo(f"\nChat Sessions:")
            for session in case_data['chat_sessions']:
                click.echo(f"  - {session['session_id']}: {session.get('session_type', 'Unknown')} ({session.get('message_count', 0)} messages)")
        
        click.echo("\nCase information retrieved successfully!")
        
    except Exception as e:
        logger.error(f"Failed to get case info: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    finally:
        await kg_service.close()


def main():
    """Main entry point with async support"""
    def run_async_command(coro):
        """Helper to run async commands"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    # Patch click commands to support async
    for name, cmd in cli.commands.items():
        if asyncio.iscoroutinefunction(cmd.callback):
            original_callback = cmd.callback
            def make_sync_callback(async_func):
                def sync_wrapper(*args, **kwargs):
                    return run_async_command(async_func(*args, **kwargs))
                return sync_wrapper
            cmd.callback = make_sync_callback(original_callback)
    
    cli()


if __name__ == '__main__':
    main()