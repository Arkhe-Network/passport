# tests/test_passport_gateway.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from node.passport_gateway import PassportGateway, HumanityProof

# Mock data
SAMPLE_SIGN_ATTEST = {
    "uid": "0xattest123",
    "is_human": True,
    "timestamp": "2026-05-30T12:00:00Z"
}

SAMPLE_GITCOIN_SCORE = {"score": "25.5"}
SAMPLE_GITCOIN_STAMPS = {
    "items": [
        {"credential": {"credentialSubject": {"provider": "EncryptedMobile"}}},
        {"credential": {"credentialSubject": {"provider": "Google"}}}
    ]
}

@pytest.fixture
def gateway():
    return PassportGateway()

@pytest.mark.asyncio
async def test_sign_protocol_human(gateway):
    with patch.object(gateway, 'check_sign_protocol_attestation', return_value=SAMPLE_SIGN_ATTEST):
        proof = await gateway.is_human("0xTest")
        assert proof.is_human is True
        assert proof.score == 1.0
        assert proof.source == "sign_protocol"
        assert proof.attestation_uid == "0xattest123"

@pytest.mark.asyncio
async def test_gitcoin_fallback(gateway):
    # Sign protocol returns None, Gitcoin gives high score
    gateway.check_sign_protocol_attestation = AsyncMock(return_value=None)
    with patch.object(gateway, "get_passport_score", return_value=SAMPLE_GITCOIN_SCORE), patch.object(gateway, "get_passport_stamps", return_value=SAMPLE_GITCOIN_STAMPS.get("items")):
        proof = await gateway.is_human("0xTest")
        assert proof.is_human is True
        assert 0.7 <= proof.score <= 1.0
        assert proof.source == "gitcoin"
        assert "EncryptedMobile" in proof.stamps

@pytest.mark.asyncio
async def test_orcid_fallback(gateway):
    # Sign protocol returns None, Gitcoin returns low score, but ORCID linked
    gateway.check_sign_protocol_attestation = AsyncMock(return_value=None)
    gateway.get_passport_score = AsyncMock(return_value={"score": "10"})
    gateway.get_passport_stamps = AsyncMock(return_value=[])
    with patch.object(gateway, '_verify_orcid_link', return_value=True):
        proof = await gateway.is_human("0xAlice...")
        assert proof.is_human is True
        assert proof.source == "orcid"
        assert proof.orcid_verified is True

@pytest.mark.asyncio
async def test_not_human(gateway):
    gateway.check_sign_protocol_attestation = AsyncMock(return_value=None)
    gateway.get_passport_score = AsyncMock(return_value={"score": "5"})
    gateway.get_passport_stamps = AsyncMock(return_value=[])
    with patch.object(gateway, '_verify_orcid_link', return_value=False):
        proof = await gateway.is_human("0xRandom")
        assert proof.is_human is False
        assert proof.score == 0.0
        assert proof.source == "none"

@pytest.mark.asyncio
async def test_verify_dao_voter(gateway):
    gateway.is_human = AsyncMock(return_value=HumanityProof("0xVoter", True, 1.0, "gitcoin"))
    assert await gateway.verify_dao_voter("0xVoter") is True

    gateway.is_human.return_value = HumanityProof("0xSybil", False, 0.0, "none")
    assert await gateway.verify_dao_voter("0xSybil") is False

@pytest.mark.asyncio
async def test_verify_node_access(gateway):
    # Missing CleanHands stamp
    gateway.is_human = AsyncMock(return_value=HumanityProof("0xNodeOp", True, 1.0, "gitcoin", ["Google"]))
    assert await gateway.verify_node_access("0xNodeOp") is False

    # Has CleanHands stamp
    gateway.is_human = AsyncMock(return_value=HumanityProof("0xClean", True, 1.0, "gitcoin", ["Google", "CleanHands"]))
    assert await gateway.verify_node_access("0xClean") is True

    # Not human
    gateway.is_human.return_value = HumanityProof("0xBad", False, 0.0, "none", [])
    assert await gateway.verify_node_access("0xBad") is False

@pytest.mark.asyncio
async def test_temporal_chain_ed25519_signing(gateway):
    gateway.check_sign_protocol_attestation = AsyncMock(return_value=SAMPLE_SIGN_ATTEST)
    proof = await gateway.is_human("0xTestSign")
    assert proof.seal is not None
    assert proof.seal.startswith("923-")
    parts = proof.seal.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 32 # sha3_256 hash first 32 chars
    assert len(parts[2]) == 16 # signature truncated to 16 chars


@pytest.mark.asyncio
async def test_is_human_cache(gateway):
    gateway._is_human_internal = AsyncMock(return_value=HumanityProof("0xCacheTest", True, 1.0, "gitcoin"))

    # First call should miss cache
    proof1 = await gateway.is_human("0xCacheTest")
    assert gateway._is_human_internal.call_count == 1

    # Second call should hit cache
    proof2 = await gateway.is_human("0xCacheTest")
    assert gateway._is_human_internal.call_count == 1
    assert proof1 is proof2
