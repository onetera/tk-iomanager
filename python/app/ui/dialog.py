# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dialog.ui'
#
# Created: Tue Oct 15 18:18:14 2019
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from tank.platform.qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1044, 685)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.lineEdit = QtGui.QLineEdit(Dialog)
        self.lineEdit.setObjectName("lineEdit")
        self.horizontalLayout_2.addWidget(self.lineEdit)
        self.select_dir = QtGui.QPushButton(Dialog)
        self.select_dir.setObjectName("select_dir")
        self.horizontalLayout_2.addWidget(self.select_dir)
        self.create_excel = QtGui.QPushButton(Dialog)
        self.create_excel.setObjectName("create_excel")
        self.horizontalLayout_2.addWidget(self.create_excel)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.check_all_btn = QtGui.QPushButton(Dialog)
        self.check_all_btn.setObjectName("check_all_btn")
        self.horizontalLayout_3.addWidget(self.check_all_btn)
        self.uncheck_all_btn = QtGui.QPushButton(Dialog)
        self.uncheck_all_btn.setObjectName("uncheck_all_btn")
        self.horizontalLayout_3.addWidget(self.uncheck_all_btn)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.seq_model_view = QtGui.QTableView(Dialog)
        self.seq_model_view.setObjectName("seq_model_view")
        self.verticalLayout.addWidget(self.seq_model_view)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.excel_file_label = QtGui.QLabel(Dialog)
        self.excel_file_label.setMinimumSize(QtCore.QSize(200, 0))
        self.excel_file_label.setText("")
        self.excel_file_label.setObjectName("excel_file_label")
        self.horizontalLayout.addWidget(self.excel_file_label)
        self.edit_excel = QtGui.QPushButton(Dialog)
        self.edit_excel.setObjectName("edit_excel")
        self.horizontalLayout.addWidget(self.edit_excel)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.validate_excel = QtGui.QPushButton(Dialog)
        self.validate_excel.setObjectName("validate_excel")
        self.horizontalLayout.addWidget(self.validate_excel)
        self.save_excel = QtGui.QPushButton(Dialog)
        self.save_excel.setObjectName("save_excel")
        self.horizontalLayout.addWidget(self.save_excel)
        self.publish = QtGui.QPushButton(Dialog)
        self.publish.setObjectName("publish")
        self.horizontalLayout.addWidget(self.publish)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "The Current Sgtk Environment", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Path : ", None, QtGui.QApplication.UnicodeUTF8))
        self.select_dir.setText(QtGui.QApplication.translate("Dialog", "Select", None, QtGui.QApplication.UnicodeUTF8))
        self.create_excel.setText(QtGui.QApplication.translate("Dialog", "Load", None, QtGui.QApplication.UnicodeUTF8))
        self.check_all_btn.setText(QtGui.QApplication.translate("Dialog", "Check All", None, QtGui.QApplication.UnicodeUTF8))
        self.uncheck_all_btn.setText(QtGui.QApplication.translate("Dialog", "Uncheck All", None, QtGui.QApplication.UnicodeUTF8))
        self.edit_excel.setText(QtGui.QApplication.translate("Dialog", "Edit", None, QtGui.QApplication.UnicodeUTF8))
        self.validate_excel.setText(QtGui.QApplication.translate("Dialog", "Validate", None, QtGui.QApplication.UnicodeUTF8))
        self.save_excel.setText(QtGui.QApplication.translate("Dialog", "Save", None, QtGui.QApplication.UnicodeUTF8))
        self.publish.setText(QtGui.QApplication.translate("Dialog", "Publish", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
