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
import subprocess

# by importing QT from sgtk rather than directly, we ensure that
# the code will be compatible with both PySide and PyQt.
from sgtk.platform.qt import QtCore, QtGui
from .ui.dialog import Ui_Dialog
from .model.seq_item_model import *
from .api import excel
from .api import publish
from .api import collect
from .api import validate
from .api.constant import *


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

        self.ui.colorspace_combo.addItems(COLORSPACE)
        self._set_colorspace()
        self.ui.select_dir.clicked.connect(self._set_path)
        self.ui.create_excel.clicked.connect(self._create_excel)
        self.ui.save_excel.clicked.connect(self._save_excel)

        self.ui.publish.clicked.connect(self._publish)
        self.ui.collect.clicked.connect(self._collect)
        self.ui.check_all_btn.clicked.connect(self._check_all)
        self.ui.uncheck_all_btn.clicked.connect(self._uncheck_all)
        self.ui.edit_excel.clicked.connect(self._open_excel)
        # self.ui.validate_excel.clicked.connect(self._validate)
        self.ui.v_timecode.clicked.connect(lambda: self._validate("timecode"))
        self.ui.v_org.clicked.connect(lambda: self._validate("org"))
        self.ui.v_src.clicked.connect(lambda: self._validate("src"))
        self.ui.v_editor.clicked.connect(lambda: self._validate("editor"))
        self.ui.edit_excel.setEnabled(False)

    def _set_colorspace(self):
        context = self._app.context
        project = context.project
        shotgun = self._app.sgtk.shotgun

        output_info = shotgun.find_one("Project", [['id', 'is', project['id']]],
                                       ['sg_colorspace', 'sg_mov_codec',
                                        'sg_out_format', 'sg_fps', 'sg_mov_colorspace'])
        colorspace = output_info['sg_colorspace']
        if not colorspace.find("ACES") == -1:
            colorspace = "ACES - " + colorspace

        print colorspace
        self.ui.colorspace_combo.setCurrentIndex(
            self.ui.colorspace_combo.findText(colorspace))

    def _validate(self, command):

        model = self.ui.seq_model_view.model()
        v = validate.Validate(model)
        if command == "timecode":
            v.timecode()
        if command == "org":
            v.uploade_status()
        if command == "src":
            v.check_src_version()
        if command == "editor":
            v.check_editor_shot()
        # self._save_excel()

    def _open_excel(self):
        excel_file = self.ui.excel_file_label.text()
        # command = ['libreoffice5.4','--calc','--nologo']
        command = ['et']
        command.append(excel_file)
        subprocess.Popen(command)

    def _check_all(self):

        model = self.ui.seq_model_view.model()
        if model:
            for row in range(0, model.rowCount(None)):
                index = model.createIndex(row, 0)
                model.setData(index, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole)

    def _uncheck_all(self):

        model = self.ui.seq_model_view.model()
        if model:
            for row in range(0, model.rowCount(None)):
                index = model.createIndex(row, 0)
                model.setData(index, QtCore.Qt.Unchecked, QtCore.Qt.CheckStateRole)

    def _set_timecode(self, index):

        row = index.row()
        column = index.column()
        if column == MODEL_KEYS['just_in']:
            timecode_col = MODEL_KEYS['timecode_in']

        elif column == MODEL_KEYS['just_out']:
            timecode_col = MODEL_KEYS['timecode_out']
        else:
            return

        model = self.ui.seq_model_view.model()

        frame = int(model.data(index, QtCore.Qt.DisplayRole))

        index = model.createIndex(row, MODEL_KEYS["scan_path"])
        dir_name = model.data(index, QtCore.Qt.DisplayRole)

        index = model.createIndex(row, MODEL_KEYS['scan_name'])
        head = model.data(index, QtCore.Qt.DisplayRole)

        index = model.createIndex(row, MODEL_KEYS['pad'])
        frame_format = model.data(index, QtCore.Qt.DisplayRole)

        index = model.createIndex(row, MODEL_KEYS['ext'])
        tail = model.data(index, QtCore.Qt.DisplayRole)

        time_code = excel.get_time_code(dir_name, head, frame_format, frame, tail)

        index = model.createIndex(row, timecode_col)
        model.setData(index, time_code, 3)

    def _set_index_by_timecode(self, index):

        row = index.row()
        column = index.column()
        if not column in [16, 17]:
            return

    def _set_path(self):
        """
        Plate Path Select
        """
        file_dialog = QtGui.QFileDialog().getExistingDirectory(None,
                                                               'Output directory',
                                                               os.path.join(self._app.sgtk.project_path, 'product',
                                                                            'scan'))

        self.ui.lineEdit.setText(file_dialog)

        # excecl load ??

    def _create_excel(self):
        path = self.ui.lineEdit.text()
        excel_file = excel.ExcelWriteModel.get_last_excel_file(path)
        if excel_file:
            model = SeqTableModel(excel.ExcelWriteModel.read_excel(excel_file))
            self.ui.excel_file_label.setText(excel_file)
            self.ui.edit_excel.setEnabled(True)
        else:
            model = SeqTableModel(excel.create_excel(path))
            rows = model.rowCount(None)
            self.ui.excel_file_label.setText("No Saved Status")

        self.ui.seq_model_view.setModel(model)
        self.ui.seq_model_view.verticalHeader().setDefaultSectionSize(144);
        model.dataChanged.connect(self._set_timecode)

    def _save_excel(self):

        path = self.ui.lineEdit.text()
        excel_writer = excel.ExcelWriteModel(path)
        excel_writer.write_model_to_excel(self.ui.seq_model_view.model())
        self.ui.excel_file_label.setText(excel.ExcelWriteModel.get_last_excel_file(path))
        self.ui.edit_excel.setEnabled(True)

    def _publish(self):
        model = self.ui.seq_model_view.model()
        colorspace = str(self.ui.colorspace_combo.currentText())
        group_model = OrderedDict()
        for row in range(0, model.rowCount(None)):

            index = model.createIndex(row, 0)
            check = model.data(index, QtCore.Qt.CheckStateRole)
            if check == QtCore.Qt.CheckState.Checked:
                scan_version_index = model.createIndex(row, MODEL_KEYS['version'])
                scan_version = str(model.data(scan_version_index, QtCore.Qt.DisplayRole))
                scan_type_index = model.createIndex(row, MODEL_KEYS['type'])
                scan_type = model.data(scan_type_index, QtCore.Qt.DisplayRole)
                scan_name_index = model.createIndex(row, MODEL_KEYS['scan_name'])
                scan_name = model.data(scan_name_index, QtCore.Qt.DisplayRole)
                shot_name_index = model.createIndex(row, MODEL_KEYS['shot_name'])
                shot_name = model.data(shot_name_index, QtCore.Qt.DisplayRole)
                dict_name = shot_name + "_" + scan_name + "_" + scan_type + "_" + scan_version
                if shot_name:
                    if group_model.has_key(dict_name):
                        group_model[dict_name].append(row)
                    else:
                        group_model[dict_name] = []
                        group_model[dict_name].append(row)


                # seq_source
                else:
                    pass

        print group_model
        for value in group_model.values():
            print value
            master_input = publish.MasterInput(model, value, 'shot_name')

            opt_dpx = self.ui.mov_dpx_check.isChecked()
            opt_non_retime = self.ui.non_retime_check.isChecked()
            publish.Publish(master_input, colorspace, opt_dpx, opt_non_retime)

    def _collect(self):

        model = self.ui.seq_model_view.model()
        colorspace = str(self.ui.colorspace_combo.currentText())
        collect_path = QtGui.QFileDialog().getExistingDirectory(None,
                                                                'Collect directory',
                                                                os.path.join(self._app.sgtk.project_path, 'product'))

        group_model = OrderedDict()
        shot_group_model = OrderedDict()
        for row in range(0, model.rowCount(None)):

            index = model.createIndex(row, 0)
            check = model.data(index, QtCore.Qt.CheckStateRole)
            if check == QtCore.Qt.CheckState.Checked:
                shot_name_index = model.createIndex(row, MODEL_KEYS['shot_name'])
                shot_name = model.data(shot_name_index, QtCore.Qt.DisplayRole)
                scan_type_index = model.createIndex(row, MODEL_KEYS['type'])
                scan_type = model.data(scan_type_index, QtCore.Qt.DisplayRole)
                scan_name_index = model.createIndex(row, MODEL_KEYS['scan_name'])
                scan_name = model.data(scan_name_index, QtCore.Qt.DisplayRole)
                dict_name = scan_name + "_" + scan_type
                if shot_name:
                    dict_name = shot_name + "_" + scan_type
                    if shot_group_model.has_key(dict_name):
                        shot_group_model[dict_name].append(row)
                    else:
                        shot_group_model[dict_name] = []
                        shot_group_model[dict_name].append(row)

                else:
                    if group_model.has_key(dict_name):
                        group_model[dict_name].append(row)
                    else:
                        group_model[dict_name] = []
                        group_model[dict_name].append(row)

        for key in shot_group_model.keys():
            print key
            print shot_group_model[key]
            merge = True
            collect.Collect(model, key, shot_group_model[key], colorspace, str(collect_path), merge)

        print group_model
        for key in group_model.keys():
            print key
            print group_model[key]
            collect.Collect(model, key, group_model[key], colorspace, str(collect_path))






















