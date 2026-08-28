# Simple diagnostic SOP knowledge base
sops = [
    "SOP-101: If vibration telemetry spikes alongside high temperature, inspect bearing lubrication immediately.",
    "SOP-102: If optical surface anomaly is detected without telemetry fluctuations, clear camera lens and verify lighting.",
    "SOP-103: If multi-modal trust gating fails, halt line operation and recalibrate sensor synchronization."
]

def get_diagnostic_explanation(query_text):
    """Simple keyword retriever to match issues against SOPs."""
    for sop in sops:
        if any(word in query_text.lower() for word in sop.lower().split()):
            return sop
    return "SOP-000: Standard operating parameters within normal limits. Monitor telemetry."