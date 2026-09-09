# Fixed, fully-specified problems for the eval harness. Each query bakes in the numbers/
# constraints a real interviewer would give if asked, so the pipeline runs non-interactively
# without needing a clarifying-question round.

PROBLEMS = [
    {
        "id": "url_shortener",
        "query": (
            "Design a URL shortener like bit.ly. Assume 100M new short URLs created per month, "
            "a 100:1 read:write ratio on redirects, redirects must respond in under 100ms at p99, "
            "links do not expire by default but users can optionally set an expiry, and custom "
            "aliases are supported."
        ),
    },
    {
        "id": "chat_system",
        "query": (
            "Design a WhatsApp-scale one-on-one and group chat system supporting 500M daily "
            "active users, with message delivery guarantees (at-least-once, ordered per "
            "conversation), online/offline presence, and group chats up to 256 members."
        ),
    },
    {
        "id": "ride_sharing_dispatch",
        "query": (
            "Design the rider-driver matching and dispatch system for a ride-sharing app "
            "operating in 50 major cities, matching a rider to the nearest available driver "
            "within 3 seconds, with driver locations updated every 4 seconds and real-time ETA "
            "updates during a trip."
        ),
    },
    {
        "id": "payments_ledger",
        "query": (
            "Design a payments ledger for an e-commerce platform processing 5,000 transactions "
            "per second at peak, requiring exactly-once processing (no double charges on client "
            "retries), an immutable audit trail for every balance change, and strong consistency "
            "on account balance reads."
        ),
    },
]
