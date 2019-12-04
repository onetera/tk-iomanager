
import os
import sgtk
import pyseq
from sgtk.platform.qt import QtCore, QtGui
import tractor.api.author as author
from .constant import *

codecs = {
    "Apple ProRes 4444":"ap4h",
    "Apple ProRes 422 HQ":"apch",
    "Apple ProRes 422":"apcn",
    "Apple ProRes 422 LT":"apcs",
    "Apple ProRes 422 Proxy":"apco",
    "Avid DNxHD Codec":"AVdn"}

colorspace_set = {

    "ACES - ACEScg"     : "Output - Rec.709",
    "ACES - ACES2065-1" : "Output - Rec.709",
    "AlexaV3LogC"       : "AlexaViewer",
    "Cineon"            : "rec709",
    "rec709"            : "rec709",

}


class Output(object):
    

    def __init__(self,info):
        
        self.mov_fps = float(info['sg_fps'])
        self._set_file_type(info['sg_out_format'])
        self._set_colorspace(info['sg_colorspace'],info)
        self.mov_codec = codecs[info['sg_mov_codec']]
    
    def _set_file_type(self,text):
        
        if text =="exr 32bit":
            self.file_type = "exr"
            self.datatype = "32 bit float"
        if text =="exr 16bit":
            self.file_type = "exr"
            self.datatype = "16 bit half"
        if text =="dpx 10bit":
            self.file_type = "dpx"
            self.datatype = "10 bit"
    
    def _set_colorspace(self,text,info):
        
        if not text.find("ACES") == -1 :
            self.colorspace = "ACES - %s"%text
            self.mov_colorspace = info['sg_mov_colorspace']
        else:
            if not info['sg_mov_colorspace'] :
                self.colorspace = text
                self.mov_colorspace = text
            else:
                self.colorspace = text
                self.mov_colorspace = info['sg_mov_colorspace']

class Collect:
    
    def __init__(self,model,org_name,rows,scan_colorspace,collect_path,parent=None):
        
        self.scan_colorspace = scan_colorspace

        self._app = sgtk.platform.current_bundle()
        self._sg = self._app.shotgun
        self.project = self._app.context.project
        self.user = self._app.context.user
        self.model = model
        self.collect_path = collect_path
        self.rows = rows
        self.org_name = org_name
        self.scan_path = self._get_data(MODEL_KEYS['scan_path'])
        self.scan_name = self._get_data(MODEL_KEYS['scan_name'])
        self.scan_colorspace = scan_colorspace


        self.nuke_mov_scripts = self.create_mov_nuke_script()

        self.create_job()
        #self.submit_job()

    
    
    def _get_data(self,col,row=None):
        if not row:
            index = self.model.createIndex(self.rows[0],col)
        else:
            index = self.model.createIndex(row,col)
        return self.model.data(index,QtCore.Qt.DisplayRole)
        
    

    def create_job(self):


        
       
        self.job = author.Job()
        self.job.title = str('[IOM]' +self.org_name+" publish")
        self.job.service = "comp"
        self.job.priority = 10
        for nuke_script in self.nuke_mov_scripts:
            task = author.Task(title = "split")
            cmd = ['rez-env','nuke','--','nuke','-ix',nuke_script]
            if not self.scan_colorspace.find("ACES") == -1: 
                cmd = ['rez-env','nuke','ocio_config','--','nuke','-ix',nuke_script]
            if not self.scan_colorspace.find("Alexa") == -1: 
                cmd = ['rez-env','nuke','alexa_config','--','nuke','-ix',nuke_script]
            command = author.Command(argv=cmd)
            task.addCommand(command)
            self.job.addChild(task)

    

        self.job.spool(hostname="10.0.20.82",owner="dellfarm")
    
    
    def create_rm_job(self):


        self.rm_task = author.Task(title = "rm")
        cmd = ['rm','-f',self.nuke_script]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)
        
        if self.master_input.retime_job:
            cmd = ['rm','-f',self.nuke_retime_script]
            command = author.Command(argv=cmd)
            self.rm_task.addCommand(command)

        if self.nuke_mov_script:
            cmd = ['rm','-f',self.nuke_mov_script]
            command = author.Command(argv=cmd)
            self.rm_task.addCommand(command)

        cmd = ['rm','-f',self.sg_script]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)

        cmd = ['rm','-f',montage_path]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)

        cmd = ['rm','-rf',self.montage_jpg_path]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)

        cmd = ['rm','-f',webm_path]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)

        #cmd = ['rm','-f',self.copy_script]
        #command = author.Command(argv=cmd)
        #self.rm_task.addCommand(command)
        
        self.job.addChild(self.rm_task)
    

    def create_mov_nuke_script(self):
    
        nuke_script_files = []
        app = sgtk.platform.current_bundle()
        context = app.context
        project = context.project

        output_info = self._sg.find_one("Project",[['id','is',project['id']]],
                               ['sg_colorspace','sg_mov_codec',
                               'sg_out_format','sg_fps','sg_mov_colorspace'])

        setting = Output(output_info)

        scan_path = os.path.join(self.scan_path,
                                 self.scan_name
                                 )

        for row in self.rows:
            
            py_filename = "."+ str(self.org_name) + "%04d.py"%(row+1)
            mov_filename = str(self.org_name) + "%04d.mov"%(row+1)

            tmp_nuke_script_file = os.path.join(str(self.collect_path),py_filename)
            out_path = os.path.join(str(self.collect_path),mov_filename)
            just_in = self._get_data(MODEL_KEYS['just_in'],row)
            just_out = self._get_data(MODEL_KEYS['just_out'],row)
            framerate = self._get_data(MODEL_KEYS['framerate'],row)

            nk = ''
            nk += 'import nuke\n'
            nk += 'read = nuke.nodes.Read( file="{}" )\n'.format( scan_path )
            nk += 'read["colorspace"].setValue("{}")\n'.format(self.scan_colorspace)
            nk += 'read["first"].setValue( {} )\n'.format(int(just_in))
            nk += 'read["last"].setValue( {} )\n'.format( int(just_out))
            tg = 'read'
            nk += 'output = "{}"\n'.format( out_path )
            nk += 'write = nuke.nodes.Write(inputs = [%s],file=output )\n'% tg
            nk += 'write["file_type"].setValue( "mov" )\n'
            nk += 'write["create_directories"].setValue(True)\n'
            nk += 'write["mov64_codec"].setValue( "{}")\n'.format(setting.mov_codec)
            nk += 'write["colorspace"].setValue("{}")\n'.format(self.scan_colorspace)
            nk += 'write["mov64_fps"].setValue({})\n'.format(framerate)
            nk += 'nuke.execute(write,{0},{1},1)\n'.format(int(just_in),int(just_out))
            nk += 'exit()\n'


            if not os.path.exists( os.path.dirname(tmp_nuke_script_file) ):
                cur_umask = os.umask(0)
                os.makedirs(os.path.dirname(tmp_nuke_script_file),0777 )
                os.umask(cur_umask)

            with open( tmp_nuke_script_file, 'w' ) as f:
                f.write( nk )
        
            nuke_script_files.append(tmp_nuke_script_file)
        
        return nuke_script_files




    
