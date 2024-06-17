import requests

COURSE = {}
COURSE["tblk9OFSKLeUPunv"]=["开篇","vewlGkI2Jp"]#tblk9OFSKLeUPunv
COURSE["tblPI00k8B14kD5m"]=["AI编程初体验","vewlGkI2Jp"]
COURSE["tbl7G4WqBtv6hycy"]=["借助AI读懂代码","vewlGkI2Jp"]
COURSE["tblFrdiqdXzebDZa"]=["判断代码的质量","vewlGkI2Jp"]
COURSE["tbl93C7esgLzrtNT"]=["用AI做代码调试","vewlGkI2Jp"]
COURSE["tbl9MytJGjsfvhvT"]=["用AI调整代码","vewlGkI2Jp"]

HOST="http://127.0.0.1:5800"
HOST="https://test-api-sifu.agiclass.cn/"


i = 0 
for k in COURSE.keys():
    print(k)
    print(COURSE.get(k))
    name= COURSE.get(k)
    url = '''{}/api/lesson/update_lesson?doc_id=LLwmbSyMcakFVJsM5yacT5Gqnse&table_id={}&view_id={}&title={}&index={}&lesson_type=401'''.format(HOST,k,name[1],name[0],i)
    i = i + 1 
    print(url)
    print(requests.get(url=url).json())
