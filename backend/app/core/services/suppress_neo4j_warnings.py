"""
Utility to suppress Neo4j informational warnings about existing indexes
"""

import logging

def suppress_neo4j_index_warnings():
    """
    Configure logging to suppress Neo4j warnings about existing indexes/constraints
    These are informational messages when using 'IF NOT EXISTS' clauses
    """
    
    # Get the neo4j.notifications logger
    neo4j_logger = logging.getLogger('neo4j.notifications')
    
    # Set level to WARNING or ERROR to suppress INFO messages
    neo4j_logger.setLevel(logging.WARNING)
    
    # You can also filter specific messages
    class Neo4jIndexFilter(logging.Filter):
        def filter(self, record):
            # Filter out messages about indexes/constraints already existing
            if 'IndexOrConstraintAlreadyExists' in record.getMessage():
                return False  # Don't log this message
            return True  # Log everything else
    
    # Add the filter to the logger
    neo4j_logger.addFilter(Neo4jIndexFilter())
    
    return neo4j_logger

# Call this at application startup
def configure_neo4j_logging():
    """Configure Neo4j logging settings at application startup"""
    suppress_neo4j_index_warnings()
    
    # Optionally set other Neo4j loggers
    logging.getLogger('neo4j').setLevel(logging.WARNING)
    logging.getLogger('neo4j.pool').setLevel(logging.WARNING)
    logging.getLogger('neo4j.io').setLevel(logging.WARNING)