#!/bin/bash
# A simple script to deploy the generated contract using Forge.
# Ensure your .env file has RPC_URL and PRIVATE_KEY configured.

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create one with RPC_URL and PRIVATE_KEY."
    exit 1
fi
set -a
source .env
set +a

echo "Compiling contract Create_product_recordRecord.sol..."
forge build
if [ $? -ne 0 ]; then
    echo "Forge build failed. Aborting deployment."
    exit 1
fi

echo "Deploying Create_product_recordRecord with constructor arguments: 'onetwothree' 'verified' 111 true"
forge create src/Create_product_recordRecord.sol:Create_product_recordRecord \
    --broadcast \
    --rpc-url "$RPC_URL" \
    --private-key "$PRIVATE_KEY" \
    --constructor-args 'onetwothree' 'verified' 111 true
if [ $? -ne 0 ]; then
    echo "Forge deployment failed."
    exit 1
fi
echo "Deployment of Create_product_recordRecord successful."
