from PyQt4.QtGui import QDialog

from ufwi_log.client.qt.ui.csvoption_ui import Ui_CSVOption

class CSVOption(QDialog):

    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.ui = Ui_CSVOption()
        self.ui.setupUi(self)

        self.rb_alldata = self.ui.rb_alldata
        self.rb_currentpage = self.ui.rb_currentpage

        self.rb_currentpage.setChecked(True)