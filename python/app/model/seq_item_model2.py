from sgtk.platform.qt import QtCore, QtGui

class SeqTableModel(QtCore.QAbstractTableModel):
    
    def __init__(self,array ,parent=None, *args):

        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = array
        self.header = ["c","Shot name","Type","Scan path","Scan Name","pad","Ext","format","Start frame","End Frame","Range","TimeCode IN","TimeCode Out","In","Out","Fr","Date"]
        self._set_header()

    def _set_header(self):
        for col in range(0,len(self.header)):
            print "18"
            self.setHeaderData(col,QtCore.Qt.Horizontal,
                                self.header[col])


    def rowCount(self, parent):
        return len(self.arraydata)

    def columnCount(self, parent):
        return len(self.arraydata[0])

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role == QtCore.Qt.DisplayRole :
            return self.arraydata[index.row()][index.column()]
        elif role == QtCore.Qt.EditRole:
            return self.arraydata[index.row()][index.column()]
        elif role == QtCore.Qt.CheckStateRole and index.column() == 0:
            if self.arraydata[index.row()][index.column()].isChecked():
                return QtCore.Qt.Checked
            else:
                return QtCore.Qt.Unchecked

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsUserCheckable

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        # print(">>> setData() role = ", role)
        # print(">>> setData() index.column() = ", index.column())
        # print(">>> setData() value = ", value)
        if role == QtCore.Qt.CheckStateRole and index.column() == 0:
            print(">>> setData() role = ", role)
            print(">>> setData() index.column() = ", index.column())
            if value == QtCore.Qt.Checked:
                self.arraydata[index.row()][index.column()].setChecked(True)
                # if studentInfos.size() > index.row():
                #     emit StudentInfoIsChecked(studentInfos[index.row()])     
            else:
                self.arraydata[index.row()][index.column()].setChecked(False)
        else:
            print(">>> setData() role = ", role)
            print(">>> setData() index.column() = ", index.column())

            self.arraydata[index.row()][index.column()] = value
        print(">>> setData() index.row = ", index.row())
        print(">>> setData() index.column = ", index.column())
        self.dataChanged.emit(index, index)

