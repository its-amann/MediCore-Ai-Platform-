// 003_create_vector_indexes.cypher
// Unified Medical AI Platform - Neo4j Vector Indexes
// This script creates vector indexes for semantic search capabilities
// Run this script after basic indexes are created

// Case Similarity Vector Index
// Used for finding similar medical cases based on symptoms, descriptions, and diagnoses
CALL db.index.vector.createNodeIndex(
  'case_similarity',
  'Case',
  'embedding',
  1536,
  'cosine'
) YIELD indexName, labelsOrTypes, properties, providerName, options, state
RETURN indexName, labelsOrTypes, properties, providerName, options, state;

// Analysis Similarity Vector Index
// Used for finding similar analyses based on findings and recommendations
CALL db.index.vector.createNodeIndex(
  'analysis_similarity',
  'Analysis',
  'embedding',
  1536,
  'cosine'
) YIELD indexName, labelsOrTypes, properties, providerName, options, state
RETURN indexName, labelsOrTypes, properties, providerName, options, state;

// Note: Additional vector indexes can be created for other node types as needed
// Example formats for future vector indexes:

// Doctor Expertise Vector Index (for future implementation)
// CALL db.index.vector.createNodeIndex(
//   'doctor_expertise',
//   'Doctor',
//   'expertise_embedding',
//   1536,
//   'cosine'
// );

// Report Content Vector Index (for future implementation)
// CALL db.index.vector.createNodeIndex(
//   'report_content',
//   'Report',
//   'content_embedding',
//   1536,
//   'cosine'
// );

// Media Description Vector Index (for future implementation)
// CALL db.index.vector.createNodeIndex(
//   'media_description',
//   'Media',
//   'description_embedding',
//   1536,
//   'cosine'
// );