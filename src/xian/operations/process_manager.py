from xian.operations.helpers.rewards import (
    distribute_rewards,
    distribute_static_rewards,)

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

def CREATE_NEW_BLOCK(application, operation):
     """
     Called during the consensus process.

     You can use this to do ``something`` for each new block.
     The overall flow of the calls are:
     begin_block()
     for each tx:
     deliver_tx(tx)
     end_block()
     commit()
     """

     nanos = get_nanotime_from_block_time(operation.header.time)
     hash = convert_binary_to_hex(operation.hash)
     height = operation.header.height

     application.current_block_meta = {
         "nanos": nanos,
         "height": height,
         "hash": hash,
     }

     application.fingerprint_hashes.append(hash)

def FINISH_BLOCK_FORMATION(application, operation):
        """
        Called at the end of processing the current block. If this is a stateful application
        you can use the height from the request to record the last_block_height
        """
        # test
        rewards = []

        if application.static_rewards:
            try:
                reward_write = distribute_static_rewards(
                    driver=application.driver,
                    foundation_reward=application.static_rewards_amount_foundation,
                    master_reward=application.static_rewards_amount_validators,
                )
                rewards.append(reward_write)
            except Exception as e:
                print(f"REWARD ERROR: {e}, No reward distributed for this block")

        if application.current_block_rewards:
            for tx_hash, reward in application.current_block_rewards.items():
                try:
                    reward_write = distribute_rewards(
                        stamp_rewards_amount=reward["amount"],
                        stamp_rewards_contract=reward["contract"],
                        driver=application.driver,
                        client=application.client,
                    )
                    rewards.append(reward_write)
                except Exception as e:
                    print(f"REWARD ERROR: {e}, No reward distributed for {tx_hash}")

        application.fingerprint_hashes.append(hash_from_rewards(rewards))
