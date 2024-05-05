"""
 @file response.py
 @author Lee A. Congdon (lee@silversat.org)
 @author Benjamin S. Cohen (ben@silversat.org)
 @brief SilverSat User and radio Doppler interface
 @version 1.0.0
 @date 2024-04-30
 
 This program provides the interface for satellite responses
 
"""

import functools

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ground_software.database import get_database

blueprint = Blueprint("response", __name__, url_prefix="/response")

from flask import Flask, render_template, request
import datetime
from ground_software.database import get_database


# Responses from satellite


# todo: implement update_responses reading responses from database
@blueprint.post("/response")
def update_responses():
    return {"Responses"}
