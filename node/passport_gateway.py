#!/usr/bin/env python3
# node/passport_gateway.py — Substrato 989.x (Pacote Real)

"""
Passport Gateway — Substrato 989.x
Verifica humanidade via:
- Sign Protocol + EAS na Base (fonte primária)
- Gitcoin Passport (scorer/stamps)
- ORCID (identidade acadêmica)
Ancora cada prova na TemporalChain (923) com assinatura do Arquiteto.
Arquiteto ORCID: 0009-0005-2697-4668
Repositório: https://github.com/Arkhe-Network/passport
"""

import asyncio
import hashlib
import json
import os
import logging
import nacl.signing
import nacl.encoding
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import time

import aiohttp

# -----------------------------------------------------------------------------
# Configuração
# -----------------------------------------------------------------------------
logger = logging.getLogger("passport_gateway")

PASSPORT_API_KEY = os.environ.get("PASSPORT_API_KEY", "demo-key")
PASSPORT_SCORER_ID = os.environ.get("PASSPORT_SCORER_ID", "1")
SIGN_PROTOCOL_API_URL = os.environ.get("SIGN_PROTOCOL_API_URL", "https://api.sign.global")
BASE_RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
EAS_CONTRACT_ADDRESS = os.environ.get("EAS_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000")
IS_HUMAN_SCHEMA_UID = os.environ.get("IS_HUMAN_SCHEMA_UID", "0x0000000000000000000000000000000000000000000000000000000000000000")
ORCID_CLIENT_ID = os.environ.get("ORCID_CLIENT_ID", "APP-XXXXXXXX")
ORCID_CLIENT_SECRET = os.environ.get("ORCID_CLIENT_SECRET", "secret")

# -----------------------------------------------------------------------------
# Modelos de Dados
# -----------------------------------------------------------------------------
@dataclass
class HumanityProof:
    address: str
    is_human: bool
    score: float                     # 0-1
    source: str                      # "sign_protocol", "gitcoin", "orcid", "none"
    stamps: List[str] = field(default_factory=list)
    orcid_verified: bool = False
    attestation_uid: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    seal: Optional[str] = None       # Selo SHA3-256 ancorado na TemporalChain

# -----------------------------------------------------------------------------
# Gateway Principal
# -----------------------------------------------------------------------------
class PassportGateway:
    """
    Passport Gateway multi-fonte.
    Prioridade: Sign Protocol > Gitcoin Passport > ORCID.
    Todas as provas são ancoradas na TemporalChain (simulação interna, mas a
    arquitetura prevê chamada ao endpoint 923 via API Gateway).
    """

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.temporalchain_endpoint = os.environ.get(
            "TEMPORALCHAIN_ENDPOINT", "https://api.arkhe-catedral.org/v1/anchor"
        )
        # Cache distribuído simulado (TTL 300s)
        self.cache = {}
        self.cache_ttl = 300

    # -----------------------------------------------------------------
    # Ciclo de vida
    # -----------------------------------------------------------------
    async def start(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={"X-API-Key": PASSPORT_API_KEY}
            )
        logger.info("[PASSPORT] Gateway iniciado (Sign + Gitcoin + ORCID)")

    async def stop(self):
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("[PASSPORT] Gateway encerrado.")

    # -----------------------------------------------------------------
    # 1. Sign Protocol / EAS
    # -----------------------------------------------------------------
    async def check_sign_protocol_attestation(self, address: str) -> Optional[dict]:
        """Consulta o Sign Protocol por uma attestation 'isHuman'."""
        if not self.session:
            raise RuntimeError("Gateway não iniciado.")
        url = f"{SIGN_PROTOCOL_API_URL}/v1/attestations"
        params = {
            "schemaId": IS_HUMAN_SCHEMA_UID,
            "recipient": address,
        }
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    attestations = data.get("attestations", [])
                    if attestations:
                        latest = attestations[0]
                        return {
                            "uid": latest.get("uid"),
                            "is_human": latest.get("data", {}).get("isHuman", False),
                            "timestamp": latest.get("timestamp"),
                        }
                else:
                    logger.warning(f"Sign Protocol retornou {resp.status}")
        except Exception as e:
            logger.error(f"Erro ao consultar Sign Protocol: {e}")
        return None

    # -----------------------------------------------------------------
    # 2. Gitcoin Passport
    # -----------------------------------------------------------------
    async def get_passport_score(self, address: str) -> dict:
        """Obtém o score de humanidade do Gitcoin Passport."""
        if not self.session:
            raise RuntimeError("Gateway não iniciado.")
        url = f"https://api.scorer.gitcoin.co/registry/score/{PASSPORT_SCORER_ID}/{address}"
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"Gitcoin Scorer retornou {resp.status}")
                    return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            logger.error(f"Erro ao consultar Gitcoin Scorer: {e}")
            return {"error": str(e)}

    async def get_passport_stamps(self, address: str) -> List[dict]:
        """Retorna os stamps verificados de um endereço."""
        if not self.session:
            raise RuntimeError("Gateway não iniciado.")
        url = f"https://api.scorer.gitcoin.co/registry/stamps/{address}"
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("items", [])
                else:
                    logger.warning(f"Gitcoin Stamps retornou {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"Erro ao consultar Gitcoin Stamps: {e}")
            return []

    # -----------------------------------------------------------------
    # 3. ORCID (simulação; em produção integra com 982)
    # -----------------------------------------------------------------
    async def _verify_orcid_link(self, address: str) -> bool:
        """
        Verifica se o endereço possui um ORCID vinculado.
        Nesta implementação, endereços que iniciam com '0xAlice' ou '0xArchitect'
        são considerados verificados. Em produção, consultará o substrato 982.
        """
        if address.startswith("0xAlice") or address.startswith("0xArchitect"):
            return True
        return False

    # -----------------------------------------------------------------
    # 4. Verificação Unificada
    # -----------------------------------------------------------------
    async def is_human(self, address: str) -> HumanityProof:
        """Determina se um endereço é humano com base nas fontes configuradas."""
        # Check cache
        cached = self.cache.get(address)
        if cached:
            proof, timestamp = cached
            if time.time() - timestamp < self.cache_ttl:
                return proof

        proof = await self._is_human_internal(address)
        self.cache[address] = (proof, time.time())
        return proof

    async def _is_human_internal(self, address: str) -> HumanityProof:
        # 1. Sign Protocol
        sign_att = await self.check_sign_protocol_attestation(address)
        if sign_att and sign_att.get("is_human"):
            proof = HumanityProof(
                address=address,
                is_human=True,
                score=1.0,
                source="sign_protocol",
                attestation_uid=sign_att.get("uid"),
            )
            await self._anchor_proof(proof)
            return proof

        # 2. Gitcoin Passport
        score_data = await self.get_passport_score(address)
        stamps_data = await self.get_passport_stamps(address)
        if "error" not in score_data:
            raw_score = float(score_data.get("score", 0))
            normalized = min(raw_score / 20.0, 1.0)
            if normalized >= 0.75:
                stamp_names = [
                    s.get("credential", {}).get("credentialSubject", {}).get("provider", "")
                    for s in stamps_data if s.get("credential")
                ]
                proof = HumanityProof(
                    address=address,
                    is_human=True,
                    score=normalized,
                    source="gitcoin",
                    stamps=stamp_names,
                )
                await self._anchor_proof(proof)
                return proof

        # 3. ORCID
        orcid_ok = await self._verify_orcid_link(address)
        if orcid_ok:
            proof = HumanityProof(
                address=address,
                is_human=True,
                score=0.8,
                source="orcid",
                orcid_verified=True,
            )
            await self._anchor_proof(proof)
            return proof

        # Nenhuma fonte confirmou humanidade
        proof = HumanityProof(
            address=address,
            is_human=False,
            score=0.0,
            source="none",
        )
        await self._anchor_proof(proof)
        return proof

    # -----------------------------------------------------------------
    # 5. Ancoragem na TemporalChain
    # -----------------------------------------------------------------
    async def _anchor_proof(self, proof: HumanityProof):
        """Simula a ancoragem da prova na TemporalChain (923)."""
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
        logger.debug(f"Proof ancorada e assinada com Ed25519: {proof.seal}")

    # -----------------------------------------------------------------
    # 6. Integrações com DAO e Malha
    # -----------------------------------------------------------------
    async def verify_dao_voter(self, address: str) -> bool:
        """Um endereço pode votar na DAO se for humano."""
        proof = await self.is_human(address)
        return proof.is_human

    async def verify_node_access(self, address: str) -> bool:
        """Um endereço pode operar um nó se for humano e possuir Proof of Clean Hands (957)."""
        proof = await self.is_human(address)
        if not proof.is_human:
            return False

        # Proof of Clean Hands (sanctions/PEP) for AGI-Telcom
        return "CleanHands" in proof.stamps
