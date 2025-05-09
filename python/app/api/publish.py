# :coding: utf-8


import os
import datetime
import sgtk
import pyseq
import tractor.api.author as author

from sgtk.platform.qt import QtCore, QtGui
from .sg_cmd import ShotgunCommands
from .constant import *

codecs = {
    "Apple ProRes 4444": "ap4h",
    "Apple ProRes 422 HQ": "apch",
    "Apple ProRes 422": "apcn",
    "Apple ProRes 422 LT": "apcs",
    "Apple ProRes 422 Proxy": "apco",
    "Avid DNxHD 444": "AVdn",
    "Avid DNxHD 422": "AVdn",
    "Avid DnxHR 422": "AVdh"
    }

colorspace_set = {
    "ACES - ACEScg": "Output - Rec.709",
    "ACES - ACES2065-1": "Output - Rec.709",
    "AlexaV3LogC": "AlexaViewer",
    "legacy": "LegacyViewer",
    "Sony.rec709": "SonyViewer",
    "Cineon": "rec709",
    "rec709": "rec709",
    "Output - Rec.709": "Output - Rec.709",
    "Gamma2.4": "Gamma2.4",
    "Arri4.rec709": "Arri4Viewer"
}


class Output(object):

    def __init__(self, info):

        self.mov_fps = float(info['sg_fps'])
        self._set_file_type(info['sg_out_format'])
        self._set_colorspace(info['sg_colorspace'], info)
        self.mov_codec = codecs[info['sg_mov_codec']]
        if info['sg_mov_codec'] == "Avid DNxHD 444":
            self.dnxhd_profile = 'DNxHD 444 10-bit 440Mbit'
        elif info['sg_mov_codec'] == "Avid DNxHD 422":
            self.dnxhd_profile = 'DNxHD 422 10-bit 220Mbit'
        else:
            self.dnxhd_profile = ''
        if info['sg_mov_codec'] == "Avid DnxHR 422":
            self.dnxhr_profile = 'HQX 4:2:2 12-bit'
        else:
            self.dnxhr_profile = ''


    def _set_file_type(self, text):

        if text == "exr 32bit":
            self.file_type = "exr"
            self.datatype = "32 bit float"
        if text == "exr 16bit":
            self.file_type = "exr"
            self.datatype = "16 bit half"
        if text == "dpx 10bit":
            self.file_type = "dpx"
            self.datatype = "10 bit"
        if text == "dpx 12bit":
            self.file_type = "dpx"
            self.datatype = "12 bit"

    def _set_colorspace(self, text, info):

        if not text.find("ACES") == -1:
            self.colorspace = "ACES - %s" % text
            self.mov_colorspace = info['sg_mov_colorspace']
        else:
            if not info['sg_mov_colorspace']:
                self.colorspace = text
                self.mov_colorspace = text
            else:
                self.colorspace = text
                self.mov_colorspace = info['sg_mov_colorspace']


class MasterInput(object):

    def __init__(self, model, group_model_rows, entity_type):

        self.model = model
        self.rows = group_model_rows
        self.entity_type = entity_type
        self._set_data()
        self._create_retime_info()

    def _set_data(self):

        self.entity_name = self._get_data(MODEL_KEYS[self.entity_type])
        self.scan_path = self._get_data(MODEL_KEYS['scan_path'])
        self.scan_name = self._get_data(MODEL_KEYS['scan_name'])
        self.clip_name = self._get_data(MODEL_KEYS['clip_name'])
        self.version = int(self._get_data(MODEL_KEYS['version']))
        self.pad = self._get_data(MODEL_KEYS['pad'])
        self.ext = self._get_data(MODEL_KEYS['ext'])
        self.resolution = self._get_data(MODEL_KEYS['resolution'])
        self.start_frame = self._get_data(MODEL_KEYS['start_frame'])
        self.end_frame = self._get_data(MODEL_KEYS['end_frame'])
        self.duration = self._get_data(MODEL_KEYS['duration'])
        self.framerate = float(self._get_data(MODEL_KEYS['framerate']))
        self.type = self._get_data(MODEL_KEYS['type'])
        self.clip_tag = self._get_data(MODEL_KEYS['clip_tag'])

    @property
    def just_in(self):

        if len(self.rows) == 1:
            return self._get_data(MODEL_KEYS['just_in'])

        else:
            temp = []
            for row in self.rows:
                temp.append(self._get_data(MODEL_KEYS['just_in'], row))

            return min(temp)

    @property
    def just_out(self):

        if len(self.rows) == 1:
            return self._get_data(MODEL_KEYS['just_out'])

        else:
            temp = []
            for row in self.rows:
                temp.append(self._get_data(MODEL_KEYS['just_out'], row))

            return max(temp)

    @property
    def timecode_in(self):

        if len(self.rows) == 1:
            return self._get_data(MODEL_KEYS['timecode_in'])

        else:
            temp = []
            for row in self.rows:
                temp.append(self._get_data(MODEL_KEYS['timecode_in'], row))

            return min(temp)

    @property
    def timecode_out(self):

        if len(self.rows) == 1:
            return self._get_data(MODEL_KEYS['timecode_out'])

        else:
            temp = []
            for row in self.rows:
                temp.append(self._get_data(MODEL_KEYS['timecode_out'], row))

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
                info['just_in'] = self._get_data(MODEL_KEYS['just_in'], row)
                info['just_out'] = self._get_data(MODEL_KEYS['just_out'], row)
                info['retime_start_frame'] = int(self._get_data(MODEL_KEYS['retime_start_frame'], row))
                info['retime_duration'] = int(self._get_data(MODEL_KEYS['retime_duration'], row))
                info['retime_percent'] = float(self._get_data(MODEL_KEYS['retime_percent'], row))
                self.retime_info.append(info)

    def _get_data(self, col, row=None):
        if not row:
            index = self.model.createIndex(self.rows[0], col)
        else:
            index = self.model.createIndex(row, col)
        return self.model.data(index, QtCore.Qt.DisplayRole)


class Publish:
    def __init__(self, master_input, scan_colorspace, opt_dpx, opt_non_retime, opt_clip, smooth_retime, parent=None):
        self.master_input = master_input
        self.scan_colorspace = scan_colorspace
        self.use_natron = False

        self.jpg4mov_alexaV3logC_py = ''
        self.jpg4mov_output = ''
        self.tmp_dpx_to_jpg_file = ''

        self._app = sgtk.platform.current_bundle()
        self._sg = self._app.shotgun
        self.project = self._app.context.project
        self.seq_type = self.master_input.type
        self.user = self._app.context.user
        self.version = self.master_input.version
        self._context = self._app.context

        output_info = self._sg.find_one("Project", [['id', 'is', self.project['id']]],
                                        ['sg_colorspace', 'sg_mov_codec',
                                         'sg_out_format', 'sg_fps', 'sg_mov_colorspace'])

        self.setting = Output(output_info)
        self._sg_cmd = ShotgunCommands(self._app, self._sg, self.project, self.clip_project, self.user, self._context)
        ## 
        if self.seq_type == "editor":
            self._opt_dpx = False
        else:
            self._opt_dpx = opt_dpx
        self._opt_non_retime = opt_non_retime
        self._opt_clip = opt_clip
        self._smooth_retime = smooth_retime

        if self.seq_type == "lib":
            self._tag_name = self.get_tag_name(self.master_input.clip_tag)
            self.clip_lib_name = self._get_clip_lib_name()
            self._proj_ver_ent, self._clip_ver_ent = None, None
        if self._opt_clip == False:
            self.shot_name = self.master_input.entity_name
        else:
            self.shot_name = self.clip_lib_name
        self.create_seq()
        self.create_shot()
        # self._get_version()
        if self._opt_clip == False:
            self.create_version()
        if self.seq_type == "org":
            self.update_shot_info()
        self.publish_to_shotgun()
        self.publish_temp_jpg()

        if self.seq_type == "lib":
            self.create_seq(switch=True)
            self.create_shot(switch=True)
            self.create_version(switch=True)

        self.nuke_retime_script = self.create_nuke_retime_script()
        self.nuke_script = self.create_nuke_script()
        self.nuke_mov_script = self.create_mov_nuke_script()
        self.sg_script = self.create_sg_script()
        if self._opt_non_retime == True:
            self.sg_nonretime_script = self.create_sg_script(switch=True)
        # self.copy_script = self._create_copy_script()

        self.create_job()
        self.create_temp_job()
        if self.seq_type == 'lib':
            self.create_rm_job(switch=True)

            self.convert_gif_job()
            self.convert_mp4_job(switch=True)
            self.create_jpg_job(switch=True)

            self.create_clip_lib_job()
        if self.seq_type != 'lib':
            self.create_rm_job()
        self.create_sg_job()
        self.convert_mp4_job(switch=False)
        self.create_jpg_job()
        self.create_org_job()
        self.submit_job()

    @property
    def seq_name(self):
        temp = self.shot_name.split("_")
        if len(temp) == 2:
            return temp[0]
        else:
            return temp[0]

    def get_tag_name(self, tag_name):
        tag_name = tag_name.decode('utf-8')
        if tag_name == '':
            print( "###  Error! YOU SHOULD INPUT TAG!  ###" )
            return None
        if ',' in tag_name:
            tags = tag_name.split(',')
        else:
            tags = [tag_name]
        return tags

    def create_job(self):
        self.job = author.Job()
        self.job.title = str('[IOM]' + self.shot_name + " publish")
        if self.seq_type == "lib":
            self.job.service = "lib"
        else:
            self.job.service = "Linux64"
        self.job.priority = 10

    def create_seq(self, switch=False):
        if switch == False and self._opt_clip == False:
            self.seq_ent = self._sg_cmd.create_seq(self.seq_name)
        else:
            self.seq_ent = self._sg_cmd.create_seq('clip')

    def create_shot(self, switch=False):
        if switch == False and self._opt_clip == False:
            self.shot_ent = self._sg_cmd.create_shot(self.shot_name)
            print(self.shot_ent)
        else:
            tags = self._sg_cmd.get_tags(self._tag_name)
            self.shot_ent = self._sg_cmd.create_shot(self.shot_name)
            if 'tags' in self.shot_ent.keys():
                for tag in tags:
                    if tag not in self.shot_ent['tags']:
                        self.shot_ent['tags'].append(tag)
                self._sg.update('Shot', self.shot_ent['id'], {'tags': self.shot_ent['tags']})
            else:
                desc = {'tags': tags}
                self._sg.update('Shot', self.shot_ent['id'], desc)
            print(self.shot_ent)


    def update_shot_info(self):
        # ** original plate duration
        #frame_count = int(self.master_input.end_frame) - int(self.master_input.start_frame) + 1
        frame_count = int(self.master_input.just_out) - int(self.master_input.just_in) + 1
        desc = {
            "sg_cut_in": 1001,
            "sg_cut_out": 1000 + frame_count,
            "sg_cut_duration": frame_count,
            "sg_timecode_in": self.master_input.timecode_in,
            "sg_timecode_out": self.master_input.timecode_out,
            "sg_resolution": self.master_input.resolution,
            "sg_clib_name": self.master_input.clip_name,

        }

        if self.master_input.retime_job:
            frame_count = sum([x['retime_duration'] for x in self.master_input.retime_info])
            desc['sg_cut_out'] = 1000 + frame_count
            desc['sg_cut_duration'] = frame_count
            desc['sg_retime_duration'] = "\n".join([str(x['retime_duration']) for x in self.master_input.retime_info])
            desc['sg_retime_percent'] = "%\n".join(
                [str(x['retime_percent']) for x in self.master_input.retime_info]) + "%"

        self._sg.update("Shot", self.shot_ent['id'], desc)

    def create_org_job(self):
        if self._opt_non_retime == True and os.path.exists(self.plate_path):
            return None

        if self.master_input.retime_job:
            self.org_task = author.Task(title="create org")
            cmd = ['rez-env', 'nuke-12.2.2', '--', 'nuke', '-ix', self.nuke_retime_script]
            if not self.scan_colorspace.find("ACES") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'ocio_config', '--', 'nuke', '-ix', self.nuke_retime_script]
            if not self.scan_colorspace.find("Alexa") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'alexa_config', '--', 'nuke', '-ix', self.nuke_retime_script]
            if not self.scan_colorspace.find("legacy") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'legacy_config', '--', 'nuke', '-ix', self.nuke_retime_script]
            if not self.scan_colorspace.find("Sony") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'sony_config', '--', 'nuke', '-ix', self.nuke_retime_script]
            if not self.scan_colorspace.find("Arri") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'alexa4_config', '--', 'nuke', '-ix', self.nuke_retime_script]
                if self.project['name'] in ["jung"]:
                    cmd = ['rez-env', 'nuke-13', 'aces_config', '--', 'nuke', '-ix', self.nuke_retime_script]
            command = author.Command(argv=cmd)
            self.org_task.addCommand(command)
            self.jpg_task.addChild(self.org_task)

        elif self.nuke_mov_script:
            self.org_task = author.Task(title="create mov")
            cmd = ['rez-env', 'nuke-12.2.2', '--', 'nuke', '-ix', self.nuke_mov_script]
            if self.project['name'] in ["jung"]:
                cmd = ['rez-env', 'nuke-13', '--', 'nuke', '-ix', self.nuke_mov_script]
            if not self.scan_colorspace.find("ACES") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'ocio_config', '--', 'nuke', '-ix', self.nuke_mov_script]
            if not self.scan_colorspace.find( 'Output' ) == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'ocio_config', '--', 'nuke', '-ix', self.nuke_mov_script]
                if self.project['name'] in ["jung"]:
                    cmd = ['rez-env', 'nuke-13', 'ocio_config', '--', 'nuke', '-ix', self.nuke_mov_script]
            if not self.scan_colorspace.find("Alexa") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'alexa_config', '--', 'nuke', '-ix', self.nuke_mov_script]
            if not self.scan_colorspace.find("legacy") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'legacy_config', '--', 'nuke', '-ix', self.nuke_mov_script]
            if not self.scan_colorspace.find("Sony") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'sony_config', '--', 'nuke', '-ix', self.nuke_mov_script]
            if not self.scan_colorspace.find("Arri") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'alexa4_config', '--', 'nuke', '-ix', self.nuke_mov_script]
                if self.project['name'] in ["jung"]:
                    cmd = ['rez-env', 'nuke-13', 'aces_config', '--', 'nuke', '-ix', self.nuke_mov_script]
            if self._opt_dpx == True:
                if self.seq_type != 'lib' and (self.setting.mov_codec == "apch" or self.setting.mov_codec == "ap4h"):
                    cmd = ["echo", "'pass'"]
                elif self.seq_type == 'lib':
                    cmd = ["echo", "'pass'"]
            if self._opt_dpx == False and (self.setting.mov_codec == "apch" or self.setting.mov_codec == "ap4h"):
                if self.project['name'] in ['marry']:
                    if not self.scan_colorspace.find('Output') == -1:
                        cmd = ['rez-env', 'nuke-12.2.2', 'ocio_config', '--', 'nuke', '-ix', self.nuke_mov_script]
                    else:
                        cmd = ['rez-env', 'nuke-12.2.2', 'sony_config', '--', 'nuke', '-ix', self.nuke_mov_script]
                elif self.project['name'] in ['asura']:
                    cmd = ['rez-env', 'nuke-12.2.2', 'alexa_config', '--', 'nuke', '-ix', self.nuke_mov_script]
                elif self.project['name'] in ['4thlove', 'waiting']:
                    cmd = ['rez-env', 'nuke-12.2.2', 'alexa4_config', '--', 'nuke', '-ix', self.nuke_mov_script]
                elif self.scan_colorspace != 'Sony.rec709':
                    cmd = ['rez-env', 'natron', 'alexa_config', '--', 'NatronRenderer', '-t', self.nuke_mov_script]
                elif self.scan_colorspace == 'Arri4.rec709':
                    cmd = ['rez-env', 'natron', 'alexa4_config', '--', 'NatronRenderer', '-t', self.nuke_mov_script]
            # if self._opt_dpx == False and (self.setting.mov_codec == "apch" or self.setting.mov_codec == "ap4h") and self.scan_colorspace != 'Arri4.rec709' :
            #     cmd = ['rez-env', 'natron', 'alexa_config', '--', 'NatronRenderer', '-t', self.nuke_mov_script]

#            print('\n')
#            print( cmd )
#            print( self.scan_colorspace )
#            print('\n')

            command = author.Command(argv=cmd)
            self.org_task.addCommand(command)
            self.jpg_task.addChild(self.org_task)
        else:
            self.create_copy_job()


    def create_clip_lib_job(self):
        if self._opt_clip == False:
            return None

        if self.seq_type == "lib":
            self.copy_clip_lib_task = author.Task(title="copy to clip lib")
            if not os.path.exists(self.clip_lib_seq_path):
                cur_umask = os.umask(0)
                os.makedirs(self.clip_lib_seq_path, 0o777)
                os.umask(cur_umask)

            if self.master_input.ext in ['mov',"mxf"]:
                clip_mov_name = self.clip_lib_name + '.mov'
                command = ['/bin/cp', '-fv']
                target_path = self.master_input.scan_path
                target_name = self.master_input.scan_name
                command.append(os.path.join(target_path, target_name))
                command.append('/' + os.path.join('stock', 'mov', clip_mov_name))
                cmd = author.Command(argv=command)
                self.copy_clip_lib_task.addCommand(cmd)

            command = ['/bin/cp', '-R']
            if self.master_input.ext in ['dpx', 'exr']:
                target_path = self.master_input.scan_path
                command.append(os.path.join(target_path))
                command.append(os.path.join(self.clip_lib_seq_path))
                cmd = author.Command(argv=command)
                self.copy_clip_lib_task.addCommand(cmd)

            # self.cliplib_mp4_task.addChild(self.copy_clip_lib_task)
            self.jpg_task.addChild(self.copy_clip_lib_task)

    def publish_temp_jpg(self):
        if self._opt_non_retime == False or self._opt_clip == True:
            return None
        else:
            data_fields = (self.plate_path, self.plate_file_name, self.version, self.file_ext)
            self.published_tmp_ent, ent_type = self._sg_cmd.publish_temp_jpg(data_fields)

            desc = {
                    "version": self.version_tmp_ent,
                    "sg_colorspace": self.scan_colorspace
                   }

            if self.published_tmp_ent and ent_type == 'OLD' and self._opt_dpx == False:
                self._sg.update("PublishedFile", self.published_tmp_ent['id'], desc)
                return None

            desc = {
                    "version": self.version_tmp_ent,
                    "sg_colorspace": self.scan_colorspace
                   }

            self.published_tmp_ent, ent_type = self._sg_cmd.publish_temp_jpg(data_fields)

            if ent_type == 'NEW':
                self._sg.update("PublishedFile", self.published_tmp_ent['id'], desc)

    def _create_temp_jpg_job(self, temp_path, temp_name):
        self.copy_jpg_task = author.Task(title="copy temp jpg")
        read_path = os.path.join(temp_path, temp_name + ".%04d." + self.master_input.ext)
        tmp_org_jpg_script = self.create_nuke_temp_script(read_path)

        if not self.scan_colorspace.find("ACES") == -1:
            cmd = ['rez-env', 'nuke-12.2.2', 'ocio_config', '--', 'nuke', '-ix', tmp_org_jpg_script]
        if not self.scan_colorspace.find("Alexa") == -1:
            cmd = ['rez-env', 'nuke-12.2.2', 'alexa_config', '--', 'nuke', '-ix', tmp_org_jpg_script]
        if not self.scan_colorspace.find("legacy") == -1:
            cmd = ['rez-env', 'nuke-12.2.2', 'legacy_config', '--', 'nuke', '-ix', tmp_org_jpg_script]
        if not self.scan_colorspace.find("Sony") == -1:
            cmd = ['rez-env', 'nuke-12.2.2', 'sony_config', '--', 'nuke', '-ix', tmp_org_jpg_script]
        if not self.scan_colorspace.find("Arri") == -1:
            cmd = ['rez-env', 'nuke-12.2.2', 'alexa4_config', '--', 'nuke', '-ix', tmp_org_jpg_script]

        command = author.Command(argv=cmd)
        self.copy_jpg_task.addCommand(command)
        if not os.path.exists(temp_path+'/'+temp_name+'.1001.'+self.master_input.ext):
            self.copy_jpg_task.addChild(self.copy_task)
        cmd = ['rm', '-f', tmp_org_jpg_script]
        self.tmp_rm_jpg_task = author.Task(title='rm tmp jpg')
        command = author.Command(argv=cmd)
        self.tmp_rm_jpg_task.addCommand(command)
        cmd = ['rm', '-rf', self.tmp_path]
        command = author.Command(argv=cmd)
        self.tmp_rm_jpg_task.addCommand(command)
        self.tmp_rm_jpg_task.addChild(self.copy_jpg_task)

    def create_temp_job(self):
        if self._opt_non_retime == False and not self.master_input.retime_job:
            return None
        if self.seq_type == 'lib':
            return None

        file_ext = self.master_input.ext
        temp_path = self.plate_path.replace('v%03d' % self.version, 'v%03d' % (self.version + 1))
        temp_name = self.plate_file_name.replace('v%03d' % self.version, 'v%03d' % (self.version + 1))

        trigger = False
        file_list = self.copy_file_list
        if os.path.exists(self.tmp_path+'/'+self.plate_file_name+'.1001.'+file_ext):
            trigger = True
            file_list = os.listdir(self.tmp_path)

        self.copy_task = author.Task(title="copy temp")
        cmd = ["/bin/mkdir", "-p"]
        if trigger == True:
            cmd.append(temp_path)
        else:
            cmd.append(self.tmp_path)
        command = author.Command(argv=cmd)
        self.copy_task.addCommand(command)

        for index in range(0, len(file_list)):
            cmd = ["/bin/cp", "-fv"]
            frame_number = str(1000 + index + 1)
            if trigger == True:
                cmd.append(os.path.join(self.tmp_path, self.plate_file_name+'.{}.{}'.format(frame_number, file_ext)))
                cmd.append(os.path.join(temp_path, temp_name+'.{}.{}'.format(frame_number, file_ext)))
            else:
                cmd.append(os.path.join(self.master_input.scan_path, self.copy_file_list[index]))
                cmd.append(os.path.join(self.tmp_path, self.plate_file_name + ".{}.{}".format(frame_number, file_ext)))
            command = author.Command(argv=cmd)
            self.copy_task.addCommand(command)
        if self._opt_non_retime == True:
            self._create_temp_jpg_job(temp_path, temp_name)
        else:
            self.job.addChild(self.copy_task)

    def _create_copy_script(self):
        scan_path = self.master_input.scan_path
        file_ext = self.master_input.ext

        tmp_copy_script_file = os.path.join(self._app.sgtk.project_path, 'seq',
                                            self.seq_name,
                                            self.shot_name, "plate",
                                            self.plate_file_name + "_copy.sh")

        cp = "#!/bin/bash\n"
        cp += "mkdir -p {}".format(self.plate_path)
        for index in range(0, len(self.copy_file_list)):
            cp += "/bin/cp -fv {0} {1}".format(os.path.join(scan_path,
                                                            self.copy_file_list[index]),
                                               os.path.join(self.plate_path,
                                                            self.plate_file_name + "."
                                                            + str(1000 + index + 1) + "."
                                                            + file_ext))
            print(index)
        with open(tmp_copy_script_file, 'w') as f:
            f.write(cp)

        return tmp_copy_script_file

    def create_copy_job(self):

        # self.copy_task = author.Task(title = "copy org")
        # cmd = ["/bin/sh",self.copy_script]
        # command = author.Command(argv=cmd)
        # self.copy_task.addCommand(command)
        # self.jpg_task.addChild(self.copy_task)

        scan_path = self.master_input.scan_path
        file_ext = self.master_input.ext

        self.copy_task = author.Task(title="copy org")
        if self.seq_type != 'lib':
            cmd = ["/bin/mkdir", "-p"]
            cmd.append(self.plate_path)
            command = author.Command(argv=cmd)
            self.copy_task.addCommand(command)

        if self.seq_type != "lib":
            for index in range(0, len(self.copy_file_list)):
                cmd = ["/bin/cp", "-fv"]
                cmd.append(os.path.join(scan_path, self.copy_file_list[index]))
                if self.seq_type != 'lib':
                    cmd.append(os.path.join(self.plate_path, self.plate_file_name + "." + str(1000 + index + 1) + "." + file_ext))
                else:
                    cmd.append(os.path.join(self.clip_lib_seq_path, self.clip_lib_name + "." + str(1000 + index + 1) + "." + file_ext))
                command = author.Command(argv=cmd)
                self.copy_task.addCommand(command)
        else:
            cp_script_path = os.path.join(self.clip_lib_seq_path, self.clip_lib_name + "_cp.py")
            cp_cmd = "import shutil\n"
            cp_cmd += "import os\n"
            cp_cmd += "src_dir = '{}'\n".format(scan_path)
            cp_cmd += "dest_dir = '{}'\n".format(self.clip_lib_seq_path)
            cp_cmd += "clip_lib_name = '{}'\n".format(self.clip_lib_name)
            cp_cmd += "cnt = 0\n"
            cp_cmd += "for x in sorted(os.listdir(src_dir)):\n"
            cp_cmd += "    src_path = os.path.join(src_dir, x)\n"
            cp_cmd += "    dest_path = os.path.join(dest_dir, '{}.{}.exr'.format(clip_lib_name, str(1001+cnt)))\n"
            cp_cmd += "    shutil.copyfile(src_path, dest_path)\n"
            cp_cmd += "    cnt += 1\n"
            cp_cmd += "exit()\n"
            with open(cp_script_path, 'w') as file:
                file.write(cp_cmd)
            file.close()
            print(cp_script_path)
            commands = ["python", cp_script_path]
            command = author.Command(argv=commands)
            self.copy_task.addCommand(command)
        self.jpg_task.addChild(self.copy_task)

    def create_version(self, switch=False):
        version = self.version

        # ver_path = self.plate_path+'/'+self.plate_file_name+'.1001.'+self.master_input.ext
        # print "==== version path ===="
        # print ver_path
        # print "======================"
        if switch == True and self._opt_non_retime == True:
            version += 1

        if self.seq_type == "org":
            version_type = "org"
        elif self.seq_type == "ref":
            version_type = "ref"
        elif self.seq_type == "editor":
            version_type = "editor"
        else:
            version_type = "src"

        plate_seq_path = self.plate_path.replace('v%03d'%self.version, 'v%03d'%version)
        plate_name = self.shot_name + "_" + version_type + "_v%03d" % version
        mov_path = os.path.join(self._app.sgtk.project_path, 'seq',
                                self.seq_name,
                                self.shot_name, "plate",
                                plate_name + ".mov")
        if switch == True and self.seq_type == "lib":
            plate_name = self.clip_lib_name
            mov_path = os.path.join(self.seq_name,
                                    self.shot_name,
                                    plate_name + ".mov")

        read_path = os.path.join(plate_seq_path, plate_name + ".%04d." + self.file_ext)
        if self.master_input.ext in ["mov","mxf"] and self.seq_type != 'lib':
            # colorspace = self.scan_colorspace.replace("ACES-", "")

            read_path = os.path.join(self._app.sgtk.project_path, 'seq',
                                     self.seq_name,
                                     self.shot_name, "plate",
                                     self.plate_file_name + ".mov")

        key = [
               ['entity', 'is', self.shot_ent],
               ['code', 'is', plate_name+".mov"]
              ]

        project_info = self.project
        if self._opt_dpx == True:
            read_path = os.path.join(self.plate_path, self.plate_file_name + ".%04d.dpx")
        if self.seq_type == "lib" and switch == True:
            project_info = self.clip_project
        if self.seq_type == 'lib':
            file_type = 'exr'
            if self.master_input.ext in ['mov','mxf']:
                file_type = 'dpx'
            read_path = os.path.join(self.clip_lib_seq_path, self.clip_lib_name + ".%04d." + file_type)
            mov_path = '/' + os.path.join('stock', 'mov', self.clip_lib_name + ".mov")

        desc = {
                "project": project_info,
                "code": plate_name+".mov",
                "sg_status_list": "fin",
                'entity': self.shot_ent,
                "sg_path_to_movie": mov_path,
                "sg_path_to_frames": read_path,
                "sg_first_frame": 1,
                "sg_just_in": int( self.master_input.just_in ),
                "sg_just_out": int( self.master_input.just_out ),
                "sg_scan_name": self.master_input.scan_name,
                "sg_clip_name": self.master_input.clip_name,
                "sg_timecode_in": self.master_input.timecode_in,
                "sg_timecode_out": self.master_input.timecode_out,
                "sg_version_type": version_type,
                "sg_scan_colorspace": self.scan_colorspace,
                "sg_uploaded_movie_frame_rate": float(self.master_input.framerate),
                "sg_cut_duration" :  int( self.master_input.just_out ) - int( self.master_input.just_in ) + 1 
               }
        
        if self.master_input.retime_job:
            desc['sg_retime_duration'] = "\n".join([str(x['retime_duration']) for x in self.master_input.retime_info])
            desc['sg_retime_percent'] = "%\n".join([str(x['retime_percent']) for x in self.master_input.retime_info]) + "%"
            desc["sg_retime_start_frame"] = "\n".join([str(x['retime_start_frame']) for x in self.master_input.retime_info])
        #tk-download에서 sg_cut_duration정보 필요로 인해 src, editor, org 모두 sg_cut_duration을 등록하는 방식으로 변경
        # if self.seq_type == "editor" or self.seq_type == "src":
            ## duration 값만 올라 가는 방식에서 just_out - just_in + 1 방식으로 변경
            #desc["sg_cut_duration"] = int(self.master_input.duration)
            # desc['sg_cut_duration'] = int( self.master_input.just_out ) - int( self.master_input.just_in ) + 1 




        if self._sg.find_one("Version", key):
            self.version_ent = self._sg.find_one("Version", key)
            self._sg.update("Version", self.version_ent['id'], desc)
            print( "found the existed version with switch false" )
            if switch == True and self._opt_non_retime == True:
                self. version_tmp_ent = self._sg.find_one("Version", key)
                self._sg.update("Version", self.version_tmp_ent['id'], desc)
                print( "found the existed version with switch true" )
            if self._opt_non_retime == True and switch == False:
                print( "found the existed version with switch false and nonretime true" )
                return self.create_version(switch=True)
            if self.seq_type == "lib" and switch == True:
                self._clip_ver_ent = self.version_ent
            else:
                self._proj_ver_ent = self.version_ent
            return None
        else:
            if switch == False or self.seq_type == "lib":
                self.version_ent = self._sg.create("Version", desc)
                print( "created a new version with switch false" )
            if switch == True and self._opt_non_retime == True:
                self.version_tmp_ent = self._sg.create('Version', desc)
                print( "created a new version with switch false" )
            if self._opt_non_retime == True and switch == False:
                print( "created a new version with switch false and nonretime true" )
                return self.create_version(switch=True)
            if self.seq_type == "lib" and switch == True:
                self._clip_ver_ent = self.version_ent
            else:
                self._proj_ver_ent = self.version_ent
            return None

    def create_jpg_job(self, switch=False):
        print('------------------------------------')
        print(self.scan_colorspace)
        print('------------------------------------')
        if self._opt_non_retime == True and os.path.exists(self.plate_path):
            return None

        self.jpg_task = author.Task(title="render jpg")
        cmd = ['rez-env', 'nuke-12.2.2', '--', 'nuke', '-ix', self.nuke_script]
        if self._opt_dpx == True:
            print('------------------------------------')
            print(self.project['name'])
            print('------------------------------------')
            if self.project['name'] not in ['jung', 'RND', 'marry', '4thlove', 'asura', 'waiting']:
                cmd = ['rez-env', 'natron', '--', 'NatronRenderer', '-t', self.nuke_script]
                if not self.scan_colorspace.find("ACES") == -1:
                    cmd = ['rez-env', 'natron', 'ocio_config', '--', 'NatronRenderer', '-t', self.nuke_script]
                if not self.scan_colorspace.find("Alexa") == -1:
                    cmd = ['rez-env', 'natron', 'alexa_config', '--', 'NatronRenderer', '-t', self.nuke_script]
                if not self.scan_colorspace.find("legacy") == -1:
                    cmd = ['rez-env', 'natron', 'legacy_config', '--', 'NatronRenderer', '-t', self.nuke_script]
                if not self.scan_colorspace.find("Sony") == -1:
                    cmd = ['rez-env', 'natron', 'sony_config', '--', 'NatronRenderer', '-t', self.nuke_script]
                if not self.scan_colorspace.find("Arri") == -1:
                    cmd = ['rez-env', 'natron', 'alexa4_config', '--', 'NatronRenderer', '-t', self.nuke_script]
            ### 정년이[jung] 프로젝트에서는 natron을 사용하지 않기로 I/O팀과 결정
            ##  정년이[jung] 종료 이후에는 복구가능한 코드
            else:
                if self.project['name'] in ['jung']:
                    nuke_ver = 'nuke-13'
                else:
                    nuke_ver = 'nuke-12.2.2'

                if not self.scan_colorspace.find("ACES") == -1 or self.scan_colorspace =='Output - Rec.709':
                    cmd = ['rez-env', nuke_ver, 'ocio_config', '--', 'nuke', '-ix', self.nuke_script]
                if not self.scan_colorspace.find("Alexa") == -1:
                    cmd = ['rez-env', nuke_ver, 'alexa_config', '--', 'nuke', '-ix', self.nuke_script]
                if not self.scan_colorspace.find("legacy") == -1:
                    cmd = ['rez-env', nuke_ver, 'legacy_config', '--', 'nuke', '-ix', self.nuke_script]
                if not self.scan_colorspace.find("Sony") == -1:
                    cmd = ['rez-env', nuke_ver, 'sony_config', '--', 'nuke', '-ix', self.nuke_script]
                if not self.scan_colorspace.find("Arri") == -1:
                    cmd = ['rez-env', nuke_ver, 'aces_config', '--', 'nuke', '-ix', self.nuke_script]
            
        else:
            if not self.scan_colorspace.find("ACES") == -1 or self.scan_colorspace == 'Output - Rec.709':
                cmd = ['rez-env', 'nuke-12.2.2', 'ocio_config', '--', 'nuke', '-ix', self.nuke_script]
            if not self.scan_colorspace.find("Alexa") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'alexa_config', '--', 'nuke', '-ix', self.nuke_script]
            if not self.scan_colorspace.find("legacy") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'legacy_config', '--', 'nuke', '-ix', self.nuke_script]
            if not self.scan_colorspace.find("Sony") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'sony_config', '--', 'nuke', '-ix', self.nuke_script]
            if not self.scan_colorspace.find("Arri") == -1:
                cmd = ['rez-env', 'nuke-12.2.2', 'alexa4_config', '--', 'nuke', '-ix', self.nuke_script]
        if self.master_input.ext in ["mov","mxf"] and self._opt_dpx == False:
            cmd = ["echo", "'pass'"]

        if switch == False:
            command = author.Command(argv=cmd)
            self.jpg_task.addCommand(command)
            self.mp4_task.addChild(self.jpg_task)
        else:
            command = author.Command(argv=cmd)
            self.jpg_task.addCommand(command)
            self.cliplib_gif_task.addChild(self.jpg_task)

    def convert_gif_job(self):
        if self.seq_type == "lib":
            self.cliplib_gif_task = author.Task(title='convert mot to gif')
            src_file = '/' + os.path.join('stock', 'mov', self.clip_lib_name+'.mov')
            target_file = '/' + os.path.join('stock', 'gif', self.clip_lib_name+'.gif')

            cmd = ['rez-env', 'ffmpeg', '--', 'ffmpeg']
            cmd.append("-i")
            cmd.append(src_file)
            cmd.append("-pix_fmt")
            cmd.append("rgb24")
            cmd.append("-s")
            cmd.append("320*180")
            cmd.append(target_file)
            command = author.Command(argv=cmd)
            self.cliplib_gif_task.addCommand(command)
            self.rm_task.addChild(self.cliplib_gif_task)


    def convert_mp4_job(self, switch=False):
        if switch == True and self._opt_non_retime == True:
            self.nonretime_mp4_task = author.Task(title='render nonretimed mp4')
        elif switch == True and self._opt_non_retime == False:
            return None
        else:
            self.mp4_task = author.Task(title="render mp4")
        version = self.version
        if switch == True:
            version += 1

        if self.seq_type != 'lib':
            file_name = self.plate_file_name.replace('v%03d'%self.version, 'v%03d'%version)
            mov_path = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name, self.shot_name, "plate",
                                    file_name + ".mov")
            mp4_path = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name, self.shot_name, "plate",
                                    file_name + ".mp4")
            webm_path = self.webm_path.replace(self.plate_file_name+'.webm', file_name+'.webm')
            montage_path = self.montage_path.replace(self.plate_file_name + "stream.jpeg", file_name+"stream.jpeg")
        else:
            file_name = self.clip_lib_name
            mov_path = '/' + os.path.join('stock', 'mov', file_name + ".mov")
            mp4_path = '/' + os.path.join('stock', 'mp4', file_name + ".mp4")
            webm_path = '/' + os.path.join('stock', 'mov', file_name + ".webm")
            montage_path = '/' + os.path.join('stock', 'mov', file_name + "stream.jpeg")

        command = ['rez-env', 'ffmpeg', '--', 'ffmpeg', '-y']
        command.append("-i")
        command.append(mov_path)
        command.append("-vcodec")
        command.append("libx264")
        # command.append("-r")
        # command.append("24")
        command.append("-pix_fmt")
        command.append("yuv420p")
        # command.append("-preset")
        # command.append("veryslow")
        command.append("-crf")
        command.append("18")
        command.append("-vf")
        command.append("pad='ceil(iw/2)*2:ceil(ih/2)*2'")
        command.append(mp4_path)
        command = author.Command(argv=command)
        if switch == True and self._opt_non_retime == True:
            self.nonretime_mp4_task.addCommand(command)
        else:
            if self.seq_type != 'lib':
                self.mp4_task.addCommand(command)

        command = ['rez-env', 'ffmpeg', '--', 'ffmpeg', '-y']
        command.append("-i")
        command.append(mov_path)
        command.append("-vcodec")
        command.append("libvpx")
        command.append("-pix_fmt")
        command.append("yuv420p")
        command.append("-g")
        command.append("30")
        command.append("-b:v")
        command.append("2000k")
        command.append("-quality")
        command.append("realtime")
        command.append("-cpu-used")
        command.append("0")
        command.append("-qmin")
        command.append("10")
        command.append("-qmax")
        command.append("42")
        command.append("-vf")
        command.append("pad='ceil(iw/2)*2:ceil(ih/2)*2'")
        command.append(webm_path)
        command = author.Command(argv=command)
        if switch == True and self._opt_non_retime == True:
            self.nonretime_mp4_task.addCommand(command)
        else:
            self.mp4_task.addCommand(command)

        before_change = "%s_v%03d_jpg" % (self.seq_type, self.version)
        if self.seq_type != 'lib':
            _montage_jpg_path = self.montage_jpg_path.replace(before_change, "%s_v%03d_jpg" % (self.seq_type, version))
            montage_template = os.path.join(_montage_jpg_path, self.plate_file_name + ".%04d.jpg")
            montage_template = montage_template.replace(self.plate_file_name+".%04d.jpg", file_name+".%04d.jpg")
        else:
            _montage_jpg_path = '/' + os.path.join('stock', 'thumb', "montage", self.clip_lib_name)
            montage_template = os.path.join(_montage_jpg_path, self.clip_lib_name + ".%04d.jpg")

        if not os.path.exists(_montage_jpg_path):
            os.makedirs(_montage_jpg_path)


        select_code = (int(self.master_input.just_out) - int(self.master_input.just_in)) / 30

        if self.master_input.retime_job:
            select_code = sum([x['retime_duration'] for x in self.master_input.retime_info]) / 30

        if select_code == 0:
            select_code = 1
        now_time = datetime.datetime.now()
        date_text = "drawtext='fontfile=/westworld/inhouse/ww_font/Vera.ttf:text= {} :fontcolor=white:fontsize=200:box=1:boxcolor=black@0.5:boxborderw=5'".format(now_time.strftime("%Y-%m-%d"))
        command = ['rez-env', "ffmpeg", "--", "ffmpeg", "-y"]
        command.append("-r")
        command.append("24")
        command.append("-i")
        command.append(mov_path)
        command.append("-vf")
        command.append("select='gte(n\,{0})*not(mod(n\,{0}))',{1}".format(select_code, date_text))
        command.append("-vsync")
        command.append("0")
        command.append("-f")
        command.append("image2")
        command.append(montage_template)
        command = author.Command(argv=command)
        if switch == True and self._opt_non_retime == True:
            self.nonretime_mp4_task.addCommand(command)
        else:
            self.mp4_task.addCommand(command)

        montage_template = os.path.join(_montage_jpg_path, file_name + ".*")

        command = ['montage']
        command.append(montage_template)
        command.append("-geometry")
        command.append("240x+0+0")
        command.append("-tile")
        command.append("x1")
        command.append("-format")
        command.append("jpeg")
        command.append("-quality")
        command.append("92")
        command.append(montage_path)

        command = author.Command(argv=command)
        if switch == True and self._opt_non_retime == True:
            self.nonretime_mp4_task.addCommand(command)
        else:
            self.mp4_task.addCommand(command)

        if self._opt_non_retime == True and switch == True:
            self.nonretime_mp4_task.addChild(self.tmp_rm_jpg_task)
        else:
            self.sg_task.addChild(self.mp4_task)

    def create_sg_job(self):
        self.sg_task = author.Task(title="sg version")
        cmd = ['rez-env', 'shotgunapi', '--', 'python', self.sg_script]
        command = author.Command(argv=cmd)
        self.sg_task.addCommand(command)
        if self._opt_non_retime == True:
            self.sg_nonretime_task = author.Task(title='sg nonretime version')
            cmd = ['rez-env', 'shotgunapi', '--', 'python', self.sg_nonretime_script]
            command = author.Command(argv=cmd)
            self.sg_nonretime_task.addCommand(command)
            cmd = ['rm', '-f', self.sg_nonretime_script]
            command = author.Command(argv=cmd)
            self.sg_nonretime_task.addCommand(command)
            nonretime_montage = self.montage_path.replace('v%03d'%self.version, 'v%03d'%(self.version+1))
            cmd = ['rm', '-f', nonretime_montage]
            command = author.Command(argv=cmd)
            self.sg_nonretime_task.addCommand(command)
            nonretime_webm_path = self.webm_path.replace('v%03d'%self.version, 'v%03d'%(self.version+1))
            cmd = ['rm', '-f', nonretime_webm_path]
            command = author.Command(argv=cmd)
            self.sg_nonretime_task.addCommand(command)
            self.sg_nonretime_task.addChild(self.nonretime_mp4_task)
            self.job.addChild(self.sg_nonretime_task)
            return None
        if self.seq_type != 'lib':
            self.rm_task.addChild(self.sg_task)
        else:
            self.cliplib_gif_task.addChild(self.sg_task)

    def create_rm_job(self, switch=False):
        if self._opt_non_retime == True and os.path.exists(self.plate_path):
            return None

        self.rm_task = author.Task(title="rm")
        cmd = ['rm', '-f', self.nuke_script]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)

        if self.master_input.retime_job:
            cmd = ['rm', '-f', self.nuke_retime_script]
            command = author.Command(argv=cmd)
            self.rm_task.addCommand(command)

        if self.nuke_mov_script:
            cmd = ['rm', '-f', self.nuke_mov_script]
            command = author.Command(argv=cmd)
            self.rm_task.addCommand(command)

        if switch == False:
            montage_path = self.montage_path
            montage_jpg_path = self.montage_jpg_path
            webm_path = self.webm_path
        else:
            montage_path = '/' + os.path.join('stock', 'mov', self.clip_lib_name + "stream.jpeg")
            montage_jpg_path = '/' + os.path.join('stock', 'thumb', 'montage', self.clip_lib_name)
            webm_path = '/' + os.path.join('stock', 'mov', self.clip_lib_name + ".webm")

        cmd = ['rm', '-f', self.sg_script]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)

        cmd = ['rm', '-f', montage_path]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)

        cmd = ['rm', '-rf', montage_jpg_path]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)

        cmd = ['rm', '-f', webm_path]
        command = author.Command(argv=cmd)
        self.rm_task.addCommand(command)

        if os.path.exists( self.jpg4mov_alexaV3logC_py ) : 
            cmd = ['rm', '-f', self.jpg4mov_alexaV3logC_py ]
            command = author.Command(argv=cmd)
            self.rm_task.addCommand(command)

        if self.jpg4mov_output: 
            cmd = ['rm', '-rf', os.path.dirname( self.jpg4mov_output ) ]
            command = author.Command(argv=cmd)
            self.rm_task.addCommand(command)

        if self.tmp_dpx_to_jpg_file: 
            cmd = ['rm', '-rf', self.tmp_dpx_to_jpg_file ]
            command = author.Command(argv=cmd)
            self.rm_task.addCommand(command)
        
        # cmd = ['rm','-f',self.copy_script]
        # command = author.Command(argv=cmd)
        # self.rm_task.addCommand(command)

        self.job.addChild(self.rm_task)

    def submit_job(self):

        user = os.environ['USER']
        self.job.spool(hostname="10.0.20.81", owner=user)

    def create_nuke_temp_script(self, read_path):
        width, height = self.master_input.resolution.split("x")
        temp_jpg_path = self.plate_path.replace('v%03d'%self.version, 'v%03d_jpg'%(self.version+1))
        file_name = self.plate_file_name.replace('v%03d'%self.version, 'v%03d'%(self.version+1))
        output_path = os.path.join(temp_jpg_path, file_name + ".%04d.jpg")
        in_color = self.scan_colorspace
        out_color = colorspace_set[in_color]
        tmp_org_jpg_file = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name, self.shot_name, "plate",
                                        self.plate_file_name + "_nonretime_jpg.py")
        mov_path = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name, self.shot_name, "plate",
                                self.shot_name + "_" + self.seq_type + "_v%03d.mov" % (self.version+1))
        nk = ''
        nk += self.create_dpx_to_output_script(1001, 1000 + len(self.copy_file_list), read_path, output_path,
                                               in_color, out_color, width, mov_path)
        if not os.path.exists(os.path.dirname(tmp_org_jpg_file)):
            cur_umask = os.umask(0)
            os.makedirs(os.path.dirname(tmp_org_jpg_file), 0o777)
            os.umask(cur_umask)
        with open(tmp_org_jpg_file, 'w') as f:
            f.write(nk)

        print( tmp_org_jpg_file )
        return tmp_org_jpg_file

    def create_nuke_retime_script(self):
        if self._opt_non_retime == True and os.path.exists(self.plate_path):
            return None
        app = sgtk.platform.current_bundle()
        context = app.context
        project = context.project
        shotgun = app.sgtk.shotgun

        output_info = shotgun.find_one("Project", [['id', 'is', project['id']]],
                                       ['sg_colorspace', 'sg_mov_codec',
                                        'sg_out_format', 'sg_fps', 'sg_mov_colorspace'])

        if not self.master_input.retime_job:
            return

        scan_path = os.path.join(self.master_input.scan_path,
                                 self.master_input.scan_name
                                 + self.master_input.pad
                                 + "." + self.master_input.ext
                                 )
        org_path = os.path.join(self.plate_path, self.plate_file_name + ".%04d." + self.file_ext)
        tmp_nuke_script_file = os.path.join(self._app.sgtk.project_path, 'seq',
                                            self.seq_name,
                                            self.shot_name, "plate",
                                            self.plate_file_name + "_retime.py")

        nk = ''
        nk += 'import nuke\n'
        nk += 'nuke.knob("root.first_frame", "{}" )\n'.format(int(self.master_input.start_frame))
        nk += 'nuke.knob("root.last_frame", "{}" )\n'.format(int(self.master_input.end_frame))
        for info in self.master_input.retime_info:
            print( info['retime_start_frame'] )
            nk += '\n'
            nk += '\n'
            nk += 'read = nuke.nodes.Read( file="{}" )\n'.format(scan_path)
            nk += 'read["colorspace"].setValue("{}")\n'.format(self.scan_colorspace)
            nk += 'read["first"].setValue( {} )\n'.format(int(self.master_input.start_frame))
            nk += 'read["last"].setValue( {} )\n'.format(int(self.master_input.end_frame))
            # nk += 'read["frame"].setValue( "frame+{}")\n'.format( int(info['just_in']-int(self.master_input.start_frame)))
            nk += 'read["frame"].setValue( "frame+{}")\n'.format(int(info['just_in']) - 1)
            tg = 'read'

            if int(info['retime_percent']) < 0:
                nk += 'reverse_retime = nuke.nodes.Retime(inputs = [%s])\n' % tg
                nk += 'reverse_retime["reverse"].setValue( "true" )\n'
                nk += 'reverse_retime["filter"].setValue( "none" )\n'
                nk += 'reverse_retime["input.last"].setValue({} )\n'.format(int(self.master_input.end_frame))
                # nk += 'reverse_retime["speed"].setValue(1)\n'
                tg = 'reverse_retime'

            if not self._smooth_retime:
                nk += 'retime = nuke.nodes.Retime(inputs = [%s])\n' % tg
                nk += 'retime["input.first_lock"].setValue( "true" )\n'
                nk += 'retime["input.last"].setValue({} )\n'.format(int(self.master_input.end_frame))
                if int(info['retime_percent']) < 0:
                    nk += 'retime["speed"].setValue( {})\n'.format(-float(info['retime_percent']) / 100.0)
                    nk += 'read["frame"].setValue( "frame-{}")\n'.format(int(info['just_in']) - 1)
                else:
                    nk += 'retime["speed"].setValue( {})\n'.format(float(info['retime_percent']) / 100.0)
                nk += 'retime["filter"].setValue( "none" )\n'
                nk += 'retime["output.first_lock"].setValue( "true" )\n'
            else:
                nk += 'retime = nuke.nodes.Kronos( inputs= [%s] ) \n' % tg 
                nk += 'retime["input.last"].setValue({} )\n'.format(int(round( self.master_input.end_frame)))
                if int(info['retime_percent']) < 0:
                    nk += 'retime["timingOutputSpeed"].setValue( {})\n'.format(-float(info['retime_percent']) / 100.0)
                    nk += 'read["frame"].setValue( "frame-{}")\n'.format(int(info['just_in']) - 1)
                else:
                    nk += 'retime["timingOutputSpeed"].setValue( {})\n'.format(float(info['retime_percent']) / 100.0)

            tg = 'retime'

            nk += 'output = "{}"\n'.format(org_path)
            nk += 'write = nuke.nodes.Write(inputs = [%s],file=output )\n' % tg
            nk += 'write["file_type"].setValue( "{}" )\n'.format(self.file_ext)
            if self.file_ext == "exr":
                nk += 'write["compression"].setValue("PIZ Wavelet (32 scanlines)")\n'
                nk += 'write["metadata"].setValue("all metadata except input/*")\n'
            nk += 'write["create_directories"].setValue(True)\n'
            nk += 'write["colorspace"].setValue("{}")\n'.format(self.scan_colorspace)
            nk += 'write["frame"].setValue( "frame+1000+{}")\n'.format(int(info['retime_start_frame'] - 1))
            nk += 'nuke.execute(write,1,{},1)\n'.format(int(info['retime_duration']))

        nk += 'exit()\n'

        if not os.path.exists(os.path.dirname(tmp_nuke_script_file)):
            cur_umask = os.umask(0)
            os.makedirs(os.path.dirname(tmp_nuke_script_file), 0o777)
            os.umask(cur_umask)

        with open(tmp_nuke_script_file, 'w') as f:
            f.write(nk)
        return tmp_nuke_script_file

    def create_jpg_for_mov( self , mov_path, first, last, output ):
        nk  = 'import nuke\n'
        nk += 'read = nuke.nodes.Read( file = "{}" )\n'.format( mov_path )
        nk += 'read["first"].setValue( {} )\n'.format( int(first) )
        nk += 'read["last"].setValue( {} )\n'.format( int( last) )
        nk += 'nuke.knob("root.first_frame", "{}" )\n'.format( int( first ))
        nk += 'nuke.knob("root.last_frame", "{}" )\n'.format( int( last ))
        nk += 'read["colorspace"].setValue( "AlexaV3LogC" )\n'
        nk += 'write = nuke.nodes.Write(name="ww_write", inputs = [read], file="{}" )\n'.format( output )
        nk += 'write["file_type"].setValue( "jpeg" )\n'
        nk += 'write["create_directories"].setValue(True)\n'
        nk += 'write["colorspace"].setValue("AlexaViewer")\n'
        nk += 'write["_jpeg_quality"].setValue( 1.0 )\n'
        nk += 'write["_jpeg_sub_sampling"].setValue( "4:4:4" )\n'
        nk += 'nuke.execute( write, {}, {}, 1 )\n'.format( int(first), int(last) )
        return nk




    def create_mov_nuke_script(self):
        print("create_mov_nuke_script")
        if self._opt_non_retime == True and os.path.exists(self.plate_path):
            return None

        if not self.master_input.ext  in ["mov","mxf"]:
            return

        width, height = self.master_input.resolution.split("x")

        scan_path = os.path.join(self.master_input.scan_path,
                                 self.master_input.scan_name
                                 )
        # colorspace = self.scan_colorspace.replace("ACES-", "")
        # org_path = os.path.join(self._app.sgtk.project_path, 'seq',
        #                         self.seq_name,
        #                         self.shot_name, "plate",
        #                         self.plate_file_name + "_" + colorspace + ".mov")
        mov_path = os.path.join(self._app.sgtk.project_path, 'seq',
                                self.seq_name,
                                self.shot_name, "plate",
                                self.plate_file_name + ".mov")

        tmp_nuke_script_file = os.path.join(self._app.sgtk.project_path, 'seq',
                                            self.seq_name,
                                            self.shot_name, "plate",
                                            self.plate_file_name + "_mov.py")

        if not os.path.exists( mov_path ):
            os.system( 'touch ' + mov_path )

        drama_flag = True
        if (self.setting.mov_codec == "apch" or self.setting.mov_codec == "ap4h"):
            if self.scan_colorspace == 'Sony.rec709' and self.project['name'] in ['4thlove', 'asura', 'waiting', 'marry']:
                drama_flag = False
            elif self.scan_colorspace in ['rec709', 'Output - Rec.709'] and self.project['name'] in ['marry']:
                drama_flag = False
            
            if drama_flag:
                self.use_natron = True
                # if (self.setting.mov_codec == "apch" or self.setting.mov_codec == "ap4h") and self.scan_colorspace != 'Arri4.rec709':
                #     self.use_natron = True

                nk = 'import os\n'
                nk += 'from NatronEngine import *\n'
                if self.scan_colorspace == 'AlexaV3LogC':
                    self.jpg4mov_alexaV3logC_py = os.path.join(self._app.sgtk.project_path, 'seq',
                                                        self.seq_name,
                                                        self.shot_name, "plate",
                                                        self.plate_file_name + "_jpg4mov_alexa.py")

                    self.jpg4mov_output = os.path.join( 
                                                    os.path.dirname( mov_path ), 
                                                    "_temp_jpg",
                                                    os.path.splitext( os.path.basename(mov_path) )[0] + ".%04d.jpg"
                                                    )
                    jpg4mov_nk = self.create_jpg_for_mov( 
                                                            scan_path, self.master_input.just_in, 
                                                            self.master_input.just_out, self.jpg4mov_output 
                                                        )                                    

                    with open( self.jpg4mov_alexaV3logC_py, 'w' ) as f:
                        f.write( jpg4mov_nk )
                    nk += 'os.system( "rez-env nuke-12.2.2 alexa_config -- nuke -ix {}" )\n'.format( self.jpg4mov_alexaV3logC_py )
                    # nk += 'os.remove( "{}" )\n'.format( self.jpg4mov_alexaV3logC_py )
                    nk += 'read = app.createReader("{}")\n'.format( self.jpg4mov_output )
                    nk += 'read.getParam("ocioInputSpace").setValue("rec709")\n'
                    nk += 'read.getParam("ocioOutputSpace").setValue("linear")\n'

                else:
                    nk += 'read = app.createReader("{}")\n'.format(scan_path)
                    if self.scan_colorspace == 'Arri4.rec709':
                        nk += 'read.getParam("ocioInputSpace").setValue("Arri4.rec709")\n'
                        nk += 'read.getParam("ocioOutputSpace").setValue("Arri4.rec709")\n'
                        # nk += 'read.getParam("ocioOutputSpaceIndex").setValue(1)\n'
                    else:
                        nk += 'read.getParam("ocioInputSpace").setValue("color_picking")\n'
                        nk += 'read.getParam("ocioOutputSpaceIndex").setValue(1)\n'
                nk += 'read.getParam("firstFrame").setValue({})\n'.format(int(self.master_input.just_in))
                nk += 'read.getParam("lastFrame").setValue({})\n'.format(int(self.master_input.just_out))

                nk += 'write = app.createWriter("{}")\n'.format(mov_path)
                nk += 'write.connectInput(0,read)\n'
    #            if self.scan_colorspace == 'AlexaV3LogC':
    #                nk += 'write.getParam("ocioInputSpace").setValue("rec709")\n'
    #                nk += 'write.getParam("ocioOutputSpace").setValue("AlexaViewer")\n'
    #            else:
    #                nk += 'write.getParam("ocioInputSpace").setValue("color_picking")\n'
    #                nk += 'write.getParam("ocioOutputSpaceIndex").setValue(1)\n'
                if self.scan_colorspace == 'AlexaV3LogC':
                    nk += 'write.getParam("ocioInputSpace").setValue("linear")\n'
                    nk += 'write.getParam("ocioOutputSpace").setValue("rec709" )\n'
                elif self.scan_colorspace == 'Arri4.rec709':
                    nk += 'write.getParam("ocioInputSpace").setValue("Arri4.rec709")\n'
                    nk += 'write.getParam("ocioOutputSpace").setValue("Arri4Viewer")\n'  
                else:
                    nk += 'write.getParam("ocioInputSpace").setValue("color_picking")\n'
                    nk += 'write.getParam("ocioOutputSpaceIndex").setValue(1)\n'
                nk += 'write.getParam("frameRange").setValue(0)\n'
                
                nk += 'if sys.version_info.minor == 7 and sys.version_info.micro == 15:\n'
                nk += '\twrite.getParam("format").setValue(5)\n'
                nk += 'else:\n'
                nk += '\twrite.getParam("format").setValue(4)\n'
                codec_index = 0
                if self.setting.mov_codec == 'apch' or self.setting.mov_codec == 'ap4h':
                    codec_index = 1
                nk += 'write.getParam("codec").setValue({})\n'.format(codec_index)
                nk += 'write.getParam("fps").setValue({})\n'.format(self.master_input.framerate)
                nk += 'write.getParam("formatType").setValue(0)\n'
                nk += 'app.render(write,{0},{1})\n'.format(int(self.master_input.just_in), int(self.master_input.just_out))
    #            if self.scan_colorspace == 'AlexaV3LogC':
    #                nk += 'import shutil\n'
    #                nk += 'shutil.rmtree( "{}" )\n'.format( os.path.dirname( self.jpg4mov_output ) )
    #            nk += 'write.getOutputFormat().set(0,0,{0},{1})\n'.format(int(width), int(height))
                nk += 'exit()\n'

            else:
                nk = ''
                nk += 'import nuke\n'
                nk += 'read = nuke.nodes.Read( file="{}" )\n'.format(scan_path)
                nk += 'read["colorspace"].setValue("{}")\n'.format(self.scan_colorspace)
                nk += 'read["first"].setValue( {} )\n'.format(int(self.master_input.just_in))
                nk += 'read["last"].setValue( {} )\n'.format(int(self.master_input.just_out))
                if self.project['name'] in ['jung', 'marry', '4thlove', 'RND', 'asura', 'waiting']:
                    if self.master_input.ext == "mov":
                        nk += 'read["mov64_decode_video_levels"].setValue("Video Range")\n'
                    if self.setting.datatype == '10 bit' and self.master_input.ext == "mxf":
                        nk += 'read["dataRange"].setValue("Video Range")\n'
                tg = 'read'
                nk += 'output = "{}"\n'.format(mov_path)
                nk += 'write = nuke.nodes.Write(name="Write_mov", inputs = [%s],file=output )\n' % tg
                nk += 'write["file_type"].setValue( "mov" )\n'
                nk += 'write["create_directories"].setValue(True)\n'
                nk += 'write["mov64_codec"].setValue( "{}")\n'.format(self.setting.mov_codec)
                if self.setting.dnxhd_profile:
                    nk += 'write["mov64_dnxhd_codec_profile"].setValue( "{}")\n'.format(self.setting.dnxhd_profile )
                if self.setting.dnxhr_profile:
                    nk += 'write["mov64_dnxhr_codec_profile"].setValue( "{}")\n'.format(self.setting.dnxhr_profile )
                nk += 'write["colorspace"].setValue("{}")\n'.format(colorspace_set[self.scan_colorspace])
                nk += 'write["mov64_fps"].setValue({})\n'.format(self.master_input.framerate)
                nk += 'nuke.execute(write,{0},{1},1)\n'.format(int(self.master_input.just_in),
                                                            int(self.master_input.just_out))
                nk += 'exit()\n'
        else:
            nk = ''
            nk += 'import nuke\n'
            nk += 'read = nuke.nodes.Read( file="{}" )\n'.format(scan_path)
            nk += 'read["colorspace"].setValue("{}")\n'.format(self.scan_colorspace)
            nk += 'read["first"].setValue( {} )\n'.format(int(self.master_input.just_in))
            nk += 'read["last"].setValue( {} )\n'.format(int(self.master_input.just_out))
            if self.project['name'] in ['jung', 'marry', '4thlove', 'RND', 'asura', 'waiting']:
                if self.master_input.ext == "mov":
                    nk += 'read["mov64_decode_video_levels"].setValue("Video Range")\n'
                if self.setting.datatype == '10 bit' and self.master_input.ext == "mxf":
                    nk += 'read["dataRange"].setValue("Video Range")\n'
            tg = 'read'
            # nk += 'output = "{}"\n'.format(org_path)
            # nk += 'write = nuke.nodes.Write(name="Write_org", inputs = [%s],file=output )\n' % tg
            # nk += 'write["file_type"].setValue( "mov" )\n'
            # nk += 'write["create_directories"].setValue(True)\n'
            # nk += 'write["mov64_codec"].setValue( "{}")\n'.format(self.setting.mov_codec)
            # if self.setting.dnxhd_profile:
            #     nk += 'write["mov64_dnxhd_codec_profile"].setValue( "{}")\n'.format(self.setting.dnxhd_profile )
            # if self.setting.dnxhr_profile:
            #     nk += 'write["mov64_dnxhr_codec_profile"].setValue( "{}")\n'.format(self.setting.dnxhr_profile )
            # nk += 'write["colorspace"].setValue("{}")\n'.format(self.scan_colorspace)
            # nk += 'write["mov64_fps"].setValue({})\n'.format(self.master_input.framerate)
            # nk += 'nuke.execute(write,{0},{1},1)\n'.format(int(self.master_input.just_in),
            #                                                int(self.master_input.just_out))

            nk += 'output = "{}"\n'.format(mov_path)
            nk += 'write = nuke.nodes.Write(name="Write_mov", inputs = [%s],file=output )\n' % tg
            nk += 'write["file_type"].setValue( "mov" )\n'
            nk += 'write["create_directories"].setValue(True)\n'
            nk += 'write["mov64_codec"].setValue( "{}")\n'.format(self.setting.mov_codec)
            if self.setting.dnxhd_profile:
                nk += 'write["mov64_dnxhd_codec_profile"].setValue( "{}")\n'.format(self.setting.dnxhd_profile )
            if self.setting.dnxhr_profile:
                nk += 'write["mov64_dnxhr_codec_profile"].setValue( "{}")\n'.format(self.setting.dnxhr_profile )
            nk += 'write["colorspace"].setValue("{}")\n'.format(colorspace_set[self.scan_colorspace])
            nk += 'write["mov64_fps"].setValue({})\n'.format(self.master_input.framerate)
            nk += 'nuke.execute(write,{0},{1},1)\n'.format(int(self.master_input.just_in),
                                                           int(self.master_input.just_out))
            nk += 'exit()\n'

        if not os.path.exists(os.path.dirname(tmp_nuke_script_file)):
            cur_umask = os.umask(0)
            os.makedirs(os.path.dirname(tmp_nuke_script_file), 0o777)
            os.umask(cur_umask)

        with open(tmp_nuke_script_file, 'w') as f:
            f.write(nk)
        return tmp_nuke_script_file

    def add_mov_to_dpx_script(self, dpx_path, input_node, start_frame, end_frame):
        nk = ''
        nk += 'write = app.createWriter("{}")\n'.format(dpx_path)
        nk += 'write.connectInput(0,{})\n'.format(input_node)
        nk += 'write.getParam( "outputComponents" ).setValue( "RGB" )\n'
        nk += 'write.getParam("ocioInputSpace").setValue("color_picking")\n'
        nk += 'write.getParam("ocioOutputSpaceIndex").setValue(1)\n'
        nk += 'write.getParam("frameRange").setValue(0)\n'
        nk += 'write.getParam("bitDepth").setValue( "10i" )\n'
        nk += 'app.render(write,{0},{1})\n'.format(start_frame, end_frame)
        return nk

    def create_dpx_to_output_script(self, start_frame, end_frame, read_path, output_path, input_color, output_color,
                                    width, mov_path):
        nk = ''
        nk += 'import nuke\n'
        nk += 'nuke.knob("root.first_frame", "{}")\n'.format(start_frame)
        nk += 'nuke.knob("root.last_frame", "{}")\n'.format(end_frame)
        nk += 'read = nuke.nodes.Read(name="Read1", file="{}")\n'.format(read_path)
        nk += 'read["first"].setValue({})\n'.format(start_frame)
        nk += 'read["last"].setValue({})\n'.format(end_frame)
        nk += 'read["colorspace"].setValue("{}")\n'.format(input_color)
        tg = 'read'
        if self.seq_type != 'lib':
            nk += 'write = nuke.nodes.Write(name="Write1", inputs=[read], file="{}")\n'.format(output_path)
            nk += 'write["file_type"].setValue("jpeg")\n'
            nk += 'write["create_directories"].setValue(True)\n'
            nk += 'write["colorspace"].setValue("{}")\n'.format(output_color)
            nk += 'write["_jpeg_quality"].setValue(1.0)\n'
            nk += 'write["_jpeg_sub_sampling"].setValue("4:4:4")\n'
            nk += 'nuke.execute(write, {}, {}, 1)\n'.format(start_frame, end_frame)
        if int(width) > 2048:
            nk += 'reformat = nuke.nodes.Reformat(inputs=[%s],type=2,scale=.5)\n' % tg
            reformat = 'reformat'
        if self.project['name'] not in ['jung'] :
            nk += 'output = "{}"\n'.format(mov_path)
            if int(width) > 2048:
                nk += 'write   = nuke.nodes.Write(name="mov_write", inputs = [%s],file=output )\n' % reformat
            else:
                nk += 'write   = nuke.nodes.Write(name="mov_write", inputs = [%s],file=output )\n' % tg
            nk += 'write["file_type"].setValue( "mov" )\n'
            nk += 'write["create_directories"].setValue(True)\n'
            nk += 'write["mov64_codec"].setValue( "{}")\n'.format(self.setting.mov_codec)
            if self.setting.dnxhd_profile:
                nk += 'write["mov64_dnxhd_codec_profile"].setValue( "{}")\n'.format(self.setting.dnxhd_profile )
            if self.setting.dnxhr_profile:
                nk += 'write["mov64_dnxhr_codec_profile"].setValue( "{}")\n'.format(self.setting.dnxhr_profile )

            nk += 'write["colorspace"].setValue("{}")\n'.format(output_color)
            nk += 'write["mov64_fps"].setValue({})\n'.format(self.master_input.framerate)
            # nk += 'write["colorspace"].setValue( "Cineon" )\n'
            # nk += 'nuke.scriptSaveAs( "{}",overwrite=True )\n'.format( nuke_file )
            nk += 'nuke.execute(write,{},{},1)\n'.format(start_frame, end_frame)
        nk += 'exit()\n'
        return nk

    def create_nuke_script(self):
        if self._opt_non_retime == True and os.path.exists(self.plate_path):
            return None

        width, height = self.master_input.resolution.split("x")

        if self.master_input.retime_job:
            frame_count = sum([x['retime_duration'] for x in self.master_input.retime_info])
        else:
            frame_count = len(self.copy_file_list)
            if frame_count == 0:
                return None

        jpg_path = os.path.join(self.plate_jpg_path, self.plate_file_name + ".%04d.jpg")
        jpg_2k_path = os.path.join(self.plate_jpg_2k_path, self.plate_file_name + ".%04d.jpg")
        if self.seq_type != 'lib':
            tmp_nuke_script_file = os.path.join(self._app.sgtk.project_path, 'seq',
                                                self.seq_name,
                                                self.shot_name, "plate",
                                                self.plate_file_name + ".py")
            mov_path = os.path.join(self._app.sgtk.project_path, 'seq',
                                    self.seq_name,
                                    self.shot_name, "plate",
                                    self.plate_file_name + ".mov")
        else:
            tmp_nuke_script_file = os.path.join(self.clip_lib_seq_path, self.clip_lib_name + ".py")
            mov_path = '/' + os.path.join('stock', 'mov', self.clip_lib_name+'.mov')

        if self._opt_dpx == False:
            start_frame = int(self.master_input.just_in)
            end_frame = int(self.master_input.just_out)
            if self.seq_type != 'lib':
                start_frame = 1001
                end_frame = 1000 + int(frame_count)
                read_path = os.path.join(self.plate_path, self.plate_file_name + ".%04d." + self.file_ext)
            else:
                if not self.master_input.ext in ['mov',"mxf"]:
                    filename = '.'.join([self.master_input.scan_name[:-1], self.master_input.pad, self.master_input.ext])
                else:
                    filename = self.master_input.scan_name
                read_path = os.path.join(self.master_input.scan_path, filename)

            nk = ''
            nk += 'import nuke\n'
            nk += 'nuke.knob("root.first_frame", "{}" )\n'.format(start_frame)
            nk += 'nuke.knob("root.last_frame", "{}" )\n'.format(end_frame)
            # nk += 'nuke.knob("root.fps", "{}" )\n'.format( framerate )
            nk += 'read = nuke.nodes.Read( name="Read1",file="{}" )\n'.format(read_path)
            nk += 'read["first"].setValue( {} )\n'.format(start_frame)
            nk += 'read["last"].setValue( {} )\n'.format(end_frame)
            nk += 'read["colorspace"].setValue("{}")\n'.format(self.scan_colorspace)
            if self.file_ext in ["dpx"] and self.project['name'] == "sweethome":
                nk += 'read["colorspace"].setValue("{}")\n'.format(colorspace_set[self.scan_colorspace])
            elif self.project['name'] in ['jung', 'marry', '4thlove', 'RND', 'asura', 'waiting']:
                if self.setting.datatype == '10 bit':
                    if self.master_input.ext == "mov":
                        nk += 'read["mov64_decode_video_levels"].setValue("Video Range")\n'
                    elif self.master_input.ext == "mxf":
                        nk += 'read["dataRange"].setValue("Video Range")\n'
            tg = 'read'

            # gizmo = ''

            # if gizmo:
            #    nk += 'giz = nuke.createNode("stamp_wswg_wygbrowser.gizmo")\n'
            #    nk += 'giz.setInput( 0, read )\n'
            #    nk += "giz['project'].setValue( '{}' )\n".format( showname )
            #    tg = 'giz'
            # if os.path.exists(lut) :
            #    nk += 'vf = nuke.nodes.Vectorfield( inputs = [%s], '% tg
            #    nk += 'vfield_file = "{}",'.format( lut )
            #    nk += 'colorspaceIn="{}",'.format( cs_in )
            #    nk += 'colorspaceOut ="{}" )\n'.format( cs_out )
            #    tg = 'vf'
            if int(width) > 2048 and self._opt_clip == False:
                nk += 'reformat = reformat = nuke.nodes.Reformat(inputs=[%s],type=2,scale=.5)\n' % tg
                reformat = 'reformat'
                nk += 'output = "{}"\n'.format(jpg_2k_path)
                nk += 'write   = nuke.nodes.Write(name="ww_write_2k", inputs = [%s],file=output )\n' % reformat
                nk += 'write["file_type"].setValue( "jpeg" )\n'
                nk += 'write["create_directories"].setValue(True)\n'
                nk += 'write["colorspace"].setValue("{}")\n'.format(colorspace_set[self.scan_colorspace])
                nk += 'write["_jpeg_quality"].setValue( 1.0 )\n'
                nk += 'write["_jpeg_sub_sampling"].setValue( "4:4:4" )\n'
                nk += 'nuke.execute(write,{},{},1)\n'.format(start_frame, end_frame)

            if self.seq_type != 'lib':
                nk += 'output = "{}"\n'.format(jpg_path)
                nk += 'write   = nuke.nodes.Write(name="ww_write", inputs = [%s],file=output )\n' % tg
                nk += 'write["file_type"].setValue( "jpeg" )\n'
                nk += 'write["create_directories"].setValue(True)\n'
                nk += 'write["colorspace"].setValue("{}")\n'.format(colorspace_set[self.scan_colorspace])
                nk += 'write["_jpeg_quality"].setValue( 1.0 )\n'
                nk += 'write["_jpeg_sub_sampling"].setValue( "4:4:4" )\n'
                # nk += 'nuke.scriptSaveAs( "{}",overwrite=True )\n'.format( nuke_file )
                nk += 'nuke.execute(write,{},{},1)\n'.format(start_frame, end_frame)

            if int(width) > 2048:
                nk += 'reformat = reformat = nuke.nodes.Reformat(inputs=[%s],type=2,scale=.5)\n' % tg
                reformat = 'reformat'
            nk += 'output = "{}"\n'.format(mov_path)
            if int(width) > 2048:
                nk += 'write   = nuke.nodes.Write(name="mov_write", inputs = [%s],file=output )\n' % reformat
            else:
                nk += 'write   = nuke.nodes.Write(name="mov_write", inputs = [%s],file=output )\n' % tg
            nk += 'write["file_type"].setValue( "mov" )\n'
            nk += 'write["create_directories"].setValue(True)\n'
            nk += 'write["mov64_codec"].setValue( "{}")\n'.format(self.setting.mov_codec)
            if self.setting.dnxhd_profile:
                nk += 'write["mov64_dnxhd_codec_profile"].setValue( "{}")\n'.format(self.setting.dnxhd_profile )
            if self.setting.dnxhr_profile:
                nk += 'write["mov64_dnxhr_codec_profile"].setValue( "{}")\n'.format(self.setting.dnxhr_profile )
                
            nk += 'write["colorspace"].setValue("{}")\n'.format(colorspace_set[self.scan_colorspace])
            nk += 'write["mov64_fps"].setValue({})\n'.format(self.master_input.framerate)
            # nk += 'write["colorspace"].setValue( "Cineon" )\n'
            # nk += 'nuke.scriptSaveAs( "{}",overwrite=True )\n'.format( nuke_file )
            nk += 'nuke.execute(write,{},{},1)\n'.format(start_frame, end_frame)
            nk += 'exit()\n'

        ### 정년이[jung] 프로젝트에서는 natron을 사용하지 않기로 I/O팀과 결정
        ##  정년이[jung] 종료 이후에는 복구가능한 코드 
        # -> 프로젝트 종료 후에도 aces_config 사용하면 natron 대신 nuke 사용할 수도 있음
        elif self._opt_dpx == True and self.project['name'] in ['jung', 'RND', 'marry', '4thlove', 'asura', 'waiting']:
            img_nk = ''
            self.use_natron = False

            start_frame = int(self.master_input.just_in)
            end_frame = int(self.master_input.just_out)

            color = self.scan_colorspace

            mov_path = os.path.join(self._app.sgtk.project_path, 'seq',
                                    self.seq_name,
                                    self.shot_name, "plate",
                                    self.plate_file_name + ".mov")
            print('-'*50)
            print(mov_path)
            print('-'*50)
            read_path = os.path.join( self.master_input.scan_path, self.master_input.scan_name )
            dpx_path = os.path.join(self.plate_path, self.plate_file_name + ".%04d.dpx")
            self.tmp_dpx_to_jpg_file = os.path.join(self._app.sgtk.project_path, 'seq',
                                                   self.seq_name,
                                                   self.shot_name, "plate",
                                                   self.plate_file_name + "_jpg.py")
            self.use_natron = False
            nk = ''
            nk += 'import os\n'
            nk += 'import nuke\n'
            nk += 'nuke.knob("root.first_frame", "{}")\n'.format(start_frame)
            nk += 'nuke.knob("root.last_frame", "{}")\n'.format(end_frame)
            # nk += 'read = nuke.nodes.Read(file = "{}")\n'.format(read_path)
            nk += 'read = nuke.nodes.Read(name="Read1", file="{}")\n'.format(read_path)
            if not self.scan_colorspace.find( "Arri" ) == -1:
                nk += 'read["colorspace"].setValue("{}")\n'.format( "rec709" )
            else:
                nk += 'read["colorspace"].setValue("{}")\n'.format(self.scan_colorspace)
            # nk += 'read["colorspace"].setValue("{}")\n'.format( "rec709" )
            nk += 'read["first"].setValue({})\n'.format(start_frame)
            nk += 'read["last"].setValue({})\n'.format(end_frame)
            if self.project['name'] in ['jung', 'marry', '4thlove', 'RND', 'asura', 'waiting']:
                if self.master_input.ext == "mov":
                    nk += 'read["mov64_decode_video_levels"].setValue("Video Range")\n'
                if self.setting.datatype == '10 bit' and self.master_input.ext == "mxf":
                    nk += 'read["dataRange"].setValue("Video Range")\n'
            tg = 'read'
            nk += 'output = "{}"\n'.format(dpx_path)
            nk += 'write  = nuke.nodes.Write(name="ww_write", inputs = [read], file=output )\n'
            # nk += 'write["file_type"].setValue( "dpx" )\n'
            nk += 'write["file_type"].setValue( "{}" )\n'.format(self.setting.file_type)
            # nk += 'write["datatype"].setValue( "12 bit" )\n'
            nk += 'write["datatype"].setValue( "{}" )\n'.format(self.setting.datatype)
            nk += 'write["create_directories"].setValue(True)\n'
            
            if not self.scan_colorspace.find( "Arri" ) == -1:
                nk += 'write["colorspace"].setValue("{}")\n'.format( "rec709" )
            else:
                # nk += 'write["colorspace"].setValue("{}")\n'.format(colorspace_set[self.scan_colorspace])
                nk += 'write["colorspace"].setValue("{}")\n'.format(self.scan_colorspace)
            nk += 'nuke.execute(write, {}, {}, 1)\n'.format(start_frame, end_frame)
            
            img_nk += self.create_dpx_to_output_script(start_frame, end_frame, dpx_path, jpg_path, color,
                                                       colorspace_set[color], width, mov_path)
            
            if not os.path.exists(os.path.dirname(self.tmp_dpx_to_jpg_file)):
                cur_umask = os.umask(0)
                os.makedirs(os.path.dirname(self.tmp_dpx_to_jpg_file), 0o777)
                os.umask(cur_umask)

            with open(self.tmp_dpx_to_jpg_file, 'w') as f:
                f.write(img_nk)
            color_config = 'alexa_config'
            if not self.scan_colorspace.find("ACES") == -1:
                color_config = 'ocio_config'
            if not self.scan_colorspace.find("Alexa") == -1:
                color_config = 'alexa_config'
            if not self.scan_colorspace.find("legacy") == -1:
                color_config = 'legacy_config'
            if not self.scan_colorspace.find("Sony") == -1:
                color_config = 'sony_config'
            if not self.scan_colorspace.find( "Arri" ) == -1:
                color_config = 'aces_config'
            if not self.scan_colorspace.find( "Output" ) == -1:
                color_config = 'ocio_config'

            if self.project['name'] in ['jung']:
                nuke_ver = 'nuke-13'
            else:
                nuke_ver = 'nuke-12.2.2'
            nk += 'os.system("rez-env {} {} -- nuke -ix {}")\n'.format(nuke_ver, color_config, self.tmp_dpx_to_jpg_file)

            nk += 'dpx_output_dir = os.path.dirname("{}")\n'.format(dpx_path)
            nk += 'dpx_output_list = sorted(os.listdir(dpx_output_dir))\n'
            nk += 'jpg_output_dir = os.path.dirname("{}")\n'.format(jpg_path)
            nk += 'jpg_output_list = sorted(os.listdir(jpg_output_dir))\n'
            nk += 'cnt1 = cnt2 = 1001\n'
            if len(str(int(self.master_input.just_out))) != len(str(int(self.master_input.just_in))) or len(str(int(self.master_input.duration))) >= 4:
                nk += 'import shutil\n'
                nk += 'dpx_temp_dir = os.path.dirname(dpx_output_dir)+"/"+"{}_dpx_temp"\n'.format(self.plate_file_name)
                nk += 'if not os.path.exists(dpx_temp_dir):\n'
                nk += '    os.makedirs(dpx_temp_dir)\n'
                nk += 'temp_dpxname_list = []\n'
                nk += 'for target in dpx_output_list:\n'
                nk += '    if ".py" not in target: \n'
                nk += '        name = target.split(".")\n'
                nk += '        if len(name[1]) != {}:\n'.format(len(str(int(self.master_input.just_out))))
                nk += '            res = name[0] + "." + name[1].zfill({}) + "." + name[2]\n'.format(len(str(int(self.master_input.just_out))))
                nk += '            os.rename(dpx_output_dir+"/"+target, dpx_output_dir+"/"+res)\n'
                nk += '            temp_dpxname_list.append(res)\n'
                nk += '        else:\n'
                nk += '            temp_dpxname_list.append(target)\n'
                nk += 'temp_dpxname_list = sorted(temp_dpxname_list)\n'
                nk += 'for i in temp_dpxname_list:\n'
                nk += '    name = i.split(".")\n'
                if len(str(int(self.master_input.just_out))) > len(str(int(self.master_input.duration))):
                    nk += '    cleanup_dpxname = name[0] + "." + str(cnt1) + "." + name[2]\n'
                    nk += '    cnt1 += 1\n'
                else:
                    nk += '    cleanup_dpxname = name[0] + "." + str(int(name[1])+cnt1-1) + "." + name[2]\n'
                nk += '    shutil.move(dpx_output_dir+"/"+i, dpx_temp_dir+"/"+cleanup_dpxname)\n'
                nk += 'if not len(os.listdir(dpx_output_dir)):\n'
                nk += '    os.rmdir(dpx_output_dir)\n'
                nk += 'os.rename(dpx_temp_dir, dpx_output_dir)\n'
                nk += 'jpg_temp_dir = os.path.dirname(jpg_output_dir)+"/"+"{}_jpg_temp"\n'.format(self.plate_file_name)
                nk += 'if not os.path.exists(jpg_temp_dir):\n'
                nk += '    os.makedirs(jpg_temp_dir)\n'
                nk += 'temp_jpgname_list = []\n'
                nk += 'for target in jpg_output_list:\n'
                nk += '        name = target.split(".")\n'
                nk += '        if len(name[1]) != {}:\n'.format(len(str(int(self.master_input.just_out))))
                nk += '            res = name[0] + "." + name[1].zfill({}) + "." + name[2]\n'.format(len(str(int(self.master_input.just_out))))
                nk += '            os.rename(jpg_output_dir+"/"+target, jpg_output_dir+"/"+res)\n'
                nk += '            temp_jpgname_list.append(res)\n'
                nk += '        else:\n'
                nk += '            temp_jpgname_list.append(target)\n'
                nk += 'temp_jpgname_list = sorted(temp_jpgname_list)\n'
                nk += 'for i in temp_jpgname_list:\n'
                nk += '    name = i.split(".")\n'
                if len(str(int(self.master_input.just_out))) > len(str(int(self.master_input.duration))):
                    nk += '    cleanup_jpgname = name[0] + "." + str(cnt2) + "." + name[2]\n'
                    nk += '    cnt2 += 1\n'
                else:
                    nk += '    cleanup_jpgname = name[0] + "." + str(int(name[1])+cnt2-1) + "." + name[2]\n'
                nk += '    shutil.move(jpg_output_dir+"/"+i, jpg_temp_dir+"/"+cleanup_jpgname)\n'
                nk += 'if not len(os.listdir(jpg_output_dir)):\n'
                nk += '    os.rmdir(jpg_output_dir)\n'
                nk += 'os.rename(jpg_temp_dir, jpg_output_dir)\n'
            elif start_frame != 1:
                nk += 'temp_dpxname_list = []\n'
                nk += 'for target in dpx_output_list:\n'
                nk += '    if ".py" not in target: \n'
                nk += '        dpx_temp_file = dpx_output_dir+"/{}.%d.dpx"%cnt1 + ".temp"\n'.format(self.plate_file_name)
                nk += '        os.rename(dpx_output_dir+"/"+target, dpx_temp_file)\n'
                nk += '        temp_dpxname_list.append(dpx_temp_file)\n'
                nk += '        cnt1 += 1\n'
                nk += 'for temp_dpxname in temp_dpxname_list:\n'
                nk += '    final_name = temp_dpxname.replace(".temp","")\n'
                nk += '    os.rename(temp_dpxname, final_name)\n'
                nk += 'temp_jpgname_list = []\n'
                nk += 'for target in jpg_output_list:\n'
                nk += '    jpg_temp_file = jpg_output_dir+"/{}.%d.jpg"%cnt2 + ".temp"\n'.format(self.plate_file_name)
                nk += '    os.rename(jpg_output_dir+"/"+target, jpg_temp_file)\n'
                nk += '    temp_jpgname_list.append(jpg_temp_file)\n'
                nk += '    cnt2 += 1\n'
                nk += 'for temp_jpgname in temp_jpgname_list:\n'
                nk += '    final_name = temp_jpgname.replace(".temp", "")\n'
                nk += '    os.rename(temp_jpgname, final_name)\n'
            else:
                nk += 'for target in dpx_output_list:\n'
                nk += '    if ".py" not in target: \n'
                nk += '        os.rename(dpx_output_dir+"/"+target, dpx_output_dir+"/{}.%d.dpx"%cnt1)\n'.format(self.plate_file_name)
                nk += '        cnt1 += 1\n'
                nk += 'for target in jpg_output_list:\n'
                nk += '    os.rename(jpg_output_dir+"/"+target, jpg_output_dir+"/{}.%d.jpg"%cnt2)\n'.format(self.plate_file_name)
                nk += '    cnt2 += 1\n'           


            nk += 'exit()\n'

        else: # self._opt_dpx == True 인 경우
            start_frame = int(self.master_input.just_in)
            end_frame = int(self.master_input.just_out)
            if self.seq_type != 'lib':
                self.tmp_dpx_to_jpg_file = os.path.join(self._app.sgtk.project_path, 'seq',
                                                   self.seq_name,
                                                   self.shot_name, "plate",
                                                   self.plate_file_name + "_jpg.py")
                # start_frame = 1
                # end_frame = int(self.master_input.just_out) - int(self.master_input.just_in) + 1
                dpx_path = os.path.join(self.plate_path, self.plate_file_name + ".%04d.dpx")
                read_path = os.path.join(self.master_input.scan_path,self.master_input.scan_name)
            else:
                self.tmp_dpx_to_jpg_file = os.path.join(self.clip_lib_seq_path, self.clip_lib_name + '_jpg.py')
                pad = len(str(end_frame))
                clip_name = '.'.join([self.clip_lib_name, "%04d", "dpx"])
                dpx_path = os.path.join(self.clip_lib_seq_path, clip_name)
                read_path = os.path.join(self.master_input.scan_path, self.master_input.scan_name)

            self.use_natron = True
            img_nk = ''
            nk = ''
            nk += 'import os\n'
            nk += 'from NatronEngine import *\n'
            nk += 'read = app.createReader("{}")\n'.format(read_path)
            nk += 'read.getParam("firstFrame").setValue({})\n'.format(start_frame)
            nk += 'read.getParam("lastFrame").setValue({})\n'.format(end_frame)
            nk += 'read.getParam("ocioInputSpace").setValue("color_picking")\n'
            nk += 'read.getParam("ocioOutputSpaceIndex").setValue(1)\n'
            tg = 'read'
            color = self.scan_colorspace

            # if int(width) > 2048:
            #     nk += 'reformat = app.createNode("net.sf.openfx.Reformat")\n'
            #     nk += 'reformat.connectInput(0, read)\n'
            #     nk += 'reformat.getParam("reformatType").setValue(2)\n'
            #     nk += 'reformat.getParam("reformatScale").setValue(.5)\n'
            #     tg = 'reformat'
            #     nk += self.add_mov_to_dpx_script(dpx_path, tg, start_frame, end_frame)
            #     img_nk += self.create_dpx_to_output_script(start_frame, end_frame, dpx_path, jpg_2k_path, color,
            #                                                colorspace_set[color], width, mov_path)
            img_nk += self.create_dpx_to_output_script(start_frame, end_frame, dpx_path, jpg_path, color,
                                                       colorspace_set[color], width, mov_path)
            nk += self.add_mov_to_dpx_script(dpx_path, tg, start_frame, end_frame)

            color_config = 'alexa_config'
            if not self.scan_colorspace.find("ACES") == -1:
                color_config = 'ocio_config'
            if not self.scan_colorspace.find("Alexa") == -1:
                color_config = 'alexa_config'
            if not self.scan_colorspace.find("legacy") == -1:
                color_config = 'legacy_config'
            if not self.scan_colorspace.find("Sony") == -1:
                color_config = 'sony_config'
            if not self.scan_colorspace.find("Arri") == -1:
                color_config = 'alexa4_config'
            if not self.scan_colorspace.find( 'Output' ) == -1:
                color_config = 'ocio_config'

            nk += 'os.system("rez-env nuke-12.2.2 {} -- nuke -ix {}")\n'.format(color_config, self.tmp_dpx_to_jpg_file)
            # if int(width) > 2048:
            #     nk += 'jpg_2k_dir = os.path.dirname("{}")\n'.format(jpg_2k_path)
            #     nk += 'jpg_2k_list = sorted(os.listdir(jpg_2k_dir))\n'
            #     nk += 'cnt = 1001\n'
            #     nk += 'for target in jpg_2k_list: \n'
            #     nk += '    os.rename(jpg_2k_dir+"/"+target, jpg_2k_dir+"/{}.%d.jpg"%cnt)\n'.format(self.plate_file_name)
            #     nk += '    cnt += 1\n'
            #     jpg_path = jpg_2k_path
            nk += 'dpx_output_dir = os.path.dirname("{}")\n'.format(dpx_path)
            nk += 'dpx_output_list = sorted(os.listdir(dpx_output_dir))\n'
            if self.seq_type != 'lib':
                nk += 'jpg_output_dir = os.path.dirname("{}")\n'.format(jpg_path)
                nk += 'jpg_output_list = sorted(os.listdir(jpg_output_dir))\n'
            if len(str(end_frame)) > 4:
                nk += 'dpx_tmp_list, jpg_tmp_list = [], []\n'
                nk += 'for target in dpx_output_list:\n'
                nk += '    name = target.split(".")\n'
                nk += '    if len(name[1]) != {}:\n'.format(len(str(end_frame)))
                nk += '        res = name[0] + "." + name[1].zfill({}) + "." + name[2]\n'.format(len(str(end_frame)))
                nk += '        os.rename(dpx_output_dir+"/"+target, dpx_output_dir+"/"+res)\n'
                nk += '        dpx_tmp_list.append(res)\n'
                nk += '    else:\n'
                nk += '        dpx_tmp_list.append(target)\n'
                if self.seq_type != 'lib':
                    nk += 'for target in jpg_output_list:\n'
                    nk += '    name = target.split(".")\n'
                    nk += '    if len(name[1]) != {}:\n'.format(len(str(end_frame)))
                    nk += '        res = name[0] + "." + name[1].zfill({}) + "." + name[2]\n'.format(len(str(end_frame)))
                    nk += '        os.rename(jpg_output_dir+"/"+target, jpg_output_dir+"/"+res)\n'
                    nk += '        jpg_tmp_list.append(res)\n'
                    nk += '    else:\n'
                    nk += '        jpg_tmp_list.append(target)\n'
                    nk += 'dpx_output_list = sorted(dpx_tmp_list)\n'
                    nk += 'jpg_output_list = sorted(jpg_tmp_list)\n'
            nk += 'cnt1 = cnt2 = 1001\n'
            nk += 'for target in dpx_output_list:\n'
            nk += '    if ".py" not in target: \n'
            nk += '        os.rename(dpx_output_dir+"/"+target, dpx_output_dir+"/{}.%d.org.dpx"%cnt1)\n'.format(self.plate_file_name)
            nk += '        cnt1 += 1\n'
            if self.seq_type != 'lib':
                nk += 'for target in jpg_output_list:\n'
                nk += '    os.rename(jpg_output_dir+"/"+target, jpg_output_dir+"/{}.%d.org.jpg"%cnt2)\n'.format(self.plate_file_name)
                nk += '    cnt2 += 1\n'
            nk += 'cnt1 = cnt2 = 1001\n'
            nk += 'dpx_output_list = sorted(os.listdir(dpx_output_dir))\n'
            if self.seq_type != 'lib':
                nk += 'jpg_output_list = sorted(os.listdir(jpg_output_dir))\n'
            nk += 'for target in dpx_output_list:\n'
            nk += '    if ".py" not in target: \n'
            nk += '        os.rename(dpx_output_dir+"/"+target, dpx_output_dir+"/{}.%d.dpx"%cnt1)\n'.format(self.plate_file_name)
            nk += '        cnt1 += 1\n'
            if self.seq_type != 'lib':
                nk += 'for target in jpg_output_list:\n'
                nk += '    os.rename(jpg_output_dir+"/"+target, jpg_output_dir+"/{}.%d.jpg"%cnt2)\n'.format(self.plate_file_name)
                nk += '    cnt2 += 1\n'
            nk += 'exit()\n'

            if not os.path.exists(os.path.dirname(self.tmp_dpx_to_jpg_file)):
                cur_umask = os.umask(0)
                os.makedirs(os.path.dirname(self.tmp_dpx_to_jpg_file), 0o777)
                os.umask(cur_umask)

            with open(self.tmp_dpx_to_jpg_file, 'w') as f:
                f.write(img_nk)

            print('self.tmp_dpx_to_jpg_file')

        if not os.path.exists(os.path.dirname(tmp_nuke_script_file)):
            cur_umask = os.umask(0)
            os.makedirs(os.path.dirname(tmp_nuke_script_file), 0o777)
            os.umask(cur_umask)

        with open(tmp_nuke_script_file, 'w') as f:
            f.write(nk)

        print( tmp_nuke_script_file )
        return tmp_nuke_script_file

    def create_sg_script(self, switch=False):
        if self._opt_non_retime == True and switch == False and os.path.exists(self.plate_path):
            return None
        if self.seq_type != 'lib':
            tmp_sg_script_file = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name, self.shot_name, "plate",
                                              self.plate_file_name + "_sg.py")
        else:
            tmp_sg_script_file = os.path.join(self.clip_lib_seq_path, self.clip_lib_name + "_sg.py")
        if switch == True and self._opt_non_retime == True:
            tmp_sg_script_file = os.path.dirname(tmp_sg_script_file) + '/' + self.plate_file_name+'_sg_nonretime.py'

        if self.seq_type != 'lib':
            mov_path01 = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name, self.shot_name, "plate",
                                      self.plate_file_name + ".mov")
            mp4_path01 = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name, self.shot_name, "plate",
                                      self.plate_file_name + ".mp4")
            jpg_path = os.path.join(self.montage_jpg_path, self.plate_file_name + ".0001.jpg")
            webm_path = self.webm_path
            montage_path = self.montage_path
        else:
            mov_path01 = '/' + os.path.join('stock', 'mov', self.clip_lib_name+".mov")
            #mp4_path01 = '/' + os.path.join('stock', 'mp4', self.clip_lib_name+".mp4")
            jpg_path = '/' + os.path.join('stock', 'thumb', 'montage', self.clip_lib_name,
                                          self.clip_lib_name+".0001.jpg")
            webm_path = '/' + os.path.join('stock', 'mov', self.clip_lib_name + ".webm")
            montage_path = '/' + os.path.join('stock', 'mov', self.clip_lib_name + "stream.jpeg")

        version = self.version
        if self._opt_non_retime == True:
            version += 1
            mov_path02 = mov_path01.replace('v%03d'%self.version, 'v%03d'%version)
            mp4_path02 = mp4_path01.replace('v%03d'%self.version, 'v%03d'%version)
            webm_path02 = self.webm_path.replace('v%03d'%self.version, 'v%03d'%version)
            jpg_path02 = jpg_path.replace('v%03d'%self.version, 'v%03d'%version)
            montage_path02 = self.montage_path.replace('v%03d'%self.version, 'v%03d'%(self.version+1))
        # ** real plate duration
        #update_desc = {'sg_just_cut': len(self.copy_file_list)}

        plate_path = os.path.join(self.plate_path, self.plate_file_name+'.1001.'+self.master_input.ext)

        if self.seq_type != 'lib':
            version_ent = self.version_ent
        else:
            version_ent = self._proj_ver_ent
            clip_version_ent = self._clip_ver_ent

        nk = ''
        nk += 'import shotgun_api3\n'
        nk += 'import time\n'
        nk += 'WW_SG_HOST = "https://west.shotgunstudio.com"\n'
        nk += 'script_name = "westworld_util"\n'
        nk += 'script_key = "yctqnqdjd0bttz)ornewKuitt"\n'
        nk += 'sg = shotgun_api3.Shotgun(WW_SG_HOST,script_name = script_name,api_key=script_key)\n'
        # nk += 'sg.upload( "Version", %s, "%s", "sg_uploaded_movie" )\n'%(self.version_ent['id'],mov_path)
        if switch == False:
            if self._opt_clip == False:
                nk += 'sg.upload_thumbnail( "PublishedFile", %s, "%s")\n' % (self.published_ent['id'], jpg_path)
                nk += 'sg.upload_thumbnail( "Version", %s, "%s")\n' % (version_ent['id'], jpg_path)
                nk += 'sg.upload_filmstrip_thumbnail( "Version", %s, "%s")\n' % (version_ent['id'], montage_path)
                # ** command for real plate duration
                #nk += 'sg.update( "Shot", {}, {})\n'.format(self.shot_ent['id'], update_desc)
                if self.seq_type != 'lib':
                    nk += 'sg.upload( "Version", %s, "%s", "sg_uploaded_movie_mp4" )\n' % (version_ent['id'], mp4_path01)
                nk += 'sg.upload( "Version", %s, "%s", "sg_uploaded_movie_webm" )\n' % (version_ent['id'], webm_path)
            if self.seq_type == 'lib' or self._opt_clip == True:
                nk += 'sg.upload_thumbnail( "Version", %s, "%s")\n' % (clip_version_ent['id'], jpg_path)
                nk += 'sg.upload_filmstrip_thumbnail( "Version", %s, "%s")\n' % (clip_version_ent['id'], montage_path)
                #nk += 'sg.upload( "Version", %s, "%s", "sg_uploaded_movie_mp4" )\n' % (clip_version_ent['id'], mp4_path01)
                nk += 'sg.upload( "Version", %s, "%s", "sg_uploaded_movie_webm" )\n' % (clip_version_ent['id'], webm_path)
        else:
            if hasattr(self, 'published_tmp_ent') is False or hasattr(self, 'version_tmp_ent') is False:
                print( "#### debug start ####" )
            else:
                nk += 'sg.upload_thumbnail( "PublishedFile", %s, "%s")\n' % (self.published_tmp_ent['id'], jpg_path02)
                nk += 'sg.upload_thumbnail( "Version", %s, "%s")\n' % (self.version_tmp_ent['id'], jpg_path02)
                nk += 'sg.upload_filmstrip_thumbnail( "Version", %s, "%s")\n' % (self.version_tmp_ent['id'], montage_path02)
                nk += 'sg.upload( "Version", %s, "%s", "sg_uploaded_movie_mp4" )\n' % (self.version_tmp_ent['id'], mp4_path02)
                nk += 'sg.upload( "Version", %s, "%s", "sg_uploaded_movie_webm" )\n' % (self.version_tmp_ent['id'], webm_path02)
        # nk += 'time.sleep(20)\n'

        if not os.path.exists(os.path.dirname(tmp_sg_script_file)):
            cur_umask = os.umask(0)
            os.makedirs(os.path.dirname(tmp_sg_script_file), 0o777)
            os.umask(cur_umask)

        print( "#### succeeded sg file save ####" )
        with open(tmp_sg_script_file, 'w') as f:
            f.write(nk)
        print( tmp_sg_script_file )
        return tmp_sg_script_file

    @property
    def clip_project(self):
        filters = [['name', 'is', '_ClibLibrary']]
        project = self._sg.find_one('Project', filters)
        return project

    def _get_clip_lib_name(self):
        # if self._opt_clip == False:
        #     project_info = self._sg.find_one('Project', [['id', 'is', self.project['id']]], ['name'])
        #     clip_name = "clip_" + project_info['name'] + "_" + self.scan_colorspace + "_" + self.shot_name
        # else:
        #     clip_name = "clip_ClibLibrary_" + self.shot_name
        now_time = datetime.datetime.now()
        clip_name = "src"+now_time.strftime("%Y%m%d%H%M%S")
        return clip_name

    @property
    def clip_lib_seq_path(self):
        seq_path = '/' + os.path.join('stock', 'src', self.clip_lib_name)
        return seq_path

    @property
    def plate_file_name(self):
        temp = self.shot_name + "_" + self.seq_type + "_v%03d" % self.version
        return temp

    @property
    def webm_path(self):
        temp = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name, self.shot_name, "plate",
                            self.plate_file_name + ".webm")
        return temp

    @property
    def montage_path(self):
        temp = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name, self.shot_name, "plate",
                            self.plate_file_name + "stream.jpeg")
        return temp

    @property
    def copy_file_list(self):

        file_list = []

        scan_path = self.master_input.scan_path
        start_index = self.master_input.just_in
        end_index = self.master_input.just_out
        pad = self.master_input.pad
        # file_name  = self.master_input.scan_name
        file_ext = self.master_input.ext
        sequence = pyseq.get_sequences(scan_path)
        if sequence != []:
            if sequence[0].length() == 1:
                file_list.append(sequence[0].head())
                return file_list
            file_format = sequence[0].format("%h%p%t")

            for i in range(int(start_index), int(end_index) + 1):
                copy_file = file_format % i
                file_list.append(copy_file)
        else:
            print( "**  Here are Not Any Sequence! Check Your Sequence!  **" )

        return file_list

    def _get_model_data(self, colname):

        col = MODEL_KEYS[colname]

        index = self.model.createIndex(self.row, col)
        return self.model.data(index, QtCore.Qt.DisplayRole)

    def _get_version(self):
        key = [
            ['project', 'is', self.project],
            ['entity', 'is', self.shot_ent],
            ["published_file_type", "is", self.published_file_type],
            ['name', 'is', self.version_file_name]
        ]
        published_ents = self._sg.find("PublishedFile", key, ['version_number'])
        print( published_ents )
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
            key = [['code', 'is', 'Plate']]
            return self._sg.find_one("PublishedFileType", key, ['id'])
        elif self.seq_type == "ref":
            key = [['code', 'is', 'Reference']]
            return self._sg.find_one("PublishedFileType", key, ['id'])
        else:
            key = [['code', 'is', 'Source']]
            return self._sg.find_one("PublishedFileType", key, ['id'])

    @property
    def plate_path(self):
        temp = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name,
                            self.shot_name, "plate", self.seq_type, "v%03d" % self.version)
        return temp

    @property
    def tmp_path(self):

        temp = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name,
                            self.shot_name, "plate", "tmp", "v%03d" % self.version)
        return temp

    @property
    def plate_jpg_path(self):
        temp = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name,
                                self.shot_name, "plate", self.seq_type, "v%03d_jpg" % self.version)
        return temp

    @property
    def montage_jpg_path(self):

        temp = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name,
                            self.shot_name, "plate", "montage", "%s_v%03d_jpg" % (self.seq_type, self.version))
        return temp

    @property
    def plate_jpg_2k_path(self):

        temp = os.path.join(self._app.sgtk.project_path, 'seq', self.seq_name,
                            self.shot_name, "plate", self.seq_type, "v%03d_jpg_2k" % self.version)
        return temp

    @property
    def version_file_name(self):
        temp = self.shot_name + "_" + self.seq_type
        return temp

    def _check_version(self):
        key = [
            ['project', 'is', self.project],
            ['entity', 'is', self.shot_ent],
            ["published_file_type", "is", self.published_file_type],
            ['name', 'is', self.version_file_name],
            ['version_number', 'is', int(self.version)]
        ]
        published_ents = self._sg.find("PublishedFile", key, ['version_number'])
        if published_ents:
            return True
        else:
            return False

    def create_thumbnail(self):
        pass

    def publish_to_shotgun(self):
        if self._opt_clip == True:
            return None

        file_ext = self.master_input.ext

        data_fields = [self.version, self.published_file_type, self.version_file_name, self.seq_type, None]

        self.published_ent, ent_type = self._sg_cmd.publish_to_shotgun(data_fields)

        desc = {
                "version": self.version_ent,
                "sg_colorspace": self.scan_colorspace
               }

        if self.published_ent and ent_type == 'OLD' and self._opt_dpx == False:
            self._sg.update("PublishedFile", self.published_ent['id'], desc)
            return None

        published_file = os.path.join(self.plate_path, self.plate_file_name + ".%04d." + file_ext)
        if self.seq_type == 'lib':
            published_file = os.path.join(self.clip_lib_seq_path, self.clip_lib_name + ".%04d." + file_ext)
        if self.master_input.ext in ["mov","mxf"]:
            if self._opt_dpx == False:
                published_file = os.path.join(self._app.sgtk.project_path, 'seq',
                                              self.seq_name,
                                              self.shot_name, "plate",
                                              self.plate_file_name + "_orignal.mov")
            else:
                published_file = os.path.join(self.plate_path, self.plate_file_name + ".%04d.dpx")
            if self.seq_type == 'lib':
                published_file = '/' + os.path.join('stock', 'mov', self.clip_lib_name + ".mov")

        data_fields[4] = published_file
        self.published_ent, ent_type = self._sg_cmd.publish_to_shotgun(data_fields)

        if ent_type == 'NEW':
            self._sg.update("PublishedFile", self.published_ent['id'], desc)

