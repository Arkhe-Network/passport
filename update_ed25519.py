import sys

filename = "node/passport_gateway.py"

with open(filename, "r") as f:
    content = f.read()

import1 = "import logging"
import2 = "import logging\nimport nacl.signing\nimport nacl.encoding"

content = content.replace(import1, import2)

anchor1 = """    async def _anchor_proof(self, proof: HumanityProof):
        \"\"\"Simula a ancoragem da prova na TemporalChain (923).\"\"\"
        # Em produção: POST para self.temporalchain_endpoint
        data = {
            "address": proof.address,
            "is_human": proof.is_human,
            "score": proof.score,
            "source": proof.source,
            "orcid_verified": proof.orcid_verified,
            "attestation_uid": proof.attestation_uid,
            "stamps": proof.stamps,
            "timestamp": proof.timestamp,
        }
        json_str = json.dumps(data, sort_keys=True)
        proof.seal = f"923-{hashlib.sha3_256(json_str.encode()).hexdigest()[:32]}"
        logger.debug(f"Proof ancorada: {proof.seal}")"""

anchor2 = """    async def _anchor_proof(self, proof: HumanityProof):
        \"\"\"Simula a ancoragem da prova na TemporalChain (923).\"\"\"
        # Em produção: POST para self.temporalchain_endpoint
        data = {
            "address": proof.address,
            "is_human": proof.is_human,
            "score": proof.score,
            "source": proof.source,
            "orcid_verified": proof.orcid_verified,
            "attestation_uid": proof.attestation_uid,
            "stamps": proof.stamps,
            "timestamp": proof.timestamp,
        }
        json_str = json.dumps(data, sort_keys=True)

        # Ed25519 Signing
        seed = os.environ.get("ARCHITECT_ED25519_SEED", "0" * 32).encode("utf-8")[:32].ljust(32, b'0')
        signing_key = nacl.signing.SigningKey(seed)
        signed = signing_key.sign(json_str.encode("utf-8"))
        signature_hex = signed.signature.hex()

        proof.seal = f"923-{hashlib.sha3_256(json_str.encode()).hexdigest()[:32]}-{signature_hex[:16]}"
        logger.debug(f"Proof ancorada e assinada com Ed25519: {proof.seal}")"""

content = content.replace(anchor1, anchor2)

with open(filename, "w") as f:
    f.write(content)
