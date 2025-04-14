package main

import (
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"

	"github.com/clhore/wireguard-client/config"
	"github.com/clhore/wireguard-packages/wgconf"
)

/*
1 reference
Los objetos Peer devueltos tienen los siguientes atributos:

PublicKey - Clave pública del par.
PresharedKey - Clave precompartida opcional para seguridad adicional.
Endpoint - Dirección de origen más reciente utilizada para la comunicación.
PersistentKeepaliveInterval - Intervalo de keepalive persistente.
LastHandshakeTime - Última vez que se realizó un handshake con este par.
ReceiveBytes - Número de bytes recibidos de este par.
TransmitBytes - Número de bytes transmitidos a este par.
AllowedIPs - Direcciones IP permitidas para la comunicación.
ProtocolVersion - Versión del protocolo WireGuard utilizada.
*/

func main() {
	fmt.Printf("Load config\n")
	configPath := os.Args[1]
	config, err := config.LoadConfig(configPath)

	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	for name, intf := range config.Interfaces {
		fmt.Println("---------- Datos de WireGuard ----------")
		printWireGuardInterface(name, intf)
		fmt.Print(setupWireGuardInterface(name, intf))
		fmt.Println("------------------------------------------")
	}
}

func printWireGuardInterface(name string, intf config.WireGuardInterface) error {
	fmt.Printf("Setting up WireGuard interface: %s\n", name)
	fmt.Printf("Private Key: %s\n", intf.PrivateKey)
	fmt.Printf("Endpoint: %s\n", intf.Endpoint)
	fmt.Printf("IP Address: %s\n", intf.IPAddress)

	for _, peer := range intf.Peers {
		fmt.Printf("Peer Public Key: %s\n", peer.PublicKey)
		fmt.Printf("Peer Endpoint: %s\n", peer.Endpoint)
		fmt.Printf("Allowed IPs: %v\n", peer.AllowedIPs)
	}

	return nil
}

func setupWireGuardInterface(name string, intf config.WireGuardInterface) error {
	parts := strings.Split(intf.IPAddress, "/")
	ip, maskStr := parts[0], parts[1]

	mask, err := strconv.Atoi(maskStr)
	if err != nil {
		return fmt.Errorf("error converting mask to integer: %v", err)
	}

	portStr := strings.Split(intf.Endpoint, ":")[1]
	port, err := strconv.Atoi(portStr)
	if err != nil {
		return fmt.Errorf("error converting port to integer: %v", err)
	}

	address := wgconf.IPAddrAndMac{IpAddr: ip, MaskAddr: mask}

	wg, err := wgconf.NewWireGuardTrun(
		wgconf.WithInterfaceName(name), wgconf.WithInterfaceIp(address), wgconf.WithListenPort(port),
		wgconf.WithPrivateKey(intf.PrivateKey),
	)
	if err != nil {
		fmt.Println("Error initializing WireGuardTrun:", err)
		return err
	}
	err = wg.CreateInterface()
	if err != nil {
		fmt.Println("Error creating interface:", err)
		return err
	}

	for _, peer := range intf.Peers {
		fmt.Printf("Peer Public Key: %s\n", peer.PublicKey)
		fmt.Printf("Peer Endpoint: %s\n", peer.Endpoint)
		fmt.Printf("Allowed IPs: %v\n", peer.AllowedIPs)

		newPeer := wgconf.Peer{
			PublicKey:  peer.PublicKey,
			AllowedIPs: peer.AllowedIPs,
			Endpoint:   wgconf.Endpoint{},
			KeepAlive:  25,
		}

		if peer.Endpoint != "" {
			parts = strings.Split(peer.Endpoint, ":")
			ip, portStr := parts[0], parts[1]

			port, err := strconv.Atoi(portStr)
			if err != nil {
				return fmt.Errorf("error converting port to integer: %v", err)
			}

			endpoint := wgconf.Endpoint{Host: ip, Port: port}
			newPeer.Endpoint = endpoint
		}

		wg.AddPeer(newPeer)
		err = wg.UpdateConfigInterfaceWgTrun()
		if err != nil {
			return fmt.Errorf("error add peer: %v", err)
		}
	}

	return nil
}
