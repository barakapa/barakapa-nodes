from io import TextIOWrapper
from json import dump, load, loads
from os import makedirs, path
from typing import Any, Optional

from folder_paths import get_output_directory

from .utils import (FALSE_VALUE, JSON_SEPARATORS, TRUE_VALUE, InputDict, Json, find_files_with_ext_in_dir,
                    find_unused_file_name, parse_bool_str, search_and_replace)
from .workflow import are_sorted_workflows_equal, sort_workflow

# The extension to use when saving a new workflow.
SAVE_EXT: str = '.json'

# This key should match the value given in "js/saveWorkflow.js".
OUTPUT_TEXT_KEY: str = 'dispText'

# A string that represents any valid ComfyUI type.
ANY_TYPE: str = '*'

# Tooltip for the directory_name input parameter.
DIRECTORY_NAME_TOOLTIP: str = 'Sub-directory of the output directory to save workflows to.'

# Tooltip for the file_name_prefix input parameter.
PREFIX_TOOLTIP: str = 'Prefix to be added before the file name.'

# Tooltip for the is_counter_enabled input parameter.
COUNTER_TOOLTIP: str = ('If enabled, counts the number of images in the specified sub-directory and uses it in the '
                        'file name. Otherwise, the file name will just consist of the prefix and the suffix.')

# Tooltip for the file_name_suffix input parameter.
SUFFIX_TOOLTIP: str = 'Suffix to be added after the file name.'

# Tooltip for the ignored_inputs input parameter.
IGNORED_INPUTS_TOOLTIP: str = "Connect any workflow node here to ignore changes in that node's inputs."

# Files with these extensions will be checked for duplicate workflows.
WORKFLOW_EXTS: set[str] = {
    '.json',
}

def get_already_exists_msg(file_name: str) -> str:
    '''Formats a message to be displayed if an equivalent workflow already exists.'''
    return f'Workflow already exists at {file_name}.'

def get_file_saved_msg(file_name: str) -> str:
    '''Formats a message to be displayed if an equivalent workflow already exists.'''
    return f'Workflow exported to {file_name}!'

def validate_link(raw_link: list[str | int]) -> tuple[str, int]:
    '''Validates the type of a rawLink and returns it in the form of a tuple.'''
    length: int = len(raw_link)
    if length != 2:
        raise ValueError(f'raw_link has incorrect length {length}!')
    if not isinstance(raw_link[0], str) or not isinstance(raw_link[1], int):
        raise ValueError(f'raw_link {str(raw_link)} has incorrect type!')
    return (raw_link[0], raw_link[1])

class SaveWorkflowNode:
    def __init__(self) -> None:
        self.output_dir: str = get_output_directory()

    @classmethod
    def INPUT_TYPES(cls) -> InputDict:
        return {
            'required': {
                'directory_name': ('STRING', {
                    'default': '',
                    'tooltip': DIRECTORY_NAME_TOOLTIP
                }),
                'file_name_prefix': ('STRING', {
                    'default': 'workflow_',
                    'tooltip': PREFIX_TOOLTIP
                }),
                'is_counter_enabled': ([TRUE_VALUE, FALSE_VALUE], {
                    'default': TRUE_VALUE,
                    'tooltip': COUNTER_TOOLTIP
                }),
                'file_name_suffix': ('STRING', {
                    'default': '',
                    'tooltip': SUFFIX_TOOLTIP
                }),
            },
            'optional': {
                'ignored_inputs_0': (ANY_TYPE, {'rawLink': True, 'tooltip': IGNORED_INPUTS_TOOLTIP}),
                'ignored_inputs_1': (ANY_TYPE, {'rawLink': True, 'tooltip': IGNORED_INPUTS_TOOLTIP}),
                'ignored_inputs_2': (ANY_TYPE, {'rawLink': True, 'tooltip': IGNORED_INPUTS_TOOLTIP}),
            },
            'hidden': {
                'prompt': 'PROMPT',
                'extra_pnginfo': 'EXTRA_PNGINFO',
            },
        }

    RETURN_TYPES: tuple[str, ...] = ('INT', 'STRING')
    RETURN_NAMES: tuple[str, ...] = ('workflow_id', 'workflow_id_str')

    FUNCTION: str = 'save_workflow'
    OUTPUT_NODE: bool = True
    CATEGORY: str = 'custom/Save'

    @classmethod
    def IS_CHANGED(self, **_) -> float:
        '''The node will always be re-executed if any of the inputs change but
        this method can be used to force the node to execute again even when the inputs don't change.
        You can make this node return a number or a string. This value will be compared to the one
        returned the last time the node was executed, if it is different the node will be executed again.
        This method is used in the core repo for the LoadImage node where they return the image hash
        as a string, if the image hash changes between executions the LoadImage node is executed again.
        '''
        # NaN is never equal to any value
        return float('nan')

    def save_workflow(
        self,
        directory_name: str,
        file_name_prefix: str,
        is_counter_enabled: str,
        file_name_suffix: str,
        ignored_inputs_0: list[str | int] = [],
        ignored_inputs_1: list[str | int] = [],
        ignored_inputs_2: list[str | int] = [],
        prompt: Optional[str | Json] = None,
        extra_pnginfo: Optional[str | Json] = None
    ) -> dict[str, dict[str, list[Any]] | tuple[int, str]]:
        '''Main method of SaveWorkflowNode.'''

        is_counter_enabled_bool: bool = parse_bool_str(is_counter_enabled)
        prefix_snr: str = search_and_replace(file_name_prefix, prompt, extra_pnginfo)
        suffix_snr: str = search_and_replace(file_name_suffix, prompt, extra_pnginfo)

        ignored_nodes_lists: list[list[str | int]] = [ignored_inputs_0, ignored_inputs_1, ignored_inputs_2]
        # Discard output parameter indices of the rawLinks, we just want the node ID value
        ignored_nodes: list[str] = [validate_link(ls)[0] for ls in ignored_nodes_lists if ls]

        full_output_dir: str = self.output_dir
        if directory_name:
            dir_name: str = search_and_replace(directory_name, prompt, extra_pnginfo)
            full_output_dir = path.join(self.output_dir, dir_name)

        existing_workflows: list[str] = find_files_with_ext_in_dir(full_output_dir, WORKFLOW_EXTS)
        counter: int = len(existing_workflows)
        makedirs(full_output_dir, exist_ok=True)

        if prompt:
            current_workflow: Json
            if isinstance(prompt, str):
                current_workflow = sort_workflow(loads(prompt))
            else:
                current_workflow = sort_workflow(prompt)

            if isinstance(current_workflow, dict):
                # Compare current workflow with other workflows in directory
                # We assume the saved workflows are already sorted
                workflow_file_name: str
                for workflow_file_name in existing_workflows:
                    full_file_path: str = path.join(full_output_dir, workflow_file_name)

                    workflow_file: TextIOWrapper
                    with open(full_file_path, 'r') as workflow_file:
                        workflow: Json = load(workflow_file)

                    # Check if current workflow has been saved before
                    if are_sorted_workflows_equal(current_workflow, workflow, ignored_nodes):
                        workflow_id_str: str = ''
                        raw_name: str = path.splitext(workflow_file_name)[0]
                        if raw_name.startswith(prefix_snr) and raw_name.endswith(suffix_snr):
                            prefix_len: int = len(prefix_snr)
                            suffix_idx: int = len(raw_name) - len(suffix_snr)
                            workflow_id_str = raw_name[prefix_len : suffix_idx]

                        workflow_id: int = -1
                        try:
                            workflow_id = int(workflow_id_str)
                        except ValueError:
                            pass

                        already_exists_msg: str = get_already_exists_msg(full_file_path)
                        return {
                            'ui': {OUTPUT_TEXT_KEY: [already_exists_msg]},
                            'result': (workflow_id, str(workflow_id))
                        }

                # Current workflow is unique, we save it to disk
                counter_str: str = ''
                if is_counter_enabled_bool:
                    counter_str = str(counter)

                new_workflow_file_name: str = f'{prefix_snr}{counter_str}{suffix_snr}'
                file_path: str = find_unused_file_name(full_output_dir, new_workflow_file_name, SAVE_EXT)
                new_workflow_file: TextIOWrapper
                with open(file_path, 'w') as new_workflow_file:
                    dump(current_workflow, new_workflow_file, separators=JSON_SEPARATORS)

                saved_message: str = get_file_saved_msg(file_path)
                return {
                    'ui': {OUTPUT_TEXT_KEY: [saved_message]},
                    'result': (counter, str(counter))
                }

        return {
            'ui': {OUTPUT_TEXT_KEY: ['Failed to retrieve workflow!']},
            'result': (-1, str(-1))
        }
