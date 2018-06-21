import logger as log
from utils.table_utils import Table
from utils.settings import *
from utils.settings import MACHINE
from utils.vision_utils import VisionUtils
from utils.roi_utils import RoiUtils
from utils.settings import *

if MACHINE == "EC2":
    from utils.pdf_utils_ubuntu import PdfUtilsUbuntu
    pdf = PdfUtilsUbuntu()
else:
    from utils.pdf_utils_win import PdfUtilsWin
    pdf = PdfUtilsWin()


vis = VisionUtils(debug=False)
tab = Table(debug=False)
roi = RoiUtils(debug=False)


def ocr_proc(src_file, debug=False):

    if not os.path.exists(src_file):
        err_msg = "no exist such file!"
        log.log_print("\t {}, {}\n".format(err_msg, src_file))
        return err_msg

    # ------------------ convert pdf to page images ----------------------------------------------------
    log.log_print("\n\t>>> {}".format(src_file))
    page_img_paths = []
    if os.path.splitext(src_file)[1].upper() == ".PDF":
        log.log_print("\tpdf to imgs...")
        page_img_paths = pdf.doc2imgs(doc_path=src_file)

    elif os.path.splitext(src_file)[1].upper() in [".JPG", ".PNG"]:
        page_img_paths = [src_file]

    if len(page_img_paths) == 0:
        err_msg = "not readable pdf format"
        log.log_print("\t" + err_msg + "\n")
        return err_msg

    # ------------------ extract the roi (table_areas) -------------------------------------------------
    pages = []
    for path in page_img_paths:
        img = cv2.imread(path)
        if img is None:
            continue
        boxes, new_img = roi.identify_table_area(page_img=img)
        if len(boxes) == 0:
            continue

        crops = []
        for box in boxes:
            [x1, y1, x2, y2] = box
            crop_img = new_img[y1:y2, x1:x2]
            crops.append({
                "crop_img": crop_img,
                "box": box
            })
        pages.append({
            "id": page_img_paths.index(path),
            "page_img": img,
            "crops": crops
        })

    if len(pages) == 0:
        err_msg = "no containing tables!"
        log.log_print("\t" + err_msg + "\n")
        return err_msg

    # ------------------ images to pdf -----------------------------------------------------------------
    log.log_print("\tgoogle vision api...")
    page_contents_queue = qu.Queue()
    threads = []
    while page_contents_queue.qsize() == 0:
        # start the multi requests
        for page_idx in range(len(pages)):
            page = pages[page_idx]
            if debug:
                log.log_print("\tpage No: {}".format(page["id"] + 1))

            crops = page["crops"]
            for i in range(len(crops)):
                crop = crops[i]
                box_idx = i
                crop_img = crop["crop_img"]
                if crop_img is None:
                    continue

                thread = thr.Thread(target=vis.detect_text, args=(crop_img, page_idx, box_idx, page_contents_queue))
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

    if len(contents) == 0:
        err_msg = "not contain candidate table"
        log.log_print("\t" + err_msg + "\n")
        return err_msg

    # ------------------ parsing and the invoice information ---------------------------------------------
    """
        'page_idx': page_idx,
        'box_idx': box_idx,
        'annos': annos,
        'label': 'text',
        'orientation': orientation,
        'image': img,
        'total_text': annotations[0]['description']
    """
    contents = sorted(contents, key=lambda k: k['page_id'])

    log.log_print("\t # candi contents: {}".format(len(contents)))
    for i in range(len(contents)):
        content = contents[i]
        content = content
        cv2.imwrite(LOG_DIR + "crops_" + str(i) + ".jpg", content['image'])
    # for content in contents:
    #     img = content['image']
    #     cv2.imshow("show", img)
    #     cv2.waitKey(0)

    res = tab.parse_table(contents=contents)
    return res


def save_temp_images(content):
    cv2.imwrite("{}temp_{}.jpg".format(LOG_DIR, content['id'] + 1), content['image'])


if __name__ == '__main__':
    path = "D:/workspace/tesseract_pdf_parse/data/example_pdf/COM_5.pdf"
    ocr_proc(path)
