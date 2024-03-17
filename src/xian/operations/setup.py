from xian.operations.helpers.utils import (
    load_tendermint_config,
    load_genesis_data,
)

from contracting.client import ContractingClient
from contracting.db.driver import (
    ContractDriver,
)
from xian.operations.helpers.node_base import Node
from xian.operations.helpers.validators import ValidatorHandler
from xian.operations.helpers.storage import NonceStorage
import time
import asyncio

def INIT_APP_STATE(application, operation):
    """
    Called the first time the application starts; when block_height is 0
    """
    # call out to hypercore service to initialize core state
    abci_genesis_state = application.genesis["abci_genesis"]
    asyncio.ensure_future(application.xian.store_genesis_block(abci_genesis_state))


def SETUP_APPLICATION(application):
    application.config = load_tendermint_config()
    application.genesis = load_genesis_data()

    application.client = ContractingClient()
    application.driver = ContractDriver()
    application.nonce_storage = NonceStorage()
    application.xian = Node(application.client, application.driver, application.nonce_storage)
    application.validator_handler = ValidatorHandler(application)

    application.current_block_meta: dict = None
    application.fingerprint_hashes = []

    application.chain_id = application.config.get("chain_id", None)

    application.block_service_mode = application.config.get("block_service_mode", True)

    if application.chain_id is None:
        raise ValueError("No value set for 'chain_id' in Tendermint config")

    if application.genesis.get("chain_id") != application.chain_id:
        raise ValueError("Value of 'chain_id' in config.toml does not match value in Tendermint genesis.json")

    if application.genesis.get("abci_genesis", None) is None:
        raise ValueError("No value set for 'abci_genesis' in Tendermint genesis.json")

    # current_block_meta :
    # schema :
    # {
    #    nanos: int
    #    height: int
    #    hash: str
    # }
    # set in begin_block
    # used as environment for each tx in block
    # unset at end_block / commit

    # benchmark metrics
    application.tx_count = 0
    application.start_time = time.time()

    application.enable_tx_fee = True
    application.static_rewards = False
    application.static_rewards_amount_foundation = 1
    application.static_rewards_amount_validators = 1

    application.current_block_rewards = {}

    return application
