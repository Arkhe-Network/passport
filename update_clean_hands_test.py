import sys

filename = "tests/test_passport_gateway.py"

with open(filename, "r") as f:
    content = f.read()

find_str = """@pytest.mark.asyncio
async def test_verify_node_access(gateway):
    gateway.verify_dao_voter = AsyncMock(return_value=True)
    assert await gateway.verify_node_access("0xNodeOp") is True
    gateway.verify_dao_voter.return_value = False
    assert await gateway.verify_node_access("0xBad") is False"""

replace_str = """@pytest.mark.asyncio
async def test_verify_node_access(gateway):
    # Missing CleanHands stamp
    gateway.is_human = AsyncMock(return_value=HumanityProof("0xNodeOp", True, 1.0, "gitcoin", ["Google"]))
    assert await gateway.verify_node_access("0xNodeOp") is False

    # Has CleanHands stamp
    gateway.is_human = AsyncMock(return_value=HumanityProof("0xClean", True, 1.0, "gitcoin", ["Google", "CleanHands"]))
    assert await gateway.verify_node_access("0xClean") is True

    # Not human
    gateway.is_human.return_value = HumanityProof("0xBad", False, 0.0, "none", [])
    assert await gateway.verify_node_access("0xBad") is False"""

content = content.replace(find_str, replace_str)

with open(filename, "w") as f:
    f.write(content)
