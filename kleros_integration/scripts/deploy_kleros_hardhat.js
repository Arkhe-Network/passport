import hre from "hardhat";

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const veaRelayerAddress = process.env.VEA_RELAYER_ADDRESS || deployer.address;

  console.log("Deploying contracts with the account:", deployer.address);

  // Deploy Oracle
  const Oracle = await hre.ethers.getContractFactory("PNKTheosisOracle");
  const oracle = await Oracle.deploy();
  await oracle.waitForDeployment();
  console.log("PNKTheosisOracle deployed to:", await oracle.getAddress());

  // Deploy Bridge
  const Bridge = await hre.ethers.getContractFactory("CathedralKlerosBridge");
  const bridge = await Bridge.deploy(veaRelayerAddress);
  await bridge.waitForDeployment();
  console.log("CathedralKlerosBridge deployed to:", await bridge.getAddress());

  // Deploy BridgeWithVoting
  const BridgeVoting = await hre.ethers.getContractFactory("CathedralKlerosBridgeWithVoting");
  const bridgeVoting = await BridgeVoting.deploy(veaRelayerAddress, await oracle.getAddress());
  await bridgeVoting.waitForDeployment();
  console.log("CathedralKlerosBridgeWithVoting deployed to:", await bridgeVoting.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
