def to_mermaid(architecture: dict) -> str:
    """Render the architecture's components/connections as a Mermaid flowchart.
    Deterministic (no LLM call needed) since it's a direct data transformation.
    """
    lines = ["flowchart LR"]

    def node_id(name: str) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in name)

    shape_by_type = {
        "relational datastore": ("[(", ")]"),
        "datastore": ("[(", ")]"),
        "cache": ("{{", "}}"),
        "queue": ("([", "])"),
        "object storage": ("[(", ")]"),
        "cdn": ("([", "])"),
    }

    for component in architecture.get("components", []):
        name = component["name"]
        ctype = component.get("type", "").lower()
        open_b, close_b = shape_by_type.get(ctype, ("[", "]"))
        lines.append(f'    {node_id(name)}{open_b}"{name}"{close_b}')

    for conn in architecture.get("connections", []):
        src, dst, purpose = conn["from"], conn["to"], conn.get("purpose", "")
        label = f'|"{purpose}"|' if purpose else ""
        lines.append(f"    {node_id(src)} -->{label} {node_id(dst)}")

    return "\n".join(lines)
