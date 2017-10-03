#encoding: utf-8

import json

from hollowman.log import logger


class ForcePullFilter():

    name = 'pull'

    def run(self, ctx):
        request = ctx.request
        if request.is_json and request.data:
            data = request.get_json()

            if self.is_single_app(data):
                original_app_dict = json.loads(self.get_original_app(ctx).to_json())
                original_app_dict.update(data)

                if self.is_docker_app(original_app_dict):
                    original_app_dict['container']['docker']["forcePullImage"] = True

                request.data = json.dumps(original_app_dict)

        return request

    def write(sef, user, request_app, app):
        try:
            request_app.container.docker.force_pull_image = True
            logger.info("Forcing pull image of app {}".format(request_app.id))
        except AttributeError as e:
            pass
        return request_app

