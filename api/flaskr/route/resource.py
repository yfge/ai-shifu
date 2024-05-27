from flask import Flask, send_from_directory

def register_resource_route(app:Flask,path_prefix:str)->Flask:
 # 下截文件地址
    @app.route(path_prefix+'/download/<path:filename>', methods=['GET', 'POST'])
    def download(filename):
        app.logger.info("download file:{}".format(filename))
        return send_from_directory("/Users/geyunfei/dev/kattgatt/gpt_plugin/smart-home-plugins/", filename, as_attachment=True)
    return app
