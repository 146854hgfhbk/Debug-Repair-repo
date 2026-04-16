from config import LLMConfig
from llm.prompts import Prompts
import tiktoken

class PromptBuilder:
    """
    构建Prompt
    """
    def __init__(self):
        self.token_limit = LLMConfig.MAX_TOKEN
        self.tokenizer = None
        if tiktoken:
            try:
                self.tokenizer = tiktoken.get_encoding(LLMConfig.TOKEN_ENCODING_NAME)
            except Exception as e:
                print(f"无法初始化 tokenizer: {e}")


    def build_debug_repair_prompt(
        self,
        buggy_function: str,
        test_context: str,
        error_info: str,
        instrumented_function: str,
        runtime_output: str,
        feedback: str
    ):
        buggy_function, test_context, error_info, instrumented_function, runtime_output, feedback = self._limit_len_for_debug_repair(
            buggy_function,
            test_context,
            error_info,
            instrumented_function,
            runtime_output,
            feedback
        )

        prompt_text = Prompts.DEBUG_REPAIR.format(
            buggy_function=buggy_function,
            test_context=test_context,
            error_info=error_info,
            instrumented_function=instrumented_function,
            runtime_output=runtime_output,
            feedback=feedback
        )

        sys_msg = Prompts.REPAIR_SYS_MSG

        prompt_text = self._limit_len(
            self.token_limit - self._count_token(sys_msg) - 10,
            prompt_text
        )

        return [
            {"role" : "system", "content" : sys_msg},
            {"role" : "user", "content" : prompt_text}
        ]


    def build_insert_print_prompt(
        self,
        buggy_function: str,
        test_context: str,
        error_info: str,
        start_marker: str,
        end_marker: str
    ):
        prompt_text = Prompts.INSERT_PRINT.format(
            buggy_function=buggy_function,
            test_context=test_context,
            error_info=error_info,
        )

        sys_msg = Prompts.INSERT_SYS_MSG.format(
            start_marker=start_marker,
            end_marker=end_marker
        )

        prompt_text = self._limit_len(
            self.token_limit - self._count_token(sys_msg) - 10,
            prompt_text
        )

        return [
            {"role" : "system", "content" : sys_msg},
            {"role" : "user", "content" : prompt_text}
        ]
    
    def build_direct_repair_prompt(
        self,
        buggy_function: str,
        test_context: str,
        error_info: str
    ):
        prompt_text = Prompts.DIRECT_REPAIR.format(
            buggy_function=buggy_function,
            test_context=test_context,
            error_info=error_info
        )

        sys_msg = Prompts.REPAIR_SYS_MSG

        prompt_text = self._limit_len(
            self.token_limit - self._count_token(sys_msg) - 10,
            prompt_text
        )

        return [
            {"role" : "system", "content" : sys_msg},
            {"role" : "user", "content" : prompt_text}
        ]

    def build_feedback(
        self,
        validator_feedback: str,
        previous_patch: str
    ):
        return Prompts.FEEDBACK.format(
            validator_feedback = validator_feedback,
            previous_patch = previous_patch
        )
    
    def build_augment_prompt(
        self,
        buggy_function: str,
        error_log: str,
        plausible_patch: str
    ):
        prompt_text = Prompts.AUGMENT_PROMPT.format(
            buggy_function=buggy_function,
            error_info=error_log,
            plausible_patch=plausible_patch
        )

        sys_msg = Prompts.AUGMENT_SYS_MSG

        prompt_text = self._limit_len(
            self.token_limit - self._count_token(sys_msg) - 10,
            prompt_text
        )

        return [
            {"role" : "system", "content" : sys_msg},
            {"role" : "user", "content" : prompt_text}
        ]
    
    def _count_token(self, text: str):
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            print("未初始化 tokenizer")
            return len(text)


    def _limit_len(self, length: int, text: str):

        failure_msg_flag = True
        failure_line_flag = True
        while self._count_token(text) > length:
            lines = text.splitlines()
            # 1. 删除错误信息
            if failure_msg_flag:
                lines = [line for line in lines if not line.startswith("[Failure message]")]
                text = "\n".join(lines)
                failure_msg_flag = False
                continue

            # 2. 删除错误行
            if failure_line_flag:
                lines = [line for line in lines if not line.startswith("[Failure line]")]
                text = "\n".join(lines)
                failure_line_flag = False
                continue

            # 3. 逐行删除
            if(len(lines)<=5):
                print("Prompt 已不足 5 行, 停止缩减")
                break
            lines.pop()
            text = "\n".join(lines)

        return text
    
    # 此为debug repair专属缩减token的逻辑，目前还没有重构优化，如果未来考虑更改逻辑请重构
    def _limit_len_for_debug_repair(
            self,
            buggy_method: str,
            current_test_context: str,
            current_error_log: str,
            current_instrumented: str,
            runtime_output: str,
            feedback: str
        ):

        method_length = self._count_token(buggy_method)
        test_length = self._count_token(current_test_context)
        log_length = self._count_token(current_error_log)
        instr_length = self._count_token(current_instrumented)
        runtime_output_length = self._count_token(runtime_output)
        feedback_length = self._count_token(feedback)


        while method_length + test_length + log_length + instr_length + runtime_output_length + feedback_length > LLMConfig.MAX_TOKEN-200:

            method_length = self._count_token(buggy_method)
            test_length = self._count_token(current_test_context)
            log_length = self._count_token(current_error_log)
            instr_length = self._count_token(current_instrumented)
            runtime_output_length = self._count_token(runtime_output)
            feedback_length = self._count_token(feedback)

            #否则完整删除runtime_output
            if runtime_output != "/* runtime debug output removed due to length */":
                print("  -> Prompt 仍然过长，移除 runtime debug output ...")
                runtime_output = "/* runtime debug output removed due to length */"
                continue

            #删除源代码
            if buggy_method != "/* buggy function removed due to length */":
                print("  -> Prompt 仍然过长，移除 buggy_function ...")
                buggy_method = "/* buggy function removed due to length */"
                continue

            #按规则删除日志
            if current_error_log != "/* error_log removed due to length */":
                print("  -> Prompt 仍然过长，缩减 error_log ...")
                #删除错误信息
                log_lines = current_error_log.splitlines()
                flag1=True
                for line in log_lines:
                    if line.startswith("[Failure message]"):
                        flag1=False
                        break
                if not flag1:
                    log_lines = [line for line in log_lines if not line.startswith("[Failure message]")]
                    current_error_log = "\n".join(log_lines)
                    print("  -> 删除了所有错误信息 ...")
                    continue

                #删除错误行信息
                for line in log_lines:
                    if line.startswith("[Failure line]"):
                        flag1=False
                        break
                if not flag1:
                    log_lines = [line for line in log_lines if not line.startswith("[Failure line]")]
                    current_error_log = "\n".join(log_lines)
                    print("  -> 删除了所有错误行信息 ...")
                    continue

                #删除日志
                print("  -> 删除所有 error_log ...")
                current_error_log = "/* error_log removed due to length */"
                continue

            #删除测试函数
            if current_test_context != "/* test_context reduced due to length */":
                print("  -> Prompt 仍然过长，缩减 test_context ...")
                current_test_context = "/* test_context reduced due to length */"
                continue
            
            print(f"  -> Prompt exceeded context window even after all reduction attempts.")
            prompt_still_too_long = True
            break

        return buggy_method, current_test_context, current_error_log, current_instrumented, runtime_output, feedback