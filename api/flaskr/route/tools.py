from flask import Flask, Response,request 
from flaskr.route.common import bypass_token_validation, make_common_response
from flaskr.service.common.models import raise_param_error
from flaskr.service.study.funcs import get_lesson_tree_to_study, get_study_record, reset_user_study_info, run_script, update_attend_lesson_info




def register_tools_handler(app:Flask,path_prefix:str)->Flask:
    # app.logger.info('register_study_handler is called, path_prefix is {}'.format(path_prefix))
    @app.route(path_prefix+'/reset',methods=['GET'])
    def reset_course():
        """
        重置用户学习信息    
        ---
        tags:
          - 工具
        
        """
        user_id = request.user.user_id
        return make_common_response(reset_user_study_info(app,user_id))
    return app