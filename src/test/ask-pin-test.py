import os
import sys
import gtk
import MobileManager.ui

class askpintest (MobileManager.ui.MobileAskPinDialog) :

    def __init__(self):
        controller = MobileManager.MobileController()
        dev = controller.get_active_device()
        dev.open_device()
        
        print dev.pin_status()
        if dev.pin_status() == MobileManager.PIN_STATUS_READY :
            print "eject your mobile device and insert again"
            sys.exit()
            return

        print dev.pin_status()
        status = dev.pin_status()
        if status == MobileManager.PIN_STATUS_WAITING_PIN or status == MobileManager.PIN_STATUS_WAITING_PUK:
            print "run dialog"
            MobileManager.ui.MobileAskPinDialog.__init__(self, controller)
            self.run ()
            return
        else :
            sys.exit()

if __name__ == '__main__':
    askpin = askpintest()
    gtk.main()
    
        
