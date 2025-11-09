# README.md
# event-commitment-soundness

## Overview
This mini repo builds a Merkle commitment over ERC-20 Transfer events from a given token within a block range. It then produces and verifies an inclusion proof for one event. This mirrors Aztec/rollup-style soundness patterns where a succinct root commits to many facts and a short proof demonstrates inclusion without revealing the entire set.

## Files
- app.py — CLI that fetches Transfer logs, builds a Keccak-based Merkle tree, prints the root, emits a proof for a chosen index, and verifies it.
- README.md — this document.

## Requirements
- Python 3.10+
- web3.py
- An Ethereum-compatible RPC endpoint (Infura, Alchemy, or your own node). Set RPC_URL as an environment variable or edit the constant in app.py.

## Installation
1) Install Python 3.10+.
2) Install dependency: pip install web3.
3) Configure RPC: export RPC_URL="https://mainnet.infura.io/v3/<KEY>" or use your node URL.

## Usage
python app.py <token_address> <from_block> <to_block> [--index N]
Example: python app.py 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 18000000 18001000 --index 3

## What it does
- Connects to your RPC and detects the network.
- Fetches all ERC-20 Transfer events for the token between from_block and to_block (inclusive).
- Builds a Merkle tree over per-event leaves using: keccak(txHash || logIndex || topic0 || keccak(eventData)).
- Prints the Merkle root.
- Outputs an inclusion proof for the specified index and verifies it locally.

## Expected output
- Network name and chain ID.
- Token address and block range.
- Number of fetched events and timing.
- Merkle root as a hex string.
- Proof target index and a list of proof elements (sibling hash plus position per level).
- Verification result indicating whether the proof reconstructs the root.
- Total elapsed time.

## Notes
- Works on any EVM network supported by your RPC. For large ranges, providers may enforce rate limits.
- If no events are found, the program exits with a message and code 0.
- The Merkle construction uses Keccak(left || right) and duplicates the last node on odd levels.
- The leaves commit to transaction hash, log index, topic0, and a hash of event data to remain compact while binding content.
- This is a conceptual soundness demo; it does not produce zero-knowledge proofs. You can port the leaf logic to a ZK circuit to prove inclusion privately in the future.
- For reproducibility, use the same block range, RPC URL, and Python/web3 versions when comparing roots across environments.
