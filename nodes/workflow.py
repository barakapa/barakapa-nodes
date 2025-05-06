'''Helper functions related to ComfyUI workflows, also often called "prompts" in the code. Each workflow
is represented by a JSON-like object, produced from litegraph.js and imported into Python as a dict.
'''

from .utils import Json, canonicalize_json, compare_json, stringify

# Length of a list that represents a reference to another node in a node's inputs.
INPUT_REFERENCE_LENGTH: int = 2

# Key of a node that contains the dict of input parameters.
INPUTS_KEY: str = 'inputs'

# Keys of a node that should be stripped by strip_metadata().
METADATA_KEYS: set[str] = {
    '_meta',
    'is_changed',
}

def strip_metadata(workflow: dict[str, Json]) -> dict[str, Json]:
    '''Strips the metadata from a workflow, which consists of information that
    does not contribute functionally to the workflow's execution.
    '''
    new_workflow: dict[str, Json] = {}
    key: str
    value: Json
    for key, value in workflow.items():
        if isinstance(value, dict):
            new_workflow[key] = {k: v for k, v in value.items() if k not in METADATA_KEYS}
        else:
            new_workflow[key] = value
    return new_workflow

def remap_node_ids(workflow: dict[str, Json]) -> list[Json]:
    '''Given a sorted workflow, remap all the input references in the workflow to use the index
    of the node in the values list as node IDs instead. Returns the list of remapped nodes.
    '''
    # Generate ID mapping from original to sorted
    id_mapping: dict[str, int] = {k: index for index, k in enumerate(workflow.keys())}

    remapped_workflow: dict[int, Json] = {}
    node_id: str
    node: Json
    for node_id, node in workflow.items():
        new_id: int = id_mapping[node_id]
        if isinstance(node, dict):
            new_node: dict[str, Json] = node.copy()
            inputs: Json = node[INPUTS_KEY]
            if isinstance(inputs, dict):
                remapped_inputs: dict[str, Json] = {}
                for k, v in inputs.items():
                    # Check for node references in the inputs
                    if isinstance(v, list) and len(v) == INPUT_REFERENCE_LENGTH and isinstance(v[0], str):
                        node_ref_id: str = v[0]
                        new_node_ref: list[Json] = [id_mapping[node_ref_id], v[1]]
                        remapped_inputs[k] = new_node_ref
                    else:
                        remapped_inputs[k] = v
                new_node[INPUTS_KEY] = remapped_inputs
                remapped_workflow[new_id] = new_node
            else:
                raise ValueError('Workflow inputs should be a dict.')
        else:
            remapped_workflow[new_id] = node
    return list(remapped_workflow.values())

def sort_workflow(workflow: Json) -> Json:
    '''Given a workflow, sorts the nodes and fixes links to create an unique representation
    for variants of the same graph. Note that unique representations will only be produced
    if every node in the graph is different from each other. If there are two or more nodes
    that are equivalent, this method may produce two different sorted workflows that are
    valid for the same graph.
    '''
    if not isinstance(workflow, dict):
        return workflow

    # Strip metadata from workflow
    stripped_workflow: dict[str, Json] = strip_metadata(workflow)

    # Canonicalize nodes in workflow
    canonical_nodes: dict[str, Json] = {k: canonicalize_json(v) for k, v in stripped_workflow.items()}

    # Sort nodes, ignoring node ID and edges (sort dict by value)
    sorted_nodes: dict[str, Json] = dict(sorted(canonical_nodes.items(), key=lambda pair: stringify(pair[1])))
    return sorted_nodes

def are_sorted_workflows_equal(workflow1: Json, workflow2: Json) -> bool:
    '''Compares two sorted workflows, ignoring their node ID values.'''
    if not isinstance(workflow1, dict) or not isinstance(workflow2, dict):
        return workflow1 == workflow2
    remapped1: list[Json] = remap_node_ids(workflow1)
    remapped2: list[Json] = remap_node_ids(workflow2)
    return compare_json(remapped1, remapped2) == 0
