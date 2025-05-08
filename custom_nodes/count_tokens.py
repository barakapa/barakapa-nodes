from abc import ABC, abstractmethod

from .utils import InputDict

# Stable Diffusion takes in tokens in chunks of 77.
# Hence the chunk size is 75 tokens, excluding the START and END token.
CHUNK_SIZE: int = 75

# Raw token ID values for special CLIP tokens.
CLIP_PADDING_TOKEN: int = 0
CLIP_START_TOKEN: int = 49406
CLIP_END_TOKEN: int = 49407

# Dictionary keys for CLIP_g and CLIP_l (used in SDXL workflow).
G_TOKENS_KEY: str = 'g'
L_TOKENS_KEY: str = 'l'

# These tokens will be ignored by the CountTokens node.
IGNORED_TOKEN_IDS_IN_COUNT: set[int] = {
    CLIP_PADDING_TOKEN,
    CLIP_START_TOKEN,
    CLIP_END_TOKEN,
}

# Abstract class for the "CLIP" type, to assist with type hints.
class CLIP(ABC):
    @abstractmethod
    def tokenize(cls, prompt: str) -> list[list[tuple[int, int]]] | dict[str, list[list[tuple[int, int]]]]:
        pass

class CountTokensNode:
    @classmethod
    def INPUT_TYPES(cls) -> InputDict:
        return {
            'required': {
                'clip': ('CLIP', {}),
                'text': ('STRING', {'default': ''}),
            }
        }

    RETURN_TYPES: tuple[str, ...] = ('INT', 'STRING')
    RETURN_NAMES: tuple[str, ...] = ('count', 'count_str')

    FUNCTION: str = 'count_tokens'

    # OUTPUT_NODE: bool = False

    CATEGORY: str = 'custom/Prompt Tokens Counter'

    def count_tokens(self, clip: CLIP, text: str) -> tuple[int, str]:
        raw_tokens: list[list[tuple[int, int]]] | dict[str, list[list[tuple[int, int]]]] = clip.tokenize(text)
        tokens_list: list[list[tuple[int, int]]] = []

        # If CLIP model is SDXL, use CLIP_g to count for simplicity
        # Both models give the same token length for the same text because they use the same vocabulary
        # Note that CLIP_g pads with 0s, while CLIP_l pads with the END token
        if isinstance(raw_tokens, dict) and G_TOKENS_KEY in raw_tokens and raw_tokens[G_TOKENS_KEY]:
            tokens_list = raw_tokens[G_TOKENS_KEY]
        elif isinstance(raw_tokens, dict):
            # For other SD models, we just take the first value in the dict to count
            _lang_model_key: str
            lang_model_tokens: list[list[tuple[int, int]]]
            _lang_model_key, lang_model_tokens = next((_key, val) for _key, val in raw_tokens.items() if val)
            # print(f'Using model with key "{_lang_model_key}" for CountTokensNode!')
            tokens_list = lang_model_tokens
        else:
            # If the tokenizer outputs a plain list, we just count that instead (SD1, SD1.5, etc.)
            tokens_list = raw_tokens

        if len(tokens_list) == 0:
            return 0, '0'

        # Retrieve the last chunk of tokens in the prompt
        last_chunk: list[tuple[int, int]] = tokens_list[-1]

        # Note that a token is a pair of (token_id, weight), we ignore weights for the count
        last_chunk_token_ids: list[int] = [token[0] for token in last_chunk]

        # Count the tokens, filtering out START, END, and padding
        last_chunk_token_count: int = sum(1 for id in last_chunk_token_ids if id not in IGNORED_TOKEN_IDS_IN_COUNT)

        # Assume every chunk is CHUNK_SIZE tokens, with the exception of the last
        token_count: int = (len(tokens_list) - 1) * CHUNK_SIZE + last_chunk_token_count
        return token_count, str(token_count)
