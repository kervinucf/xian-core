import pytest
import asyncio
from xian.xian_abci import Xian 
from tendermint.abci.types_pb2 import (
    RequestInitChain, ConsensusParams, ValidatorUpdate, RequestBeginBlock, RequestCheckTx, RequestDeliverTx, RequestEndBlock, RequestQuery, RequestInfo)
from google.protobuf.timestamp_pb2 import Timestamp


@pytest.mark.asyncio
async def test_application_startup_and_transaction_processing():
    # Initialize the application
    app = Xian()

    # Simulate application startup
    req_info = RequestInfo(version='0.34.24')
    response_info = app.info(req_info)
    assert response_info is not None, "Info response should not be null"
    assert getattr(response_info, 'version', None) is not None, "Info response should contain version"
    assert getattr(response_info, 'last_block_height', None) is not None, "Info response should contain last_block_height"
    assert getattr(response_info, 'last_block_app_hash', None) is not None, "Info response should contain last_block_app_hash"

    # Simulate init chain
    req_init_chain = RequestInitChain(
        time=Timestamp(seconds=0, nanos=0),
        chain_id='test-chain',
        consensus_params=ConsensusParams(),
        validators=[ValidatorUpdate()]
    )
    response_init_chain = app.init_chain(req_init_chain)
    assert response_init_chain is not None, "Init chain response should not be null"

    # TODO: Prepare a transaction
    
    # TODO: Simulate begin block

    # TODO: Simulate check tx

    # TODO: Simulate deliver tx

    # TODO: Simulate end block

    # TODO: Simulate query balance

    # TODO: Simulate commit
    
    # TODO: Simulate query balance (should be up)
    
# Run the test
pytest.main(["-v", "test_application_startup_and_transaction_processing.py"])
