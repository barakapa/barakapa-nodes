from datetime import datetime
from json import loads
from os import listdir, path
from re import Match, findall, finditer
from typing import Optional, TypeAlias

from folder_paths import get_output_directory
from typing_extensions import Self

IMAGE_EXTS: set[str] = {
    '.png',
}

Json: TypeAlias = dict[str, 'Json'] | list['Json'] | str | int | float | bool
InputDict: TypeAlias = dict[str, dict[str, str | tuple[str, dict[str, str]]]]

class JsonOpt:
    def __init__(self, json: Optional[Json] = None):
        self.json: Optional[Json] = json
    
    def get(self, key: str) -> Self:
        if isinstance(self.json, dict):
            return self.__class__(self.json[key])
        else:
            return self.__class__()
    
    def to_list(self) -> list[Self]:
        if isinstance(self.json, dict):
            return [self.__class__(obj) for obj in self.json.keys()]
        elif isinstance(self.json, list):
            return [self.__class__(obj) for obj in self.json]
        else:
            return []
    
    def to_str(self) -> Optional[str]:
        if isinstance(self.json, str):
            return self.json
        elif isinstance(self.json, int):
            return str(self.json)
        else:
            return None
    
    def is_none(self) -> bool:
        return self.json is None

def search_and_replace(text: str, prompt: Optional[str], extra_pnginfo: Optional[str]) -> str:
    if extra_pnginfo is None or prompt is None:
        return text

    # if %date: in text, then replace with date
    if '%date:' in text:
        match: Match[str]
        for match in finditer(r'%date:(.*?)%', text):
            date_match: str = match.group(1)
            cursor: int = 0
            date_pattern: str = ''
            now: datetime = datetime.now()

            pattern_map: dict[str, str] = {
                'yyyy': now.strftime('%Y'),
                'yy': now.strftime('%y'),
                'MM': now.strftime('%m'),
                'M': now.strftime('%m').lstrip('0'),
                'dd': now.strftime('%d'),
                'd': now.strftime('%d').lstrip('0'),
                'hh': now.strftime('%H'),
                'h': now.strftime('%H').lstrip('0'),
                'mm': now.strftime('%M'),
                'm': now.strftime('%M').lstrip('0'),
                'ss': now.strftime('%S'),
                's': now.strftime('%S').lstrip('0')
            }

            sorted_keys: list[str] = sorted(pattern_map.keys(), key=len, reverse=True)

            while cursor < len(date_match):
                replaced: bool = False
                key: str
                for key in sorted_keys:
                    if date_match.startswith(key, cursor):
                        date_pattern += pattern_map[key]
                        cursor += len(key)
                        replaced = True
                        break
                if not replaced:
                    date_pattern += date_match[cursor]
                    cursor += 1

            text = text.replace('%date:' + match.group(1) + '%', date_pattern)

    # Parse JSON if they are strings
    extra_pnginfo_json: Optional[Json] = None
    if isinstance(extra_pnginfo, str):
        extra_pnginfo_json = loads(extra_pnginfo)
    extra_pnginfo_jsonopt: JsonOpt = JsonOpt(extra_pnginfo_json)

    prompt_json: Optional[Json] = None
    if isinstance(prompt, str):
        prompt_json = loads(prompt)
    prompt_jsonopt: JsonOpt = JsonOpt(prompt_json)

    nodes: list[JsonOpt] = extra_pnginfo_jsonopt.get('workflow').get('nodes').to_list()
    if not nodes:
        return text

    # Map from "Node name for S&R" to id in the workflow
    node_to_id_map: dict[str, str] = {}
    for node in nodes:
        node_name: Optional[str] = node.get('properties').get('Node name for S&R').to_str()
        node_id: Optional[str] = node.get('id').to_str()
        if node_name and node_id:
            node_to_id_map[node_name] = node_id
        else: 
            return text

    # Find all patterns in the text that need to be replaced
    patterns: list[str] = findall(r"%([^%]+)%", text)
    pattern: str
    for pattern in patterns:
        # Split the pattern to get the node name and widget name
        node_name_key: str
        widget_name: str
        node_name_key, widget_name = pattern.split('.')

        # Find the id for this node name
        node_id_str: str
        if node_name_key in node_to_id_map:
            node_id_str = node_to_id_map[node_name_key]
        else:
            print(f"No node with name {node_name_key} found.")
            # check if user entered id instead of node name
            if node_name_key in node_to_id_map.values():
                node_id_str = node_name_key
            else:
                continue

        # Find the value of the specified widget in prompt JSON
        prompt_node: JsonOpt = prompt_jsonopt.get(node_id_str)
        if prompt_node.is_none():
            print(f"No prompt data for node with id {node_id_str}.")
            continue

        widget_value: JsonOpt = prompt_node.get('inputs').get(widget_name)
        if widget_value.is_none():
            print(f"No widget with name {widget_name} found for node {node_name}.")
            continue

        # Replace the pattern in the text
        text = text.replace(f"%{pattern}%", str(widget_value))

    return text

class DirectoryImageCounterNode:
    def __init__(self):
        self.output_dir: str = get_output_directory()
    
    @classmethod
    def INPUT_TYPES(s) -> InputDict:
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
 
    #OUTPUT_NODE = False
 
    CATEGORY: str = 'custom/Directory Image Counter'
 
    def count_dir_images(
        self, directory_name: str, prompt: Optional[str] = None, extra_pnginfo: Optional[str] = None
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
 
# A dictionary that contains all nodes you want to export with their names.
# NOTE: Names should be globally unique.
NODE_CLASS_MAPPINGS: dict[str, type] = {
    'Directory Image Counter': DirectoryImageCounterNode
}
 
# A dictionary that contains the friendly/humanly readable titles for the nodes.
NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {
    'Directory Image Counter': 'Directory Image Counter (Custom)'
}
