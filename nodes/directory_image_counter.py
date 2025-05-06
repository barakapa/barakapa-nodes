from os import listdir, path
from typing import Optional

from folder_paths import get_output_directory

from .utils import InputDict, Json, search_and_replace

IMAGE_EXTS: set[str] = {
    '.png',
}

class DirectoryImageCounterNode:
    def __init__(self):
        self.output_dir: str = get_output_directory()
    
    @classmethod
    def INPUT_TYPES(cls) -> InputDict:
        return {
            'required': {
                'directory_name': ('STRING', {'default': ''}),
            },
            'hidden': {
                'prompt': 'PROMPT',
                'extra_pnginfo': 'EXTRA_PNGINFO'
            },
        }

    RETURN_TYPES: tuple[str, ...] = ('INT', 'STRING')
    RETURN_NAMES: tuple[str, ...] = ('int', 'string')

    FUNCTION: str = 'count_dir_images'

    # OUTPUT_NODE: bool = False

    CATEGORY: str = 'custom/Directory Image Counter'

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

    def count_dir_images(
        self, directory_name: str, prompt: Optional[str | Json] = None, extra_pnginfo: Optional[str | Json] = None
    ) -> tuple[int, str]:
        dir_name: str = search_and_replace(directory_name, prompt, extra_pnginfo)
        full_output_folder: str = path.join(self.output_dir, dir_name)

        counter: int
        try:
            dir_children: list[str] = listdir(full_output_folder)
            counter = len([d for d in dir_children if path.splitext(d)[1] in IMAGE_EXTS])
        except FileNotFoundError:
            counter = 0
        return counter, f'{counter:05d}'
 