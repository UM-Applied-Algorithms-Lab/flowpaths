from collections import defaultdict
import networkx as nx
from typing import List, Tuple, Dict, Set, Optional


class MultiGraphDecomposer:
    """
    A class to handle decomposition problems on MultiDiGraphs by splitting parallel edges,
    then converting back to the original multigraph representation for solutions.
    """
    
    def __init__(self, G: nx.MultiDiGraph, additional_starts: List = [], additional_ends: List = []):
        """
        Initialize with a MultiDiGraph and optional additional start/end nodes.
        
        Parameters:
        - G: The input MultiDiGraph
        - additional_starts: List of additional start nodes
        - additional_ends: List of additional end nodes
        """

        self.original_graph = G
        self.additional_starts = additional_starts
        self.additional_ends = additional_ends
        
        # Create the split graph representation
        self._create_split_graph()

        
    def _create_split_graph(self) -> None:
        """Create a DiGraph representation by splitting parallel edges."""
        self.split_graph = nx.DiGraph()
        self.edge_mapping = {}  # Maps split edges to original multiedge keys
        self.reverse_edge_mapping = defaultdict(dict)  # Maps original edges to split edges
        
        # Add all nodes from original graph
        self.split_graph.add_nodes_from(self.original_graph.nodes(data=True))
        
        # Process each edge in the multigraph
        for u, v, key, data in self.original_graph.edges(keys=True, data=True):
            # Create unique target node for parallel edges
            if self.split_graph.has_edge(u, v):
                # This is a parallel edge - need to split
                new_node = f"{u}_{v}_split_{len(self.reverse_edge_mapping[(u, v)])}"
                self.split_graph.add_node(new_node)
                
                # Add edge from u to new node
                self.split_graph.add_edge(u, new_node, **data)
                self.edge_mapping[(u, new_node)] = (u, v, key)
                self.reverse_edge_mapping[(u, v)][key] = (u, new_node)

                
                # Add edge from new node to v
                # make the flow value be 0 for the new edge
                zero_flow_data = data.copy()
                zero_flow_data['flow'] = 0
                self.split_graph.add_edge(new_node, v, **zero_flow_data)
                self.edge_mapping[(new_node, v)] = (u, v, key)

            else:
                # First edge between u and v - add directly
                self.split_graph.add_edge(u, v, **data)
                self.edge_mapping[(u, v)] = (u, v, key)
                self.reverse_edge_mapping[(u, v)][key] = (u, v)
    
    def get_digraph(self) -> nx.DiGraph:
        """Get the split DiGraph representation."""
        return self.split_graph
    
    def convert_path_to_original(self, path: List) -> List[Tuple]:
        """
        Convert a path in the split graph back to the original multigraph representation.
        
        Parameters:
        - path: List of nodes in the split graph
        
        Returns:
        - List of edges (u, v, key) in the original multigraph
        """
        original_path = []
        
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i+1]
            
            # Get the original edge this split edge corresponds to
            original_edge = self.edge_mapping.get((u, v), None)

            if original_edge is None:
                raise ValueError(f"Edge {u}->{v} not found in edge mapping")
            
            if not "_split_" in u:
                original_path.append(original_edge)
        
        # handle consecutive edges that were split
        # (u -> new_node -> v) represented as just (u, v, key)
        simplified_path = []
        i = 0
        while i < len(original_path):
            if i + 1 < len(original_path):
                u1, v1, k1 = original_path[i]
                u2, v2, k2 = original_path[i+1]
                
                if k1 == k2 and "_split_" in v1 and u2 == v1:
                    # This is a split edge pair - combine them
                    simplified_path.append((u1, v2, k1))
                    i += 2
                    continue
            
            simplified_path.append(original_path[i])
            i += 1

        return simplified_path
    
    def convert_edge_to_original(self, edge: Tuple) -> Tuple:
        """
        Convert a single edge in the split graph back to original multigraph representation.
        
        Parameters:
        - edge: Tuple (u, v) representing edge in split graph
        
        Returns:
        - Tuple (u, v, key) representing edge in original multigraph
        """
        return self.edge_mapping.get(edge, None)
    
    def convert_original_to_split(self, edge: Tuple) -> List[Tuple]:
        """
        Convert an original multigraph edge to its split graph representation.
        
        Parameters:
        - edge: Tuple (u, v, key) representing edge in original multigraph
        
        Returns:
        - List of edges in split graph (may be 1 or 2 edges depending on splitting)
        """
        u, v, key = edge
        split_edges = []
        
        if (u, v) in self.reverse_edge_mapping:
            if key in self.reverse_edge_mapping[(u, v)]:
                split_edge = self.reverse_edge_mapping[(u, v)][key]
                if isinstance(split_edge[1], str) and "_split_" in split_edge[1]:
                    # This was split into two edges
                    split_node = split_edge[1]
                    split_edges.append((u, split_node))
                    split_edges.append((split_node, v))
                else:
                    split_edges.append(split_edge)
        
        return split_edges
    

    def get_ignore_split_edges(self, edges_to_ignore: Set[Tuple]) -> Set[Tuple]:
        """
        Get a set of edges that should be igored when finding kleasterrors..
        """
        
        ignore_set = set(edges_to_ignore)  # Start with original edges

        
        # Add edges connected to split nodes
        for edge in self.split_graph.edges(data=True):
           
            u = edge[0]
            
            # Check if either node is a split node
            if  "_split_" in u:
                ignore_set.add(edge[:2])  # Add as (u, v) tuple
        
        return ignore_set
            
        
    
