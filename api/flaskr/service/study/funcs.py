from concurrent.futures import thread
import datetime
import json
import re
import openai
from typing import Generator
from flask import Flask
from flaskr.service.lesson.funs import AILessonInfoDTO
from flaskr.service.profile.funcs import get_user_profiles, save_user_profiles
from flaskr.service.sales.consts import ATTEND_STATUS_TYPES, ATTEND_STATUS_UNAVAILABE, ATTEND_STATUS_VALUES
from flaskr.service.study.const import *
from langchain.prompts import PromptTemplate


from flaskr.service.lesson.const import CONTENT_TYPE_IMAGE, LESSON_TYPE_BRANCH_HIDDEN, SCRIPT_TYPE_FIX, SCRIPT_TYPE_PORMPT, UI_TYPE_BUTTON, UI_TYPE_CONTINUED, UI_TYPE_INPUT, UI_TYPE_SELECTION
from ...dao import db

from flaskr.service.lesson.models import AICourse, AILesson, AILessonScript
from flaskr.service.sales.funs import AICourseLessonAttendDTO, init_trial_lesson
from flaskr.service.sales.models import ATTEND_STATUS_COMPLETED, ATTEND_STATUS_IN_PROGRESS, ATTEND_STATUS_NOT_STARTED, AICourseBuyRecord, AICourseLessonAttend
from .models import *
import time 

from ...api.langfuse import langfuse_client as langfuse

class AILessonAttendDTO:
    def __init__(self,lesson_no:str,lesson_name:str,lesson_id:str,status,children=None) -> None:
        self.lesson_no = lesson_no
        self.lesson_name = lesson_name
        self.lesson_id = lesson_id
        self.children = children
        self.status = status
    def __json__(self):
        return {
            'lesson_no':self.lesson_no,
            'lesson_name':self.lesson_name,
            'lesson_id':self.lesson_id,
            'status':self.status,
            'children':self.children
        }
class AICourseDTO:
    def __init__(self,course_id:str,course_name:str,lessons:list[AILessonAttendDTO]) -> None:
        self.course_id = course_id
        self.course_name = course_name
        self.lessons=lessons
    def __json__(self):
        return {
            'course_id':self.course_id,
            'course_name':self.course_name,
            'lessons':self.lessons
        }


class AICourseLessonAttendScriptDTO:
    def __init__(self, attend_id, script_id, lesson_id, course_id, user_id, script_index, script_role, script_content, status):
        self.attend_id = attend_id
        self.script_id = script_id
        self.lesson_id = lesson_id
        self.course_id = course_id
        self.user_id = user_id
        self.script_index = script_index
        self.script_role = script_role
        self.script_content = script_content
        self.status = status

    def __json__(self):
        return {
            "attend_id": self.attend_id,
            "script_id": self.script_id,
            "lesson_id": self.lesson_id,
            "course_id": self.course_id,
            "user_id": self.user_id,
            "script_index": self.script_index,
            "script_role": self.script_role,
            "script_content": self.script_content,
            "status": self.status
        }




client = openai.Client(api_key="sk-proj-TsOFXPGAkp6GZKt1AUinT3BlbkFJiFiJO0hAu7om7TOl4RRY") #,base_url="https://openai-api.kattgatt.com/v1")


def fmt(o):
    if isinstance(o, datetime.datetime):
        return o.isoformat()
    else:
        return o.__json__()
    
    


def get_profile_array(profile:str)->list:
    return re.findall(r'\[(.*?)\]', profile)

def get_fmt_prompt(app:Flask,user_id:str,profile_tmplate:str,input:str=None,profile_array_str:str=None)->str:

    app.logger.info("raw prompt:"+profile_tmplate)
    propmpt_keys = []
    profiles = {}
    if profile_array_str:
        propmpt_keys = get_profile_array(profile_array_str) 
        profiles = get_user_profiles(app,user_id,propmpt_keys)
    else:
        profiles = get_user_profiles(app,user_id)
        propmpt_keys = list(profiles.keys())
    if input:
        profiles['input'] = input
        propmpt_keys.append('input')
    app.logger.info(propmpt_keys)
    app.logger.info(profiles)
    
    prompt_template = PromptTemplate(input_variables=propmpt_keys, template=profile_tmplate)
    # prompt_keys = prompt_template.
    prompt = prompt_template.format(**profiles)
    app.logger.info('fomat input:{}'.format(prompt))
    return prompt.encode('utf-8').decode('utf-8')
 
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
    return    'data: '+json.dumps(ScriptDTO(script_type,script_content,script_id),default=fmt)+'\n\n'.encode('utf-8').decode('utf-8')
                
def get_current_lesson(app: Flask, lesssons:list[AICourseLessonAttendDTO] )->AICourseLessonAttendDTO:
    return lesssons[0]


def get_script(app:Flask,attend_id:str,next:bool)->AILessonScript:

 
    attend_info = AICourseLessonAttend.query.filter(AICourseLessonAttend.attend_id ==attend_id).first()
    app.logger.info("get next script,current:{},next:{}".format(attend_info.script_index,next))
    if attend_info.status == ATTEND_STATUS_NOT_STARTED:
        attend_info.status = ATTEND_STATUS_IN_PROGRESS
        attend_info.script_index = 1
    elif next:
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
def generation_attend(app:Flask,attend:AICourseLessonAttendDTO,script_info:AILessonScript)->AICourseLessonAttendScript:
    attendScript = AICourseLessonAttendScript()
    attendScript.attend_id = attend.attend_id
    attendScript.user_id = attend.user_id
    attendScript.lesson_id =  script_info.lesson_id
    attendScript.course_id = attend.course_id   
    attendScript.script_id = script_info.script_id
    return attendScript


# 得到一个课程的System Prompt

def get_lesson_system(app:Flask,lesson_id:str)->str:
    with app.app_context:
        # 缓存逻辑 
        lesson_ids = [lesson_id]
        lesson = AILesson.query.filter(AILesson.lesson_id == lesson_id).first()
        lesson_no = lesson.lesson_no 
        parent_no = lesson_no
 
        if len(parent_no)>2:
            parent_no = parent_no[:2]
        if parent_no != lesson_no:
            parent_lesson = AILesson.query.filter(AILesson.lesson_no == parent_no).first()
            if parent_lesson:
                lesson_ids.append(parent_lesson.lesson_id)
        scripts = AILessonScript.query.filter(AILessonScript.lesson_id.in_(lesson_ids) == True,AILessonScript.script_content_type).all()
        if len(scripts)>0:
            for script in scripts:
                if script.lesson_id == lesson_id:
                    return script.script_prompt
            return scripts[0].script_prompt
        return None

def run_script(app: Flask, user_id: str, course_id: str, lesson_id: str=None,input:str=None,input_type:str=None)->Generator[ScriptDTO,None,None]:
    with app.app_context():
        attend = AICourseLessonAttendDTO
        if not lesson_id:
            # 检查有没有购课记录
            buy_record = AICourseBuyRecord.query.filter_by(user_id=user_id, course_id=course_id).first() 
            if not buy_record:
                lessons = init_trial_lesson(app, user_id, course_id)
                attend = get_current_lesson(app,lessons)
                lesson_id = attend.lesson_id
        else:
            # 获取课程记录
            app.logger.info("user_id:{},course_id:{},lesson_id:{}".format(user_id,course_id,lesson_id))
            attend_info = AICourseLessonAttend.query.filter_by(user_id=user_id, course_id=course_id,lesson_id=lesson_id).first()
            if not attend_info:
                # 没有课程记录
                for i in "请购买课程":
                    yield make_script_dto("text",i,None)
                    time.sleep(0.04)
                yield make_script_dto("text_end","",None)
                return
            attend = AICourseLessonAttendDTO(attend_info.attend_id,attend_info.lesson_id,attend_info.course_id,attend_info.user_id,attend_info.status,attend_info.script_index)
        db.session.commit()


        # Langfuse 集成 

        trace_args ={}
        trace_args['user_id'] = user_id
        trace_args['session_id'] = attend.attend_id
        trace_args['input'] = input 
        trace_args['name'] = "ai-python"
        trace = langfuse.trace(**trace_args)
        trace_args["output"]=""

        check_success = False
        next = False
        if input_type == INPUT_TYPE_CONTINUE:
            next=True
        while True:
            # 如果有用户输入,就得到当前这一条,否则得到下一条
            script_info = get_script(app,attend_id=attend.attend_id,next=next)
         
            if script_info:
                app.logger.info("begin to run script:{},model:{},input_type:{}".format(script_info.script_id,script_info.script_model,input_type))
                log_script = generation_attend(app,attend,script_info)
                # 得到脚本
        
                # 输入校验
                if input_type == INPUT_TYPE_TEXT:
                    check_flag = script_info.script_check_flag
                    prompt = get_fmt_prompt(app,user_id,script_info.script_check_prompt,input,script_info.script_profile)
                    ## todo 换成通用的
                    log_script = generation_attend(app,attend,script_info)
                    log_script.script_content = input
                    log_script.script_role = ROLE_STUDENT 
                    db.session.add(log_script)

                    span = trace.span(name="user_input",input=input)

                    generation = span.generation( model="gpt-3.5-turbo-0125",input=[{"role": "user", "content": prompt}])
                     
                    resp = client.chat.completions.create(
                        model="gpt-3.5-turbo-0125",
                        stream=True,
                        temperature=0.1,
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
                    generation.end(output=response_text)


                    if check_success:
                        app.logger.info('check success')
                        values = response_text.replace(check_flag,"")
                        if values.strip() != "":
                            profile_tosave = json.loads(values)
                            save_user_profiles(app,user_id,profile_tosave)
                        input = None
                        next = True
                        input_type = INPUT_TYPE_CONTINUE
                        span.end()
                        continue
                    else:
                        log_script = generation_attend(app,attend,script_info)
                        log_script.script_content = response_text
                        log_script.script_role = ROLE_TEACHER
                        db.session.add(log_script)
                        span.end(output=response_text)

                        trace_args ["output"] = trace_args["output"]+"\r\n"+response_text
                        trace.update(**trace_args)
                        break
                elif input_type == INPUT_TYPE_CONTINUE:
                    log_script = generation_attend(app,attend,script_info)
                    log_script.script_content = "继续"
                    log_script.script_role = ROLE_STUDENT
                    db.session.add(log_script)

                    span = trace.span(name="user_continue",input=input)
                    span.end()

                    pass
                elif input_type == INPUT_TYPE_SELECT:
                    profile_keys = get_profile_array(script_info.script_ui_profile)

                    profile_tosave = {}
                    for k in profile_keys:
                        profile_tosave[k]=input
                    save_user_profiles(app,user_id,profile_tosave)
                  


                    log_script = generation_attend(app,attend,script_info)
                    log_script.script_content = input
                    log_script.script_role = ROLE_STUDENT
                    db.session.add(log_script)
                    input = None
                    next = True
                    input_type = INPUT_TYPE_CONTINUE
                    span = trace.span(name="user_select",input=input)
                    span.end()
                    continue 
                if script_info.script_type == SCRIPT_TYPE_FIX:
                    prompt = ""
                    if script_info.script_content_type == CONTENT_TYPE_IMAGE:
                        prompt = "![img]({})".format(script_info.script_media_url)
                        yield make_script_dto("text",prompt,script_info.script_id)
                    else:
                        prompt = get_fmt_prompt(app,user_id,script_info.script_prompt,profile_array_str=script_info.script_profile)
                        for i in prompt:
                            msg =  make_script_dto("text",i,script_info.script_id)
                            yield msg
                            time.sleep(0.04)
                    log_script = generation_attend(app,attend,script_info)
                    log_script.script_content = prompt
                    log_script.script_role = ROLE_TEACHER
                    db.session.add(log_script)
                    data = ScriptDTO("text_end","")

                    span = trace.span(name="fix_script")
                    span.end(output=prompt)

                    trace_args ["output"] = trace_args["output"]+"\r\n"+prompt
                    trace.update(**trace_args)
                    msg =  'data: '+json.dumps(data,default=fmt)+'\n\n'
                    app.logger.info(msg)


                    yield msg
                    
                elif script_info.script_type == SCRIPT_TYPE_PORMPT:
                    span = trace.span(name="prompt_sript")
                    
                    prompt = get_fmt_prompt(app,user_id,script_info.script_prompt,profile_array_str=script_info.script_profile)


                    generation = span.generation( model="gpt-3.5-turbo-0125",input=[
                            {"role": "user", "content": prompt}
                        ])
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
                    generation.end(output=response_text)
                    span.end(output=response_text)


                    trace_args ["output"] = trace_args["output"]+"\r\n"+prompt
                    trace.update(**trace_args)
                    log_script = generation_attend(app,attend,script_info)
                    log_script.script_content = response_text
                    log_script.script_role = ROLE_TEACHER
                    db.session.add(log_script)
                    yield make_script_dto("text_end","",None)
                if script_info.script_ui_type == UI_TYPE_CONTINUED:
                    continue
                elif script_info.script_ui_type == UI_TYPE_INPUT and not check_success:
                    yield  make_script_dto("input",script_info.script_ui_content,script_info.script_id) 
                    break
                elif script_info.script_ui_type == UI_TYPE_BUTTON:
                    btn = [{
                        "label":script_info.script_ui_content,
                        "value":script_info.script_ui_content
                    }]
                    yield make_script_dto("buttons",{"title":"接下来","buttons":btn},script_info.script_id)
                    break
                elif script_info.script_ui_type == UI_TYPE_SELECTION:
                    yield make_script_dto("buttons",{"title":script_info.script_ui_content,"buttons":json.loads(script_info.script_other_conf)["btns"]},script_info.script_id)
                    break
            else:
                # 更新完课信息
                attend_updates = update_attend_lesson_info(app,attend_id=attend_info.attend_id)
                # 更新到课信息
                if len (attend_updates) > 0 :
                    for attend_update in attend_updates:
                        yield make_script_dto("lesson_update",attend_update.__json__(),"")
                break
        db.session.commit()


def get_lesson_and_attend_info(app:Flask,parent_no,course_id,user_id):
    lessons = AILesson.query.filter(AILesson.lesson_no.like(parent_no+'%'),AILesson.course_id ==course_id,AILesson.lesson_type !=LESSON_TYPE_BRANCH_HIDDEN, AILesson.status==1 ).all()
    if len(lessons)==0:
        return [] 
    attend_infos = AICourseLessonAttend.query.filter(AICourseLessonAttend.lesson_id.in_([lesson.lesson_id for lesson in lessons]),AICourseLessonAttend.user_id == user_id ).all()
    app.logger.info("attends:{}".format(",".join(a.attend_id for a in attend_infos)))
    attend_lesson_infos = [{'attend':attend,'lesson': [lesson for lesson in lessons if lesson.lesson_id == attend.lesson_id][0]} for attend in attend_infos]
    attend_lesson_infos =  sorted(attend_lesson_infos, key=lambda x: (len(x['lesson'].lesson_no), x['lesson'].lesson_no)) 
    return attend_lesson_infos

def update_attend_lesson_info(app:Flask,attend_id:str)->list[AILessonAttendDTO]:
    res = []
    attend_info = AICourseLessonAttend.query.filter(AICourseLessonAttend.attend_id ==attend_id).first()
    lesson = AILesson.query.filter(AILesson.lesson_id == attend_info.lesson_id).first()
    lesson_no = lesson.lesson_no
    parent_no = lesson_no
    attend_info.status = ATTEND_STATUS_COMPLETED
    res.append(AILessonAttendDTO(lesson_no,lesson.lesson_name,lesson.lesson_id,ATTEND_STATUS_VALUES[ATTEND_STATUS_COMPLETED]))
 
    if len(parent_no)>2:
        parent_no = parent_no[:2]
    attend_lesson_infos =  get_lesson_and_attend_info(app,parent_no,lesson.course_id,attend_info.user_id)
    if attend_lesson_infos[-1]['attend'].attend_id == attend_id:
        # 最后一个已经完课
        # 整体章节完课
        attend_lesson_infos[0]['attend'].status = ATTEND_STATUS_COMPLETED
        res.append(AILessonAttendDTO(attend_lesson_infos[0]['lesson'].lesson_no,attend_lesson_infos[0]['lesson'].lesson_name,attend_lesson_infos[0]['lesson'].lesson_id,ATTEND_STATUS_VALUES[ATTEND_STATUS_COMPLETED]))
        # 找到下一章节进行解锁
        next_no = str(int(parent_no)+1).zfill(2)
        next_lessons = get_lesson_and_attend_info(app,next_no,lesson.course_id,attend_info.user_id)
        if len(next_lessons) > 0 :
            # 解锁
            for next_lesson_attend in next_lessons:
                if next_lesson_attend['lesson'].lesson_no == next_no:
                    next_lesson_attend['attend'].status = ATTEND_STATUS_NOT_STARTED
                    res.append(AILessonAttendDTO(next_lesson_attend['lesson'].lesson_no,next_lesson_attend['lesson'].lesson_name,next_lesson_attend['lesson'].lesson_id,ATTEND_STATUS_VALUES[ATTEND_STATUS_NOT_STARTED]))
                if next_lesson_attend['lesson'].lesson_no == next_no+'01':
                    next_lesson_attend['attend'].status = ATTEND_STATUS_NOT_STARTED
                    res.append(AILessonAttendDTO(next_lesson_attend['lesson'].lesson_no,next_lesson_attend['lesson'].lesson_name,next_lesson_attend['lesson'].lesson_id,ATTEND_STATUS_VALUES[ATTEND_STATUS_NOT_STARTED]))

    for i in range(len(attend_lesson_infos)):
        app.logger.info(i)
        if i>0 and  attend_lesson_infos[i-1]['attend'].attend_id == attend_id:
            # 更新下一节
            app.logger.info('to update' + attend_lesson_infos[i]['lesson'].lesson_no)
            attend_lesson_infos[i]['attend'].status = ATTEND_STATUS_NOT_STARTED
            res.append(AILessonAttendDTO( attend_lesson_infos[i]['lesson'].lesson_no,  attend_lesson_infos[i]['lesson'].lesson_name,  attend_lesson_infos[i]['lesson'].lesson_id,ATTEND_STATUS_VALUES[ATTEND_STATUS_NOT_STARTED]))
    return res








def get_lesson_tree_to_study(app:Flask,user_id:str,course_id:str)->AICourseDTO:
    with app.app_context():
          # 检查有没有购课记录
        buy_record = AICourseBuyRecord.query.filter_by(user_id=user_id, course_id=course_id).first() 
        if not buy_record:
            app.logger.info('no buy record found')
            # 没有购课记录
            # 生成体验课记录
            init_trial_lesson(app, user_id, course_id)
        lessons = AILesson.query.filter(course_id==course_id,AILesson.lesson_type !=LESSON_TYPE_BRANCH_HIDDEN, AILesson.status==1).all()
        lessons = sorted(lessons, key=lambda x: (len(x.lesson_no), x.lesson_no))
        lesson_ids =  [ i.lesson_id  for  i in lessons]
        app.logger.info("lesson ids :{}".format(lesson_ids))
        app.logger.info("user_id:"+user_id)
        attend_infos = AICourseLessonAttend.query.filter(AICourseLessonAttend.user_id == user_id,AICourseLessonAttend.course_id == course_id).all()
        app.logger.info("attends count:{}".format(len(attend_infos)))
        attend_infos_map = {i.lesson_id:i for i in attend_infos}
        lessonInfos = []
        lesson_dict = {}
        for lesson in lessons:
            attend_info = attend_infos_map.get(lesson.lesson_id,None)
            status = ATTEND_STATUS_VALUES[attend_info.status if  attend_info else  ATTEND_STATUS_UNAVAILABE]
            lessonInfo = AILessonAttendDTO(lesson.lesson_no,lesson.lesson_name,lesson.lesson_id,status, [])
            lesson_dict[lessonInfo.lesson_no] = lessonInfo
            if len(lessonInfo.lesson_no) == 2:  # 假设2位数是根节点
                lessonInfos.append(lessonInfo)
            else:
                # 获取父节点编号
                parent_no = lessonInfo.lesson_no[:-2]
                if parent_no in lesson_dict:
                    lesson_dict[parent_no].children.append(lessonInfo)
        course_info = AICourse.query.filter(AICourse.course_id == course_id).first()
        return AICourseDTO(course_id=course_id,course_name=course_info.course_name,lessons=lessonInfos)
    


class StudyRecordDTO:
    def __init__(self,script_index,script_role,script_type,script_content):
        self.script_index = script_index
        self.script_role = script_role
        self.script_type = script_type
        self.script_content = script_content
    def __json__(self):
        return {
            "script_index": self.script_index,
            "script_role": self.script_role,
            "script_type": self.script_type,
            "script_content": self.script_content
        }

def get_study_record(app:Flask,user_id:str,lesson_id:str)->list[StudyRecordDTO]:
    with app.app_context():
        attend_info = AICourseLessonAttend.query.filter_by(user_id=user_id,lesson_id=lesson_id).first()
        if not attend_info:
            return None
        attend_scripts = AICourseLessonAttendScript.query.filter_by(attend_id=attend_info.attend_id).all()
        return [StudyRecordDTO(i.script_index,ROLE_VALUES[i.script_role],0,i.script_content) for i in attend_scripts]