# -*- coding: utf-8 -*-
import glob
import os
import xlsxwriter
import pyseq
import xlrd
import pydpx_meta
import OpenEXR
from sgtk.platform.qt import QtCore, QtGui


def create_excel(path):
    
    sequences = _get_sequences(path)
    array = _create_seq_array(sequences)
    
    return array

def _create_seq_array(sequences):
        
    array = []

    for seq in sequences:
        info = []
        info.append(QtGui.QCheckBox())
        info.append("")
        info.append("")
        info.append("org")
        info.append(seq.dirname)
        info.append(seq.head().split(".")[0])
        info.append(seq.format("%p"))
        info.append(seq.tail().split(".")[-1])
        info.append(_get_resolution(seq))
        info.append(seq.start())
        info.append(seq.end())
        info.append(len(seq.frames()))
        info.append(_get_time_code(seq,seq.start()))
        info.append(_get_time_code(seq,seq.end()))
        info.append(seq.start())
        info.append(seq.end())
        info.append(_get_framerate(seq))
        info.append("")
        array.append(info)
    
    return array


def _get_time_code(seq,frame):
    if seq.tail() == ".exr":
        exr_file = os.path.join(seq.dirname,seq.head()+seq.format("%p")%frame+seq.tail())
        exr = OpenEXR.InputFile(exr_file)
        if exr.header().has_key("timeCode"):
            ti = exr.header()['timeCode']
            return "%d:%d:%d:%d"%(ti.hours,ti.minutes,ti.seconds,ti.frame)
        return ""
    elif seq.tail() == ".dpx":
        dpx_file = os.path.join(seq.dirname,seq.head()+seq.format("%p")%frame+seq.tail())
        dpx = pydpx_meta.DpxHeader(dpx_file)
        return dpx.tv_header.time_code
    else:
        return ""

def _get_framerate(seq):
    if seq.tail() == ".exr":
        exr_file = os.path.join(seq.dirname,seq.head()+seq.format("%p")%seq.start()+seq.tail())
        exr = OpenEXR.InputFile(exr_file)
        if exr.header().has_key("framesPerSecond"):
            fr = exr.header()['framesPerSecond']
            return  fr.n 
        return ""
    elif seq.tail() == ".dpx":
        dpx_file = os.path.join(seq.dirname,seq.head()+seq.format("%p")%seq.start()+seq.tail())
        dpx = pydpx_meta.DpxHeader(dpx_file)
        return int(dpx.raw_header.TvHeader.FrameRate)
    else:
        return ""

def _get_resolution(seq):
    if seq.tail() == ".exr":
        exr_file = os.path.join(seq.dirname,seq.head()+seq.format("%p")%seq.start()+seq.tail())
        exr = OpenEXR.InputFile(exr_file)
        if exr.header().has_key("dataWindow"):
            res = exr.header()['dataWindow']
            return "%d x %d"%(res.max.x+1,res.max.y+1)
        return ""
    elif seq.tail() == ".dpx":
        dpx_file = os.path.join(seq.dirname,seq.head()+seq.format("%p")%seq.start()+seq.tail())
        dpx = pydpx_meta.DpxHeader(dpx_file)
        return '%d x %d'%(dpx.raw_header.OrientHeader.XOriginalSize,
                          dpx.raw_header.OrientHeader.YOriginalSize)
    else:
        return ""


def _get_sequences(path):
    
    sequences = []

    for temp in os.listdir(path):
        temp = os.path.join(path,temp)
        if os.path.isdir(temp):
            sequence = pyseq.get_sequences(temp)
            if sequence:
                sequences.extend(sequence)
    
    return sequences

 






class ExcelWriteModel:

    def __init__( self, excel_path ):

        self._excel_path = excel_path
        self.excel_file  = self._get_excel_file()

        self.wWorkbook  = xlsxwriter.Workbook( self._excel_file )
        self.wWorksheet = self.wWorkbook.add_worksheet()     # 엑셀 파일 생성
        self.bold       = self.wWorkbook.add_format( {'bold': 1} )
        #self.initHorizontalItems()
    
    def _get_excel_file(self):

	    excel_files = ""
	    excel_files = glob.glob("%s/scanlist_*.xls"%self._excel_path)
	    if not excel_files:
		    self._excel_file  = "%s/scanlist_01.xls"%self._excel_path
	    else:
		    last = sorted(excel_files)[-1]
		    num = filter(str.isdigit,str(os.path.basename(last)))
		    new_name = "scanlist_%02d.xls"%(int(num)+1)
		    self._excel_file = "%s/%s"%(self._excel_path,new_name)

    @classmethod    
    def get_last_excel_file(self,path):
        excel_files = ""
        excel_files = glob.glob("%s/scanlist_*.xls"%path)
        if not excel_files:
            return None
        else:
            last = sorted(excel_files)[-1]
            return last
    
    @classmethod    
    def read_excel(self,excel_file):


        rWorkbook  = xlrd.open_workbook( excel_file )
        rWorksheet = rWorkbook.sheet_by_name( 'Sheet1' )
        rows = rWorksheet.nrows  
        cols = rWorksheet.ncols
        array = []
        for row in range(0,rows):
            info = []
            info.append(QtGui.QCheckBox())
            for col in range(1,cols):
                data = rWorksheet.cell_value( row, col )
                if not data == "NaN":
                    info.append(data)
                else:
                    info.append("")
            array.append(info)
        return array

    def write_model_to_excel(self,model):



        for row in range(0,model.rowCount(None)):
            for col in range(0,model.columnCount(None)):
                index = model.createIndex(row,col)
                data = model.data(index,QtCore.Qt.DisplayRole )
                try:
                    if data == "" :
                        self.wWorksheet.write( row, col, "NaN" )
                    else:
                        self.wWorksheet.write( row, col, data )
                except Exception as e :
                    print e
                    pass
        
        self.wWorkbook.close()

    def set_global_data( self ,temp_folder,scan_date ):
        self.ws_2 = self.wWorkbook.add_worksheet()
        self.ws_2.write( 0 , 0 , temp_folder )
        self.ws_2.write( 1 , 0 , self.excelfile )
        self.ws_2.write( 2 , 0 , scan_date )

    def initHorizontalItems( self ):
        for i, col in enumerate( HORIZONTALITEMS ):
            self.wWorksheet.write( string.uppercase[i] + '1', col[0], self.bold ) ### A1(0행 0열에 col값)
            self.wWorksheet.set_column( '{0}:{0}'.format( string.uppercase[i]), col[1] ) ### ( Colum 넓이 조정 )
            self.bold.set_align( 'center')
            self.bold.set_align( 'vcenter')
            self.bold.set_bg_color( 'green')
            self.bold.set_font_size ( 13 )

    def saveExcel( self ):
        self.wWorkbook.close()
        if os.path.isfile( self.excelfile ):
            return True
        else :
            return False

    def insertImage( self, row, col, img ):
        ''' 엑셀 이미지 넣기 (썸네일)'''
        if not os.path.isfile( img ):
            pass
        else:
            col_size,rowsize = Image.open(img).size
            #self.wWorksheet.set_column( col, col, 20 )
            self.wWorksheet.set_row( row, 60 )   # 엑셀 높이설정 (썸네일크기 맞춰서)
            self.wWorksheet.insert_image( row, col, img, {'x_offset':10, 'y_offset':5, 'x_scale': 0.05, 'y_scale': 0.05} )

    def insertData( self, row, col, string ):
        self.wWorksheet.write( row, col, string )

    def insertDataN( self, row, colName, string ):
        #col = HORIZONTALITEMS.index( colName )
        self.wWorksheet.write( row, colName, string )


def get_time_code(dir_name,head,frame_format,frame,tail):
    if tail == "exr":
        exr_file = os.path.join(dir_name,head+"."+frame_format%frame+"."+tail)
        exr = OpenEXR.InputFile(exr_file)
        if exr.header().has_key("timeCode"):
            ti = exr.header()['timeCode']
            return "%d:%d:%d:%d"%(ti.hours,ti.minutes,ti.seconds,ti.frame)
        return ""
    elif tail == "dpx":
        dpx_file = os.path.join(dir_name,head+"."+frame_format%frame+"."+tail)
        dpx = pydpx_meta.DpxHeader(dpx_file)
        return dpx.tv_header.time_code
    else:
        return ""
