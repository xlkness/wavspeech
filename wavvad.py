import logging
import handlefile
from multiprocessing import cpu_count
import sys,os
import time
import queue
import threading
import signal
from pathlib import Path
import global_val
import configparser as configparser

# rootPath = os.path.dirname(os.path.abspath(__file__))
rootPath = os.path.dirname(os.path.realpath(sys.argv[0]))

#获取输入文件夹内的所有wav文件，并返回文件名全称列表
def files_name(file_dir):
    L = []
    if not Path(file_dir).is_dir():
        return L
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if os.path.splitext(file)[1].lower() == '.wav':
                filename=os.path.join(root, file)
                # print(get_label(filename))
                L.append(filename)
        for dir in dirs:
            L = L + (files_name(dir))
    return L  

fix_src_path = 'wav'
path = os.path.join(rootPath, fix_src_path)
outpath = os.path.join(rootPath, 'output')
skippath = os.path.join(rootPath, 'skip')
try:
    os.makedirs(outpath)
except:
    pass

try:
    os.makedirs(skippath)
except:
    pass

# log_record = open(os.path.join(outpath, 'process.log'), 'w')
skip_record = open(os.path.join(outpath, 'skip_records.txt'), 'w')

def init():
    level = logging.DEBUG # DEBUG/INFO/WARNING/ERROR/CRITICAL
    format='[%(levelname)s] %(asctime)s %(filename)s.%(funcName)s:%(lineno)d | %(message)s'
    format='[%(levelname)s][%(asctime)s][%(filename)s.%(funcName)s:%(lineno)d] %(message)s'
    datefmt='%Y%m%d%I%M%S'
    logfile = os.path.join(outpath, 'process.log')
    handler = logging.FileHandler(logfile, 'w', encoding="UTF-8")
    logging.basicConfig(level=level, format=format, datefmt=datefmt)

    global log
    log = logging.getLogger("logger1")
    log.addHandler(handler)
    global_val.__init(log)
    
exitFlag = False
retainDura = 650 # 除人声段外，前后保留的静音段时长（ms）

# 是否使用webrtc检查出来的段修正机器学习得到的人声段，例如webrtc检测到100-1000为声音段，
# 机器学习是200-800，则最后人声会被修正为100-800（修正前一部分，保留后一部分，测试到机器学习在前段有异常，后段比webrtc效果好些）
webrtcCorrectSpeech = True

class handleFileThread(threading.Thread):
    def __init__(self, queueLock, taskQueue, srcpath, outpath, count):
        threading.Thread.__init__(self)
        self.queueLock = queueLock
        self.taskQueue = taskQueue
        self.srcpath = srcpath
        self.outpath = outpath
        self.count = count
    def run(self):
        # log.debug("thread running...")
        self.handle_file()
    def handle_file(self):
        while not exitFlag:
            self.queueLock.acquire()
            if not self.taskQueue.empty():
                (no, file) = self.taskQueue.get()
                self.queueLock.release()
                err_msg = handlefile.handle_file(no, self.count, file, self.srcpath, self.outpath, retainDura, webrtcCorrectSpeech)
                if err_msg != '':
                    # 另存文件
                    f = open(file, 'rb')
                    content = f.read()
                    f.close()
                    baseName = os.path.basename(file)
                    fullOutPath = os.path.join(skippath, baseName)
                    f = open(fullOutPath, 'wb+')
                    f.write(content)
                    f.close()
                    log.info('转存跳过文件[{}]成功'.format(fullOutPath))
            else:
                self.queueLock.release()
                # log.info('线程任务处理完毕，退出')
                return

# appdata\roaming\python\python36\site-packages\PyInstaller\__main__.py -F __main__.py -n wavvad
# appdata\roaming\python\python36\site-packages\PyInstaller\__main__.py -F wavvad.spec -n wavvad
# pipreqs . --encoding=utf8 --force
if __name__ == '__main__':
    configFile = 'properties.txt'
    configFilePath = os.path.join(rootPath, configFile

    if Path(configFilePath).is_file():
        cf = configparser.ConfigParser()
        cf.read(configFilePath)
        kvs = dict(cf.items("default"))
        dura = int(kvs['retain_dura'])
        isCorrect = bool(kvs['webrtc_correct_speech'])
        retainDura = dura
        webrtcCorrectSpeech = isCorrect

    init()

    

    startTime = time.time()

    wav_files=files_name(path) #获取文件夹内的所有语音文件
    if len(wav_files) <= 0:
        log.warn('目录%s下没有找到音频文件', path)
        os._exit(1)
    
    if not Path(outpath).is_dir():
        os.mkdir(outpath)

    log.info("获取到目录{}下文件数量{}个".format(path, len(wav_files)))

    threadsNum = 1
    if len(wav_files) > cpu_count() * 2:
        log.info("文件数量{}过多，开启两倍cpu核心{}线程加速".format(len(wav_files), cpu_count()*2))
        threadsNum = cpu_count()*2
        # threadsNum = 1
  
    queueLock = threading.Lock()
    taskQueue = queue.Queue(len(wav_files))

    # 填充并行任务
    i = 0
    for filename in wav_files:
        i += 1
        taskQueue.put((i, filename))
        # log.debug("file name:%s", filename)

    allThreads = []
    for i in range(threadsNum):
        thread = handleFileThread(queueLock, taskQueue, path, outpath, len(wav_files))
        thread.start()
        allThreads.append(thread)

    try:
        while not taskQueue.empty():
            time.sleep(1)

        endTime = time.time()

        for t in allThreads:
            t.join()

        log.info("处理目录{}下文件数量{}个，输出目录：{}，总耗时：{:d}ms".format(path, len(wav_files), outpath, int((endTime-startTime)*1000)))

        time.sleep(5)
    except KeyboardInterrupt:
        log.info("接收到停止信号，退出程序")
        exitFlag = True
        os._exit(1)