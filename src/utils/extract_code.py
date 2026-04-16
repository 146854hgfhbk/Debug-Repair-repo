def extract_code_block(text: str) -> str:
    """
    优先从 text 中提取 ```java ... ``` 代码块（正则），
    若未找到则返回空字符串（调用方可继续尝试其他策略或直接使用原始文本）。
    """
    if not text:
        return ""
    # 优先匹配 ```java code block
    print("extracting code block from text")
    import re
    code_pattern = re.compile(r'```(?:java)?\s*\n(.*?)\n```', re.DOTALL | re.IGNORECASE)
    m = code_pattern.search(text)
    if m:
        code_block = m.group(1).strip()
        print(f"found code block\n{code_block}")
        return code_block
    return ""
