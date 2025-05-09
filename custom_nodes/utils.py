'''Helper classes, functions, and declarations for custom nodes.'''

from datetime import datetime
from json import dumps, loads
from math import isclose
from os import listdir, path
from re import Match, findall, finditer
from typing import Callable, Optional, TypeAlias, TypeVar

from nodes import NODE_DISPLAY_NAME_MAPPINGS
from typing_extensions import Self

# This value is used for comparing between two floating-point numbers.
FLOAT_COMPARISON_EPSILON: float = 1e-9

# String value to be shown in the UI for the boolean value True.
TRUE_VALUE: str = 'true'

# String value to be shown in the UI for the boolean value False.
FALSE_VALUE: str = 'false'

# A pair of separator symbols that reduce whitespaces in serialized JSON.
JSON_SEPARATORS: tuple[str, str] = (',', ':')

Json: TypeAlias = dict[str, 'Json'] | list['Json'] | str | int | float | bool
InputDict: TypeAlias = dict[str, dict[str, str | tuple[str | list[str], dict[str, str | int | bool | float]]]]

class JsonOpt:
    '''Represents an optional JSON object. Allows for .get method chaining.'''

    def __init__(self, json: Optional[Json] = None) -> None:
        self.json: Optional[Json] = json

    def get(self, key: str) -> Self:
        if isinstance(self.json, dict) and key in self.json:
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
        elif self.json:
            return str(self.json)
        else:
            return None

    def is_none(self) -> bool:
        return self.json is None

def find_node_id(node: JsonOpt) -> str:
    '''Attempts to retrieve a node's ID.'''
    node_id: Optional[str] = node.get('id').to_str()
    if not node_id:
        raise ValueError('ComfyUI node has missing ID!')
    return node_id

def find_node_display_name(node: JsonOpt) -> str:
    '''Attempts to retrieve a node's display name in the following order.
    1. Get node.title (custom display name added by user).
    2. Attempt to map node.type to the node's default display name.
    3. If no display name exists, return node.type (the internal node type name).
    '''
    title: Optional[str] = node.get('title').to_str()
    if title:
        return title

    node_type: Optional[str] = node.get('type').to_str()
    if not node_type:
        raise ValueError(f'ComfyUI node has missing type!')

    if node_type in NODE_DISPLAY_NAME_MAPPINGS:
        return NODE_DISPLAY_NAME_MAPPINGS[node_type]
    else:
        return node_type

def find_node_snr(node: JsonOpt) -> Optional[str]:
    '''Attempts to retrieve a node's custom search and replace value specified by the user.'''
    return node.get('properties').get('Node name for S&R').to_str()

T = TypeVar('T')
def map_unique_value_from_node(
    node: JsonOpt,
    retrieve_fn: Callable[[JsonOpt], Optional[T]],
    value_to_id_map: dict[T, str],
    duplicates_set: set[T],
    is_fail_on_missing: bool = True
) -> None:
    '''Attempts to retrieve a certain value of type T from a node using "retrieve_fn".
    If the value is None and "is_fail_on_missing" is set to True, raise an error.
    If the value is unique, store it as a key in "id_map" for the node's ID,
    otherwise, delete the value from "id_map" and store it in "duplicates_set".
    '''

    value: Optional[T] = retrieve_fn(node)
    if not value:
        if is_fail_on_missing:
            raise ValueError('Failed to retrieve unique value!')
        else:
            return

    node_id: str = find_node_id(node)
    if value not in value_to_id_map and value not in duplicates_set:
        value_to_id_map[value] = node_id
    elif value in value_to_id_map:
        # print(f'Unique Value Warning: Node #{value_to_id_map[value]} and '
        #       f'#{node_id} share the same retrieved value  "{value}"!')
        del value_to_id_map[value]
        duplicates_set.add(value)
    # else: # value in duplicates_set
    #     print(f'Warning: Node #{node_id} has duplicate retrieved value "{value}"!')

def search_and_replace(text: str, prompt: Optional[str | Json], extra_pnginfo: Optional[str | Json]) -> str:
    '''Replaces date and other S&R tags in a string with the correct values.'''

    if not text or not extra_pnginfo or not prompt:
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
    elif extra_pnginfo:
        extra_pnginfo_json = extra_pnginfo
    extra_pnginfo_jsonopt: JsonOpt = JsonOpt(extra_pnginfo_json)

    prompt_json: Optional[Json] = None
    if isinstance(prompt, str):
        prompt_json = loads(prompt)
    elif prompt:
        prompt_json = prompt
    prompt_jsonopt: JsonOpt = JsonOpt(prompt_json)

    nodes: list[JsonOpt] = extra_pnginfo_jsonopt.get('workflow').get('nodes').to_list()
    if not nodes:
        return text

    # Map of unique node display names to their IDs
    node_name_map: dict[str, str] = {}
    # Map of "Node name for S&R" values to their IDs
    node_snr_map: dict[str, str] = {}
    # Map of unique node types to their IDs
    node_type_map: dict[str, str] = {}

    # Set of duplicated display names
    node_name_duplicates: set[str] = set()
    # Set of duplicated S&R names
    node_snr_duplicates: set[str] = set()
    # Set of duplicated node types
    node_type_duplicates: set[str] = set()

    # Set of all unique node IDs
    node_ids: set[str] = set()

    for node in nodes:
        node_id: str = find_node_id(node)
        if node_id in node_ids:
            raise ValueError('Duplicate node IDs in ComfyUI workflow graph!')
        node_ids.add(node_id)

        map_unique_value_from_node(node, find_node_display_name, node_name_map, node_name_duplicates)
        map_unique_value_from_node(node, find_node_snr, node_snr_map, node_snr_duplicates, False)
        map_unique_value_from_node(node, lambda n: n.get('type').to_str(), node_type_map, node_type_duplicates)

    # Find all patterns in the text that need to be replaced
    patterns: list[str] = findall(r'%([^%]+)%', text)
    pattern: str
    for pattern in patterns:
        # Split the pattern to get the node key and widget name
        node_key: str
        widget_name: str
        node_key, widget_name = pattern.split('.')

        if node_key in node_snr_duplicates or node_key in node_name_duplicates or node_key in node_type_duplicates:
            raise ValueError(f'Ambiguous node key "{node_key}" for search and replace!')

        # Find the ID for a given node key
        node_id_str: str
        if node_key in node_ids:        # 1. Check if node_key is node's ID
            node_id_str = node_key
        elif node_key in node_snr_map:  # 2. Check if node_key is S&R value
            node_id_str = node_snr_map[node_key]
        elif node_key in node_name_map: # 3. Check if node_key is unique node display name
            node_id_str = node_name_map[node_key]
        elif node_key in node_type_map: # 4. Check if node_key is unique node type
            node_id_str = node_type_map[node_key]
        else:
            print(f'No node with ID, or unique name, or unique type "{node_key}" found.')
            continue

        # Find the value of the specified widget in prompt JSON
        node_from_id: JsonOpt = prompt_jsonopt.get(node_id_str)
        if node_from_id.is_none():
            raise ValueError(f'No node with ID {node_id_str} found in prompt!')

        widget_value: JsonOpt = node_from_id.get('inputs').get(widget_name)
        if widget_value.is_none():
            raise ValueError(f'No input with name {widget_name} found for node '
                             '"{node_key}" with ID #{node_id_str}!')

        # Finally, replace the pattern in the text
        widget_value_str: Optional[str] = widget_value.to_str()
        replace_value: str = ''
        if not widget_value_str:
            print(f'Warning: Search and replace value is falsy: "{str(widget_value.json)}"!')
        else:
            replace_value = widget_value_str
        text = text.replace(f'%{pattern}%', replace_value)

    return text

def find_files_with_ext_in_dir(dir_path: str, exts: set[str]) -> list[str]:
    '''Gelper function to get a list of all files with certain extensions within a given dir_path.'''
    try:
        dir_children: list[str] = listdir(dir_path)
    except FileNotFoundError:
        return []
    matched_files: list[str] = [d for d in dir_children if path.splitext(d)[1] in exts]
    return matched_files

def count_files_in_dir(dir_path: str, exts: set[str]) -> int:
    '''Helper function to count files with certain extensions within a given dir_path.'''
    matched_files: list[str] =  find_files_with_ext_in_dir(dir_path, exts)
    return len(matched_files)

def form_full_path(dir_path: str, file_name: str, file_ext: str) -> str:
    '''Helper function to create a full file path.'''
    file_name_with_ext: str = f'{file_name}{file_ext}'
    file_path: str = path.join(dir_path, file_name_with_ext)
    return file_path

def find_unused_file_name(dir_path: str, orig_file_name: str, file_ext: str) -> str:
    '''Helper function to find an unused file name in a given directory. Returns the full path ot the file.'''
    file_name: str = orig_file_name
    file_path: str = form_full_path(dir_path, file_name, file_ext)
    save_attempts: int = 0
    while path.exists(file_path):
        save_attempts += 1
        file_name = f'{orig_file_name}_{save_attempts}'
        file_path = form_full_path(dir_path, file_name, file_ext)
    return file_path

def normalize_float(x: float, epsilon: float = FLOAT_COMPARISON_EPSILON) -> float:
    '''Converts a float to a rounded value for comparison, based on an epsilon.'''
    precision: int
    for precision in range(16): # IEEE-754 has ~15-17 significant digits
        rounded: float = round(x, precision)
        if isclose(x, rounded, abs_tol=epsilon):
            return rounded
    return x

def canonicalize_json(obj: Json) -> Json:
    '''Converts a JSON object to a canonical form, taking into account nested objects and float comparison.'''
    if isinstance(obj, float):
        return normalize_float(obj)
    elif isinstance(obj, dict):
        # Sort keys and canonicalize values
        return dict(sorted((k, canonicalize_json(v)) for k, v in obj.items()))
    elif isinstance(obj, list):
        return [canonicalize_json(item) for item in obj]
    else:
        return obj
    
def stringify(obj: Json) -> str:
    '''Helper function to convert a JSON object into a compact string.'''
    return dumps(obj, separators=JSON_SEPARATORS)

def compare_json(obj1: Json, obj2: Json) -> int:
    '''Compares two JSON objects for equality. Returns 0 if both objects are equivalent.
    Otherwise, returns -1 if obj1 < obj2, or returns 1 if obj2 > obj1.
    '''
    obj1_str: str = stringify(obj1)
    obj2_str: str = stringify(obj2)
    return (obj1_str > obj2_str) - (obj1_str < obj2_str)

def parse_bool_str(string: str) -> bool:
    '''Parses a string used to represent a Boolean value, returning an actual Boolean.'''
    if string == TRUE_VALUE:
        return True
    elif string == FALSE_VALUE:
        return False
    else:
        raise ValueError(f'Unrecognized boolean string "{string}"!')
