import os
import time
import json
from prometheus_client import start_http_server, Gauge
from web3 import Web3

# Configuration
RPC_URL = os.getenv("RPC_URL", "https://governors.testnet.redbelly.network")
ORACLE_ADDRESS = os.getenv("ORACLE_ADDRESS", "0x0000000000000000000000000000000000000000")
EXPORTER_PORT = int(os.getenv("EXPORTER_PORT", "8000"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "15"))

# Load ABI
def load_oracle_abi():
    # Attempt to load ABI. For fallback we use a minimal interface.
    try:
        path = "../artifacts/contracts/PNKTheosisOracle.sol/PNKTheosisOracle.json"
        with open(path, 'r') as f:
            data = json.load(f)
        return data['abi']
    except Exception as e:
        print(f"Using minimal ABI due to: {e}")
        return [{
            "inputs": [{"internalType": "address", "name": "juror", "type": "address"}],
            "name": "getJurorTheosis",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        }]

def main():
    print(f"Starting Prometheus Theosis Exporter on port {EXPORTER_PORT}...")
    start_http_server(EXPORTER_PORT)

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print("Failed to connect to Ethereum node.")
        return

    abi = load_oracle_abi()
    contract = w3.eth.contract(address=Web3.to_checksum_address(ORACLE_ADDRESS), abi=abi)

    # Prometheus Metric
    # In a real scenario, you'd iterate over known jurors or listen to events
    # We create a metric to track an aggregate or specific jurors
    juror_theosis_gauge = Gauge('kleros_juror_theosis_score', 'Theosis score of a juror', ['juror_address'])

    # Demo Jurors to track
    demo_jurors = [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222"
    ]

    while True:
        try:
            for juror in demo_jurors:
                score = contract.functions.getJurorTheosis(Web3.to_checksum_address(juror)).call()
                juror_theosis_gauge.labels(juror_address=juror).set(score)
            print("Metrics updated.")
        except Exception as e:
            print(f"Error fetching data: {e}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
