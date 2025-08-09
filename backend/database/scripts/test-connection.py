"""
Test script to verify database connection and MCP server functionality
"""
import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.database.neo4j_client import Neo4jClient
from app.core.mcp.history_server import HistoryServer
from app.core.config import settings

async def test_connections():
    """Test database connection and MCP server"""
    print("=" * 60)
    print("Testing Medical AI Database and MCP Server Connections")
    print("=" * 60)
    
    # Test Neo4j connection
    print("\n1. Testing Neo4j Database Connection...")
    print(f"   URI: {settings.neo4j_uri}")
    
    try:
        neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        await neo4j_client.connect()
        
        # Test query
        result = await neo4j_client.execute_query("MATCH (d:Doctor) RETURN count(d) as count")
        doctor_count = result[0]['count'] if result else 0
        print(f"   ✅ Connected successfully!")
        print(f"   ✅ Found {doctor_count} doctors in database")
        
        # Check constraints and indexes
        constraints = await neo4j_client.execute_query("SHOW CONSTRAINTS")
        indexes = await neo4j_client.execute_query("SHOW INDEXES")
        print(f"   ✅ Constraints: {len(constraints)}")
        print(f"   ✅ Indexes: {len(indexes)}")
        
    except Exception as e:
        print(f"   ❌ Failed to connect: {e}")
        return False
    
    # Test MCP History Server
    print("\n2. Testing MCP History Server...")
    try:
        history_server = HistoryServer(neo4j_client)
        print("   ✅ MCP History Server initialized successfully")
        
        # Test PubMed client
        print("\n3. Testing PubMed Integration...")
        if hasattr(history_server, 'pubmed_client'):
            print("   ✅ PubMed client is available")
        else:
            print("   ⚠️  PubMed client not found")
            
    except Exception as e:
        print(f"   ❌ Failed to initialize MCP server: {e}")
        return False
    
    # Test Redis connection (optional)
    print("\n4. Testing Redis Connection (Optional)...")
    try:
        import redis.asyncio as redis
        redis_client = await redis.from_url(settings.redis_url)
        await redis_client.ping()
        print(f"   ✅ Redis connected at {settings.redis_url}")
        await redis_client.close()
    except Exception as e:
        print(f"   ⚠️  Redis not available (optional): {e}")
    
    # Cleanup
    await neo4j_client.close()
    
    print("\n" + "=" * 60)
    print("✅ All critical services are properly configured!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_connections())
    sys.exit(0 if success else 1)