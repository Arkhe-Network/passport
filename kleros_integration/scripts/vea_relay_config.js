/**
 * Vea Relay Configuration Script
 *
 * Sets up configuration for the Vea relayer bridging Arbitrum to RedBelly Blockchain.
 */

const veaConfig = {
  // Source Chain
  arbitrum: {
    chainId: 42161,
    rpcUrl: "https://arb1.arbitrum.io/rpc",
    contracts: {
      veaSender: "0x0000000000000000000000000000000000000000" // Replace with real sender
    }
  },
  // Destination Chain
  redbelly: {
    chainId: 153, // Assuming Testnet ID
    rpcUrl: "https://governors.testnet.redbelly.network",
    contracts: {
      veaReceiver: "0x0000000000000000000000000000000000000000" // Replace with real receiver
    }
  },

  // Relayer config
  relayer: {
    address: process.env.VEA_RELAYER_ADDRESS || "0x0000000000000000000000000000000000000000",
    batchSize: 10,
    intervalMs: 60000
  }
};

export default veaConfig;
