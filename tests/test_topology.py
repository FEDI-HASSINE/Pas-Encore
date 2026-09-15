import pytest

from src.env.topology import build_topology, build_nodes, build_links, Topology
from src.env.node import Node
from src.env.link import Link


def test_build_nodes_table1():
    """Verify build_nodes instantiates the 4 nodes conforming to Table 1."""
    nodes = build_nodes()
    assert len(nodes) == 4
    assert set(nodes.keys()) == {"LEO-1", "LEO-2", "GS-Tunisia", "Cloud-AWS"}

    # LEO-1
    leo1 = nodes["LEO-1"]
    assert leo1.id == "LEO-1"
    assert leo1.cpu_capacity == 10.0
    assert leo1.ram_capacity == 32.0
    assert leo1.energy_cost == 2.0
    assert leo1.startup_penalty == 5.0
    assert leo1.sensor_noise == 0.05
    assert leo1.cpu_utilized == 0.0

    # LEO-2
    leo2 = nodes["LEO-2"]
    assert leo2.id == "LEO-2"
    assert leo2.cpu_capacity == 10.0
    assert leo2.ram_capacity == 32.0
    assert leo2.energy_cost == 2.0
    assert leo2.startup_penalty == 5.0
    assert leo2.sensor_noise == 0.05
    assert leo2.cpu_utilized == 0.0

    # GS-Tunisia
    gs = nodes["GS-Tunisia"]
    assert gs.id == "GS-Tunisia"
    assert gs.cpu_capacity == 20.0
    assert gs.ram_capacity == 64.0
    assert gs.energy_cost == 0.5
    assert gs.startup_penalty == 1.0
    assert gs.sensor_noise == 0.01
    assert gs.cpu_utilized == 0.0

    # Cloud-AWS
    cloud = nodes["Cloud-AWS"]
    assert cloud.id == "Cloud-AWS"
    assert cloud.cpu_capacity == 100.0
    assert cloud.ram_capacity == 256.0
    assert cloud.energy_cost == 0.1
    assert cloud.startup_penalty == 0.0
    assert cloud.sensor_noise == 0.0
    assert cloud.cpu_utilized == 0.0


def test_build_links_table2():
    """Verify build_links instantiates the 4 links conforming to Table 2."""
    links = build_links()
    assert len(links) == 4

    # Helper to find link
    def find_link(n1: str, n2: str) -> Link:
        for l in links:
            if (l.node1 == n1 and l.node2 == n2) or (l.node1 == n2 and l.node2 == n1):
                return l
        raise AssertionError(f"Link {n1} <-> {n2} not found")

    # 1. LEO-1 <-> GS-Tunisia: 10 Mbps, active for 600s every 5400s (offset 0s)
    l_leo1_gs = find_link("LEO-1", "GS-Tunisia")
    assert l_leo1_gs.bandwidth == 10.0
    assert l_leo1_gs.is_active(0) is True
    assert l_leo1_gs.is_active(500) is True
    assert l_leo1_gs.is_active(600) is False
    assert l_leo1_gs.is_active(5400) is True

    # 2. LEO-2 <-> GS-Tunisia: 10 Mbps, active for 600s every 5400s (offset 2700s)
    l_leo2_gs = find_link("LEO-2", "GS-Tunisia")
    assert l_leo2_gs.bandwidth == 10.0
    assert l_leo2_gs.is_active(0) is False
    assert l_leo2_gs.is_active(2700) is True
    assert l_leo2_gs.is_active(3200) is True
    assert l_leo2_gs.is_active(3300) is False

    # 3. GS-Tunisia <-> Cloud-AWS: 100 Mbps, always active
    l_gs_cloud = find_link("GS-Tunisia", "Cloud-AWS")
    assert l_gs_cloud.bandwidth == 100.0
    assert l_gs_cloud.always_active is True
    assert l_gs_cloud.is_active(0) is True
    assert l_gs_cloud.is_active(50000) is True

    # 4. LEO-1 <-> LEO-2 (ISL): 50 Mbps, always active
    l_isl = find_link("LEO-1", "LEO-2")
    assert l_isl.bandwidth == 50.0
    assert l_isl.always_active is True
    assert l_isl.is_active(0) is True
    assert l_isl.is_active(50000) is True


def test_build_topology_unpacking():
    """Verify build_topology can be unpacked as (nodes, links)."""
    nodes, links = build_topology()
    assert isinstance(nodes, dict)
    assert isinstance(links, list)
    assert len(nodes) == 4
    assert len(links) == 4


def test_topology_object_methods():
    """Verify Topology helper methods and mapping interface."""
    topo = build_topology()

    # Mapping access
    assert topo["LEO-1"].cpu_capacity == 10.0
    assert "GS-Tunisia" in topo
    assert "UnknownNode" not in topo
    assert topo.get("Cloud-AWS") is not None
    assert len(topo) == 4

    # Node & Link retrieval
    assert topo.get_node("LEO-2").id == "LEO-2"
    assert topo.get_node("NonExistent") is None

    # Bidirectional link lookup
    l1 = topo.get_link("LEO-1", "GS-Tunisia")
    l2 = topo.get_link("GS-Tunisia", "LEO-1")
    assert l1 is not None
    assert l1 == l2

    assert topo.get_link("LEO-1", "Cloud-AWS") is None

    # Connectivity check
    assert topo.is_connected("LEO-1", "GS-Tunisia", current_time=0) is True
    assert topo.is_connected("LEO-1", "GS-Tunisia", current_time=600) is False
    assert topo.is_connected("GS-Tunisia", "Cloud-AWS", current_time=10000) is True
    assert topo.is_connected("LEO-1", "Cloud-AWS", current_time=0) is False


def test_topology_reset():
    """Verify resetting the topology clears task load across all nodes."""
    topo = build_topology()
    topo["LEO-1"].add_task(5.0)
    topo["GS-Tunisia"].add_task(10.0)

    assert topo["LEO-1"].cpu_utilized == 5.0
    assert topo["GS-Tunisia"].cpu_utilized == 10.0

    topo.reset()

    assert topo["LEO-1"].cpu_utilized == 0.0
    assert topo["GS-Tunisia"].cpu_utilized == 0.0
