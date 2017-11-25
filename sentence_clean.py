import scipy.io
import numpy as np
import os
import sys
from dependency_parse import *
from config_environment import *

def saveObject(object_file, object):
    with open(object_file, 'wb+') as f:
        pickle.dump(object, f)

def loadObject(object_file):
    with open(object_file, 'rb+') as f:
        return pickle.load(f)



def format_line(line):
    # This will take in a raw input sentence and return [[element strings], [indicies of elements], [sentence with elements removed]]
    words = line.split(' ')
    
    e1detagged = []
    e2detagged = []
    rebuilt_line = ''
    count = 1 # 对单词的位置进行标记，从1开始
    for word in words:
        # if tagged at all
        if word.find('<e') != -1 or word.find('</e') != -1:
            # e1 or e2
            if word[2] == '1' or word[word.find('>')-1] == '1':
                # remove tags from word for 
                e1detagged = get_word(words, word)
                e1detagged.append(count)
                # replace and tac back on . at end if needed
                word = replace_word(word)
            else:
                e2detagged = get_word(words, word)
                e2detagged.append(count)
                word = replace_word(word)
        rebuilt_line += ' ' + word
        # 处理关系的数据
        first_char = word[0]
        last_char = word[len(word)-1]
        if first_char == '(' or last_char == ')' or last_char == ',':
            count += 1
        count += 1
    rebuilt_line = rebuilt_line[1:len(rebuilt_line)]
    rebuilt_line += '\n'
    return [[e1detagged[0], e2detagged[0]], [e1detagged[1], e2detagged[1]], [e1detagged[2], e2detagged[2]], rebuilt_line]

def get_word(words, word):
    if end_two_words(word):
        return [replace_word(word, False), 1]
    else:
        return [replace_word(word, False), 0]

def replace_word(word, should_end_sentence = True):
    word_list = word.split('</')
    end_sentence = ''
    if len(word_list) == 2 and len(word_list[len(word_list)-1]) != 3:
        end = word_list[len(word_list)-1]
        end_sentence += end[end.find('>')+1:len(end)]
    word_list = word_list[0].split('>')
    new_word = word_list[len(word_list)-1]
    if should_end_sentence:
        new_word += end_sentence
    return new_word

# if this has a two or more words ex. <e2>fast cars</e2>
def end_two_words(word):
    return word.find('<e') == -1



# 对一个entity的位置进行矫正
def correct_single_index(dependency, entity, id):
    index = 0
    min_sep = 99999
    def last_index(string, char):
        id = -1
        for i in range(0, len(string)):
            if string[i] == char:
                id = i
        return id

    for i in range(0, len(dependency)):
        str = dependency[i]
        str2 = re.split("[()]", str)
        str3 = str2[1].split(", ")
        word1_sep = last_index(str3[0], "-")
        word2_sep = last_index(str3[1], "-")

        word1 = str3[0][:word1_sep]
        word1_index = int(str3[0][word1_sep+1:])
        word2 = str3[1][:word2_sep]
        word2_index = int(str3[1][word2_sep+1:])

        if word1.lower() == entity.lower() and (abs(word1_index-id))<min_sep:
            min_sep = abs(word1_index-id)
            index = word1_index
        if word2.lower() == entity.lower() and (abs(word2_index-id))<min_sep:
            min_sep = abs(word2_index-id)
            index = word2_index
    if index == 0:
        print(dependency)
        print(entity)
        print(id)
        #raise IOError("Something wrong")
    print(min_sep)
    return index

def get_exact_index(dependency_result, entity_string, entity_id):
    # 使用最近邻原则进行位置矫正，以stanford corenlp的位置为标准
    for i in range(0, len(dependency_result)):
        #print(dependency_result[i], entity_string[i][0], entity_id[i][0])
        #print(dependency_result[i], entity_string[i][1], entity_id[i][1])
        #print(i)
        entity_id[i][0] = correct_single_index(dependency_result[i], entity_string[i][0], entity_id[i][0])
        entity_id[i][1] = correct_single_index(dependency_result[i], entity_string[i][1], entity_id[i][1])
    return entity_id

def pre_process(file, cat_map):
    # parameters to return
    entity_strings = []  # the entity name
    entity_ind = []  # the index of the elements
    sentence_label = []
    raw_sentences = []

    sentences = open(file, 'r')
    line = sentences.readline()
    while True:
        # 空行或者数字行跳出循环
        while (line != '' and not line[0].isdigit()):
            line = sentences.readline()
        if line == '':
            break
        line = line[line.find('"')+1:len(line)-3]  # 保留到句号前一位

        format_output = format_line(line)
        line = format_output[3]
        entity_strings.append(format_output[0])
        entity_ind.append(format_output[2])
        raw_sentences.append(line[:-1] + '.')

        line = sentences.readline()
        if (line != '' and not line[0].isdigit()):
            category = line
            # use dictionary to get sentence label
            sentence_label.append(cat_map.get(category.strip()))
            line = sentences.readline()  # 跳过comment这一行
    sentences.close()

    return entity_strings, entity_ind, sentence_label, raw_sentences

def get_dependency(sentences, opt_options="basicDependencies"): # basicDependencies / treeDependencies
    dependency_results = []
    p = Parse(opt_options=opt_options)
    for i in range(0, len(sentences)):
        # 原始数据中的句子格式存在一定的错误，因此会有一些解析错误
        # 用下面的方法来弥补一下, 去掉最后一个. 补充为" .\n"
        # 结果中统计过，能够保证最后一个字符为"."
        # 没想到别的办法，这样子做不会出错，但是效率非常低，不如用java来实现
        sent = sentences[i]
        dependency_result = p.sentence_dependency_parse(sent)
        rst = []
        for dep in dependency_result:
            if dep != "":
                rst.append(dep)
        dependency_results.append(rst)
    return dependency_results

def get_sdp_path(entity_strings, entity_ind, dependency):
    sdp_paths = []
    assert len(entity_strings) == len(entity_ind)
    for i in range(0, len(entity_strings)):
        sdp_obj = ShortestDepenencyPath()
        dependency_obj = sdp_obj.change_format(dependency[i])
        sdp_path = sdp_obj.get_shortest_dependent_path(entity_strings[i][0], entity_ind[i][0],
                                                       entity_strings[i][1], entity_ind[i][1],
                                                       dependency_obj, True)
        sdp_paths.append(sdp_path)
    return sdp_paths

def get_sentence_process():
    # 建立好关系的映射
    cat_map = create_cat_map(cat_names)

    # 解析出原始的句子
    train_data_file = "data/TRAIN_FILE.TXT"
    test_data_file = "data/TEST_FILE_FULL.TXT"
    entity_strings_train, entity_ind_train, sentence_label_train, raw_sentences_train = \
        pre_process(train_data_file, cat_map)
    entity_strings_test, entity_ind_test, sentence_label_test, raw_sentences_test = \
        pre_process(test_data_file, cat_map)

    """
    # 获取依存分析结果(时间较长，因此缓存)
    if not os.path.exists("data/dep_rsts_train.pkl"):
        dep_rsts_train = get_dependency(raw_sentences_train)
        saveObject("data/dep_rsts_train.pkl", dep_rsts_train)
    else:
        dep_rsts_train = loadObject("dep_rsts_train.pkl")

    if not os.path.exists("data/dep_rsts_test.pkl"):
        dep_rsts_test = get_dependency(raw_sentences_test)
        saveObject("data/dep_rsts_test.pkl", dep_rsts_test)
    else:
        dep_rsts_test = loadObject("dep_rsts_test.pkl")

    # 对entity的位置索引进行矫正
    entity_ind_train = get_exact_index(dep_rsts_train, entity_strings_train, entity_ind_train)
    entity_ind_test = get_exact_index(dep_rsts_test, entity_strings_test, entity_ind_test)
    # 获取最短依存路径
    sdp_rsts_train = get_sdp_path(entity_strings_train, entity_ind_train, dep_rsts_train)
    sdp_rsts_test = get_sdp_path(entity_strings_test, entity_ind_test, dep_rsts_test)
    """

    sdp_rsts_train = loadObject("data/sdp_data/generate_by_java/sdp_rsts_train.pkl")
    sdp_rsts_test = loadObject("data/sdp_data/generate_by_java/sdp_rsts_test.pkl")

    return cat_map, sentence_label_train, sentence_label_test, sdp_rsts_train, sdp_rsts_test





