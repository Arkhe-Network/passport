import os
import json
from web3 import Web3
from web3.middleware import geth_poa_middleware

# Arbitrum settings
ARBITRUM_RPC_URL = os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc")
# RedBelly Blockchain (RBB) settings
RBB_RPC_URL = os.getenv("RBB_RPC_URL", "https://governors.testnet.redbelly.network")

PRIVATE_KEY = os.getenv("PRIVATE_KEY", "0x0000000000000000000000000000000000000000000000000000000000000000")
VEA_RELAYER_ADDRESS = os.getenv("VEA_RELAYER_ADDRESS", "0x0000000000000000000000000000000000000000")

def load_abi_bytecode(contract_name):
    # This assumes hardhat compile has been run
    path = f"./artifacts/contracts/{contract_name}.sol/{contract_name}.json"
    with open(path, 'r') as f:
        data = json.load(f)
    return data['abi'], data['bytecode']

def deploy_contract(w3, contract_name, abi, bytecode, constructor_args, account):
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    transaction = Contract.constructor(*constructor_args).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 3000000,
        'gasPrice': w3.eth.gas_price
    })

    signed_txn = w3.eth.account.sign_transaction(transaction, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

    print(f"[{contract_name}] Deploying... Tx Hash: {w3.to_hex(tx_hash)}")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    contract_address = tx_receipt.contractAddress
    print(f"[{contract_name}] Deployed at: {contract_address}")
    return contract_address

def main():
    if PRIVATE_KEY == "0x0000000000000000000000000000000000000000000000000000000000000000":
        print("Warning: Using dummy private key.")

    # Deploy on Arbitrum
    w3_arb = Web3(Web3.HTTPProvider(ARBITRUM_RPC_URL))
    # Arbitrum is PoA
    w3_arb.middleware_onion.inject(geth_poa_middleware, layer=0)

    account_arb = w3_arb.eth.account.from_key(PRIVATE_KEY)

    print("=== Deploying to Arbitrum ===")
    abi_oracle, bytecode_oracle = load_abi_bytecode("PNKTheosisOracle")
    oracle_address_arb = deploy_contract(w3_arb, "PNKTheosisOracle", abi_oracle, bytecode_oracle, [], account_arb)

    abi_bridge, bytecode_bridge = load_abi_bytecode("CathedralKlerosBridgeWithVoting")
    bridge_address_arb = deploy_contract(w3_arb, "CathedralKlerosBridgeWithVoting", abi_bridge, bytecode_bridge, [VEA_RELAYER_ADDRESS, oracle_address_arb], account_arb)


    # Deploy on RBB
    w3_rbb = Web3(Web3.HTTPProvider(RBB_RPC_URL))
    w3_rbb.middleware_onion.inject(geth_poa_middleware, layer=0)

    account_rbb = w3_rbb.eth.account.from_key(PRIVATE_KEY)

    print("\n=== Deploying to RBB ===")
    oracle_address_rbb = deploy_contract(w3_rbb, "PNKTheosisOracle", abi_oracle, bytecode_oracle, [], account_rbb)
    bridge_address_rbb = deploy_contract(w3_rbb, "CathedralKlerosBridgeWithVoting", abi_bridge, bytecode_bridge, [VEA_RELAYER_ADDRESS, oracle_address_rbb], account_rbb)

    print("\nDeployment Complete!")

if __name__ == "__main__":
    main()
