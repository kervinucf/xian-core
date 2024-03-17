from gc import garbage
from xian.operations.helpers.utils import (
    encode_str,
    decode_transaction_bytes,
    unpack_transaction,
    get_nanotime_from_block_time,
    convert_binary_to_hex,
    load_tendermint_config,
    stringify_decimals,
    load_genesis_data,
    hash_from_rewards,
    verify,
    hash_list
)

from xian.operations.helpers.driver_api import (
    get_latest_block_hash,
    set_latest_block_hash,
    get_latest_block_height,
    set_latest_block_height,
    get_value_of_key,
    get_keys,
)

def UPDATE_APPLICATION_STATE(application, garbage_collector):
        """
        Called after ``end_block``.  This should return a compact ``fingerprint``
        of the current state of the application. This is usually the root hash
        of a merkletree.  The returned data is used as part of the consensus process.

        Save all cached state from the block to filesystem DB
        """

        # a hash of the previous block's app_hash + each of the tx hashes from this block.
        fingerprint_hash = hash_list(application.fingerprint_hashes)

        # commit block to filesystem db
        set_latest_block_hash(fingerprint_hash, application.driver)
        set_latest_block_height(application.current_block_meta["height"], application.driver)

        application.driver.hard_apply(str(application.current_block_meta["nanos"]))

        # unset current_block_meta & cleanup
        application.current_block_meta = None
        application.fingerprint_hashes = []
        application.current_block_rewards = {}

        garbage_collector.collect()

        return fingerprint_hash
