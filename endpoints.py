
import os
import queue as qu
import sys
import threading as thr

import cv2

import logger as log
from utils.table_utils import Table
from utils.settings import *
from utils.settings import MACHINE
from utils.vision_utils import VisionUtils
if MACHINE == "EC2":
    from utils.pdf_utils_ubuntu import PdfUtilsUbuntu
    pdf = PdfUtilsUbuntu()
else:
    from utils.pdf_utils_win import PdfUtilsWin
    pdf = PdfUtilsWin()


vis = VisionUtils(debug=False)
tab = Table(debug=False)


def ocr_proc(src_file, debug=False):

    if not os.path.exists(src_file):
        log.log_print("\t no exist such file! {}\n".format(src_file))
        sys.exit(1)

    # ------------------ convert pdf to page images ----------------------------------------------------
    log.log_print("\n\t>>> {}".format(src_file))

    if os.path.splitext(src_file)[1].upper() == ".PDF":
        log.log_print("\tpdf to imgs...")
        page_img_paths = pdf.doc2imgs(doc_path=src_file)

    elif os.path.splitext(src_file)[1].upper() in [".JPG", ".PNG"]:
        page_img_paths = [src_file]

    # ------------------ imges to pdf ------------------------------------------------------------------
    log.log_print("\tgoogle vision api...")
    page_contents_queue = qu.Queue()
    threads = []
    while page_contents_queue.qsize() == 0:
        # start the multi requests
        for path in page_img_paths:
            if debug:
                log.log_print("\tpage No: {}".format(page_img_paths.index(path) + 1))
            # detect the text from the image
            idx = page_img_paths.index(path)
            thread = thr.Thread(target=vis.detect_text, args=(path, idx, page_contents_queue))
            threads.append(thread)
            thread.start()
        # join
        for thread in threads:
            if thread is not None and thread.isAlive():
                thread.join()

        if page_contents_queue.qsize() == 0:
            log.log_print("response error. resend the request...")
            break

    # ------------------ parsing the invoice  -------------------------------------------------------------
    log.log_print("\t # contents: {}".format(page_contents_queue.qsize()))
    contents = []
    while page_contents_queue.qsize() > 0:
        content = page_contents_queue.get(True, 1)
        if content is None:
            continue

        if tab.candidate(content):
            contents.append(content)

    # ------------------ parsing and the invoice information ---------------------------------------------
    if len(contents) == 0:
        err_msg = "not candidate document"
        log.log_print(err_msg)
        return err_msg

    contents = sorted(contents, key=lambda k: k['id'])

    result_dict = tab.parse_table(contents=contents)
    print(result_dict)
    return result_dict


def save_temp_images(content):
    # log.log_print("\t page No     : {}".format(content['id']))
    # log.log_print("\t\t page label  : {}".format(content['label']))
    # log.log_print("\t\t orientation : {}".format(ORIENTATIONS[content['orientation']]))
    # log.log_print("\t\t len of annos: {}".format(len(content['annos'])))
    # log.log_print("\t\t image size  : {} x {}".format(content['image'].shape[1], content['image'].shape[0]))
    cv2.imwrite("{}temp_{}.jpg".format(LOG_DIR, content['id'] + 1), content['image'])


if __name__ == '__main__':

    path = "D:/workspace/tesseract_pdf_parse/data/COM_1-1.jpg"
    ocr_proc(path)