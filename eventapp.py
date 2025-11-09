# app.py
import os
import sys
import time
import argparse
from typing import List, Tuple
from web3 import Web3

RPC_URL = os.getenv("RPC_URL", "https://mainnet.infura.io/v3/your_api_key")

NETWORKS = {
    1: "Ethereum Mainnet",
    11155111: "Sepolia Testnet",
    10: "Optimism",
    137: "Polygon",
    42161: "Arbitrum One",
}

# ERC-20 Transfer event topic
TRANSFER_TOPIC0 = Web3.keccak(text="Transfer(address,address,uint256)").hex()

def network_name(chain_id: int) -> str:
    return NETWORKS.get(chain_id, f"Unknown (chain ID {chain_id})")

def to_hex(b: bytes) -> str:
    return "0x" + b.hex()

def pad32(b: bytes) -> bytes:
    return b.rjust(32, b"\x00")

def keccak_pair(l: bytes, r: bytes) -> bytes:
    return Web3.keccak(l + r)

def build_merkle_tree(leaves: List[bytes]) -> List[List[bytes]]:
    if not leaves:
        raise ValueError("No leaves to build a tree")
    level = [pad32(x) for x in leaves]
    tree = [level]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            L = level[i]
            R = level[i + 1] if i + 1 < len(level) else level[i]
            nxt.append(keccak_pair(L, R))
        tree.append(nxt)
        level = nxt
    return tree

def merkle_root(tree: List[List[bytes]]) -> bytes:
    return tree[-1][0]

def merkle_proof(tree: List[List[bytes]], index: int) -> List[Tuple[bytes, str]]:
    proof = []
    idx = index
    for level in tree[:-1]:
        sib_idx = idx ^ 1
        sibling = level[sib_idx] if sib_idx < len(level) else level[idx]
        pos = "right" if idx % 2 == 0 else "left"
        proof.append((sibling, pos))
        idx //= 2
    return proof

def verify_proof(leaf: bytes, proof: List[Tuple[bytes, str]], root: bytes) -> bool:
    cur = pad32(leaf)
    for sib, pos in proof:
        sib = pad32(sib)
        cur = keccak_pair(cur, sib) if pos == "right" else keccak_pair(sib, cur)
    return cur == root

def connect(url: str) -> Web3:
    w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        print("❌ Failed to connect to RPC. Check RPC_URL.")
        sys.exit(1)
    return w3

def fetch_transfer_logs(w3: Web3, token: str, start_block: int, end_block: int):
    """Fetch Transfer logs for a token between inclusive block range."""
    params = {
        "fromBlock": start_block,
        "toBlock": end_block,
        "address": token,
        "topics": [TRANSFER_TOPIC0],
    }
    return w3.eth.get_logs(params)

def build_event_leaf(log) -> bytes:
    """
    Build a leaf commitment for an event:
    keccak(txHash[32] || logIndex[8] || topic0[32] || dataKeccak[32])
    """
    txh = bytes.fromhex(log["transactionHash"].hex()[2:])
    log_index = int(log["logIndex"])
    topic0 = bytes.fromhex(log["topics"][0].hex()[2:])
    data_hash = Web3.keccak(bytes.fromhex(log["data"][2:]))
    payload = (
        txh +
        log_index.to_bytes(8, "big") +
        topic0 +
        data_hash
    )
    return Web3.keccak(payload)

def parse_args():
    p = argparse.ArgumentParser(description="Build a Merkle commitment over ERC-20 Transfer events for a block range.")
    p.add_argument("token", help="ERC-20 token contract address")
    p.add_argument("from_block", type=int, help="Start block (inclusive)")
    p.add_argument("to_block", type=int, help="End block (inclusive)")
    p.add_argument("--index", type=int, default=0, help="Event index to produce and verify a proof for (default 0)")
    return p.parse_args()

def main():
    args = parse_args()
    try:
        token = Web3.to_checksum_address(args.token)
    except Exception:
        print("❌ Invalid token address.")
        sys.exit(1)
    if args.to_block < args.from_block:
        print("❌ to_block must be >= from_block.")
        sys.exit(1)

    w3 = connect(RPC_URL)
    print(f"🌐 Connected to {network_name(w3.eth.chain_id)} (chainId {w3.eth.chain_id})")
    print(f"🧪 Token: {token}")
    print(f"🔢 Range: {args.from_block} .. {args.to_block}")

    t0 = time.time()
    logs = fetch_transfer_logs(w3, token, args.from_block, args.to_block)
    elapsed_fetch = time.time() - t0
    if not logs:
        print("ℹ️  No Transfer events found in the provided range.")
        sys.exit(0)

    print(f"📬 Events fetched: {len(logs)} in {elapsed_fetch:.2f}s")

    leaves = [build_event_leaf(l) for l in logs]
    tree = build_merkle_tree(leaves)
    root = merkle_root(tree)

    idx = args.index
    if idx < 0 or idx >= len(leaves):
        print("❌ --index out of range for fetched events.")
        sys.exit(1)

    leaf = leaves[idx]
    proof = merkle_proof(tree, idx)
    ok = verify_proof(leaf, proof, root)

    def h(x: bytes) -> str:
        return "0x" + x.hex()

    print("🌳 Merkle Root:", h(root))
    print(f"🍃 Proof target index: {idx}")
    print("🧾 Proof (sibling, position):")
    for d, (sib, pos) in enumerate(proof):
        print(f"  L{d}: sibling={h(sib)} position={pos}")
    print("🧩 Inclusion verifies root:", "✅ OK" if ok else "❌ FAIL")
    print(f"⏱️  Total time: {time.time() - t0:.2f}s")

if __name__ == "__main__":
    main()
