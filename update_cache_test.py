import sys

filename = "tests/test_passport_gateway.py"

with open(filename, "r") as f:
    content = f.read()

find_str = """@pytest.mark.asyncio
async def test_sign_protocol_human(gateway):
    with patch.object(gateway, 'check_sign_protocol_attestation', return_value=SAMPLE_SIGN_ATTEST):
        proof = await gateway.is_human("0xTest")
        assert proof.is_human is True
        assert proof.score == 1.0
        assert proof.source == "sign_protocol"
        assert proof.attestation_uid == "0xattest123" """

replace_str = """@pytest.mark.asyncio
async def test_sign_protocol_human(gateway):
    with patch.object(gateway, 'check_sign_protocol_attestation', return_value=SAMPLE_SIGN_ATTEST):
        proof = await gateway.is_human("0xTest")
        assert proof.is_human is True
        assert proof.score == 1.0
        assert proof.source == "sign_protocol"
        assert proof.attestation_uid == "0xattest123"

@pytest.mark.asyncio
async def test_is_human_cache(gateway):
    gateway._is_human_internal = AsyncMock(return_value=HumanityProof("0xCacheTest", True, 1.0, "gitcoin"))

    # First call should miss cache
    proof1 = await gateway.is_human("0xCacheTest")
    assert gateway._is_human_internal.call_count == 1

    # Second call should hit cache
    proof2 = await gateway.is_human("0xCacheTest")
    assert gateway._is_human_internal.call_count == 1
    assert proof1 is proof2"""

content = content.replace(find_str, replace_str)

with open(filename, "w") as f:
    f.write(content)
