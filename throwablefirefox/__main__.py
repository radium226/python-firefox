#!/usr/bin/env python

from throwablefirefox.firefox import Firefox, Profile
from throwablefirefox.networknamespace import NetworkNamespace
from throwablefirefox.openvpn import OpenVPN

if __name__ == "__main__":
    with NetworkNamespace(name="toto") as network_namespace:
        with OpenVPN(network_namespace=network_namespace, country="Sweden"):
            with Profile.throwable(network_namespace=network_namespace) as profile:
                firefox = Firefox.start(profile, private=True)
                firefox.wait()
