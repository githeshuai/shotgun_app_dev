import tank
import sys
sys.path.insert(0, "Z:/miraSG")
import miraCore
from miraLibs.pipeLibs.get_engine_from_step import get_engine_from_step
from miraLibs.pyLibs import join_path
from miraLibs.pipeLibs import pipeFile
from miraLibs.deadlineLibs import submit
from miraLibs.pipeLibs.get_task_name import get_task_name


class TaskStart(tank.platform.Application):

    def init_app(self):

        deny_permissions = self.get_setting("deny_permissions")
        deny_platforms = self.get_setting("deny_platforms")
                
        p = {
            "title": "Task Start",
            "deny_permissions": deny_permissions,
            "deny_platforms": deny_platforms,
            "supports_multiple_selection": True
        }
        
        self.engine.register_command("task_start", self.task_start, p)

    def task_start(self, entity_type, entity_ids):
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
                self.do_start(entity_type, entity_ids)
            except Exception, error:
                self.log_error(error)

    def do_start(self, entity_type, entity_ids):
        # get current task
        for eid in entity_ids:
            # Use the path cache to look up all paths linked to the task's entity
            context = self.tank.context_from_entity(entity_type, eid)
            step = context.step
            step_info = self.tank.shotgun.find_one("Step", [["id", "is", step["id"]]], ["short_name"])
            step_short_name = step_info["short_name"]
            engine_name = get_engine_from_step(step_short_name)
            if not engine_name:
                self.log_warning("Can't get engine from this task step.")
                continue
            engine = "tk-%s" % engine_name
            link_type = context.entity["type"]
            if link_type == "Asset":
                template_name = "%s_asset_work" % engine_name
            else:
                template_name = "%s_shot_work" % engine_name
            template = self.tank.templates[template_name]
            fields = context.as_template_fields(template)
            fields['version'] = 0
            task_path = template.apply_fields(fields)
            task_path = task_path.replace("\\", "/")
            self.start_from_task_path(task_path)
            self.tank.shotgun.update(entity_type, eid, {"sg_status_list": "hld"})

    @staticmethod
    def start_from_task_path(work_file):
        scripts_dir = miraCore.get_scripts_dir()
        start_script_path = join_path.join_path2(scripts_dir, "pipeTools", "pipeline", "task_start", "start.py")
        obj = pipeFile.PathDetails.parse_path(work_file)
        task_name = get_task_name(obj)
        deadline_job_name = "start_%s" % task_name
        # work_file, change_task
        argv = work_file
        submitter = u'pipemanager'
        tar_name = u'pipemanager'
        submit.submit_python_job(deadline_job_name, start_script_path, argv, submitter, tar_name)
