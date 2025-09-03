#!/bin/bash

# A simple script to deploy the generated contract using Forge.
# It uses the environment variables from your .env file.

# Load environment variables
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create one with RPC_URL and PRIVATE_KEY."
    exit 1
fi
set -a
source .env
set +a

# Run the deployment command
echo "Running Forge deployment command..."
forge create --broadcast \
    --rpc-url "$RPC_URL" \
    --private-key "$PRIVATE_KEY" \
    src/Create_product_recordRecord.sol:Create_product_recordRecord \
    --constructor-args 'PBA-001' 'Beautiful_Bali_Shirt' 40 true

# Check if the deployment was successful
if [ $? -ne 0 ]; then
    echo "Forge deployment failed."
    exit 1
fi

echo "Deployment of Create_product_recordRecord successful."
