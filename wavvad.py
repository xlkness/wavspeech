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
import torch

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
        model, utils = torch.hub.load(repo_or_dir='vad',model='silero_vad',source='local', onnx=False)
        # model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',model='silero_vad', onnx=USE_ONNX)
        (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils
        self.handle_file(model, utils)
    def handle_file(self, model, utils):
        while not exitFlag:
            self.queueLock.acquire()
            if not self.taskQueue.empty():
                (no, file) = self.taskQueue.get()
                self.queueLock.release()
                err_msg = handlefile.handle_file(model, utils, no, self.count, file, self.srcpath, self.outpath, 650, True)
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
# pyinstaller -F .\wavvad.spec --log-level WARN -c --noconfirm
if __name__ == '__main__':
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
        threadsNum = 1
  
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