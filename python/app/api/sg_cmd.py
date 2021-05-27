# :coding: utf-8

import os
import sgtk


class ShotgunCommands(object):
    def __init__(self, app, sg, project, clip_project, user, context):
        self._app = app
        self._sg = sg
        self._project = project
        self._clip_project = clip_project
        self._user = user
        self._context = context
        self._clip_tag = []

    def create_seq(self, seq_name):
        project = self._project
        if seq_name == 'clip':
            project = self._clip_project

        key = [
               ['project', 'is', project],
               ['code', 'is', seq_name]
              ]

        seq_ent = self._sg.find_one('Sequence', key)
        if seq_ent:
            self.seq_ent = seq_ent
            return self.seq_ent
        desc = {
                'project': project,
                'code': seq_name
               }
        self.seq_ent = self._sg.create("Sequence", desc)
        return self.seq_ent

    def get_tags(self, tag_name):
        for tag in tag_name:
            filters = [['name', 'is', tag]]
            fields = ['type', 'id', 'name']
            tag_info = self._sg.find_one('Tag', filters, fields)
            if not tag_info:
                tag_dict = {'name': tag}
                self._sg.create('Tag', tag_dict)

            self._clip_tag.append(tag_info)
        return self._clip_tag

    def create_shot(self, shot_name):
        print "create Shot"
        project = self._project
        if self._project['name'] in shot_name:
            project = self._clip_project

        key = [
               ['project', 'is', project],
               ['sg_sequence', 'is', self.seq_ent],
               ['code', 'is', shot_name]
              ]

        shot_ent = self._sg.find_one('Shot', key)
        if self._project['name'] in shot_name:
            fields = ['code', 'tags']
            shot_ent = self._sg.find_one('Shot', key, fields)

        if shot_ent:
            self.shot_ent = shot_ent
            return self.shot_ent

        desc = {
                'project': project,
                'sg_sequence': self.seq_ent,
                'code': shot_name
               }
        if self._project['name'] in shot_name:
            desc['tags'] = self._clip_tag
        self.shot_ent = self._sg.create("Shot", desc)
        return self.shot_ent

    def publish_temp_jpg(self, data_fields):
        plate_path = data_fields[0]
        plate_file_name = data_fields[1]
        version = data_fields[2]
        file_type = data_fields[3]

        context = sgtk.Context(self._app.tank, project=self._project,
                               entity=self.shot_ent,
                               step=None,
                               task=None,
                               user=self._user)

        temp_jpg_dir = plate_path.split('/')[:-1]
        temp_jpg_path = os.path.join('/'.join(temp_jpg_dir), "v%03d_jpg" % (version + 1))
        file_name = plate_file_name.replace('v%03d' % version, 'v%03d' % (version + 1))
        published_file = os.path.join(temp_jpg_path, file_name + ".%04d.jpg")
        published_name = os.path.basename(published_file)

        key = [
               ['project', 'is', self._project],
               ['entity', 'is', self.shot_ent],
               ["published_file_type", "is", file_type],
               ['name', 'is', published_name],
               ['version_number', 'is', int(version)]
              ]
        self.published_tmp_ent = self._sg.find_one("PublishedFile", key, ['version_number'])

        if self.published_tmp_ent:
            return (self.published_tmp_ent, 'OLD')

        publish_data = {
                        "tk": self._app.tank,
                        "context": context,
                        "path": published_file,
                        "name": published_name,
                        "created_by": self._user,
                        "version_number": version,
                        # "thumbnail_path": item.get_thumbnail_as_path(),
                        "published_file_type": 'Plate',
                        # "dependency_paths": publish_dependencies
                        }

        self.published_tmp_ent = sgtk.util.register_publish(**publish_data)
        return (self.published_tmp_ent, 'NEW')

    def publish_to_shotgun(self, data_fields):
        version = data_fields[0]
        published_file_type = data_fields[1]
        version_file_name = data_fields[2]
        seq_type = data_fields[3]
        published_file = data_fields[4]

        context = sgtk.Context(self._app.tank, project=self._project,
                               entity=self.shot_ent,
                               step=None,
                               task=None,
                               user=self._user)

        key = [
               ['project', 'is', self._project],
               ['entity', 'is', self.shot_ent],
               ["published_file_type", "is", published_file_type],
               ['name', 'is', version_file_name],
               ['version_number', 'is', int(version)]
              ]
        self.published_ent = self._sg.find_one("PublishedFile", key, ['version_number'])

        if self.published_ent:
            return (self.published_ent, 'OLD')

        if seq_type == "org":
            published_type = "Plate"
        elif seq_type == "ref":
            published_type = "Reference"
        else:
            published_type = "Source"

        publish_data = {
                        "tk": self._app.tank,
                        "context": context,
                        "path": published_file,
                        "name": version_file_name,
                        "created_by": self._user,
                        "version_number": version,
                        # "thumbnail_path": item.get_thumbnail_as_path(),
                        "published_file_type": published_type,
                        # "dependency_paths": publish_dependencies
                        }

        if published_file is not None:
            self.published_ent = sgtk.util.register_publish(**publish_data)
            return (self.published_ent, 'NEW')
        return ({}, None)