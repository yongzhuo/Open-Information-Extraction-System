# !/usr/bin/python
# -*- coding: utf-8 -*-
# @time    : 2020/12/31 15:07
# @author  : Mo
# @function: build open-knowledge-graph(SPO) by pyltp(version==3.4.0)


from pyltp import Segmentor,  Postagger,  Parser
from pyltp import NamedEntityRecognizer
from pyltp import SementicRoleLabeller
import logging
import os


# logging 配置
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Macadam")
logger.setLevel(level = logging.INFO)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(formatter)
logger.addHandler(console)


# 依存句法 --- 关系类型
_REL = ["CMP", "ATT", "LAD", "RAD", "ADV"]  # 关系可以接的类型
_RIGHT = ["ATT", "LAD", "RAD"]  # 右边可以连的关系
_LEFT = ["ATT", "LAD", "RAD"]  # 左边可以连的关系
_OBJ = ["VOB", "IOB", "FOB"]  # 宾语: 直接宾语, 间接宾语, 前置宾语
_SBV = "SBV"  # 主谓关系
_ATT = "ATT"  # 定中关系
_CMP = "CMP"  # 动补结构
_POB = "POB"  # 介宾关系
_RAD = "RAD"  # 左附加关系
_COO = "COO"  # 并列关系

_noun = "n"   # 名词
_verb = "v"   # 动词


class Triple:
    def __init__(self, ltp_dir="./ltp_data_v3.4.0"):
        # LTP初始化模型, 从模型文件---ltp_data_v3.4.0
        # 分词模型, 词性标注模型, 依存句法分析, 命名实体识别, # 语义角色标注
        self.ner = NamedEntityRecognizer()
        self.seg = Segmentor()
        self.pos = Postagger()
        self.ppd = Parser()
        self.seg.load_with_lexicon(os.path.join(ltp_dir,  "cws.model"),  "ltp_data/lexicon.txt")
        self.ppd.load(os.path.join(ltp_dir,  "parser.model"))
        self.pos.load(os.path.join(ltp_dir,  "pos.model"))
        self.ner.load(os.path.join(ltp_dir,  "ner.model"))

    def extract_triple(self, words, poss, rels, ddps_dict, ddps_hds_rels):
        """
        抽取三元组(规则, 即五大基本句式: 主谓, 主谓宾, 主系表, 主谓宾宾, 主谓宾补)
        Args:
            words: list, sentence cut, eg. ["依存句法", "分析"] 
            poss:  list, postag of sent, eg. ["n", "v"]
            ddps:  list<object>, dependency parsing(ddp) of sent, eg. [object, object...]
            rels:  list, relation of ddp, eg. ["ATT"]
            ddps_dict: list<dict>, ddp of word, eg. [{}, {'ATT': [0]}]
            ddps_hds_rels: list<list>, ddp of detail, eg. [['ATT', '依存句法', 0, 'n', '分析', 1, 'v'], ['HED', '分析', 1, 'v', 'ROOT', -1, 'v']]
        Returns:
            tuple(list, list, list<object>, list, dict, list<list>) 
        """

        ddps_dict = self.fix_pr(ddps_dict)

        logger.info("fix ddps_dict: {}".format(ddps_dict))

        self.triples = []
        # if _SBV in rels:  # 句子存在主谓关系
        # COO并列关系处理
        len_words = len(words)
        for idx in range(len_words):
            relation = ddps_hds_rels[idx][0]
            head = ddps_hds_rels[idx][2]
            idx_dict = ddps_dict[idx]

            if _SBV in idx_dict:  # 存在---主谓宾
                logger.info("extract SBV")
                e1_idx = idx_dict[_SBV][0]  # 然后根据SBV获取 主语subject
                logger.info("entity_1_s(e1s) extract start!")
                e1s = self.entity_extend(words, poss, ddps_dict, e1_idx, [])
                # 宾语object 统一处理, 包括 直接宾语, 间接宾语, 前置宾语
                logger.info("relation_object(ro) extract start!")
                self.relation_object(e1s, idx, words, poss, ddps_dict, idx_dict)
                if _COO in idx_dict:  # 并列关系(谓语-即关系)
                    logger.info("relation_object_coo(roo) extract start!")
                    idx_coos = idx_dict[_COO]
                    for idx_coo in idx_coos:
                        idx_dict2 = ddps_dict[idx_coo]
                        self.relation_object(e1s, idx_coo, words, poss, ddps_dict, idx_dict2)
            else:
                ee = 0

            if _ATT == relation:  # 定中关系
                r = words[idx]
                for obj in _OBJ:  # 遍历三种宾语
                    if obj in idx_dict:
                        e1 = self.entity_extend(words, poss, ddps_dict, head-1)
                        e2 = self.entity_extend(words, poss, ddps_dict, idx_dict[obj][0])
                        temp = r + e2[0]
                        if temp == e1[:len(temp)]:
                            e1 = e1[len(temp):]
                        if temp not in e1:
                            self.triples.append([e1, r, e2[0]])

        return self.triples

    def relation_object(self, e1s, idx, words, poss, ddps_dict, idx_dict):
        """
        抽取宾语
        Args:
            e1s: str, entity of subject, eg. ["依存句法"] 
            r:  str, relation, eg. ["是"]
            idx:  int, position of word in words, eg. 3
            idx_dict: dict, enum in ddps_dict, eg. {'ATT': [0]}
        Returns:
            tuple(list, list, list<object>, list, dict, list<list>) 
        """
        logger.info("idx:{}, idx_dict:{}".format(idx, idx_dict))

        def relation_extend():
            rel_inters = list(set(_REL) & set(list(idx_dict.keys())))  # 所有的依存关系成分(可拓展的)
            ris_idxs = []
            for ris in rel_inters:  # 成分标记(大写) 转 int
                ris_idx = idx_dict[ris][0]
                ris_idxs.append(ris_idx)
            ris_idxs_add = ris_idxs + [idx]  # idxs 排序
            ris_idxs_add.sort()
            r = "".join([words[i] for i in ris_idxs_add])
            return r, ris_idxs

        r, ris_idxs = relation_extend()  # 先获取关系(包括并列的情况 COO)
        logger.info("r:{}, ris_idxs:{}".format(r, ris_idxs))

        for obj in _OBJ:  # 遍历三种宾语, 宾语在前面的谓语, 例句: "他做完了作业"
            if obj in idx_dict:
                logger.info("e2s---1:")
                e2s = self.entity_extend(words, poss, ddps_dict, idx_dict[obj][0], [])
                for e2 in e2s:
                    for e1 in e1s:
                        self.triples.append([e1, r, e2])
                        logger.info("{}---{}---{}".format(e1, r, e2))
        for obj in _OBJ:
            for ris_idx in ris_idxs:
                if ris_idx and obj in ddps_dict[ris_idx]:
                    logger.info("e2s---2:")
                    e2s = self.entity_extend(words, poss, ddps_dict, ddps_dict[ris_idx][obj][0], [])
                    for e2 in e2s:
                        for e1 in e1s:
                            self.triples.append([e1, r, e2])
                            logger.info("{}---{}---{}".format(e1, r, e2))
        # if _CMP in idx_dict:  # 含有介宾关系的主谓动补关系, 宾语在后面的谓语, 例句: "李白上得了厅堂, 下得了厨房。"
        #     cmp_idx = idx_dict[_CMP][0]
        #     r = words[idx] + words[cmp_idx]
        #     for obj in _OBJ:
        #         if obj in ddps_dict[cmp_idx]:
        #             e2s = self.entity_extend(words, poss, ddps_dict, ddps_dict[cmp_idx][obj][0], [])
        #             for e2 in e2s:
        #                 self.triples.append([e1, r, e2])

    def entity_extend(self, words, poss, ddps_dict, idx, ext=[]):
        """
        实体进行左右扩展(主语, 宾语)
        Args:
            words: list, sentence cut, eg. ["依存句法", "分析"] 
            poss:  list, postag of sent, eg. ["n", "v"]
            ddps_dict: list<dict>, ddp of word, eg. [{}, {'ATT': [0]}]
            idx: int, index of words of parser, eg. 32
            ext: list, ids of entity which can extend, eg.[1,2,3]
        Returns:
            entity: str  
        """
        entitys = [self.entity2str(words, poss, ddps_dict, idx, ext)]
        logger.info("ddps_dict[idx] is: {}".format(ddps_dict[idx]))
        if _COO in ddps_dict[idx]:
            idx_coo = ddps_dict[idx][_COO]
            entitys_common = []
            for ic in idx_coo:
                entity = self.entity2str(words, poss, ddps_dict, ic, ext)
                entitys_common.append(entity)
            logger.info("entitys_common is: {}".format(entitys_common))
            return entitys + entitys_common
        return entitys

    def entity2str(self, words, poss, ddps_dict, idx, ext=[]):
        """
        实体进行左右扩展(主语, 宾语)
        Args:
            words: list, sentence cut, eg. ["依存句法", "分析"] 
            poss:  list, postag of sent, eg. ["n", "v"]
            ddps_dict: list<dict>, ddp of word, eg. [{}, {'ATT': [0]}]
            idx: int, index of words of parser, eg. 32
            ext: list, ids of entity which can extend, eg.[1,2,3]
        Returns:
            entity: str  
        """
        entity_ids = self.ddp_rec(words, poss, ddps_dict, idx, ext) + [idx]
        if entity_ids:
            entity_ids.sort()
            entity = "".join([words[i] for i in entity_ids if i < len(words)-1])
        else:
            entity = None
        return entity

    def ddp_rec(self, words, poss, ddps_dict, idx, ext=[]):
        """
        递归, 实体ID进行左右扩展(主语, 宾语)
        Args:
            words: list, sentence cut, eg. ["依存句法", "分析"] 
            poss:  list, postag of sent, eg. ["n", "v"]
            ddps_dict: list<dict>, ddp of word, eg. [{}, {'ATT': [0]}]
            idx: int, index of words of parser, eg. 32
            ext: list, ids of entity which can extend, eg.[1,2,3]
        Returns:
            tuple(list, list, list<object>, list, dict, list<list>) 
        """
        ddp_dic = ddps_dict[idx]
        for _le in _LEFT:
            if _le in ddp_dic:
                for dd_id in ddp_dic[_le]:
                    ext.append(dd_id)
                    self.ddp_rec(words, poss, ddps_dict, dd_id, ext)
        return ext

    def ruler(self, words, poss, ddps_dict, ddps_hds_rels):
        svos = []
        for idx in range(len(poss)):
            if poss[idx]:
                # 抽取以谓词为中心的事实三元组
                child_dict = ddps_dict[idx]
                # 主谓宾
                if "SBV" in child_dict and "VOB" in child_dict:
                    print(child_dict)
                    r = words[idx]
                    e1 = self.entity_extend(words, poss, ddps_dict, child_dict["SBV"][0])
                    e2 = self.entity_extend(words, poss, ddps_dict, child_dict["VOB"][0])
                    svos.append([e1, r, e2])
                # 定语后置，动宾关系
                # print(ddps_hds_rels[idx])
                relation = ddps_hds_rels[idx][0]
                head = ddps_hds_rels[idx][2]
                if relation == "ATT":
                    if "VOB" in child_dict:
                        e1 = self.entity_extend(words, poss, ddps_dict, head - 1)
                        r = words[idx]
                        e2 = self.entity_extend(words, poss, ddps_dict, child_dict["VOB"][0])
                        temp_string = r + e2
                        if temp_string == e1[:len(temp_string)]:
                            e1 = e1[len(temp_string):]
                        if temp_string not in e1:
                            svos.append([e1, r, e2])
                # 含有介宾关系的主谓动补关系
                if "SBV" in child_dict and "CMP" in child_dict:
                    e1 = self.entity_extend(words, poss, ddps_dict, child_dict["SBV"][0])
                    cmp_index = child_dict["CMP"][0]
                    r = words[idx] + words[cmp_index]
                    if "POB" in ddps_dict[cmp_index]:
                        e2 = self.entity_extend(words, poss, ddps_dict, ddps_dict[cmp_index]["POB"][0])
                        svos.append([e1, r, e2])
        return svos

    def detail(self, words, poss, ddps):
        """
        依存句法分析结果详细处理, 获取每个词存在依存关系-每个词
        Args:
            words: list, words of cut-sentence, eg. ["依存句法", "分析"]
            poss: list, Postagger of words, eg. ["n", "v"]
            ddps: pyltp.VectorOfParseResult object, eg. [object(head, relation)...]
        Returns:
            tuple(list, dict, list<list>), eg. (["ATT"],  [{}, {'ATT': [0]}],
                                                [['ATT', '依存句法', 0, 'n', '分析', 1, 'v'], ['HED', '分析', 1, 'v', 'ROOT', -1, 'v']])
        """
        len_words, len_ddps = len(words), len(ddps)
        ddps_hds_rels = []
        ddps_dict = []
        for idx in range(len_words):  # 获取句子中每个词的所有依存关系
            ddp_dic = {}  # 获取一个词的所有依存关系
            for i in range(len_ddps):
                rel = ddps[i].relation
                hd = ddps[i].head
                if hd == idx + 1:  # ddps的索引从1开始
                    if rel in ddp_dic:
                        ddp_dic[rel].append(i)
                    else:
                        ddp_dic[rel] = [i]
            ddps_dict.append(ddp_dic)  # [{}, {'ATT': [0]}]
        rels = [ddp.relation for ddp in ddps]  # 提取依存关系
        hds = [ddp.head for ddp in ddps]  # 提取依存父节点id
        heads = [words[h-1] if h != 0 else "ROOT" for h in hds]
        for i in range(len_words):  # 获取输出结果, 依存关系两两, 按照切词结果排序
            hds_rels = [rels[i], words[i], i, poss[i], heads[i], hds[i]-1, poss[hds[i]-1]]
            ddps_hds_rels.append(hds_rels)
        return rels, ddps_dict, ddps_hds_rels

    def fix_pr(self, ddps_dict):
        """
        补全谓语的并列关系(即关系)的宾语, COO
        Args:
            ddps_dict: ddps_dict: list<dict>, ddp of word, eg. [{}, {'ATT': [0]}]
        Returns:
            ddps_dict
        """

        def fix_coo(i, dic, coos=[]):
            """
            递归查找谓语的并列关系(即关系), COO
            Args:
                ddps_dict: ddps_dict: list<dict>, ddp of word, eg. [{}, {'ATT': [0]}]
                i:  int, position of sign, eg. 2
                coos:  list<int>, store i, eg. [1, 3, 5]
            Returns:
                None
            """
            if _COO in dic[i]:  # 存储 i 和 coo_idx, 后期再过滤
                coos.append(i)
                coo_idx = dic[i].get(_COO)[0]
                coos.append(coo_idx)
                fix_coo(coo_idx, dic, coos)
            else:
                return

        for i in range(len(ddps_dict)):
            coos = []  # 首先递归查找当前 idx 所有谓语的COO
            fix_coo(i, ddps_dict, coos)
            if coos:  # 如果存在则补全
                coos = list(set(coos))
                coos_dict = {}
                for coo_idx in coos:  # 获取谓语COO中可以接的宾语
                    coo_keys = list(ddps_dict[coo_idx].keys())
                    signs_coo = list(set(_OBJ) & set(coo_keys))
                    if signs_coo:
                        for sc in signs_coo:
                            coos_dict[sc] = ddps_dict[coo_idx][sc]
                for coo_idx in coos:  # 更新宾语(全部)
                    ddps_dict[coo_idx].update(coos_dict)

        return ddps_dict

    def base(self, text):
        """
        LTP支持的基础功能, 以及对依存句法分析结果进行处理ddps
        Args:
            text: str, sentence of orginal, eg. "依存句法分析"
        Returns:
            tuple(list, list, list<object>, list, dict, list<list>) 
        """
        words = list(self.seg.segment(text)) # segmentor, seg
        poss = list(self.pos.postag(words))  # pos tagger, pos
        ddps = self.ppd.parse(words,  poss)  # dependency parsing, ddp
        rels, ddps_dict, ddps_hds_rels = self.detail(words, poss, ddps) # ddps explain
        # print(words)
        # print(poss)
        # print(ddps)
        # print(ddps_dict)
        # print(ddps_hds_rels)
        return words, poss, ddps, rels, ddps_dict, ddps_hds_rels

    def spo(self, text):
        """
        LTP支持的三元组抽取(spo)
        Args:
            text: str, sentence of orginal, eg. "依存句法分析"
        Returns:
            tuple(list, list, list<object>, list, dict, list<list>) 
        """
        words, poss, ddps, rels, ddps_dict, ddps_hds_rels = self.base(text)
        triples = self.extract_triple(words, poss, rels, ddps_dict, ddps_hds_rels)
        return triples


if __name__  ==  "__main__":
    trp = Triple(ltp_dir="/OIE/ltp_data_v3.4.0")
    arcs = trp.base("称霸一方、胡作非为的人叫什么蛇？")
    while True:
        print("请输入: ")
        ques = input()
        words, poss, ddps, rels, ddps_dict, ddps_hds_rels = trp.base(ques)
        # sovs = spo.ruler(words, poss, ddps_dict, ddps_hds_rels)
        triples = trp.extract_triple(words, poss, rels, ddps_dict, ddps_hds_rels)
        # print(sovs)
        print(triples)

# [{"VOB": [2],  "WP": [3,  10], "COO": [7]},  {},
#  {"ATT": [1]},  {},  {"RAD": [5]},  {},
#  {"ATT": [4]},  {"SBV": [6],  "VOB": [9]},
#  {},  {"ATT": [8]},  {}]


# [["HED",  "称霸",  0,  "v",  "ROOT",  -1,  "wp"],
#  ["ATT",  "一",  1,  "m",  "方",  2,  "q"],
#  ["VOB",  "方",  2,  "q",  "称霸",  0,  "v"],
#  ["WP",  "，",  3,  "wp",  "称霸",  0,  "v"],
#  ["ATT",  "胡作非为",  4,  "i",  "人",  6,  "n"],
#  ["RAD",  "的",  5,  "u",  "胡作非为",  4,  "i"],
#  ["SBV",  "人",  6,  "n",  "叫",  7,  "v"],
#  ["COO",  "叫",  7,  "v",  "称霸",  0,  "v"],
#  ["ATT",  "什么",  8,  "r",  "蛇",  9,  "n"],
#  ["VOB",  "蛇",  9,  "n",  "叫",  7,  "v"],
#  ["WP",  "?",  10,  "wp",  "称霸",  0,  "v"]]


[{}, {}, {'ATT': [1]},
 {'SBV': [2], 'VOB': [5], 'WP': [6], 'COO': [8]},
 {}, {'ATT': [4]}, {}, {}, {'ATT': [7]}]

['ATT', '李白', 0, 'nh', '人', 2, 'n']
['ATT', '二', 1, 'm', '人', 2, 'n']

['SBV', '人', 2, 'n', '是', 3, 'v']

['HED', '是', 3, 'v', 'ROOT', -1, 'n']
['ATT', '党国', 4, 'n', '精英', 5, 'n']
['VOB', '精英', 5, 'n', '是', 3, 'v']
['WP', '，', 6, 'wp', '是', 3, 'v']
['ATT', '军中', 7, 'nl', '栋梁', 8, 'n']
['COO', '栋梁', 8, 'n', '是', 3, 'v']


[{}, {'SBV': [0], 'RAD': [2], 'VOB': [7]}, {}, {}, {'ATT': [3], 'COO': [6]}, {}, {'WP': [5]}, {'ATT': [4]}]

[['SBV', '李白', 0, 'nh', '歼灭', 1, 'v'],
 ['HED', '歼灭', 1, 'v', 'ROOT', -1, 'n'],
 ['RAD', '了', 2, 'u', '歼灭', 1, 'v'],
 ['ATT', '王百韬', 3, 'nh', '兵团', 4, 'n'],
 ['ATT', '兵团', 4, 'n', '兵团', 7, 'n'],
 ['WP', '、', 5, 'wp', '邱清泉', 6, 'nh'],
 ['COO', '邱清泉', 6, 'nh', '兵团', 4, 'n'],
 ['VOB', '兵团', 7, 'n', '歼灭', 1, 'v']]

[['SBV', '李小茗', 0, 'nh', '上', 1, 'v'],
 ['HED', '上', 1, 'v', 'ROOT', -1, 'n'],
 ['CMP', '得', 2, 'v', '上', 1, 'v'],
 ['RAD', '了', 3, 'u', '得', 2, 'v'],
 ['VOB', '厅堂', 4, 'n', '得', 2, 'v'],
 ['WP', '，', 5, 'wp', '上', 1, 'v'],
 ['COO', '下', 6, 'v', '上', 1, 'v'],
 ['RAD', '得', 7, 'u', '下', 6, 'v'],
 ['RAD', '了', 8, 'u', '下', 6, 'v'],
 ['VOB', '厨房', 9, 'n', '下', 6, 'v']]


[{}, {'SBV': [0], 'COO': [3]}, {}, {'LAD': [2], 'RAD': [4], 'VOB': [5]}, {}, {'COO': [7]}, {}, {'LAD': [6]}]
[['SBV', '李宗仁', 0, 'nh', '喜欢', 1, 'v'],
 ['HED', '喜欢', 1, 'v', 'ROOT', -1, 'nh'],
 ['LAD', '和', 2, 'c', '热爱', 3, 'v'],
 ['COO', '热爱', 3, 'v', '喜欢', 1, 'v'],
 ['RAD', '着', 4, 'u', '热爱', 3, 'v'],
 ['VOB', '蒋介石', 5, 'nh', '热爱', 3, 'v'],
 ['LAD', '和', 6, 'c', '白崇禧', 7, 'nh'],
 ['COO', '白崇禧', 7, 'nh', '蒋介石', 5, 'nh']]


# 李宗仁喜欢、热爱和欣赏李白
[{}, {'SBV': [0], 'COO': [3]}, {}, {'WP': [2], 'COO': [5], 'VOB': [6]}, {}, {'LAD': [4]}, {}]
[['SBV', '李宗仁', 0, 'nh', '喜欢', 1, 'v'],
 ['HED', '喜欢', 1, 'v', 'ROOT', -1, 'nh'],
 ['WP', '、', 2, 'wp', '热爱', 3, 'v'],
 ['COO', '热爱', 3, 'v', '喜欢', 1, 'v'],
 ['LAD', '和', 4, 'c', '欣赏', 5, 'v'],
 ['COO', '欣赏', 5, 'v', '热爱', 3, 'v'],
 ['VOB', '李白', 6, 'nh', '热爱', 3, 'v']]


