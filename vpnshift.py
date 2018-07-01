#!/bin/env python

from socket import AF_INET
from pyroute2 import IPRoute, netns
import subprocess as sp
import getpass
from pathlib import Path
import ipgetter
import argparse as ap
import sys
from time import sleep

NETWORK_NAMESPACE = "toto"
VETH_VPN = "veth_vpn"
VETH_DEFAULT="veth_default"
FOLDER_PATH = Path(f"/etc/netns/{NETWORK_NAMESPACE}")
OPENVPN_TUNNEL = "tunvpn"

class Country:

    def __init__(self, openvpn_config_file_name):
        self.openvpn_config_file_name = openvpn_config_file_name

    @classmethod
    def sweden(cls):
        return cls(Path("Sweden.conf"))

class OpenVPN:

    def __init__(self, process):
        self.process = process

    @classmethod
    def start(cls, country, network_namespace=None):
        config_file_path = Path("/etc/openvpn/client") / country.openvpn_config_file_name
        command = [
            "openvpn",
                "--cd", str(Path("/etc/openvpn/client")),
                "--config", str(config_file_path),
                "--dev", OPENVPN_TUNNEL,
                "--errors-to-stderr"
        ]
        process = execute(command, sudo=True, network_namespace=network_namespace, background=True)
        return OpenVPN(process)

    def stop(self):
        self.process.kill()

class IPInfo:

    def __init__(self, ip):
        self.ip = ip

    @classmethod
    def for_http(cls):
        ip = ipgetter.myip()
        return cls(ip)

    def __str__(self):
        return f"IPInfo(ip={self.ip})"

def execute(command, success_exit_codes=[0], sudo=False, network_namespace=None, background=False, stdin=None, stdout=None):
    before_command = []
    if network_namespace:
        user = getpass.getuser()
        before_command = ["sudo", "-E", "ip", "netns", "exec", network_namespace, "sudo", "-E", "-u", user]

    if sudo:
        before_command = before_command + ["sudo", "-E"]

    process = sp.Popen(before_command + command, stdin=stdin, stdout=stdout, start_new_session=True)
    if background:
        return process
    else:
        process.wait()
        exit_code = process.returncode
        if exit_code not in success_exit_codes:
            raise Exception(f"The {before_command + command} process failed! ")

def check_ip_action(arguments):
    ip_info = IPInfo.for_http()
    print(ip_info)

def to_command_argument(arguments):
    return [arguments.action]

def setup_network_namespace():
    execute(["ip", "netns", "add", NETWORK_NAMESPACE], sudo=True)
    FOLDER_PATH.mkdir(parents=True, exist_ok=True)

    # Loopback
    execute(["ip", "address", "add", "127.0.0.1/8", "dev", "lo"], sudo=True, network_namespace=NETWORK_NAMESPACE)
    execute(["ip", "address", "add", "::1/128", "dev", "lo"], sudo=True, network_namespace=NETWORK_NAMESPACE)
    execute(["ip", "link", "set", "lo", "up"], sudo=True, network_namespace=NETWORK_NAMESPACE)

    # Tunnel
    execute(["ip", "link", "add", VETH_VPN, "type", "veth", "peer", "name", VETH_DEFAULT], sudo=True)
    execute(["ip", "link", "set", VETH_VPN, "netns", NETWORK_NAMESPACE], sudo=True)

    execute(["ip", "link", "set", VETH_DEFAULT, "up"], sudo=True)
    execute(["ip", "link", "set", VETH_VPN, "up"], sudo=True, network_namespace=NETWORK_NAMESPACE)

    execute(["ip", "address", "add", "10.10.10.10/31", "dev", VETH_DEFAULT], sudo=True)
    execute(["ip", "address", "add", "10.10.10.11/31", "dev", VETH_VPN], sudo=True, network_namespace=NETWORK_NAMESPACE)

    execute(["ip", "route", "add", "default", "via", "10.10.10.10", "dev", VETH_VPN], sudo=True, network_namespace=NETWORK_NAMESPACE)

    execute(["sysctl", "--quiet", "net.ipv4.ip_forward=1"], sudo=True)
    execute(["iptables", "--table", "nat", "--append", "POSTROUTING", "--jump", "MASQUERADE", "--source", "10.10.10.10/31"], sudo=True)


    with (FOLDER_PATH / "resolv.conf").open("w") as f:
        content = f"""nameserver 108.62.19.131
nameserver 104.238.194
"""
        f.write(content)



if __name__ == "__main__":
    parser = ap.ArgumentParser()
    parser.add_argument("--netns")
    subparsers = parser.add_subparsers(dest="action")
    ping_parser = subparsers.add_parser("check-ip")
    #ping_parser.add_argument("host")

    arguments = parser.parse_args()
    if arguments.netns:
        script_file_path = sys.argv[0]
        setup_network_namespace()
        openvpn = OpenVPN.start(Country.sweden(), network_namespace=arguments.netns)
        sleep(20)
        execute([script_file_path] + to_command_argument(arguments), network_namespace=arguments.netns)
        sleep(5)
        openvpn.stop()
    else:
        actions = {
            "check-ip": check_ip_action
        }
        actions[arguments.action](arguments)
