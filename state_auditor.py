'''
evm-state-auditor-py
Compares JSON-RPC responses for a set of addresses across two blocks,
producing a compact anomaly report (nonce/balance/code/storage slots).
Usage:
  RPC=https://eth.drpc.org python3 state_auditor.py 17000000 17050000 0xabc.. 0xdef..
'''
import os, sys, json
from web3 import Web3

RPC = os.getenv("RPC", "https://eth.drpc.org")
SLOTS = [0, 1, 2]  # light sampling of storage slots

def wei_to_eth(v: int) -> float:
    return float(v) / 1e18

def get_account_view(w3: Web3, addr: str, block: int):
    balance = w3.eth.get_balance(addr, block_identifier=block)
    nonce = w3.eth.get_transaction_count(addr, block_identifier=block)
    code = w3.eth.get_code(addr, block_identifier=block).hex()
    storage = {}
    for slot in SLOTS:
        storage[str(slot)] = w3.eth.get_storage_at(addr, slot, block_identifier=block).hex()
    return {"balance": balance, "nonce": nonce, "code": code, "storage": storage}

def main():
    if len(sys.argv) < 4:
        print("Usage: state_auditor.py <blockA> <blockB> <addr1> [addr2 ...]")
        sys.exit(1)

    blockA = int(sys.argv[1]); blockB = int(sys.argv[2]); addrs = [Web3.to_checksum_address(a) for a in sys.argv[3:]]
    w3 = Web3(Web3.HTTPProvider(RPC))
    if not w3.is_connected():
        print("RPC not reachable:", RPC); sys.exit(2)

    report = {"rpc": RPC, "blockA": blockA, "blockB": blockB, "results": []}

    for a in addrs:
        aA = get_account_view(w3, a, blockA)
        aB = get_account_view(w3, a, blockB)

        diff = {}
        if aA["nonce"] != aB["nonce"]:
            diff["nonce"] = [aA["nonce"], aB["nonce"]]
        if aA["balance"] != aB["balance"]:
            diff["balance_eth"] = [round(wei_to_eth(aA["balance"]),6), round(wei_to_eth(aB["balance"]),6)]
        if aA["code"] != aB["code"]:
            diff["codeChanged"] = True
        slot_changes = {k:[aA["storage"][k], aB["storage"][k]] for k in aA["storage"] if aA["storage"][k] != aB["storage"][k]}
        if slot_changes:
            diff["slots"] = slot_changes

        report["results"].append({"address": a, "diff": diff})

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
