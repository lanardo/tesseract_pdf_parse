import logger as log
import utils.string_manage as stringer
import utils.text_annos_manage as manager
from utils.settings import *

EMP = ""
THRESH_MERGE = 1.5
SP = "_"


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
        img_height, img_width = img.shape[:2]

        # clear the overlap annos --------------------------------------------------
        to_del_ids = []
        for i in range(len(annos) - 1):
            for j in range(i+1, len(annos)):
                if manager.is_overlap_anno(annos[i], annos[j]):
                    if len(annos[i]['text']) > len(annos[j]['text']):
                        to_del_ids.append(j)
                    else:
                        to_del_ids.append(i)
        to_del_ids.sort()
        for i in range(len(to_del_ids)-1, -1, -1):
            del annos[to_del_ids[i]]

        # --- bundle to the lines --------------------------------------------------------------
        lines = manager.bundle_to_lines(origin_annos=annos)

        # --- merge the neighbors --------------------------------------------------------------
        manager.merge_annos_on_lines(lines=lines, annos=annos)

        # --- determine title line -------------------------------------------------------------
        """
            line = {
                    'ids': line,
                    'pos': line_pos, 
                    'text': line_text}
                    )
        """
        title_line_id = -1
        for i in range(len(lines)):
            line = lines[i]
            line_text = line['text'].replace(' ', '')
            for title in self.titles:
                title_text = title.replace(' ', '')
                if line_text.find(title_text) != -1:
                    title_line_id = i
                    res_title = title
                    break

        if title_line_id == -1:
            err_msg = "can not find the title"
            return err_msg

        # ----------------------------- configure the keywords -------------------------------------------
        keyword = "TYPE"
        keyword_line_id = -1
        for line_id in range(title_line_id + 1, len(lines)):
            if lines[line_id]['text'].find(keyword) != -1:
                keyword_line_id = line_id
                break
        if keyword_line_id == -1:
            err_msg = "can not find keyword line with {}".format(keyword)
            return err_msg

        # --------------------- update the keyword multi line --------------------------------
        keyword_line = lines[keyword_line_id]
        key_annos = []
        for id in keyword_line['ids']:
            key_annos.append(annos[id])

        start_line_id = -1
        for line_id in range(title_line_id + 1, len(lines)):
            if line_id == keyword_line_id:
                continue
            cur_line = lines[line_id]

            if line_id < keyword_line_id:
                for id in cur_line['ids']:
                    j = 0
                    while j < len(key_annos):
                        if j != len(key_annos):
                            if manager.get_right_edge(key_annos[j])[0] < manager.get_left_edge(annos[id])[0] < manager.get_left_edge(key_annos[j + 1])[0]:
                                key_annos.insert(j + 1, annos[id])
                                break
                        elif j == len(key_annos) - 1:
                            if manager.get_right_edge(key_annos[j])[0] < manager.get_left_edge(annos[id])[0]:
                                key_annos.append(annos[id])
                                break
                        if manager.get_left_edge(key_annos[j])[0] < manager.get_left_edge(annos[id])[0] < manager.get_right_edge(key_annos[j + 1])[0]:
                            key_annos[j]['text'] = annos[id]['text'] + SP + key_annos[j]['text']
                        j += 1

            if line_id > keyword_line_id:
                if len(cur_line['ids']) > len(key_annos) // 3:
                    start_line_id = line_id
                    break
                for id in cur_line['ids']:
                    j = 0
                    to_update_key_ids = [[]] * len(key_annos)
                    while j < len(key_annos):
                        if j == 0:
                            if 0 < manager.get_cenpt(annos[id])[0] < manager.get_left_edge(key_annos[1])[0]:
                                to_update_key_ids[0].append(annos[id])
                        elif j == len(key_annos) - 1:
                            if manager.get_right_edge(key_annos[-2])[0] < manager.get_cenpt(annos[id])[0] < img_width:
                                to_update_key_ids[-1].append(annos[id])
                        elif manager.get_right_edge(key_annos[j - 1])[0] < manager.get_cenpt(annos[id])[0] < \
                                manager.get_left_edge(key_annos[j + 1])[0]:
                            to_update_key_ids[j].append(annos[id])

                    for j in range(len(to_update_key_ids) - 1, -1, -1):
                        if len(to_update_key_ids[j]) == 0:
                            continue
                        base = key_annos[j]['text']
                        del key_annos[j]
                        for k in range(len(to_update_key_ids[j])-1, -1, -1):
                            anno = to_update_key_ids[j][k]
                            anno['text'] = base + anno['text']
                            key_annos.insert(j, anno)

        if start_line_id == -1:
            err_msg = "error on configure the keyword lines"
            return err_msg

        # ----------- configure the table ------------------------------------------------------------
        table = []
        last_line = None
        end_flag = False
        for line_id in range(start_line_id, len(lines)):
            if last_line is None:
                dis = 0
            else:
                dis = cur_line['pos'] - last_line['pos']

            cur_height = manager.get_height(annos[cur_line['ids'][0]])
            if dis > cur_height * 0.5:
                end_flag = True
                break

            value_line = [''] * len(key_annos)
            end_flag = False
            for id in cur_line['ids']:
                for j in range(len(key_annos)):
                    if j == 0:
                        if 0 < manager.get_cenpt(annos[id])[0] < manager.get_left_edge(key_annos[2])[0]:
                            value_line[0] = annos[id]['text']
                    elif j == len(key_annos) - 1:
                        if manager.get_right_edge(key_annos[-2])[0] < manager.get_cenpt(annos[id])[0] < img_width:
                            value_line[-1] = annos[id]['text']
                    elif manager.get_right_edge(key_annos[j-1])[0] < manager.get_cenpt(annos[id])[0] < manager.get_left_edge(key_annos[j+1])[0]:
                        value_line[j] = annos[id]['text']
                    else:
                        end_flag = True
                        break
            if end_flag:
                break
            else:
                table.append(value_line)

        for key in key_annos:
            sys.stdout.write(key['text'] + ' ')
        for line in table:
            print(line)
        return {
            'title': res_title,
            'lines': table,
            'keywords': [key_anno['text'] for key_anno in key_annos]
        }