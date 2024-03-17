from abci.server import ABCIServer
from abci.application import BaseApplication, OkCode, ErrorCode
# Tendermint
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
# Operations
from xian.operations.setup import SETUP_APPLICATION, INIT_APP_STATE

from xian.operations.query import QUERY_OPERATION
from xian.operations.info import GET_LATEST_INFO
from xian.operations.block_manager import CREATE_NEW_BLOCK, FINISH_BLOCK_FORMATION
from xian.operations.state_change import VALIDATE_STATE_CHANGE, PROCESS_STATE_CHANGE
from xian.operations.updater import UPDATE_APPLICATION_STATE

import gc
import logging
import os

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class Xian(BaseApplication):

    chain_id = None
    block_service_mode = False

    def __init__(self):
        try:
            SETUP_APPLICATION(self)
        except Exception as e:
            logger.error(e)
            raise SystemExit()

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

        INIT_APP_STATE(
            application=self,
            operation=req
        )

        return ResponseInitChain()

    def check_tx(self, req) -> ResponseCheckTx:
        """
        Validate the Tx before entry into the mempool
        Checks the state_paths are submitted in order 1,2,3...
        If not an order, a non-zero code is returned and the state_path
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
        for each state_change as proposed_state_change:
        deliver_tx(proposed_state_change)
        end_block()
        commit()
        """

        CREATE_NEW_BLOCK(
            application=self,
            operation=req,
        )

        return ResponseBeginBlock()

    def deliver_tx(self, req) -> ResponseDeliverTx:
        """
        Process each state_path from the block & add to cached state.
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
        of the current state of the application. This is usually the root hash
        of a merkletree.  The returned data is used as part of the consensus process.

        Save all cached state from the block to filesystem DB
        """

        # a hash of the previous block's app_hash + each of the state_path hashes from this block.

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
