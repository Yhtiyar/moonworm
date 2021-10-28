from typing import Any, Callable, Dict, List, Optional, Tuple
import os


from eth_typing.evm import ChecksumAddress
from hexbytes.main import HexBytes
from web3 import Web3, eth
from web3.contract import Contract, ContractFunction
from web3.types import Nonce, TxParams, TxReceipt, Wei


def build_transaction(
    web3: Web3,
    builder: ContractFunction,
    sender: ChecksumAddress,
) -> Dict[str, Any]:
    """
    Builds transaction json with the given arguments. It is not submitting transaction
    Arguments:
    - web3: Web3 client
    - builder: ContractFunction or other class that has method buildTransaction(TxParams)
    - sender: `from` value of transaction, address which is sending this transaction
    - maxFeePerGas: Optional, max priority fee for dynamic fee transactions in Wei
    - maxPriorityFeePerGas: Optional the part of the fee that goes to the miner
    """
    transaction = builder.buildTransaction(
        {
            "from": sender,
            "nonce": get_nonce(web3, sender),
        }
    )
    return transaction


def get_nonce(web3: Web3, address: ChecksumAddress) -> Nonce:
    """
    Returns Nonce: number of transactions for given address
    """
    nonce = web3.eth.get_transaction_count(address)
    return nonce


def submit_transaction(
    web3: Web3, transaction: Dict[str, Any], signer_private_key: str
) -> HexBytes:
    """
    Signs and submits json transaction to blockchain from the name of signer
    """
    signed_transaction = web3.eth.account.sign_transaction(
        transaction, private_key=signer_private_key
    )
    return submit_signed_raw_transaction(web3, signed_transaction.rawTransaction)


def submit_signed_raw_transaction(
    web3: Web3, signed_raw_transaction: HexBytes
) -> HexBytes:
    """
    Submits already signed raw transaction.
    """
    transaction_hash = web3.eth.send_raw_transaction(signed_raw_transaction)
    return transaction_hash


def wait_for_transaction_receipt(web3: Web3, transaction_hash: HexBytes):
    return web3.eth.wait_for_transaction_receipt(transaction_hash)


def deploy_contract(
    web3: Web3,
    contract_bytecode: str,
    contract_abi: Dict[str, Any],
    deployer: ChecksumAddress,
    deployer_private_key: str,
    constructor_arguments: Optional[List[Any]] = None,
) -> ChecksumAddress:
    """
    Deploys smart contract to blockchain
    Arguments:
    - web3: web3 client
    - contract_bytecode: Compiled smart contract bytecode
    - contract_abi: Json abi of contract. Must include `constructor` function
    - deployer: Address which is deploying contract. Deployer will pay transaction fee
    - deployer_private_key: Private key of deployer. Needed for signing and submitting transaction
    - constructor_arguments: arguments that are passed to `constructor` function  of the smart contract
    """
    contract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
    transaction = build_transaction(
        web3, contract.constructor(*constructor_arguments), deployer
    )

    transaction_hash = submit_transaction(web3, transaction, deployer_private_key)
    transaction_receipt = wait_for_transaction_receipt(web3, transaction_hash)
    contract_address = transaction_receipt.contractAddress
    return web3.toChecksumAddress(contract_address)


def decode_transaction_input(web3: Web3, transaction_input: str, abi: Dict[str, Any]):
    contract = web3.eth.contract(abi=abi)
    return contract.decode_function_input(transaction_input)


def read_keys_from_cli() -> Tuple[ChecksumAddress, str]:
    raw_address = input("Enter your ethereum address:")
    private_key = input("Enter private key of your address:")
    return (Web3.toChecksumAddress(raw_address), private_key)


def read_keys_from_env() -> Tuple[ChecksumAddress, str]:
    raw_address = os.environ.get("CENTIPEDE_ETHEREUM_ADDRESS")
    if raw_address is None:
        raise ValueError("CENTIPEDE_ETHEREUM_ADDRESS is not set")
    private_key = os.environ.get("CENTIPEDE_ETHEREUM_ADDRESS_PRIVATE_KEY")
    if raw_address is None:
        raise ValueError("CENTIPEDE_ETHEREUM_ADDRESS_PRIVATE_KEY is not set")
    return (Web3.toChecksumAddress(raw_address), private_key)


def cast_to_python_type(evm_type: str) -> Callable:
    if evm_type.startswith(("uint", "int")):
        return int
    elif evm_type.startswith("bytes"):
        return bytes
    elif evm_type == "string":
        return str
    elif evm_type == "address":
        return Web3.toChecksumAddress
    elif evm_type == "bool":
        return bool
    else:
        raise ValueError(f"Cannot convert to python type {evm_type}")
