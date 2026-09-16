"""Test Semantic Purification —— DebugRepair 论文 Algorithm 1 的实现。

论文: DebugRepair: Enhancing LLM-Based Automated Program Repair via
      Self-Directed Debugging (arXiv:2604.19305), 见 3.2 节与 Algorithm 1。

输入失败测试方法 T、失败触发语句 s_fail 以及测试类 C 的 AST，输出:
  * T_min: 仅保留与 s_fail 相关语句的最小测试方法 (Algorithm 1, L1-L24);
  * D:     T_min 及其依赖方法所需的、声明在 C 内的成员方法与字段 (L25-L34)。

与论文的对应关系逐条标注在各函数的注释中。两处在论文之外补充的工程约定
(均是论文未定义的边界情形, 不改变算法语义) 已在 NOTE 中说明。
"""

import os
import tempfile
from collections.abc import Callable

from tree_sitter import Language, Parser
import tree_sitter_java

# --- Tree-sitter 环境设置 ---
# 延迟初始化: 作为库被导入时不应在 import 期退出进程。
_PARSER = None


def _get_parser() -> Parser:
    global _PARSER
    if _PARSER is not None:
        return _PARSER
    try:
        language = Language(tree_sitter_java.language())
    except TypeError:  # tree_sitter 0.21 及更早版本需要显式语言名
        language = Language(tree_sitter_java.language(), "java")
    try:
        _PARSER = Parser(language)  # tree_sitter >= 0.23
    except TypeError:
        _PARSER = Parser()
        if hasattr(_PARSER, "set_language"):
            _PARSER.set_language(language)  # tree_sitter <= 0.21
        else:
            _PARSER.language = language  # tree_sitter 0.22
    return _PARSER


# --- 节点类型常量 ---
# 基本类型 -> 非对象; 其余类型节点 (类名/泛型/数组/限定名) -> 对象。
_PRIMITIVE_TYPE_NODES = frozenset({
    "integral_type", "floating_point_type", "boolean_type", "void_type",
})
_OBJECT_TYPE_NODES = frozenset({
    "type_identifier", "generic_type", "array_type", "scoped_type_identifier",
    "annotated_type",
})
_TYPE_DECL_NODES = frozenset({
    "class_declaration", "interface_declaration", "enum_declaration",
    "record_declaration", "annotation_type_declaration",
})
_COMMENT_NODES = frozenset({"line_comment", "block_comment"})
# IsAssert: 前缀 assert 的调用 (assertEquals/Assert.assertThat/...) 与 JUnit fail
_ASSERT_EXTRA_NAMES = frozenset({"fail"})


# --- 辅助函数 ---
def get_node_text(node, code_bytes) -> str:
    if node is None:
        return ""
    return code_bytes[node.start_byte:node.end_byte].decode("utf8", "replace")


def _named_children(node) -> list:
    """跳过标点与注释后的命名子节点。"""
    return [c for c in node.children if c.is_named and c.type not in _COMMENT_NODES]


def _iter_nodes(node):
    """前序遍历整棵子树。"""
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _enclosing_type_decl(node):
    """向上找到最近的类型声明, 即 Algorithm 1 中的测试类 C。"""
    current = node.parent
    while current is not None:
        if current.type in _TYPE_DECL_NODES:
            return current
        current = current.parent
    return None


def _type_members(class_node) -> list:
    """C 直接声明的成员 (不含嵌套类型的成员)。"""
    if class_node is None:
        return []
    body = class_node.child_by_field_name("body")
    return list(body.children) if body else []


def _root_identifier(node, code_bytes):
    """取访问链最左端的名字, 如 this.a.b -> this, System.out -> System。"""
    current = node
    while current is not None:
        if current.type in ("identifier", "this"):
            return get_node_text(current, code_bytes)
        following = (current.child_by_field_name("object")
                     or current.child_by_field_name("array"))
        if following is None:
            named = _named_children(current)
            following = named[0] if named else None
        if following is None or following is current:
            return None
        current = following
    return None


class _SymbolTable:
    """记录方法内可见名字是对象还是基本类型, 用于 IsObject 与 FetchUsedObj。

    NOTE: tree-sitter 只做语法分析, 无法解析出跨文件的真实类型。因此对无法
    判定的名字 (如 var 声明、外部继承字段) 统一按对象处理 —— 论文中对象参与
    的两条规则都是为了不漏掉隐式状态修改, 宁可多留语句也不能漏掉。
    """

    def __init__(self):
        self._kinds = {}

    def declare(self, name: str, type_node) -> None:
        if not name:
            return
        if type_node is None:
            kind = "unknown"
        elif type_node.type in _PRIMITIVE_TYPE_NODES:
            kind = "primitive"
        elif type_node.type in _OBJECT_TYPE_NODES:
            kind = "unknown" if type_node.type == "type_identifier" and \
                type_node.text == b"var" else "object"
        else:
            kind = "unknown"
        self._kinds[name] = kind

    def mark_object(self, name: str) -> None:
        """被当作接收者使用的名字必然是对象 (x.foo() / x.f / x[i])。"""
        if name and self._kinds.get(name, "unknown") == "unknown":
            self._kinds[name] = "object"

    def is_object(self, name: str) -> bool:
        return self._kinds.get(name, "unknown") != "primitive"

    def is_known(self, name: str) -> bool:
        return name in self._kinds


def _declared_name_and_type(node):
    """返回声明节点引入的 (名字节点, 类型节点) 列表。"""
    kind = node.type
    if kind in ("local_variable_declaration", "field_declaration"):
        type_node = node.child_by_field_name("type")
        return [(child.child_by_field_name("name"), type_node)
                for child in node.children if child.type == "variable_declarator"]
    if kind in ("formal_parameter", "spread_parameter", "resource",
                "enhanced_for_statement"):
        return [(node.child_by_field_name("name"),
                 node.child_by_field_name("type"))]
    if kind == "catch_formal_parameter":
        return [(node.child_by_field_name("name"), None)]  # 异常一定是对象
    return []


def _build_symbol_table(method_node, class_node, code_bytes) -> _SymbolTable:
    symbols = _SymbolTable()
    # 先登记声明: 类字段 -> 方法形参与方法体内的各类声明。
    scopes = [n for n in _type_members(class_node) if n.type == "field_declaration"]
    scopes.extend(_iter_nodes(method_node))
    for node in scopes:
        for name_node, type_node in _declared_name_and_type(node):
            if name_node is not None:
                symbols.declare(get_node_text(name_node, code_bytes), type_node)
        if node.type == "catch_formal_parameter":
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                symbols.mark_object(get_node_text(name_node, code_bytes))
    # 再按使用位置补齐: 出现在接收者位置的名字视为对象。
    for node in _iter_nodes(method_node):
        receiver = None
        if node.type in ("method_invocation", "field_access"):
            receiver = node.child_by_field_name("object")
        elif node.type == "array_access":
            receiver = node.child_by_field_name("array")
        if receiver is not None and receiver.type == "identifier":
            symbols.mark_object(get_node_text(receiver, code_bytes))
    return symbols


def _is_variable_access(object_node, code_bytes, symbols: _SymbolTable) -> bool:
    """判断 field_access 的宿主是变量还是类名 (用于排除 System.out 这类静态访问)。"""
    root = _root_identifier(object_node, code_bytes)
    if root is None:
        return False
    if root == "this" or symbols.is_known(root):
        return True
    return not root[:1].isupper()  # Java 命名约定: 大写开头视为类型名


def _lvalue_targets(node, code_bytes, symbols: _SymbolTable) -> set:
    """赋值目标所修改的名字。obj.f = v 既改 f 也改 obj; arr[i] = v 改 arr。"""
    if node is None:
        return set()
    if node.type == "identifier":
        return {get_node_text(node, code_bytes)}
    if node.type == "field_access":
        targets = set()
        host = node.child_by_field_name("object")
        field = node.child_by_field_name("field")
        if field is not None and _is_variable_access(host, code_bytes, symbols):
            targets.add(get_node_text(field, code_bytes))
        root = _root_identifier(host, code_bytes)
        if root and root != "this":
            targets.add(root)
        return targets
    if node.type == "array_access":
        root = _root_identifier(node.child_by_field_name("array"), code_bytes)
        return {root} if root else set()
    return set()


def _collect_vars(node, code_bytes, symbols: _SymbolTable, names: set, defined: set) -> None:
    """FetchVarAndObj / FetchDefinedVarAndObj 的统一实现。

    names 收集语句中出现的全部变量与对象, defined 收集其中被定义或赋值的部分。
    方法名与类型名不是变量, 因此不计入 (原实现把它们当变量, 会让 V_req 被
    add/size 之类的方法名污染)。
    """
    kind = node.type
    if kind in _COMMENT_NODES:
        return
    if kind == "identifier":
        names.add(get_node_text(node, code_bytes))
        return
    if kind == "method_invocation":
        # 跳过 name 字段: 方法名不是变量。接收者与实参照常收集。
        for field in ("object", "arguments"):
            child = node.child_by_field_name(field)
            if child is not None:
                _collect_vars(child, code_bytes, symbols, names, defined)
        return
    if kind == "field_access":
        host = node.child_by_field_name("object")
        if host is not None:
            _collect_vars(host, code_bytes, symbols, names, defined)
        field = node.child_by_field_name("field")
        if field is not None and _is_variable_access(host, code_bytes, symbols):
            names.add(get_node_text(field, code_bytes))
        return
    if kind in ("assignment_expression", "update_expression"):
        target = node.child_by_field_name("left") if kind == "assignment_expression" \
            else next(iter(_named_children(node)), None)
        defined.update(_lvalue_targets(target, code_bytes, symbols))
        for child in _named_children(node):
            _collect_vars(child, code_bytes, symbols, names, defined)
        return

    for name_node, _ in _declared_name_and_type(node):
        if name_node is not None:
            text = get_node_text(name_node, code_bytes)
            names.add(text)
            defined.add(text)
    for child in _named_children(node):
        if child.type == "variable_declarator":
            value = child.child_by_field_name("value")
            if value is not None:
                _collect_vars(value, code_bytes, symbols, names, defined)
            continue
        if child.type in _OBJECT_TYPE_NODES or child.type in _PRIMITIVE_TYPE_NODES:
            continue  # 类型注解中没有变量
        _collect_vars(child, code_bytes, symbols, names, defined)


def _is_assert(stmt_node, code_bytes) -> bool:
    """IsAssert: Java 原生 assert 语句, 或 assertXxx()/Assert.assertXxx()/fail()。"""
    if stmt_node.type == "assert_statement":
        return True
    if stmt_node.type != "expression_statement":
        return False
    expression = next(iter(_named_children(stmt_node)), None)
    if expression is None or expression.type != "method_invocation":
        return False
    name = get_node_text(expression.child_by_field_name("name"), code_bytes)
    return name.lower().startswith("assert") or name in _ASSERT_EXTRA_NAMES


def _parse_to_statements(method_node, code_bytes, symbols: _SymbolTable) -> list:
    """Algorithm 1, L1: 把方法体解析为语句序列 S = <s_1, ..., s_n>。

    序列元素是方法体的顶层语句; if/for/try 等复合语句整体作为一个 s_i,
    其内部所有变量与副作用都通过子树遍历一并计入, 因此一旦被选中就完整保留,
    不会产生语法上不完整的切片。
    """
    body_node = method_node.child_by_field_name("body")
    if not body_node:
        return []
    statements = []
    for index, stmt_node in enumerate(_named_children(body_node)):
        names, defined = set(), set()
        _collect_vars(stmt_node, code_bytes, symbols, names, defined)
        statements.append({
            "index": index,
            "node": stmt_node,
            "code": get_node_text(stmt_node, code_bytes),
            "is_assert": _is_assert(stmt_node, code_bytes),
            "vars": names,                                  # V_i
            "defined": defined,                             # V_def
            "used_objects": {n for n in names if symbols.is_object(n)},  # V_use
        })
    return statements


def _perform_final_slice(all_statements: list, anchor_index: int,
                         required_vars: set, symbols: _SymbolTable) -> set:
    """Algorithm 1, L2-L23: 以 s_fail 为锚点的迭代式后向切片。

    L13 的两条准则:
      * 直接数据依赖   V_def ∩ V_req != 空
      * 隐式状态修改   非断言语句且 V_use ∩ V_req != 空 (V_use 只含对象)
    外层 while 由 L18 的 "新增名字中存在对象" 驱动重复遍历, 用于捕获别名导致
    的、首轮被跳过的副作用 (论文 Figure 3 的 listB 例子)。
    每次置 changed 都伴随 V_req 严格增长, 名字集有限, 故循环必然收敛。
    """
    slice_indices = {anchor_index}
    preceding = [s for s in all_statements if s["index"] < anchor_index]
    changed = True
    while changed:
        changed = False
        for stmt in reversed(preceding):  # L7: 自 s_fail 向前回溯
            if stmt["index"] in slice_indices:
                continue
            data_dependent = not stmt["defined"].isdisjoint(required_vars)
            state_modifying = (not stmt["is_assert"]
                               and not stmt["used_objects"].isdisjoint(required_vars))
            if not (data_dependent or state_modifying):
                continue
            slice_indices.add(stmt["index"])
            newly_added = stmt["vars"] - required_vars      # L16: V_new
            required_vars |= stmt["vars"]                   # L17
            if any(symbols.is_object(name) for name in newly_added):
                changed = True                              # L18-L19
    return slice_indices


def _reindent(stmt_node, code_bytes, indent: str) -> str:
    """按语句原始起始列做去缩进, 保证多行语句 (for/try 块) 排版不被破坏。"""
    raw = get_node_text(stmt_node, code_bytes)
    lines = raw.split("\n")
    result = [indent + lines[0].strip()]
    base = stmt_node.start_point[1]
    for line in lines[1:]:
        prefix, rest = line[:base], line[base:]
        result.append(indent + (rest.rstrip() if prefix.strip() == "" else line.strip()))
    return "\n".join(result)


def _reconstruct_method(original_method_node, required_indices: set,
                        all_statements: list, code_bytes: bytes) -> str:
    """Algorithm 1, L24: 保留原方法签名, 按原始执行顺序拼装保留语句。"""
    body_node = original_method_node.child_by_field_name("body")

    # 如果方法没有主体 (例如接口中的方法), 则直接返回原始文本
    if not body_node:
        return get_node_text(original_method_node, code_bytes)

    # 提取从方法开始到方法体 '{' 之前的所有文本作为签名 (含注解与 throws)
    signature_text = code_bytes[
        original_method_node.start_byte:body_node.start_byte
    ].decode("utf8", "replace").strip()

    node_map = {s["index"]: s["node"] for s in all_statements}
    body_lines = [
        _reindent(node_map[i], code_bytes, " " * 8)
        for i in sorted(required_indices) if i in node_map
    ]
    body = "\n".join(body_lines)
    return f"    {signature_text} {{\n{body}\n    }}"


def _invocation_signature(invocation_node, code_bytes, class_name: str):
    """把方法调用归一为 (名字, 实参个数); 只认对 C 自身成员的调用。

    过滤掉 s1.add(...) 这类作用在其他对象上的调用 —— 它们不是 C 定义的方法,
    原实现仅按名字匹配会把同名成员误当依赖。
    """
    receiver = invocation_node.child_by_field_name("object")
    if receiver is not None:
        receiver_text = get_node_text(receiver, code_bytes)
        if receiver_text not in ("this", class_name):
            return None
    name_node = invocation_node.child_by_field_name("name")
    if name_node is None:
        return None
    arguments = invocation_node.child_by_field_name("arguments")
    arity = len(_named_children(arguments)) if arguments is not None else 0
    return get_node_text(name_node, code_bytes), arity


def _callee_signatures(nodes, code_bytes, class_name: str) -> set:
    """FetchCalleeSigs: 给定节点集合中出现的、对 C 自身成员的调用签名。"""
    signatures = set()
    for root in nodes:
        for node in _iter_nodes(root):
            if node.type != "method_invocation":
                continue
            signature = _invocation_signature(node, code_bytes, class_name)
            if signature is not None:
                signatures.add(signature)
    return signatures


def _method_signature_index(class_node, code_bytes) -> dict:
    """M_C: C 内声明的方法, 以 (名字, 形参个数) 建索引并保留同名重载。"""
    index = {}
    for member in _type_members(class_node):
        if member.type not in ("method_declaration", "constructor_declaration"):
            continue
        name_node = member.child_by_field_name("name")
        if name_node is None:
            continue
        name = get_node_text(name_node, code_bytes)
        parameters = member.child_by_field_name("parameters")
        arity = len(_named_children(parameters)) if parameters is not None else 0
        index.setdefault((name, arity), []).append(member)
        index.setdefault((name, None), []).append(member)  # 形参个数无法匹配时的兜底
    return index


def _method_accepts_arity(method_node, arity: int) -> bool:
    """Conservatively match Java fixed-arity and varargs declarations."""
    parameters = method_node.child_by_field_name("parameters")
    declared = _named_children(parameters) if parameters is not None else []
    if declared and declared[-1].type == "spread_parameter":
        return arity >= len(declared) - 1
    return arity == len(declared)


def _declared_field_index(class_node, code_bytes) -> dict:
    """FetchDeclaredFields: 字段名 -> 其声明节点 (一条声明可含多个声明符)。"""
    fields = {}
    for member in _type_members(class_node):
        if member.type != "field_declaration":
            continue
        for child in member.children:
            if child.type != "variable_declarator":
                continue
            name_node = child.child_by_field_name("name")
            if name_node is not None:
                fields[get_node_text(name_node, code_bytes)] = member
    return fields


def _find_external_dependencies(sliced_statement_nodes: list, class_node,
                                 code_bytes: bytes, symbols: _SymbolTable) -> dict:
    """Algorithm 1, L25-L34: 求 T_min 在 C 内的方法闭包 D_m 与字段集合 D_v。"""
    class_name_node = class_node.child_by_field_name("name") if class_node else None
    class_name = get_node_text(class_name_node, code_bytes)
    method_index = _method_signature_index(class_node, code_bytes)
    field_index = _declared_field_index(class_node, code_bytes)

    def resolve(signature):
        name, arity = signature
        exact = method_index.get((name, arity), [])
        varargs = [method for method in method_index.get((name, None), [])
                   if _method_accepts_arity(method, arity)]
        resolved = {method.id: method for method in exact + varargs}
        return list(resolved.values())

    # L26-L31: 从 T_min 的直接调用出发, 迭代求传递闭包直到没有新方法。
    # NOTE: 论文以 "交集为空" 作为终止条件; 这里额外扣除已收集的签名, 否则递归
    # 或相互调用的辅助方法会让 M_new 稳定在非空集合而无法终止。语义不变。
    pending = _callee_signatures(sliced_statement_nodes, code_bytes, class_name)
    class_method_names = {name for name, _ in method_index}
    pending = {signature for signature in pending
               if signature[0] in class_method_names}
    dependent_signatures, dependent_methods = set(), []
    seen_method_ids = set()
    while pending:
        newly_found = set()
        for signature in pending:
            dependent_signatures.add(signature)
            for method_node in resolve(signature):
                if method_node.id in seen_method_ids:
                    continue
                seen_method_ids.add(method_node.id)
                dependent_methods.append(method_node)
                newly_found |= _callee_signatures([method_node], code_bytes, class_name)
        pending = ({signature for signature in newly_found
                    if signature[0] in class_method_names}
                   - dependent_signatures)

    dependent_methods.sort(key=lambda node: node.start_byte)

    # L32-L33: V_all = FetchVarAndObj(T_min) ∪ FetchVarAndObj(D_m), 再与字段求交。
    all_names = set()
    for node in list(sliced_statement_nodes) + dependent_methods:
        names, defined = set(), set()
        _collect_vars(node, code_bytes, symbols, names, defined)
        all_names |= names | defined
    dependent_fields = []
    seen_field_ids = set()
    for name in sorted(all_names & set(field_index)):
        field_node = field_index[name]
        if field_node.id not in seen_field_ids:
            seen_field_ids.add(field_node.id)
            dependent_fields.append(field_node)
    dependent_fields.sort(key=lambda node: node.start_byte)

    # L34: 取出对应的定义文本, 构成完整外部依赖 D。
    return {
        "methods": [get_node_text(n, code_bytes) for n in dependent_methods],
        "variables": [get_node_text(n, code_bytes) for n in dependent_fields],
    }


def _normalize_for_comparison(line: str) -> str:
    return " ".join(line.strip().rstrip(";").split())


def _locate_method(test_method_name: str, test_method_code: str,
                   full_file_tree, full_code_bytes: bytes):
    """在文件中唯一定位目标测试方法, 必要时用传入的源码解析出权威方法名。"""

    def candidates_named(name):
        return [n for n in _iter_nodes(full_file_tree.root_node)
                if n.type == "method_declaration"
                and get_node_text(n.child_by_field_name("name"), full_code_bytes) == name]

    candidate_nodes = candidates_named(test_method_name)
    if len(candidate_nodes) == 1:
        return candidate_nodes[0], None
    if len(candidate_nodes) > 1:
        print(f"信息: 文件中找到多个名为 '{test_method_name}' 的方法，将通过解析源码来确定唯一目标。")
    else:
        print(f"信息: 未在文件中找到名为 '{test_method_name}' 的方法，将通过解析源码来确定目标。")

    wrapped_code = f"class TemporaryWrapper {{\n{test_method_code}\n}}"
    temp_tree = _get_parser().parse(bytes(wrapped_code, "utf8"))
    wrapped_bytes = bytes(wrapped_code, "utf8")
    parsed_names = [get_node_text(n.child_by_field_name("name"), wrapped_bytes)
                    for n in _iter_nodes(temp_tree.root_node)
                    if n.type == "method_declaration"]
    if not parsed_names:
        return None, "错误: 无法从输入代码中解析出方法名。"
    final_candidates = candidates_named(parsed_names[0])
    if len(final_candidates) == 1:
        return final_candidates[0], None
    return None, f"错误: 最终无法在文件中唯一定位方法 '{parsed_names[0]}'。"


def _locate_failing_statement(statements: list, target_assert: str,
                              code_bytes: bytes, target_assert_line):
    """定位 s_fail, 返回 (锚点语句下标, s_fail 节点, 失败原因)。

    NOTE: 论文把 s_fail 作为输入直接给出。这里按文本匹配还原它, 并允许 s_fail
    位于 for/try 等复合语句内部 —— 此时锚点取其所在的顶层语句, 而 V_req 仍按
    L3 从真正的失败语句取种子。s_fail 本身是顶层语句时, 行为与论文完全一致。
    """
    clean_target = _normalize_for_comparison(target_assert)
    if not clean_target:
        return None, None, "未提供目标断言，返回原始完整函数。"

    def matches(node):
        return clean_target in _normalize_for_comparison(get_node_text(node, code_bytes))

    def pick(candidates, level: str):
        if target_assert_line is not None:
            narrowed = [c for c in candidates
                        if c[1].start_point[0] + 1 == target_assert_line]
            if len(narrowed) == 1:
                return narrowed[0], None
        if len(candidates) == 1:
            return candidates[0], None
        if len(candidates) > 1:
            return None, f"目标断言在{level}重复出现，返回原始完整函数。"
        return None, None

    top_level = [(s["index"], s["node"]) for s in statements if matches(s["node"])]
    chosen, reason = pick(top_level, "顶层语句中")
    if chosen is not None:
        return chosen[0], chosen[1], None
    if reason is not None:
        return None, None, reason

    # 回退: 在复合语句内部寻找断言, 锚点落在其所在的顶层语句上。
    index_of = {s["node"].id: s["index"] for s in statements}
    nested = []
    for stmt in statements:
        for node in _iter_nodes(stmt["node"]):
            if node is stmt["node"] or node.type not in ("expression_statement",
                                                         "assert_statement"):
                continue
            if matches(node):
                nested.append((index_of[stmt["node"].id], node))
    chosen, reason = pick(nested, "嵌套语句中")
    if chosen is not None:
        return chosen[0], chosen[1], None
    return None, None, reason or "未找到目标断言，返回原始完整函数。"


# --- 主入口函数 ---
def analyze_test_with_dependencies(test_method_name: str, test_method_code: str,
                                   target_assert: str, file_path: str,
                                   target_assert_line: int = None,
                                   validator: Callable | None = None) -> list:
    """对失败测试执行语义精简, 返回 [{"sliced_method", "dependencies"}]。

    target_assert_line 可选 (文件内 1 起始行号), 用于在同一断言文本重复出现时
    消歧; 不传时保持原有行为, 即退回原始完整方法。

    validator 可选, 由调用层执行编译与原故障保持检查。它接收候选方法及其依赖,
    返回包含 accepted(bool) 与 diagnostic(str) 的字典。拒绝或验证异常时保守回退
    到原始测试。该门禁位于 Algorithm 1 之外, 不改变切片判定规则。
    """
    try:
        with open(file_path, "rb") as f:
            full_code_bytes = f.read()
        full_file_tree = _get_parser().parse(full_code_bytes)
    except FileNotFoundError:
        return [{"status": "error",
                 "sliced_method": f"错误: 文件未找到 - {file_path}",
                 "dependencies": {},
                 "diagnostic": f"文件未找到: {file_path}"}]

    method_node, error = _locate_method(test_method_name, test_method_code,
                                        full_file_tree, full_code_bytes)
    if method_node is None:
        return [{"status": "error", "sliced_method": error,
                 "dependencies": {}, "diagnostic": error}]

    original_method_code = get_node_text(method_node, full_code_bytes)
    if full_file_tree.root_node.has_error:
        diagnostic = "Java AST 包含语法错误或缺失节点，已返回原始完整方法。"
        return [{"status": "fallback",
                 "sliced_method": original_method_code,
                 "dependencies": {"info": diagnostic},
                 "diagnostic": diagnostic}]

    class_node = _enclosing_type_decl(method_node)
    symbols = _build_symbol_table(method_node, class_node, full_code_bytes)
    statements = _parse_to_statements(method_node, full_code_bytes, symbols)
    if not statements:
        diagnostic = "方法体为空。"
        return [{"status": "fallback", "sliced_method": original_method_code,
                 "dependencies": {"info": diagnostic},
                 "diagnostic": diagnostic}]

    anchor_index, failing_node, reason = _locate_failing_statement(
        statements, target_assert, full_code_bytes, target_assert_line)
    if anchor_index is None:
        return [{"status": "fallback", "sliced_method": original_method_code,
                 "dependencies": {"info": reason}, "diagnostic": reason}]

    # L3: V_req 由真正的失败触发语句取种子
    seed_names, seed_defined = set(), set()
    _collect_vars(failing_node, full_code_bytes, symbols, seed_names, seed_defined)
    required_indices = _perform_final_slice(statements, anchor_index,
                                            seed_names | seed_defined, symbols)
    sliced_code = _reconstruct_method(method_node, required_indices,
                                      statements, full_code_bytes)
    sliced_nodes = [s["node"] for s in statements if s["index"] in required_indices]
    dependencies = _find_external_dependencies(sliced_nodes, class_node,
                                               full_code_bytes, symbols)
    if validator is None:
        return [{"status": "success", "sliced_method": sliced_code,
                 "dependencies": dependencies, "diagnostic": ""}]

    try:
        validation = validator(sliced_code, dependencies)
        if not isinstance(validation, dict) or \
                not isinstance(validation.get("accepted"), bool):
            raise ValueError("validator 必须返回包含 accepted(bool) 的字典")
        diagnostic = str(validation.get("diagnostic", ""))
        if validation["accepted"]:
            return [{"status": "validated", "sliced_method": sliced_code,
                     "dependencies": dependencies, "diagnostic": diagnostic}]
    except Exception as exc:
        diagnostic = f"纯化结果验证失败: {exc}"

    original_nodes = [statement["node"] for statement in statements]
    original_dependencies = _find_external_dependencies(
        original_nodes, class_node, full_code_bytes, symbols)
    original_dependencies["info"] = diagnostic
    return [{"status": "fallback", "sliced_method": original_method_code,
             "dependencies": original_dependencies,
             "diagnostic": diagnostic}]


if __name__ == "__main__":
    DEFAULT_TEST_FILE = ("/root/autodl-tmp/APR/defects4j_v2.0/source_projects/Chart-1/"
                         "tests/org/jfree/chart/renderer/category/junit/"
                         "AbstractCategoryItemRendererTests.java")

    DEMO_SOURCE = """package org.jfree.chart.renderer.category.junit;

public class AbstractCategoryItemRendererTests extends TestCase {

    private static final double EPSILON = 0.0000000001;

    private DefaultCategoryDataset buildDataset() {
        return new DefaultCategoryDataset();
    }

    public void test2947660() {
        AbstractCategoryItemRenderer r = new LineAndShapeRenderer();
        assertNotNull(r.getLegendItems());
        assertEquals(0, r.getLegendItems().getItemCount());

        DefaultCategoryDataset dataset = buildDataset();
        CategoryPlot plot = new CategoryPlot();
        plot.setDataset(dataset);
        plot.setRenderer(r);
        assertEquals(0, r.getLegendItems().getItemCount());

        dataset.addValue(1.0, "S1", "C1");
        LegendItemCollection lic = r.getLegendItems();
        assertEquals(1, lic.getItemCount());
        assertEquals("S1", lic.get(0).getLabel());
    }

    public void testAliasSideEffect() {
        List<String> listA = new ArrayList<>();
        List<String> listB = listA;
        listB.add("Bug Trigger!");
        assertEquals(1, listA.size());
    }
}
"""

    CASES = [
        ("test2947660", "assertEquals(1, lic.getItemCount());"),
        ("testAliasSideEffect", "assertEquals(1, listA.size());"),
    ]

    test_file_path = DEFAULT_TEST_FILE
    if not os.path.exists(test_file_path):
        test_file_path = os.path.join(tempfile.mkdtemp(prefix="java_slicer_demo_"),
                                      "AbstractCategoryItemRendererTests.java")
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(DEMO_SOURCE)
        print(f"提示: 未找到 '{DEFAULT_TEST_FILE}'，已使用示例文件 '{test_file_path}'。")

    for method_name, assertion in CASES:
        print("\n" + "=" * 60)
        print(f"--- 开始分析 {method_name} ---")
        print(f"文件路径: {test_file_path}")
        print(f"目标Assert语句: {assertion}")
        for result in analyze_test_with_dependencies(method_name, "", assertion,
                                                    test_file_path):
            print("\n[处理后的测试函数]")
            print(result["sliced_method"])
            print("\n[外部依赖分析]")
            dependencies = result.get("dependencies", {})
            info_msg = dependencies.get("info")
            if info_msg:
                print(f"信息: {info_msg}")
            elif not dependencies.get("methods") and not dependencies.get("variables"):
                print("未找到当前类定义的外部依赖。")
            else:
                if dependencies.get("variables"):
                    print("\n依赖的成员变量:")
                    for var_code in dependencies["variables"]:
                        print(var_code)
                if dependencies.get("methods"):
                    print("\n依赖的成员方法:")
                    for method_code in dependencies["methods"]:
                        print(method_code)
