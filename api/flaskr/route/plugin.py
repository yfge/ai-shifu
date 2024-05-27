from flask import Flask, request, Response,g

def register_test_plug(app:Flask,path_prefix:str)->Flask:
    @app.route(path_prefix+'/test', methods=['GET'])
    def test():
        
        return Response('test', mimetype="text/event-stream")
    return app