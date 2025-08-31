#!/usr/bin/env python3
"""
Substrate deployment integration for the Blockchain Supply Chain scanner
"""

import json
import asyncio
from substrateinterface import SubstrateInterface, Keypair, KeypairType
from substrateinterface.contracts import ContractInstance, ContractCode
import hashlib
import os

class SubstrateDeployment:
    def __init__(self, substrate_url="ws://127.0.0.1:9944"):
        """Initialize connection to Substrate node"""
        self.substrate_url = substrate_url
        self.substrate = None
        self.contract_address = None
        self.keypair = None

    def connect(self):
        """Connect to Substrate node"""
        try:
            self.substrate = SubstrateInterface(url=self.substrate_url)
            print(f"Connected to Substrate node at {self.substrate_url}")
            return True
        except Exception as e:
            print(f"Failed to connect to Substrate: {e}")
            return False

    def setup_keypair(self, mnemonic=None):
        """Setup or generate a keypair for transactions"""
        if mnemonic:
            self.keypair = Keypair.create_from_mnemonic(mnemonic, ss58_format=42)
        else:
            # Generate a new keypair (for testing)
            self.keypair = Keypair.create_from_mnemonic(
                Keypair.generate_mnemonic(), ss58_format=42
            )

        print(f"Using account: {self.keypair.ss58_address}")
        return self.keypair.ss58_address

    def load_contract_metadata(self, metadata_path):
        """Load contract ABI metadata"""
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            return metadata
        except FileNotFoundError:
            print(f"Contract metadata not found at {metadata_path}")
            return None

    def deploy_contract(self, wasm_path, metadata_path):
        """Deploy the dynamic contract to Substrate"""
        if not self.substrate or not self.keypair:
            raise Exception("Not connected to Substrate or no keypair set")

        # Load contract code and metadata
        try:
            with open(wasm_path, 'rb') as f:
                wasm_code = f.read()

            metadata = self.load_contract_metadata(metadata_path)
            if not metadata:
                raise Exception("Could not load contract metadata")

            # Deploy contract
            contract_code = ContractCode.create_from_contract_files(
                metadata_file=metadata_path,
                wasm_file=wasm_path,
                substrate=self.substrate
            )

            # Instantiate contract
            contract = contract_code.deploy(
                keypair=self.keypair,
                constructor="new",
                args=[],
                gas_limit={"ref_time": 25990000000, "proof_size": 119903},
                value=0
            )

            self.contract_address = contract.contract_address
            print(f"Contract deployed at: {self.contract_address}")
            return contract

        except Exception as e:
            print(f"Contract deployment failed: {e}")
            return None

    def deploy_function(self, contract_instance, function_data):
        """Deploy a Python function to the substrate contract"""
        if not contract_instance:
            raise Exception("No contract instance available")

        try:
            # Extract function information
            name = function_data.get('functionName', 'unknown')
            source_file = function_data.get('file', 'unknown.py')
            class_name = function_data.get('className')

            # Get the actual Python code (you'll need to read this from the file)
            python_code = self.extract_function_code(function_data)

            # Analyze function parameters (simplified)
            parameters = self.extract_parameters(python_code)
            return_type = self.extract_return_type(python_code)

            # Call the contract's deploy_function method
            receipt = contract_instance.exec(
                keypair=self.keypair,
                method="deploy_function",
                args=[
                    name,
                    source_file,
                    class_name,
                    parameters,
                    return_type,
                    python_code
                ],
                gas_limit={"ref_time": 25990000000, "proof_size": 119903}
            )

            if receipt.is_success:
                print(f"Function '{name}' deployed successfully")
                # Extract function ID from events
                function_id = self.extract_function_id_from_receipt(receipt)
                return {
                    'success': True,
                    'function_id': function_id,
                    'transaction_hash': receipt.extrinsic_hash,
                    'name': name
                }
            else:
                print(f"Function deployment failed: {receipt.error_message}")
                return {
                    'success': False,
                    'error': receipt.error_message
                }

        except Exception as e:
            print(f"Error deploying function: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def execute_function(self, contract_instance, function_id, parameters):
        """Execute a deployed function"""
        try:
            receipt = contract_instance.exec(
                keypair=self.keypair,
                method="execute_function",
                args=[function_id, parameters],
                gas_limit={"ref_time": 25990000000, "proof_size": 119903}
            )

            if receipt.is_success:
                # Get result from contract
                result = contract_instance.read(
                    keypair=self.keypair,
                    method="get_result",
                    args=[function_id]
                )

                return {
                    'success': True,
                    'result': result.contract_result_data,
                    'transaction_hash': receipt.extrinsic_hash
                }
            else:
                return {
                    'success': False,
                    'error': receipt.error_message
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def list_deployed_functions(self, contract_instance):
        """Get list of all deployed functions"""
        try:
            result = contract_instance.read(
                keypair=self.keypair,
                method="list_functions",
                args=[]
            )

            return {
                'success': True,
                'functions': result.contract_result_data
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def extract_function_code(self, function_data):
        """Extract the actual Python function code from the file"""
        # This is a simplified version - you'd want to use AST parsing
        # to extract the exact function definition
        file_path = function_data.get('file', '')
        function_name = function_data.get('functionName', '')
        class_name = function_data.get('className')

        # For now, return a placeholder
        # In a real implementation, you'd parse the AST and extract the function
        if class_name:
            return f"# Method {class_name}.{function_name} from {file_path}\n# Code would be extracted here"
        else:
            return f"# Function {function_name} from {file_path}\n# Code would be extracted here"

    def extract_parameters(self, code):
        """Extract function parameters from code"""
        # Simplified parameter extraction
        # In a real implementation, use AST parsing
        return ["param1", "param2"]  # Placeholder

    def extract_return_type(self, code):
        """Extract return type from function code"""
        # Simplified return type extraction
        return "Any"  # Placeholder

    def extract_function_id_from_receipt(self, receipt):
        """Extract deployed function ID from transaction receipt"""
        # Parse events from receipt to get function ID
        # This is substrate-specific event parsing
        try:
            for event in receipt.triggered_events:
                if event.value['event']['event_id'] == 'FunctionDeployed':
                    return event.value['event']['attributes']['function_id']
        except:
            pass
        return 1  # Fallback

    def get_balance(self, address=None):
        """Get account balance"""
        if not address:
            address = self.keypair.ss58_address if self.keypair else None

        if not address:
            return None

        try:
            balance = self.substrate.query('System', 'Account', [address])
            return balance.value['data']['free']
        except Exception as e:
            print(f"Error getting balance: {e}")
            return None

# Test deployment class
class MockSubstrateDeployment(SubstrateDeployment):
    """Mock deployment for testing without actual Substrate node"""

    def __init__(self):
        self.deployed_functions = []
        self.function_counter = 0

    def connect(self):
        print("Mock: Connected to Substrate node")
        return True

    def setup_keypair(self, mnemonic=None):
        print("Mock: Keypair setup complete")
        return "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"  # Mock address

    def deploy_contract(self, wasm_path=None, metadata_path=None):
        print("Mock: Contract deployed successfully")
        return True

    def deploy_function(self, contract_instance, function_data):
        self.function_counter += 1

        deployed_function = {
            'function_id': self.function_counter,
            'name': function_data.get('functionName', 'unknown'),
            'file': function_data.get('file', ''),
            'className': function_data.get('className'),
            'transaction_hash': f"0x{hashlib.md5(str(self.function_counter).encode()).hexdigest()}"
        }

        self.deployed_functions.append(deployed_function)

        return {
            'success': True,
            'function_id': self.function_counter,
            'transaction_hash': deployed_function['transaction_hash'],
            'name': deployed_function['name']
        }

    def list_deployed_functions(self, contract_instance=None):
        return {
            'success': True,
            'functions': [(f['function_id'], f['name'], f['className'])
                         for f in self.deployed_functions]
        }
