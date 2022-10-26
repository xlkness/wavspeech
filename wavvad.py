import logging
import handlefile
from multiprocessing import cpu_count
import sys,os
import time
import queue
import threading
import signal
from pathlib import Path

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
        return L  

log = logging.getLogger('null')

def init():
    level = logging.DEBUG # DEBUG/INFO/WARNING/ERROR/CRITICAL
    format='[%(levelname)s] %(asctime)s %(filename)s.%(funcName)s:%(lineno)d | %(message)s'
    format='[%(levelname)s][%(asctime)s][%(filename)s.%(funcName)s:%(lineno)d] %(message)s'
    datefmt='%Y%m%d%I%M%S'
    logging.basicConfig(level=level, format=format, datefmt=datefmt)
    log = logging.getLogger("logger1")

exitFlag = False

class handleFileThread(threading.Thread):
    def __init__(self, queueLock, taskQueue, outpath):
        threading.Thread.__init__(self)
        self.queueLock = queueLock
        self.taskQueue = taskQueue
        self.outpath = outpath
    def run(self):
        # log.debug("thread running...")
        self.handle_file()
    def handle_file(self):
        while not exitFlag:
            self.queueLock.acquire()
            if not self.taskQueue.empty():
                data = self.taskQueue.get()
                self.queueLock.release()
                handlefile.handle_file(data, self.outpath)
            else:
                self.queueLock.release()
                # log.info('线程任务处理完毕，退出')
                return

# appdata\roaming\python\python36\site-packages\PyInstaller\__main__.py -F __main__.py -n wavvad
# appdata\roaming\python\python36\site-packages\PyInstaller\__main__.py -F wavvad.spec -n wavvad
# pipreqs . --encoding=utf8 --force
if __name__ == '__main__':
    init()
    path = 'wav/bad/344048.wav'
    path = 'wav/good/1336482.wav'
    path = 'wav/normal/335305.wav'
    path = 'wav/normal'
    # path = os.path.join(rootPath, 'wav')
    outpath = os.path.join(rootPath, 'output')

    startTime = time.time()

    wav_files=files_name(path) #获取文件夹内的所有语音文件
    if len(wav_files) <= 0:
        log.warn('目录%s下没有找到音频文件', path)
        exit(1)
    
    if not Path(outpath).is_dir():
        os.mkdir(outpath)

    log.info("获取到目录{}下文件数量{}个".format(path, len(wav_files)))

    threadsNum = 1
    if len(wav_files) > cpu_count() * 2:
        log.info("文件数量{}过多，开启两倍cpu核心{}线程加速".format(len(wav_files), cpu_count()*2))
        threadsNum = cpu_count()*2
  
    queueLock = threading.Lock()
    taskQueue = queue.Queue(len(wav_files))

    # 填充并行任务
    for filename in wav_files:
        taskQueue.put(filename)
        # log.debug("file name:%s", filename)

    allThreads = []
    for i in range(threadsNum):
        thread = handleFileThread(queueLock, taskQueue, outpath)
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
        exit(1)