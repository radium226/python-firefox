#!/usr/bin/env python

ef wait_for(condition):
    while True:
        try:
            result = condition()
            if result is None or result:
                break
        except:
            pass
        sleep(1)
