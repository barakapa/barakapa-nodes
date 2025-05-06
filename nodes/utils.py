'''Helper classes, functions, and declarations for custom nodes.'''

from datetime import datetime
from json import dumps, loads
from math import isclose
from re import Match, findall, finditer
from typing import Optional, TypeAlias

from typing_extensions import Self

# This value is used for comparing between two floating-point numbers.
FLOAT_COMPARISON_EPSILON: float = 1e-9

Json: TypeAlias = dict[str, 'Json'] | list['Json'] | str | int | float | bool
InputDict: TypeAlias = dict[str, dict[str, str | tuple[str, dict[str, str]]]]

class JsonOpt:
    '''Represents an optional JSON object. Allows for .get method chaining.'''

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

def search_and_replace(text: str, prompt: Optional[str | Json], extra_pnginfo: Optional[str | Json]) -> str:
    '''Replaces date and other S&R tags in a string with the correct values.'''

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
    # Reduce whitespace in serialized JSON
    separator_symbols: tuple[str, str] = (',', ':')
    return dumps(obj, separators=separator_symbols)

def compare_json(obj1: Json, obj2: Json) -> int:
    '''Compares two JSON objects for equality. Returns 0 if both objects are equivalent.
    Otherwise, returns -1 if obj1 < obj2, or returns 1 if obj2 > obj1.
    '''
    obj1_str: str = stringify(obj1)
    obj2_str: str = stringify(obj2)
    return (obj1_str > obj2_str) - (obj1_str < obj2_str)
