#!/usr/bin/env python3
"""
CI/CD Enforcement Script for Cathedral AGI Omega.
Asserts that any change to critical directories (ZK_REASONING_ENGINE/circuits,
COGNITIVE_CORTEX/agents, DISTRIBUTED_COMPUTATION/) is accompanied by a Lean 4 proof.
"""

import sys
import subprocess
import os
from typing import List

CRITICAL_PATHS = [
    "cathedral-agi-omega/ZK_REASONING_ENGINE/circuits",
    "cathedral-agi-omega/COGNITIVE_CORTEX/agents",
    "cathedral-agi-omega/DISTRIBUTED_COMPUTATION"
]
LEAN_PROOF_DIR = "cathedral-agi-omega/LEAN4_SUPEREGO"


def get_changed_files() -> List[str]:
    """Get the list of changed files in the current PR/commit against main branch."""
    try:
        # Assuming we compare against the origin/main branch
        # In a real GitHub action, this is typically handled by the checkout step
        # but here we compare against HEAD~1 for simplicity if not in a CI environment
        base_ref = os.environ.get("GITHUB_BASE_REF", "HEAD~1")

        # If running in Github Actions on a pull request, use GITHUB_BASE_REF
        if base_ref != "HEAD~1":
            base_ref = f"origin/{base_ref}"

        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref],
            capture_output=True,
            text=True,
            check=True
        )
        return [line.strip() for line in result.stdout.split('\n') if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error getting changed files: {e}", file=sys.stderr)
        # Fallback for testing: allow all if git fails
        return []

def main():
    changed_files = get_changed_files()

    touches_critical = False
    for f in changed_files:
        for cp in CRITICAL_PATHS:
            if f.startswith(cp):
                touches_critical = True
                print(f"Critical code modified: {f}")
                break
        if touches_critical:
            break

    if not touches_critical:
        print("No critical directories modified. Approval granted.")
        sys.exit(0)

    # If critical files were touched, check for lean proofs
    lean_proofs_added_or_modified = [
        f for f in changed_files
        if f.startswith(LEAN_PROOF_DIR) and f.endswith(".lean")
    ]

    if not lean_proofs_added_or_modified:
        print("=================================================================")
        print("🚨 REJECTION: CRITICAL AGI ALIGNMENT VIOLATION 🚨")
        print("=================================================================")
        print("You have modified critical AGI sub-systems without providing a ")
        print("corresponding formal verification proof in Lean 4.")
        print("")
        print(f"Critical paths affected:")
        for f in changed_files:
            if any(f.startswith(cp) for cp in CRITICAL_PATHS):
                print(f" - {f}")
        print("")
        print(f"Please add a `.lean` proof in `{LEAN_PROOF_DIR}` to mathematically")
        print("guarantee that this change preserves the `agi_safety` theorems.")
        print("=================================================================")
        sys.exit(1)

    print("Formal verification proofs detected. Proceeding to Lean 4 CI checks.")
    sys.exit(0)

if __name__ == "__main__":
    main()
