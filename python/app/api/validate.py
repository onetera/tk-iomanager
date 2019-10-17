# -*- coding: utf-8 -*-

import os
from sgtk.platform.qt import QtCore, QtGui
from timecode import Timecode
import pyseq
import pydpx_meta
import OpenEXR
import math
from .constant import *


class Validate(object):

    def __init__(self,model,parent=None):
        
        self.model = model
        

        pass
    
    def timecode(self):
        
        rows = self.model.rowCount(None)
        timecode_in = MODEL_KEYS['timecode_in']
        timecode_out = MODEL_KEYS['timecode_out']
        for row in range(0,rows):
            
            framerate = math.ceil(self._get_data(row,MODEL_KEYS['framerate']))
            mod_start_frame = self._get_data(row,MODEL_KEYS['start_frame'])


            seq_path = self._get_data(row,MODEL_KEYS['scan_path'])
            seq = pyseq.get_sequences(seq_path)
            if not seq:
                return
            seq = seq[0]
            start_timecode = self._get_timecode(seq,seq.start())
            start_frame = Timecode(framerate,start_timecode).frame_number
            
            timecode_in = self._get_data(row,MODEL_KEYS['timecode_in'])
            just_in_frame = Timecode(int(framerate),timecode_in).frame_number
            
            timecode_out = self._get_data(row,MODEL_KEYS['timecode_out'])
            just_out_frame = Timecode(framerate,timecode_out).frame_number
            
            just_in = mod_start_frame + (just_in_frame - start_frame)
            just_out = mod_start_frame + (just_out_frame - start_frame)
            
            self._set_data(row,MODEL_KEYS['just_in'],just_in)
            self._set_data(row,MODEL_KEYS['just_out'],just_out)

    def shotname(self):
        rows = self.model.rowCount(None)
        pass


    def seq_name(self):
        pass


    def _get_data(self,row,col):

        index = self.model.createIndex(row,col)
        data = self.model.data(index,QtCore.Qt.DisplayRole)

        return data
    def _set_data(self,row,col,data):

        index = self.model.createIndex(row,col)
        self.model.setData(index,data,3)

    def _get_timecode(self,seq,frame):
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
        else:
            return ""
