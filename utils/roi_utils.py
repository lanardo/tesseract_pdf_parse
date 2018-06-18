import cv2
import numpy as np


class ROI:
    def __init__(self, debug):
        self.debug = debug
        self.tar_width = 1000
        self.overlapThresh = 0.0001

    def identifi_table_area(self, img):
        # --------------------------------- convert to the gray ----------------------------------
        if len(img.shape) == 3 and img.shape[2] != 1:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        img_h, img_w = gray.shape[:2]
        if self.tar_width == -1:
            tar_width, tar_height = img_w, img_h
        else:
            tar_width, tar_height = self.tar_width, int(img_h * self.tar_width / img_w)

        resize = cv2.resize(gray, (tar_width, tar_height))

        thresh = cv2.adaptiveThreshold(resize, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 1)
        if self.debug:
            cv2.imwrite("thresh.jpg", thresh)

        # --------------------------------- horizon and vertical line detection -------------------
        horizontal = thresh.copy()
        h_sz = int(tar_width / 30)
        h_element = cv2.getStructuringElement(cv2.MORPH_RECT, (h_sz, 1))
        horizontal = cv2.erode(horizontal, h_element, (-1, -1))
        horizontal = cv2.dilate(horizontal, h_element, (-1, -1))
        if self.debug:
            cv2.imwrite("horizontal.jpg", horizontal)

        vertical = thresh.copy()
        v_sz = int(tar_height / 30)
        v_element = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_sz))
        vertical = cv2.erode(vertical, v_element, (-1, -1))
        vertical = cv2.dilate(vertical, v_element, (-1, -1))
        if self.debug:
            cv2.imwrite("vertical.jpg", vertical)

        lines = cv2.bitwise_or(vertical, horizontal)
        if self.debug:
            cv2.imwrite("lines.jpg", lines)

        # ------------------------------- extract the contour -----------------------------------
        overlap_margin = 2
        show_img = cv2.cvtColor(resize, cv2.COLOR_GRAY2BGR)
        _, contours, hierarchy = cv2.findContours(lines, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for i in range(len(contours)):
            x, y, w, h = cv2.boundingRect(contours[i])
            cv2.rectangle(show_img, (x, y), (x+w, y+h), (255, 255, 0), 1)
            if w * h > tar_height * tar_width // 3:
                continue
            else:
                boxes.append([x - overlap_margin, y - overlap_margin, x + w + overlap_margin, y + h + overlap_margin])

            # cv2.imshow("show", show_img)
            # cv2.waitKey(0)

        merged = self.non_max_suppression_fast(boxes=boxes, img=show_img)

        for [x, y, x1, y1] in merged:
            cv2.rectangle(show_img, (x, y), (x1, y1), (0, 0, 255), 2)
        if self.debug:
            cv2.imwrite("contours.jpg", show_img)

        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def non_max_suppression_fast(self, boxes, img):
        if len(boxes) == 0:
            return []

        # initialize the list of picked indexes
        merged = []

        for i in range(len(boxes)):
            [r_x1, r_y1, r_x2, r_y2] = boxes[i]

            j = 0
            while j < len(merged):
                [m_x1, m_y1, m_x2, m_y2] = merged[j]

                xx1 = np.maximum(r_x1, m_x1)
                yy1 = np.maximum(r_y1, m_y1)
                xx2 = np.minimum(r_x2, m_x2)
                yy2 = np.minimum(r_y2, m_y2)

                w = np.maximum(0, xx2 - xx1 + 1)
                h = np.maximum(0, yy2 - yy1 + 1)
                if (w * h) > 0:
                    _xx1 = np.minimum(r_x1, m_x1)
                    _yy1 = np.minimum(r_y1, m_y1)
                    _xx2 = np.maximum(r_x2, m_x2)
                    _yy2 = np.maximum(r_y2, m_y2)

                    [r_x1, r_y1, r_x2, r_y2] = [_xx1, _yy1, _xx2, _yy2]
                    del merged[j]
                    j = 0
                    continue

                j += 1
            merged.append([r_x1, r_y1, r_x2, r_y2])
        return merged


if __name__ == '__main__':
    roi = ROI()
    path = "D:/workspace/tesseract_pdf_parse/data/COM_15-1.jpg"

    img = cv2.imread(path)

    roi.identifi_table_area(img)
