


from flaskr.service.study.const import ROLE_STUDENT


def input_phone(app,attend,script_info,user_id,input,trace:TraceContext):
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
        yield make_script_dto("text_end","",script_info.script_id)
        yield make_script_dto(UI_TYPE_PHONE,script_info.script_ui_content,script_info.script_id) 
        log_script = generation_attend(app,attend,script_info)
        log_script.script_content = response_text
        log_script.script_role = ROLE_TEACHER
        db.session.add(log_script)
        span.end(output=response_text)
        span.end()
        break
    span.end()