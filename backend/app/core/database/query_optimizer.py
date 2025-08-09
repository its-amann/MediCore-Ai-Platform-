"""
Database Query Optimization Utilities
Agent 8: Performance & Optimization Specialist

Provides query optimization, indexing recommendations, and performance monitoring for Neo4j
"""

import time
import logging
from typing import Dict, List, Any, Optional
from functools import wraps
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class QueryPerformanceMonitor:
    """Monitor and analyze query performance"""
    
    def __init__(self):
        self.query_stats: Dict[str, List[Dict[str, Any]]] = {}
        self.slow_query_threshold = 1000  # 1 second in milliseconds
        
    def log_query(self, query: str, execution_time: float, params: dict = None):
        """Log query execution for performance analysis"""
        query_hash = hash(query)
        query_key = f"query_{query_hash}"
        
        if query_key not in self.query_stats:
            self.query_stats[query_key] = []
        
        self.query_stats[query_key].append({
            'query': query,
            'execution_time': execution_time,
            'timestamp': datetime.now(),
            'params': params or {},
            'is_slow': execution_time > self.slow_query_threshold
        })
        
        # Log slow queries
        if execution_time > self.slow_query_threshold:
            logger.warning(f"Slow query detected ({execution_time:.2f}ms): {query[:100]}...")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance analysis report"""
        total_queries = sum(len(stats) for stats in self.query_stats.values())
        slow_queries = []
        query_patterns = {}
        
        for query_key, stats in self.query_stats.items():
            if not stats:
                continue
                
            avg_time = sum(s['execution_time'] for s in stats) / len(stats)
            max_time = max(s['execution_time'] for s in stats)
            slow_count = sum(1 for s in stats if s['is_slow'])
            
            query_patterns[query_key] = {
                'sample_query': stats[0]['query'],
                'execution_count': len(stats),
                'average_time': avg_time,
                'max_time': max_time,
                'slow_executions': slow_count,
                'slow_percentage': (slow_count / len(stats)) * 100
            }
            
            if slow_count > 0:
                slow_queries.extend([s for s in stats if s['is_slow']])
        
        return {
            'total_queries': total_queries,
            'unique_patterns': len(self.query_stats),
            'slow_queries_count': len(slow_queries),
            'query_patterns': query_patterns,
            'recommendations': self._generate_recommendations(query_patterns)
        }
    
    def _generate_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        for pattern_key, stats in patterns.items():
            if stats['slow_percentage'] > 20:  # More than 20% slow executions
                recommendations.append(
                    f"High slow query rate for pattern: {stats['sample_query'][:50]}... "
                    f"({stats['slow_percentage']:.1f}% slow)"
                )
            
            if stats['average_time'] > 500:  # Average > 500ms
                recommendations.append(
                    f"High average execution time: {stats['sample_query'][:50]}... "
                    f"({stats['average_time']:.1f}ms average)"
                )
        
        return recommendations


# Global performance monitor instance
query_monitor = QueryPerformanceMonitor()


def monitor_query_performance(func):
    """Decorator to monitor query performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Try to extract query from function name or args
            query_info = getattr(func, '__name__', 'unknown_query')
            query_monitor.log_query(query_info, execution_time)
            
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            query_monitor.log_query(f"FAILED_{func.__name__}", execution_time)
            raise
    
    return wrapper


class Neo4jQueryOptimizer:
    """Neo4j specific query optimization utilities"""
    
    @staticmethod
    def get_index_recommendations() -> List[Dict[str, Any]]:
        """Get index recommendations for common query patterns"""
        return [
            {
                'index_type': 'BTREE',
                'property': 'Case.case_id',
                'reason': 'Frequently used for case lookups',
                'query': 'CREATE INDEX case_id_idx FOR (c:Case) ON (c.case_id)'
            },
            {
                'index_type': 'BTREE',
                'property': 'User.user_id',
                'reason': 'Used for user authentication and authorization',
                'query': 'CREATE INDEX user_id_idx FOR (u:User) ON (u.user_id)'
            },
            {
                'index_type': 'BTREE',
                'property': 'Case.status',
                'reason': 'Frequently filtered by status',
                'query': 'CREATE INDEX case_status_idx FOR (c:Case) ON (c.status)'
            },
            {
                'index_type': 'BTREE',
                'property': 'Case.created_at',
                'reason': 'Used for sorting and date range queries',
                'query': 'CREATE INDEX case_created_at_idx FOR (c:Case) ON (c.created_at)'
            },
            {
                'index_type': 'FULLTEXT',
                'property': 'Case.symptoms,chief_complaint,description',
                'reason': 'Enable text search across case content',
                'query': '''
                    CREATE FULLTEXT INDEX case_content_search 
                    FOR (c:Case) ON EACH [c.symptoms, c.chief_complaint, c.description]
                '''
            }
        ]
    
    @staticmethod
    def get_optimized_queries() -> Dict[str, str]:
        """Get optimized versions of common queries"""
        return {
            'get_user_cases_optimized': '''
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                WHERE c.status <> 'archived'
                RETURN c
                ORDER BY c.created_at DESC
                LIMIT $limit
            ''',
            
            'get_case_with_chat_optimized': '''
                MATCH (c:Case {case_id: $case_id})<-[:OWNS]-(u:User {user_id: $user_id})
                OPTIONAL MATCH (c)-[:HAS_SESSION]->(s:ChatSession)
                OPTIONAL MATCH (s)-[:HAS_MESSAGE]->(m:ChatMessage)
                RETURN c, collect(DISTINCT s) as sessions, collect(DISTINCT m) as messages
            ''',
            
            'search_cases_optimized': '''
                CALL db.index.fulltext.queryNodes("case_content_search", $search_term) 
                YIELD node, score
                MATCH (node)<-[:OWNS]-(u:User {user_id: $user_id})
                WHERE score > 0.5
                RETURN node as case, score
                ORDER BY score DESC
                LIMIT $limit
            ''',
            
            'get_recent_activity_optimized': '''
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                WHERE c.updated_at > datetime() - duration({days: 30})
                OPTIONAL MATCH (c)-[:HAS_SESSION]->(s:ChatSession)
                WHERE s.last_activity > datetime() - duration({days: 7})
                RETURN c, s
                ORDER BY coalesce(s.last_activity, c.updated_at) DESC
                LIMIT $limit
            '''
        }
    
    @staticmethod
    async def analyze_query_plan(driver, query: str, params: dict = None) -> Dict[str, Any]:
        """Analyze query execution plan"""
        async with driver.session() as session:
            try:
                # Get query plan using EXPLAIN
                explain_query = f"EXPLAIN {query}"
                result = await session.run(explain_query, params or {})
                plan = await result.single()
                
                # Get profile for actual execution statistics
                profile_query = f"PROFILE {query}"
                profile_result = await session.run(profile_query, params or {})
                profile = await profile_result.single()
                
                return {
                    'plan': plan,
                    'profile': profile,
                    'recommendations': Neo4jQueryOptimizer._analyze_plan_for_optimizations(plan)
                }
            except Exception as e:
                logger.error(f"Failed to analyze query plan: {e}")
                return {'error': str(e)}
    
    @staticmethod
    def _analyze_plan_for_optimizations(plan) -> List[str]:
        """Analyze execution plan for optimization opportunities"""
        recommendations = []
        
        # This is a simplified analysis - in practice, you'd analyze the actual plan structure
        plan_str = str(plan)
        
        if 'AllNodesScan' in plan_str:
            recommendations.append("Query uses full node scan - consider adding indexes or more specific filters")
        
        if 'CartesianProduct' in plan_str:
            recommendations.append("Query contains Cartesian product - review join conditions")
        
        if 'Sort' in plan_str and 'Limit' in plan_str:
            recommendations.append("Consider adding index for sorting to improve LIMIT performance")
        
        return recommendations


class DatabaseConnectionPool:
    """Optimized database connection pool manager"""
    
    def __init__(self, max_connections: int = 10, max_idle_time: int = 300):
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time  # 5 minutes
        self.active_connections = 0
        self.connection_semaphore = asyncio.Semaphore(max_connections)
        
    async def acquire_connection(self, driver):
        """Acquire database connection with pooling"""
        await self.connection_semaphore.acquire()
        self.active_connections += 1
        
        try:
            session = driver.session()
            return session
        except Exception as e:
            self.connection_semaphore.release()
            self.active_connections -= 1
            raise
    
    def release_connection(self, session):
        """Release database connection"""
        try:
            session.close()
        finally:
            self.connection_semaphore.release()
            self.active_connections -= 1
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            'max_connections': self.max_connections,
            'active_connections': self.active_connections,
            'available_connections': self.max_connections - self.active_connections,
            'utilization_percent': (self.active_connections / self.max_connections) * 100
        }


# Optimized database operations
class OptimizedCaseOperations:
    """Optimized database operations for case management"""
    
    def __init__(self, driver, connection_pool: DatabaseConnectionPool = None):
        self.driver = driver
        self.pool = connection_pool or DatabaseConnectionPool()
    
    @monitor_query_performance
    async def get_user_cases_paginated(self, user_id: str, page: int = 1, limit: int = 20) -> List[dict]:
        """Get user cases with optimized pagination"""
        offset = (page - 1) * limit
        
        session = await self.pool.acquire_connection(self.driver)
        try:
            query = '''
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                WHERE c.status <> 'archived'
                RETURN c
                ORDER BY c.created_at DESC
                SKIP $offset LIMIT $limit
            '''
            
            result = await session.run(query, {
                'user_id': user_id,
                'offset': offset,
                'limit': limit
            })
            
            cases = []
            async for record in result:
                cases.append(dict(record['c']))
            
            return cases
            
        finally:
            self.pool.release_connection(session)
    
    @monitor_query_performance
    async def search_cases_fulltext(self, user_id: str, search_term: str, limit: int = 20) -> List[dict]:
        """Optimized fulltext search for cases"""
        session = await self.pool.acquire_connection(self.driver)
        try:
            # First try fulltext search if index exists
            query = '''
                CALL db.index.fulltext.queryNodes("case_content_search", $search_term) 
                YIELD node, score
                MATCH (node)<-[:OWNS]-(u:User {user_id: $user_id})
                WHERE score > 0.3
                RETURN node as case, score
                ORDER BY score DESC
                LIMIT $limit
            '''
            
            try:
                result = await session.run(query, {
                    'user_id': user_id,
                    'search_term': search_term,
                    'limit': limit
                })
                
                cases = []
                async for record in result:
                    case_data = dict(record['case'])
                    case_data['search_score'] = record['score']
                    cases.append(case_data)
                
                return cases
                
            except Exception:
                # Fallback to simple text search if fulltext index doesn't exist
                fallback_query = '''
                    MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                    WHERE c.chief_complaint CONTAINS $search_term 
                       OR c.description CONTAINS $search_term 
                       OR any(symptom IN c.symptoms WHERE symptom CONTAINS $search_term)
                    RETURN c as case
                    ORDER BY c.created_at DESC
                    LIMIT $limit
                '''
                
                result = await session.run(fallback_query, {
                    'user_id': user_id,
                    'search_term': search_term,
                    'limit': limit
                })
                
                cases = []
                async for record in result:
                    cases.append(dict(record['case']))
                
                return cases
                
        finally:
            self.pool.release_connection(session)


# Performance optimization utilities
def get_database_performance_recommendations() -> List[Dict[str, Any]]:
    """Get comprehensive database performance recommendations"""
    return [
        {
            'category': 'Indexing',
            'recommendations': Neo4jQueryOptimizer.get_index_recommendations()
        },
        {
            'category': 'Query Optimization',
            'recommendations': [
                'Use parameterized queries to enable query plan caching',
                'Limit result sets with LIMIT clause when possible',
                'Use OPTIONAL MATCH instead of multiple MATCH clauses when appropriate',
                'Profile slow queries with PROFILE keyword',
                'Consider using UNION for complex OR conditions'
            ]
        },
        {
            'category': 'Connection Management',
            'recommendations': [
                'Implement connection pooling to reduce overhead',
                'Set appropriate session timeout values',
                'Close sessions promptly after use',
                'Monitor active connection count'
            ]
        },
        {
            'category': 'Data Modeling',
            'recommendations': [
                'Denormalize frequently accessed data',
                'Use appropriate relationship directions',
                'Consider using composite indexes for multi-property queries',
                'Implement proper data archiving strategy'
            ]
        }
    ]