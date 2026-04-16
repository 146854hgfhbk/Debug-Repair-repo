import threading
import functools

def timeout(seconds=120):
    """超时装饰器，超时抛出TimeoutError"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]
            completed = [False]  # 标记是否完成
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
                finally:
                    completed[0] = True
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=seconds)
            
            if not completed[0]:  # 如果线程还在运行
                print(f"[TIMEOUT] 函数 {func.__name__} 执行超时 ({seconds}秒)")
                raise TimeoutError(f"函数 {func.__name__} 执行超时 ({seconds}秒)")
            
            if exception[0]:
                raise exception[0]
            
            return result[0]
        return wrapper
    return decorator