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

import json

def VALIDATE_STATE_CHANGE(application, operation):
        """
        Validate the Tx before entry into the mempool
        Checks the txs are submitted in order 1,2,3...
        If not an order, a non-zero code is returned and the tx
        will be dropped.
        """
        operands = decode_transaction_bytes(operation)

        application.xian.validate_transaction(operands)
        sender, signature, payload = unpack_transaction(operands)


        if not verify(vk=sender, msg=payload, signature=signature):
            return "Invalid Signature"

        payload = json.loads(payload)
        if payload.get("chain_id") != application.chain_id:
            return "Invalid Chain ID"

        return "OK"


def PROCESS_STATE_CHANGE(application, operation):
    """
    Process each tx from the block & add to cached state.
    """
    operands = decode_transaction_bytes(operation)

    # Attach metadata to the transaction
    operands["b_meta"] = application.current_block_meta

    result = application.xian.tx_processor.process_tx(operands, enabled_fees=application.enable_tx_fee)

    if application.enable_tx_fee:
        application.current_block_rewards[operands['b_meta']['hash']] = {
            "amount": result["stamp_rewards_amount"],
            "contract": result["stamp_rewards_contract"]
        }

    application.xian.set_nonce(operands)
    tx_hash = result["tx_result"]["hash"]
    application.fingerprint_hashes.append(tx_hash)
    parsed_tx_result = json.dumps(stringify_decimals(result["tx_result"]))
    return result, encode_str(parsed_tx_result)
