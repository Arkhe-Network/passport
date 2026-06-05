// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title CathedralKlerosBridge
 * @dev Bridge contract between Kleros and Cathedral
 */
contract CathedralKlerosBridge {
    address public veaRelayer;

    event BridgeMessageReceived(address indexed sender, bytes data);

    modifier onlyRelayer() {
        require(msg.sender == veaRelayer, "Not relayer");
        _;
    }

    constructor(address _veaRelayer) {
        veaRelayer = _veaRelayer;
    }

    function receiveMessage(bytes calldata data) external onlyRelayer {
        // Logic for interpreting cross-chain messages from Vea relay
        emit BridgeMessageReceived(msg.sender, data);
    }
}
