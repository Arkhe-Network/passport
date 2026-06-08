"""Testes para HashtreeBridge 1101."""
import pytest

class TestHashtreeBridge:
    def test_imports(self):
        from cathedral.substrates.hashtree.bridge import (
            HashtreeBridge1101, HashtreeVisibility, CHKEncryption,
            HashtreeMerkleEngine, NostrPublisher, BlossomClient, P2PTransport,
        )
        assert HashtreeVisibility.PUBLIC == 0
        assert HashtreeVisibility.LINK_VISIBLE == 1

    def test_chk_encrypt_decrypt(self):
        from cathedral.substrates.hashtree.bridge import CHKEncryption
        plaintext = b"hello hashtree world"
        ciphertext, key = CHKEncryption.encrypt(plaintext)
        decrypted = CHKEncryption.decrypt(ciphertext, key)
        assert decrypted == plaintext

    def test_chk_deduplication(self):
        from cathedral.substrates.hashtree.bridge import CHKEncryption
        ct1, k1 = CHKEncryption.encrypt(b"same content")
        ct2, k2 = CHKEncryption.encrypt(b"same content")
        assert ct1 == ct2  # Same content → same ciphertext
        assert k1 == k2  # Same key

    def test_merkle_engine(self):
        from cathedral.substrates.hashtree.bridge import HashtreeMerkleEngine
        engine = HashtreeMerkleEngine()
        h1 = engine.add_leaf(b"data1")
        h2 = engine.add_leaf(b"data2")
        root = engine.build_tree()
        assert root is not None
        proof = engine.get_proof(h1)
        assert proof is not None
        assert engine.verify_proof(h1, proof, root) is True

    def test_nost_publisher(self):
        from cathedral.substrates.hashtree.bridge import NostrPublisher
        pub = NostrPublisher(private_key="test_key")
        eid = pub.publish_merkle_anchor("0x" + "aa" * 32, "0x" + "bb" * 32)
        assert eid is not None

    def test_blossom_client(self):
        from cathedral.substrates.hashtree.bridge import BlossomClient
        client = BlossomClient()
        blob = client.upload_blob(b"test data", "text/plain")
        assert blob is not None
        assert blob.sha256 is not None

    def test_p2p_transport(self):
        from cathedral.substrates.hashtree.bridge import P2PTransport
        p2p = P2PTransport(max_hops=5)
        p2p.add_peer("peer1", "ws://localhost:9999")
        assert p2p.get_peer_count() == 1

    def test_hashtree_bridge_persist_lake(self):
        from cathedral.substrates.hashtree.bridge import HashtreeBridge1101, HashtreeVisibility
        bridge = HashtreeBridge1101(visibility=HashtreeVisibility.LINK_VISIBLE)
        cid = bridge.persist_memory_lake([{"test": True, "i": 1}], encrypt=True)
        assert cid is not None
        assert cid.codec == "chk+json"

    def test_hashtree_bridge_telemetry(self):
        from cathedral.substrates.hashtree.bridge import HashtreeBridge1101
        bridge = HashtreeBridge1101()
        telem = bridge.get_telemetry()
        assert telem["module"] == "HashtreeBridge1101"
        assert telem["substrate"] == "1101"
        assert "HASHTREE-BRIDGE-1101" in telem["seal"]
