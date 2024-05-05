"""
 @file __init__.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief SilverSat User and radio Doppler interface
 @version 1.0.1
 @date 2023-12-15
 
 This package provides the user interface for the ground station
 
"""

import os
from flask import Flask


def create_app(test_config=None):
    application = Flask(__name__, instance_relative_config=True)
    application.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(application.instance_path, "radio.db"),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        application.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        application.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(application.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @application.route("/hello")
    def hello():
        return "Hello, World!"

    from . import database
    database.init_app(application)

    from . import control
    application.register_blueprint(control.blueprint)
    application.add_url_rule("/", endpoint="index")

    from . import response
    application.register_blueprint(response.blueprint)

    return application
