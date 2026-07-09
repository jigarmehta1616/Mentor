"""Seed a couple of topic prerequisite DAGs.

Each concept lists the prerequisites that must be learned first (prereq -> concept
edges). These are plain data so tests and the planner can consume them without a DB.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import text

from app.db.engine import get_engine
from app.lib.logger import get_logger

logger = get_logger()


@dataclass(frozen=True)
class SeedConcept:
    id: str
    name: str
    summary: str
    difficulty: int
    prereqs: list[str] = field(default_factory=list)


# --- Topic: Neural Networks --------------------------------------------------
NEURAL_NETWORKS: list[SeedConcept] = [
    SeedConcept("nn.linear_algebra", "Vectors & Matrices", "The math objects a network operates on.", 1),
    SeedConcept("nn.derivatives", "Derivatives & Gradients", "How outputs change with inputs.", 1),
    SeedConcept("nn.perceptron", "The Perceptron", "A single weighted neuron.", 2, ["nn.linear_algebra"]),
    SeedConcept("nn.activations", "Activation Functions", "Non-linearities like ReLU and sigmoid.", 2, ["nn.perceptron"]),
    SeedConcept("nn.forward", "Forward Pass", "Propagating inputs to a prediction.", 2, ["nn.activations", "nn.linear_algebra"]),
    SeedConcept("nn.loss", "Loss Functions", "Quantifying how wrong a prediction is.", 2, ["nn.forward"]),
    SeedConcept("nn.gradient_descent", "Gradient Descent", "Stepping downhill on the loss.", 3, ["nn.loss", "nn.derivatives"]),
    SeedConcept("nn.backprop", "Backpropagation", "Efficient gradients via the chain rule.", 4, ["nn.gradient_descent"]),
    SeedConcept("nn.overfitting", "Overfitting", "Memorizing instead of generalizing.", 3, ["nn.backprop"]),
    SeedConcept("nn.regularization", "Regularization", "Dropout, weight decay, early stopping.", 3, ["nn.overfitting"]),
]

# --- Topic: SQL --------------------------------------------------------------
SQL: list[SeedConcept] = [
    SeedConcept("sql.relational_model", "The Relational Model", "Tables, rows, keys.", 1),
    SeedConcept("sql.select", "SELECT Basics", "Reading columns from a table.", 1, ["sql.relational_model"]),
    SeedConcept("sql.filtering", "Filtering with WHERE", "Restricting rows by predicate.", 1, ["sql.select"]),
    SeedConcept("sql.joins", "Joins", "Combining rows across tables.", 2, ["sql.filtering"]),
    SeedConcept("sql.aggregation", "Aggregation", "COUNT, SUM, AVG over rows.", 2, ["sql.filtering"]),
    SeedConcept("sql.group_by", "GROUP BY & HAVING", "Aggregating within groups.", 2, ["sql.aggregation"]),
    SeedConcept("sql.subqueries", "Subqueries", "Queries nested inside queries.", 3, ["sql.joins", "sql.group_by"]),
    SeedConcept("sql.indexes", "Indexes", "B-trees that make lookups O(log n).", 3, ["sql.joins"]),
    SeedConcept("sql.transactions", "Transactions & ACID", "Atomic, consistent units of work.", 3, ["sql.subqueries"]),
]

TOPICS: dict[str, list[SeedConcept]] = {
    "neural-networks": NEURAL_NETWORKS,
    "sql": SQL,
}


def seed_all() -> None:
    """Insert all seed topics idempotently. O(V + E) over the seed data."""
    engine = get_engine()
    with engine.begin() as conn:
        for topic, concepts in TOPICS.items():
            for c in concepts:
                conn.execute(
                    text(
                        "INSERT INTO concepts (id, topic, name, summary, difficulty) "
                        "VALUES (:id, :topic, :name, :summary, :difficulty) "
                        "ON CONFLICT (id) DO NOTHING"
                    ),
                    {"id": c.id, "topic": topic, "name": c.name, "summary": c.summary, "difficulty": c.difficulty},
                )
                for prereq in c.prereqs:
                    conn.execute(
                        text(
                            "INSERT INTO concept_edges (concept_id, prereq_id) "
                            "VALUES (:cid, :pid) ON CONFLICT DO NOTHING"
                        ),
                        {"cid": c.id, "pid": prereq},
                    )
    logger.info("Seeded %d topics.", len(TOPICS))


def edges_for_topic(topic: str) -> dict[str, list[str]]:
    """Return an adjacency map {concept_id: [prereq_ids]} for a seed topic. O(V + E)."""
    return {c.id: list(c.prereqs) for c in TOPICS.get(topic, [])}
