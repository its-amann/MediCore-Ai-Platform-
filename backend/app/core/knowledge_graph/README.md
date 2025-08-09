# Knowledge Graph Module

The Knowledge Graph module provides unified relationship management across all microservices in the medical AI application, ensuring proper bidirectional relationships and enabling full patient journey traversal.

## Features

- **Unified Relationship Management**: Centralized handling of all relationships between Users, Cases, Medical Reports, and Chat Sessions
- **Bidirectional Relationships**: Automatic creation and maintenance of bidirectional relationships for graph traversal
- **Cross-Microservice Integration**: Seamless relationship management across different microservices
- **Validation and Repair**: Comprehensive validation and automatic repair of graph inconsistencies
- **Patient Journey Traversal**: Complete patient journey analysis through the knowledge graph

## Architecture

### Core Components

1. **KnowledgeGraphService** (`knowledge_graph_service.py`)
   - Central service for managing the medical knowledge graph
   - Handles User-Case, Case-Report, and ChatSession-Case relationships
   - Provides patient journey traversal and relationship validation

2. **RelationshipManager** (`relationship_manager.py`)
   - Manages complex relationship operations
   - Supports all relationship types in the system
   - Provides path finding and related entity queries

3. **GraphValidator** (`graph_validator.py`)
   - Validates graph integrity
   - Detects orphaned nodes, missing relationships, and inconsistencies
   - Provides automatic repair functionality

## Relationship Types

### Primary Relationships

- **User → Case**: `OWNS` (with reverse `OWNED_BY`)
- **Case → MedicalReport**: `HAS_REPORT` (with reverse `BELONGS_TO_CASE`)
- **Case → ChatSession**: `HAS_CHAT_SESSION` (with reverse `BELONGS_TO_CASE`)
- **ChatSession → ChatMessage**: `HAS_MESSAGE`

### Additional Relationships

- **MedicalReport → Citation**: `CITES`
- **MedicalReport → Finding**: `HAS_FINDING`
- **MedicalReport → ImageAnalysis**: `ANALYZED_IMAGE`
- **Case → Case**: `RELATED_TO`, `FOLLOW_UP_OF`

## Usage

### Basic Setup

```python
from app.core.knowledge_graph import KnowledgeGraphService, get_knowledge_graph_service

# Get singleton instance
kg_service = get_knowledge_graph_service()

# Ensure indexes exist
await kg_service.ensure_indexes()
```

### Creating Relationships

```python
# Ensure User-Case relationship
await kg_service.ensure_user_case_relationship(
    user_id="user123",
    case_id="case456",
    create_user_if_missing=True
)

# Create Case-Report relationship
await kg_service.create_case_report_relationship(
    case_id="case456",
    report_id="report789"
)

# Ensure ChatSession-Case relationship
await kg_service.ensure_session_case_relationship(
    session_id="session111",
    case_id="case456"
)
```

### Patient Journey Analysis

```python
# Get complete patient journey
journey = await kg_service.get_patient_journey(
    user_id="user123",
    include_reports=True,
    include_chats=True,
    include_messages=False  # Can be large
)

# Get complete case data
case_data = await kg_service.get_case_complete_data(
    case_id="case456",
    user_id="user123"  # Optional for verification
)
```

### Validation and Repair

```python
# Validate relationships
report = await kg_service.validate_relationships(fix_issues=False)

# Validate and repair
report = await kg_service.validate_relationships(fix_issues=True)

# Use GraphValidator for detailed validation
validator = GraphValidator(kg_service)
detailed_report = await validator.run_full_validation(
    fix_issues=True,
    detailed_report=True
)
```

## CLI Tools

The module includes a command-line interface for management tasks:

```bash
# Validate the knowledge graph
python -m app.core.knowledge_graph.cli validate

# Validate and fix issues
python -m app.core.knowledge_graph.cli validate --fix

# Quick repair common issues
python -m app.core.knowledge_graph.cli repair

# Analyze patient journey
python -m app.core.knowledge_graph.cli journey --user-id USER123 --include-reports --include-chats

# Get case information
python -m app.core.knowledge_graph.cli case-info CASE456
```

## Integration with Microservices

### Cases Chat Microservice

The unified storage has been updated to use the knowledge graph service:

```python
# In unified_storage.py
self.kg_service = get_knowledge_graph_service()

# After case creation
await self.kg_service.ensure_user_case_relationship(
    case_data['user_id'],
    result['case_id'],
    create_user_if_missing=True
)
```

### Medical Imaging Microservice

The report storage integrates with the knowledge graph:

```python
# In neo4j_report_storage.py
self.kg_service = get_knowledge_graph_service()

# After report save
if report.case_id and self.kg_service:
    relationship_created = await self.kg_service.create_case_report_relationship(
        report.case_id,
        report_id
    )
```

## Testing

Run the test suite to verify functionality:

```bash
# Run all tests
python -m pytest tests/test_knowledge_graph.py -v

# Run specific test
python tests/test_knowledge_graph.py
```

## Common Issues and Solutions

### Orphaned Nodes

**Issue**: Cases without User relationships, Reports without Case relationships

**Solution**: Run `python -m app.core.knowledge_graph.cli repair`

### Missing Bidirectional Relationships

**Issue**: Forward relationship exists but reverse is missing

**Solution**: The validation tool automatically detects and fixes these

### Data Inconsistencies

**Issue**: Case.user_id doesn't match the User in the OWNS relationship

**Solution**: Validation detects these and can fix them automatically

## Best Practices

1. **Always use bidirectional relationships** for main entity connections
2. **Run validation periodically** to ensure graph integrity
3. **Use the knowledge graph service** instead of direct Neo4j queries for relationships
4. **Handle relationship creation failures gracefully** - don't fail the entire operation
5. **Test relationship creation** in your microservice tests

## Performance Considerations

- Indexes are automatically created for all ID fields
- Bidirectional relationships enable efficient traversal in both directions
- The singleton pattern ensures connection pooling
- Batch operations are used where possible
- Validation can be run on subsets of data for large graphs