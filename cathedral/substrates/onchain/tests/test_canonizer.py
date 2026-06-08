"""Testes para OnChainCanonizer 1100."""
import pytest

class TestOnChainCanonizer:
    def test_imports(self):
        from cathedral.substrates.onchain.types import CanonizationType, ChainId
        from cathedral.substrates.onchain.memory_lake import MemoryLake
        from cathedral.substrates.onchain.proof_chain import RecursiveProofChain
        from cathedral.substrates.onchain.signer import EIP712Signer
        from cathedral.substrates.onchain.governance import GovernanceBridge
        from cathedral.substrates.onchain.canonizer import OnChainCanonizer
        assert CanonizationType.KERNEL_INTEGRITY == 1
        assert ChainId.MAINNET == 1

    def test_memory_lake_ingest(self):
        from cathedral.substrates.onchain.types import MemoryLakeEntry, CanonizationType
        from cathedral.substrates.onchain.memory_lake import MemoryLake
        lake = MemoryLake()
        entry = MemoryLakeEntry(entry_hash="", entry_type=CanonizationType.KERNEL_INTEGRITY, data={"test": True})
        assert lake.ingest(entry) is True
        assert len(lake.entries) == 1
        assert lake.get_merkle_root() is not None

    def test_merkle_proof(self):
        from cathedral.substrates.onchain.types import MemoryLakeEntry, CanonizationType
        from cathedral.substrates.onchain.memory_lake import MemoryLake
        lake = MemoryLake()
        for i in range(5):
            e = MemoryLakeEntry(entry_hash="", entry_type=CanonizationType.STATE_TRANSITION, data={"i": i})
            lake.ingest(e)
        root = lake.get_merkle_root()
        for h in lake.ordered_hashes:
            proof = lake.get_proof(h)
            assert proof is not None
            assert len(proof) > 0

    def test_proof_chain(self):
        from cathedral.substrates.onchain.proof_chain import RecursiveProofChain
        chain = RecursiveProofChain()
        node = chain.add_canonization_proof("0xabc", "0xdef", "test")
        assert node.index == 1
        valid, errors = chain.verify_chain_integrity()
        assert valid is True

    def test_governance_propose(self):
        from cathedral.substrates.onchain.types import CanonizationType
        from cathedral.substrates.onchain.memory_lake import MemoryLake
        from cathedral.substrates.onchain.proof_chain import RecursiveProofChain
        from cathedral.substrates.onchain.signer import EIP712Signer
        from cathedral.substrates.onchain.governance import GovernanceBridge
        signer = EIP712Signer()
        lake = MemoryLake()
        chain = RecursiveProofChain()
        gov = GovernanceBridge(signer, lake, chain)
        pid = gov.propose_canonization(CanonizationType.ARCHITECTURAL_DECISION, {"test": True})
        assert pid.startswith("0x")
        assert len(gov.get_pending_proposals()) == 1

    def test_governance_local_sign(self):
        from cathedral.substrates.onchain.types import CanonizationType
        from cathedral.substrates.onchain.memory_lake import MemoryLake
        from cathedral.substrates.onchain.proof_chain import RecursiveProofChain
        from cathedral.substrates.onchain.signer import EIP712Signer
        from cathedral.substrates.onchain.governance import GovernanceBridge, ProposalState
        signer = EIP712Signer()
        lake = MemoryLake()
        chain = RecursiveProofChain()
        gov = GovernanceBridge(signer, lake, chain)
        pid = gov.propose_canonization(CanonizationType.ARCHITECTURAL_DECISION, {"test": True})
        result = gov.sign_and_canonize_locally(pid)
        assert result is True
        status = gov.get_proposal_status(pid)
        assert status["canonized"] is True
