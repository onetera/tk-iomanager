
import os
import sgtk
from sgtk.platform.qt import QtCore, QtGui
import tractor.api.author as author


class Publish:
    
    def __init__(self,model,row,parent=None):
        
        self.model = model
        self.row = row

        self._app = sgtk.platform.current_bundle()
        self._sg = self._app.shotgun
        self.project = self._app.context.project
        self.shot_name = self._get_model_data(2)
        self.seq_type = self._get_model_data(3)
        self.user = self._app.context.user

        self.create_seq()
        self.create_shot()
        self._get_version()
        self.create_version()
        if self.seq_type == "org":
            self.update_shot_info()

        self.nuke_script = self.create_nuke_script()
        self.sg_script = self.create_sg_script()

        self.create_job()
        self.create_rm_job()
        self.create_sg_job()
        self.create_jpg_job()
        self.create_copy_job()
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
        print "create seq"
        
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
                "sg_timecode_in": self._get_model_data(12),
                "sg_timecode_out": self._get_model_data(13),

               }

        self._sg.update("Shot",self.shot_ent['id'],desc)
    

    def create_copy_job(self):

        
        scan_path = self._get_model_data(4)
        file_ext = self._get_model_data(7)
        
        self.copy_task = author.Task(title = "copy files")
        cmd = ["/bin/mkdir","-p"]
        cmd.append(self.plate_path)
        command = author.Command(argv=cmd)
        self.copy_task.addCommand(command)

        for index in range(0,len(self.copy_file_list)):
            cmd = ["/bin/cp","-fv"]
            cmd.append(os.path.join(scan_path,self.copy_file_list[index]))
            cmd.append(os.path.join(self.plate_path,self.plate_file_name+"."+str(1000+index+1)+"."+file_ext))
            print cmd
            command = author.Command(argv=cmd)
            self.copy_task.addCommand(command)
        
        self.jpg_task.addChild(self.copy_task)
    
    def create_version(self):
        
        
        mov_path = os.path.join(self._app.sgtk.project_path,'seq',
                                self.seq_name,
                                self.shot_name,"plate",
                                self.plate_file_name+".mov")
        
        mov_name = self.plate_file_name+".mov"
        
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
                "sg_version_type" : self.seq_type,
                }
        self.version_ent = self._sg.create("Version",desc)
    
    def create_jpg_job(self):
        self.jpg_task = author.Task(title = "render jpg")
        cmd = ['rez-env','nuke','--','nuke','-ix',self.nuke_script]
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

        cmd = ['rm','-f',self.sg_script]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)
        
        self.job.addChild(self.rm_task)
    
    def submit_job(self):

        self.job.spool(hostname="10.0.20.81",owner="west")




    def create_nuke_script(self):
        
        jpg_path = os.path.join(self.plate_jpg_path,self.plate_file_name+".%04d.jpg")
        read_path = os.path.join(self.plate_path,self.plate_file_name+".%04d."+self.file_ext)
        tmp_nuke_script_file = os.path.join(self._app.sgtk.project_path,'seq',
                                self.seq_name,
                                self.shot_name,"plate",
                                self.plate_file_name+".py")

        mov_path = os.path.join(self._app.sgtk.project_path,'seq',
                                self.seq_name,
                                self.shot_name,"plate",
                                self.plate_file_name+".mov")


        nk = ''
        nk += 'import nuke\n'
        nk += 'nuke.knob("root.first_frame", "{}" )\n'.format( "1001" )
        nk += 'nuke.knob("root.last_frame", "{}" )\n'.format("%d"%(1000+len(self.copy_file_list)) )
        #nk += 'nuke.knob("root.fps", "{}" )\n'.format( framerate )
        nk += 'read = nuke.nodes.Read( name="Read1",file="{}" )\n'.format( read_path )
        nk += 'read["first"].setValue( {} )\n'.format( "1001" )
        nk += 'read["last"].setValue( {} )\n'.format( "%d"%(1000+len(self.copy_file_list)) )
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

        nk += 'output = "{}"\n'.format( jpg_path )
        nk += 'write   = nuke.nodes.Write(name="ww_write", inputs = [%s],file=output )\n'% tg
        nk += 'write["file_type"].setValue( "jpeg" )\n'
        nk += 'write["create_directories"].setValue(True)\n'
        nk += 'write["_jpeg_quality"].setValue( 1.0 )\n'
        nk += 'write["_jpeg_sub_sampling"].setValue( "4:4:4" )\n'
        #nk += 'nuke.scriptSaveAs( "{}",overwrite=True )\n'.format( nuke_file )
        nk += 'nuke.execute(write,1001,%d,1)\n'%(1000+len(self.copy_file_list))

        nk += 'output = "{}"\n'.format( mov_path )
        nk += 'write   = nuke.nodes.Write(name="mov_write", inputs = [%s],file=output )\n'% tg
        nk += 'write["file_type"].setValue( "mov" )\n'
        nk += 'write["create_directories"].setValue(True)\n'
        nk += 'write["mov64_codec"].setValue( "apcn")\n'
        #nk += 'write["colorspace"].setValue( "Cineon" )\n'
        #nk += 'nuke.scriptSaveAs( "{}",overwrite=True )\n'.format( nuke_file )
        nk += 'nuke.execute(write,1001,%d,1)\n'%(1000+len(self.copy_file_list))



        
        if not os.path.exists( os.path.dirname(tmp_nuke_script_file) ):
            os.makedirs(os.path.dirname(tmp_nuke_script_file) )

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
        temp = self.shot_name + "_"+self.seq_type+"_v%02d"%self.version
        return temp
    
    @property
    def copy_file_list(self):
        
        file_list = []

        start_index = self._get_model_data(14)
        end_index = self._get_model_data(15)
        pad = self._get_model_data(6)
        file_name  = self._get_model_data(5)
        file_ext = self._get_model_data(7)
        
        for i in range(int(start_index),int(end_index)+1):
            copy_file = file_name + "."+pad%i+"."+file_ext
            file_list.append(copy_file)
        
        return file_list




    
    def _get_model_data(self,col):

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
            self.version = published_ents[-1]['version_number'] + 1
            
    
    @property
    def file_ext(self):
        return self._get_model_data(7)

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
    def plate_jpg_path(self):

        temp = os.path.join(self._app.sgtk.project_path,'seq',self.seq_name,
               self.shot_name,"plate",self.seq_type,"v%03d_jpg"%self.version)
        return temp

    @property
    def plate_file_name(self):
        temp = self.shot_name + "_"+self.seq_type+"_v%02d"%self.version
        return temp
    @property
    def version_file_name(self):
        temp = self.shot_name + "_"+self.seq_type
        return temp
    

    def publish_to_shotgun(self):
        
        context = sgtk.Context(self._app.tank,project = self.project,
                               entity = self.shot_ent,
                               step = None,
                               task = None,
                               user = self.user)

        file_ext = self._get_model_data(7)

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

