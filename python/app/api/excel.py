# -*- coding: utf-8 -*-
import glob
import re
import os
import sys
import xlsxwriter
import pyseq
import xlrd
import pydpx_meta
import OpenEXR
from PIL import Image
from sgtk.platform.qt import QtCore, QtGui
from .constant import *
import glob
import ffmpeg
from timecode import Timecode
from edl import Parser

class CutItem(object):

    def __init__(self,parent=None):
        self.start_tc = ""
        self.end_tc = ""
        self.rec_start_tc = ""
        self.rec_end_tc = ""
        self.clibname = ""

class MOV_INFO:

    def __init__(self,mov_file,video_stream=None,event=None,first_start=None,clip_name=None,cutitem = None):

        self.mov_file = mov_file
        self.video_stream = video_stream
        self.event = event
        self.first_start = first_start
        self.dirname = os.path.dirname(mov_file)
        self.scan_name = os.path.basename(mov_file)
        if clip_name:
            clip_name = clip_name.split(".")
            if len(clip_name) > 1:
                self.clip_name = clip_name[0] + "."
            else:
                self.clip_name = clip_name[0]
        else:
            self.clip_name = "None"
        self.cutitem = cutitem
        self.ext = "mov"


    def master_frame(self):
        start_frame = Timecode(round(self.framerate()),str(self.first_start.rec_start_tc)).frame_number
        if start_frame > 0 and start_frame < 86400:
            return 0 
        if start_frame > 86400:
            return 86400

        return start_frame
    
    @classmethod
    def video_stream(self,mov_file):
        probe = ffmpeg.probe(mov_file)
        video_stream = next((stream for stream in probe['streams'] 
                             if stream['codec_type'] == 'video'), None)
        
        if video_stream : 
            return video_stream
        
        return None
    
    def master_timecode(self):
        if self.video_stream['tags'].has_key("timecode"):
            start_timecode = self.video_stream['tags']['timecode']
        else:
            start_timecode = "00:00:00:00"
        start_timecode = Timecode(round(self.framerate()),str(start_timecode))
        return str(start_timecode)

    def head(self):
        return self.scan_name
    
    def tail(self):
        return None
    
    def format(self,format_str):
        return None
    

    def frames(self):

        if self.event:
            end_timecode = str(self.event.rec_end_tc)
            end_frame = Timecode(round(self.framerate()),end_timecode).frame_number

            start_timecode = str(self.event.rec_start_tc)
            start_frame = Timecode(round(self.framerate()),start_timecode).frame_number
            duraiton = end_frame - start_frame
            return duraiton
        return self.video_stream['nb_frames']

    def start(self):
        if self.event:
            start_timecode = str(self.event.rec_start_tc)
            
            mod_start_frame = Timecode(round(self.framerate()),self.master_timecode()).frame_number
            start_frame = Timecode(round(self.framerate()),start_timecode).frame_number
            return start_frame - self.master_frame() + 1
        
        return 1
            
            

    def end(self):
        if self.event:
            end_timecode = str(self.event.rec_end_tc)
            end_frame = Timecode(round(self.framerate()),end_timecode).frame_number

            start_timecode = str(self.event.rec_start_tc)
            start_frame = Timecode(round(self.framerate()),start_timecode).frame_number
            duraiton = end_frame - start_frame

            return self.start() +  duraiton - 1
        
        return self.frames()
    
    def framerate(self):
        n ,d = self.video_stream['r_frame_rate'].split("/")
        frame_rate = float(n) / float(d)
        return frame_rate
    
    


def create_excel(path):
    
    sequences = _get_sequences(path)
    movs = _get_movs(path)
    if movs:
        _create_thumbnail_for_mov(movs)
        sequences = movs + sequences
    array = _create_seq_array(sequences)
    return array


def _create_thumbnail_for_mov(movs):
    
    mov_jobs = {}

    for mov in movs:
        mov_key = os.path.join(mov.dirname,mov.scan_name)
        if mov_jobs.has_key(mov_key):
            mov_jobs[mov_key].append(mov)
        else:
            mov_jobs[mov_key] = [mov]

    thumbnail_path = os.path.join(movs[0].dirname,".thumbnail")
    if not os.path.exists(thumbnail_path):
        os.makedirs(thumbnail_path)

    for mov_file in mov_jobs:
            
        thumbnail_file = os.path.join(thumbnail_path,mov.scan_name.split(".")[0]+".%04d.jpg")
        select_frames = [ mov.start() for mov in mov_jobs[mov_file]]
        select_frames = list(set(select_frames))
        select_frames.sort()
        select_frames = ["eq(n\,{})".format(frame) for frame in select_frames]
        select_command ="+".join(select_frames)
        
        command = ['rez-env',"ffmpeg","--","ffmpeg","-y"]
        command.append("-i")
        command.append(mov_file)
        command.append("-vf")
        command.append("select='{}'".format(select_command))
        #command.append("-vframes")
        #command.append("{}".format(len(select_frames)))
        command.append("-vsync")
        command.append("0")
        command.append("-s")
        command.append("960x540")
        command.append(thumbnail_file)

        command = " ".join(command)
        print command
        os.system(command)

def _create_seq_array(sequences):
        
    array = []
    for seq in sequences:
        print "create dir seq info {}".format(seq.start())
        info = []
        info.insert(MODEL_KEYS['check'], QtGui.QCheckBox())
        info.insert(MODEL_KEYS['thumbnail'],_get_thumbnail(seq,sequences))
        info.insert(MODEL_KEYS['roll'],"")
        info.insert(MODEL_KEYS['seq_name'],"")
        info.insert(MODEL_KEYS['shot_name'], "")
        info.insert(MODEL_KEYS['version'],"")
        info.insert(MODEL_KEYS['type'], "org")
        info.insert(MODEL_KEYS['scan_path'], seq.dirname)
        info.insert(MODEL_KEYS['scan_name'], seq.head())
        if _get_ext(seq) == "mov":
            info.insert(MODEL_KEYS['clip_name'], seq.clip_name)
        else:
            info.insert(MODEL_KEYS['clip_name'], seq.head())
        info.insert(MODEL_KEYS['pad'],seq.format('%p'))
        info.insert(MODEL_KEYS['ext'],_get_ext(seq))
        info.insert(MODEL_KEYS['resolution'] , _get_resolution(seq))
        info.insert(MODEL_KEYS['start_frame'], _get_start(seq))
        info.insert(MODEL_KEYS['end_frame'], _get_end(seq))
        info.insert(MODEL_KEYS['duraiton'],_get_duration(seq))
        info.insert(MODEL_KEYS['retime_duration'],None)
        info.insert(MODEL_KEYS['retime_percent'],None)
        info.insert(MODEL_KEYS["retime_start_frame"],None)
        if _get_ext(seq) == "mov":
            if seq.cutitem:
                info.insert(MODEL_KEYS['timecode_in'],str(seq.cutitem.start_tc))
                info.insert(MODEL_KEYS['timecode_out'],str(seq.cutitem.end_tc))
            else:
                info.insert(MODEL_KEYS['timecode_in'], _get_time_code(seq,_get_start(seq)))
                info.insert(MODEL_KEYS['timecode_out'],_get_time_code(seq,_get_end(seq)))
        else:
            info.insert(MODEL_KEYS['timecode_in'], _get_time_code(seq,_get_start(seq)))
            info.insert(MODEL_KEYS['timecode_out'],_get_time_code(seq,_get_end(seq)))
        info.insert(MODEL_KEYS['just_in'],_get_start(seq))
        info.insert(MODEL_KEYS['just_out'], _get_end(seq))
        info.insert(MODEL_KEYS['framerate'] ,_get_framerate(seq))
        info.insert(MODEL_KEYS['date'] , "")
        array.append(info)
    
    return array


def _get_thumbnail(seq,sequences):
    
    

    if _get_ext(seq)== "mov":
        
        
        index_search =  [ x.start() for x in sequences ]
        index_search = list(set(index_search))
        index_search.sort()
        index = index_search.index(seq.start()) + 1

        mov_file = os.path.join(seq.dirname,seq.scan_name)
        thumbnail_path = os.path.join(seq.dirname,".thumbnail")
        #if not os.path.exists(thumbnail_path):
        #    os.makedirs(thumbnail_path)
        if seq.event:
            thumbnail_file = os.path.join(thumbnail_path,seq.scan_name.split(".")[0]+".%04d.jpg"%index)
        else:
            thumbnail_file = os.path.join(thumbnail_path,seq.scan_name.split(".")[0]+".0001.jpg")
        #start_frame = seq.start()

        #command = ['rez-env',"ffmpeg","--","ffmpeg","-y"]
        #command.append("-i")
        #command.append(mov_file)
        #command.append("-vf")
        #command.append("select='gte(n\,{0})'".format(seq.start()-1))
        #command.append("-vframes")
        #command.append("1")
        #command.append("-s")
        #command.append("240x144")
        #command.append(thumbnail_file)

        #command = " ".join(command)
        #os.system(command)
        return thumbnail_file
    else:
        original_file = os.path.join(seq.dirname,
                                     seq.head()+seq.format("%p")%seq.start()+seq.tail())
        
        thumbnail_path = os.path.join(os.path.dirname(seq.dirname),".thumbnail")
        thumbnail_file = os.path.join(thumbnail_path,
                                     seq.head()+seq.format("%p")%seq.start()+".jpg")
        if not os.path.exists(thumbnail_path):
            os.makedirs(thumbnail_path)

        command = ['rez-env',"oiio","--","oiiotool"]
        command.append(original_file)
        command.append("--colorconvert")
        command.append("linear")
        command.append("sRGB")
        command.append("--resize")
        command.append("960x540")
        command.append("-o")
        command.append(thumbnail_file)

        command = " ".join(command)
        os.system(command)
        return thumbnail_file
        
def _get_duration(seq):
    if _get_ext(seq)== "mov":

        return seq.frames()
    else:
        return len(seq.frames())
        
def _get_start(seq):

    return seq.start()

def _get_end(seq):

    return seq.end()

def _get_ext(seq):
    if not seq.tail():
        return seq.mov_file.split(".")[-1]
    return seq.tail().split(".")[-1]

def _get_time_code(seq,frame):
    if _get_ext(seq) == "mov":

        mov_file = os.path.join(seq.dirname,seq.head())
        video_stream = MOV_INFO.video_stream(mov_file)
        mov_info = MOV_INFO(mov_file,video_stream)
        if mov_info.video_stream['tags'].has_key('timecode'):
            start_timecode = mov_info.video_stream['tags']['timecode']
        else:
            start_timecode = "00:00:00:00"
        n ,d = mov_info.video_stream['r_frame_rate'].split("/")
        frame_rate = float(n) / float(d)
        start_timecode = Timecode(round(frame_rate),str(start_timecode))
        return str(start_timecode + (int(frame) - 1))



    if seq.tail() == ".exr":
        exr_file = os.path.join(seq.dirname,seq.head()+seq.format("%p")%frame+seq.tail())
        exr = OpenEXR.InputFile(exr_file)
        if exr.header().has_key("timeCode"):
            ti = exr.header()['timeCode']
            return "%02d:%02d:%02d:%02d"%(ti.hours,ti.minutes,ti.seconds,ti.frame)
        return ""
    elif seq.tail() == ".dpx":
        dpx_file = os.path.join(seq.dirname,seq.head()+seq.format("%p")%frame+seq.tail())
        dpx = pydpx_meta.DpxHeader(dpx_file)
        return dpx.tv_header.time_code
    elif seq.tail() == "":
        tail = seq.head().split(".")[-1]
        if tail == "dpx":
            dpx_file = os.path.join(seq.dirname,seq.head())
            dpx = pydpx_meta.DpxHeader(dpx_file)
            return dpx.tv_header.time_code
        elif tail == "exr":
            exr_file = os.path.join(seq.dirname,seq.head())
            exr = OpenEXR.InputFile(exr_file)
            if exr.header().has_key("timeCode"):
                ti = exr.header()['timeCode']
                return "%02d:%02d:%02d:%02d"%(ti.hours,ti.minutes,ti.seconds,ti.frame)
            return ""
    else:
        return ""

def _get_framerate(seq):

    if _get_ext(seq) == "mov":

        mov_file = os.path.join(seq.dirname,seq.head())
        video_stream = MOV_INFO.video_stream(mov_file)
        mov_info = MOV_INFO(mov_file,video_stream)
        n ,d = mov_info.video_stream['r_frame_rate'].split("/")
        frame_rate = float(n) / float(d)
        return frame_rate

    if seq.tail() == ".exr":
        exr_file = os.path.join(seq.dirname,seq.head()+seq.format("%p")%seq.start()+seq.tail())
        exr = OpenEXR.InputFile(exr_file)
        if exr.header().has_key("framesPerSecond"):
            fr = exr.header()['framesPerSecond']
            return  float(fr.n)/float(fr.d) 
        return ""
    elif seq.tail() == ".dpx":
        dpx_file = os.path.join(seq.dirname,seq.head()+seq.format("%p")%seq.start()+seq.tail())
        dpx = pydpx_meta.DpxHeader(dpx_file)
        return dpx.raw_header.TvHeader.FrameRate
    elif seq.tail() == "":
        tail = seq.head().split(".")[-1]
        if tail == "dpx":
            dpx_file = os.path.join(seq.dirname,seq.head())
            dpx = pydpx_meta.DpxHeader(dpx_file)
            return dpx.raw_header.TvHeader.FrameRate
        elif tail == "exr":
            exr_file = os.path.join(seq.dirname,seq.head())
            exr = OpenEXR.InputFile(exr_file)
            if exr.header().has_key("framesPerSecond"):
                fr = exr.header()['framesPerSecond']
                return  float(fr.n)/float(fr.d) 
            return ""
    else:
        return ""

def _get_resolution(seq):

    if _get_ext(seq) == "mov":

        mov_file = os.path.join(seq.dirname,seq.head())
        video_stream = MOV_INFO.video_stream(mov_file)
        mov_info = MOV_INFO(mov_file,video_stream)
        width  = mov_info.video_stream['width']
        height  = mov_info.video_stream['height']
        return "%d x %d"%(width,height)

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

        width = dpx.raw_header.OrientHeader.XOriginalSize
        height = dpx.raw_header.OrientHeader.YOriginalSize
        if width == 0:
            from subprocess import check_output
            dpx_info = check_output(["rez-env", "oiio","--","iinfo",dpx_file])
            resolution_info = re.search("\d+\ x\ \d+",dpx_info)
            if resolution_info :
                width,height = resolution_info.group().split("x")
                width = int(width)
                height = int(height)
        return '%d x %d'%(width,height)

    elif seq.tail() in [ '.jpg','.jpeg']:
        jpg_file = os.path.join(seq.dirname,seq.head()+seq.format("%p")%seq.start()+seq.tail())
        jpeg = Image.open(jpg_file)
        return '%d x %d'%(jpeg.size[0],jpeg.size[1])
    elif seq.tail() == "":
        tail = seq.head().split(".")[-1]
        if tail == "dpx":
            dpx_file = os.path.join(seq.dirname,seq.head())
            dpx = pydpx_meta.DpxHeader(dpx_file)
            width = dpx.raw_header.OrientHeader.XOriginalSize
            height = dpx.raw_header.OrientHeader.YOriginalSize
            if width == 0:
                from subprocess import check_output
                dpx_info = check_output(["rez-env", "oiio","--","iinfo",dpx_file])
                resolution_info = re.search("\d+\ x\ \d+",dpx_info)
                if resolution_info :
                    width,height = resolution_info.group().split("x")
                    width = int(width)
                    height = int(height)
            return '%d x %d'%(width,height)
        elif tail == "exr":
            exr_file = os.path.join(seq.dirname,seq.head())
            exr = OpenEXR.InputFile(exr_file)
            if exr.header().has_key("dataWindow"):
                res = exr.header()['dataWindow']
                return "%d x %d"%(res.max.x+1,res.max.y+1)
            return ""
    else:
        return ""


def _get_sequences(path):
    
    sequences = []

    for temp in os.listdir(path):
        if temp in ['.thumbnail']:
            continue
        temp = os.path.join(path,temp)
        if os.path.isdir(temp):
            sequence = pyseq.get_sequences(temp)
            if sequence:
                sequences.extend(sequence)
    

    return sequences

def _get_movs(path):
    
    movs = []

    mov_files = glob.glob(os.path.join(path,"*.mov"))
    
    for mov_file in mov_files:
        
        video_stream = MOV_INFO.video_stream(mov_file)
        mov_info = MOV_INFO(mov_file,video_stream)
        mov_name = mov_file.split(".")[0]
        edl_files = glob.glob(mov_name + "*.edl")
        if edl_files:
            for edl_file in edl_files:
                if os.path.exists(edl_file):
                    parser = Parser(round(mov_info.framerate()))
                    f = open(edl_file)
                    dl = parser.parse(f)
                    first_start = dl[0]
                    for event in dl:

                        cutitem = CutItem()
                        cutitem.clibname = event.clip_name
                        cutitem.start_tc = event.src_start_tc
                        cutitem.end_tc = event.src_end_tc
                        cutitem.rec_start_tc = event.rec_start_tc
                        cutitem.rec_end_tc = event.rec_end_tc
                        mov_info = MOV_INFO(mov_file,video_stream,event,first_start,event.clip_name,cutitem)
                        movs.append(mov_info)    
                    f.close()
        else:
            mov_info = MOV_INFO(mov_file,video_stream)
            movs.append(mov_info)    

    return movs

 




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
        for row in range(1,rows):
            info = []
            check_data = rWorksheet.cell_value( row, MODEL_KEYS['check'] )
            check_box = QtGui.QCheckBox()
            if check_data:
                check_box.setChecked(True)
            info.append(check_box)
            for col in range(1,cols):
                data = rWorksheet.cell_value( row, col )
                if not data == "NaN":
                    if col == 1:
                        ext = rWorksheet.cell_value(row,MODEL_KEYS['ext'])
                        if ext in ['mov']:
                            path = rWorksheet.cell_value( row, 7 )
                        else:
                            path = os.path.dirname(rWorksheet.cell_value( row, 7 ))
                        thumbnail_path = os.path.join(path,
                            ".thumbnail")
                        thumbnail_file = os.path.join(thumbnail_path,data)
                        info.append(thumbnail_file)
                    elif col in [MODEL_KEYS["timecode_in"],MODEL_KEYS['timecode_out']]:
                        if type(data) == float:
                            data = "%08d"%int(data)
                            temp = list(data)
                            temp = [ temp[x]+temp[x+1] for x in range(0,len(temp)) if (x+1)%2 == 1 ]
                            data = ":".join(temp)
                        info.append(data)
                    else:
                        info.append(data)
                else:
                    info.append("")
            array.append(info)
        return array
    
    def write_model_to_excel(self,model):
        for col in range(0,len(model.header)):

            self.wWorksheet.write(0,col,model.header[col])

        for row in range(0,model.rowCount(None)):
            index = model.createIndex(row,MODEL_KEYS['check'])
            check_box = model.data(index,QtCore.Qt.CheckStateRole)
            if check_box:
                self.wWorksheet.write( row+1, MODEL_KEYS['check'], "o" )

            for col in range(1,model.columnCount(None)):
                index = model.createIndex(row,col)
                data = model.data(index,QtCore.Qt.DisplayRole )
                try:
                    if data == "" :
                        self.wWorksheet.write( row+1, col, "" )
                    else:
                        if col == 1:
                            thumbnail_file = os.path.basename(data)
                            self.wWorksheet.write( row+1, col, thumbnail_file )
                        else:
                            self.wWorksheet.write( row+1, col, data )
                    if col == 1:
                        #col = self.wWorksheet.col(1)
                        #col.width = 240
                        self.wWorksheet.set_row( row+1, 144 )   # 엑셀 높이설정 (썸네일크기 맞춰서)
                        self.wWorksheet.insert_image( row+1, col,data,{'x_scale':0.25, 'y_scale': 0.25})

                except Exception as e :
                    print e
                    pass
        
        for col in MODEL_KEYS.values()[1:]:
            self.wWorksheet.set_column( col,col ,15 )
        self.wWorksheet.set_column( MODEL_KEYS['thumbnail'], MODEL_KEYS['thumbnail'], 40 )
        self.wWorksheet.set_column( MODEL_KEYS['scan_path'], MODEL_KEYS['scan_path'], 45 )
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
            self.wWorksheet.insert_image( row, col, img, {'x_scale': 0.00001, 'y_scale': 0.00001} )

    def insertData( self, row, col, string ):
        self.wWorksheet.write( row, col, string )

    def insertDataN( self, row, colName, string ):
        #col = HORIZONTALITEMS.index( colName )
        self.wWorksheet.write( row, colName, string )


def get_time_code(dir_name,head,frame_format,frame,tail):

    if tail == "mov":

        mov_file = os.path.join(dir_name,head)
        video_stream = MOV_INFO.video_stream(mov_file)
        mov_info = MOV_INFO(mov_file,video_stream)
        start_timecode = mov_info.video_stream['tags']['timecode']
        n ,d = mov_info.video_stream['r_frame_rate'].split("/")
        frame_rate = float(n) / float(d)
        start_timecode = Timecode(round(frame_rate),str(start_timecode))
        return str(start_timecode + (int(frame) - 1))

    if tail == "exr":
        exr_file = os.path.join(dir_name,head+"."+frame_format%frame+"."+tail)
        exr = OpenEXR.InputFile(exr_file)
        if exr.header().has_key("timeCode"):
            ti = exr.header()['timeCode']
            return "%02d:%02d:%02d:%02d"%(ti.hours,ti.minutes,ti.seconds,ti.frame)
        return ""
    elif tail == "dpx":
        dpx_file = os.path.join(dir_name,head+"."+frame_format%frame+"."+tail)
        dpx = pydpx_meta.DpxHeader(dpx_file)
        return dpx.tv_header.time_code
    else:
        return ""
