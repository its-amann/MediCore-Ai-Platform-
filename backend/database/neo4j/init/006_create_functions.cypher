// 006_create_functions.cypher
// Unified Medical AI Platform - Custom Functions and Procedures
// This script creates useful functions and procedures for the application
// Run this script after all other initialization scripts

// Note: These are example queries that would typically be implemented
// as stored procedures in Neo4j. For actual implementation, you would
// need to create these as Java/Kotlin procedures or use APOC procedures.

// Example: Find similar cases using vector similarity
// This would be implemented as a custom procedure
/*
CALL medical.findSimilarCases($caseId, $limit) YIELD case, score
WHERE score > 0.8
RETURN case, score
ORDER BY score DESC;
*/

// Example: Get user's case timeline
/*
CALL medical.getUserCaseTimeline($userId, $startDate, $endDate) 
YIELD date, caseCount, analysisCount, messageCount
RETURN date, caseCount, analysisCount, messageCount
ORDER BY date;
*/

// Example: Calculate doctor performance metrics
/*
CALL medical.getDoctorPerformance($doctorId, $period)
YIELD metric, value
RETURN metric, value;
*/

// Useful query templates that can be used directly:

// 1. Get case with full context (all related data)
// Use: CALL db.query($getCaseFullContext, {caseId: 'case_001'})
WITH '
MATCH (c:Case {case_id: $caseId})
OPTIONAL MATCH (c)<-[:OWNS]-(owner:User)
OPTIONAL MATCH (c)-[:HAS_ANALYSIS]->(a:Analysis)
OPTIONAL MATCH (a)-[:ANALYZED_BY]->(d:Doctor)
OPTIONAL MATCH (c)-[:CONTAINS_MEDIA]->(m:Media)
OPTIONAL MATCH (c)-[:HAS_CHAT_HISTORY]->(ch:ChatHistory)
OPTIONAL MATCH (c)-[:GENERATES]->(r:Report)
OPTIONAL MATCH (c)<-[:DISCUSSES]-(room:Room)
WITH c, owner, 
     collect(DISTINCT {analysis: a, doctor: d}) as analyses,
     collect(DISTINCT m) as media,
     collect(DISTINCT ch) as chatHistory,
     collect(DISTINCT r) as reports,
     collect(DISTINCT room) as rooms
RETURN c as case, 
       owner,
       analyses,
       media,
       chatHistory,
       reports,
       rooms
' AS getCaseFullContext
RETURN getCaseFullContext;

// 2. Get user's dashboard data
// Use: CALL db.query($getUserDashboard, {userId: 'user_001'})
WITH '
MATCH (u:User {user_id: $userId})
OPTIONAL MATCH (u)-[:OWNS]->(c:Case)
WITH u, count(c) as totalCases,
     count(CASE WHEN c.status = "active" THEN 1 END) as activeCases,
     count(CASE WHEN c.status = "closed" THEN 1 END) as closedCases
OPTIONAL MATCH (u)-[:PARTICIPATES_IN]->(r:Room {status: "active"})
WITH u, totalCases, activeCases, closedCases, count(r) as activeRooms
OPTIONAL MATCH (u)-[:RECEIVED_INVITATION]->(inv:Invitation {status: "pending"})
WITH u, totalCases, activeCases, closedCases, activeRooms, count(inv) as pendingInvitations
OPTIONAL MATCH (u)-[:HAS_CHAT_HISTORY]->(ch:ChatHistory)
WHERE ch.timestamp > datetime() - duration("P7D")
RETURN {
  user: u,
  stats: {
    totalCases: totalCases,
    activeCases: activeCases,
    closedCases: closedCases,
    activeRooms: activeRooms,
    pendingInvitations: pendingInvitations,
    recentChats: count(ch)
  }
} as dashboard
' AS getUserDashboard
RETURN getUserDashboard;

// 3. Find cases by symptoms (text search + vector similarity)
// Use: CALL db.query($findCasesBySymptoms, {symptoms: ['chest pain', 'shortness of breath'], embedding: [...]})
WITH '
MATCH (c:Case)
WHERE any(symptom IN $symptoms WHERE symptom IN c.symptoms)
WITH c, size([s IN $symptoms WHERE s IN c.symptoms]) as matchCount
ORDER BY matchCount DESC
LIMIT 20
CALL db.index.vector.queryNodes("case_similarity", 10, $embedding)
YIELD node as similarCase, score
WHERE similarCase.case_id = c.case_id
RETURN c as case, matchCount, score as similarityScore
ORDER BY matchCount DESC, similarityScore DESC
LIMIT 10
' AS findCasesBySymptoms
RETURN findCasesBySymptoms;

// 4. Get doctor availability and workload
// Use: CALL db.query($getDoctorWorkload, {specialty: 'cardiologist'})
WITH '
MATCH (d:Doctor {specialty: $specialty, is_active: true})
OPTIONAL MATCH (d)<-[:ANALYZED_BY]-(a:Analysis)
WHERE a.created_at > datetime() - duration("P1D")
WITH d, count(a) as recentAnalyses
OPTIONAL MATCH (d)-[:PARTICIPATED_IN_CHAT]->(ch:ChatHistory)
WHERE ch.timestamp > datetime() - duration("PT1H")
WITH d, recentAnalyses, count(ch) as recentChats
RETURN d as doctor,
       recentAnalyses,
       recentChats,
       d.consultation_count as totalConsultations,
       d.average_rating as rating,
       CASE 
         WHEN recentAnalyses < 10 AND recentChats < 5 THEN "available"
         WHEN recentAnalyses < 20 AND recentChats < 10 THEN "moderate"
         ELSE "busy"
       END as availability
ORDER BY availability, rating DESC
' AS getDoctorWorkload
RETURN getDoctorWorkload;

// 5. Get collaboration room analytics
// Use: CALL db.query($getRoomAnalytics, {roomId: 'room_001'})
WITH '
MATCH (r:Room {room_id: $roomId})
OPTIONAL MATCH (r)<-[:PARTICIPATES_IN]-(u:User)
WITH r, count(DISTINCT u) as participantCount
OPTIONAL MATCH (r)-[:HAS_MESSAGE]->(m:Message)
WHERE m.timestamp > datetime() - duration("P1D")
WITH r, participantCount, count(m) as dailyMessages
OPTIONAL MATCH (r)-[:DISCUSSES]->(c:Case)
WITH r, participantCount, dailyMessages, collect(c.case_id) as discussedCases
OPTIONAL MATCH (r)-[:HAS_CHAT_HISTORY]->(ch:ChatHistory)
RETURN {
  room: r,
  analytics: {
    participantCount: participantCount,
    dailyMessages: dailyMessages,
    discussedCases: discussedCases,
    totalChats: count(ch),
    lastActivity: r.last_activity,
    isActive: r.status = "active"
  }
} as roomAnalytics
' AS getRoomAnalytics
RETURN getRoomAnalytics;

// 6. Medical category statistics
// Use: CALL db.query($getMedicalCategoryStats, {})
WITH '
MATCH (c:Case)
WITH c.medical_category as category, count(*) as caseCount,
     avg(c.urgency_level) as avgUrgency,
     count(CASE WHEN c.status = "active" THEN 1 END) as activeCases,
     count(CASE WHEN c.outcome = "Resolved with treatment" THEN 1 END) as successfulOutcomes
RETURN category,
       caseCount,
       round(avgUrgency, 2) as avgUrgency,
       activeCases,
       successfulOutcomes,
       round(toFloat(successfulOutcomes) / caseCount * 100, 2) as successRate
ORDER BY caseCount DESC
' AS getMedicalCategoryStats
RETURN getMedicalCategoryStats;

// 7. User activity timeline
// Use: CALL db.query($getUserActivityTimeline, {userId: 'user_001', days: 7})
WITH '
MATCH (u:User {user_id: $userId})
OPTIONAL MATCH (u)-[:OWNS]->(c:Case)
WHERE c.created_at > datetime() - duration("P" + toString($days) + "D")
WITH u, collect({type: "case_created", timestamp: c.created_at, title: c.title}) as caseEvents
OPTIONAL MATCH (u)-[:HAS_CHAT_HISTORY]->(ch:ChatHistory)
WHERE ch.timestamp > datetime() - duration("P" + toString($days) + "D")
WITH u, caseEvents, collect({type: "chat", timestamp: ch.timestamp, doctor: ch.doctor_specialty}) as chatEvents
OPTIONAL MATCH (u)-[:SENT]->(m:Message)
WHERE m.timestamp > datetime() - duration("P" + toString($days) + "D")
WITH u, caseEvents + chatEvents + collect({type: "message", timestamp: m.timestamp}) as allEvents
UNWIND allEvents as event
RETURN event
ORDER BY event.timestamp DESC
' AS getUserActivityTimeline
RETURN getUserActivityTimeline;

// 8. Find expertise matches for case
// Use: CALL db.query($findExpertiseMatches, {caseId: 'case_001'})
WITH '
MATCH (c:Case {case_id: $caseId})
MATCH (d:Doctor {is_active: true})
WHERE c.medical_category IN d.expertise_areas OR 
      any(symptom IN c.symptoms WHERE symptom IN d.expertise_areas)
WITH c, d, 
     size([e IN d.expertise_areas WHERE e = c.medical_category OR e IN c.symptoms]) as matchScore
RETURN d as doctor,
       matchScore,
       d.average_rating as rating,
       d.consultation_count as experience
ORDER BY matchScore DESC, rating DESC
LIMIT 5
' AS findExpertiseMatches
RETURN findExpertiseMatches;