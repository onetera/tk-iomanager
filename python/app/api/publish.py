
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
            #nuke.root()['colorManagement'].setValue("OCIO")
            #nuke.root()['OCIO_config'].setValue("aces_1.0.1")
            self.colorspace = "ACES - %s"%text
            self.mov_colorspace = info['sg_mov_colorspace']
        else:
            #nuke.root()['colorManagement'].setValue("Nuke")
            self.colorspace = text
            self.mov_colorspace = text


class MasterInput(object):

    def __init__(self,model,group_model_rows,entity_type):

        self.model = model
        self.rows = group_model_rows
        self.entity_type = entity_type
        self._set_data()
        self._create_retime_info()

    def _set_data(self):
        
        self.entity_name = self._get_data(MODEL_KEYS[self.entity_type])
        self.scan_path = self._get_data(MODEL_KEYS['scan_path'])
        self.scan_name = self._get_data(MODEL_KEYS['scan_name'])
        self.version = int(self._get_data(MODEL_KEYS['version']))
        self.pad = self._get_data(MODEL_KEYS['pad'])
        self.ext = self._get_data(MODEL_KEYS['ext'])
        self.resolution = self._get_data(MODEL_KEYS['resolution'])
        self.start_frame = self._get_data(MODEL_KEYS['start_frame'])
        self.end_frame = self._get_data(MODEL_KEYS['end_frame'])
        self.framerate = float(self._get_data(MODEL_KEYS['framerate']))
        self.type = self._get_data(MODEL_KEYS['type'])
    
    @property
    def just_in(self):

        if len(self.rows) == 1:
            return self._get_data(MODEL_KEYS['just_in'])
        
        else:
            temp = []
            for row in self.rows:
                temp.append(self._get_data(MODEL_KEYS['just_in'],row))

            return min(temp)
            
    @property
    def just_out(self):

        if len(self.rows) == 1:
            return self._get_data(MODEL_KEYS['just_out'])
        
        else:
            temp = []
            for row in self.rows:
                temp.append(self._get_data(MODEL_KEYS['just_out'],row))

            return max(temp)

    @property
    def timecode_in(self):

        if len(self.rows) == 1:
            return self._get_data(MODEL_KEYS['timecode_in'])
        
        else:
            temp = []
            for row in self.rows:
                temp.append(self._get_data(MODEL_KEYS['timecode_in'],row))

            return min(temp)

    @property
    def timecode_out(self):

        if len(self.rows) == 1:
            return self._get_data(MODEL_KEYS['timecode_out'])
        
        else:
            temp = []
            for row in self.rows:
                temp.append(self._get_data(MODEL_KEYS['timecode_out'],row))

            return max(temp)

    
    def _create_retime_info(self):

        if not self._get_data(MODEL_KEYS['retime_duration']):
            self.retime_job = False
            return
        else:
            self.retime_info = []
            self.retime_job = True
            for row in self.rows:
                info = {}
                info['just_in'] = self._get_data(MODEL_KEYS['just_in'],row)
                info['just_out'] = self._get_data(MODEL_KEYS['just_out'],row)
                info['retime_start_frame'] = int(self._get_data(MODEL_KEYS['retime_start_frame'],row))
                info['retime_duration'] = int(self._get_data(MODEL_KEYS['retime_duration'],row))
                info['retime_percent'] = int(self._get_data(MODEL_KEYS['retime_percent'],row))
                self.retime_info.append(info)
    
        
    def _get_data(self,col,row=None):
        if not row:
            index = self.model.createIndex(self.rows[0],col)
        else:
            index = self.model.createIndex(row,col)
        return self.model.data(index,QtCore.Qt.DisplayRole)

class Publish:
    
    def __init__(self,master_input,parent=None):
        
        self.master_input = master_input

        self._app = sgtk.platform.current_bundle()
        self._sg = self._app.shotgun
        self.project = self._app.context.project
        self.shot_name = self.master_input.entity_name
        self.seq_type = self.master_input.type
        self.user = self._app.context.user
        self.version = self.master_input.version

        self.create_seq()
        self.create_shot()
        #self._get_version()
        self.create_version()
        if self.seq_type == "org":
            self.update_shot_info()

        self.nuke_retime_script = self.create_nuke_retime_script()
        self.nuke_script = self.create_nuke_script()
        self.sg_script = self.create_sg_script()
        #self.copy_script = self._create_copy_script()

        self.create_job()
        self.create_temp_job()
        self.create_rm_job()
        self.create_sg_job()
        self.create_jpg_job()
        self.create_org_job()
        self.submit_job()

        self.publish_to_shotgun()

        
    @property
    def seq_name(self):
        temp = self.shot_name.split("_")
        if len(temp) == 2:
            return temp[0]
        else:
            return temp[0]
    

    def create_job(self):


        
       
        self.job = author.Job()
        self.job.title = str('[IOM]' +self.shot_name+" publish")
        self.job.service = "Linux64"
        self.job.priority = 10

    
    

    
    def create_seq(self):
        
        key = [
                ['project','is',self.project],
                ['code','is',self.seq_name]
                ]
        
        seq_ent = self._sg.find_one('Sequence',key)
        if seq_ent:
            self.seq_ent = seq_ent
            return
        desc = {
                'project' :self.project,
                'code' : self.seq_name
                }
        self.seq_ent = self._sg.create("Sequence",desc)
        return 


    def create_shot(self):
        print "create Shot"

        key = [
                ['project','is',self.project],
                ['sg_sequence','is',self.seq_ent],
                ['code','is',self.shot_name]
                ]

        shot_ent = self._sg.find_one('Shot',key)
        if shot_ent:
            self.shot_ent = shot_ent
            return
        desc = {
                'project' : self.project,
                'sg_sequence': self.seq_ent,
                'code' : self.shot_name
                }
        self.shot_ent = self._sg.create("Shot",desc)
        return 
        
    def update_shot_info(self):
        desc = {
                "sg_cut_in" : 1001,
                "sg_cut_out" : 1000+len(self.copy_file_list),
                "sg_cut_duration": len(self.copy_file_list),
                "sg_timecode_in": self.master_input.timecode_in,
                "sg_timecode_out": self.master_input.timecode_out,
                "sg_resolution": self.master_input.resolution,

               }

        self._sg.update("Shot",self.shot_ent['id'],desc)
    
    

    def create_org_job(self):
        if self.master_input.retime_job:
            self.org_task = author.Task(title = "create org")
            cmd = ['rez-env','nuke','--','nuke','-ix',self.nuke_retime_script]
            if not self.colorspace.find("ACES") == -1: 
                cmd = ['rez-env','nuke','ocio_config','--','nuke','-ix',self.nuke_retime_script]
            command = author.Command(argv=cmd)
            self.org_task.addCommand(command)
            self.jpg_task.addChild(self.org_task)
        else:
            self.create_copy_job()
    
    def create_temp_job(self):

        if not self.master_input.retime_job:
            return

        scan_path = self.master_input.scan_path
        file_ext = self.master_input.ext
        
        self.copy_task = author.Task(title = "copy temp")
        cmd = ["/bin/mkdir","-p"]
        cmd.append(self.tmp_path)
        command = author.Command(argv=cmd)
        self.copy_task.addCommand(command)

        for index in range(0,len(self.copy_file_list)):
            cmd = ["/bin/cp","-fv"]
            cmd.append(os.path.join(scan_path,self.copy_file_list[index]))
            cmd.append(os.path.join(self.tmp_path,self.plate_file_name+"."+str(1000+index+1)+"."+file_ext))
            command = author.Command(argv=cmd)
            self.copy_task.addCommand(command)
        
        self.job.addChild(self.copy_task)
    

    def _create_copy_script(self):
        scan_path = self.master_input.scan_path
        file_ext = self.master_input.ext
        
        tmp_copy_script_file = os.path.join(self._app.sgtk.project_path,'seq',
                                self.seq_name,
                                self.shot_name,"plate",
                                self.plate_file_name+"_copy.sh")

        
        cp = "#!/bin/bash\n"
        cp += "mkdir -p {}".format(self.plate_path)
        for index in range(0,len(self.copy_file_list)):
            cp += "/bin/cp -fv {0} {1}".format(os.path.join(scan_path,
                                                       self.copy_file_list[index]),
                                          os.path.join(self.plate_path,
                                                       self.plate_file_name+"."
                                                       +str(1000+index+1)+"."
                                                       +file_ext))
            print index
        with open( tmp_copy_script_file, 'w' ) as f:
            f.write( cp )
        
        return tmp_copy_script_file

    def create_copy_job(self):
        


        #self.copy_task = author.Task(title = "copy org")
        #cmd = ["/bin/sh",self.copy_script]
        #command = author.Command(argv=cmd)
        #self.copy_task.addCommand(command)
        #self.jpg_task.addChild(self.copy_task)

        scan_path = self.master_input.scan_path
        file_ext = self.master_input.ext
        
        self.copy_task = author.Task(title = "copy org")
        cmd = ["/bin/mkdir","-p"]
        cmd.append(self.plate_path)
        command = author.Command(argv=cmd)
        self.copy_task.addCommand(command)

        for index in range(0,len(self.copy_file_list)):
            cmd = ["/bin/cp","-fv"]
            cmd.append(os.path.join(scan_path,self.copy_file_list[index]))
            cmd.append(os.path.join(self.plate_path,self.plate_file_name+"."+str(1000+index+1)+"."+file_ext))
            command = author.Command(argv=cmd)
            self.copy_task.addCommand(command)
        
        self.jpg_task.addChild(self.copy_task)
    
    def create_version(self):
        
        if self.seq_type == "org":
            version_type = "org"
        else:
            version_type = "src"

        mov_path = os.path.join(self._app.sgtk.project_path,'seq',
                                self.seq_name,
                                self.shot_name,"plate",
                                self.plate_file_name+".mov")
        
        mov_name = self.plate_file_name+".mov"
        read_path = os.path.join(self.plate_path,self.plate_file_name+".%04d."+self.file_ext)
        
        key = [
                ['entity','is',self.shot_ent],
                ['code','is',mov_name]
                ]
        if self._sg.find_one("Version",key):
            self.version_ent = self._sg.find_one("Version",key)
            return
        desc = {
                "project" : self.project,
                "code" : mov_name,
                "sg_status_list" : "rev",
                'entity' : self.shot_ent,
                "sg_path_to_movie" : mov_path,
                "sg_path_to_frames" : read_path,
                "sg_version_type" : version_type,
                }
        self.version_ent = self._sg.create("Version",desc)
    
    def create_jpg_job(self):

        self.jpg_task = author.Task(title = "render jpg")
        cmd = ['rez-env','nuke','--','nuke','-ix',self.nuke_script]
        if not self.colorspace.find("ACES") == -1: 
            cmd = ['rez-env','nuke','ocio_config','--','nuke','-ix',self.nuke_script]
        command = author.Command(argv=cmd)
        self.jpg_task.addCommand(command)
        self.sg_task.addChild(self.jpg_task)
    
    def create_sg_job(self):

        self.sg_task = author.Task(title = "sg version")
        cmd = ['rez-env','shotgunapi','--','python',self.sg_script]
        command = author.Command(argv=cmd)
        self.sg_task.addCommand(command)
        self.rm_task.addChild(self.sg_task)
    
    def create_rm_job(self):

        self.rm_task = author.Task(title = "rm")
        cmd = ['rm','-f',self.nuke_script]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)
        
        if self.master_input.retime_job:
            cmd = ['rm','-f',self.nuke_retime_script]
            command = author.Command(argv=cmd)
            self.rm_task.addCommand(command)

        cmd = ['rm','-f',self.sg_script]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)

        #cmd = ['rm','-f',self.copy_script]
        #command = author.Command(argv=cmd)
        #self.rm_task.addCommand(command)
        
        self.job.addChild(self.rm_task)
    
    def submit_job(self):

        self.job.spool(hostname="10.0.20.81",owner="west")

    def create_nuke_retime_script(self):

        app = sgtk.platform.current_bundle()
        context = app.context
        project = context.project
        shotgun = app.sgtk.shotgun

        output_info = shotgun.find_one("Project",[['id','is',project['id']]],
                               ['sg_colorspace','sg_mov_codec',
                               'sg_out_format','sg_fps','sg_mov_colorspace'])

    
    
        setting = Output(output_info)

        if not self.master_input.retime_job:
            return
        
        scan_path = os.path.join(self.master_input.scan_path,
                                 self.master_input.scan_name
                                 +"."+self.master_input.pad
                                 +"."+self.master_input.ext
                                 )
        org_path = os.path.join(self.plate_path,self.plate_file_name+".%04d."+self.file_ext)
        tmp_nuke_script_file = os.path.join(self._app.sgtk.project_path,'seq',
                                self.seq_name,
                                self.shot_name,"plate",
                                self.plate_file_name+"_retime.py")

        nk = ''
        nk += 'import nuke\n'
        nk += 'nuke.knob("root.first_frame", "{}" )\n'.format(int(self.master_input.start_frame))
        nk += 'nuke.knob("root.last_frame", "{}" )\n'.format(int(self.master_input.end_frame))
        for info in self.master_input.retime_info:
            print info['retime_start_frame']
            nk += '\n'
            nk += '\n'
            nk += 'read = nuke.nodes.Read( file="{}" )\n'.format( scan_path )
            nk += 'read["colorspace"].setValue("{}")\n'.format(setting.colorspace)
            nk += 'read["first"].setValue( {} )\n'.format(int(self.master_input.start_frame))
            nk += 'read["last"].setValue( {} )\n'.format( int(self.master_input.end_frame))
            nk += 'read["frame"].setValue( "frame+{}")\n'.format( int(info['just_in']-1))
            tg = 'read'

            nk += 'retime = nuke.nodes.Retime(inputs = [%s])\n'% tg
            nk += 'retime["input.first_lock"].setValue( "true" )\n'
            nk += 'retime["input.last"].setValue({} )\n'.format(int(self.master_input.end_frame))
            if int (info['retime_percent']) < 0:
                nk += 'retime["reverse"].setValue( "true" )\n'
                nk += 'retime["speed"].setValue( {})\n'.format(-float(info['retime_percent'])/100.0)
            else:
                nk += 'retime["speed"].setValue( {})\n'.format(float(info['retime_percent'])/100.0)
            nk += 'retime["filter"].setValue( "none" )\n'
            nk += 'retime["output.first_lock"].setValue( "true" )\n'
            tg = 'retime'
            nk += 'output = "{}"\n'.format( org_path )
            nk += 'write = nuke.nodes.Write(inputs = [%s],file=output )\n'% tg
            nk += 'write["file_type"].setValue( "{}" )\n'.format(self.file_ext)
            if self.file_ext == "exr":
                nk += 'write["compression"].setValue("PIZ Wavelet (32 scanlines)")\n'
            nk += 'write["create_directories"].setValue(True)\n'
            nk += 'write["colorspace"].setValue("{}")\n'.format(setting.colorspace)
            nk += 'write["frame"].setValue( "frame+1000+{}")\n'.format( int(info['retime_start_frame']-1))
            nk += 'nuke.execute(write,1,{},1)\n'.format(int(info['retime_duration']))
        
        nk += 'exit()\n'

        if not os.path.exists( os.path.dirname(tmp_nuke_script_file) ):
            cur_umask = os.umask(0)
            os.makedirs(os.path.dirname(tmp_nuke_script_file),0777 )
            os.umask(cur_umask)

        with open( tmp_nuke_script_file, 'w' ) as f:
            f.write( nk )
        return tmp_nuke_script_file

    def create_nuke_script(self):
        
        width,height = self.master_input.resolution.split("x")
        app = sgtk.platform.current_bundle()
        context = app.context
        project = context.project
        shotgun = app.sgtk.shotgun

        output_info = shotgun.find_one("Project",[['id','is',project['id']]],
                               ['sg_colorspace','sg_mov_codec',
                               'sg_out_format','sg_fps','sg_mov_colorspace'])

    
    
        setting = Output(output_info)

        self.colorspace = setting.colorspace
        
        jpg_path = os.path.join(self.plate_jpg_path,self.plate_file_name+".%04d.jpg")
        jpg_2k_path = os.path.join(self.plate_jpg_2k_path,self.plate_file_name+".%04d.jpg")
        read_path = os.path.join(self.plate_path,self.plate_file_name+".%04d."+self.file_ext)
        tmp_nuke_script_file = os.path.join(self._app.sgtk.project_path,'seq',
                                self.seq_name,
                                self.shot_name,"plate",
                                self.plate_file_name+".py")

        mov_path = os.path.join(self._app.sgtk.project_path,'seq',
                                self.seq_name,
                                self.shot_name,"plate",
                                self.plate_file_name+".mov")
        
        if self.master_input.retime_job:
            frame_count = sum([x['retime_duration'] for x in self.master_input.retime_info ])
        else:
            frame_count = len(self.copy_file_list)

        nk = ''
        nk += 'import nuke\n'
        nk += 'nuke.knob("root.first_frame", "{}" )\n'.format(1001)
        nk += 'nuke.knob("root.last_frame", "{}" )\n'.format(int(1000+frame_count))
        #nk += 'nuke.knob("root.fps", "{}" )\n'.format( framerate )
        nk += 'read = nuke.nodes.Read( name="Read1",file="{}" )\n'.format( read_path )
        nk += 'read["first"].setValue( {} )\n'.format( 1001 )
        nk += 'read["last"].setValue( {} )\n'.format(int(1000+frame_count))
        if self.file_ext  in ["dpx"] : 
            nk += 'read["colorspace"].setValue("{}")\n'.format(setting.mov_colorspace)
        tg = 'read'
    
        #gizmo = ''

        #if gizmo:
        #    nk += 'giz = nuke.createNode("stamp_wswg_wygbrowser.gizmo")\n'
        #    nk += 'giz.setInput( 0, read )\n'
        #    nk += "giz['project'].setValue( '{}' )\n".format( showname )
        #    tg = 'giz'
        #if os.path.exists(lut) :
        #    nk += 'vf = nuke.nodes.Vectorfield( inputs = [%s], '% tg
        #    nk += 'vfield_file = "{}",'.format( lut )
        #    nk += 'colorspaceIn="{}",'.format( cs_in )
        #    nk += 'colorspaceOut ="{}" )\n'.format( cs_out )
        #    tg = 'vf'
        if int(width) > 2048:
            
            nk += 'reformat = reformat = nuke.nodes.Reformat(inputs=[%s],type=2,scale=.5)\n' %tg
            reformat = 'reformat'
            nk += 'output = "{}"\n'.format( jpg_2k_path )
            nk += 'write   = nuke.nodes.Write(name="ww_write_2k", inputs = [%s],file=output )\n'% reformat
            nk += 'write["file_type"].setValue( "jpeg" )\n'
            nk += 'write["create_directories"].setValue(True)\n'
            nk += 'write["colorspace"].setValue("{}")\n'.format(setting.mov_colorspace)
            nk += 'write["_jpeg_quality"].setValue( 1.0 )\n'
            nk += 'write["_jpeg_sub_sampling"].setValue( "4:4:4" )\n'
            nk += 'nuke.execute(write,1001,{},1)\n'.format(int(1000+frame_count))

        nk += 'output = "{}"\n'.format( jpg_path )
        nk += 'write   = nuke.nodes.Write(name="ww_write", inputs = [%s],file=output )\n'% tg
        nk += 'write["file_type"].setValue( "jpeg" )\n'
        nk += 'write["create_directories"].setValue(True)\n'
        nk += 'write["colorspace"].setValue("{}")\n'.format(setting.mov_colorspace)
        nk += 'write["_jpeg_quality"].setValue( 1.0 )\n'
        nk += 'write["_jpeg_sub_sampling"].setValue( "4:4:4" )\n'
        #nk += 'nuke.scriptSaveAs( "{}",overwrite=True )\n'.format( nuke_file )
        nk += 'nuke.execute(write,1001,{},1)\n'.format(int(1000+frame_count))

        if int(width) > 2048:
            nk += 'reformat = reformat = nuke.nodes.Reformat(inputs=[%s],type=2,scale=.5)\n' %tg
            reformat = 'reformat'
        nk += 'output = "{}"\n'.format( mov_path )
        if int(width) > 2048:
            nk += 'write   = nuke.nodes.Write(name="mov_write", inputs = [%s],file=output )\n'% reformat
        else:
            nk += 'write   = nuke.nodes.Write(name="mov_write", inputs = [%s],file=output )\n'% tg
        nk += 'write["file_type"].setValue( "mov" )\n'
        nk += 'write["create_directories"].setValue(True)\n'
        nk += 'write["mov64_codec"].setValue( "apcn")\n'
        nk += 'write["colorspace"].setValue("{}")\n'.format(setting.mov_colorspace)
        nk += 'write["mov64_fps"].setValue({})\n'.format(self.master_input.framerate)
        #nk += 'write["colorspace"].setValue( "Cineon" )\n'
        #nk += 'nuke.scriptSaveAs( "{}",overwrite=True )\n'.format( nuke_file )
        nk += 'nuke.execute(write,1001,{},1)\n'.format(int(1000+frame_count))
        nk += 'exit()\n'


        
        if not os.path.exists( os.path.dirname(tmp_nuke_script_file) ):
            cur_umask = os.umask(0)
            os.makedirs(os.path.dirname(tmp_nuke_script_file),0777 )
            os.umask(cur_umask)

        with open( tmp_nuke_script_file, 'w' ) as f:
            f.write( nk )
        print tmp_nuke_script_file
        return tmp_nuke_script_file
    
    def create_sg_script(self):

        tmp_sg_script_file = os.path.join(self._app.sgtk.project_path,'seq',
                                self.seq_name,
                                self.shot_name,"plate",
                                self.plate_file_name+"_sg.py")

        mov_path = os.path.join(self._app.sgtk.project_path,'seq',
                                self.seq_name,
                                self.shot_name,"plate",
                                self.plate_file_name+".mov")
        #shotgun 

        nk = ''
        nk += 'import shotgun_api3\n'
        nk += 'WW_SG_HOST = "https://west.shotgunstudio.com"\n'
        nk += 'script_name = "westworld_util"\n'
        nk += 'script_key = "yctqnqdjd0bttz)ornewKuitt"\n'
        nk += 'sg = shotgun_api3.Shotgun(WW_SG_HOST,script_name = script_name,api_key=script_key)\n'
        nk += 'sg.upload( "Version", %s, "%s", "sg_uploaded_movie" )\n'%(self.version_ent['id'],mov_path)



        

        with open( tmp_sg_script_file, 'w' ) as f:
            f.write( nk )
        print tmp_sg_script_file
        return tmp_sg_script_file

    @property
    def plate_file_name(self):
        temp = self.shot_name + "_"+self.seq_type+"_v%03d"%self.version
        return temp
    
    @property
    def copy_file_list(self):
        
        file_list = []

        scan_path = self.master_input.scan_path
        start_index = self.master_input.just_in
        end_index = self.master_input.just_out
        pad = self.master_input.pad
        file_name  = self.master_input.scan_name
        file_ext = self.master_input.ext
        sequence = pyseq.get_sequences(scan_path)
        if sequence[0].length() == 1 :
            file_list.append(sequence[0].head())
            return file_list
        file_format = sequence[0].format("%h%p%t")
        
        for i in range(int(start_index),int(end_index)+1):
            copy_file = file_format%i
            file_list.append(copy_file)
        
        return file_list




    
    def _get_model_data(self,colname):
        
        col = MODEL_KEYS[colname]

        index = self.model.createIndex(self.row,col)
        return self.model.data(index,QtCore.Qt.DisplayRole )

    def _get_version(self):
        key = [
                ['project','is',self.project],
                ['entity','is',self.shot_ent],
                ["published_file_type","is",self.published_file_type],
                ['name','is',self.version_file_name]
               ]
        published_ents = self._sg.find("PublishedFile",key,['version_number'])
        print published_ents
        if not published_ents:
            self.version = 1
        else:
            self.version = published_ents[-1]['version_number']
            
    
    @property
    def file_ext(self):
        return self.master_input.ext

    @property
    def published_file_type(self):
        if self.seq_type == "org":
            key  = [['code','is','Plate']]
            return self._sg.find_one("PublishedFileType",key,['id'])
        else:
            key  = [['code','is','Source']]
            return self._sg.find_one("PublishedFileType",key,['id'])

    @property
    def plate_path(self):
        
        temp = os.path.join(self._app.sgtk.project_path,'seq',self.seq_name,
               self.shot_name,"plate",self.seq_type,"v%03d"%self.version)
        return temp

    @property
    def tmp_path(self):
        
        temp = os.path.join(self._app.sgtk.project_path,'seq',self.seq_name,
               self.shot_name,"plate","tmp","v%03d"%self.version)
        return temp

    @property
    def plate_jpg_path(self):

        temp = os.path.join(self._app.sgtk.project_path,'seq',self.seq_name,
               self.shot_name,"plate",self.seq_type,"v%03d_jpg"%self.version)
        return temp

    @property
    def plate_jpg_2k_path(self):

        temp = os.path.join(self._app.sgtk.project_path,'seq',self.seq_name,
               self.shot_name,"plate",self.seq_type,"v%03d_jpg_2k"%self.version)
        return temp

    @property
    def plate_file_name(self):
        temp = self.shot_name + "_"+self.seq_type+"_v%03d"%self.version
        return temp

    @property
    def version_file_name(self):
        temp = self.shot_name + "_"+self.seq_type
        return temp
    
    def _check_version(self):
        key = [
                ['project','is',self.project],
                ['entity','is',self.shot_ent],
                ["published_file_type","is",self.published_file_type],
                ['name','is',self.version_file_name],
                ['version_number','is',int(self.version)]
               ]
        published_ents = self._sg.find("PublishedFile",key,['version_number'])
        if published_ents:
            return True
        else:
            return False

    def publish_to_shotgun(self):
        
        context = sgtk.Context(self._app.tank,project = self.project,
                               entity = self.shot_ent,
                               step = None,
                               task = None,
                               user = self.user)

        file_ext = self.master_input.ext
        

        if self._check_version():
            return

        if self.seq_type == "org":
            published_type = "Plate"
        else:
            published_type = "Source"
            

        publish_data = {
            "tk": self._app.tank,
            "context": context,
            "path": os.path.join(self.plate_path,self.plate_file_name+".%04d."+file_ext),
            "name": self.version_file_name,
            "created_by": self.user,
            "version_number": self.version,
            #"thumbnail_path": item.get_thumbnail_as_path(),
            "published_file_type": published_type,
            #"dependency_paths": publish_dependencies
        }

        sgtk.util.register_publish(**publish_data)

