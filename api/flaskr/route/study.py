from flask import Flask, Response,request 
from flaskr.service.study.funcs import run_script



def register_study_handler(app:Flask,path_prefix:str)->Flask:
    app.logger.info('register_study_handler is called, path_prefix is {}'.format(path_prefix))
    @app.route(path_prefix+'/run',methods=['POST'])
    def run_lesson_script():
        course_id = request.get_json().get('course_id', 'dfca19aab2654fe4882e002a58567240')
        input = request.get_json().get('input', None)
        script_id = request.get_json().get('script_id', None)
        if course_id =="" or course_id is None:
            course_id = 'dfca19aab2654fe4882e002a58567240' 
        user_id = request.user.user_id
        return Response(run_script(app,course_id=course_id,user_id=user_id,input=input,script_id=script_id), mimetype="text/event-stream")
   
    @app.route(path_prefix+'/next',methods=['POST'])
    def next_script():
        pass
    @app.route(path_prefix+'/current',methods=['POST'])
    def current_script():
        pass
    return app