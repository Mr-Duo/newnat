from copy import deepcopy
from newnat.data_models import FunctionInfo
from newnat.language_processors.PythonProcessor import PythonProcessor
from newnat.language_processors.GoProcessor import GoProcessor
from newnat.language_processors.JsProcessor import JsProcessor

LANG_TO_PROCESSOR = {
    "python": PythonProcessor,
    "go": GoProcessor,
    "javascript": JsProcessor,
}

# Map transform names to method names on the processor
TRANSFORM = {
    "block_swap": "block_swap",
    "insert_dead_code": "insert_dead_code",
    "var_renaming": "var_renaming",
    "operand_swap": "operand_swap",
    "for_while_swap": "for_while_swap"
}


def main(
    funcs: list[FunctionInfo],
    src: bytes,
    language: str,
    transform: str = "block_swap",
) -> tuple[bytes, str, bool]:
    if language not in LANG_TO_PROCESSOR:
        raise ValueError(f"Unsupported language: {language!r}")
    if transform not in TRANSFORM:
        raise ValueError(f"Unknown transform: {transform!r}")

    transformed_src = deepcopy(src)
    modified_code = ""
    success = False
    processor = LANG_TO_PROCESSOR[language]()
    transform_fn = getattr(processor, TRANSFORM[transform])

    for func in funcs:
        transformed_src, modified_code, _success = transform_fn(func, transformed_src)
        success = success or _success

    return transformed_src, modified_code, success