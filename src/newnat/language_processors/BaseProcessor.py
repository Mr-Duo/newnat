import numpy as np
import random
from tree_sitter import Node, Parser
from copy import deepcopy
from collections import defaultdict

from newnat.data_models import FunctionInfo
from newnat.utils import *

class BaseProcessor:
    def __init__(self):
        pass
        
    def insert_dead_code (self, fn: FunctionInfo, src: bytes) \
        ->  tuple[bytes, str, bool]:
        root_node = fn.root_node
        original_src = deepcopy(src)
        original_code = deepcopy(fn.source)
        max_node_in_statement = int(count_children(root_node) / 4)
        statements = extract_statement_within_size(
            fn, 
            src,
            min_node=1,
            max_node=max_node_in_statement, 
            endswith=None
        )
        # print(len(statements))
        while len(statements) > 0:
            random_stmt, node_before = np.random.choice(statements, 2)
            statements.remove(random_stmt)
            dead_code_body = text_of(random_stmt, src)
            dead_code_function = np.random.choice(self.dead_code_functions)
            indent = last_line_indent(node_before, src)
            dead_code = dead_code_function(dead_code_body, indent)
            modified_src = insert_bytes(src, dead_code, node_before.end_byte)
            modified_start_byte = fn.start_byte
            modified_end_byte = fn.end_byte + len(dead_code)
            modified_code = modified_src[modified_start_byte: modified_end_byte].decode()
            
            if modified_code != original_code:
                return modified_src, modified_code, True
            
        return original_src, original_code, False
    

    def var_renaming(self, fn: FunctionInfo, src: bytes) \
        ->  tuple[bytes, str, bool]:
        
        def is_valid(node: Node, cfg: dict) -> True:
            parent = node.parent
            if parent is None:
                return False
            
            if parent.type in cfg["not_var_ptype"]:
                return False
            
            while parent is not None:
                if parent.type in cfg["imports"]:
                    return False
                parent = parent.parent

            return True
        
        root_node = fn.root_node
        original_src = deepcopy(src)
        original_code = deepcopy(fn.source)
        cfg = self.config
        
        sus_names = ["_"]
        var_map = defaultdict(list)

        for current_node in tree_walk(root_node):
            var_name = text_of(current_node, src)
            if (current_node.type in cfg["identifiers"] and var_name not in sus_names):
                if is_valid(current_node, cfg):
                    var_map[var_name].append(current_node)
                else:
                    sus_names.append(var_name)

        for sus_name in sus_names:
            if sus_name in var_map:
                del(var_map[sus_name])
                
                
        var_map = {f"VAR_{i}": v for i, v in enumerate(var_map.values())}
        items = [(sp.start_byte, sp.end_byte, key)
                    for key, lst in var_map.items() for sp in lst]
        items.sort(key=lambda t: t[0], reverse=True)
        
        modified_src = deepcopy(src)
        modified_start_byte = fn.start_byte
        modified_end_byte = fn.end_byte
        
        for start, end, key in items:
            modified_src = replace_bytes(modified_src, key.encode(), start, end)
            modified_end_byte = modified_end_byte + len(key) - (end - start)
            
        modified_code = modified_src[modified_start_byte: modified_end_byte].decode()

        if modified_code != original_code:
            return modified_src, modified_code, True
            
        return original_src, original_code, False
    
    def operand_swap(self, fn: FunctionInfo, src: bytes) \
        ->  tuple[bytes, str, bool]:
          
        original_src = deepcopy(src)  
        original_code = deepcopy(fn.source)
        expressions = []
        for current_node in tree_walk(fn.root_node):
            # print(current_node.type)
            if str(current_node.type) in self.config["comparisons"]:
                children_nodes = current_node.children
                counter = 0
                for w in children_nodes:
                    if str(w.type) in self.parterns.OPERAND_PAIRS or str(w.type) in self.parterns.LOGIC_PAIRS:
                        counter = counter + 1
                if counter == 1:
                    expressions.append(current_node)
        
        while len(expressions) > 0:
            selected_exp = np.random.choice(expressions)
            expressions.remove(selected_exp)
            bin_exp = selected_exp
            condition = text_of(bin_exp, original_src)
            node_condition = bin_exp.children
            if len(node_condition) != 3:
                continue
            
            left_oprd, operator, right_oprd = node_condition
            left_txt = text_of(left_oprd, src)
            opr_text = text_of(operator, src)
            right_text = text_of(right_oprd, src)
            
            if opr_text in self.parterns.OPERAND_PAIRS:
                pass
            else:
                found = None
                for key in self.parterns.OPERAND_PAIRS:
                    if key in opr_text:
                        found = key
                        break
                  
                if found:
                    l, r = opr_text.split(found)
                    left_txt += l
                    right_text += r
                    opr_text = found
                else:
                    # print(opr_text.split(found))
                    # print(f"{"="*10}\nleft: {left_txt}\nopr: {opr_text}\nright: {right_text}")
                    continue
            
            modified_bin_condition = self.parterns.get_reversed_operand((left_txt, opr_text, right_text))
            modified_src = replace_bytes(src, modified_bin_condition, bin_exp.start_byte, bin_exp.end_byte)
            
            modified_start_byte = bin_exp.start_byte
            modified_end_byte = bin_exp.start_byte + len(modified_bin_condition)
            modified_code = modified_src[modified_start_byte:modified_end_byte].decode()
            if modified_code != original_code:
                return modified_src, modified_code, True
        return original_src, original_code, False
    
    def block_swap(self, fn: FunctionInfo, src: bytes) \
        ->  tuple[bytes, str, bool]:
        original_src = deepcopy(src)  
        original_code = deepcopy(fn.source)
        
        expressions = []
        _if = self.config["if_conditions"]
        _else = self.config["else_conditions"]
        _alter = self.config["alternative_conditions"]
        for current_node in tree_walk(fn.root_node):
            
            if str(current_node.type) in _if and \
                current_node.parent.type not in _alter:
                
                des = current_node.children[1]
                leaves = [child for child in tree_walk(des) if len(child.children) == 0 ]

                opr_counter = 0

                for w in leaves:
                    if str(w.type) in self.parterns.OPERAND_PAIRS:
                        opr_counter = opr_counter + 1

                if not (opr_counter == 1):
                    continue
                
                children_types = [child.type for child in current_node.children]
                else_child = []
                for __else in _else:
                    for child in current_node.children:
                        if child == __else:
                            else_child.extend(__el.type for __el in child.children)
                                 
                # print(_alter)
                # print(children_types)
                if any(node_type in children_types for node_type in _else) and \
                    all(node_type not in children_types for node_type in _alter) and \
                    all(node_type not in else_child for node_type in _alter):
                        expressions.append([current_node, des]) 
        
        while len(expressions) > 0:
            selected = random.choice(expressions)
            expressions.remove(selected)
            clause, des = selected
                
            if len(des.children) != 3:
                continue
            
            left_oprd, operator, right_oprd = des.children
            left_txt = text_of(left_oprd, src)
            opr_text = text_of(operator, src)
            right_text = text_of(right_oprd, src)
            # print("="*20)
            # print(f"left: {left_txt}")
            # print(f"oprs: {opr_text}")
            # print(f"righ: {right_text}")
            # print("="*20)
            if opr_text in self.parterns.OPERAND_PAIRS:
                pass
            else:
                found = None
                for key in self.parterns.OPERAND_PAIRS:
                    if key in opr_text:
                        found = key
                        break
                  
                if found:
                    l, r = opr_text.split(found)
                    left_txt += l
                    right_text = r + right_text
                    opr_text = found
                else:
                    # print(opr_text.split(found))
                    # print(f"{"="*10}\nleft: {left_txt}\nopr: {opr_text}\nright: {right_text}")
                    continue
                
            
            _block = self.config["condition_blocks"]
            count = 0
            for node in tree_walk(clause):
                if node.type in _block:
                    if count == 0:
                        if_clause = node
                        count += 1
                    else:
                        else_clause = node
                        count += 1
                        break
            # print(f"{"=" * 20}\nif: {if_clause}\nelse:{else_clause}")
            if count != 2:
                continue
                
            indent = first_line_indent(clause, src)
            modified_if_clause = text_of(if_clause, src)
            modified_else_clause = text_of(else_clause, src)
            modified_code_src = self.parterns.get_reversed_if_condition(
                (left_txt, opr_text, right_text), modified_if_clause, modified_else_clause, indent
            )
            modified_src = replace_bytes(src, modified_code_src, clause.start_byte, clause.end_byte)
            modified_start_byte = clause.start_byte
            modified_end_byte = clause.end_byte - clause.start_byte + len(modified_code_src)
            modified_code = modified_src[modified_start_byte:modified_end_byte].decode()

            if modified_code != original_code:
                return modified_src, modified_code, True

        return original_src, original_code, False
    
    def for_while_swap(self, fn: FunctionInfo, src:bytes) \
        ->  tuple[bytes, str, bool]:
        original_src = deepcopy(src)  
        original_code = deepcopy(fn.source)
        
        return original_src, original_code, False
    

                    
