from json import dumps
from typing import Any
from .utils import InputDict


class ConvertToStringNode:
    @classmethod
    def INPUT_TYPES(cls) -> InputDict:
        return {
            'required': {'input': ('*', {})},
        }

    RETURN_TYPES: tuple[str, ...] = ('STRING',)
    RETURN_NAMES: tuple[str, ...] = ('output_str',)
    FUNCTION: str = 'to_string'
    CATEGORY: str = 'custom'

    def to_string(self, input: Any) -> tuple[str]:
        output_str: str  = ''
        if isinstance(input, str):
            output_str = input
        elif isinstance(input, (int, float, bool)):
            output_str = str(input)
        elif input:
            try:
                output_str = dumps(input)
            except Exception:
                output_str = str(input)
        return (output_str,)
