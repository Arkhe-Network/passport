import { expect } from "chai";
import hre from "hardhat";
import fs from "fs";
import { execSync } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe("CathedralSPHINCSVerifier", function () {
    let verifier;

    before(async function () {
        this.timeout(120000);
        console.log("Generating mock SPHINCS+ signature...");
        execSync("python3 scripts/generate_sphincs_signature.py", { cwd: path.join(__dirname, "..") });

        const Verifier = await hre.ethers.getContractFactory("CathedralSPHINCSVerifier");
        verifier = await Verifier.deploy();
    });

    it("should successfully verify a valid signature", async function () {
        const dataPath = path.join(__dirname, "..", "scripts", "mock_sphincs_sig.json");
        const testData = JSON.parse(fs.readFileSync(dataPath, "utf8"));

        const message = testData.message;
        const signature = testData.signature;
        const publicKeyRoot = testData.publicKeyRoot;

        expect(signature.length).to.equal(3952 * 2 + 2);

        const gasEstimate = await verifier.verifySPHINCS.estimateGas(message, signature, publicKeyRoot);
        console.log(`Gas used for verifySPHINCS: ${gasEstimate.toString()}`);

        const result = await verifier.verifySPHINCS(message, signature, publicKeyRoot);
        expect(result).to.be.true;
    });

    it("should fail on invalid signature size", async function () {
        const message = "0x1234";
        const signature = "0x" + "00".repeat(3951); // 3951 bytes instead of 3952
        const publicKeyRoot = "0x" + "00".repeat(32);

        await expect(verifier.verifySPHINCS(message, signature, publicKeyRoot))
            .to.be.revertedWith("CathedralSPHINCSVerifier: invalid signature length");
    });

    it("should fail on invalid signature data (tampered public key root)", async function () {
        const dataPath = path.join(__dirname, "..", "scripts", "mock_sphincs_sig.json");
        const testData = JSON.parse(fs.readFileSync(dataPath, "utf8"));

        const message = testData.message;
        const signature = testData.signature;
        const publicKeyRoot = "0x" + "11".repeat(32); // Invalid PK

        const result = await verifier.verifySPHINCS(message, signature, publicKeyRoot);
        expect(result).to.be.false;
    });

    it("should fail on tampered message", async function () {
        const dataPath = path.join(__dirname, "..", "scripts", "mock_sphincs_sig.json");
        const testData = JSON.parse(fs.readFileSync(dataPath, "utf8"));

        const message = "0x" + "11".repeat(32); // Invalid message
        const signature = testData.signature;
        const publicKeyRoot = testData.publicKeyRoot;

        const result = await verifier.verifySPHINCS(message, signature, publicKeyRoot);
        expect(result).to.be.false;
    });
});
