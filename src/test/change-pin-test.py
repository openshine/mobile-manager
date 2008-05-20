import os
import sys
import gtk
import MobileManager.ui

class changepintest (MobileManager.ui.MobileChangePinDialog) :

    def __init__(self):
        controller = MobileManager.MobileController()
        dev = controller.get_active_device()
        dev.open_device("/dev/ttyUSB0")

        print dev.pin_status()
        status = dev.pin_status()
        if status == MobileManager.PIN_STATUS_READY or status == MobileManager.PIN_STATUS_WAITING_PUK:
            print "run dialog"
            MobileManager.ui.MobileChangePinDialog.__init__(self, controller)
            self.run ()
            return
        else :
            sys.exit()

if __name__ == '__main__':
    changepin = changepintest()
    gtk.main()
    
        
