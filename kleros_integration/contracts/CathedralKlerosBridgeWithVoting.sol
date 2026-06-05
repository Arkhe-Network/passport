// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./CathedralKlerosBridge.sol";
import "./PNKTheosisOracle.sol";

/**
 * @title CathedralKlerosBridgeWithVoting
 * @dev Extend the bridge with "Theosis-weighted voting".
 */
contract CathedralKlerosBridgeWithVoting is CathedralKlerosBridge {
    PNKTheosisOracle public theosisOracle;
    uint256 public baseWeight = 1000;

    constructor(address _veaRelayer, address _theosisOracle) CathedralKlerosBridge(_veaRelayer) {
        theosisOracle = PNKTheosisOracle(_theosisOracle);
    }

    function getVotingWeight(address juror) external view returns (uint256 weight) {
        uint256 theosisScore = theosisOracle.getJurorTheosis(juror);
        // Multiplier based on Theosis. If theosis is 0, weight is baseWeight.
        // E.g. score of 50 gives 1050 weight (baseWeight + theosisScore * some_factor)
        // For simplicity, we just add the score to the base weight.
        weight = baseWeight + theosisScore;
        return weight;
    }
}
