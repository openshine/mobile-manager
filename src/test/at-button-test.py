import MobileManager.ui
import gtk

mcontroller = MobileManager.MobileController()
dev = mcontroller.get_active_device()
dev.open_device()
ob = MobileManager.ui.MobileATOptionsButton(mcontroller)
ob.set_label("Options")
win = gtk.Window()
win.add(ob)
win.show()
ob.show()

gtk.main()

dev.close_device()
