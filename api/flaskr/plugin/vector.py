
from flask import Flask
from ..service.vector import search_text,save_text_to_collection,getUserCollection


def search(app:Flask,user_id,chat_id,text):
    return search_text(app,user_id,text)
def save_memory(app:Flask,user_id,chat_id,text):
    return save_text_to_collection(app,user_id,chat_id,"assistant",text)

def enable_search(functions):
    functions.append(
         {
            "func": search,
            "name": "search_memory",
            "msg": "回忆",
            "description": "Allows the model to search its 'memory' and retrieve information previously provided by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text":{
                        "type":"string",
                        "description": "Text criteria for the model to search within its 'memory'."
                    },
                  
                },
                "required": ["text"]
            }

        })
    functions.append(
        {
            "func": save_memory,
            "name": "save_memory",
            "msg": "记忆",
            "description": "save the memory to remember info from the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "text":{
                        "type":"string",
                        "description": "Information the model should 'remember' for future interactions."
                    },
                },
                "required": ["text"]
            }
        });