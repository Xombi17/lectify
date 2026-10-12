"""Neo4j service for knowledge graph operations."""
import os
import time
import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver, Session

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "lecturemind")

class Neo4jService:
    _instance: Optional['Neo4jService'] = None
    _driver: Optional[Driver] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jService, cls).__new__(cls)
            cls._instance._driver = GraphDatabase.driver(
                NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            # Verify connectivity
            try:
                cls._instance._driver.verify_connectivity()
                logger.info("Connected to Neo4j at %s", NEO4J_URI)
            except Exception:
                # Don't cache a half-built instance; get_neo4j_service handles reporting.
                cls._instance.close()
                raise
        return cls._instance

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
            Neo4jService._instance = None

    def _get_session(self) -> Session:
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized")
        return self._driver.session()

    def add_lecture_node(self, lecture_id: str, title: str, subject: Optional[str] = None, semester: Optional[str] = None) -> None:
        """Add a lecture node to the graph."""
        with self._get_session() as session:
            session.run(
                """
                MERGE (l:Lecture {id: $lecture_id})
                SET l.title = $title,
                    l.subject = $subject,
                    l.semester = $semester
                """,
                lecture_id=lecture_id,
                title=title,
                subject=subject,
                semester=semester
            )
            logger.debug("Added lecture node: %s", lecture_id)

    def add_concept_node(self, lecture_id: str, concept: str) -> None:
        """Add a concept node and connect it to the lecture."""
        with self._get_session() as session:
            session.run(
                """
                MERGE (c:Concept {name: $concept})
                WITH c
                MATCH (l:Lecture {id: $lecture_id})
                MERGE (l)-[:HAS_CONCEPT]->(c)
                """,
                lecture_id=lecture_id,
                concept=concept
            )
            logger.debug("Added concept node: %s for lecture %s", concept, lecture_id)

    def add_relationship_between_concepts(self, lecture_id: str, concept1: str, concept2: str, relationship_type: str = "RELATED_TO") -> None:
        """Add a relationship between two concepts within the context of a lecture."""
        with self._get_session() as session:
            session.run(
                """
                MATCH (l:Lecture {id: $lecture_id})-[:HAS_CONCEPT]->(c1:Concept {name: $concept1})
                MATCH (l)-[:HAS_CONCEPT]->(c2:Concept {name: $concept2})
                WHERE c1 <> c2
                MERGE (c1)-[r:%s]->(c2)
                SET r.lecture_id = $lecture_id
                """ % relationship_type,
                lecture_id=lecture_id,
                concept1=concept1,
                concept2=concept2
            )
            logger.debug("Added relationship: %s -[%s]-> %s in lecture %s", concept1, relationship_type, concept2, lecture_id)

    def get_lecture_graph(self, lecture_id: str) -> Dict[str, Any]:
        """Retrieve the lecture's concept graph as nodes and edges."""
        with self._get_session() as session:
            # Get lecture info
            lecture_result = session.run(
                """
                MATCH (l:Lecture {id: $lecture_id})
                RETURN l.id as id, l.title as title, l.subject as subject, l.semester as semester
                """,
                lecture_id=lecture_id
            )
            lecture_record = lecture_result.single()
            if not lecture_record:
                return {"nodes": [], "edges": []}

            # Get concepts and relationships
            graph_result = session.run(
                """
                MATCH (l:Lecture {id: $lecture_id})-[:HAS_CONCEPT]->(c:Concept)
                OPTIONAL MATCH (l)-[:HAS_CONCEPT]->(c1:Concept)-[r]->(c2:Concept)-[:HAS_CONCEPT]->(l)
                WHERE c1 <> c2 AND TYPE(r) IN ['RELATED_TO', 'PREREQUISITE', 'EXAMPLE_OF']
                RETURN 
                    collect(distinct {id: c.name, name: c.name, type: 'concept'}) as concepts,
                    collect(distinct {start: c1.name, end: c2.name, type: TYPE(r)}) as edges
                """,
                lecture_id=lecture_id
            )
            record = graph_result.single()
            concepts = record["concepts"] if record else []
            edges = record["edges"] if record else []
            # Filter out None edges
            edges = [e for e in edges if e["start"] and e["end"]]
            return {
                "lecture": {
                    "id": lecture_record["id"],
                    "title": lecture_record["title"],
                    "subject": lecture_record["subject"],
                    "semester": lecture_record["semester"]
                },
                "nodes": concepts,
                "edges": edges
            }

    def search_concepts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for concepts by name (fuzzy match)."""
        with self._get_session() as session:
            result = session.run(
                """
                MATCH (c:Concept)
                WHERE c.name CONTAINS $query
                RETURN c.name as name
                LIMIT $limit
                """,
                query=query,
                limit=limit
            )
            return [{"name": record["name"]} for record in result]

# Singleton instance getter
class Neo4jUnavailable(RuntimeError):
    """Neo4j is unreachable (non-fatal for callers)."""


_COOLDOWN_S = 60.0
_down_until = 0.0


def get_neo4j_service() -> Neo4jService:
    """Return the service; after a failed connect, fail fast for a cooldown (one WARNING)."""
    global _down_until
    if Neo4jService._instance is not None:
        return Neo4jService._instance
    if time.monotonic() < _down_until:
        raise Neo4jUnavailable("Neo4j unreachable (cooldown)")
    try:
        return Neo4jService()
    except Exception as e:
        _down_until = time.monotonic() + _COOLDOWN_S
        logger.warning("Neo4j unreachable at %s (%s); skipping graph sync for %ds",
                       NEO4J_URI, type(e).__name__, _COOLDOWN_S)
        raise Neo4jUnavailable(str(e)) from e