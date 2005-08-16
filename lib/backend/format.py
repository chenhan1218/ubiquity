#!/usr/bin/python


def format_target(self, mountpoints):
    '''format_target(mountpoints) -> bool

    From mountpoints extract the devices to partition 
    and do it.
    The method return true or false depends the result
    of this operation.
    '''
    for path, device in mountpoints.items():
        if path in ['/']:
            try:
                self.ex('mkfs.ext3','device')
            except:
                return False
        elif path == 'swap':
            try:
                self.ex('mkswap','device')
            except:
                return False
    return True



# vim:ai:et:sts=2:tw=80:sw=2:
