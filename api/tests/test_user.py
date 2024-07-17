import pytest
import json

from tests.common import print_json
def test_get_user_profile(app):


    from flaskr.service.profile.funcs import get_user_profile_labels

    resp =  get_user_profile_labels(app,"49037a81b0a54ac8a9c823bbec23f0e3")
    print_json(resp)
    