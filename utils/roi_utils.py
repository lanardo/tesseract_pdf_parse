import cv2
import numpy as np


class RoiUtils:
    def __init__(self, debug=False):
        self.debug = debug
        self.tar_width = -1
        self.margin = 5

    def binary_inv_img(self, img):

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

        return thresh

    def grid_lines(self, binary):
        height, width = binary.shape[:2]

        horizontal = binary.copy()
        h_sz = int(width / 30)
        h_element = cv2.getStructuringElement(cv2.MORPH_RECT, (h_sz, 1))
        horizontal = cv2.erode(horizontal, h_element, (-1, -1))
        horizontal = cv2.dilate(horizontal, h_element, (-1, -1))
        if self.debug:
            cv2.imwrite("horizontal.jpg", horizontal)

        vertical = binary.copy()
        v_sz = int(height / 30)
        v_element = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_sz))
        vertical = cv2.erode(vertical, v_element, (-1, -1))
        vertical = cv2.dilate(vertical, v_element, (-1, -1))
        if self.debug:
            cv2.imwrite("vertical.jpg", vertical)

        lines = cv2.bitwise_or(vertical, horizontal)
        element = cv2.getStructuringElement(cv2.MORPH_RECT, (self.margin, self.margin))
        lines = cv2.dilate(lines, element, (-1, -1))
        if self.debug:
            cv2.imwrite("lines.jpg", lines)
        return lines

    def extract_boxes(self, line_img):
        # show_img = cv2.cvtColor(line_img, cv2.COLOR_GRAY2BGR)

        height, width = line_img.shape[:2]
        _, contours, hierarchy = cv2.findContours(line_img, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for i in range(len(contours)):
            x, y, w, h = cv2.boundingRect(contours[i])
            # print(hierarchy[0][i])
            if w * h > height * width // 2:
                continue
            else:
                boxes.append([x - self.margin, y - self.margin, x + w + self.margin, y + h + self.margin])
                # cv2.rectangle(show_img, (x - self.margin, y - self.margin), (x+w+self.margin, y+h+self.margin), (255, 0, 0), 10)
                # cv2.imshow("show_img", cv2.resize(show_img, (1000, 700)))
                # cv2.waitKey(1)

        return boxes

    def filter_non_table_area(self, boxes):
        filters = []
        for box in boxes:
            [x1, y1, x2, y2] = box
            w = x2 - x1
            h = y2 - y1
            if w > h * 10 or h > w * 10:
                continue
            filters.append(box)
        return filters

    def non_max_suppression_fast(self, boxes):
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

    def identify_table_area(self, page_img):
        # --------------------------------- convert to the gray ---------------------------------
        binary_inv_img = self.binary_inv_img(img=page_img)

        # --------------------------------- horizon and vertical line detection -----------------
        line_img = self.grid_lines(binary=binary_inv_img)

        # ------------------------------- extract the contour -----------------------------------
        boxes = self.extract_boxes(line_img=line_img)

        # ------------------------------- merge the extracted contours --------------------------
        merged_boxes = self.non_max_suppression_fast(boxes=boxes)
        candi_boxes = self.filter_non_table_area(boxes=merged_boxes)

        # ---------------------------------------------------------------------------------------
        binary_img = cv2.bitwise_not(binary_inv_img)

        show_img = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2BGR)
        # for [x, y, x1, y1] in boxes:
        #     cv2.rectangle(show_img, (x, y), (x1, y1), (255, 0, 0), 2)
        # for [x, y, x1, y1] in merged_boxes:
        #     cv2.rectangle(show_img, (x, y), (x1, y1), (0, 0, 255), 2)
        for [x, y, x1, y1] in candi_boxes:
            cv2.rectangle(show_img, (x, y), (x1, y1), (0, 0, 255), 10)
        cv2.imwrite("contours.jpg", show_img)
        candi_img = binary_img + line_img
        cv2.imwrite("candi_img.jpg", candi_img)

        return candi_boxes, candi_img


if __name__ == '__main__':
    roi = RoiUtils()
    path = "D:/workspace/tesseract_pdf_parse/data/COM_1-1.jpg"

    img = cv2.imread(path)

    roi.identify_table_area(img)
