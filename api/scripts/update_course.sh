HOST="http://127.0.0.1:5800"



declare -A COURSE
COURSE["tblk9OFSKLeUPunv"]="开篇"
COURSE["tblPI00k8B14kD5m"]="AI编程初体验"
COURSE["tbl7G4WqBtv6hycy"]="借助AI读懂代码"
COURSE["tblFrdiqdXzebDZa"]="判断代码的质量"
COURSE["tbl93C7esgLzrtNT"]="用AI做代码调试"
COURSE["tbl9MytJGjsfvhvT"]="用AI调整代码"
# COURSE["tblk9OFSKLeUPunv"]="开篇"

# curl "$HOST/api/lesson/update_lesson?doc_id=LLwmbSyMcakFVJsM5yacT5Gqnse&table_id=tbl1t3JItMgbitAB&title=试学&index=0&lesson_type=401"
# curl "$HOST/api/lesson/update_lesson?doc_id=LLwmbSyMcakFVJsM5yacT5Gqnse&table_id=tbl1t3JItMgbitAB&title=试学&index=0&lesson_type=401"

for key in "${!COURSE[@]}"; do
    echo "$key: ${COURSE[$key]}"
done