from PyQt4.QtGui import QDialog

from ufwi_log.client.qt.ui.autorefresh_ui import Ui_Dialog


class AutorefreshDialog(QDialog):

    def __init__(self, auto_refresh, parent=None):
        QDialog.__init__(self, parent)
    
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.cb_autorefresh = self.ui.cb_autorefresh
        self.te_seconds = self.ui.te_seconds

        self.cb_autorefresh.setChecked(auto_refresh)
        
