import { expect } from "chai";
import hre from "hardhat";

describe("CathedralKlerosBridgeWithVoting", function () {
  let bridgeVoting;
  let oracle;
  let relayer;
  let owner;
  let juror;

  beforeEach(async function () {
    [owner, relayer, juror] = await hre.ethers.getSigners();

    const Oracle = await hre.ethers.getContractFactory("PNKTheosisOracle");
    oracle = await Oracle.deploy();
    await oracle.waitForDeployment();

    const BridgeVoting = await hre.ethers.getContractFactory("CathedralKlerosBridgeWithVoting");
    bridgeVoting = await BridgeVoting.deploy(relayer.address, await oracle.getAddress());
    await bridgeVoting.waitForDeployment();
  });

  it("Should calculate base voting weight for 0 theosis", async function () {
    const weight = await bridgeVoting.getVotingWeight(juror.address);
    expect(weight).to.equal(1000); // base weight
  });

  it("Should calculate boosted voting weight based on theosis", async function () {
    const theosisScore = 500;
    await oracle.connect(owner).updateTheosis(juror.address, theosisScore);

    const weight = await bridgeVoting.getVotingWeight(juror.address);
    expect(weight).to.equal(1500); // 1000 base + 500 score
  });
});
