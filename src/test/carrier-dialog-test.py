import os
import sys
import gtk
import MobileManager.ui

class carrierdialogtest (MobileManager.ui.MobileCarrierSelectorDialog) :

    def __init__(self):
        controller = MobileManager.MobileController()
        dev = controller.get_active_device()
        dev.open_device()
        
        print dev.pin_status()
        if dev.pin_status() != MobileManager.PIN_STATUS_READY :
            print "pin not ready !!"
            sys.exit()
            return

        MobileManager.ui.MobileCarrierSelectorDialog.__init__(self, controller)

if __name__ == '__main__':
    carrierdialog = carrierdialogtest()
    gtk.main()
    
        
