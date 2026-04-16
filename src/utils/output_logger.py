import json
import os
import threading
from config import BasicConfig, LLMConfig
from typing import Optional, List

_file_lock = threading.Lock()

def output_log(
    bug_id: str,
    type: str,
    first_msg: str,
    second_msg: str,
    usage_info: Optional[dict] = None,
    status: Optional[bool] = None,
    final_msg : Optional[str] = None
):
    with _file_lock:
        # 目前想法：type == insert print , first msg == instrumented_code, second_msg == runtime_output
        # type == direct_repair , first msg == patch, second_msg == validate msg
        data = _preprocess(bug_id)
        if type == "insert_print" or type == "ruled_insert_print" or type == "llm_insert_print":
            if usage_info is not None:
                data[bug_id]["pipeline"].append({   # 目前insert_print候选阶段不会收集输出, 所以第二消息没有用
                    "type" : type,
                    "instrumented_code" : first_msg,
                    "usage_info" : usage_info
                })
                print("insert_print with usage_info")
            else:
                data[bug_id]["pipeline"].append({
                    "type" : type,
                    "instrumented_code" : first_msg,
                    "runtime_output" : second_msg
                })
                print("insert_print without usage_info")
        elif type == "direct_repair" or type == "debug_repair":
            if usage_info is not None:
                data[bug_id]["pipeline"].append({
                    "type" : type,
                    "patch" : first_msg,
                    "validate_msg" : second_msg,
                    "usage_info" : usage_info
                })
            else:
                data[bug_id]["pipeline"].append({
                    "type" : type,
                    "patch" : first_msg,
                    "validate_msg" : second_msg
                })
        elif type == "patch_augment":
            if usage_info is not None:
                data[bug_id]["pipeline"].append({
                    "type" : type,
                    "patch" : first_msg,
                    "validate_msg" : second_msg,
                    "usage_info" : usage_info
                })
            else:
                data[bug_id]["pipeline"].append({
                    "type" : type,
                    "patch" : first_msg,
                    "validate_msg" : second_msg
                })
        
        if status is not None:
            data[bug_id]["status"] = ("success" if status else "fail")
        if final_msg is not None:
            data[bug_id]["message"] = final_msg

        _write_json(data)

def update_time_consumed(bug_id: str, time_consumed: float):
    with _file_lock:
        data = _preprocess(bug_id)
        data[bug_id]["time_consumed"] = time_consumed
        _write_json(data)

def update_status_and_final_msg(bug_id: str, status: bool, final_msg: str):
    with _file_lock:
        data = _preprocess(bug_id)
        data[bug_id]["status"] = ("success" if status else "fail")
        data[bug_id]["message"] = final_msg
        _write_json(data)

def update_plausible_patches(bug_id: str, plausible_patches: List[str]):
    with _file_lock:
        data = _preprocess(bug_id)
        data[bug_id]["plausible_patches"] = plausible_patches
        _write_json(data)

def _preprocess(bug_id: str):
    """预处理函数, 确保路径存在且文件格式正确, 并返回文件内容"""
    # 如果路径不存在就创建
    if not os.path.exists(os.path.join(
        BasicConfig.OUTPUT_PATH,
        BasicConfig.MODE,
        LLMConfig.LLM_MODEL
    )):
        os.makedirs(os.path.join(
            BasicConfig.OUTPUT_PATH,
            BasicConfig.MODE,
            LLMConfig.LLM_MODEL
        ))

    # 如果文件不存在就创建
    if not os.path.exists(os.path.join(
        BasicConfig.OUTPUT_PATH,
        BasicConfig.MODE,
        LLMConfig.LLM_MODEL,
        BasicConfig.OUTPUT_FILE_NAME + ".json"
    )):
        with open(os.path.join(
            BasicConfig.OUTPUT_PATH,
            BasicConfig.MODE,
            LLMConfig.LLM_MODEL,
            BasicConfig.OUTPUT_FILE_NAME + ".json"
        ),'w') as f:
            json.dump({}, f, indent=4)
    
    # 如果文件内没有 bug_id 的信息，就创建格式
    with open(os.path.join(
        BasicConfig.OUTPUT_PATH,
        BasicConfig.MODE,
        LLMConfig.LLM_MODEL,
        BasicConfig.OUTPUT_FILE_NAME + ".json"
    ),'r') as f:
        data = json.load(f)
    
    if bug_id not in data:
        print(f"{bug_id}尚未创建, 先创建空的框架")
        data[bug_id] = {
            "status" : "in-progress",
            "time_consumed" : 0,
            "pipeline" : [],
            "plausible_patches" : [],
            "message" : ""
        }
    return data

def _write_json(data: dict):
    """将数据写入json文件"""
    with open(os.path.join(
        BasicConfig.OUTPUT_PATH,
        BasicConfig.MODE,
        LLMConfig.LLM_MODEL,
        BasicConfig.OUTPUT_FILE_NAME + ".json"
    ),'w') as f:
        json.dump(data, f, indent=4)