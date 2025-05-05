from .nodes.count_tokens import CountTokensNode
from .nodes.directory_image_counter import DirectoryImageCounterNode

# A dictionary that contains all nodes you want to export with their names.
# NOTE: Names should be globally unique.
NODE_CLASS_MAPPINGS: dict[str, type] = {
    'brkp_CountTokens': CountTokensNode,
    'brkp_DirectoryImageCounter': DirectoryImageCounterNode,
}
 
# A dictionary that contains the friendly/humanly readable titles for the nodes.
NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {
    'brkp_CountTokens': 'Prompt Tokens Counter (Custom)',
    'brkp_DirectoryImageCounter': 'Directory Image Counter (Custom)',
}

__all__: list[str] = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
