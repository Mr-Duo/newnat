from copy import deepcopy
from newnat.data_models import FunctionInfo
from newnat.language_processors.PythonProcessor import PythonProcessor
from newnat.language_processors.GoProcessor import GoProcessor
from newnat.language_processors.JsProcessor import JsProcessor

LANG_TO_PROCESSOR = {
    "python": PythonProcessor,
    "go": GoProcessor,
    "javascript": JsProcessor
}

def main(funcs: list[FunctionInfo], src: bytes, language: str) \
    -> tuple[bytes, str, bool]:
    transformed_src = deepcopy(src)
    success = False
    processor = LANG_TO_PROCESSOR[language]()
    
    for func in funcs:
        transformed_src, modified_code, _success = processor.block_swap(func, transformed_src)
        success = success or _success
    return transformed_src, modified_code, success