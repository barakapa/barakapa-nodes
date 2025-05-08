from .utils import InputDict


class PromptBoxNode:
    @classmethod
    def INPUT_TYPES(cls) -> InputDict:
        return {
            'required': {
                'prompt': ('STRING', {
                    'default': '',
                    'multiline': True, 
                }),
            },
        }

    RETURN_TYPES: tuple[str, ...] = ('STRING',)
    RETURN_NAMES: tuple[str, ...] = ('prompt',)
    FUNCTION: str = 'get_prompt'
    CATEGORY: str = 'custom/Prompt Box'
    
    def get_prompt(self, prompt: str) -> tuple[str]:
        return (prompt,)
