"""Deterministic hallucination proxy for the final write-up — no LLM judge grading itself here.

Definition used: the Presenter's narrative "hallucinates" if it names a specific real-world
technology that was never actually selected (or even considered and rejected) by the Tech Lead
for this design. The Presenter only ever *sees* the Tech Lead's structured choices — if a named
technology shows up in the prose that isn't traceable to that input, it was invented at the
write-up stage, not carried forward from an earlier reasoning step.

`alternative_considered` counts as grounded too: "we picked Postgres over MySQL because..." is a
legitimate tradeoff mention, not a fabrication, even though MySQL wasn't chosen.

This is a proxy, not a full hallucination detector — it only catches fabricated *technology
choices*, not fabricated numbers or claims. Documented as a known limitation, not silently implied
to be complete.
"""

import re

TECH_VOCAB = [
    "PostgreSQL", "Postgres", "MySQL", "MariaDB", "SQLite", "MongoDB", "Cassandra", "DynamoDB",
    "Redis", "Memcached", "Kafka", "RabbitMQ", "SQS", "SNS", "Kinesis", "Pulsar", "ActiveMQ",
    "S3", "Google Cloud Storage", "Azure Blob Storage", "HDFS", "MinIO",
    "Elasticsearch", "OpenSearch", "Solr", "Algolia",
    "CDN", "Cloudflare", "Fastly", "Akamai", "CloudFront",
    "Zookeeper", "etcd", "Consul",
    "gRPC", "GraphQL", "WebSocket", "Protobuf", "Thrift",
    "Nginx", "HAProxy", "Envoy", "Traefik",
    "Kubernetes", "Docker", "ECS", "Lambda",
    "Spanner", "CockroachDB", "TiDB", "Vitess", "YugabyteDB",
    "BigTable", "ClickHouse", "Snowflake", "BigQuery", "Redshift",
    "Neo4j", "InfluxDB", "TimescaleDB", "Prometheus", "Grafana",
]


def find_mentions(text: str, vocab: list[str]) -> set[str]:
    found = set()
    for term in vocab:
        if re.search(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE):
            found.add(term)
    return found


# Colloquial short forms the narrative may use for a technology the Tech Lead named in full.
ALIASES = {
    "postgres": "postgresql",
    "mongo": "mongodb",
    "es": "elasticsearch",
}


def _is_grounded(term: str, grounded_texts: set[str]) -> bool:
    # The Tech Lead often hedges with compound values like "CockroachDB (or Google Cloud Spanner
    # if on GCP)" in a single field — a set-membership check against the whole string would miss
    # that "CockroachDB" is genuinely the grounded choice, so this checks substring containment
    # (word-boundaried) against each grounded string instead of exact equality.
    candidates = {term.lower(), ALIASES.get(term.lower(), term.lower())}
    return any(
        re.search(r"\b" + re.escape(c) + r"\b", text)
        for c in candidates
        for text in grounded_texts
    )


def run(design: dict) -> dict:
    tech = design["tech"]
    explanation = design["explanation"]
    narrative = f"{explanation.get('summary', '')}\n{explanation.get('narrative', '')}"

    grounded = set()
    for choice in tech.get("choices", []):
        for field in ("technology", "alternative_considered"):
            value = (choice.get(field) or "").strip()
            if value:
                grounded.add(value.lower())

    mentioned = find_mentions(narrative, TECH_VOCAB)
    ungrounded = sorted(m for m in mentioned if not _is_grounded(m, grounded))

    return {
        "mentioned_technologies": sorted(mentioned),
        "grounded_technologies": sorted(grounded),
        "ungrounded_technologies": ungrounded,
        "hallucinated": len(ungrounded) > 0,
    }
