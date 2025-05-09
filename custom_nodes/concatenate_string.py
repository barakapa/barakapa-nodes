from .utils import InputDict


class ConcatenateStringNode:
    @classmethod
    def INPUT_TYPES(cls) -> InputDict:
        return {
            'required': {
                'str_1': ('STRING', {'default': ''}),
                'str_2': ('STRING', {'default': ''}),
                'str_3': ('STRING', {'default': ''}),
            },
        }

    RETURN_TYPES: tuple[str, ...] = ('STRING',)
    RETURN_NAMES: tuple[str, ...] = ('output_str',)
    FUNCTION: str = 'concatenate_string'
    CATEGORY: str = 'custom'

    def concatenate_string(self, str_1: str, str_2: str, str_3: str) -> tuple[str]:
        return (str_1 + str_2 + str_3,)
