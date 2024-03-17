import asyncio
import json
import time
import gc
import logging
import os

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from tendermint.abci.types_pb2 import (
    ResponseInfo,
    ResponseInitChain,
    ResponseCheckTx,
    ResponseDeliverTx,
    ResponseQuery,
    ResponseCommit,
    RequestBeginBlock,
    ResponseBeginBlock,
    RequestEndBlock,
    ResponseEndBlock,
    ResponseCommit,
)

from xian.operations.setup import INIT_APP_STATE, SETUP_APPLICATION
from xian.operations.info import GET_LATEST_INFO
from xian.operations.state_change import VALIDATE_STATE_CHANGE, PROCESS_STATE_CHANGE
from xian.operations.block_manager import CREATE_NEW_BLOCK, FINISH_BLOCK_FORMATION
from xian.operations.updater import UPDATE_APPLICATION_STATE
from xian.operations.query import QUERY_OPERATION



from xian.operations.helpers.validators import ValidatorHandler

from abci.server import ABCIServer
from abci.application import BaseApplication, OkCode, ErrorCode

from xian.operations.helpers.utils import (
    load_tendermint_config,
    load_genesis_data,
)

from xian.operations.helpers.storage import NonceStorage
from contracting.client import ContractingClient
from contracting.db.driver import (
    ContractDriver,
)
from contracting.stdlib.bridge.decimal import ContractingDecimal
from contracting.compilation import parser
from xian.operations.helpers.node_base import Node

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class Xian(BaseApplication):

    def __init__(self):
        try:
            self.config = load_tendermint_config()
            self.genesis = load_genesis_data()
        except Exception as e:
            logger.error(e)
            raise SystemExit()



        self.client = ContractingClient()
        self.driver = ContractDriver()
        self.nonce_storage = NonceStorage()
        self.xian = Node(self.client, self.driver, self.nonce_storage)
        self.validator_handler = ValidatorHandler(self)
        self.current_block_meta: dict = None
        self.fingerprint_hashes = []
        self.chain_id = self.config.get("chain_id", None)
        self.block_service_mode = self.config.get("block_service_mode", True)

        if self.chain_id is None:
            raise ValueError("No value set for 'chain_id' in Tendermint config")

        if self.genesis.get("chain_id") != self.chain_id:
            raise ValueError("Value of 'chain_id' in config.toml does not match value in Tendermint genesis.json")

        if self.genesis.get("abci_genesis", None) is None:
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
        self.tx_count = 0
        self.start_time = time.time()

        self.enable_tx_fee = True
        self.static_rewards = False
        self.static_rewards_amount_foundation = 1
        self.static_rewards_amount_validators = 1

        self.current_block_rewards = {}
            

    def info(self, req) -> ResponseInfo:
        """
        Called every time the application starts
        """

        r = ResponseInfo()
        r.version = req.version
        app_state_info = GET_LATEST_INFO(application=self)

        r.last_block_height = app_state_info["latest_event_height"]
        r.last_block_app_hash = app_state_info["latest_event_hash"]
        logger.debug(f"LAST_BLOCK_HEIGHT = {r.last_block_height}")
        logger.debug(f"LAST_BLOCK_HASH = {r.last_block_app_hash}")
        logger.debug(f"CHAIN_ID = {self.chain_id}")
        logger.debug(f"BLOCK_SERVICE_MODE = {self.block_service_mode}")
        logger.debug(f"BOOTED")
        return r

    def init_chain(self, req) -> ResponseInitChain:
        """Called the first time the application starts; when block_height is 0"""

        INIT_APP_STATE(application=self, operation=req)
        return ResponseInitChain()

    def check_tx(self, raw_tx) -> ResponseCheckTx:
        """
        Validate the Tx before entry into the mempool
        Checks the txs are submitted in order 1,2,3...
        If not an order, a non-zero code is returned and the tx
        will be dropped.
        """
        try:

            state_change_flags = VALIDATE_STATE_CHANGE(application=self, operation=req)

            if state_change_flags != "OK":
                return ResponseCheckTx(code=ErrorCode, info=state_change_flags)

            return ResponseCheckTx(code=OkCode)

        except Exception as e:
            logger.error(e)
            return ResponseCheckTx(code=ErrorCode, info=f"ERROR: {e}")

    def begin_block(self, req: RequestBeginBlock) -> ResponseBeginBlock:
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

        CREATE_NEW_BLOCK(
            application=self,
            operation=req,
        )

        return ResponseBeginBlock()

    def deliver_tx(self, tx_raw) -> ResponseDeliverTx:
        """
        Process each tx from the block & add to cached state.
        """
        try:
            result, encoded_parsed_state_path_result = PROCESS_STATE_CHANGE(
                application=self,
                operation=req
            )
            logger.debug(f"parsed state_path result : {encoded_parsed_state_path_result}")
            return ResponseDeliverTx(
                code=result["state_path_result"]["status"],
                data=encoded_parsed_state_path_result,
                gas_used=result["stamp_rewards_amount"],
            )
        except Exception as err:
            logger.error(f"DELIVER TX ERROR: {err}")
            return ResponseDeliverTx(code=ErrorCode, info=f"ERROR: {err}")

    def end_block(self, req: RequestEndBlock) -> ResponseEndBlock:
        """
        Called at the end of processing the current block. If this is a stateful application
        you can use the height from the request to record the last_block_height
        """

        FINISH_BLOCK_FORMATION(
            application=self,
            operation=req,
        )

        return ResponseEndBlock(validator_updates=self.validator_handler.build_validator_updates())

    def commit(self) -> ResponseCommit:
        """
        Called after ``end_block``.  This should return a compact ``fingerprint``
        of the current state of the self. This is usually the root hash
        of a merkletree.  The returned data is used as part of the consensus process.

        Save all cached state from the block to filesystem DB
        """

        return ResponseCommit(
            data=UPDATE_APPLICATION_STATE(
                application=self,
                garbage_collector=gc
            ))

    # TODO: Probably best to use FastAPI here and add proper error handling
    def query(self, req) -> ResponseQuery:
        """
        Query the application state
        Request Ex. http://localhost:26657/abci_query?path="path"
        (Yes you need to quote the path)
        """

        try:
            value, type_of_data, encoded_key = QUERY_OPERATION(
                application=self,
                operation=req
            )

            return ResponseQuery(
                code=OkCode,
                value=value,
                info=type_of_data,
                key=encoded_key)

        except Exception as e:
            logger.error(f"QUERY ERROR: {e}")

            return ResponseQuery(code=ErrorCode, log=f"QUERY ERROR")


def main():
    app = ABCIServer(app=Xian())
    app.run()


if __name__ == "__main__":
    main()
