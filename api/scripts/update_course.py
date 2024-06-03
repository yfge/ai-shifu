import requests

COURSE = {}
COURSE["tblk9OFSKLeUPunv"]="开篇"
COURSE["tblPI00k8B14kD5m"]="AI编程初体验"
COURSE["tbl7G4WqBtv6hycy"]="借助AI读懂代码"
COURSE["tblFrdiqdXzebDZa"]="判断代码的质量"
COURSE["tbl93C7esgLzrtNT"]="用AI做代码调试"
COURSE["tbl9MytJGjsfvhvT"]="用AI调整代码"

HOST="http://127.0.0.1:5800"


i = 0 
for k in COURSE.keys():
    print(k)
    print(COURSE.get(k))
    name= COURSE.get(k)
    url = '''{}/api/lesson/update_lesson?doc_id=LLwmbSyMcakFVJsM5yacT5Gqnse&table_id={}&title={}&index={}&lesson_type=401'''.format(HOST,k,name,i)
    i = i + 1 
    print(url)
    print(requests.get(url=url).json())
