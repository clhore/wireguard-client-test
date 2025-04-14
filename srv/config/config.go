package config

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
)

type Peer struct {
	PublicKey  string   `json:"public_key"`
	Endpoint   string   `json:"endpoint"`
	AllowedIPs []string `json:"allowed_ips"`
}

type WireGuardInterface struct {
	PrivateKey string `json:"private_key"`
	Endpoint   string `json:"endpoint"`
	IPAddress  string `json:"ip_address"`
	Peers      []Peer `json:"peers"`
}

type Config struct {
	Interfaces map[string]WireGuardInterface `json:"wireguard_interfaces"`
}

func LoadConfig(filename string) (Config, error) {
	data, err := ioutil.ReadFile(filename)
	if err != nil {
		return Config{}, fmt.Errorf("error reading configuration file: %v", err)
	}

	var config Config
	err = json.Unmarshal(data, &config)
	if err != nil {
		return Config{}, fmt.Errorf("error parsing configuration file: %v", err)
	}

	return config, nil
}
