# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import os
import sys
import threading

# by importing QT from sgtk rather than directly, we ensure that
# the code will be compatible with both PySide and PyQt.
from sgtk.platform.qt import QtCore, QtGui
from .ui.dialog import Ui_Dialog
from .model.seq_item_model import *
from .api import excel
from .api import publish

def show_dialog(app_instance):
    """
    Shows the main dialog window.
    """
    # in order to handle UIs seamlessly, each toolkit engine has methods for launching
    # different types of windows. By using these methods, your windows will be correctly
    # decorated and handled in a consistent fashion by the system. 
    
    # we pass the dialog class to this method and leave the actual construction
    # to be carried out by toolkit.
    app_instance.engine.show_dialog("IO Manager", app_instance, AppDialog)
    


class AppDialog(QtGui.QWidget):
    """
    Main application dialog window
    """
    
    def __init__(self):
        """
        Constructor
        """
        QtGui.QWidget.__init__(self)
        
        self.ui = Ui_Dialog() 
        self.ui.setupUi(self)
        
        self._app = sgtk.platform.current_bundle()



        self.ui.select_dir.clicked.connect(self._set_path)
        self.ui.create_excel.clicked.connect(self._create_excel)
        self.ui.save_excel.clicked.connect(self._save_excel)

        self.ui.publish.clicked.connect(self._publish)


    def _set_path(self):
        """
        Plate Path Select
        """
        file_dialog = ileName = QtGui.QFileDialog().getExistingDirectory(None, 
        'Output directory', 
        os.path.join(self._app.sgtk.project_path,'product','scan'))
        
        self.ui.lineEdit.setText(file_dialog)

        #excecl load ??
    def _create_excel(self):
        path = self.ui.lineEdit.text()
        excel_file = excel.ExcelWriteModel.get_last_excel_file(path)
        if excel_file:
            model = SeqTableModel(excel.ExcelWriteModel.read_excel(excel_file))
        else:
            model = SeqTableModel(excel.create_excel(path))

        self.ui.seq_model_view.setModel(model)
    

    def _save_excel(self):
        
        path = self.ui.lineEdit.text()
        excel_writer = excel.ExcelWriteModel(path)
        excel_writer.write_model_to_excel(self.ui.seq_model_view.model())
    
    def _publish(self):
        model = self.ui.seq_model_view.model()
        for row in range(0,model.rowCount(None)):
            publish.Publish(model,row)
