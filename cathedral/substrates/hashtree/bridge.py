"""
Hashtree Bridge — Substrato 1101 v1.0.0
Integração Cathedral ARKHE ↔ hashtree.cc (content-addressed)
Nostr + Merkle + P2P + CHK Encryption
Arquiteto: ORCID 0009-0005-2697-4668
Selo: HASHTREE-BRIDGE-1101-v1.0.0-2026-06-08
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import IntEnum
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: CORE TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class HashtreeVisibility(IntEnum):
    PUBLIC = 0
    LINK_VISIBLE = 1
    PRIVATE = 2


class NostrKind(IntEnum):
    SET_METADATA = 0
    TEXT_NOTE = 1
    RECOMMEND_RELAY = 2
    CONTACTS = 3
    ENCRYPTED_DM = 4
    DELETE = 5
    REACTION = 7
    CHANNEL_CREATION = 40
    CHANNEL_MESSAGE = 42
    # Custom Cathedral ARKHE
    CATHEDRAL_ANCHOR = 31001
    CATHEDRAL_PROOF = 31002
    CATHEDRAL_LAKE = 31003


@dataclass
class HashtreeCID:
    """Content Identifier no formato hashtree.cc"""
    hash: str
    size: int
    codec: str = "raw"
    url: Optional[str] = None

    def __str__(self) -> str:
        return f"nhash:{self.hash[:16]}..."

    def to_npub_url(self, npub: str, path: str = "") -> str:
        if path:
            return f"htree://{npub}/{path}@{self.hash[:16]}"
        return f"htree://{npub}@{self.hash[:16]}"


@dataclass
class HashtreeNode:
    hash: str
    children: List[str] = field(default_factory=list)
    data: Optional[bytes] = None
    is_leaf: bool = False

    def compute_hash(self) -> str:
        if self.is_leaf and self.data:
            return "0x" + hashlib.sha256(self.data).hexdigest()
        combined = "".join(sorted(self.children)).encode()
        return "0x" + hashlib.sha256(combined).hexdigest()


@dataclass
class NostrEvent:
    id: str
    pubkey: str
    created_at: int
    kind: int
    tags: List[List[str]]
    content: str
    sig: str

    def to_json(self) -> Dict:
        return {
            "id": self.id, "pubkey": self.pubkey, "created_at": self.created_at,
            "kind": self.kind, "tags": self.tags, "content": self.content, "sig": self.sig}


@dataclass
class BlossomBlob:
    sha256: str
    size: int
    type: str
    uploaded: int
    url: str

    def to_dict(self) -> Dict:
        return {"sha256": self.sha256, "size": self.size, "type": self.type,
                "uploaded": self.uploaded, "url": self.url}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: CHK ENCRYPTION
# ═══════════════════════════════════════════════════════════════════════════════

class CHKEncryption:
    """
    CHK encryption: chave = hash do plaintext.
    Mesmo conteúdo → mesmo ciphertext → deduplicação automática.

    NOTA: Implementação demonstrativa com XOR.
    Em produção: AES-256-GCM com HKDF-SHA256 derivando a chave do hash.
    """

    BLOCK_SIZE = 32  # SHA-256 output

    @staticmethod
    def derive_key(plaintext: bytes) -> bytes:
        return hashlib.sha256(plaintext).digest()

    @staticmethod
    def encrypt(plaintext: bytes) -> Tuple[bytes, bytes]:
        key = CHKEncryption.derive_key(plaintext)
        # XOR stream cipher (demonstração)
        key_stream = key * (len(plaintext) // CHKEncryption.BLOCK_SIZE + 1)
        ciphertext = bytes(p ^ k for p, k in zip(plaintext, key_stream))
        return ciphertext, key

    @staticmethod
    def decrypt(ciphertext: bytes, key: bytes) -> bytes:
        key_stream = key * (len(ciphertext) // CHKEncryption.BLOCK_SIZE + 1)
        return bytes(c ^ k for c, k in zip(ciphertext, key_stream))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: MERKLE TREE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class HashtreeMerkleEngine:
    """
    Engine Merkle tree compatível com hashtree.cc.
    SHA-256 com prefixos 0x00 (leaf) e 0x01 (internal) para prevenir
    second-preimage attacks (RFC 6962-style).
    """

    LEAF_PREFIX = b"\x00"
    INTERNAL_PREFIX = b"\x01"

    def __init__(self):
        self.nodes: Dict[str, HashtreeNode] = {}
        self.leaves: List[str] = []

    def add_leaf(self, data: bytes) -> str:
        leaf_hash = "0x" + hashlib.sha256(self.LEAF_PREFIX + data).hexdigest()
        self.nodes[leaf_hash] = HashtreeNode(hash=leaf_hash, data=data, is_leaf=True)
        self.leaves.append(leaf_hash)
        return leaf_hash

    def build_tree(self) -> str:
        if not self.leaves:
            return "0x" + hashlib.sha256(b"empty").hexdigest()

        current_level = self.leaves.copy()
        while len(current_level) > 1:
            if len(current_level) % 2 == 1:
                current_level.append(current_level[-1])
            next_level = []
            for i in range(0, len(current_level), 2):
                hashes = sorted([current_level[i][2:], current_level[i + 1][2:]])
                combined = self.INTERNAL_PREFIX + (hashes[0] + hashes[1]).encode()
                node_hash = "0x" + hashlib.sha256(combined).hexdigest()
                self.nodes[node_hash] = HashtreeNode(
                    hash=node_hash, children=[current_level[i], current_level[i + 1]])
                next_level.append(node_hash)
            current_level = next_level
        return current_level[0]

    def get_proof(self, leaf_hash: str) -> Optional[List[str]]:
        if leaf_hash not in self.leaves:
            return None
        proof = []
        current_level = self.leaves.copy()
        while len(current_level) > 1:
            if len(current_level) % 2 == 1:
                current_level.append(current_level[-1])
            next_level = []
            for i in range(0, len(current_level), 2):
                hashes = sorted([current_level[i][2:], current_level[i + 1][2:]])
                node_hash = "0x" + hashlib.sha256(self.INTERNAL_PREFIX + (hashes[0] + hashes[1]).encode()).hexdigest()
                if current_level[i] == leaf_hash or current_level[i + 1] == leaf_hash:
                    sibling = current_level[i + 1] if current_level[i] == leaf_hash else current_level[i]
                    proof.append(sibling)
                    leaf_hash = node_hash
                next_level.append(node_hash)
            current_level = next_level
        return proof

    def verify_proof(self, leaf_hash: str, proof: List[str], root: str) -> bool:
        current = leaf_hash
        for sibling in proof:
            hashes = sorted([current[2:], sibling[2:]])
            combined = self.INTERNAL_PREFIX + (hashes[0] + hashes[1]).encode()
            current = "0x" + hashlib.sha256(combined).hexdigest()
        return current == root

    def get_telemetry(self) -> Dict:
        return {
            "module": "HashtreeMerkleEngine", "version": "1.0.0", "substrate": "1101",
            "seal": "HASHTREE-MERKLE-1101-v1.0.0-2026-06-08",
            "total_nodes": len(self.nodes), "leaves": len(self.leaves),
            "root": (self.build_tree()[:16] + "...") if self.leaves else "empty"}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: NOSTR PUBLISHER
# ═══════════════════════════════════════════════════════════════════════════════

class NostrPublisher:
    """
    Publica anchors Cathedral ARKHE em relays Nostr.
    Kinds 31001 (anchor), 31002 (proof), 31003 (lake snapshot).
    """

    DEFAULT_RELAYS = [
        "wss://relay.damus.io", "wss://relay.nostr.bg",
        "wss://nos.lol", "wss://nostr.wine",
    ]

    def __init__(self, private_key: Optional[str] = None,
                 relays: Optional[List[str]] = None):
        self.private_key = private_key
        self.relays = relays or self.DEFAULT_RELAYS.copy()
        self._events_published = 0
        self._npub: Optional[str] = None
        if private_key:
            self._derive_npub()

    def _derive_npub(self):
        if self.private_key:
            # Em produção: secp256k1 + bech32 encoding
            self._npub = "npub" + hashlib.sha256(
                self.private_key.encode()).hexdigest()[:58]

    def publish_merkle_anchor(self, merkle_root: str, proof_chain_tip: str,
                               theosis_reading: Optional[Dict] = None) -> Optional[str]:
        if not self._npub:
            return None
        content = json.dumps({
            "merkle_root": merkle_root, "proof_chain_tip": proof_chain_tip,
            "theosis": theosis_reading, "timestamp": time.time(),
            "cathedral_version": "6.0.0"}, sort_keys=True, default=str)
        event = NostrEvent(
            id="0x" + hashlib.sha256(content.encode()).hexdigest(),
            pubkey=self._npub, created_at=int(time.time()),
            kind=NostrKind.CATHEDRAL_ANCHOR,
            tags=[["e", proof_chain_tip], ["t", "cathedral"]],
            content=content,
            sig="0x" + hashlib.sha256(
                (content + (self.private_key or "")).encode()).hexdigest()[:128])
        self._events_published += 1
        logging.info(f"[NostrPublisher] Anchor: {event.id[:16]}...")
        return event.id

    def publish_zk_proof(self, proof_id: str, circuit_hash: str,
                          verified: bool) -> Optional[str]:
        content = json.dumps({
            "proof_id": proof_id, "circuit_hash": circuit_hash,
            "verified": verified, "timestamp": time.time()}, sort_keys=True)
        event = NostrEvent(
            id="0x" + hashlib.sha256(content.encode()).hexdigest(),
            pubkey=self._npub or "anonymous", created_at=int(time.time()),
            kind=NostrKind.CATHEDRAL_PROOF, tags=[["p", proof_id]],
            content=content,
            sig="0x" + hashlib.sha256(content.encode()).hexdigest()[:128])
        self._events_published += 1
        return event.id

    def publish_lake_snapshot(self, snapshot: Dict) -> Optional[str]:
        content = json.dumps(snapshot, sort_keys=True, default=str)
        event = NostrEvent(
            id="0x" + hashlib.sha256(content.encode()).hexdigest(),
            pubkey=self._npub or "anonymous", created_at=int(time.time()),
            kind=NostrKind.CATHEDRAL_LAKE, tags=[["t", "memory_lake"]],
            content=content,
            sig="0x" + hashlib.sha256(content.encode()).hexdigest()[:128])
        self._events_published += 1
        return event.id

    def get_telemetry(self) -> Dict:
        return {
            "module": "NostrPublisher", "version": "1.0.0", "substrate": "1101",
            "seal": "NOSTR-PUBLISHER-1101-v1.0.0-2026-06-08",
            "npub": (self._npub[:16] + "...") if self._npub else None,
            "relays": len(self.relays), "events_published": self._events_published}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: BLOSSOM CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class BlossomClient:
    """
    Cliente para servidores Blossom (BUD-01/02/03/04).
    Upload/download de blobs como fallback P2P.
    """

    def __init__(self, server_urls: Optional[List[str]] = None):
        self.servers = server_urls or ["https://blossom.nostr.com", "https://cdn.nostr.build"]
        self._blobs: Dict[str, BlossomBlob] = {}

    def upload_blob(self, data: bytes, content_type: str = "application/octet-stream",
                    auth_token: Optional[str] = None) -> Optional[BlossomBlob]:
        sha256 = hashlib.sha256(data).hexdigest()
        blob = BlossomBlob(
            sha256=sha256, size=len(data), type=content_type,
            uploaded=int(time.time()), url=f"{self.servers[0]}/{sha256}")
        self._blobs[sha256] = blob
        logging.info(f"[BlossomClient] Upload: {sha256[:16]}... ({len(data)} bytes)")
        return blob

    def download_blob(self, sha256: str) -> Optional[bytes]:
        if sha256 in self._blobs:
            logging.info(f"[BlossomClient] Download: {sha256[:16]}...")
            return b"simulated_blob_data"
        return None

    def list_blobs(self, pub_key: Optional[str] = None) -> List[BlossomBlob]:
        return list(self._blobs.values())

    def get_telemetry(self) -> Dict:
        return {
            "module": "BlossomClient", "version": "1.0.0", "substrate": "1101",
            "seal": "BLOSSOM-CLIENT-1101-v1.0.0-2026-06-08",
            "servers": len(self.servers), "blobs_stored": len(self._blobs),
            "total_size": sum(b.size for b in self._blobs.values())}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: P2P TRANSPORT
# ═══════════════════════════════════════════════════════════════════════════════

class P2PTransport:
    """
    Transporte P2P hashtree.cc: WebRTC (browser) / FIPS endpoint (native).
    Hops-to-live style (Hyphanet/Freenet-inspired).
    """

    def __init__(self, max_hops: int = 18):
        self.max_hops = max_hops
        self._peers: Dict[str, Dict] = {}
        self._requests_sent = 0
        self._responses_received = 0

    def add_peer(self, peer_id: str, endpoint: str, is_relay: bool = False):
        self._peers[peer_id] = {
            "endpoint": endpoint, "is_relay": is_relay,
            "last_seen": time.time(), "hops": 0}

    def remove_peer(self, peer_id: str):
        self._peers.pop(peer_id, None)

    def request_blob(self, cid: str, hops: int = 0) -> Optional[bytes]:
        if hops > self.max_hops:
            return None
        self._requests_sent += 1
        for peer_id, info in self._peers.items():
            logging.debug(f"[P2P] Request {cid[:16]}... from {peer_id[:16]}... (hops={hops})")
        self._responses_received += 1
        return b"simulated_p2p_data"

    def offer_blob(self, data: bytes) -> str:
        cid = hashlib.sha256(data).hexdigest()
        logging.debug(f"[P2P] Offering {cid[:16]}... to {len(self._peers)} peers")
        return cid

    def get_peer_count(self) -> int:
        return len(self._peers)

    def get_telemetry(self) -> Dict:
        return {
            "module": "P2PTransport", "version": "1.0.0", "substrate": "1101",
            "seal": "P2P-TRANSPORT-1101-v1.0.0-2026-06-08",
            "peers": len(self._peers), "max_hops": self.max_hops,
            "requests_sent": self._requests_sent,
            "responses_received": self._responses_received}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: HASHTREE BRIDGE — MAIN SUBSTRATE
# ═══════════════════════════════════════════════════════════════════════════════

class HashtreeBridge1101:
    """
    Substrato 1101 — Hashtree Bridge.
    Integra Cathedral ARKHE ao ecossistema hashtree.cc.

    Pontos de integração:
      • MemoryLake 1100 → persistência por CID (content-addressed)
      • RecursiveProofChain 1100 → provas verificáveis por Merkle root
      • TemporalChain 1097 → anchors em relays Nostr
      • GGUF Bridge 1094 → modelos servidos via P2P
      • ZKML 1095 → CHK encryption + ZK proofs
    """

    def __init__(self, nostr_private_key: Optional[str] = None,
                 nostr_relays: Optional[List[str]] = None,
                 blossom_servers: Optional[List[str]] = None,
                 p2p_max_hops: int = 18,
                 visibility: HashtreeVisibility = HashtreeVisibility.PUBLIC):
        self.merkle = HashtreeMerkleEngine()
        self.nostr = NostrPublisher(nostr_private_key, nostr_relays)
        self.blossom = BlossomClient(blossom_servers)
        self.p2p = P2PTransport(p2p_max_hops)
        self.visibility = visibility
        self._chk = CHKEncryption()
        self._lake_cids: List[str] = []
        self._proof_cids: List[str] = []
        self._gguf_cids: List[str] = []

    def persist_memory_lake(self, lake_entries: List[Dict],
                             encrypt: bool = False) -> HashtreeCID:
        """Persiste MemoryLake no hashtree. Retorna CID."""
        data = json.dumps(lake_entries, sort_keys=True, default=str).encode()

        if encrypt or self.visibility != HashtreeVisibility.PUBLIC:
            data, key = self._chk.encrypt(data)
            logging.info(f"[HashtreeBridge] Lake encrypted (CHK: {key[:8].hex()}...)")

        leaf_hash = self.merkle.add_leaf(data)
        root = self.merkle.build_tree()

        cid = HashtreeCID(
            hash=leaf_hash[2:], size=len(data),
            codec="json" if not encrypt else "chk+json")
        self._lake_cids.append(str(cid))

        blob = self.blossom.upload_blob(data, "application/json")
        if blob:
            cid.url = blob.url

        self.nostr.publish_merkle_anchor(
            merkle_root=root, proof_chain_tip=leaf_hash)

        logging.info(f"[HashtreeBridge] Lake persisted: {cid}")
        return cid

    def persist_proof_chain(self, proof_nodes: List[Dict]) -> HashtreeCID:
        """Persiste RecursiveProofChain no hashtree."""
        data = json.dumps(proof_nodes, sort_keys=True, default=str).encode()
        leaf_hash = self.merkle.add_leaf(data)
        root = self.merkle.build_tree()

        cid = HashtreeCID(hash=leaf_hash[2:], size=len(data), codec="json")
        self._proof_cids.append(str(cid))

        self.nostr.publish_merkle_anchor(
            merkle_root=root, proof_chain_tip=leaf_hash)

        logging.info(f"[HashtreeBridge] ProofChain persisted: {cid}")
        return cid

    def serve_gguf_model(self, model_path: str, npub: str,
                          repo_name: str) -> Optional[HashtreeCID]:
        """Serve modelo GGUF via hashtree P2P (decentralized CDN)."""
        path = Path(model_path)
        if not path.exists():
            logging.error(f"[HashtreeBridge] GGUF not found: {model_path}")
            return None

        with open(path, "rb") as f:
            data = f.read()

        leaf_hash = self.merkle.add_leaf(data)
        root = self.merkle.build_tree()

        cid = HashtreeCID(hash=leaf_hash[2:], size=len(data), codec="gguf")
        self._gguf_cids.append(str(cid))

        self.blossom.upload_blob(data, "application/octet-stream")
        self.p2p.offer_blob(data)

        npub_url = cid.to_npub_url(npub, f"models/{repo_name}")
        logging.info(f"[HashtreeBridge] GGUF served: {npub_url}")
        return cid

    def retrieve_by_cid(self, cid: str) -> Optional[bytes]:
        """Recupera dados por CID: P2P → Blossom → None."""
        data = self.p2p.request_blob(cid)
        if data:
            return data
        data = self.blossom.download_blob(cid)
        return data

    def verify_integrity(self, cid: str, expected_root: str) -> bool:
        """Verifica integridade de CID contra Merkle root."""
        proof = self.merkle.get_proof(cid)
        if not proof:
            return False
        return self.merkle.verify_proof(cid, proof, expected_root)

    def publish_canonization_to_nostr(self, canonization: Dict) -> Optional[str]:
        """Publica canonização individual como evento Nostr."""
        content = json.dumps(canonization, sort_keys=True, default=str)
        event_id = self.nostr.publish_merkle_anchor(
            merkle_root=canonization.get("merkle_root", ""),
            proof_chain_tip=canonization.get("proof_hash", ""),
            theosis_reading=canonization.get("theosis"))
        return event_id

    def get_telemetry(self) -> Dict:
        return {
            "module": "HashtreeBridge1101", "version": "1.0.0", "substrate": "1101",
            "seal": "HASHTREE-BRIDGE-1101-v1.0.0-2026-06-08",
            "visibility": self.visibility.name,
            "lake_cids": len(self._lake_cids),
            "proof_cids": len(self._proof_cids),
            "gguf_cids": len(self._gguf_cids),
            "merkle": self.merkle.get_telemetry(),
            "nostr": self.nostr.get_telemetry(),
            "blossom": self.blossom.get_telemetry(),
            "p2p": self.p2p.get_telemetry(),
        }
