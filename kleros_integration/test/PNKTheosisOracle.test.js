import { expect } from "chai";
import hre from "hardhat";

describe("PNKTheosisOracle", function () {
  let oracle;
  let owner;
  let juror;

  beforeEach(async function () {
    [owner, juror] = await hre.ethers.getSigners();
    const Oracle = await hre.ethers.getContractFactory("PNKTheosisOracle");
    oracle = await Oracle.deploy();
    await oracle.waitForDeployment();
  });

  it("Should set the right owner", async function () {
    expect(await oracle.owner()).to.equal(owner.address);
  });

  it("Should allow owner to update theosis score", async function () {
    const score = 42;
    await expect(oracle.connect(owner).updateTheosis(juror.address, score))
      .to.emit(oracle, "TheosisUpdated")
      .withArgs(juror.address, score);

    expect(await oracle.getJurorTheosis(juror.address)).to.equal(score);
  });

  it("Should not allow others to update theosis score", async function () {
    const score = 42;
    await expect(
      oracle.connect(juror).updateTheosis(juror.address, score)
    ).to.be.revertedWith("Not owner");
  });
});
