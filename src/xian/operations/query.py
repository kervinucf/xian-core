from xian.operations.helpers.driver_api import (
    get_value_of_key,
    get_keys,
)

from xian.operations.helpers.utils import (
    encode_str,
)

import json
from contracting.stdlib.bridge.decimal import ContractingDecimal
from contracting.compilation import parser


def QUERY_OPERATION(application, operation):
        """
        Query the application state
        Request Ex. http://localhost:26657/abci_query?path="path"
        (Yes you need to quote the path)
        """

        result = None
        type_of_data = "None"
        key = ""

        request_path = operation.path
        path_parts = [part for part in request_path.split("/") if part]

        # http://localhost:26657/abci_query?path="/get/currency.balances:c93dee52d7dc6cc43af44007c3b1dae5b730ccf18a9e6fb43521f8e4064561e6"
        if path_parts and path_parts[0] == "get":
            result = get_value_of_key(path_parts[1], application.driver)
            key = path_parts[1]

        # http://localhost:26657/abci_query?path="/keys/currency.balances" BLOCK SERVICE MODE ONLY
        if application.block_service_mode:
            if path_parts[0] == "keys":
                result = get_keys(application.driver, path_parts[1])

        # http://localhost:26657/abci_query?path="/health"
        if path_parts[0] == "health":
            result = "OK"

        # http://localhost:26657/abci_query?path="/get_next_nonce/ddd326fddb5d1677595311f298b744a4e9f415b577ac179a6afbf38483dc0791"
        if path_parts[0] == "get_next_nonce":
            result = application.nonce_storage.get_next_nonce(sender=path_parts[1])

        # http://localhost:26657/abci_query?path="/contract/con_some_contract"
        if path_parts[0] == "contract":
            application.client.raw_driver.clear_pending_state()
            result = application.client.raw_driver.get_contract(path_parts[1])

        # http://localhost:26657/abci_query?path="/contract_methods/con_some_contract"
        if path_parts[0] == "contract_methods":
            application.client.raw_driver.clear_pending_state()

            contract_code = application.client.raw_driver.get_contract(path_parts[1])
            if contract_code is not None:
                funcs = parser.methods_for_contract(contract_code)
                result = {"methods": funcs}

        # http://localhost:26657/abci_query?path="/contract_vars/con_some_contract"
        if path_parts[0] == "contract_vars":
            application.client.raw_driver.clear_pending_state()

            contract_code = application.client.raw_driver.get_contract(path_parts[1])
            if contract_code is not None:
                result = parser.variables_for_contract(contract_code)

        # http://localhost:26657/abci_query?path="/ping"
        if path_parts[0] == "ping":
            result = {'status': 'online'}

        if result:
            if isinstance(result, str):
                value = encode_str(result)
                type_of_data = "str"
            elif isinstance(result, int):
                value = encode_str(str(result))
                type_of_data = "int"
            elif isinstance(result, float) or isinstance(result, ContractingDecimal):
                value = encode_str(str(result))
                type_of_data = "decimal"
            elif isinstance(result, dict) or isinstance(result, list):
                value = encode_str(json.dumps(result))
                type_of_data = "str"
            else:
                value = encode_str(str(result))
                type_of_data = "str"
        else:
            # If no result, return a byte string representing None
            value = b"\x00"
            type_of_data = "None"

        return value, type_of_data, encode_str(key)
