import javalang
from defs.bug_info import BugInfo
from utils.ast_utils import code_to_ast, ast_to_code


def _escape_java_string_literal(text: str) -> str:
    return text.replace('\\', '\\\\').replace('"', '\\"')


def _create_println_statement(message: str) -> javalang.tree.StatementExpression:
    """创建 System.out.println(message) 的 AST 节点"""
    escaped = _escape_java_string_literal(message)
    literal = javalang.tree.Literal(value=f'"{escaped}"')
    invoke = javalang.tree.MethodInvocation(
        qualifier='System.out',
        member='println',
        arguments=[literal],
        type_arguments=None,
        postfix_operators=[],
        prefix_operators=[],
        selectors=[]
    )
    stmt = javalang.tree.StatementExpression(expression=invoke)
    return stmt


def _extract_var_debug_info(stmt: javalang.tree.Node) -> list:
    """提取变量声明或赋值，返回 (variable_name, value_expr) 的列表"""
    result = []
    if isinstance(stmt, javalang.tree.LocalVariableDeclaration):
        for declarator in stmt.declarators:
            var_name = declarator.name
            if var_name.startswith("__debug_"):
                continue
            if declarator.initializer is not None:
                result.append((var_name, declarator.initializer))
    elif isinstance(stmt, javalang.tree.StatementExpression):
        expr = stmt.expression
        if isinstance(expr, javalang.tree.Assignment):
            var_name = ast_to_code(expr.expressionl, 0)
            if not var_name.startswith("__debug_"):
                result.append((var_name, expr.value))
    return result


def _create_debug_output_statement(var_name: str, value_expr: javalang.tree.Node) -> javalang.tree.StatementExpression:
    """创建 // DEBUG [VAR] name = value 的输出语句"""
    # 创建字符串拼接表达式: "// DEBUG [VAR] " + var_name + " = " + var_name
    debug_prefix = javalang.tree.Literal(value='"// DEBUG [VAR] "')
    equals_literal = javalang.tree.Literal(value='" = "')
    
    # var_name 作为字符串
    escaped_name = _escape_java_string_literal(var_name)
    var_name_literal = javalang.tree.Literal(value=f'"{escaped_name}"')
    
    # 构建拼接表达式
    concat_expr = javalang.tree.BinaryOperation(
        operandl=javalang.tree.BinaryOperation(
            operandl=javalang.tree.BinaryOperation(
                operandl=debug_prefix,
                operandr=var_name_literal,
                operator="+"
            ),
            operandr=equals_literal,
            operator="+"
        ),
        operandr=javalang.tree.MemberReference(
            member=var_name,
            postfix_operators=[],
            prefix_operators=[],
            qualifier=None,
            selectors=[]
        ),
        operator="+"
    )
    
    invoke = javalang.tree.MethodInvocation(
        qualifier='System.out',
        member='println',
        arguments=[concat_expr],
        type_arguments=None,
        postfix_operators=[],
        prefix_operators=[],
        selectors=[]
    )
    stmt = javalang.tree.StatementExpression(expression=invoke)
    return stmt


def _create_return_debug_statement(return_expr: javalang.tree.Node = None, temp_var_name: str = None) -> javalang.tree.StatementExpression:
    """创建 return 调试输出语句"""
    if return_expr is None:
        # void return
        message = javalang.tree.Literal(value='"// DEBUG [RETURN] void"')
    else:
        # 有返回值，使用临时变量名
        debug_prefix = javalang.tree.Literal(value='"// DEBUG [RETURN] "')
        concat_expr = javalang.tree.BinaryOperation(
            operandl=debug_prefix,
            operandr=javalang.tree.MemberReference(
                member=temp_var_name,
                postfix_operators=[],
                prefix_operators=[],
                qualifier=None,
                selectors=[]
            ),
            operator="+"
        )
        message = concat_expr
    
    invoke = javalang.tree.MethodInvocation(
        qualifier='System.out',
        member='println',
        arguments=[message],
        type_arguments=None,
        postfix_operators=[],
        prefix_operators=[],
        selectors=[]
    )
    stmt = javalang.tree.StatementExpression(expression=invoke)
    return stmt


def _create_loop_debug_statement(loop_expr_str: str, temp_var_name: str) -> javalang.tree.StatementExpression:
    """创建循环调试输出语句: // DEBUG [LOOP] condition = boolean_value"""
    # 创建字符串拼接表达式: "// DEBUG [LOOP] " + loop_expr_str + " = " + temp_var_name
    debug_prefix = javalang.tree.Literal(value='"// DEBUG [LOOP] "')
    equals_literal = javalang.tree.Literal(value='" = "')
    
    # 循环条件表达式字符串
    escaped_loop = _escape_java_string_literal(loop_expr_str)
    loop_str_literal = javalang.tree.Literal(value=f'"{escaped_loop}"')
    
    # 构建拼接表达式
    concat_expr = javalang.tree.BinaryOperation(
        operator='+',
        operandl=debug_prefix,
        operandr=javalang.tree.BinaryOperation(
            operator='+',
            operandl=loop_str_literal,
            operandr=javalang.tree.BinaryOperation(
                operator='+',
                operandl=equals_literal,
                operandr=javalang.tree.MemberReference(
                    member=temp_var_name,
                    postfix_operators=[],
                    prefix_operators=[],
                    qualifier=None,
                    selectors=[]
                )
            )
        )
    )
    
    message = concat_expr
    
    invoke = javalang.tree.MethodInvocation(
        qualifier='System.out',
        member='println',
        arguments=[message],
        type_arguments=None,
        postfix_operators=[],
        prefix_operators=[],
        selectors=[]
    )
    stmt = javalang.tree.StatementExpression(expression=invoke)
    return stmt


def _create_direct_loop_debug_statement(loop_expr_str: str) -> javalang.tree.StatementExpression:
    """创建循环调试输出语句: // DEBUG [LOOP] condition = true"""
    debug_prefix = javalang.tree.Literal(value='"// DEBUG [LOOP] "')
    equals_literal = javalang.tree.Literal(value='" = "')
    escaped_loop = _escape_java_string_literal(loop_expr_str)
    loop_str_literal = javalang.tree.Literal(value=f'"{escaped_loop}"')
    true_literal = javalang.tree.Literal(value='true')
    concat_expr = javalang.tree.BinaryOperation(
        operator='+',
        operandl=debug_prefix,
        operandr=javalang.tree.BinaryOperation(
            operator='+',
            operandl=loop_str_literal,
            operandr=javalang.tree.BinaryOperation(
                operator='+',
                operandl=equals_literal,
                operandr=true_literal
            )
        )
    )
    invoke = javalang.tree.MethodInvocation(
        qualifier='System.out',
        member='println',
        arguments=[concat_expr],
        type_arguments=None,
        postfix_operators=[],
        prefix_operators=[],
        selectors=[]
    )
    return javalang.tree.StatementExpression(expression=invoke)


def _create_cond_debug_statement(cond_expr_str: str, temp_var_name: str) -> javalang.tree.StatementExpression:
    """创建条件调试输出语句: // DEBUG [COND] condition = boolean_value"""
    # 创建字符串拼接表达式: "// DEBUG [COND] " + cond_expr_str + " = " + temp_var_name
    debug_prefix = javalang.tree.Literal(value='"// DEBUG [COND] "')
    equals_literal = javalang.tree.Literal(value='" = "')
    
    # 条件表达式字符串
    escaped_cond = _escape_java_string_literal(cond_expr_str)
    cond_str_literal = javalang.tree.Literal(value=f'"{escaped_cond}"')
    
    # 构建拼接表达式
    concat_expr = javalang.tree.BinaryOperation(
        operator='+',
        operandl=debug_prefix,
        operandr=javalang.tree.BinaryOperation(
            operator='+',
            operandl=cond_str_literal,
            operandr=javalang.tree.BinaryOperation(
                operator='+',
                operandl=equals_literal,
                operandr=javalang.tree.MemberReference(
                    member=temp_var_name,
                    postfix_operators=[],
                    prefix_operators=[],
                    qualifier=None,
                    selectors=[]
                )
            )
        )
    )
    
    message = concat_expr
    
    invoke = javalang.tree.MethodInvocation(
        qualifier='System.out',
        member='println',
        arguments=[message],
        type_arguments=None,
        postfix_operators=[],
        prefix_operators=[],
        selectors=[]
    )
    stmt = javalang.tree.StatementExpression(expression=invoke)
    return stmt


_EXPR_OPERATOR_PRECEDENCE = {
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

def _get_expr_precedence(expr) -> int:
    if isinstance(expr, javalang.tree.BinaryOperation):
        return _EXPR_OPERATOR_PRECEDENCE.get(expr.operator, 0)
    if isinstance(expr, javalang.tree.Assignment):
        return -1
    return 100

def _format_expr_with_parentheses(expr, parent_operator: str = None, is_right: bool = False) -> str:
    if expr is None:
        return "null"
    if isinstance(expr, javalang.tree.Assignment):
        return f"({_expr_to_string(expr)})"
    if isinstance(expr, javalang.tree.BinaryOperation) and parent_operator is not None:
        child_prec = _get_expr_precedence(expr)
        parent_prec = _EXPR_OPERATOR_PRECEDENCE.get(parent_operator, 0)
        if child_prec < parent_prec:
            return f"({_expr_to_string(expr)})"
        if expr.operator != parent_operator:
            return f"({_expr_to_string(expr)})"
    return _expr_to_string(expr)

def _expr_to_string(expr) -> str:
    """将AST表达式转换为字符串表示"""
    if expr is None:
        return "null"
    
    # 获取前缀和后缀操作符
    prefix = ''.join(getattr(expr, 'prefix_operators', []) or [])
    postfix = ''.join(getattr(expr, 'postfix_operators', []) or [])
    
    # 处理不同类型的AST节点
    if isinstance(expr, javalang.tree.This):
        # 处理 this.field 或 this.method() 等
        result = "this"
        if expr.selectors:
            for selector in expr.selectors:
                if isinstance(selector, javalang.tree.MemberReference):
                    result += f".{selector.member}"
                # 可以扩展处理其他类型的selector
        return f"{prefix}{result}{postfix}"
    elif isinstance(expr, javalang.tree.MemberReference):
        # MemberReference like obj.method or variable, 也包括数组访问
        result = expr.member
        if expr.qualifier:
            qualifier_str = _expr_to_string(expr.qualifier)
            result = f"{qualifier_str}.{result}"
        
        # 处理选择器（如数组索引、方法调用）
        if expr.selectors:
            for selector in expr.selectors:
                if isinstance(selector, javalang.tree.ArraySelector):
                    index_str = _expr_to_string(selector.index)
                    result += f"[{index_str}]"
                else:
                    result += "." + ast_to_code(selector, 0)
        return f"{prefix}{result}{postfix}"
    elif isinstance(expr, javalang.tree.Assignment):
        left = _expr_to_string(expr.expressionl)
        right = _expr_to_string(expr.value)
        operator = expr.type if getattr(expr, 'type', None) else '='
        return f"{prefix}{left} {operator} {right}{postfix}"
    elif isinstance(expr, javalang.tree.ReferenceType):
        return f"{prefix}{ast_to_code(expr, 0)}{postfix}"
    elif isinstance(expr, javalang.tree.Literal):
        # Literal values: preserve string/char quotes
        result = str(expr.value) if expr.value is not None else ""
        if getattr(expr, 'selectors', None):
            for selector in expr.selectors:
                if isinstance(selector, javalang.tree.ArraySelector):
                    result += f"[{_expr_to_string(selector.index)}]"
                else:
                    result += "." + ast_to_code(selector, 0)
        return f"{prefix}{result}{postfix}"
    elif isinstance(expr, javalang.tree.BinaryOperation):
        # Binary operations like ==, !=, >, <, etc.
        left = _format_expr_with_parentheses(expr.operandl, expr.operator, is_right=False)
        right = _format_expr_with_parentheses(expr.operandr, expr.operator, is_right=True)
        inner = f"{left} {expr.operator} {right}"
        if prefix:
            return f"{prefix}({inner}){postfix}"
        return f"{inner}{postfix}"
    elif isinstance(expr, javalang.tree.MethodInvocation):
        # Method calls
        args = []
        if expr.arguments:
            for arg in expr.arguments:
                args.append(_expr_to_string(arg))
        args_str = ", ".join(args)
        if expr.qualifier:
            qualifier_str = _expr_to_string(expr.qualifier)
            return f"{prefix}{qualifier_str}.{expr.member}({args_str}){postfix}"
        else:
            return f"{prefix}{expr.member}({args_str}){postfix}"
    elif isinstance(expr, javalang.tree.Cast):
        # Type casting
        type_str = ast_to_code(expr.type, 0)
        expr_str = _expr_to_string(expr.expression)
        selectors = getattr(expr, "selectors", None)
        selector_part = ""
        if selectors:
            for selector in selectors:
                if isinstance(selector, javalang.tree.ArraySelector):
                    selector_part += f"[{_expr_to_string(selector.index)}]"
                else:
                    selector_part += "." + ast_to_code(selector, 0)
        return f"{prefix}({type_str})({expr_str}){selector_part}{postfix}"
    elif isinstance(expr, javalang.tree.TernaryExpression):
        # Ternary operator: condition ? trueExpr : falseExpr
        condition_str = _expr_to_string(expr.condition)
        true_str = _expr_to_string(expr.if_true)
        false_str = _expr_to_string(expr.if_false)
        return f"{prefix}{condition_str} ? {true_str} : {false_str}{postfix}"
    else:
        # 其他情况，尝试返回合理的字符串表示
        if hasattr(expr, '__str__'):
            return f"{prefix}{str(expr)}{postfix}"
        else:
            return f"{prefix}unknown_expression{postfix}"


def _find_last_return_in_block(block: javalang.tree.BlockStatement) -> javalang.tree.ReturnStatement:
    """递归查找块中的最后一个 return 语句"""
    if not block or not hasattr(block, 'statements'):
        return None
    
    for stmt in reversed(block.statements):
        if isinstance(stmt, javalang.tree.ReturnStatement):
            return stmt
        elif isinstance(stmt, javalang.tree.IfStatement):
            # 检查 then 和 else 块
            if stmt.then_statement and isinstance(stmt.then_statement, javalang.tree.BlockStatement):
                found = _find_last_return_in_block(stmt.then_statement)
                if found:
                    return found
            if stmt.else_statement and isinstance(stmt.else_statement, javalang.tree.BlockStatement):
                found = _find_last_return_in_block(stmt.else_statement)
                if found:
                    return found
        elif isinstance(stmt, javalang.tree.ForStatement):
            if stmt.body and isinstance(stmt.body, javalang.tree.BlockStatement):
                found = _find_last_return_in_block(stmt.body)
                if found:
                    return found
        elif isinstance(stmt, javalang.tree.WhileStatement):
            if stmt.body and isinstance(stmt.body, javalang.tree.BlockStatement):
                found = _find_last_return_in_block(stmt.body)
                if found:
                    return found
    return None


def _statement_completes_normally(stmt) -> bool:
    if stmt is None:
        return True
    if isinstance(stmt, javalang.tree.ReturnStatement):
        return False
    if isinstance(stmt, (javalang.tree.ThrowStatement, javalang.tree.BreakStatement, javalang.tree.ContinueStatement)):
        return False
    if isinstance(stmt, javalang.tree.BlockStatement):
        return _block_completes_normally(stmt)
    if isinstance(stmt, javalang.tree.IfStatement):
        then_norm = _statement_completes_normally(stmt.then_statement)
        if stmt.else_statement is None:
            return True
        return then_norm or _statement_completes_normally(stmt.else_statement)
    if isinstance(stmt, javalang.tree.TryStatement):
        if stmt.finally_block is not None:
            return _statement_completes_normally(stmt.finally_block)
        return True
    if isinstance(stmt, (javalang.tree.WhileStatement, javalang.tree.ForStatement, javalang.tree.DoStatement, javalang.tree.SwitchStatement)):
        return True
    if isinstance(stmt, javalang.tree.SynchronizedStatement):
        return _block_completes_normally(stmt.block)
    if hasattr(javalang.tree, 'LabeledStatement') and isinstance(stmt, javalang.tree.LabeledStatement):
        return _statement_completes_normally(stmt.statement)
    return True


def _block_completes_normally(block: javalang.tree.BlockStatement) -> bool:
    if not block or not hasattr(block, 'statements'):
        return True
    for stmt in block.statements:
        if not _statement_completes_normally(stmt):
            return False
    return True


def _process_statement_with_return_debug(stmt, end_marker: str, temp_var_counter: int, return_type=None):
    """处理单个语句或语句块中的 return 插桩"""
    if stmt is None:
        return None, temp_var_counter
    if isinstance(stmt, javalang.tree.BlockStatement):
        return _process_block_with_return_debug(stmt, end_marker, temp_var_counter, False, return_type)

    wrapper = javalang.tree.BlockStatement(label=None, statements=[stmt])
    wrapper, temp_var_counter = _process_block_with_return_debug(wrapper, end_marker, temp_var_counter, False, return_type)
    return wrapper, temp_var_counter


def _process_block_with_return_debug(block: javalang.tree.BlockStatement, end_marker: str, temp_var_counter: int, is_top_level: bool = False, return_type=None) -> tuple:
    """递归处理块中的 return 语句，插入调试输出"""
    if not block or not hasattr(block, 'statements'):
        return block, temp_var_counter
    
    new_statements = []
    last_return = _find_last_return_in_block(block) if is_top_level else None
    
    for stmt in block.statements:
        if isinstance(stmt, javalang.tree.ReturnStatement):
            
            # 处理 return 调试
            if stmt.expression is None:
                # return; -> 插入 void 调试
                debug_stmt = _create_return_debug_statement()
                new_statements.append(debug_stmt)
            else:
                # return value; -> 创建临时变量，插入调试，返回临时变量
                temp_var_name = f"__debug_return_{temp_var_counter}"
                temp_var_counter += 1
                
                # 创建临时变量声明: __debug_return_0 = value;
                temp_decl = javalang.tree.LocalVariableDeclaration(
                    annotations=[],
                    declarators=[javalang.tree.VariableDeclarator(
                        dimensions=[],
                        initializer=stmt.expression,
                        name=temp_var_name
                    )],
                    modifiers=set(),
                    type=return_type  # 使用方法的返回类型
                )
                new_statements.append(temp_decl)
                
                # 插入调试输出
                debug_stmt = _create_return_debug_statement(stmt.expression, temp_var_name)
                new_statements.append(debug_stmt)
                
                # 修改 return 语句返回临时变量
                stmt.expression = javalang.tree.MemberReference(
                    member=temp_var_name,
                    postfix_operators=[],
                    prefix_operators=[],
                    qualifier=None,
                    selectors=[]
                )

            # 在实际 return 前始终插入 end marker
            end_marker_stmt = _create_println_statement(end_marker)
            new_statements.append(end_marker_stmt)
        
        elif isinstance(stmt, javalang.tree.IfStatement):
            # 跳过循环内部自动插入的 break-if 语句
            if isinstance(stmt.condition, javalang.tree.MemberReference) and stmt.condition.prefix_operators == ['!'] and stmt.condition.member.startswith("__debug_loop_"):
                new_statements.append(stmt)
                continue
            
            # 处理 if 语句的条件插桩
            if stmt.condition:
                original_condition = stmt.condition
                
                # 创建布尔临时变量存储条件值
                cond_temp_var_name = f"__debug_cond_{temp_var_counter}"
                temp_var_counter += 1
                
                # 创建临时变量声明: boolean __debug_cond_0 = original_condition;
                cond_temp_decl = javalang.tree.LocalVariableDeclaration(
                    annotations=[],
                    declarators=[javalang.tree.VariableDeclarator(
                        dimensions=[],
                        initializer=original_condition,
                        name=cond_temp_var_name
                    )],
                    modifiers=set(),
                    type=javalang.tree.BasicType(name="boolean")
                )
                new_statements.append(cond_temp_decl)
                
                # 插入条件调试输出
                cond_expr_str = _expr_to_string(original_condition)
                cond_debug_stmt = _create_cond_debug_statement(cond_expr_str, cond_temp_var_name)
                new_statements.append(cond_debug_stmt)
                
                # 修改 if 语句的条件为临时变量
                stmt.condition = javalang.tree.MemberReference(
                    member=cond_temp_var_name,
                    postfix_operators=[],
                    prefix_operators=[],
                    qualifier=None,
                    selectors=[]
                )
            
            # 递归处理 if 语句的 then 和 else 块
            if stmt.then_statement is not None:
                stmt.then_statement, temp_var_counter = _process_statement_with_return_debug(stmt.then_statement, end_marker, temp_var_counter, return_type)
            if stmt.else_statement is not None:
                stmt.else_statement, temp_var_counter = _process_statement_with_return_debug(stmt.else_statement, end_marker, temp_var_counter, return_type)
        
        elif isinstance(stmt, javalang.tree.ForStatement):
            # 处理 for 循环的条件插桩
            if isinstance(stmt.control, javalang.tree.ForControl) and stmt.control.condition:
                # 创建布尔临时变量存储循环条件
                loop_temp_var_name = f"__debug_loop_{temp_var_counter}"
                temp_var_counter += 1
                
                # 获取原条件的字符串表示
                loop_expr_str = _expr_to_string(stmt.control.condition)
                original_condition = stmt.control.condition
                
                # 将循环条件改成true
                stmt.control.condition = javalang.tree.Literal(value='true')
                
                # 处理循环体
                if stmt.body is not None:
                    body_block = stmt.body if isinstance(stmt.body, javalang.tree.BlockStatement) else javalang.tree.BlockStatement(label=None, statements=[stmt.body])
                    new_body_stmts = []
                    
                    # 1. 创建临时变量声明: boolean __debug_loop_0 = 原条件;
                    loop_temp_decl = javalang.tree.LocalVariableDeclaration(
                        annotations=[],
                        declarators=[javalang.tree.VariableDeclarator(
                            dimensions=[],
                            initializer=original_condition,
                            name=loop_temp_var_name
                        )],
                        modifiers=set(),
                        type=javalang.tree.BasicType(name="boolean")
                    )
                    new_body_stmts.append(loop_temp_decl)
                    
                    # 2. 插入循环调试输出
                    loop_debug_stmt = _create_loop_debug_statement(loop_expr_str, loop_temp_var_name)
                    new_body_stmts.append(loop_debug_stmt)
                    
                    # 3. 插入break if (!temp_var)
                    break_if_stmt = javalang.tree.IfStatement(
                        condition=javalang.tree.MemberReference(
                            member=loop_temp_var_name,
                            postfix_operators=[],
                            prefix_operators=['!'],
                            qualifier=None,
                            selectors=[]
                        ),
                        then_statement=javalang.tree.BreakStatement(),
                        else_statement=None
                    )
                    new_body_stmts.append(break_if_stmt)
                    
                    # 4. 添加原循环体的语句
                    for orig_stmt in body_block.statements:
                        new_body_stmts.append(orig_stmt)
                    
                    # 更新循环体
                    stmt.body = javalang.tree.BlockStatement(label=None, statements=new_body_stmts)
                    
                    # 递归处理循环体
                    stmt.body, temp_var_counter = _process_block_with_return_debug(stmt.body, end_marker, temp_var_counter, False, return_type)
            else:
                # 如果没有条件，递归处理循环体
                if stmt.body is not None:
                    stmt.body, temp_var_counter = _process_statement_with_return_debug(stmt.body, end_marker, temp_var_counter, return_type)
        
        elif isinstance(stmt, javalang.tree.WhileStatement):
            # 处理 while 循环的条件插桩
            if stmt.condition:
                is_true_loop = isinstance(stmt.condition, javalang.tree.Literal) and str(stmt.condition.value).lower() == 'true'
                if is_true_loop:
                    # 保持 while(true) 原始逻辑，只在每次循环开始时打印 true
                    if stmt.body is not None:
                        body_block = stmt.body if isinstance(stmt.body, javalang.tree.BlockStatement) else javalang.tree.BlockStatement(label=None, statements=[stmt.body])
                        new_body_stmts = []
                        loop_debug_stmt = _create_direct_loop_debug_statement('true')
                        new_body_stmts.append(loop_debug_stmt)
                        for orig_stmt in body_block.statements:
                            new_body_stmts.append(orig_stmt)
                        stmt.body = javalang.tree.BlockStatement(label=None, statements=new_body_stmts)
                        stmt.body, temp_var_counter = _process_block_with_return_debug(stmt.body, end_marker, temp_var_counter, False, return_type)
                else:
                    # 创建布尔临时变量存储循环条件
                    loop_temp_var_name = f"__debug_loop_{temp_var_counter}"
                    temp_var_counter += 1
                    
                    # 获取原条件的字符串表示
                    loop_expr_str = _expr_to_string(stmt.condition)
                    original_condition = stmt.condition
                    
                    # 将循环条件改成true
                    stmt.condition = javalang.tree.Literal(value='true')
                    
                    # 处理循环体
                    if stmt.body is not None:
                        body_block = stmt.body if isinstance(stmt.body, javalang.tree.BlockStatement) else javalang.tree.BlockStatement(label=None, statements=[stmt.body])
                        new_body_stmts = []
                        
                        # 1. 创建临时变量声明: boolean __debug_loop_0 = 原条件;
                        loop_temp_decl = javalang.tree.LocalVariableDeclaration(
                            annotations=[],
                            declarators=[javalang.tree.VariableDeclarator(
                                dimensions=[],
                                initializer=original_condition,
                                name=loop_temp_var_name
                            )],
                            modifiers=set(),
                            type=javalang.tree.BasicType(name="boolean")
                        )
                        new_body_stmts.append(loop_temp_decl)
                        
                        # 2. 插入循环调试输出
                        loop_debug_stmt = _create_loop_debug_statement(loop_expr_str, loop_temp_var_name)
                        new_body_stmts.append(loop_debug_stmt)
                        
                        # 3. 插入break if (!temp_var)
                        break_if_stmt = javalang.tree.IfStatement(
                            condition=javalang.tree.MemberReference(
                                member=loop_temp_var_name,
                                postfix_operators=[],
                                prefix_operators=['!'],
                                qualifier=None,
                                selectors=[]
                            ),
                            then_statement=javalang.tree.BreakStatement(),
                            else_statement=None
                        )
                        new_body_stmts.append(break_if_stmt)
                        
                        # 4. 添加原循环体的语句
                        for orig_stmt in body_block.statements:
                            new_body_stmts.append(orig_stmt)
                        
                        # 更新循环体
                        stmt.body = javalang.tree.BlockStatement(label=None, statements=new_body_stmts)
                        
                        # 递归处理循环体
                        stmt.body, temp_var_counter = _process_block_with_return_debug(stmt.body, end_marker, temp_var_counter, False, return_type)
            else:
                # 如果没有条件，递归处理循环体
                if stmt.body is not None:
                    stmt.body, temp_var_counter = _process_statement_with_return_debug(stmt.body, end_marker, temp_var_counter, return_type)
        
        new_statements.append(stmt)
        
        # 插入变量调试输出
        var_info = _extract_var_debug_info(stmt)
        for var_name, value_expr in var_info:
            debug_stmt = _create_debug_output_statement(var_name, value_expr)
            new_statements.append(debug_stmt)
    
    block.statements = new_statements
    return block, temp_var_counter


def _is_constructor_invocation_statement(stmt) -> bool:
    if not isinstance(stmt, javalang.tree.StatementExpression):
        return False
    expr = getattr(stmt, 'expression', None)
    if expr is None:
        return False
    expr_type = type(expr).__name__
    return expr_type in {'SuperConstructorInvocation', 'ConstructorInvocation', 'ExplicitConstructorInvocation'}


def _process_body_statements(statements: list, start_marker: str, end_marker: str, return_type=None) -> list:
    """处理函数body语句，插入调试输出"""
    if not statements:
        statements = []
    
    # 保留传入的斜杠前缀；如果没有，默认添加一对 //
    start_marker = start_marker.strip()
    end_marker = end_marker.strip()
    if not start_marker.startswith("/"):
        start_marker = f"//{start_marker}"
    if not end_marker.startswith("/"):
        end_marker = f"//{end_marker}"
    
    # 创建一个虚拟的 BlockStatement 来包装顶级语句
    top_level_block = javalang.tree.BlockStatement(label=None, statements=statements)
    
    # 1. 开头插入 start marker
    start_stmt = _create_println_statement(start_marker)
    insert_index = 0
    if top_level_block.statements and _is_constructor_invocation_statement(top_level_block.statements[0]):
        insert_index = 1
    top_level_block.statements.insert(insert_index, start_stmt)
    
    # 2. 递归处理所有块中的 return 语句
    temp_var_counter = 0
    top_level_block, temp_var_counter = _process_block_with_return_debug(top_level_block, end_marker, temp_var_counter, True, return_type)
    
    # 3. 只有方法正常结束时才插入 end marker
    if _block_completes_normally(top_level_block):
        end_stmt = _create_println_statement(end_marker)
        top_level_block.statements.append(end_stmt)
    
    return top_level_block.statements


def rule_based_instrument_method(
    bug_info: BugInfo,
    start_marker: str = "DEBUG_MARKER_START",
    end_marker: str = "DEBUG_MARKER_END"
) -> str:
    """解析为AST，插入调试语句，转回源码。"""
    buggy_method = bug_info.buggy_method.strip()
    if not buggy_method:
        raise ValueError("buggy_method is empty")

    try:
        method_node = code_to_ast(buggy_method, source_type='member')
    except Exception:
        class_code = f"public class DummyClass {{\n{buggy_method}\n}}"
        compilation_unit = code_to_ast(class_code, source_type='compilation_unit')
        method_node = None
        for _, node in compilation_unit.filter(javalang.tree.MethodDeclaration):
            method_node = node
            break
        if method_node is None:
            raise ValueError("未找到方法声明")

    # 处理方法体语句
    if method_node.body:
        return_type = getattr(method_node, 'return_type', None)
        method_node.body = _process_body_statements(method_node.body, start_marker, end_marker, return_type)
    
    return ast_to_code(method_node)


def rule_insert_print(
    bug_info: BugInfo,
    start_marker: str = "START_DEBUG",
    end_marker: str = "END_DEBUG"
) -> str:
    """插桩函数：在方法体的关键位置插入调试输出语句。"""
    try:
        return rule_based_instrument_method(bug_info, start_marker, end_marker)
    except Exception as e:
        import traceback
        print(f"Instrumentation failed: {e}")
        print(traceback.format_exc())
        return ""
