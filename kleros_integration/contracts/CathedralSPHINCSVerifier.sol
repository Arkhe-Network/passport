// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.28;

contract CathedralSPHINCSVerifier {
    uint256 private constant N = 16;
    uint256 private constant W = 8;
    uint256 private constant LOG2W = 3;
    uint256 private constant L = 43;
    uint256 private constant K = 8;
    uint256 private constant A = 16;
    uint256 private constant D = 2;
    uint256 private constant H_TOTAL = 24;
    uint256 private constant H_PER_LAYER = 12;
    uint256 private constant WOTS_MAX_STEP = W - 1;

    uint256 private constant SIG_RAND_SIZE = N;
    uint256 private constant FORS_LEAF_SIZE = N;
    uint256 private constant FORS_AUTH_SIZE = A * N;
    uint256 private constant FORS_SIG_ITEM_SIZE = FORS_LEAF_SIZE + FORS_AUTH_SIZE;
    uint256 private constant FORS_TOTAL_SIZE = K * FORS_SIG_ITEM_SIZE;
    uint256 private constant WOTS_SIG_SIZE = L * N;
    uint256 private constant MERKLE_AUTH_SIZE = H_PER_LAYER * N;
    uint256 private constant SIG_SIZE = 3952;

    function verifySPHINCS(
        bytes memory message,
        bytes calldata signature,
        bytes32 publicKeyRoot
    ) external pure returns (bool) {
        require(signature.length == SIG_SIZE, "CathedralSPHINCSVerifier: invalid signature length");

        bytes32 randomizer;
        uint256 offset = 0;
        assembly {
            randomizer := and(calldataload(signature.offset), 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000)
        }
        offset += N;

        bytes32 hMsg = keccak256(abi.encodePacked(randomizer, publicKeyRoot, message));
        bytes32 md = hMsg & bytes32(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000);
        uint256 idxTree = (uint256(hMsg) >> (N * 8)) & ((1 << H_PER_LAYER) - 1);
        uint256 idxLeaf = (uint256(hMsg) >> ((N + H_PER_LAYER) * 8)) & ((1 << H_PER_LAYER) - 1);

        bytes32 forsPK = _verifyFORS(
            signature[offset:offset + FORS_TOTAL_SIZE],
            md,
            idxTree,
            idxLeaf
        );
        offset += FORS_TOTAL_SIZE;

        bytes32 nodeLayer0 = _verifyWOTSC(
            signature[offset:offset + WOTS_SIG_SIZE],
            forsPK,
            idxLeaf,
            idxTree
        );
        offset += WOTS_SIG_SIZE;

        nodeLayer0 = _verifyMerklePath(
            nodeLayer0,
            signature[offset:offset + MERKLE_AUTH_SIZE],
            idxLeaf,
            H_PER_LAYER
        );
        offset += MERKLE_AUTH_SIZE;

        bytes32 nodeLayer1 = _verifyWOTSC(
            signature[offset:offset + WOTS_SIG_SIZE],
            nodeLayer0,
            idxTree,
            0
        );
        offset += WOTS_SIG_SIZE;

        bytes32 computedRoot = _verifyMerklePath(
            nodeLayer1,
            signature[offset:offset + MERKLE_AUTH_SIZE],
            idxTree,
            H_PER_LAYER
        );
        offset += MERKLE_AUTH_SIZE;

        bytes16 root16 = bytes16(computedRoot);
        bytes16 pk16 = bytes16(publicKeyRoot);

        return (root16 == pk16);
    }

    function _verifyFORS(
        bytes calldata forsData,
        bytes32 md,
        uint256 idxTree,
        uint256 idxLeaf
    ) private pure returns (bytes32) {
        bytes32[] memory roots = new bytes32[](K);
        uint256 innerOffset = 0;

        for (uint256 i = 0; i < K; i++) {
            bytes32 leafIdxHash = keccak256(abi.encodePacked(md, idxTree, idxLeaf, i));
            uint256 leafIdx = uint256(leafIdxHash) % (1 << A);

            bytes32 leafValue;
            assembly {
                leafValue := and(calldataload(add(forsData.offset, innerOffset)), 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000)
            }
            innerOffset += N;

            bytes32[] memory authPath = new bytes32[](A);
            for (uint256 j = 0; j < A; j++) {
                bytes32 tempAuth;
                assembly {
                    let pos := add(forsData.offset, innerOffset)
                    tempAuth := and(calldataload(pos), 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000)
                }
                authPath[j] = tempAuth;
                innerOffset += N;
            }

            bytes32 node = leafValue;
            uint256 currentIdx = leafIdx;
            for (uint256 level = 0; level < A; level++) {
                bytes32 sibling = authPath[level];
                if ((currentIdx >> level) & 1 == 0) {
                    node = keccak256(abi.encodePacked(node, sibling)) & bytes32(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000);
                } else {
                    node = keccak256(abi.encodePacked(sibling, node)) & bytes32(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000);
                }
            }
            roots[i] = node;
        }

        return keccak256(abi.encodePacked(roots)) & bytes32(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000);
    }

    function _verifyWOTSC(
        bytes calldata wotsSig,
        bytes32 message,
        uint256 leafIdx,
        uint256 treeIdx
    ) private pure returns (bytes32) {
        uint8[L] memory digits = _computeWinternitzDigits(message, leafIdx, treeIdx);

        bytes32[] memory chainValues = new bytes32[](L);
        uint256 offset = 0;
        for (uint256 i = 0; i < L; i++) {
            bytes32 sigValue;
            assembly {
                sigValue := and(calldataload(add(wotsSig.offset, offset)), 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000)
            }
            offset += N;

            uint256 steps = WOTS_MAX_STEP - digits[i];
            bytes32 current = sigValue;
            for (uint256 step = 0; step < steps; step++) {
                current = keccak256(abi.encodePacked(current)) & bytes32(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000);
            }
            chainValues[i] = current;
        }

        return keccak256(abi.encodePacked(chainValues)) & bytes32(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000);
    }

    function _verifyMerklePath(
        bytes32 leaf,
        bytes calldata authPath,
        uint256 leafIndex,
        uint256 treeHeight
    ) private pure returns (bytes32) {
        require(authPath.length == treeHeight * N, "Invalid Merkle auth path length");
        bytes32 node = leaf;
        uint256 idx = leafIndex;
        for (uint256 level = 0; level < treeHeight; level++) {
            bytes32 sibling;
            assembly {
                sibling := and(calldataload(add(authPath.offset, mul(level, N))), 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000)
            }
            if ((idx >> level) & 1 == 0) {
                node = keccak256(abi.encodePacked(node, sibling)) & bytes32(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000);
            } else {
                node = keccak256(abi.encodePacked(sibling, node)) & bytes32(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000);
            }
        }
        return node;
    }

    function _computeWinternitzDigits(
        bytes32 msgHash,
        uint256 leafIdx,
        uint256 treeIdx
    ) private pure returns (uint8[L] memory digits) {
        bytes32 expanded = keccak256(abi.encodePacked(msgHash, leafIdx, treeIdx, uint8(0)));
        uint256 bitsAvailable = 256;
        uint256 bitPos = 0;
        for (uint256 i = 0; i < L; i++) {
            if (bitsAvailable < LOG2W) {
                expanded = keccak256(abi.encodePacked(expanded, uint8(i)));
                bitsAvailable = 256;
                bitPos = 0;
            }
            uint256 digit = (uint256(expanded) >> bitPos) & ((1 << LOG2W) - 1);
            digits[i] = uint8(digit);
            bitPos += LOG2W;
            bitsAvailable -= LOG2W;
        }
    }
}
