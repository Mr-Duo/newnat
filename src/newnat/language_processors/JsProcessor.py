import numpy as np
from tree_sitter import Node

from newnat.data_models import FunctionInfo
from newnat.utils import *
from newnat.language_processors.BaseProcessor import BaseProcessor

class JsParterns:
    OPERAND_PAIRS = {
        "<" : ">", ">" : "<", "<=" : ">=", ">=" : "<=", "===": "===", "!==": "!==", "==" : "==", "!=" : "!=", "&&" : "&&", "||" : "||", "!" : "",
    }
    @classmethod
    def get_dead_for_loop(self, body: str, indent: str) -> bytes:
        control_variable = "_i_" + str(np.random.choice(list(range(10))))
        p = np.random.uniform(0, 1)
        if p < 0.5:
            loop = f'\nfor ( let {control_variable} = 0; {control_variable} > 0; {control_variable}++ ) {{\n\t{body}\n}}\n'
        else:
            loop = f"\nfor ( ; false ; ) {{\n\t{body}\n}}\n"
        loop = f"\n{indent}".join(loop.split("\n")).encode()
        return loop

    @classmethod
    def get_dead_while_loop(self, body: str, indent: str) -> bytes:
        p = np.random.uniform(0, 1)
        control_variable = "_i_" + str(np.random.choice(list(range(10))))
        if p < 0.33:
            return_str = f"\nwhile (false) {{\n\t{body}\n}}\n"
        elif p < 0.66:
            return_str = f"\nwhile ({control_variable} > {control_variable}) {{\n\t{body}\n}}\n"
        else:
            return_str = f"\nwhile ({control_variable} < {control_variable}) {{\n\t{body}\n}}\n"

        return_str = f"\n{indent}".join(return_str.split("\n")).encode()
        return return_str
        
    @classmethod
    def get_dead_if_condition(self, body: str, indent: str) -> bytes:
        p = np.random.uniform(0, 1)
        control_variable = "_i_" + str(np.random.choice(list(range(10))))
        if p < 0.33:
            return_str = f"\nif (false) {{\n\t{body}\n}}\n"
        elif p < 0.66:
            return_str = f"\nif ({control_variable} > {control_variable}) {{\n\t{body}\n}}\n"
        else:
            return_str = f"\nif ({control_variable} < {control_variable}) {{\n\t{body}\n}}\n"

        return_str = f"\n{indent}".join(return_str.split("\n")).encode()
        return return_str
    
    @classmethod
    def get_reversed_operand(self, condition: Node) -> bytes:
        left_oprd, operator, right_oprd = condition
        reverse_condition = " ".join([right_oprd, self.OPERAND_PAIRS[operator], left_oprd])
        return reverse_condition.encode()
        
    @classmethod
    def get_reversed_if_condition(self, condition: tuple[str, str, str], if_clause: str, else_clause: str, indent: str) -> bytes:
        left_oprd, operator, right_oprd = condition
        condition_clause = " ".join([left_oprd, operator, right_oprd])
        return_str = f"if !({condition_clause}) {else_clause} else {if_clause}"
        return_str = f"\n{indent}".join(return_str.split("\n")).encode()
        
        # print("="*20)
        # print(f"left: {left_oprd}")
        # print(f"oprs: {operator}")
        # print(f"righ: {right_oprd}")
        # print(f"condition: {condition_clause}")
        # print(f"return: {return_str}")
        # print("="*20)
        return return_str
        
class JsProcessor(BaseProcessor):
        
    def __init__(self):
        
        self.language = "javascript"
        self.parterns = JsParterns
        self.config = LANGUAGE_CONFIG[self.language]
        self.dead_code_functions = [
            self.parterns.get_dead_for_loop,
            self.parterns.get_dead_while_loop,
            self.parterns.get_dead_if_condition
        ]
        
    
    def insert_dead_code (self, fn: FunctionInfo, src: bytes) \
        ->  tuple[bytes, str, bool]:
            return super().insert_dead_code (fn, src)
            
    def var_renaming(self, fn: FunctionInfo, src: bytes) \
        ->  tuple[bytes, str, bool]:
            return super().var_renaming (fn, src)
            
    def operand_swap(self, fn: FunctionInfo, src: bytes) \
        ->  tuple[bytes, str, bool]:
            return super().operand_swap (fn, src)

    def block_swap(self, fn: FunctionInfo, src: bytes) \
        ->  tuple[bytes, str, bool]:
            return super().block_swap (fn, src)
            
    def for_while_swap(self, fn: FunctionInfo, src:bytes) \
        ->  tuple[bytes, str, bool]:
            return super().for_while_swap (fn, src)
 