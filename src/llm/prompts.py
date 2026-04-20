
class Prompts:
    """
    一个集中的Prompt模板库
    """
    # 仅提供 buggy func 的空白对照
    EASY_REPAIR = """
    Your mission is to repair the provided buggy Java function.
    
    **Buggy Java Function:**
    ```java
    {buggy_function}

    Buggy lines are marked with '// Buggy Line' as hints. The actual fix may involve changes around these lines or adding new statements if necessary.

    CRITICAL OUTPUT FORMAT:
    Your response must enclose the entire function within a ```java ... ``` code block.
    """

    # llm直接修复, 提供buggy func, test context, error info
    DIRECT_REPAIR = """
    Your mission is to repair the provided buggy Java function using the context below.
    
    **Buggy Java Function:**
    ```java
    {buggy_function}

    Buggy lines are marked with '// Buggy Line' as hints. The actual fix may involve changes around these lines or adding new statements if necessary.
    
    **Bug Context:**
    1.  **Failing Test Context:**
        ```java
        {test_context}
        ```
    2.  **Error information:**
        ```
        {error_info}
        ```

    CRITICAL OUTPUT FORMAT:
    Your response must enclose the entire function within a ```java ... ``` code block.
    """

    # 核心方法, 提供 buggy func, test context, error info, instrumented func, feedback
    DEBUG_REPAIR = """
    The following Java function contains a bug:
    ```java
    {buggy_function}
    ```
    Buggy lines are marked with '// Buggy Line' as hints. The actual fix may involve changes around these lines or adding new statements if necessary.

    The following is the information that can help you with the repair:

        1) Failing test context:
        ```java
        {test_context}
        ```
        2) Filtered error log:
        ```
        {error_info}
        ```
        3) The buggy method, with debug prints and runtime output comments:
        ```java
        {instrumented_function}
        ```
        {runtime_output}
        4) Feedback on the PREVIOUS attempt:
        ```
        {feedback}
        ```
    Based on all the information above, provide a new, corrected version of the entire method.
    Output the FINAL complete fixed Java method **must enclose the entire function within a ```java ... ``` code block**.
    """

    # 构建 feedback 的 prompt
    FEEDBACK = """
    The previous attempt to fix the bug was unsuccessful. Here is the feedback from the validator and the code that was submitted:
    
    [Validator Feedback]
    {validator_feedback}

    [Previous Incorrect Patch]
    {previous_patch}

    Please analyze the feedback and the incorrect patch to provide a new, correct version of the entire method.
    """

    # 插入输出的消融测试
    ABLATION_TEST_OF_INSERT_PRINT = """
    The following Java function contains a bug:
    ```java
    {buggy_function}
    ```
    Buggy lines are marked with '// Buggy Line' as hints. The actual fix may involve changes around these lines or adding new statements if necessary.

    The following is the information that can help you with the repair:
        1) Failing test context:
        ```java
        {test_context}
        ```
        2) Filtered error log:
        ```
        {error_info}
        ```
        3) Feedback on the PREVIOUS attempt:
        ```
        {feedback}
        ```
    Based on all the information above, provide a new, corrected version of the entire method.
    Output the FINAL complete fixed Java method **must enclose the entire function within a ```java ... ``` code block**.
    """

    # 插入输出使用的 prompt
    INSERT_PRINT = """
    Please add debugging print statements to the following Java function:
    ```java
    {buggy_function}
    ```
    The following information helps you add the debugging print statements:
        1) Failing Test Context:
        ```java
        {test_context}
        ```
        2) Filtered error log:
        ```
        {error_info}
        ```
    """

    AUGMENT_PROMPT = """
    The following Java function contains a bug:
    ```java
    {buggy_function}
    ```

    Buggy lines are marked with '// Buggy Line' as hints. The actual fix may involve changes around these lines or adding new statements if necessary. 

    The original code fails on the following test(s):
    {error_info}

    It can be fixed by this patch function (Reference Solution):
    ```java
    {plausible_patch}
    ```

    Please analyze all the provided information and generate a **new, alternative and also correct fix** of the complete Java function. 
    Try to implement the fix differently if possible (e.g., different control flow, helper methods, or logic simplification), but ensure it remains functionally correct and passes the tests.

    Your response must enclose the entire function within a ```java ... ``` block.
    """

    REPAIR_SYS_MSG = "You are a helpful assistant that fixes Java code."

    AUGMENT_SYS_MSG = "You are an expert Java developer specializing in code refactoring and repair."

    INSERT_SYS_MSG = """
    You are a professional Java developer skilled in adding effective debugging print statements to code. Please add appropriate debugging print statements to the given Java function to help  repair bugs.

    Follow the following requirements:
    1. At the beginning of the function body, the following must be added: System.out.println("{start_marker}");
    2. Before the function is about to end, you must add: System.out.println("{end_marker}");
    3. Add print statements at key positions (after variable assignment, before and after conditional judgments, inside and outside loops, before and after function calls, etc.)
    4. Print statements should clearly display variable values, execution flow, or conditional results.
    5. Do not modify the logic, parameters, or return values of the original function.
    6. Keep the code format neat, and print statements should be properly indented with the surrounding code.
    7. Only return the complete modified function code without adding any explanations or extra content.
    8. Every debug print statement's content must start with "// DEBUG:", for example: System.out.println("// DEBUG: x = " + x);
    """
