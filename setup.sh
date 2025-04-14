#!/bin/bash

function create_wg_keys(){ wg genkey | tee "${1}_privatekey" | wg pubkey > "${1}_publickey"; }


function create_default_config()
{
    local DEFAULT_INTERFACE="wg0"

    create_wg_keys "$DEFAULT_INTERFACE"
    WG_PRIVATE_KEY="$(cat ${DEFAULT_INTERFACE}_privatekey)"
    
    cat <<EOF > "$CONFIG_FILE"
{
    "wireguard_interfaces": {
      "wg0": {
        "private_key": "$WG_PRIVATE_KEY",
        "endpoint": "0.0.0.0:51820",
        "ip_address": "10.7.0.1/24",
        "peers": []
      }
    }
} 
EOF
}

: "${CONFIG_FILE:=/etc/wireguard/config.json}"

printf "Check config file [${CONFIG_FILE}]"
[ -f "$CONFIG_FILE" ] || {
    printf "[x] Config file not found [$CONFIG_FILE]\n"
    printf ":: Creating a default config [$CONFIG_FILE]\n"
    create_default_config
}

echo ":: Using config file: $CONFIG_FILE"
./wireguard-client "$CONFIG_FILE"

sleep infinity