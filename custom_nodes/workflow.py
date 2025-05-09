'''Helper functions related to ComfyUI workflows, also often called "prompts" in the code. Each workflow
is represented by a JSON-like object, produced from litegraph.js and imported into Python as a dict.
'''

from .utils import Json, canonicalize_json, compare_json, stringify

# Length of a list that represents a reference to another node in a node's inputs.
REFERENCE_LENGTH: int = 2

# Key of a node that contains the dict of input parameters.
INPUTS_KEY: str = 'inputs'

# Keys of a node that should be stripped by strip_metadata().
METADATA_KEYS: set[str] = {
    '_meta',
    'is_changed',
}

# Input parameters of a node that should be stripped by strip_metadata().
IGNORED_INPUTS_KEYS: set[str] = {
    '_displayed_text',  # Used by SaveWorkflowNode to output information to the UI.
}

def strip_metadata(workflow: dict[str, Json]) -> dict[str, Json]:
    '''Strips the metadata from a workflow, which consists of information that
    does not contribute functionally to the workflow's execution.
    '''
    new_workflow: dict[str, Json] = {}
    node_id: str
    node_obj: Json

    for node_id, node_obj in workflow.items():
        if not isinstance(node_obj, dict):
            new_workflow[node_id] = node_obj
            continue

        new_node: dict[str, Json] = {k: v for k, v in node_obj.items() if k not in METADATA_KEYS and k != INPUTS_KEY}
        inputs: Json = node_obj[INPUTS_KEY]

        if not isinstance(inputs, dict):
            raise ValueError('Workflow inputs should be a dict.')

        new_node[INPUTS_KEY] = {k: v for k, v in inputs.items() if k not in IGNORED_INPUTS_KEYS}
        new_workflow[node_id] = new_node

    return new_workflow

def remap_node_ids(workflow: dict[str, Json]) -> tuple[list[Json], dict[str, int]]:
    '''Given a sorted workflow, remap all the input references in the workflow to use the index
    of the node in the values list as node IDs instead. Returns the list of remapped nodes and a
    dict representing the mapping from original node IDs to the new index of the node in the list.
    '''
    # Generate ID mapping from original to sorted
    id_mapping: dict[str, int] = {k: index for index, k in enumerate(workflow.keys())}

    remapped_workflow: dict[int, Json] = {}
    node_id: str
    node_obj: Json

    for node_id, node_obj in workflow.items():
        new_id: int = id_mapping[node_id]
        if not isinstance(node_obj, dict):
            remapped_workflow[new_id] = node_obj
            continue

        new_node: dict[str, Json] = node_obj.copy()
        inputs: Json = node_obj[INPUTS_KEY]

        if not isinstance(inputs, dict):
            raise ValueError('Workflow inputs should be a dict.')

        remapped_inputs: dict[str, Json] = {}
        for k, v in inputs.items():
            # Check for references to other nodes in the inputs and remap them
            if isinstance(v, list) and len(v) == REFERENCE_LENGTH and isinstance(v[0], str):
                node_ref_id: str = v[0]
                new_node_ref: list[Json] = [id_mapping[node_ref_id], v[1]]
                remapped_inputs[k] = new_node_ref
            else:
                remapped_inputs[k] = v
        new_node[INPUTS_KEY] = remapped_inputs
        remapped_workflow[new_id] = new_node

    return list(remapped_workflow.values()), id_mapping

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

def are_sorted_workflows_equal(workflow: Json, other_workflow: Json, ignored_nodes: list[str]) -> bool:
    '''Compares two sorted workflows, ignoring their node ID values.
    If "ignored_nodes" is given, which is a list of node IDs of "workflow",
    comparison will ignore all input parameters of these specified nodes.
    '''
    if not isinstance(workflow, dict) or not isinstance(other_workflow, dict):
        raise ValueError('Incorrect JSON objects passed to are_sorted_workflows_equal()!')

    # Remap main workflow
    remapped: list[Json]
    node_id_mappings: dict[str, int]
    remapped, node_id_mappings = remap_node_ids(workflow)

    # Remap ignored_inputs as well
    remapped_ignored: list[int] = [node_id_mappings[node_id] for node_id in ignored_nodes]

    # Remap the other workflow
    remapped_other: list[Json]
    remapped_other, _ = remap_node_ids(other_workflow)

    # Remove input values of remapped_ignored nodes from both workflows
    def clear_inputs(node: Json) -> None:
        if isinstance(node, dict):
            node[INPUTS_KEY] = {}
    for node_idx in remapped_ignored:
        clear_inputs(remapped[node_idx])
        if node_idx < len(remapped_other):
            clear_inputs(remapped_other[node_idx])

    # Compare the two remapped workflows
    return compare_json(remapped, remapped_other) == 0
