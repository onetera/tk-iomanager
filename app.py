# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

def get_rez_root_command():

    return 'rez-env rez -- printenv REZ_REZ_ROOT'

def get_rez_module_root():
        
        
    command = get_rez_root_command()
    module_path, stderr = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()

    module_path = module_path.strip()

    if not stderr and module_path:
        return module_path

    return ''


def set_module_path(module_path):
    
    for module in module_path.split(":"):
        sys.path.append(module)

import sys
import os
import subprocess

try:
    import rez as _
except ImportError:
    rez_path = get_rez_module_root()
    if not rez_path:
        raise EnvironmentError('rez is not installed and could not be automatically found. Cannot continue.')

    sys.path.append(rez_path)
from rez.resolved_context import ResolvedContext
cotext = ResolvedContext(['tractor','pyseq','Xlrd','XlsxWriter','pydpx_meta','pyopenexr_tk','Pillow'])
module_path = cotext.get_environ()['PYTHONPATH']
set_module_path(module_path)


from sgtk.platform import Application



class StgkStarterApp(Application):
    """
    The app entry point. This class is responsible for intializing and tearing down
    the application, handle menu registration etc.
    """
    
    def init_app(self):
        """
        Called as the application is being initialized
        """
        
        # first, we use the special import_module command to access the app module
        # that resides inside the python folder in the app. This is where the actual UI
        # and business logic of the app is kept. By using the import_module command,
        # toolkit's code reload mechanism will work properly.
        try:
            app_payload = self.import_module("app")
        # now register a *command*, which is normally a menu entry of some kind on a Shotgun
        # menu (but it depends on the engine). The engine will manage this command and 
        # whenever the user requests the command, it will call out to the callback.

        # first, set up our callback, calling out to a method inside the app module contained
        # in the python folder of the app
            menu_callback = lambda : app_payload.dialog.show_dialog(self)
        # now register the command with the engine
            self.engine.register_command("IO Manager", menu_callback)
        except Exception:
            import traceback
            traceback.print_exc()

