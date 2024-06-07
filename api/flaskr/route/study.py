from flask import Flask, Response,request 
from flaskr.route.common import bypass_token_validation, make_common_response
from flaskr.service.common.models import raise_param_error
from flaskr.service.study.funcs import get_lesson_tree_to_study, get_study_record, run_script, update_attend_lesson_info



def register_study_handler(app:Flask,path_prefix:str)->Flask:
    app.logger.info('register_study_handler is called, path_prefix is {}'.format(path_prefix))
    @app.route(path_prefix+'/run',methods=['POST'])
    def run_lesson_script():
        course_id = request.get_json().get('course_id', 'dfca19aab2654fe4882e002a58567240')
        lesson_id = request.get_json().get('lesson_id', None)
        input = request.get_json().get('input', None)
        input_type = request.get_json().get('input_type','start')
        if course_id =="" or course_id is None:
            course_id = 'dfca19aab2654fe4882e002a58567240' 
        user_id = request.user.user_id
        return Response(run_script(app,course_id=course_id,lesson_id=lesson_id,user_id=user_id,input=input,input_type=input_type), mimetype="text/event-stream")
   

    @app.route(path_prefix+'/get_lesson_tree', methods=['GET'])
    def get_lesson_tree_study():
        course_id = request.args.get('course_id')
        if not course_id:
            raise_param_error("doc_id is not found")
        user_id =request.user.user_id 
        return make_common_response(get_lesson_tree_to_study(app,user_id,course_id))
    @app.route(path_prefix+'/get_lesson_study_record', methods=['GET'])
    def get_lesson_study_record():
        lesson_id = request.args.get('lesson_id')
        if not lesson_id:
            raise_param_error("lesson_id is not found")
        user_id =request.user.user_id
        return make_common_response(get_study_record(app,user_id,lesson_id))
    

    @app.route(path_prefix+"/test_attend",methods=['GET'])
    @bypass_token_validation
    def test_attend():


        attend_id = request.args.get("attend_id")


        return make_common_response(update_attend_lesson_info(app,attend_id))


    return app