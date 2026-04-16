from config import BasicConfig
from defs.bug_info import BugInfo
from llm.llm_client import LLMClient
from llm.prompt_builder import PromptBuilder
from utils.build_bug_list import build_default_list, build_custom_list
from utils.output_logger import update_time_consumed

from typing import List, Optional
import time
import threading
import queue

def run(bug_list: Optional[List[int]] = None):
    llm_client = LLMClient()
    prompt_builder = PromptBuilder()

    if BasicConfig.MODE == "LLM_INSERT":
        print("模式: LLM_INSERT")
        try:
            from pipeline.llm_insert_test import pipeline
        except Exception as e:
            print(f"引用 llm_insert 失败, 失败原因: {e}")
    elif BasicConfig.MODE == "RULE_INSERT":
        print("模式: RULE_INSERT")
        try:
            from pipeline.rule_insert_test import pipeline
        except Exception as e:
            print(f"引用 rule_insert 失败, 失败原因: {e}")
    elif BasicConfig.MODE == "INSERT_PRINT":
        print("模式: INSERT_PRINT")
        try:
            from pipeline.insert_print import pipeline
        except Exception as e:
            print(f"引用 insert_print 失败, 失败原因: {e}")
    elif BasicConfig.MODE == "INFO_DEBUG":
        print("模式: INFO_DEBUG")
        try:
            from pipeline.info_debug import pipeline
        except Exception as e:
            print(f"引用 info_debug 失败, 失败原因: {e}")
    elif BasicConfig.MODE == "AB_RULE_INSERT":
        print("模式: AB_RULE_INSERT")
        try:
            from pipeline.ablation_rule_insert import pipeline
        except Exception as e:
            print(f"引用 ablation_rule_insert 失败, 失败原因: {e}")
    elif BasicConfig.MODE == "AB_LLM_INSERT":
        print("模式: AB_LLM_INSERT")
        try:
            from pipeline.ablation_llm_insert import pipeline
        except Exception as e:
            print(f"引用 ablation_llm_insert 失败, 失败原因: {e}")
    elif BasicConfig.MODE == "COLLECT_OUTPUT":
        print("模式: COLLECT_OUTPUT")
        try:
            from pipeline.collect_output import pipeline
        except Exception as e:
            print(f"引用 ablation_llm_insert 失败, 失败原因: {e}")
    else:
        return

    if bug_list is None:
        bug_ids = build_default_list()
    else:
        bug_ids = build_custom_list(bug_list)
    print(f"共{len(bug_ids)}个bug")
    print(bug_ids)

    # 多线程执行
    process_bugs_multithreaded(bug_ids, pipeline, llm_client, prompt_builder)

def process_single_bug(bug_id: int, pipeline_func, llm_client, prompt_builder):
    """处理单个bug的线程函数"""
    start_time = time.time()
    
    print(f"运行{bug_id}")
    bug_info = BugInfo(bug_id)
    pipeline_func(bug_id, bug_info, llm_client, prompt_builder)
    
    end_time = time.time()
    time_consumed = end_time - start_time
    print(f"运行{bug_id}耗时: {time_consumed}秒")
    update_time_consumed(bug_id, time_consumed)

def process_bugs_multithreaded(bug_ids: List[int], pipeline_func, llm_client, prompt_builder):
    """多线程处理bug列表"""
    max_threads = BasicConfig.THREAD_COUNT
    # 创建bug队列
    bug_queue = queue.Queue()
    for bug_id in bug_ids:
        bug_queue.put(bug_id)
    
    def worker():
        """工作线程函数"""
        while not bug_queue.empty():
            try:
                bug_id = bug_queue.get_nowait()
            except queue.Empty:
                break
                
            try:
                process_single_bug(bug_id, pipeline_func, llm_client, prompt_builder)
            finally:
                bug_queue.task_done()
    
    # 创建并启动线程
    threads = []
    for i in range(min(max_threads, len(bug_ids))):
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()