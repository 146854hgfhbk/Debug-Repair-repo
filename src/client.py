from runner import run
from config import ClientConfig

if __name__ == '__main__':
    if ClientConfig.DEFAULT:
        run()
    elif ClientConfig.RANGE:
        bug_list = [i for i in range(ClientConfig.RANGE_START, ClientConfig.RANGE_END + 1)]
        run(bug_list)
    elif ClientConfig.CUSTOM:
        run(ClientConfig.CUSTOM_LIST)

    print("------Done------")