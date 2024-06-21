import requests

COURSE = {}
# COURSE["tblk9OFSKLeUPunv"]=["开篇","vewlGkI2Jp"]#tblk9OFSKLeUPunv
COURSE["tbl41CFTMha7pU1d"]=["测试开篇","vewlGkI2Jp",401]#tblk9OFSKLeUPunv
COURSE["tblPI00k8B14kD5m"]=["AI编程初体验","vewlGkI2Jp",402]
COURSE["tbl7G4WqBtv6hycy"]=["借助AI读懂代码","vewlGkI2Jp",402]
COURSE["tblFrdiqdXzebDZa"]=["判断代码的质量","vewlGkI2Jp",402]
COURSE["tbl93C7esgLzrtNT"]=["用AI做代码调试","vewlGkI2Jp",402]
COURSE["tbl9MytJGjsfvhvT"]=["用AI调整代码","vewlGkI2Jp",402]

HOST="http://127.0.0.1:5800"
# HOST="https://test-api-sifu.agiclass.cn/"


# lesson_type 定义

# 401 课程

# LESSON_TYPE_TRIAL=401
# LESSON_TYPE_NORMAL=402
# LESSON_TYPE_EXTEND=403
# LESSON_TYPE_BRANCH=404
# LESSON_TYPE_BRANCH_HIDDEN=405
# LESSON_TYPES = {
#     "试用课":LESSON_TYPE_TRIAL,
#     "正式课":LESSON_TYPE_NORMAL,
#     "延展课":LESSON_TYPE_EXTEND,
#     "分支课":LESSON_TYPE_BRANCH,
#     "隐藏分支课":LESSON_TYPE_BRANCH_HIDDEN
# }


i = 0 
for k in COURSE.keys():
    print(k)
    print(COURSE.get(k))
    name= COURSE.get(k)
    url = '''{}/api/lesson/update_lesson?doc_id=LLwmbSyMcakFVJsM5yacT5Gqnse&table_id={}&view_id={}&title={}&index={}&lesson_type={}'''.format(HOST,k,name[1],name[0],i,name[2])
    i = i + 1 
    print(url)
    print(requests.get(url=url).json())
