import json
import builtins
import os
import sys
from web3 import Web3
from eth_utils import to_hex

N = 16
W = 8
LOG2W = 3
L = 43
K = 8
A = 16
D = 2
H_TOTAL = 24
H_PER_LAYER = 12
WOTS_MAX_STEP = W - 1

def keccak256(data: bytes) -> bytes:
    return Web3.keccak(data)

def compute_winternitz_digits(msg_hash: bytes, leaf_idx: int, tree_idx: int) -> list[int]:
    expanded = keccak256(msg_hash + leaf_idx.to_bytes(32, 'big') + tree_idx.to_bytes(32, 'big') + b'\x00')
    bits_available = 256
    bit_pos = 0
    digits = []

    expanded_int = int.from_bytes(expanded, 'big')

    for i in range(L):
        if bits_available < LOG2W:
            expanded = keccak256(expanded + bytes([i]))
            expanded_int = int.from_bytes(expanded, 'big')
            bits_available = 256
            bit_pos = 0

        digit = (expanded_int >> bit_pos) & ((1 << LOG2W) - 1)
        digits.append(digit)

        bit_pos += LOG2W
        bits_available -= LOG2W

    return digits

def build_merkle_tree(leaves: list[bytes]) -> tuple[bytes, list[list[bytes]]]:
    n_leaves = len(leaves)
    tree = [leaves]

    current_level = leaves
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i][:N] + b'\x00' * (32 - N)
            right = current_level[i+1][:N] + b'\x00' * (32 - N)
            next_level.append(keccak256(left + right)[:N] + b'\x00' * (32 - N))
        tree.append(next_level)
        current_level = next_level

    root = tree[-1][0]

    auth_paths = []
    for i in range(n_leaves):
        path = []
        idx = i
        for level in range(len(tree) - 1):
            sibling_idx = idx ^ 1
            sibling = tree[level][sibling_idx][:N]
            path.append(sibling)
            idx >>= 1
        auth_paths.append(path)

    return root, auth_paths

def sign():
    seed = b'Cathedral ARKHE Seed for SPHINCS+ C13 Keygen'
    randomizer = keccak256(seed + b'randomizer')[:N]

    def get_wots_sk_seed(layer, index):
        return keccak256(b"WOTS_SK" + layer.to_bytes(4, 'big') + index.to_bytes(8, 'big'))[:N]

    def wots_pk(layer, index):
        sk_seed = get_wots_sk_seed(layer, index)
        chain_tops = []
        for i in range(L):
            current = keccak256(sk_seed + i.to_bytes(32, 'big'))[:N] + b'\x00' * (32 - N)
            for _ in range(WOTS_MAX_STEP):
                current = keccak256(current)[:N] + b'\x00' * (32 - N)
            chain_tops.append(current)
        return keccak256(b''.join(chain_tops))[:N] + b'\x00' * (32 - N)

    def wots_sign(layer, index, msg_hash, leaf_idx, tree_idx):
        sk_seed = get_wots_sk_seed(layer, index)
        digits = compute_winternitz_digits(msg_hash, leaf_idx, tree_idx)
        sig = []
        for i in range(L):
            current = keccak256(sk_seed + i.to_bytes(32, 'big'))[:N] + b'\x00' * (32 - N)
            for _ in range(digits[i]):
                current = keccak256(current)[:N] + b'\x00' * (32 - N)
            sig.append(current[:N])
        return sig

    layer1_leaves = []
    for i in range(1 << H_PER_LAYER):
        layer1_leaves.append(wots_pk(1, i)[:N])
    pk_root, layer1_auth_paths = build_merkle_tree(layer1_leaves)
    public_key_root_32 = pk_root[:N] + b'\x00' * (32 - N)

    message = b"Test message for SPHINCS C13 verifier"
    randomizer_32 = randomizer + b'\x00' * (32 - N)
    h_msg = keccak256(randomizer_32 + public_key_root_32 + message)
    md = h_msg[:N]
    h_msg_int = int.from_bytes(h_msg, 'big')
    idx_tree = (h_msg_int >> (N * 8)) & ((1 << H_PER_LAYER) - 1)
    idx_leaf = (h_msg_int >> ((N + H_PER_LAYER) * 8)) & ((1 << H_PER_LAYER) - 1)

    layer0_leaves = []
    for i in range(1 << H_PER_LAYER):
        layer0_leaves.append(wots_pk(0, (idx_tree << H_PER_LAYER) + i)[:N])
    layer0_root, layer0_auth_paths = build_merkle_tree(layer0_leaves)

    fors_sig_parts = []
    fors_roots = []
    md_32 = md + b'\x00' * (32 - N)
    for i in range(K):
        leaf_idx_hash = keccak256(md_32 + idx_tree.to_bytes(32, 'big') + idx_leaf.to_bytes(32, 'big') + i.to_bytes(32, 'big'))
        leaf_idx = int.from_bytes(leaf_idx_hash, 'big') % (1 << A)

        leaf_value = os.urandom(N)
        fors_sig_parts.append(leaf_value)

        auth_path = [os.urandom(N) for _ in range(A)]
        for ap in auth_path:
            fors_sig_parts.append(ap)

        node = leaf_value + b'\x00' * (32 - N)
        current_idx = leaf_idx
        for level in range(A):
            sibling = auth_path[level] + b'\x00' * (32 - N)
            if (current_idx >> level) & 1 == 0:
                node = keccak256(node + sibling)[:N] + b'\x00' * (32 - N)
            else:
                node = keccak256(sibling + node)[:N] + b'\x00' * (32 - N)
        fors_roots.append(node)

    fors_pk = keccak256(b''.join(fors_roots))[:N] + b'\x00' * (32 - N)

    signature_parts = []
    signature_parts.append(randomizer)
    signature_parts.extend(fors_sig_parts)

    wots_sig_0 = wots_sign(0, (idx_tree << H_PER_LAYER) + idx_leaf, fors_pk, idx_leaf, idx_tree)
    signature_parts.extend(wots_sig_0)
    signature_parts.extend(layer0_auth_paths[idx_leaf])

    wots_sig_1 = wots_sign(1, idx_tree, layer0_root, idx_tree, 0)
    signature_parts.extend(wots_sig_1)
    signature_parts.extend(layer1_auth_paths[idx_tree])

    signature_bytes = b''.join(signature_parts)

    output = {
        "message": to_hex(message),
        "signature": to_hex(signature_bytes),
        "publicKeyRoot": to_hex(public_key_root_32),
        "logs": {
            "md": to_hex(md_32),
            "idxTree": idx_tree,
            "idxLeaf": idx_leaf,
            "forsPK": to_hex(fors_pk),
            "nodeLayer0": to_hex(wots_pk(0, (idx_tree << H_PER_LAYER) + idx_leaf)),
            "node0Root": to_hex(layer0_root[:N] + b'\x00' * (32 - N)),
            "nodeLayer1": to_hex(wots_pk(1, idx_tree)),
            "computedRoot": to_hex(pk_root[:N] + b'\x00' * (32 - N))
        }
    }

    import builtins
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_sphincs_sig.json"), "w") as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    sign()
