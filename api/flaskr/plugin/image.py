import os
import re
import openai
from flask import Flask
import json
import oss2
import uuid
import requests
from PIL import Image
from ..service.img import add_image
endpoint = 'https://oss-cn-beijing.aliyuncs.com' # Suppose that your bucket is in the Hangzhou region.




# 为降低 AccessKey 泄露的风险，自 2023 年 7 月 5 日起，新建的主账号 AccessKey 只在创建时提供 Secret，后续不可再进行查询，请保存好Secret。
# AccessKey ID
# LTAI5t6oFQF4jg2uvwcAbgCJ

# AccessKey Secret
# 4p63cRGRBUevNCitEmvcrELCpr8grX


## LTAI5t7QqfjkP5ATgEWyUmAt
 #vYPkZ9bPpwpsYKOjCdOHsDaSchhCTZ
 # oss-cn-beijing.aliyuncs.com
base = "https://assistant-pic.oss-cn-beijing.aliyuncs.com"
auth = oss2.Auth('LTAI5t6oFQF4jg2uvwcAbgCJ', '4p63cRGRBUevNCitEmvcrELCpr8grX')
bucket = oss2.Bucket(auth, endpoint, 'assistant-pic')

# The object key in the bucket is story.txt


promptFormat = f"""
As a professional specializing in AI-powered image synthesis, your role is to meticulously craft user inputs into comprehensive prompts that DALL-E 3 can interpret with high fidelity. Adhere to the following structured principles to ensure optimal results:
1.Explicit Detailing: Infuse the input with elaborate and vivid details that capture the essence of subjects, landscapes, and interactions within the image framework.
2.Unambiguous Definitions: Clearly demarcate all elements in the prompt, from focal objects to ancillary scenery, ensuring precision and clarity.
3.Contextual Accuracy: Embed detailed context to accurately depict the scene’s setting, considering temporal, spatial, and stylistic dimensions.
4.Defined Perspective: Specify the visual perspective, including the angle and orientation, and articulate the structural composition, such as symmetry or rule of thirds.
5.Color Palette and Illumination: Designate a specific color palette and describe the lighting conditions, considering directionality, quality, and ambiance.
6.Aesthetic and Tone: Select an artistic aesthetic, ranging from photorealism to abstract art, and set the emotional tone, capturing the mood precisely.
7.Concise Language: Utilize concise and targeted language to convey the prompt’s requirements, avoiding redundant or vague descriptors.
8.Compliance with Guidelines: Ensure all prompts are in strict adherence to intellectual property rights and content policy standards, avoiding any potentially sensitive or infringing content.
9.Output Format:Return the optimized prompts as a JSON array of strings without internal line breaks.
10. Example_output: [
    "Detailed prompt 1 based on user input following the specified principles.",
    "Detailed prompt 2 based on user input following the specified principles.",
    "Detailed prompt 3 based on user input following the specified principles.",
    "Detailed prompt 4 based on user input following the specified principles."
  ].

  In line with these principles, meticulously formulate the user input: 

  
"""
client = openai.Client(api_key="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",base_url="https://openai-api.kattgatt.com/v1")
# 检查tmp目录，如果不存在则创建
if not os.path.exists("./tmp"):
    os.mkdir("./tmp")

def invokeChat(model:str,prompt:str):
    response = client.chat.completions.create(
        model=model,
        messages=[{"content":prompt,"role":"user"}],
        temperature=0,

    )
    return response.choices[0].message.content

def generate_image(app:Flask, user_id, prompt,chat_id=None):

    # prompt = invokeChat("gpt-4-1106-preview",promptFormat+prompt)

   

    app.logger.info("生成图片的prompt:{}".format(prompt))
    # prompts = json.loads(prompt)
    # app.logger.info("生成图片的prompt:{}".format(prompts[0]))
    resp = client.images.generate(
       model="dall-e-3",
       n = 1,
       size = '1792x1024',
       response_format = 'url',
       prompt = prompt,
       quality="hd"
    )

    url = resp.data[0].url
    app.logger.info("优化的prompt:{}".format(resp.data[0].revised_prompt))
    imagId = str(uuid.uuid4()).replace("-","")
    input = requests.get(url)
    fileName = "./tmp/{}.png".format(imagId)
    with open(fileName, 'wb') as f:
        f.write(input.content)
    app.logger.info("获取图片url:{}".format(url))
    # 下载图片

    ret = bucket.put_object_from_file(imagId+".png", fileName)
   
    app.logger.info("上传图片到oss,返回结果:{}".format(ret))

    delete = os.remove(fileName)
    

    add_image(app, imagId, chat_id, user_id, "kt-ai-assistant", prompt, '1792x1024', base + "/" + imagId+".png", base)

    return base + "/" + imagId+".png"
    # 得到跳转后的url 

def edit_image(app:Flask,user_id,prompt,url,chat_id=None):

    app.logger.info("获取图片url:{}".format(url))
    filename=re.search(r'/([^/]+)$', url).group(1)
    input = requests.get(url)
    originFileName = "./tmp/{}".format(filename)
    with open(originFileName, 'wb') as f:
        f.write(input.content)
    # 下载图片

    updateFileName = "./tmp/{}".format(filename)

    app.logger.info("下载图片到本地:{}".format(updateFileName))
    img = Image.open(originFileName)
    if img.mode not in ["RGBA", "L", "LA"]:
            rgba_image = img.convert("RGBA")
            rgba_image.save(updateFileName)

    Image.new('RGBA', (1024, 1024), (0, 0, 0, 0)).save('./mask.png')
    resp = openai.Image.create_edit(
         n = 1,
            size = '1024x1024',
            response_format = 'url',
            prompt = prompt,
            image = open(updateFileName, 'rb'),
            mask= open('./mask.png', 'rb')
    )
    url = resp['data'][0]['url']
    imagId = str(uuid.uuid4()).replace("-","")
    fileName = "./tmp/{}.png".format(imagId)
    input = requests.get(url)
    with open(fileName, 'wb') as f:
        f.write(input.content)

    ret = bucket.put_object_from_file(imagId+".png", fileName)
    delete = os.remove(fileName)
    return base + "/" + imagId+".png"






def enable_image(ret):
    ret.append({
        "name":"generate_image",
        "description":"generate image from prompt using openai,the result is a url and shoud be displayed in markdown,with img[alt](url)] ,attention:the url should be full url ",
        "parameters":{
            "type":"object",
            "properties":{
                "prompt":{
                "description":"the prompt to generate image,should be optimized for image generation ,and be translated in English",
                "type":"string"
            }
            },
            "required":["prompt"]
        },
        "func":generate_image,
        "msg":"生成图片"
    })
         

