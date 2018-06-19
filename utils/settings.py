import os
import cv2
import sys
import json
import base64
import requests
import queue as qu
import numpy as np
import threading as thr
# api key
API_KEY = 'AIzaSyC_X5oZ5WdKAru6AGNrggNyMZNgs_w5elI'

# endpoints
ORIENTATION_270_DEGREE = 0
ORIENTATION_180_DEGREE = 1
ORIENTATION_90_DEGREE = 2
ORIENTATION_NORMAL = 3

ROTATE_90_CLOCKWISE = 0
ROTATE_180 = 1
ROTATE_90_COUNTERCLOCKWISE = 2


MAXIMUM_SIZE = 2.5 * 1024 * 1024  # google could api limitation 4 MB

ALLOWED_EXT = [".pdf", ".jpg"]

# predefined the location for saving the uploaded files
UPLOAD_DIR = 'data/'

# endpoints
LOG_DIR = "./logs/"
ORIENTATIONS = ["270 Deg", "180 Deg", "90 Deg", "0 Deg(Normal)"]

MACHINE = "EC2"  # which is for the pdf manager


TITLE = "LIGHTING FIXTURE SCHEDULE"

try:
    from utils.settings_local import *
except Exception:
    pass
