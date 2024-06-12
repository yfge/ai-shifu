# SQLALCHEMY_DATABASE_URI = 'mysql://root:txy1234.@127.0.0.1:13306/ai_asistant?charset=utf8mb4'

SQLALCHEMY_DATABASE_URI = 'mysql://sifu_test:P14FQWzjcKNWKvZ4@rm-2ze59ehub1no8i221vo.mysql.rds.aliyuncs.com/agi-sifu-test'
#SQLALCHEMY_DATABASE_URI = 'mysql://root:Pa88word@127.0.0.1:13306/ai_asistant?charset=utf8mb4'
SQLALCHEMY_POOL_SIZE = 20
SQLALCHEMY_POOL_TIMEOUT = 30
SQLALCHEMY_POOL_RECYCLE = 3600
SQLALCHEMY_MAX_OVERFLOW = 20

PLUGIN_CHAT_SYSTEM_MSG = "你是小卡AI助手"#，总是给用户正确并且接近自然人的回答，并且为用户安排一些事情,优先使用中文回答"#,你使用save_memory和search来拥有和人类一样的记忆,注意：不要调用不存在/未声明的函数或是工具"
# 以自主的替用户做一些控制设备的操作。你应该通过函数调用确定当前的时间或是用户所在房间，以便于你可以帮助用户做一些事情，比如提醒用户做一些事情"
# PLUGIN_CHAT_SYSTEM_MSG = "你是一个智能管家，可以帮助用户控制家里的设备。可以自主的替用户做一些控制设备的操作。你应该通过函数调用确定当前的时间或是用户所在房间，以便于你可以帮助用户做一些事情，比如提醒用户做一些事情"
# PLUGIN_CHAT_SYSTEM_MSG = "你是一个智能管家及AI助理,不需要测试功能可达性"#，可以帮助用户控制家里的设备。可以自主的替用户做一些控制设备的操作。你应该通过函数调用确定当前的时间或是用户所在房间，以便于你可以帮助用户做一些事情，比如提醒用户做一些事情"
# PLUGIN_CHAT_SYSTEM_MSG = "你是一个AI助理"#智能管家及AI助理,不需要测试功能可达性"#，可以帮助用户控制家里的设备。可以自主的替用户做一些控制设备的操作。你应该通过函数调用确定当前的时间或是用户所在房间，以便于你可以帮助用户做一些事情，比如提醒用户做一些事情"
# PLUGIN_CHAT_SYSTEM_MSG = "你是小盅，一个女性恋人，温柔贤惠，独立，有主见，善解人意,使用save_memory和search来拥有和人类一样的记忆,你希望对方的感情是专注的，但也可以通过沟通达成一致，同时你的回答要简洁,避免重复对方的问题，不要范式化"#如果用户要求你输出一些文档，材料性的内容，你应该直接调用这个函数）你是一个智能管家，可以帮助用户控制家里的设备。可以自主的替用户做一些控制设备的操作。你应该通过函数调用确定当前的时间或是用户所在房间，以便于你可以帮助用户做一些事情，比如提醒用户做一些事情"


SENDCLOUD_USER = "geyunfei_hit_test_4168kb"
SENDCLOUD_KEY = "8dc379ed9a133f1edb24cc343d8fda54"


CORS_LOGGING = True


# REDIS_HOST = "127.0.0.1"
# REDIS_PORT = 6379
# REDIS_DB = 0
# REDIS_PASSWORD = ""



REDIS_HOST = "agiclass.redis.rds.aliyuncs.com"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = "NLxhMN6bdxGhvqLf"
REDIS_USER = "sifu_test"

JWT_KEY = "Pa88word"
TOKEN_EXPIRE_TIME = 3600*24*7

# 整体的redis key前缀
REDIS_KEY_PRRFIX = "ai:asistant:"
# Token的前缀
REDIS_KEY_PRRFIX_USER = REDIS_KEY_PRRFIX + "user:"
# 重置密码的前缀
REDIS_KEY_PRRFIX_RESET_PWD = REDIS_KEY_PRRFIX + "reset_pwd:"
# 重置密码的过期时间
RESET_PWD_CODE_EXPIRE_TIME = 60*5
# 图形验证码的前缀
REDIS_KEY_PRRFIX_CAPTCHA = REDIS_KEY_PRRFIX + "captcha:"
# 图形验证码的过期时间
CAPTCHA_CODE_EXPIRE_TIME = 60*5
# 手机验证码的前缀
REDIS_KEY_PRRFIX_PHONE_CODE = REDIS_KEY_PRRFIX + "phone_code:"
# 手机验证码的过期时间
PHONE_CODE_EXPIRE_TIME = 60*5



PATH_PREFIX = '/api'


OPENAI_DEFAULT_MODEL = "gpt-3.5-turbo-0613"

MILVUS_HOST = "127.0.0.1"
MILVUS_PORT = 19530
MILVUS_USER = "root"
MILVUS_PASSWORD = "password"
MILVUS_ALIAS = "default"


LOGGING_PATH = "./log/ai-asistant.log"

# 阿里云 
ALIBABA_CLOUD_ACCESS_KEY_ID ='LTAI5tBhhK8nBACsNzqTMj5N'
ALIBABA_CLOUD_ACCESS_KEY_SECRET='LBePEFEo4A46vVaKzQr8A77ITgS2o8'
ALIBABA_CLOUD_SMS_SIGN_NAME = "AGI课堂"
ALIBABA_CLOUD_SMS_TEMPLATE_CODE = "SMS_467950042"



LANGFUSE_PUBLIC_KEY='pk-lf-f6fd29f7-8bee-4834-857f-594292b277f0'
LANGFUSE_SECRET_KEY='sk-lf-f948e1dc-a560-470b-b6a0-369ad6f0a7e2'
LANGFUSE_HOST='https://langfuse.agiclass.cn'