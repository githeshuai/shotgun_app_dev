import os
import tank
import sys
sys.path.insert(0, "Z:/miraSG")
import miraCore
from miraLibs.pyLibs import join_path
from miraLibs.pipeLibs import pipeFile
from miraLibs.deadlineLibs import submit
from miraLibs.pipeLibs.get_task_name import get_task_name


class TaskPublish(tank.platform.Application):

    def init_app(self):

        deny_permissions = self.get_setting("deny_permissions")
        deny_platforms = self.get_setting("deny_platforms")
                
        p = {
            "title": "Task Publish",
            "deny_permissions": deny_permissions,
            "deny_platforms": deny_platforms,
            "supports_multiple_selection": True
        }
        
        self.engine.register_command("task_publish", self.task_publish, p)

    def task_publish(self, entity_type, entity_ids):
        if len(entity_ids) == 0:
            self.log_info("No entities specified!")
            return
        try:
            entities_processed = self.tank.create_filesystem_structure(entity_type, entity_ids)
        except tank.TankError, tank_error:
            # tank errors are errors that are expected and intended for the user
            self.log_error(tank_error)
        except Exception, error:
            # other errors are not expected and probably bugs - here it's useful with a callstack.
            self.log_exception("Error when creating folders!")
        else:
            try:
                self.do_publish(entity_type, entity_ids)
            except Exception, error:
                self.log_error(error)

    def do_publish(self, entity_type, entity_ids):
        # get current task
        for eid in entity_ids:
            # get the work file
            filters = [["id", "is", eid]]
            entity_info = self.tank.shotgun.find_one(entity_type, filters, ["sg_workfile"])
            work_file = entity_info["sg_workfile"] if entity_info. has_key("sg_workfile") else None
            if not work_file:
                self.log_warning("Can't get current task(id: %s) sg_workfile" % eid)
                continue
            if not os.path.isfile(work_file):
                self.log_error("%s is not an exist file." % work_file)
                continue
            self.publish(work_file)
            self.tank.shotgun.update(entity_type, eid, {"sg_status_list": "psh"})

    @staticmethod
    def publish(work_file):
        scripts_dir = miraCore.get_scripts_dir()
        start_script_path = join_path.join_path2(scripts_dir, "pipeTools", "pipeline", "task_publish", "publish.py")
        obj = pipeFile.PathDetails.parse_path(work_file)
        task_name = get_task_name(obj)
        deadline_job_name = "publish_%s" % task_name
        # work_file, change_task
        argv = work_file
        submitter = u'pipemanager'
        tar_name = u'pipemanager'
        submit.submit_python_job(deadline_job_name, start_script_path, argv, submitter, tar_name)
