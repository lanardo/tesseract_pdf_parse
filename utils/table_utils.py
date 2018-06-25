import logger as log
import utils.string_manage as stringer
import utils.text_annos_manage as manager
from utils.settings import *

EMP = ''
THRESH_MERGE = 1.5
SP = "_"


class Table:
    def __init__(self, debug, show_img_w=300):
        self.debug = debug
        self.show_img_w = show_img_w
        self.show_line_w = 2

        self.titles = ["LIGHTING FIXTURE SCHEDULE", "LIGHT FIXTURE SCHEDULE"]
        self.title = self.titles[0]
        self.fst_keys = ["TYPE", "DESCRIPTION"]

    def candidate(self, content):
        total_text = content['total_text']
        total_text = total_text.replace(" ", EMP)

        for title in self.titles:
            dst_word = title.replace(" ", EMP)
            if total_text.find(dst_word) != -1:
                self.title = title
                return True
        return False

    def find_title_line(self, lines):
        """
                    line = {
                            'ids': line,
                            'pos': line_pos,
                            'text': line_text}
                            )
                """
        res_title = EMP
        title_line_id = -1
        for i in range(len(lines)):
            line = lines[i]
            line_text = line['text'].replace(' ', EMP)
            for title in self.titles:
                title_text = title.replace(' ', EMP)
                if line_text.find(title_text) != -1:
                    title_line_id = i
                    res_title = title
                    break
        return title_line_id, res_title

    def find_keyword_lind(self, lines, title_line_id):
        keyword_line_id = -1
        for line_id in range(title_line_id + 1, len(lines)):
            for dst_keyword in self.fst_keys:
                if lines[line_id]['text'].find(dst_keyword) != -1:
                    keyword_line_id = line_id
                    break
            if keyword_line_id != -1:
                break
        if keyword_line_id == -1 or keyword_line_id > 5:
            return title_line_id + 1
        return keyword_line_id

    def update_multi_keyword_line(self, annos, lines, keyword_line_id, title_line_id):
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
                        if j != len(key_annos) - 1:
                            if manager.get_right_edge(key_annos[j])[0] < manager.get_left_edge(annos[id])[0] < \
                                    manager.get_right_edge(annos[id])[0] < manager.get_left_edge(key_annos[j + 1])[0]:
                                key_annos.insert(j + 1, annos[id])
                                break
                        elif j == len(key_annos) - 1:
                            if manager.get_right_edge(key_annos[j])[0] < manager.get_left_edge(annos[id])[0]:
                                key_annos.append(annos[id])
                                break
                        if j < len(key_annos) and \
                                manager.get_left_edge(key_annos[j])[0] < manager.get_cenpt(annos[id])[0] < manager.get_right_edge(key_annos[j])[0]:
                            key_annos[j]['text'] = annos[id]['text'] + SP + key_annos[j]['text']
                        j += 1

            if line_id > keyword_line_id:
                if len(cur_line['ids']) > len(key_annos) // 3:
                    start_line_id = line_id
                    break

                to_update_key_ids = [[] for i in range(len(key_annos))]
                for id in cur_line['ids']:
                    for j in range(len(key_annos) - 1, -1, -1):
                        if j == 0:
                            if 0 < manager.get_cenpt(annos[id])[0] < manager.get_left_edge(key_annos[1])[0]:
                                to_update_key_ids[0].append(annos[id])
                                break
                        elif j == len(key_annos) - 1:
                            if manager.get_right_edge(key_annos[-2])[0] < manager.get_cenpt(annos[id])[0] < img_width:
                                to_update_key_ids[-1].append(annos[id])
                                break
                        elif manager.get_right_edge(key_annos[j - 1])[0] < manager.get_left_edge(annos[id])[0] < \
                                manager.get_right_edge(annos[id])[0] < manager.get_left_edge(key_annos[j + 1])[0]:
                            to_update_key_ids[j].append(annos[id])
                            break

                for j in range(len(to_update_key_ids) - 1, -1, -1):
                    if len(to_update_key_ids[j]) == 0:
                        continue
                    base = key_annos[j]['text']
                    del key_annos[j]
                    for k in range(len(to_update_key_ids[j]) - 1, -1, -1):
                        anno = to_update_key_ids[j][k]
                        anno['text'] = base + SP + anno['text']
                        key_annos.insert(j, anno)

        return key_annos, start_line_id

    def configure_table(self, annos, lines, key_annos, start_line_id):
        table = []
        last_line = None
        end_flag = False
        for line_id in range(start_line_id, len(lines)):
            cur_line = lines[line_id]
            if last_line is None:
                dis = 0
            else:
                dis = cur_line['pos'] - last_line['pos']
            cur_height = manager.get_height(annos[cur_line['ids'][0]])
            if dis > cur_height * 3.5:
                end_flag = True
                break

            value_line = [EMP] * len(key_annos)
            end_flag = False
            for id in cur_line['ids']:
                _candi_line_flag = False
                for j in range(len(key_annos) - 1, -1, -1):
                    if j > 0 and manager.get_left_edge(annos[id])[0] < manager.get_right_edge(key_annos[j-1])[0] < manager.get_left_edge(key_annos[j])[0] < manager.get_right_edge(annos[id])[0]:
                        _candi_line_flag = False
                        break

                    if j == 0:
                        if 0 < manager.get_cenpt(annos[id])[0] < manager.get_left_edge(key_annos[1])[0]:
                            value_line[0] = value_line[0] + EMP + annos[id]['text']
                            _candi_line_flag = True
                            break
                    elif j == len(key_annos) - 1:
                        if manager.get_right_edge(key_annos[-2])[0] < manager.get_cenpt(annos[id])[0]:
                            value_line[-1] = value_line[-1] + EMP + annos[id]['text']
                            _candi_line_flag = True
                            break
                    elif manager.get_right_edge(key_annos[j-1])[0] < manager.get_left_edge(annos[id])[0] < manager.get_right_edge(annos[id])[0] < manager.get_left_edge(key_annos[j+1])[0]:
                        value_line[j] = value_line[j] + EMP + annos[id]['text']
                        _candi_line_flag = True
                        break

                if not _candi_line_flag:
                    end_flag = True

            if end_flag:
                break

            else:
                # dis1 = lines[line_id]['pos'] - lines[line_id - 1]['pos']
                # dis2 = lines[line_id - 1]['pos'] - lines[line_id - 2]['pos']
                num_no_empty = len(value_line) - value_line.count(EMP)
                if 2 < line_id < len(lines) - 1 and num_no_empty <= len(value_line) // 3:  # dis2 > dis1 and dis1 < cur_height * 1.5 and
                    if value_line[0] == EMP:
                        for j in range(len(value_line)):
                            table[-1][j] = table[-1][j] + ' ' + value_line[j]
                    else:
                        end_flag = True
                        continue
                else:
                    table.append(value_line)
                last_line = lines[line_id]

        return table, end_flag

    def show_dict(self, res_dict):
        """
        'title': title_text,
        'lines': table,
        'keywords': [key_anno['text'] for key_anno in key_annos]
        """

        title = res_dict['title']
        print("\n>>> title: ")
        print(title.encode('utf-8'))

        keywords = res_dict['keywords']
        print("\n>>> keywords: ")
        for key in keywords:
            print(key.encode('utf-8'))

        lines = res_dict['lines']
        print("\n>>> Table: ")
        for line in lines:
            print()
            for value in line:
                sys.stdout.write(" {}".format(value.encode('utf-8')))

    def parse_content(self, content):
        annos = content['annos']
        img = content['image']
        img_height, img_width = img.shape[:2]

        # clear the overlap annos --------------------------------------------------
        to_del_ids = []
        for i in range(len(annos) - 1):
            for j in range(i + 1, len(annos)):
                ov = manager.is_overlap_anno(annos[i], annos[j])
                if ov in ["same", "error"]:
                    if len(annos[i]['text']) > len(annos[j]['text']):
                        to_del_ids.append(j)
                    else:
                        to_del_ids.append(i)
        to_del_ids.sort()
        for i in range(len(to_del_ids) - 1, -1, -1):
            del annos[to_del_ids[i]]

        # --- bundle to the lines --------------------------------------------------------------------------------------
        lines = manager.bundle_to_lines(origin_annos=annos)

        # --- merge the line annos -------------------------------------------------------------------------------------
        manager.merge_annos_on_lines(lines=lines, annos=annos)

        # --- determine title line -------------------------------------------------------------------------------------
        title_line_id, title_text = self.find_title_line(lines=lines)
        if title_line_id == -1:
            err_msg = "can not find the title"
            return err_msg

        # --- configure the keywords -----------------------------------------------------------------------------------
        keyword_line_id = self.find_keyword_lind(lines=lines, title_line_id=title_line_id)
        if keyword_line_id == -1:
            err_msg = "can not find keyword line with {}".format(keyword)
            return err_msg

        # --------------------- update the keyword multi line ----------------------------------------------------------
        key_annos, start_line_id = self.update_multi_keyword_line(annos=annos, lines=lines,
                                                                  keyword_line_id=keyword_line_id,
                                                                  title_line_id=title_line_id)
        if start_line_id == -1:
            err_msg = "error on configure the keyword lines"
            return err_msg

        # ----------- configure the table ------------------------------------------------------------------------------
        table, _ = self.configure_table(annos=annos, lines=lines, key_annos=key_annos, start_line_id=start_line_id)

        print("\n>>> raw lines: ")
        for line in lines:
            print(line['text'].encode('utf-8'))

        # rearrange the result dict ------------------------------------------------------------------------------------
        line_dict_list = []
        for line in table:
            line_dict = {}
            for i in range(len(key_annos)):
                key = key_annos[i]['text']
                value = line[i]
                line_dict[key] = value.encode('utf-8')
            line_dict_list.append(line_dict)

        return {
            'table': line_dict_list
        }

    def parse_table(self, contents):
        max_num_anno = -1
        max_content_id = -1
        for i in range(len(contents)):
            content = contents[i]
            annos = content['annos']
            if len(annos) > max_num_anno:
                max_num_anno = len(annos)
                max_content_id = i

        print("max_num_anno_content_id: ", max_content_id)
        result = self.parse_content(contents[max_content_id])

        if type(result) == str:
            print(result)
        else:
            print(result)
            # self.show_dict(result)
            pass
        return result
