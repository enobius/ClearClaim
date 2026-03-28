"""
Supervisor Agent
================
Reads state["mode"] and logs the routing decision.
Actual routing is handled by conditional edges in graph.py.
This agent exists as a named node so the graph topology matches the architecture diagram.
"""


def supervisor(state: dict) -> dict:
    mode = state.get("mode", "patient")
    return {
        "messages": [{"role": "system", "content": f"Supervisor: routing to {mode} path."}]
    }
