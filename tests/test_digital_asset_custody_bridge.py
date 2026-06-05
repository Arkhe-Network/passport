import pytest
from unittest.mock import patch, MagicMock
from node.digital_asset_custody_bridge.digital_asset_custody_bridge import get_validators_by_entity, compute_total_balance, check_slashing_risk

def test_compute_total_balance():
    validators = [
        {"balance": 32000000000},
        {"balance": 32000000000}
    ]
    assert compute_total_balance(validators) == 64000000000

def test_check_slashing_risk():
    validators = [
        {"slashed": False},
        {"slashed": True},
        {}
    ]
    risky = check_slashing_risk(validators)
    assert len(risky) == 1
    assert risky[0] == {"slashed": True}

@patch('node.digital_asset_custody_bridge.digital_asset_custody_bridge.requests.get')
def test_get_validators_by_entity(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"balance": 32000000000}]}
    mock_get.return_value = mock_response

    validators = get_validators_by_entity("AthenaFoundation")
    assert len(validators) == 1
    assert validators[0]["balance"] == 32000000000
    mock_get.assert_called_once_with("https://beaconcha.in/api/v1/validator/AthenaFoundation")
