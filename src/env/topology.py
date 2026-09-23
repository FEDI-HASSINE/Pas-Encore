from __future__ import annotations

from typing import Any, Iterator
from src.env.node import Node
from src.env.link import Link


def build_nodes() -> dict[str, Node]:
    """Instantiate the 4 standard nodes as specified in Table 1 of 02_EXPERIMENTAL_DESIGN.

    Table 1 – Fixed Node Configuration with Realistic Parameters:
        - LEO-1:       Orbital Satellite | CPU: 10  | RAM: 32  | Energy: 2.0 | Startup: 5.0 | Noise: ±5%
        - LEO-2:       Orbital Satellite | CPU: 10  | RAM: 32  | Energy: 2.0 | Startup: 5.0 | Noise: ±5%
        - GS-Tunisia:  Ground Station    | CPU: 20  | RAM: 64  | Energy: 0.5 | Startup: 1.0 | Noise: ±1%
        - Cloud-AWS:   Terrestrial Cloud | CPU: 100 | RAM: 256 | Energy: 0.1 | Startup: 0.0 | Noise: ±0%

    Returns:
        Dictionary mapping node IDs to initialized Node instances.
    """
    return {
        "LEO-1": Node(
            id="LEO-1",
            cpu_capacity=10.0,
            ram_capacity=32.0,
            energy_cost=2.0,
            startup_penalty=5.0,
            sensor_noise=0.05,
            node_type="Orbital Satellite",
        ),
        "LEO-2": Node(
            id="LEO-2",
            cpu_capacity=10.0,
            ram_capacity=32.0,
            energy_cost=2.0,
            startup_penalty=5.0,
            sensor_noise=0.05,
            node_type="Orbital Satellite",
        ),
        "GS-Tunisia": Node(
            id="GS-Tunisia",
            cpu_capacity=20.0,
            ram_capacity=64.0,
            energy_cost=0.5,
            startup_penalty=1.0,
            sensor_noise=0.01,
            node_type="Ground Station",
        ),
        "Cloud-AWS": Node(
            id="Cloud-AWS",
            cpu_capacity=100.0,
            ram_capacity=256.0,
            energy_cost=0.1,
            startup_penalty=0.0,
            sensor_noise=0.0,
            node_type="Terrestrial Cloud",
        ),
    }


def build_links() -> list[Link]:
    """Instantiate the 4 standard links as specified in Table 2 of 02_EXPERIMENTAL_DESIGN.

    Table 2 – Fixed Link Dynamics:
        - LEO-1 ↔ GS-Tunisia:     10 Mbps  | Active for 600s every 5400s (offset 0s, pass at t=0)
        - LEO-2 ↔ GS-Tunisia:     10 Mbps  | Active for 600s every 5400s (offset by 2700s)
        - GS-Tunisia ↔ Cloud-AWS: 100 Mbps | Always Active
        - LEO-1 ↔ LEO-2 (ISL):    50 Mbps  | Always Active

    Returns:
        List of initialized Link instances.
    """
    return [
        Link(
            node1="LEO-1",
            node2="GS-Tunisia",
            bandwidth=10.0,
            visibility_window=(600.0, 5400.0, 0.0),
        ),
        Link(
            node1="LEO-2",
            node2="GS-Tunisia",
            bandwidth=10.0,
            visibility_window=(600.0, 5400.0, 2700.0),
        ),
        Link(
            node1="GS-Tunisia",
            node2="Cloud-AWS",
            bandwidth=100.0,
            always_active=True,
        ),
        Link(
            node1="LEO-1",
            node2="LEO-2",
            bandwidth=50.0,
            always_active=True,
        ),
    ]


class Topology:
    """Fixed heterogeneous space-ground computing environment topology.

    Provides convenient access to nodes and links, supports dictionary-like
    node access (e.g. `topology['LEO-1']`), and unpacks cleanly into `(nodes, links)`.

    Attributes:
        nodes: Dictionary of node IDs to Node objects.
        links: List of Link objects connecting the nodes.
    """

    def __init__(self, nodes: dict[str, Node], links: list[Link]) -> None:
        self.nodes = nodes
        self.links = links

    def get_node(self, node_id: str) -> Node | None:
        """Retrieve a node by its ID."""
        return self.nodes.get(node_id)

    def get_link(self, node1: str, node2: str) -> Link | None:
        """Find the communication link between two nodes (bidirectional)."""
        n1 = getattr(node1, "id", str(node1))
        n2 = getattr(node2, "id", str(node2))
        for link in self.links:
            if (link.node1 == n1 and link.node2 == n2) or (link.node1 == n2 and link.node2 == n1):
                return link
        return None

    def is_connected(self, node1: str, node2: str, current_time: float = 0.0) -> bool:
        """Check if an active communication link exists between two nodes at current_time."""
        link = self.get_link(node1, node2)
        if link is None:
            return False
        return link.is_active(current_time)

    def reset(self) -> None:
        """Reset all nodes in the topology."""
        for node in self.nodes.values():
            node.reset()

    def __iter__(self) -> Iterator[Any]:
        """Support unpacking: `nodes, links = build_topology()`."""
        return iter((self.nodes, self.links))

    def __getitem__(self, node_id: str) -> Node:
        """Access a node as a mapping: `topology['LEO-1']`."""
        return self.nodes[node_id]

    def __contains__(self, node_id: str) -> bool:
        """Check if node ID exists in topology: `'LEO-1' in topology`."""
        return node_id in self.nodes

    def get(self, node_id: str, default: Any = None) -> Any:
        """Mapping get method: `topology.get('LEO-1')`."""
        return self.nodes.get(node_id, default)

    def keys(self):
        return self.nodes.keys()

    def values(self):
        return self.nodes.values()

    def items(self):
        return self.nodes.items()

    def __len__(self) -> int:
        return len(self.nodes)


def build_topology() -> Topology:
    """Build and return the fixed simulation topology (4 Nodes and 4 Links).

    Returns:
        Topology instance containing the 4 Nodes and 4 Links.
        Can be used directly as an object, indexed like a dictionary (`topology['LEO-1']`),
        or unpacked: `nodes, links = build_topology()`.
    """
    nodes = build_nodes()
    links = build_links()
    return Topology(nodes=nodes, links=links)
