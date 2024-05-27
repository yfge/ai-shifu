from concurrent.futures import thread
import datetime
import json
import re
import openai
from typing import Generator
from flask import Flask
from flaskr.service.profile.funcs import get_user_profiles, save_user_profiles
from langchain_core.prompts import PromptTemplate


from flaskr.service.lesson.const import SCRIPT_TYPE_FIX, SCRIPT_TYPE_PORMPT, UI_TYPE_BUTTON, UI_TYPE_CONTINUED, UI_TYPE_INPUT
from ...dao import db

from flaskr.service.lesson.models import AILessonScript
from flaskr.service.sales.funs import AICourseLessonAttendDTO, init_trial_lesson
from flaskr.service.sales.models import ATTEND_STATUS_COMPLETED, ATTEND_STATUS_IN_PROGRESS, ATTEND_STATUS_NOT_STARTED, AICourseBuyRecord, AICourseLessonAttend
import time 


client = openai.Client(api_key="sk-proj-TsOFXPGAkp6GZKt1AUinT3BlbkFJiFiJO0hAu7om7TOl4RRY")#,base_url="https://openai-api.kattgatt.com/v1")


def fmt(o):
    if isinstance(o, datetime.datetime):
        return o.isoformat()
    else:
        return o.__json__()
    
    


def get_profile_array(profile:str)->list:
    return re.findall(r'\[(.*?)\]', profile)


#
#   
#
class ScriptDTO:
    def __init__(self,script_type,script_content,script_id=None):
        self.script_type = script_type
        self.script_content = script_content
        self.script_id = script_id
    def __json__(self):
        return {
            "type": self.script_type,
            "content": self.script_content,
            "id": self.script_id    
        }


def make_script_dto(script_type,script_content,script_id)->str:
    return    'data: '+json.dumps(ScriptDTO(script_type,script_content,script_id),default=fmt)+'\n\n'
                
def get_current_lesson(app: Flask, lesssons:list[AICourseLessonAttendDTO] )->AICourseLessonAttendDTO:
    return lesssons[0]

# Path: flaskr/service/study/funcs.py
# 运行脚本
# 1


def get_next_script(app: Flask,attend_id:str)->AILessonScript:
        attend_info = AICourseLessonAttend.query.filter(AICourseLessonAttend.attend_id ==attend_id ).first()
        if attend_info.status == ATTEND_STATUS_NOT_STARTED:
            # 还没开始
            attend_info.status = ATTEND_STATUS_IN_PROGRESS
            attend_info.script_index = 1
           # 获取第一个脚本
        else:
            # 获取下一个脚本
            attend_info.script_index = attend_info.script_index + 1
        script_info = AILessonScript.query.filter(AILessonScript.lesson_id==attend_info.lesson_id,AILessonScript.script_index==attend_info.script_index).first()
        if not script_info:
            # 没有下一个脚本
            attend_info.status = ATTEND_STATUS_COMPLETED
            app.logger.info('no script found')
        db.session.commit()
        return script_info
def get_script_by_id(app: Flask,script_id:str)->AILessonScript:
    return AILessonScript.query.filter_by(script_id=script_id).first()

def run_script(app: Flask, user_id: str, course_id: str, lesson_id: str=None,input:str=None, script_id: str=None)->Generator[ScriptDTO,None,None]:
    with app.app_context():
        attend = AICourseLessonAttendDTO
        if not lesson_id:
            # 检查有没有购课记录
            buy_record = AICourseBuyRecord.query.filter_by(user_id=user_id, course_id=course_id).first() 
            if not buy_record:
                app.logger.info('no buy record found')
                # 没有购课记录
                # 生成体验课记录
                lessons = init_trial_lesson(app, user_id, course_id)
                attend = get_current_lesson(app,lessons)
                lesson_id = attend.lesson_id
        else:
            # 获取课程记录
            attend_info = AICourseLessonAttend.query.filter_by(user_id=user_id, course_id=course_id,lesson_id=lesson_id).first()
            if not attend_info:
                app.logger.info('no attend record found')
            attend = AICourseLessonAttendDTO(attend_info.attend_id,attend_info.lesson_id,attend_info.course_id,attend_info.user_id,attend_info.status,attend_info.index)
        app.logger.info('attend info:{},lesson_id :{}'.format(attend.attend_id,lesson_id))
        db.session.commit()
        check_success = False
        while True:
            script_info = AILessonScript
            if script_id and input:
                # 同时有Script ID和输入
                app.logger.info('script_id:{},input:{}'.format(script_id,input))
                script_info = get_script_by_id(app,script_id)
            else:
                script_info = get_next_script(app,attend.attend_id)
            if script_info:
            # 得到脚本
                if script_info.script_type == SCRIPT_TYPE_FIX:
                    if script_id and input:
                        vars = {"input":input}
                        prompt_template = PromptTemplate(input_variables=list(vars.keys()), template=script_info.script_check_prompt)
                        prompt = prompt_template.format(**vars)
                        check_flag = script_info.script_check_flag
                        ## todo 换成通用的
                        app.logger.info('prompt:{}'.format(prompt))
                        resp = client.chat.completions.create(
                            model="gpt-3.5-turbo-0125",
                            stream=True,
                            temperature=0.5,
                            messages=[
                                {"role": "user", "content": prompt}
                              
                            ])
                        response_text = ""
                        check_success = False
                        stream = False
                        for i in resp:
                            if len(response_text) >= len(check_flag):
                                if response_text.find(check_flag) in [0,1]:
                                    check_success = True
                                else:
                                    if stream == False:
                                        stream = True
                                        for text in response_text:
                                            yield make_script_dto("text",text,script_info.script_id)
                                            time.sleep(0.1)
                            current_content = i.choices[0].delta.content
                            if isinstance(current_content ,str):
                                response_text += current_content
                                if stream:
                                    yield make_script_dto("text", current_content,script_info.script_id)
                        app.logger.info('response_text:{}'.format(response_text))
                        if check_success:
                            app.logger.info('check success')
                            values = response_text.replace(check_flag,"")
                            profile_tosave = json.loads(values)
                            save_user_profiles(app,user_id,profile_tosave)
                            input = None
                    else:
                        for i in script_info.script_prompt:
                            yield make_script_dto("text",i,script_info.script_id)
                            time.sleep(0.1)
                    data = ScriptDTO("text_end","")
                    msg =  'data: '+json.dumps(data,default=fmt)+'\n\n'
                    yield msg
                elif script_info.script_type == SCRIPT_TYPE_PORMPT: 
                    propmpt_keys = get_profile_array(script_info.script_profile) 
                    profiles = get_user_profiles(app,user_id,propmpt_keys)
                    prompt_template = PromptTemplate(input_variables=propmpt_keys, template=script_info.script_prompt)
                    prompt = prompt_template.format(**profiles)
                    app.logger.info('prompt:{}'.format(prompt))
                    resp = client.chat.completions.create(
                        model="gpt-3.5-turbo-0125",
                        stream=True,
                        temperature=0.5,
                        messages=[
                            {"role": "user", "content": prompt}
                          
                        ])
                    response_text = ""
                    for chunk in resp:
                        current_content = chunk.choices[0].delta.content
                        if isinstance(current_content ,str):
                            response_text += current_content
                            yield make_script_dto("text", current_content,script_info.script_id)
                    yield make_script_dto("text_end","",None)
                if script_info.script_ui_type == UI_TYPE_CONTINUED:
                    continue
                elif script_info.script_ui_type == UI_TYPE_INPUT and not check_success:
                    yield  make_script_dto("input",script_info.script_ui_content,script_info.script_id) 
                    break
                elif script_info.script_ui_type == UI_TYPE_BUTTON:
                    yield make_script_dto("buttons",script_info.script_ui_content,script_info.script_id)
                    break
            else:
                break
        data = ScriptDTO("text_end","")
        msg =  'data: '+json.dumps(data,default=fmt)+'\n\n'
        yield msg


def run_current_script(app: Flask, user_id: str, course_id: str, lesson_id: str, script_id: str):
    pass