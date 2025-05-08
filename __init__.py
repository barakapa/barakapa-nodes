from .custom_nodes.concatenate_string import ConcatenateStringNode
from .custom_nodes.count_tokens import CountTokensNode
from .custom_nodes.directory_image_counter import DirectoryImageCounterNode
from .custom_nodes.prompt_box import PromptBoxNode
from .custom_nodes.save_workflow import SaveWorkflowNode

# A dictionary that contains all nodes you want to export with their names.
# NOTE: Names should be globally unique.
NODE_CLASS_MAPPINGS: dict[str, type] = {
    'brkp_ConcatenateString': ConcatenateStringNode,
    'brkp_CountTokens': CountTokensNode,
    'brkp_DirectoryImageCounter': DirectoryImageCounterNode,
    'brkp_PromptBox': PromptBoxNode,
    'brkp_SaveWorkflow': SaveWorkflowNode,
}
 
# A dictionary that contains the friendly/humanly readable titles for the nodes.
NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {
    'brkp_ConcatenateString': 'Concatenate String (Custom)',
    'brkp_CountTokens': 'Prompt Tokens Counter (Custom)',
    'brkp_DirectoryImageCounter': 'Directory Image Counter (Custom)',
    'brkp_PromptBox': 'Prompt Box (Custom)',
    'brkp_SaveWorkflow': 'Save Workflow (Custom)',
}

# Ensure that custom JavaScript for nodes is loaded.
WEB_DIRECTORY = './js'

__all__: list[str] = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
