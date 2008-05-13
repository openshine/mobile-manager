import os
import sys
import gtk
import MobileManager.ui

class puktest  (MobileManager.ui.MobilePukDialog) :

    def __init__(self):
        controller = MobileManager.MobileController()
        dev = controller.get_active_device()
        dev.open_device("/dev/ttyUSB0")
        
        print dev.pin_status()
        if dev.pin_status() == MobileManager.PIN_STATUS_READY :
            print "eject your mobile device and insert again"
            sys.exit()
            return

        print dev.pin_status()
        while dev.pin_status() == MobileManager.PIN_STATUS_WAITING_PIN :
            print "send false pin"
            dev.send_pin("0001")

        print dev.pin_status()
        if dev.pin_status() == MobileManager.PIN_STATUS_WAITING_PUK :
            print "run dialog"
            MobileManager.ui.MobilePukDialog.__init__(self, controller)
            self.run ()
            return

        sys.exit()

if __name__ == '__main__':
    puk = puktest()
    gtk.main()
    
        
