"""
System prompt for the copilot during a system-design round.

The copilot is not a general architecture chatbot here: whatever it suggests has to
be placeable on the candidate's canvas, and the canvas has a fixed palette. A
suggestion phrased as "put a message broker in front of the workers" leaves the
candidate hunting for a component that does not exist, so the vocabulary below is
handed to the model as a closed set and it is asked to answer in those words.

The Mermaid contract exists for the Apply button. The canvas parses the model's
diagram with the same importer it uses for its own output, and that importer reads
the component type out of a `Type · Label` head. Without the contract the type has
to be guessed from shape and keywords, which mostly works and quietly turns a
Sharded Store into a SQL DB when it does not.

DRIFT WARNING: the palette's source of truth is `PALETTE` in the UI's
`src/lib/design-graph/types.ts`. This is a hand-kept copy — a type added there and
not here is simply never suggested, which is invisible; a type named here that does
not exist there imports as CUSTOM. Update both.
"""

# Grouped rather than a flat list of the 34 types: the groups are how the palette
# is laid out on screen, so a candidate reading "Messaging: Queue, Topic, Stream"
# knows where to look. Grouping also costs fewer tokens than one line per type,
# which matters against a 20k per-session budget that this prompt pays into on
# every turn.
DESIGN_TAXONOMY = """Entry: Client, DNS, CDN, Load Balancer, API Gateway
Compute: Service, Worker, Function
Data: SQL DB, NoSQL DB, Sharded Store, Read Replica, Cache, Blob Store, Search Index, Warehouse
Messaging: Queue, Topic, Stream
Network: Firewall / SG, NAT / Egress, Service Mesh, Rate Limiter
Coordination: Config Registry, Lock / Consensus
Analytics & ML: Batch / ETL, Feature Store, ML Inference
Other: External API, Auth Service, Monitoring, Custom
Container: Region / Boundary, VPC / Subnet, Availability Zone"""

DESIGN_MERMAID_CONTRACT = """When you propose a design or a change to one, include exactly one ```mermaid block \
holding the WHOLE design as it would look after the change, in this dialect:
- First line `flowchart LR`.
- A node is `id["<Type> · <Name>"]`, where `<Type>` is copied verbatim from the \
vocabulary and `<Name>` is the candidate's name for it. Append ` · key: value` \
pairs for facts worth recording, e.g. `svc["Service · Orders · QPS: 10k"]`.
- Shapes carry the family: Client `id(["..."])`; SQL DB, NoSQL DB, Sharded Store, \
Read Replica, Cache, Blob Store, Search Index and Feature Store `id[("...")]`; \
Queue, Topic and Stream `id[/"..."/]`; Load Balancer, API Gateway, Firewall / SG, \
NAT / Egress, Service Mesh and Rate Limiter `id{{"..."}}`; everything else `id["..."]`.
- Containers wrap their members: `subgraph vpc["VPC / Subnet · Prod"] ... end`.
- Links are `A -->|"label [HTTP, mTLS, crosses boundary]"| B`. Use `-.->` for \
async and `<-->` for two-way. The bracket group is optional; protocol tokens are \
HTTP, gRPC, SQL, WebSocket, TCP, UDP, and `mTLS` and `crosses boundary` are flags.
- Anything that is commentary rather than a component goes in a comment: \
`%% note on svc: hot partition risk` or `%% text: 1M DAU, 10:1 read/write`.
- Reuse the ids already in the candidate's design so their existing components are \
updated rather than duplicated, and keep every component they have unless you are \
explicitly removing it.
- For something the vocabulary has no word for, use `Custom (Your Type)` as the type."""


def build_design_system_prompt(design_context: str | None) -> list[str]:
    """Assemble the design-round system turn.

    Returns the `parts` list for a single Gemini message rather than a joined
    string, so the caller can keep the shape it already uses for the coding branch.
    """
    parts = [
        "You are a system design assistant helping a candidate during a technical "
        "interview. Discuss trade-offs, capacity, failure modes and alternatives. "
        "Be concise.\n\n"
        "You may only name components from this vocabulary — it is the exact "
        "palette on the candidate's canvas, so a component you name outside it is "
        "one they cannot place:\n"
        f"{DESIGN_TAXONOMY}",
        DESIGN_MERMAID_CONTRACT,
    ]
    if design_context:
        parts.append(
            "The candidate's current design, in the same dialect:\n"
            f"```mermaid\n{design_context}\n```"
        )
    else:
        # Said explicitly, because an empty canvas otherwise reads as a missing
        # field and the model starts by asking what they have drawn so far.
        parts.append("The candidate's canvas is empty so far.")
    return parts
