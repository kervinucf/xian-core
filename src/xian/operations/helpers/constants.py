from pathlib import Path
import os 

base_path = Path(os.getcwd())

TENDERMINT_HOME = Path.home() / Path(f"{base_path}/src/xian")
TENDERMINT_CONFIG = TENDERMINT_HOME / Path("config/config.toml")
TENDERMINT_GENESIS = TENDERMINT_HOME / Path("genesis/genesis.json")

NONCE_FILENAME = '__n'
PENDING_NONCE_FILENAME = '__pn'
STORAGE_HOME = TENDERMINT_HOME / Path('xian/')
