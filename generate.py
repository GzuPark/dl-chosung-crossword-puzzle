import argparse
import datetime
import os
import random
import time

from utils import Config, pickle_load, safe_pickle_dump, preview


def kor_char_chosung_decompose(x):
    """
    https://github.com/naver/ai-hackathon/blob/ai_hackathon_1st/missions/examples/movie-review/example/kor_char_parser.py
    """
    cho = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"  # len = 19

    if x < ord('가') or x > ord('힣'):
        if x == ord(' '):
            return chr(x)
        else:
            raise ValueError('가 - 힣 범위에 있는 글자가 아닙니다. -> [{}]'.format(chr(x)))
    x = (x - ord('가')) // 28 // 21
    return cho[x]


def read_database(filepath):
    with open(filepath, 'r') as f:
        words = f.readlines()
    words = [word.replace('\n', '').rstrip() for word in words]
    return words


def extract_chosung(words):
    cho = []
    for word in words:
        temp = []
        for letter in word:
            temp.append(kor_char_chosung_decompose(ord(letter)))
        cho.append(''.join(temp))
    return cho


def select_word(corpus, dim):
    random_state = random.randint(0, len(corpus) - 1)
    selected = {
        'guide': corpus[random_state]['guide'],
        'word': corpus[random_state]['word'],
        'grid': [random.randint(0, dim[0] - 1), random.randint(0, dim[1] - 1)],
        'direction': 'V' if random.random() > 0.5 else 'H'
    }
    return selected


def get_valid_words(selected, env, corpus):
    col = selected['grid'][0]
    row = selected['grid'][1]
    guide = selected['guide']
    word = selected['word']
    direction = selected['direction']

    if (direction == 'V' and col + len(word) > len(env)) or (direction == 'H' and row + len(word) > len(env[0])):
        return [False, []]

    for idx, letter in enumerate(list(word)):
        if direction == 'V':
            if (env[col+idx][row] != 0) and (env[col+idx][row] != letter):
                return [False, []]
        elif direction == 'H':
            if (env[col][row+idx] != 0) and (env[col][row+idx] != letter):
                return [False, []]

    if direction == 'V':
        if (col > 0) and (env[col-1][row] != 0):
            return [False, []]
        elif (col + len(word) < len(env)) and (env[col+len(word)][row] != 0):
            return [False, []]
    elif direction == 'H':
        if (row > 0) and (env[col][row-1] != 0):
            return [False, []]
        elif (row + len(word) < len(env[0])) and (env[col][row+len(word)] != 0):
            return [False, []]

    new_words = []
    for idx, letter in enumerate(list(word)):
        if direction == 'V':
            if (env[col+idx][row] == 0) and ((row > 0) and (env[col+idx][row-1] != 0) or (row < len(env) - 1) and (env[col+idx][row+1] != 0)):
                _word = [letter]

                l_idx = 1
                while (row + l_idx < len(env[0])) and (env[col+idx][row+l_idx] != 0):
                    _word.append(env[col+idx][row+l_idx])
                    l_idx += 1

                l_idx = 1
                while (row - l_idx > 0) and (env[col+idx][row-l_idx] != 0):
                    _word.insert(0, env[col+idx][row-l_idx])
                    l_idx += 1

                _word = ''.join(_word)
                if _word not in [element['word'] for element in corpus]:
                    return [False, []]

                temp = {
                    'direction': direction,
                    'guide': guide,
                    'word': _word,
                    'grid': [row-l_idx+1, col+idx]
                }
                new_words.append(temp)
        elif direction == 'H':
            if (env[col][row+idx] == 0) and ((col > 0) and (env[col-1][row+idx] != 0) or (col < len(env[0]) - 1) and (env[col+1][row+idx] != 0)):
                _word = [letter]

                l_idx = 1
                while (col + l_idx < len(env)) and (env[col+l_idx][row+idx] != 0):
                    _word.append(env[col+l_idx][row+idx])
                    l_idx += 1

                l_idx = 1
                while (col - l_idx > 0) and (env[col-l_idx][row+idx] != 0):
                    _word.insert(0, env[col-l_idx][row+idx])
                    l_idx += 1

                _word = ''.join(_word)
                if _word not in [element['word'] for element in corpus]:
                    return [False, []]

                temp = {
                    'direction': direction,
                    'guide': guide,
                    'word': _word,
                    'grid': [row+idx, col-l_idx+1]
                }
                new_words.append(temp)
    return [True, new_words]


def add_word_to_env(selected, env):
    col = selected['grid'][0]
    row = selected['grid'][1]
    word = selected['word']

    if selected['direction'] == 'V':
        for idx, letter in enumerate(list(word)):
            env[col+idx][row] = letter
    elif selected['direction'] == 'H':
        env[col][row:row+len(list(word))] = list(word)
    return env


def generate_environment(corpus, dim, timeout, limited_capacity):
    env = [x[:] for x in [[0] * dim[1]] * dim[0]]
    added_words = []
    capacity = 0

    start_time = time.time()

    while (capacity < limited_capacity) and (time.time() - start_time < timeout):
        candidates = []
        i = 0
        new_words = []
        while (not candidates) or (candidates and (i < 100)):
            valid = False
            while not valid:
                new = select_word(corpus, dim)
                valid, new_words = get_valid_words(new, env, corpus)
                i += 1
            candidates.append(new)

        candidates = sorted(candidates, key=lambda x: len(x['word']), reverse=True)
        new = candidates[random.randint(0, len(candidates) - 1)]

        if new['word'] not in [e['word'] for e in added_words]:
            env = add_word_to_env(new, env)
            added_words.append(new)

            capacity = 1 - (sum(x.count(0) for x in env) / (dim[0] * dim[1]))
            print('문제에 "{}" 추가 (용량: {:2.1f}%)'.format(new['word'], capacity*100))

    print('문제 구성 완료 (용량: {:2.1f}%)'.format(capacity*100))
    return {'env': env, 'words': added_words}


def save_problem(problem, dim, db_path):
    print()
    do_save = input('문제를 저장하시겠습니까? (y/n) : ')
    if do_save.lower() in ['y', 'yes']:
        db = pickle_load(db_path)
        _KST = datetime.timezone(datetime.timedelta(hours=9))
        _id = datetime.datetime.now(_KST).strftime('%Y%m%d%H%M%S')
        _problem = {
            'grid': dim,
            'env': problem['env'],
            'words': problem['words']
        }
        db[_id] = _problem
        safe_pickle_dump(db, db_path)
        print('문제 저장 완료! (ID: {})'.format(_id))


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', type=str, default='example.txt')
    parser.add_argument('-d', '--dim', type=int, nargs='+', default=[10, 10])
    parser.add_argument('-t', '--timeout', type=int, default=5)
    parser.add_argument('-c', '--capacity', type=float, default=0.5)
    args = parser.parse_args()

    data_path = Config.data_path
    args.file_path = os.path.join(data_path, args.file)
    args.db_path = Config.db_path
    return args


def main():
    args = get_args()
    words = read_database(args.file_path)
    chosung = extract_chosung(words)
    corpus = [{'guide': w, 'word': c} for w, c in zip(words, chosung)]
    problem = generate_environment(corpus, args.dim, args.timeout, args.capacity)
    preview(problem)
    save_problem(problem, args.dim, args.db_path)


if __name__ == '__main__':
    main()
