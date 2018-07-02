#!/usr/bin/env python

from time import sleep

def wait_for(condition, timeout=None):
    while True:
        try:
            result = condition()
            if result is None or result:
                break
        except:
            pass
        sleep(1)
