from xian.operations.helpers.driver_api import (
    get_latest_block_hash,
    set_latest_block_hash,
    get_latest_block_height,
    set_latest_block_height,
    get_value_of_key,
    get_keys,
)
import asyncio

def GET_LATEST_INFO(application):
    """
    Called the first time the application starts; when block_height is 0
    """
    return {
        "latest_event_hash": get_latest_block_hash(application.driver),
        "latest_event_height": get_latest_block_height(application.driver),
    }
