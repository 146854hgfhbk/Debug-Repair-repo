import javalang
from typing import Any, Iterable, List, Optional


def code_to_ast(code: str, source_type: str = "compilation_unit") -> Any:
    """Parse Java source into a javalang AST node.

    Args:
        code: Java source text.
        source_type: One of "compilation_unit", "member", "statement", "expression", "block".

    Returns:
        A parsed AST node from javalang.
    """
    source_type = source_type.strip().lower()
    if source_type not in {"compilation_unit", "member", "statement", "expression", "block"}:
        raise ValueError(f"Unsupported source_type: {source_type}")

    java_code = code.strip()
    if not java_code:
        raise ValueError("Empty Java source code")

    tokens = javalang.tokenizer.tokenize(java_code)
    parser = javalang.parser.Parser(tokens)

    if source_type == "member":
        return parser.parse_member_declaration()
    if source_type == "statement":
        wrapped = f"public class Dummy {{ void m() {{ {java_code} }} }}"
        compilation_unit = javalang.parse.parse(wrapped)
        for _, node in compilation_unit.filter(javalang.tree.MethodDeclaration):
            if node.body:
                return node.body[0]
        raise ValueError("Unable to parse statement")
    if source_type == "expression":
        return javalang.parse.parse_expression(java_code)
    if source_type == "block":
        if not java_code.strip().startswith("{"):
            java_code = "{" + java_code + "}"
        tokens = javalang.tokenizer.tokenize(java_code)
        parser = javalang.parser.Parser(tokens)
        return parser.parse_block()

    return parser.parse()


def ast_to_code(node: Any, indent_level: int = 0) -> str:
    """Convert a javalang AST node back into Java source text.

    This is not a fully general Java pretty-printer, but it covers common AST
    nodes used for method bodies, statements, expressions, declarations, and
    simple class structures.
    """
    if node is None:
        return ""

    if isinstance(node, str):
        return node

    if isinstance(node, bool):
        return "true" if node else "false"

    if isinstance(node, (int, float)):
        return str(node)

    if isinstance(node, javalang.tree.Node):
        return _node_to_code(node, indent_level)

    if isinstance(node, (list, tuple)):
        return _sequence_to_code(node, indent_level)

    return str(node)


def _sequence_to_code(nodes: Iterable[Any], indent_level: int = 0) -> str:
    parts: List[str] = []
    for child in nodes:
        value = ast_to_code(child, indent_level)
        if value:
            parts.append(value)
    return "\n".join(parts)


def _join_args(items: Optional[Iterable[Any]], separator: str = ", ", indent_level: int = 0) -> str:
    if not items:
        return ""
    parts: List[str] = []
    for item in items:
        part = ast_to_code(item, indent_level)
        if part:
            parts.append(part)
    return separator.join(parts)


def _apply_selectors(node: javalang.tree.Node, indent_level: int = 0) -> str:
    selectors = getattr(node, "selectors", None)
    if not selectors:
        return ""
    parts: List[str] = []
    for selector in selectors:
        if isinstance(selector, javalang.tree.ArraySelector):
            parts.append(f"[{ast_to_code(selector.index, indent_level)}]")
        else:
            parts.append("." + ast_to_code(selector, indent_level))
    return "".join(parts)


_OPERATOR_PRECEDENCE = {
    "||": 1,
    "&&": 2,
    "|": 3,
    "^": 4,
    "&": 5,
    "==": 6,
    "!=": 6,
    "<": 7,
    ">": 7,
    "<=": 7,
    ">=": 7,
    "instanceof": 7,
    "<<": 8,
    ">>": 8,
    ">>>": 8,
    "+": 9,
    "-": 9,
    "*": 10,
    "/": 10,
    "%": 10,
}


def _format_binary_operand(child: Any, parent_operator: str, is_right: bool = False) -> str:
    text = ast_to_code(child, 0)
    if isinstance(child, javalang.tree.Assignment):
        return f"({text})"
    if isinstance(child, javalang.tree.BinaryOperation):
        child_prec = _OPERATOR_PRECEDENCE.get(child.operator, 0)
        parent_prec = _OPERATOR_PRECEDENCE.get(parent_operator, 0)
        if child_prec < parent_prec or child.operator != parent_operator:
            return f"({text})"
        if is_right and child_prec == parent_prec and parent_operator not in {"+", "*", "||", "&&", "&", "|", "^"}:
            return f"({text})"
    return text


def _prefix_postfix(node: javalang.tree.Node) -> str:
    prefix = getattr(node, "prefix_operators", None)
    if prefix:
        return "".join(prefix)
    return ""


def _postfix(node: javalang.tree.Node) -> str:
    postfix = getattr(node, "postfix_operators", None)
    if postfix:
        return "".join(postfix)
    return ""


def _format_reference_type(node: javalang.tree.ReferenceType) -> str:
    if node is None:
        return ""
    name = node.name if isinstance(node.name, str) else ast_to_code(node.name, 0)
    if getattr(node, "sub_type", None):
        name = f"{name}.{_format_reference_type(node.sub_type)}"
    type_args = _type_arguments(node.arguments, 0)
    dimensions = "[]" * len(node.dimensions) if getattr(node, "dimensions", None) else ""
    return f"{name}{type_args}{dimensions}"


def _node_to_code(node: javalang.tree.Node, indent_level: int = 0) -> str:
    indent = "    " * indent_level

    if isinstance(node, javalang.tree.Literal):
        prefix = _prefix_postfix(node)
        postfix = _postfix(node)
        result = node.value if node.value is not None else ""
        if getattr(node, 'selectors', None):
            for selector in node.selectors:
                if isinstance(selector, javalang.tree.ArraySelector):
                    result += f"[{ast_to_code(selector.index, indent_level)}]"
                else:
                    result += "." + ast_to_code(selector, indent_level)
        return f"{prefix}{result}{postfix}"

    if isinstance(node, javalang.tree.ArrayCreator):
        type_str = ast_to_code(node.type, 0)
        dims = "".join(f"[{ast_to_code(dim, 0)}]" for dim in (node.dimensions or []))
        initializer = f"{ast_to_code(node.initializer, 0)}" if getattr(node, "initializer", None) is not None else ""
        return f"new {type_str}{dims}{initializer}"

    if isinstance(node, javalang.tree.ArraySelector):
        return f"[{ast_to_code(node.index, 0)}]"

    if isinstance(node, javalang.tree.ArrayInitializer):
        values = _join_args(node.initializers, ", ", 0)
        return f"{{{values}}}"

    if isinstance(node, javalang.tree.ThrowStatement):
        expr = ast_to_code(node.expression, 0) if getattr(node, "expression", None) is not None else ""
        return f"{indent}throw {expr};"

    if isinstance(node, javalang.tree.MemberReference):
        qualifier = ast_to_code(node.qualifier, 0)
        qualifier_part = f"{qualifier}." if qualifier else ""
        selector_part = _apply_selectors(node, 0)
        prefix = _prefix_postfix(node)
        postfix = _postfix(node)
        return f"{prefix}{qualifier_part}{node.member}{selector_part}{postfix}"

    if isinstance(node, javalang.tree.MethodInvocation):
        qualifier = ast_to_code(node.qualifier, 0)
        qualifier_part = f"{qualifier}." if qualifier else ""
        type_args = _type_arguments(node.type_arguments, 0)
        args = _join_args(node.arguments, ", ", 0)
        selector_part = _apply_selectors(node, 0)
        return f"{qualifier_part}{node.member}{type_args}({args}){selector_part}"

    if isinstance(node, javalang.tree.ClassCreator):
        type_str = ast_to_code(node.type, 0)
        args = _join_args(node.arguments, ", ", 0)
        body = ast_to_code(node.body, indent_level) if getattr(node, "body", None) else ""
        return f"new {type_str}({args}){body}"

    if isinstance(node, javalang.tree.This):
        return "this" + _apply_selectors(node, 0)

    if isinstance(node, javalang.tree.SuperMemberReference):
        selector_part = _apply_selectors(node, 0)
        return f"super.{node.member}{selector_part}"

    if isinstance(node, javalang.tree.SuperMethodInvocation):
        type_args = _type_arguments(node.type_arguments, 0)
        args = _join_args(node.arguments, ", ", 0)
        selector_part = _apply_selectors(node, 0)
        return f"super.{node.member}{type_args}({args}){selector_part}"

    if isinstance(node, javalang.tree.SuperConstructorInvocation):
        args = _join_args(node.arguments, ", ", 0)
        return f"super({args})"

    if isinstance(node, javalang.tree.ExplicitConstructorInvocation):
        args = _join_args(node.arguments, ", ", 0)
        return f"this({args})"

    if isinstance(node, javalang.tree.ReferenceType):
        return _format_reference_type(node)

    if isinstance(node, javalang.tree.BasicType):
        dimensions = "[]" * len(node.dimensions) if getattr(node, "dimensions", None) else ""
        return f"{node.name}{dimensions}"

    if isinstance(node, javalang.tree.Assignment):
        left = ast_to_code(node.expressionl, 0)
        right = ast_to_code(node.value, 0)
        operator = node.type if getattr(node, "type", None) else "="
        return f"{left} {operator} {right}"

    if isinstance(node, javalang.tree.BinaryOperation):
        left = _format_binary_operand(node.operandl, node.operator, is_right=False)
        right = _format_binary_operand(node.operandr, node.operator, is_right=True)
        prefix = _prefix_postfix(node)
        inner = f"{left} {node.operator} {right}"
        if prefix:
            return f"{prefix}({inner})"
        return inner

    if isinstance(node, javalang.tree.TernaryExpression):
        cond = ast_to_code(node.condition, 0)
        true_part = ast_to_code(node.if_true, 0)
        false_part = ast_to_code(node.if_false, 0)
        return f"{cond} ? {true_part} : {false_part}"

    if isinstance(node, javalang.tree.Cast):
        type_str = ast_to_code(node.type, 0)
        expr_str = ast_to_code(node.expression, 0)
        selector_part = _apply_selectors(node, 0)
        return f"({type_str})({expr_str}){selector_part}"

    if isinstance(node, javalang.tree.VariableDeclarator):
        name = node.name
        if getattr(node, "initializer", None) is not None:
            return f"{name} = {ast_to_code(node.initializer, 0)}"
        return name

    if isinstance(node, javalang.tree.LocalVariableDeclaration):
        modifiers = " ".join(sorted(node.modifiers)) if getattr(node, "modifiers", None) else ""
        type_str = ast_to_code(node.type, 0)
        declarators = _join_args(node.declarators, ", ", 0)
        prefix = f"{modifiers} " if modifiers else ""
        return f"{indent}{prefix}{type_str} {declarators};"

    if isinstance(node, javalang.tree.FormalParameter):
        type_str = ast_to_code(node.type, 0)
        if getattr(node, 'varargs', False):
            type_str += '...'
        modifiers = " ".join(sorted(node.modifiers)) if getattr(node, 'modifiers', None) else ""
        prefix = f"{modifiers} " if modifiers else ""
        return f"{prefix}{type_str} {node.name}"

    if isinstance(node, javalang.tree.VariableDeclaration):
        type_str = ast_to_code(node.type, 0)
        declarators = _join_args(node.declarators, ", ", 0)
        modifiers = " ".join(sorted(node.modifiers)) if getattr(node, "modifiers", None) else ""
        prefix = f"{modifiers} " if modifiers else ""
        return f"{prefix}{type_str} {declarators}"

    if isinstance(node, javalang.tree.StatementExpression):
        expr = ast_to_code(node.expression, 0)
        return f"{indent}{expr};"

    if isinstance(node, javalang.tree.ReturnStatement):
        expression = ast_to_code(node.expression, 0) if getattr(node, "expression", None) is not None else ""
        return f"{indent}return{(' ' + expression) if expression else ''};"

    if isinstance(node, javalang.tree.IfStatement):
        condition = ast_to_code(node.condition, 0)
        if isinstance(node.then_statement, javalang.tree.BlockStatement):
            then_block = ast_to_code(node.then_statement, indent_level)
            then_lines = then_block.splitlines()
            if then_lines:
                then_lines[0] = then_lines[0].strip()
            result = f"{indent}if ({condition}) {then_lines[0]}"
            if len(then_lines) > 1:
                result += "\n" + "\n".join(then_lines[1:])
        else:
            then_code = ast_to_code(node.then_statement, indent_level + 1)
            result = f"{indent}if ({condition}) {{\n{then_code}\n{indent}}}"

        if getattr(node, "else_statement", None) is not None:
            if isinstance(node.else_statement, javalang.tree.BlockStatement):
                else_block = ast_to_code(node.else_statement, indent_level)
                else_lines = else_block.splitlines()
                if else_lines:
                    else_lines[0] = else_lines[0].strip()
                result += f" else {else_lines[0]}"
                if len(else_lines) > 1:
                    result += "\n" + "\n".join(else_lines[1:])
            else:
                else_code = ast_to_code(node.else_statement, indent_level + 1)
                result += f" else {{\n{else_code}\n{indent}}}"
        return result

    if isinstance(node, javalang.tree.BreakStatement):
        return f"{indent}break;"

    if isinstance(node, javalang.tree.ContinueStatement):
        return f"{indent}continue;"

    if isinstance(node, javalang.tree.WhileStatement):
        condition = ast_to_code(node.condition, 0)
        if isinstance(node.body, javalang.tree.BlockStatement):
            body_block = ast_to_code(node.body, indent_level)
            body_lines = body_block.splitlines()
            if body_lines:
                body_lines[0] = body_lines[0].strip()
            result = f"{indent}while ({condition}) {body_lines[0]}"
            if len(body_lines) > 1:
                result += "\n" + "\n".join(body_lines[1:])
            return result
        body = ast_to_code(node.body, indent_level + 1)
        return f"{indent}while ({condition}) {{\n{body}\n{indent}}}"

    if isinstance(node, javalang.tree.ForStatement):
        control = node.control
        if isinstance(control, javalang.tree.EnhancedForControl):
            var_str = ast_to_code(control.var, 0)
            iterable_str = ast_to_code(control.iterable, 0)
            if isinstance(node.body, javalang.tree.BlockStatement):
                body_block = ast_to_code(node.body, indent_level)
                body_lines = body_block.splitlines()
                if body_lines:
                    body_lines[0] = body_lines[0].strip()
                result = f"{indent}for ({var_str} : {iterable_str}) {body_lines[0]}"
                if len(body_lines) > 1:
                    result += "\n" + "\n".join(body_lines[1:])
                return result
            body = ast_to_code(node.body, indent_level + 1)
            return f"{indent}for ({var_str} : {iterable_str}) {{\n{body}\n{indent}}}"
        else:
            init = _format_control_part(getattr(control, "init", None))
            condition = ast_to_code(getattr(control, "condition", None), 0)
            update = _format_control_part(getattr(control, "update", None))
            if isinstance(node.body, javalang.tree.BlockStatement):
                body_block = ast_to_code(node.body, indent_level)
                body_lines = body_block.splitlines()
                if body_lines:
                    body_lines[0] = body_lines[0].strip()
                result = f"{indent}for ({init}; {condition}; {update}) {body_lines[0]}"
                if len(body_lines) > 1:
                    result += "\n" + "\n".join(body_lines[1:])
                return result
            body = ast_to_code(node.body, indent_level + 1)
            return f"{indent}for ({init}; {condition}; {update}) {{\n{body}\n{indent}}}"

    if isinstance(node, javalang.tree.DoStatement):
        condition = ast_to_code(node.condition, 0)
        if isinstance(node.body, javalang.tree.BlockStatement):
            body = ast_to_code(node.body, indent_level)
            body_lines = body.splitlines()
            if body_lines:
                body_lines[0] = body_lines[0].lstrip()
            body = "\n".join(body_lines)
            return f"{indent}do {body} while ({condition});"
        body = ast_to_code(node.body, indent_level + 1)
        return f"{indent}do {{\n{body}\n{indent}}} while ({condition});"

    if isinstance(node, javalang.tree.SwitchStatementCase):
        lines: List[str] = []
        cases = getattr(node, 'case', None)
        if not cases:
            lines.append(f"{indent}default:")
        else:
            # case may be a list of labels
            if isinstance(cases, (list, tuple)):
                for case in cases:
                    lines.append(f"{indent}case {ast_to_code(case, 0)}:")
            else:
                lines.append(f"{indent}case {ast_to_code(cases, 0)}:")
        for statement in node.statements or []:
            stmt_code = ast_to_code(statement, indent_level + 1)
            if stmt_code:
                lines.append(stmt_code)
        return "\n".join(lines)

    if isinstance(node, javalang.tree.SwitchStatement):
        expression = ast_to_code(node.expression, 0)
        case_lines: List[str] = []
        for case in node.cases or []:
            case_lines.append(ast_to_code(case, indent_level + 1))
        cases_code = "\n".join(case_lines)
        return f"{indent}switch ({expression}) {{\n{cases_code}\n{indent}}}"

    if isinstance(node, javalang.tree.BlockStatement):
        lines: List[str] = []
        for statement in node.statements or []:
            s = ast_to_code(statement, indent_level + 1)
            if s:
                lines.append(s)
        block_body = "\n".join(lines)
        return f"{indent}{{\n{block_body}\n{indent}}}"

    if isinstance(node, javalang.tree.CatchClauseParameter):
        types = []
        for t in node.types or []:
            types.append(ast_to_code(t, 0) if isinstance(t, javalang.tree.Node) else str(t))
        types_str = " | ".join(types)
        return f"{types_str} {node.name}"

    if isinstance(node, javalang.tree.CatchClause):
        param = ast_to_code(node.parameter, 0)
        body_lines: List[str] = []
        for statement in node.block or []:
            body_lines.append(ast_to_code(statement, indent_level + 1))
        body = "\n".join(body_lines)
        return f"{indent}catch ({param}) {{\n{body}\n{indent}}}"

    if isinstance(node, javalang.tree.TryStatement):
        body_lines: List[str] = []
        for statement in node.block or []:
            body_lines.append(ast_to_code(statement, indent_level + 1))
        body = "\n".join(body_lines)
        result = f"{indent}try {{\n{body}\n{indent}}}"
        for catch_clause in node.catches or []:
            result += "\n" + ast_to_code(catch_clause, indent_level)
        if getattr(node, "finally_block", None) is not None:
            finally_lines: List[str] = []
            for statement in node.finally_block or []:
                finally_lines.append(ast_to_code(statement, indent_level + 1))
            finally_body = "\n".join(finally_lines)
            result += f"\n{indent}finally {{\n{finally_body}\n{indent}}}"
        return result

    if isinstance(node, javalang.tree.MethodDeclaration):
        modifiers = " ".join(sorted(node.modifiers)) if getattr(node, "modifiers", None) else ""
        type_params = _type_parameters(getattr(node, "type_parameters", None), 0)
        return_type = ast_to_code(node.return_type, 0) if getattr(node, "return_type", None) else "void"
        params = _join_args(node.parameters, ", ", 0)
        throws = " throws " + _join_args(node.throws, ", ", 0) if getattr(node, "throws", None) else ""
        body_lines = []
        if node.body:
            for stmt in node.body:
                body_lines.append(ast_to_code(stmt, indent_level + 1))
        body = "\n".join(body_lines)
        header = f"{modifiers + ' ' if modifiers else ''}{type_params + ' ' if type_params else ''}{return_type} {node.name}({params}){throws}"
        return f"{indent}{header} {{\n{body}\n{indent}}}"

    if isinstance(node, javalang.tree.ConstructorDeclaration):
        modifiers = " ".join(sorted(node.modifiers)) if getattr(node, "modifiers", None) else ""
        params = _join_args(node.parameters, ", ", 0)
        body_lines = []
        if node.body:
            for stmt in node.body:
                body_lines.append(ast_to_code(stmt, indent_level + 1))
        body = "\n".join(body_lines)
        header = f"{modifiers + ' ' if modifiers else ''}{node.name}({params})"
        return f"{indent}{header} {{\n{body}\n{indent}}}"

    if isinstance(node, javalang.tree.ClassDeclaration):
        modifiers = " ".join(sorted(node.modifiers)) if getattr(node, "modifiers", None) else ""
        extends = f" extends {ast_to_code(node.extends, 0)}" if getattr(node, "extends", None) else ""
        implements = " implements " + _join_args(node.implements, ", ", 0) if getattr(node, "implements", None) else ""
        body_lines: List[str] = []
        for member in node.body or []:
            body_lines.append(ast_to_code(member, indent_level + 1))
        body = "\n".join(body_lines)
        header = f"{modifiers + ' ' if modifiers else ''}class {node.name}{extends}{implements}"
        return f"{indent}{header} {{\n{body}\n{indent}}}"

    if isinstance(node, javalang.tree.CompilationUnit):
        parts: List[str] = []
        if getattr(node, "package", None) is not None:
            parts.append(ast_to_code(node.package, 0))
        for imp in getattr(node, "imports", []) or []:
            parts.append(ast_to_code(imp, 0))
        for type_decl in getattr(node, "types", []) or []:
            parts.append(ast_to_code(type_decl, 0))
        return "\n\n".join(parts)

    if hasattr(node, "children"):
        child_parts: List[str] = []
        for child in node.children:
            if child is None:
                continue
            child_text = ast_to_code(child, indent_level)
            if child_text:
                child_parts.append(child_text)
        return " ".join(child_parts)

    return str(node)


def _FormatModifierList(modifiers: Optional[Iterable[str]]) -> str:
    if not modifiers:
        return ""
    return " ".join(sorted(modifiers))


def _type_arguments(type_args: Optional[Iterable[Any]], indent_level: int = 0) -> str:
    if not type_args:
        return ""
    return "<" + _join_args(type_args, ", ", indent_level) + ">"


def _type_parameters(type_params: Optional[Iterable[Any]], indent_level: int = 0) -> str:
    if not type_params:
        return ""
    return "<" + _join_args(type_params, ", ", indent_level) + ">"


def _format_control_part(item: Any) -> str:
    if item is None:
        return ""
    if isinstance(item, (list, tuple)):
        return ", ".join(ast_to_code(elem, 0) for elem in item if ast_to_code(elem, 0))
    return ast_to_code(item, 0)
