#! /bin/bash
# ensure hard exit on any failure
set -e
export PYTHONWARNINGS="ignore"
# Debug mode
if [ "$DEBUG" == "1" ];
then
    echo "Debugging..."
    while true; do echo "waiting" ; sleep 2; done
fi


cd agent



# a generalised function to generate a key to the agent
function generateKey() {
    if [ "$AEA_PASSWORD" != "" ];
    then
        echo "Generating key $1 with a password!"
        aea generate-key $1 --password $AEA_PASSWORD
    else
        echo "Generating key $1 without a password!"
        aea generate-key $1
    fi
}


# usage;
# generateKey cosmos


# a generalised function to check if an agent requires a key.
# if it does, it will generate it.

function checkKey() {
    export FILE=/agent_key/$(echo $1)_private_key.txt
    echo "Checking to see if $FILE exists"
    if [ -f "$FILE" ]; then
        echo "AEA key provided. Copying to agent."
        cp $FILE .
    else
        # we now check the dependecies, and generate keys we need, if not present.
        if grep open-aea-ledger-$1 aea-config.yaml -q
        then
            echo "AEA key not provided yet is required. Generating."
            generateKey $1
        fi
    fi
    addKey $1

}

# usage;
# checkKey cosmos


# a function to handle the case of the ethereum flashbots key, where we need to copy the ethereum key
# to the ethereum flashbots key.
function handleFlashbotsKey() {
    if grep "open-aea-ledger-ethereum-flashbots" aea-config.yaml -q
    then
        echo "Copying ethereum key to ethereum flashbots key"
        cp ethereum_private_key.txt ethereum_flashbots_private_key.txt
    fi
}

# usage;
# handleFlashbotsKey

# a specialist function to handle the case of the cosmos *connection* key, where we need to generate it for the libp2p connection.
function handleCosmosConnectionKeyAndCerts() {
    echo "Generating cosmos key for libp2p connection"
    # we generate a cosmos key should it not exist.
    if [ ! -f "cosmos_private_key.txt" ]; then
        generateKey cosmos
    fi
    aea add-key cosmos --connection 
    aea issue-certificates
}

# usage;
# handleCosmosConnectionKey

function runAgent() {
    if [[ "$AEA_PASSWORD" != "" ]];
    then
        aea run --password $AEA_PASSWORD
    else
        aea run
    fi

}


function addKey() {
    # we check if the private key file exists, and if it does, we add it to the agent.
    FILE=$(echo $1)_private_key.txt
    if [ -f "$FILE" ]; then
        echo "$1 key provided. Adding to agent."
        if [[ "$AEA_PASSWORD" != "" ]];
        then
            aea add-key $1 --password $AEA_PASSWORD
        else
            aea add-key $1
        fi
    fi
}


# usage;
# runAgent


function main() {
    echo "Running the aea with $(aea --version)"
    echo "Checking keys"

    checkKey ethereum
    checkKey cosmos
    checkKey solana

    # autonomy specific functions

    echo "Checking autonomy specific connection keys"

    handleFlashbotsKey
    handleCosmosConnectionKeyAndCerts

    echo "Running the aea"
    runAgent

}

# usage;
# main

main
