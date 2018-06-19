import copy

import cv2

import logger as log
import utils.string_manage as stringer
import utils.text_annos_manage as manager


EMP = ""
SPLITER = "_/SP/_"
THRESH_MIN_LINE_KEYS = 3


class Table:
    def __init__(self, debug, show_img_w=300):
        self.debug = debug
        self.show_img_w = show_img_w
        self.show_line_w = 2

        self.titles = ["LIGHTING FIXTURE SCHEDULE", "LIGHT FIXTURE SCHEDULEO"]
        self.title = self.titles[0]
        self.fst_key = "TYPE"

    def candidate(self, content):
        total_text = content['total_text']
        total_text = total_text.replace(" ", "")

        for title in self.titles:
            dst_word = title.replace(" ", "")
            if total_text.find(dst_word) != -1:
                self.title = title
                return True
        return False

    def parse_table(self, content):
        annos = content['annos']
        img = content['image']

        lines = manager.bundle_to_lines()

        # --- determine title area -------------------------------------------------
        title_anno_ids = []
        title_txt = ""
        keys = self.title.split(" ")

        for id in range(len(annos)):
            if annos[id]['text'].upper().find(keys[0]) != -1:
                title_anno_ids.append(id)
                title_txt += annos[id]['text']
                if stringer.equal(title_txt.upper(), self.title):
                    break

                right_id_1 = manager.get_right_neighbor(src_anno_id=id, annos=annos)[0]
                if right_id_1 is None:
                    continue
                title_anno_ids.append(right_id_1)
                title_txt += annos[right_id_1]['text']
                if stringer.equal(title_txt.upper(), self.title):
                    break

                right_id_2 = manager.get_right_neighbor(src_anno_id=right_id_1, annos=annos)[0]
                if right_id_2 is None:
                    continue
                title_anno_ids.append(right_id_2)
                title_txt += annos[right_id_2]['text']
                if stringer.equal(title_txt.upper(), self.title):
                    break

            title_anno_ids.clear()
            title_txt = ''

        if len(title_txt) == 0:
            log.log_print("not contains the target title.")
            return

        # --- determine the roi area -----------------------------------------------
        fst_id = title_anno_ids[0]
        last_id = title_anno_ids[-1]

        _left_edge_id, _ = manager.get_left_neighbor_no_same_sz(src_anno_id=fst_id, annos=annos)
        _right_edge_id, _ = manager.get_right_neighbor_no_same_sz(src_anno_id=last_id, annos=annos)

        img = content['image']
        height, width = img.shape[:2]
        if _left_edge_id is None:
            l_edge_pt = [0, manager.get_left_edge(annos[fst_id])[1]]
        else:
            l_edge_pt = manager.get_left_edge(annos[_left_edge_id])

        if _right_edge_id is None:
            r_edge_pt = [width, manager.get_left_edge(annos[last_id])[1]]
        else:
            r_edge_pt = manager.get_right_edge(annos[_right_edge_id])

        candidates = []
        for id in range(len(annos)):
            anno = annos[id]
            l_pt = manager.get_left_edge(anno)
            r_pt = manager.get_right_edge(anno)
            if l_edge_pt[0] < l_pt[0] < r_pt[0] < r_edge_pt[0] and l_pt[1] > l_edge_pt[1]:
                candidates.append(anno)

        print(l_edge_pt[1], l_edge_pt[0], r_edge_pt[0])
        crop = img[int(l_edge_pt[1]):, int(l_edge_pt[0]):int(r_edge_pt[0])]
        cv2.imwrite("crop_1.jpg", crop)

        # ---------- configure the table -------------------------------------------
        lines = manager.bundle_to_lines(origin_annos=candidates)

        annos = copy.deepcopy(candidates)

        min_pos = None
        key_line_id = None
        for line_id in range(len(lines)):
            line = lines[line_id]
            line_text = line['text'].upper()

            pos = line_text.find(self.fst_key)
            if pos != -1 and (min_pos is None or min_pos > pos):
                min_pos = pos
                key_line_id = line_id

        if key_line_id is None:
            return

        num_keys = len(lines[key_line_id]['line'])
        key_line = [""] * num_keys
        key_anno_list = [None] * num_keys
        for line_id in range(key_line_id + 1):
            for j in lines[line_id]['line']:
                min_dis = None
                min_i = None
                for i in lines[key_line_id]['line']:
                    dis = manager.dis_anno2anno(annos[i], annos[j])
                    if min_dis is None or min_dis > dis:
                        min_dis = dis
                        min_i = lines[key_line_id]['line'].index(i)
                if min_dis is not None:
                    key_line[min_i] += " " + annos[j]['text']
                    key_anno_list[min_i] = annos[j]

        # rearrange the keyword list --------------------------------------------------------
        merge_pair_list = []
        end_line_id = None
        for line_id in range(key_line_id + 1, len(lines)):
            for i in range(len(key_anno_list)):
                for j in lines[line_id]['line']:
                    try:
                        if end_line_id is None:
                            anno_l = manager.get_left_edge(annos[j])[0]
                            anno_r = manager.get_right_edge(annos[j])[0]

                            cur_key_r = manager.get_right_edge(key_anno_list[i])[0]
                            next_key_l = manager.get_left_edge(key_anno_list[i + 1])[0]
                            if anno_l < cur_key_r < next_key_l < anno_r and [i, i+1] not in merge_pair_list:
                                merge_pair_list.append([i, i+1])

                            before_key_r = manager.get_right_edge(key_anno_list[i - 1])[0]
                            if anno_l < before_key_r < next_key_l < anno_r:
                                end_line_id = line_id

                    except Exception as e:
                        continue

        if end_line_id is None:
            end_line_id = len(lines)
        print(merge_pair_list)
        if len(merge_pair_list) != 0:
            for p in range(len(merge_pair_list) - 1 , -1, -1):
                [p1, p2] = merge_pair_list[p]
                try:
                    key_line[p1] = key_line[p1] + key_line[p2]
                    key_anno_list[p1]['text'] = key_anno_list[p1]['text'] + key_anno_list[p2]['text']
                    key_line[p2] = None
                    key_anno_list[p2] = None
                except Exception:
                    continue

            i = len(key_anno_list) - 1
            while i > 0:
                if key_line[i] is None:
                    del key_line[i]
                if key_anno_list[i] is None:
                    del key_anno_list[i]
                i -= 1

        # ------------ table ----------------------------------------------------------------------------------------
        value_lines = []
        last_line_id = None

        for line_id in range(key_line_id + 1, end_line_id):
            line = lines[line_id]['line']
            
            value_line = [""] * len(key_line)
            start = 0
            for k in range(0, len(key_anno_list)):
                temp_str = EMP
                if k == 0:  # first annotation
                    for i in range(start, len(line)):
                        if annos[line[i]]['used']: continue
                        if manager.get_right_edge(annos[line[i]])[0] <= manager.get_left_edge(key_anno_list[k + 1])[0]:
                            temp_str += annos[line[i]]['text'] + ' '
                            annos[line[i]]['used'] = True
                        else:
                            start = i
                            value_line[k] = temp_str
                            break
                elif k != len(key_anno_list) - 1:  # middle annotations
                    for i in range(start, len(line)):
                        if annos[line[i]]['used']:
                            continue
                        if manager.get_right_edge(key_anno_list[k - 1])[0] <= manager.get_left_edge(annos[line[i]])[0] and \
                                    manager.get_right_edge(annos[line[i]])[0] < manager.get_left_edge(key_anno_list[k + 1])[0]:

                            if i != len(line) - 1 and manager.dis_anno2anno(annos[line[i]], annos[line[i + 1]]) < 3 * manager.get_height(annos[lines[key_line_id]['line'][0]]):
                                temp_str += annos[line[i]]['text'] + ' '
                                annos[line[i]]['used'] = True
                            else:
                                temp_str += annos[line[i]]['text'] + ' '
                                annos[line[i]]['used'] = True
                                value_line[k] = temp_str
                                start = i + 1
                                break
                        else:
                            start = i
                            value_line[k] = temp_str
                            break
                elif k == len(key_anno_list) - 1:  # last annotation
                    for i in range(start, len(line)):
                        if annos[line[i]]['used']:
                            continue
                        if manager.get_right_edge(key_anno_list[k - 1])[0] < manager.get_left_edge(annos[line[i]])[0]:
                            temp_str += annos[line[i]]['text'] + ' '
                            annos[line[i]]['used'] = True
                    value_line[k] = temp_str

            if last_line_id is not None and manager.dis_line2line(lines[line_id], lines[last_line_id]) > 2 * manager.get_height(annos[lines[line_id]['line'][0]]):
                break

            if value_line[0] == "" and len(value_lines) > 0:
                if value_line[1] == "":
                    for j in range(len(value_lines[-1])):
                        value_lines[-1][j] = value_lines[-1][j] + value_line[j]
                else:
                    _flag_same_line = True
                    for j in range(len(value_lines[-1])):
                        if value_lines[-1][j] == "" and value_line[j] != "":
                            _flag_same_line = False

                    _cnt1 = value_lines[-1].count("")
                    _cnt2 = value_line.count("")
                    if _cnt1 < _cnt2 or _cnt2 > len(value_line) // 3:
                        _flag_same_line = False

                    if _flag_same_line:
                        for j in range(len(value_lines[-1])):
                            value_lines[-1][j] = value_lines[-1][j] + value_line[j]
                        continue
                    else:
                        value_lines.append(value_line)
                        last_line_id = line_id

                continue
            value_lines.append(value_line)
            last_line_id = line_id

        result_dicts = []
        for value_line in value_lines:
            dict_line = {}
            for i in range(len(key_line)):
                dict_line[key_line[i]] = value_line[i]
            result_dicts.append(dict_line)
        return result_dicts
