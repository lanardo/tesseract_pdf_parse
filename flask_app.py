import base64
import json
import os

from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from utils.settings import *

import endpoints
import logger as log

app = Flask(__name__)

# predefined the location for saving the uploaded files
cur = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(cur, 'data')


def allowed_file(filename):
    return os.path.splitext(filename)[-1].lower() in ALLOWED_EXT


@app.route('/')
def ocr():
    """
        initial rendering of the web interface
    """
    return render_template('table.html')


@app.route('/submit', methods=['POST'])
def submit():
    if len(request.files) > 0:
        file = request.files['file']
        doc_fn = secure_filename(file.filename)

        if not (file and allowed_file(file.filename)):
            str = "\tnot allowed file format {}.".format(doc_fn)
            log.log_print(str)
            return str
        try:
            # upload the file to the server -------------------------------------------------------
            log.log_print("\t>>>uploading invoice {}".format(file.filename))

            # check its directory for uploading the requested file --------------------------------
            if not os.path.isdir(UPLOAD_DIR):
                os.mkdir(UPLOAD_DIR)

            # remove all the previous processed document file -------------------------------------
            for fname in os.listdir(UPLOAD_DIR):
                path = os.path.join(UPLOAD_DIR, fname)
                if os.path.isfile(path):
                    os.remove(path)

            # save the uploaded document on UPLOAD_DIR --------------------------------------------
            file.save(os.path.join(UPLOAD_DIR, doc_fn))

            # ocr progress with the uploaded files ------------------------------------------------
            src_fpath = os.path.join(UPLOAD_DIR, doc_fn)
            ressult = endpoints.ocr_proc(src_file=src_fpath)
            log.log_print("\n>>>finished")

            return jsonify(ressult)

        except Exception as e:
            error_str = '\tException: {}'.format(e)
            log.log_print("\t exception :" + error_str)
            return error_str


if __name__ == '__main__':
    # open the port 5000 to connect betweeen client and server
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
        threaded=True,
    )
