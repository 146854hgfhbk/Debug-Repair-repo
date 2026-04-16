import json

from config import BasicConfig
from typing import List


def build_default_list():
    with open(BasicConfig.INDEX_MAP_JSON, "r") as f:
        index_map = json.load(f)

    default_list = []

    for key, value in index_map.items():
        default_list.append(value)

    return default_list


def build_custom_list(id_list):
    with open(BasicConfig.INDEX_MAP_JSON, "r") as f:
        index_map = json.load(f)

    custom_list = []

    for id in id_list:
        if str(id) in index_map:
            custom_list.append(index_map[str(id)])

    return custom_list