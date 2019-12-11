# -*- coding: utf-8 -*-

import os
import sgtk
from sgtk.platform.qt import QtCore, QtGui
from timecode import Timecode
import pyseq
import pydpx_meta
import OpenEXR
import math
from .constant import *
import ffmpeg

class MOV_INFO:

    def __init__(self,mov_file):

        self.mov_file = mov_file
    
    @property
    def video_stream(self):
        probe = ffmpeg.probe(self.mov_file)
        video_stream = next((stream for stream in probe['streams'] 
                             if stream['codec_type'] == 'video'), None)
        
        if video_stream : 
            return video_stream
        
        return None


class Validate(object):

    def __init__(self,model,parent=None):
        
        self.model = model
        self._app = sgtk.platform.current_bundle()
        self._sg = self._app.shotgun
        self.project = self._app.context.project

        pass
    
    def timecode(self):
        
        rows = self.model.rowCount(None)
        timecode_in = MODEL_KEYS['timecode_in']
        timecode_out = MODEL_KEYS['timecode_out']
        for row in range(0,rows):

            index = self.model.createIndex(row,0)
            check = self.model.data(index,QtCore.Qt.CheckStateRole )
            if check == QtCore.Qt.CheckState.Unchecked:
                continue
            
            framerate = math.ceil(self._get_data(row,MODEL_KEYS['framerate']))
            mod_start_frame = self._get_data(row,MODEL_KEYS['start_frame'])


            seq_path = self._get_data(row,MODEL_KEYS['scan_path'])
            ext = self._get_data(row,MODEL_KEYS['ext'])
            if ext == "mov":
                return
                scan_name = self._get_data(row, MODEL_KEYS['scan_name'])
                seq_path = os.path.join(seq_path,scan_name)
            seq = pyseq.get_sequences(seq_path)

            if not seq:
                return
            seq = seq[0]
            start_timecode = self._get_timecode(seq,self._get_start(seq))
            start_frame = Timecode(framerate,start_timecode).frame_number
            
            timecode_in = self._get_data(row,MODEL_KEYS['timecode_in'])
            just_in_frame = Timecode(round(framerate),timecode_in).frame_number
            
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
    
    def uploade_status(self):
        rows = self.model.rowCount(None)
        for row in range(0,rows):

            index = self.model.createIndex(row,0)
            check = self.model.data(index,QtCore.Qt.CheckStateRole )
            if check == QtCore.Qt.CheckState.Unchecked:
                continue
            version,date = self._get_version(row)
            self._set_data(row,MODEL_KEYS['version'],version)
            self._set_data(row,MODEL_KEYS['date'],str(date))
    
    def check_src_version(self):
        
        group_model = {}

        for row in range(0,self.model.rowCount(None)):

            index = self.model.createIndex(row,0)
            check = self.model.data(index,QtCore.Qt.CheckStateRole )
            if check == QtCore.Qt.CheckState.Unchecked:
                continue

            type_value = self._get_data(row,MODEL_KEYS['type'])
            if not type_value.find("src") ==  -1:
                shot_name = self._get_data(row,MODEL_KEYS['shot_name'])
            if group_model.has_key(shot_name):
                group_model[shot_name].append(row)
            else:
                group_model[shot_name] = []
                group_model[shot_name].append(row)
        
        for value in group_model.values():
            print value
            add_value = 0
            for row in value:
                version = self._get_data(row,MODEL_KEYS['version'])
                self._set_data(row,MODEL_KEYS['version'],int(version)+add_value)
                add_value += 1



    def _get_version(self,row):
        
        file_type = self._get_data(row,MODEL_KEYS['type'])
        file_type_ent = self.published_file_type(file_type)
        shot_name = self._get_data(row,MODEL_KEYS['shot_name'])
        version_name = shot_name + "_" + file_type
        key = [
                ['project','is',self.project],
                ['code','is',shot_name]
                ]

        shot_ent = self._sg.find_one('Shot',key)

        key = [
                ['project','is',self.project],
                ['entity','is',shot_ent],
                ["published_file_type","is",file_type_ent],
                ['name','is',version_name]
               ]
        published_ents = self._sg.find("PublishedFile",key,['version_number','created_at'])
        if not published_ents:
            return 1,""
        else:
            return published_ents[-1]['version_number']+1 ,published_ents[-1]['created_at']


    def published_file_type(self,file_type):

        if file_type== "org":
            key  = [['code','is','Plate']]
            return self._sg.find_one("PublishedFileType",key,['id'])
        else:
            key  = [['code','is','Source']]
            return self._sg.find_one("PublishedFileType",key,['id'])
            

    def _get_data(self,row,col):

        index = self.model.createIndex(row,col)
        data = self.model.data(index,QtCore.Qt.DisplayRole)

        return data
    def _set_data(self,row,col,data):

        index = self.model.createIndex(row,col)
        self.model.setData(index,data,3)

    def _get_timecode(self,seq,frame):

        if seq.head().split(".")[-1] == "mov":

            mov_file = os.path.join(seq.dirname,seq.head())
            mov_info = MOV_INFO(mov_file)
            start_timecode = mov_info.video_stream['tags']['timecode']
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
        else:
            return ""

    def _get_start(self,seq):

        if seq.head().split(".")[-1] == "mov":
            return 1
        return seq.start()

