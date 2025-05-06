from io import TextIOWrapper
from json import dump, load, loads
from os import listdir, path
from typing import Any, Optional

from folder_paths import get_output_directory

from .utils import FALSE_VALUE, TRUE_VALUE, InputDict, Json, parse_bool_str, search_and_replace
from .workflow import are_sorted_workflows_equal, sort_workflow

# The extension to use when saving a new workflow.
SAVE_EXT: str = '.json'

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

class SaveWorkflowNode:
    def __init__(self) -> None:
        self.output_dir: str = get_output_directory()

    @classmethod
    def INPUT_TYPES(cls) -> InputDict:
        return {
            'required': {
                'directory_name': ('STRING', {'default': ''}),
                'file_name': ('STRING', {'default': 'workflow'}),
                'is_appending_counter': ([TRUE_VALUE, FALSE_VALUE], {'default': TRUE_VALUE}),
            },
            'hidden': {
                'prompt': 'PROMPT',
                'extra_pnginfo': 'EXTRA_PNGINFO'
            },
        }

    RETURN_TYPES: tuple[str, ...] = ('INT', 'STRING')
    RETURN_NAMES: tuple[str, ...] = ('workflow_id', 'workflow_id_str')

    FUNCTION: str = 'save_workflow'
    OUTPUT_NODE: bool = True
    CATEGORY: str = 'custom/Save Workflow'

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
        file_name: str,
        is_appending_counter: str,
        prompt: Optional[str | Json] = None,
        extra_pnginfo: Optional[str | Json] = None
    ) -> dict[str, dict[str, Any] | tuple[int, str]]:
        '''Main method of SaveWorkflowNode.'''

        is_appending_counter_bool: bool = parse_bool_str(is_appending_counter)
        full_output_folder: str = self.output_dir
        if directory_name:
            dir_name: str = search_and_replace(directory_name, prompt, extra_pnginfo)
            full_output_folder = path.join(self.output_dir, dir_name)

        counter: int
        try:
            dir_children: list[str] = listdir(full_output_folder)
            existing_workflows: list[str] = [d for d in dir_children if path.splitext(d)[1] in WORKFLOW_EXTS]
            counter = len(existing_workflows)
        except FileNotFoundError:
            counter = 0

        ui_message: str = ''
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
                    full_file_path: str = path.join(full_output_folder, workflow_file_name)
                    workflow_file: TextIOWrapper
                    with open(full_file_path, 'r') as workflow_file:
                        workflow: Json = load(workflow_file)
                    if are_sorted_workflows_equal(current_workflow, workflow):
                        already_exists_msg: str = get_already_exists_msg(full_file_path)
                        return {'ui': {'text': already_exists_msg}, 'result': (counter, f'{counter:05d}')}

                # Current workflow is unique, we save it to disk
                new_workflow_file_name: str = ''
                if is_appending_counter_bool:
                    new_workflow_file_name = f'{file_name}{str(counter)}{SAVE_EXT}'
                else:
                    new_workflow_file_name = f'{file_name}{SAVE_EXT}'
                new_workflow_file_path: str = path.join(full_output_folder, new_workflow_file_name)
                new_workflow_file: TextIOWrapper
                with open(new_workflow_file_path, 'w') as new_workflow_file:
                    dump(current_workflow, new_workflow_file)
                counter += 1
                ui_message = get_file_saved_msg(new_workflow_file_path)

        return {'ui': {'text': ui_message}, 'result': (counter, f'{counter:05d}')}
