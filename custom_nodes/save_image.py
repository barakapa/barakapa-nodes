
from json import dumps
from os import makedirs, path
from typing import Any, Optional

from comfy.cli_args import args
from folder_paths import get_output_directory
from numpy import clip, ndarray, uint8
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from torch import Tensor

from .utils import FALSE_VALUE, TRUE_VALUE, InputDict, Json, count_files_in_dir, parse_bool_str, search_and_replace

# Key for an output image passed to the UI.
OUTPUT_IMAGE_KEY: str = 'images'

# Represents the PNG file format. Images will be saved with the following extension.
PNG_FILE_FORMAT: str = '.png'

# File extensions that represent a file to be picked up by the counter.
IMAGE_EXTS: set[str] = {
    PNG_FILE_FORMAT,
}

# Tooltip for the directory_name input parameter.
DIRECTORY_NAME_TOOLTIP: str = 'Sub-directory of the output directory to save images to.'

PREFIX_TOOLTIP: str = 'Prefix to be added before the file name.'

# Tooltip for the is_counter_enabled input parameter.
COUNTER_TOOLTIP: str = ('If enabled, counts the number of files in the specified sub-directory and uses it as the '
                        'file name. Otherwise, the file name will just consist of the prefix and the suffix.')

# Tooltip for the file_name_suffix input parameter.
SUFFIX_TOOLTIP: str = 'Suffix to be added after the file name.'

# Tooltip for the compress_level input parameter.
COMPRESS_LEVEL_TOOLTIP: str = 'Compression level to be used for saved images.'

# This tag is used to add the image batch number to the saved file name.
BATCH_NUM_TAG: str = '%batch_num%'

def form_full_path(dir: str, file_name: str, ext: str) -> str:
    '''Helper function to create the full image save path.'''
    file_name_with_ext: str = f'{file_name}{ext}'
    file_path: str = path.join(dir, file_name_with_ext)
    return file_path

class SaveImageNode:
    def __init__(self) -> None:
        self.output_dir: str = get_output_directory()
        self.type = 'output'

    @classmethod
    def INPUT_TYPES(cls) -> InputDict:
        return {
            'required': {
                'images': ('IMAGE', {}),
                'directory_name': ('STRING', {
                    'default': '',
                    'tooltip': DIRECTORY_NAME_TOOLTIP
                }),
                'file_name_prefix': ('STRING', {
                    'default': 'ComfyUI_',
                    'tooltip': PREFIX_TOOLTIP
                }),
                'is_counter_enabled': ([TRUE_VALUE, FALSE_VALUE], {
                    'default': TRUE_VALUE,
                    'tooltip': COUNTER_TOOLTIP
                }),
                'file_name_suffix': ('STRING', {
                    'default': '_',
                    'tooltip': SUFFIX_TOOLTIP
                }),
                'compress_level': ('INT', {
                    'default': 4,
                    'tooltip': COMPRESS_LEVEL_TOOLTIP
                }),
            },
            'hidden': {
                'prompt': 'PROMPT',
                'extra_pnginfo': 'EXTRA_PNGINFO',
            },
        }

    RETURN_TYPES: tuple[str, ...] = ()
    FUNCTION: str = 'save_image'
    OUTPUT_NODE: bool = True
    CATEGORY: str = 'custom/Save'

    def save_image(
        self,
        images: Tensor,
        directory_name: str,
        file_name_prefix: str,
        is_counter_enabled: str,
        file_name_suffix: str,
        compress_level: int,
        prompt: Optional[str | Json] = None,
        extra_pnginfo: Optional[str | Json] = None
    ) -> dict[str, dict[str, list[Any]]]:
        '''Main method of SaveImageNode.'''

        is_counter_enabled_bool: bool = parse_bool_str(is_counter_enabled)
        prefix_snr: str = search_and_replace(file_name_prefix, prompt, extra_pnginfo)
        suffix_snr: str = search_and_replace(file_name_suffix, prompt, extra_pnginfo)

        full_output_dir: str = self.output_dir
        if directory_name:
            dir_name: str = search_and_replace(directory_name, prompt, extra_pnginfo)
            full_output_dir = path.join(self.output_dir, dir_name)

        counter: int = 0
        if is_counter_enabled_bool:
            counter = count_files_in_dir(full_output_dir, IMAGE_EXTS)
        makedirs(full_output_dir, exist_ok=True)

        img_results: list[dict[str, str]] = list()
        batch_number: int
        tensor: Tensor
        for (batch_number, tensor) in enumerate(images):
            i: ndarray = 255.0 * tensor.cpu().numpy()
            clipped: ndarray = clip(i, 0, 255).astype(uint8)
            img: Image = Image.fromarray(clipped)
            metadata: Optional[PngInfo] = None
            if not args.disable_metadata:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text('prompt', dumps(prompt))
                if isinstance(extra_pnginfo, dict):
                    key: str
                    val: Json
                    for key, val in extra_pnginfo.items():
                        metadata.add_text(key, dumps(val))

            batch_num_str: str = str(batch_number)
            prefix_batch_num: str = prefix_snr.replace(BATCH_NUM_TAG, batch_num_str)
            suffix_batch_num: str = suffix_snr.replace(BATCH_NUM_TAG, batch_num_str)

            counter_str: str = ''
            if is_counter_enabled_bool:
                counter_str = f'{counter:05d}'

            orig_file_name: str = f'{prefix_batch_num}{counter_str}{suffix_batch_num}'
            file_name: str = orig_file_name
            file_path: str = form_full_path(full_output_dir, file_name, PNG_FILE_FORMAT)

            save_attempts: int = 0
            while path.exists(file_path):
                save_attempts += 1
                file_name = f'{orig_file_name}_{save_attempts}'
                file_path = form_full_path(full_output_dir, file_name, PNG_FILE_FORMAT)
            img.save(file_path, pnginfo=metadata, compress_level=compress_level)
            img_results.append({'filename': file_path, 'subfolder': full_output_dir, 'type': self.type})

            counter += 1

        return {'ui': {OUTPUT_IMAGE_KEY: img_results}}
