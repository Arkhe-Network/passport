import { expect } from "chai";
import hre from "hardhat";

describe("CathedralKlerosBridge", function () {
  let bridge;
  let relayer;
  let otherAccount;

  beforeEach(async function () {
    [relayer, otherAccount] = await hre.ethers.getSigners();
    const Bridge = await hre.ethers.getContractFactory("CathedralKlerosBridge");
    bridge = await Bridge.deploy(relayer.address);
    await bridge.waitForDeployment();
  });

  it("Should set the right relayer", async function () {
    expect(await bridge.veaRelayer()).to.equal(relayer.address);
  });

  it("Should allow relayer to receive message", async function () {
    const data = hre.ethers.toUtf8Bytes("hello bridge");
    await expect(bridge.connect(relayer).receiveMessage(data))
      .to.emit(bridge, "BridgeMessageReceived")
      .withArgs(relayer.address, data);
  });

  it("Should not allow others to receive message", async function () {
    const data = hre.ethers.toUtf8Bytes("hello bridge");
    await expect(
      bridge.connect(otherAccount).receiveMessage(data)
    ).to.be.revertedWith("Not relayer");
  });
});
