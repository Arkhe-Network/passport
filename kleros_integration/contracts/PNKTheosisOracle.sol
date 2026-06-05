// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title PNKTheosisOracle
 * @dev Oracle for storing Theosis metrics on-chain
 */
contract PNKTheosisOracle {
    mapping(address => uint256) public jurorTheosis;
    address public owner;

    event TheosisUpdated(address indexed juror, uint256 theosisScore);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function updateTheosis(address juror, uint256 theosisScore) external onlyOwner {
        jurorTheosis[juror] = theosisScore;
        emit TheosisUpdated(juror, theosisScore);
    }

    function getJurorTheosis(address juror) external view returns (uint256) {
        return jurorTheosis[juror];
    }
}
