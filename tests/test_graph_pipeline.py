from agentx.layers.orchestrator.graph import build_graph


def test_graph_has_detect_validate_repair_nodes():
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert "detect" in node_names
    assert "validate" in node_names
    assert "repair" in node_names
    assert "transaction_processing" not in node_names


def test_graph_edges_detect_validate_repair_chain():
    graph = build_graph()
    edge_pairs = {(e.source, e.target) for e in graph.get_graph().edges}
    assert ("ingest", "detect") in edge_pairs
    assert ("detect", "validate") in edge_pairs

    validate_targets = {target for source, target in edge_pairs if source == "validate"}
    assert validate_targets & {"repair", "human_review"}

    repair_targets = {target for source, target in edge_pairs if source == "repair"}
    assert repair_targets & {"route", "human_review"}
