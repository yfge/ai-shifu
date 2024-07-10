from concurrent.futures import thread
import datetime
import json
import re
import openai
from typing import Generator
from flask import Flask, typing
from flaskr.service.user.models import User
from flaskr.service.common  import AppException
from flaskr.service.user.funs import get_sms_code_info, send_sms_code_without_check, verify_sms_code, verify_sms_code_without_phone
from flaskr.common import register_schema_to_swagger
from flaskr.service.lesson.funs import AILessonInfoDTO
from flaskr.service.profile.funcs import get_user_profiles, save_user_profiles
from flaskr.service.order.consts import ATTEND_STATUS_BRANCH, ATTEND_STATUS_TYPES, ATTEND_STATUS_UNAVAILABE, ATTEND_STATUS_VALUES
from flaskr.service.study.const import *
from langchain.prompts import PromptTemplate


from flaskr.service.lesson.const import CONTENT_TYPE_IMAGE, LESSON_TYPE_BRANCH_HIDDEN, SCRIPT_TYPE_FIX, SCRIPT_TYPE_PORMPT, SCRIPT_TYPE_SYSTEM, UI_TYPE_BRANCH, UI_TYPE_BUTTON, UI_TYPE_CHECKCODE, UI_TYPE_CONTINUED, UI_TYPE_INPUT, UI_TYPE_LOGIN, UI_TYPE_PHONE, UI_TYPE_SELECTION, UI_TYPE_TO_PAY
from ...dao import db

from flaskr.service.lesson.models import AICourse, AILesson, AILessonScript
from flaskr.service.order.funs import AICourseLessonAttendDTO, init_buy_record, init_trial_lesson
from flaskr.service.order.models import ATTEND_STATUS_COMPLETED, ATTEND_STATUS_IN_PROGRESS, ATTEND_STATUS_NOT_STARTED, AICourseBuyRecord, AICourseLessonAttend
from .models import *
import time 

from ...api.langfuse import langfuse_client as langfuse
from ...api.llm import invoke_llm
from typing import List




@register_schema_to_swagger
class AILessonAttendDTO:
    lesson_no:str
    lesson_name:str
    lesson_id:str
    status:str
    children:List[AICourseLessonAttendDTO]
    status:str
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

@register_schema_to_swagger
class AICourseDTO:
    course_id:str
    course_name:str
    lessons:list[AILessonAttendDTO]
    def __init__(self,course_id:str,course_name:str,lessons:List[AILessonAttendDTO]) -> None:
        self.course_id = course_id
        self.course_name = course_name
        self.lessons=lessons
    def __json__(self):
        return {
            'course_id':self.course_id,
            'course_name':self.course_name,
            'lessons':self.lessons
        }

@register_schema_to_swagger
class AICourseLessonAttendScriptDTO:
    attend_id:str
    script_id:str
    lesson_id:str
    course_id:str
    user_id:str
    script_index:int
    script_role:str
    script_content:str
    status:str
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



   

# 更新课程信息
@register_schema_to_swagger 
class ScriptDTO:
    script_type:str #  "'text' 'input' 'buttons' 'text_end'"
    script_content:str
    script_id:str
    def __init__(self,script_type,script_content,script_id=None):
        self.script_type = script_type
        self.script_content = script_content
        self.script_id = script_id
    def __json__(self):
        return {
            "type": self.script_type,
            "content": self.script_content,
            "script_id": self.script_id    
        }




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
    prompt_template_lc = PromptTemplate.from_template(profile_tmplate)
    keys = prompt_template_lc.input_variables
    fmt_keys = {}
    for key in keys:
        if key in profiles:
            fmt_keys[key] = profiles[key]
    app.logger.info(fmt_keys)
    if len(fmt_keys) == 0:
        if len(profile_tmplate) == 0:
            prompt = input
        else: 
            prompt = profile_tmplate
    else:
        prompt = prompt_template_lc.format(**fmt_keys)
    app.logger.info('fomat input:{}'.format(prompt))
    return prompt
 

# 从文本中提取json对象
def extract_json(app:Flask,text:str):
    stack = []
    start = None
    for i, char in enumerate(text):
        if char == '{':
            if not stack:
                start = i
            stack.append(char)
        elif char == '}':
            if stack:
                stack.pop()
                if not stack:
                    json_str = text[start:i+1]
                    try:
                        json_obj = json.loads(json_str)
                        return json_obj
                    except json.JSONDecodeError:
                        pass
    return {}

def make_script_dto(script_type,script_content,script_id)->str:
    return    'data: '+json.dumps(ScriptDTO(script_type,script_content,script_id),default=fmt)+'\n\n'.encode('utf-8').decode('utf-8')
def get_current_lesson(app: Flask, lesssons:list[AICourseLessonAttendDTO] )->AICourseLessonAttendDTO:
    return lesssons[0]
def get_script(app:Flask,attend_id:str,next:bool) :
    attend_info = AICourseLessonAttend.query.filter(AICourseLessonAttend.attend_id ==attend_id).first()
    attend_infos = []
    app.logger.info("get next script,current:{},next:{}".format(attend_info.script_index,next))
    if attend_info.status == ATTEND_STATUS_NOT_STARTED:
        attend_info.status = ATTEND_STATUS_IN_PROGRESS
        attend_info.script_index = 1
           # 检查是否是第一节课
        lesson = AILesson.query.filter(AILesson.lesson_id == attend_info.lesson_id).first()
        attend_infos.append(AILessonAttendDTO(lesson.lesson_no,lesson.lesson_name,lesson.lesson_id,ATTEND_STATUS_VALUES[ATTEND_STATUS_IN_PROGRESS]))
        app.logger.info(lesson.lesson_no)
        app.logger.info(lesson.lesson_no[-2:])   
        if len(lesson.lesson_no)>=2 and lesson.lesson_no[-2:] == '01':
            # 第一节课
            app.logger.info('first lesson')
            parent_lesson = AILesson.query.filter(AILesson.lesson_no == lesson.lesson_no[:-2]).first()
            parent_attend = AICourseLessonAttend.query.filter(AICourseLessonAttend.lesson_id == parent_lesson.lesson_id,AICourseLessonAttend.user_id == attend_info.user_id).first()
            if parent_attend.status == ATTEND_STATUS_NOT_STARTED:
                parent_attend.status = ATTEND_STATUS_IN_PROGRESS
                attend_infos.append(AILessonAttendDTO(parent_lesson.lesson_no,parent_lesson.lesson_name,parent_lesson.lesson_id,ATTEND_STATUS_VALUES[ATTEND_STATUS_IN_PROGRESS]))
    elif attend_info.status == ATTEND_STATUS_BRANCH:
        # 分支课程
        current = attend_info
        assoation = AICourseAttendAsssotion.query.filter(AICourseAttendAsssotion.from_attend_id==current.attend_id).first()
        if assoation:
            current = AICourseLessonAttend.query.filter(AICourseLessonAttend.attend_id==assoation.to_attend_id).first()
        while current.status == ATTEND_STATUS_BRANCH:
            # 分支课程
            assoation = AICourseAttendAsssotion.query.filter(AICourseAttendAsssotion.from_attend_id==current.attend_id).first()
            if assoation:
                current = AICourseLessonAttend.query.filter(AICourseLessonAttend.attend_id==assoation.to_attend_id).first()
        script_info,attend_infos = get_script(app,current.attend_id,next)
        if script_info:
            return script_info,[]
        else:
            current.status = ATTEND_STATUS_COMPLETED
            attend_info.status = ATTEND_STATUS_IN_PROGRESS
            db.session.commit()
            return get_script(app,attend_id,next)
    elif next:
        attend_info.script_index = attend_info.script_index + 1
    script_info = AILessonScript.query.filter(AILessonScript.lesson_id==attend_info.lesson_id,AILessonScript.status ==1,AILessonScript.script_index==attend_info.script_index).first()
    if not script_info:

        attend_info.status = ATTEND_STATUS_COMPLETED
    db.session.commit()
    return script_info,attend_infos

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


def check_phone_number(app,user_id,input):
    # 检查手机号是否合法
    if not re.match(r'^1[3-9]\d{9}$', input):
        return False
    return True

# 得到一个课程的System Prompt

def get_lesson_system(lesson_id:str)->str:
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
        scripts = AILessonScript.query.filter(AILessonScript.lesson_id.in_(lesson_ids) == True,AILessonScript.script_content_type==SCRIPT_TYPE_SYSTEM).all()
        if len(scripts)>0:
            for script in scripts:
                if script.lesson_id == lesson_id:
                    return script.script_prompt
            return scripts[0].script_prompt
        return None

def run_script(app: Flask, user_id: str, course_id: str, lesson_id: str=None,input:str=None,input_type:str=None,script_id:str = None)->Generator[ScriptDTO,None,None]:
    with app.app_context():
        course_info = AICourse.query.filter(AICourse.course_id == course_id).first()
        if not course_info:
            course_info = AICourse.query.first()
            course_id = course_info.course_id
        if not lesson_id:
            buy_record = AICourseBuyRecord.query.filter_by(user_id=user_id, course_id=course_id).first() 
            if not buy_record:
                lessons = init_trial_lesson(app, user_id, course_id)
                app.logger.info("user_id:{},course_id:{},lesson_id:{}".format(user_id,course_id,lesson_id))
                attend = get_current_lesson(app,lessons)
                app.logger.info("{}".format(attend))
                lesson_id = attend.lesson_id
        else:
            # 获取课程记录
            app.logger.info("user_id:{},course_id:{},lesson_id:{}".format(user_id,course_id,lesson_id))
            attend_info = AICourseLessonAttend.query.filter_by(user_id=user_id, course_id=course_id,lesson_id=lesson_id).first()
            if not attend_info:
                # 没有课程记录
                for i in "请购买课程":
                    yield make_script_dto("text",i,None)
                    time.sleep(0.01)
                yield make_script_dto("text_end","",None)
                return
            attend = AICourseLessonAttendDTO(attend_info.attend_id,attend_info.lesson_id,attend_info.course_id,attend_info.user_id,attend_info.status,attend_info.script_index)
            db.session.commit()
        # Langfuse 集成 
        # attend = AICourseLessonAttendDTO(attend_info.attend_id,attend_info.lesson_id,attend_info.course_id,attend_info.user_id,attend_info.status)
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
            input_type = None
            next=True
        while True:
            # 如果有用户输入,就得到当前这一条,否则得到下一条
            if script_id and not next:
                script_info = get_script_by_id(app,script_id)
            else:
                script_info,attend_updates = get_script(app,attend_id=attend.attend_id,next=next)
                if len(attend_updates)>0:
                    for attend_update in attend_updates:
                        if len(attend_update.lesson_no) > 2:
                            yield make_script_dto("lesson_update",attend_update.__json__(),"")
                        else:
                            yield make_script_dto("chapter_update",attend_update.__json__(),"") 
            if script_info:
                app.logger.info("begin to run script,lesson_id:{},script_index:{},script_id:{},model:{},input_type:{}".format(script_info.lesson_id,script_info.script_index,script_info.script_id,script_info.script_model,input_type))
                log_script = generation_attend(app,attend,script_info)
                #  检查后续操作是否为手机号和验证码
                #  如果用户已经注册,则跳过
                if script_info.script_ui_type == UI_TYPE_PHONE or script_info.script_ui_type == UI_TYPE_CHECKCODE:
                    user = User.query.filter_by(user_id=user_id).first()
                    if user.user_state > 0:
                        next = True
                        continue
                # 得到脚本
                # 输入校验
                if input_type == INPUT_TYPE_TEXT:
                    prompt = get_fmt_prompt(app,user_id,script_info.script_check_prompt,input,script_info.script_profile)
                    ## todo 换成通用的
                    log_script = generation_attend(app,attend,script_info)
                    log_script.script_content = input
                    log_script.script_role = ROLE_STUDENT 
                    db.session.add(log_script)
                    span = trace.span(name="user_input",input=input)
                    resp = invoke_llm(app,
                                      span,
                        model=script_info.script_model,
                        json=True,
                        stream=True,
                        temperature=0.1,
                        message=prompt)
                    response_text = ""
                    check_success = False
                    stream = False

                    for i in resp:
                        current_content = i.result
                        if isinstance(current_content ,str):
                            response_text += current_content
                    jsonObj = extract_json(app,response_text)
                    check_success = jsonObj.get("result","")=="ok"
                    if check_success:
                        app.logger.info('check success')
                        profile_tosave = jsonObj.get("parse_vars")
                        save_user_profiles(app,user_id,profile_tosave)
                        for key in profile_tosave:
                            yield make_script_dto("profile_update",{"key":key,"value":profile_tosave[key]},script_info.script_id)
                            time.sleep(0.01)
                        input = None
                        next = True
                        input_type = None 
                        span.end()
                        db.session.commit() 
                        continue
                    else:
                        reason = jsonObj.get("reason",response_text)
                        for text in reason:
                            yield make_script_dto("text",text,script_info.script_id)
                            time.sleep(0.01)
                        yield make_script_dto("text_end","",script_info.script_id)
                        log_script = generation_attend(app,attend,script_info)
                        log_script.script_content = response_text
                        log_script.script_role = ROLE_TEACHER
                        db.session.add(log_script)
                        span.end(output=response_text)
                        trace_args ["output"] = trace_args["output"]+"\r\n"+response_text
                        trace.update(**trace_args)
                        db.session.commit()
                        yield make_script_dto("input",script_info.script_ui_content,script_info.script_id) 
                        break
                elif input_type == INPUT_TYPE_CONTINUE:
                    log_script = generation_attend(app,attend,script_info)
                    log_script.script_content = "继续"
                    log_script.script_role = ROLE_STUDENT
                    db.session.add(log_script)
                    span = trace.span(name="user_continue",input=input)
                    span.end()
                    next=True
                elif input_type == INPUT_TYPE_SELECT:
                    profile_keys = get_profile_array(script_info.script_ui_profile)
                    profile_tosave = {}
                    if len(profile_keys) == 0 :
                        btns = json.loads(script_info.script_other_conf)
                        conf_key = btns.get('var_name','input')
                        profile_tosave[conf_key] = input
                        
                    for k in profile_keys:
                        profile_tosave[k]=input
                    save_user_profiles(app,user_id,profile_tosave)
                    log_script = generation_attend(app,attend,script_info)
                    log_script.script_content = input
                    log_script.script_role = ROLE_STUDENT
                    db.session.add(log_script)
                    input = None
                    next = True
                    input_type = None
                    span = trace.span(name="user_select",input=input)
                    span.end()
                    db.session.commit()
                    continue
                elif input_type == INPUT_TYPE_PHONE:
                    log_script = generation_attend(app,attend,script_info)
                    log_script.script_content = input
                    log_script.script_role = ROLE_STUDENT
                    db.session.add(log_script)
                    # input = None
                    input_type =  None 
                    span = trace.span(name="user_input_phone",input=input)
                    response_text ="请输入正确的手机号" 
                    if not check_phone_number(app,user_id,input):
                        for i in response_text:
                            yield make_script_dto("text",i,script_info.script_id)
                            time.sleep(0.01)
                        make_script_dto("text_end","",script_info.script_id)
                        make_script_dto(UI_TYPE_PHONE,script_info.script_ui_content,script_info.script_id) 
                        log_script = generation_attend(app,attend,script_info)
                        log_script.script_content = response_text
                        log_script.script_role = ROLE_TEACHER
                        db.session.add(log_script)
                        span.end(output=response_text)
                        span.end()
                        break
                    span.end()

               


                    next = True
                    continue
                elif  input_type == INPUT_TYPE_CHECKCODE:
                    try:
                        ret = verify_sms_code_without_phone(app,user_id,input)
                        yield make_script_dto("profile_update",{"key":"phone","value":ret.userInfo.mobile},script_info.script_id)
                        yield make_script_dto("user_login",{"phone":ret.userInfo.mobile,"user_id":ret.userInfo.user_id},script_info.script_id)

                    except AppException as e:
                        for i in e.message:
                            yield make_script_dto("text",i,script_info.script_id)
                            time.sleep(0.01)
                        break
                    input = None
                    input_type = None 
                    span = trace.span(name="user_input_phone",input=input)
                    span.end()
                    next = True
                    continue
                elif  input_type == INPUT_TYPE_LOGIN:
                    yield make_script_dto(INPUT_TYPE_LOGIN,{"phone":ret.userInfo.mobile,"user_id":ret.userInfo.user_id},script_info.script_id)
                    break
                elif  input_type == INPUT_TYPE_START:
                    next = True
                else:
                    input_type = None
                # 执行脚本
                input_type = None
                if script_info.script_type == SCRIPT_TYPE_FIX:
                    prompt = ""
                    if script_info.script_content_type == CONTENT_TYPE_IMAGE:
                        prompt = "![img]({})".format(script_info.script_media_url)
                        yield make_script_dto("text",prompt,script_info.script_id)
                    else:
                        prompt = get_fmt_prompt(app,user_id,script_info.script_prompt,profile_array_str=script_info.script_profile)
                        if not prompt:
                            prompt = ""
                        for i in prompt:
                            msg =  make_script_dto("text",i,script_info.script_id)
                            yield msg
                            time.sleep(0.01)
                    log_script = generation_attend(app,attend,script_info)
                    log_script.script_content = prompt
                    log_script.script_role = ROLE_TEACHER
                    db.session.add(log_script)
                    data = ScriptDTO("text_end",script_info.script_id)

                    span = trace.span(name="fix_script")
                    span.end(output=prompt)

                    trace_args ["output"] = trace_args["output"]+"\r\n"+prompt
                    trace.update(**trace_args)
                    msg =  'data: '+json.dumps(data,default=fmt)+'\n\n'
                    app.logger.info(msg)
                    yield msg
                elif script_info.script_type == SCRIPT_TYPE_PORMPT:
                    span = trace.span(name="prompt_sript")
                    system = get_lesson_system(script_info.lesson_id)
                    system_prompt = None if system == None or system == "" else get_fmt_prompt(app,user_id,system)
                    prompt = get_fmt_prompt(app,user_id,script_info.script_prompt,profile_array_str=script_info.script_profile)
                    resp = invoke_llm(app,span,
                        model=script_info.script_model,
                        stream=True,
                        system=system_prompt,
                        temperature=0.1,
                        message=prompt)
                    response_text = ""
                    for chunk in resp:
                        current_content = chunk.result
                        if isinstance(current_content ,str):
                            response_text += current_content
                            yield make_script_dto("text", current_content,script_info.script_id)

                    trace_args ["output"] = trace_args["output"]+"\r\n"+prompt
                    trace.update(**trace_args)
                    log_script = generation_attend(app,attend,script_info)
                    log_script.script_content = response_text
                    log_script.script_role = ROLE_TEACHER
                    db.session.add(log_script)
                    yield make_script_dto("text_end","",script_info.script_id)
                else:
                    next = True
                # 返回下一轮的交互方式
                if script_info.script_ui_type == UI_TYPE_CONTINUED:
                    next = True
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
                elif script_info.script_ui_type == UI_TYPE_BRANCH:
                      # 分支课程
                    app.logger.info("branch")
                    branch_info = json.loads(script_info.script_other_conf)
                    branch_key = branch_info.get("var_name","")
                    profile = get_user_profiles(app,user_id,[branch_key])
                    branch_value = profile.get(branch_key,"")
                    jump_rule = branch_info.get("jump_rule",[])
                    for rule in jump_rule:
                        if branch_value == rule.get("value",""):
                            attend_info = AICourseLessonAttend.query.filter(AICourseLessonAttend.attend_id == attend.attend_id).first()
                            next_lesson = AILesson.query.filter(AILesson.lesson_feishu_id == rule.get("lark_table_id",""), AILesson.status == 1, func.length(AILesson.lesson_no)>2).first()
                            if next_lesson:
                                next_attend = AICourseLessonAttend.query.filter(AICourseLessonAttend.user_id==user_id, AICourseLessonAttend.course_id==course_id,AICourseLessonAttend.lesson_id==next_lesson.lesson_id).first()
                                if next_attend:
                                    assoation =AICourseAttendAsssotion()
                                    assoation.from_attend_id = attend_info.attend_id
                                    assoation.to_attend_id = next_attend.attend_id 
                                    assoation.user_id = user_id
                                    db.session.add(assoation)
                                    next_attend.status = ATTEND_STATUS_IN_PROGRESS
                                    next_attend.script_index =0
                                    attend_info.status = ATTEND_STATUS_BRANCH
                                    db.session.commit()
                                    next = False
                                    attend_info = next_attend
                                         
                    btn = [{
                        "label":script_info.script_ui_content,
                        "value":script_info.script_ui_content
                    }]
                    yield make_script_dto("buttons",{"title":"接下来","buttons":btn},script_info.script_id)
                    break
                elif script_info.script_ui_type == UI_TYPE_SELECTION:
                    yield make_script_dto("buttons",{"title":script_info.script_ui_content,"buttons":json.loads(script_info.script_other_conf)["btns"]},script_info.script_id)
                    break
                elif script_info.script_ui_type == UI_TYPE_PHONE:
                    yield make_script_dto(INPUT_TYPE_PHONE,script_info.script_ui_content,script_info.script_id)
                    break
                elif script_info.script_ui_type == UI_TYPE_CHECKCODE:
                    try:
                        expires = send_sms_code_without_check(app,user_id,input)
                        yield make_script_dto(INPUT_TYPE_CHECKCODE,expires,script_info.script_id)
                        break
                    except AppException as e:
                        for i in e.message:
                            yield make_script_dto("text",i,script_info.script_id)
                            time.sleep(0.01)
                        yield make_script_dto("text_end","",script_info.script_id)
                        break 
                elif script_info.script_ui_type == UI_TYPE_LOGIN:
                    yield make_script_dto(INPUT_TYPE_LOGIN,script_info.script_ui_content,script_info.script_id)

                    # 这里控制暂时是否启用登录
                    next=True
                elif script_info.script_ui_type == UI_TYPE_TO_PAY:
                    order =  init_buy_record(app,user_id,course_id,999)
                    btn = [{
                        "label":script_info.script_ui_content,
                        "value":order.record_id
                    }]
                    yield make_script_dto("order",{"title":"买课！","buttons":btn},script_info.script_id)
                    break
                elif script_info.script_ui_type == UI_TYPE_CONTINUED:
                    next = True
                    input_type= None 
                    continue
                  
                else:
                    break
            else:
                # 更新完课信息
                attend_updates = update_attend_lesson_info(app,attend_id=attend.attend_id)
                # 更新到课信息
                if len (attend_updates) > 0 :
                    for attend_update in attend_updates:
                        if len(attend_update.lesson_no) > 2:
                            yield make_script_dto("lesson_update",attend_update.__json__(),"")
                        else:
                            yield make_script_dto("chapter_update",attend_update.__json__(),"")
                break
        db.session.commit()


def get_lesson_and_attend_info(app:Flask,parent_no,course_id,user_id):
    lessons = AILesson.query.filter(AILesson.lesson_no.like(parent_no+'%'),AILesson.course_id ==course_id,AILesson.lesson_type !=LESSON_TYPE_BRANCH_HIDDEN, AILesson.status==1 ).all()
    if len(lessons)==0:
        return [] 
    attend_infos = AICourseLessonAttend.query.filter(AICourseLessonAttend.lesson_id.in_([lesson.lesson_id for lesson in lessons]),AICourseLessonAttend.user_id == user_id ).all()
    app.logger.info("attends:{}".format(",".join("'"+a.attend_id+"'" for a in attend_infos)))
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
        course_info = AICourse.query.filter(AICourse.course_id == course_id).first()
        if not course_info:
            course_info = AICourse.query.first()
            course_id = course_info.course_id
          # 检查有没有购课记录
        buy_record = AICourseBuyRecord.query.filter_by(user_id=user_id, course_id=course_id).first() 
        if not buy_record:
            app.logger.info('no buy record found')
            # 没有购课记录
            # 生成体验课记录
            init_trial_lesson(app, user_id, course_id)
        lessons = AILesson.query.filter(course_id==course_id,AILesson.lesson_type !=LESSON_TYPE_BRANCH_HIDDEN, AILesson.status==1).all()
        lessons = sorted(lessons, key=lambda x: (len(x.lesson_no), x.lesson_no))
        attend_infos = AICourseLessonAttend.query.filter(AICourseLessonAttend.user_id == user_id,AICourseLessonAttend.course_id == course_id).all()
        attend_infos_map = {i.lesson_id:i for i in attend_infos}
        lessonInfos = []
        lesson_dict = {}
        for lesson in lessons:
            attend_info = attend_infos_map.get(lesson.lesson_id,None)
            if not attend_info:
                continue
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

@register_schema_to_swagger
class StudyRecordItemDTO:
    script_index:int
    script_role:str
    script_type:int
    script_content:str
    lesson_id: str
    id: str
    
    def __init__(self,script_index,script_role,script_type,script_content,lesson_id,id):
        self.script_index = script_index
        self.script_role = script_role
        self.script_type = script_type
        self.script_content = script_content
        self.lesson_id = lesson_id
        self.id = id
    def __json__(self):
        return {
            "script_index": self.script_index,
            "script_role": self.script_role,
            "script_type": self.script_type,
            "script_content": self.script_content,
            "lesson_id":self.lesson_id,
            "id":self.id
        }
    
@register_schema_to_swagger
class StudyUIDTO:
    type: str 
    content: object
    lesson_id:str
    def __init__(self,type,content,lesson_id):
        self.type = type
        self.content = content
        self.lesson_id = lesson_id
    def __json__(self):
        return {
            "type": self.type,
            "content": self.content,
            "lesson_id":self.lesson_id
        }
@register_schema_to_swagger 
class StudyRecordDTO:
    records:List[StudyRecordItemDTO]
    ui:StudyUIDTO
    def __init__(self,records,ui=None):
        self.records = records
        self.ui = ui
    def __json__(self):
        return {
            "records": self.records,
            "ui":self.ui
        }
    



# 获取学习记录

def get_study_record(app:Flask,user_id:str,lesson_id:str)->StudyRecordDTO:
    with app.app_context():

        lesson_info = AILesson.query.filter_by(lesson_id=lesson_id).first()
        lesson_ids = [lesson_id]
        if not lesson_info:
            return None
        if len(lesson_info.lesson_no) <= 2:
            lesson_infos = AILesson.query.filter(AILesson.lesson_no.like(lesson_info.lesson_no+'%')).all()
            lesson_ids = [lesson.lesson_id for lesson in lesson_infos]
        app.logger.info("lesson_ids:{}".format(lesson_ids))
        attend_infos = AICourseLessonAttend.query.filter(AICourseLessonAttend.user_id==user_id,  AICourseLessonAttend.lesson_id.in_(lesson_ids)).order_by(AICourseLessonAttend.id).all()
        if not attend_infos:
            return None
        attend_ids = [attend_info.attend_id for attend_info in attend_infos]
        app.logger.info("attend_ids:{}".format(attend_ids))
        attend_scripts = AICourseLessonAttendScript.query.filter(AICourseLessonAttendScript.attend_id.in_(attend_ids)).order_by(AICourseLessonAttendScript.id).all()
        app.logger.info("attend_scripts:{}".format(len(attend_scripts)))
        if len(attend_scripts) == 0:
            return StudyRecordDTO(None)
        items =  [StudyRecordItemDTO(i.script_index,ROLE_VALUES[i.script_role],0,i.script_content,i.lesson_id,i.id) for i in attend_scripts]
        ret = StudyRecordDTO(items)
        last_script_id = attend_scripts[-1].script_id

        last_script = AILessonScript.query.filter_by(script_id=last_script_id).first()
        app.logger.info("last_script:{}".format(last_script)) 
        if last_script.script_ui_type == UI_TYPE_INPUT:
            ret.ui = StudyUIDTO("input",last_script.script_ui_content,last_script.lesson_id)
        elif last_script.script_ui_type == UI_TYPE_BUTTON:
            btn = [{
                        "label":last_script.script_ui_content,
                        "value":last_script.script_ui_content
                    }]
            ret.ui = StudyUIDTO("buttons",{"title":"接下来","buttons":btn},last_script.lesson_id)
        elif last_script.script_ui_type == UI_TYPE_CONTINUED:
            ret.ui = StudyUIDTO("buttons",{"title":"继续","buttons":[{"label":"继续","value":"继续"}]},last_script.lesson_id)
        elif last_script.script_ui_type == UI_TYPE_SELECTION:
            ret.ui = StudyUIDTO("buttons",{"title":last_script.script_ui_content,"buttons":json.loads(last_script.script_other_conf)["btns"]},last_script.lesson_id)
        elif last_script.script_ui_type == UI_TYPE_PHONE:
            ret.ui = StudyUIDTO(INPUT_TYPE_PHONE,last_script.script_ui_content,last_script.lesson_id)
        elif last_script.script_ui_type == UI_TYPE_CHECKCODE:
            expires = get_sms_code_info(app,user_id,False)
            ret.ui = StudyUIDTO(INPUT_TYPE_CHECKCODE,expires,last_script.lesson_id)
        elif last_script.script_ui_type == UI_TYPE_LOGIN:
            ret.ui = StudyUIDTO(INPUT_TYPE_LOGIN,last_script.script_ui_content,last_script.lesson_id)
        elif last_script.script_ui_type == UI_TYPE_TO_PAY:
            order =  init_buy_record(app,user_id,lesson_info.course_id,999)
            btn = [{
                        "label":last_script.script_ui_content,
                        "value":order.record_id
                    }]
            ret.ui = StudyUIDTO("order",{"title":"买课！","buttons":btn},last_script.lesson_id)
            # ret.ui = StudyUIDTO("buttons",{"title":"继续","buttons":[{"label":"继续","value":"继续"}]},last_script.lesson_id)
        
        return ret
# 重置用户信息
# 重置用户学习信息
def reset_user_study_info(app:Flask,user_id:str):
    with app.app_context():
        db.session.execute(text("delete from ai_course_buy_record where user_id = :user_id"),{"user_id":user_id})
        db.session.execute(text("delete from ai_course_lesson_attend where user_id = :user_id"),{"user_id":user_id})
        db.session.execute(text("delete from ai_course_lesson_attendscript where user_id = :user_id"),{"user_id":user_id})
        db.session.execute(text("delete from ai_course_lesson_generation where user_id = :user_id"),{"user_id":user_id})
        db.session.execute(text("delete from user_profile where user_id = :user_id"),{"user_id":user_id})
        db.session.commit()
        return True