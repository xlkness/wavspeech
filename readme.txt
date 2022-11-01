1.介绍
wav音频文件标记人声段，将人声段前后噪点去除，并截取人声段前后0.6s保留

2.使用方法
原始音频放在wav目录，支持各种目录/文件嵌套，双击运行，生成文件按原始路径放在output，跳过的文件放在skip目录，并记录出错原因。
注意：程序运行目录必须放置在英文路径下，不过wav目录内可以英文、中文随意放置。

3.依赖版本
python3.6.4:
* torch==1.10.1
* torchaudio==0.10.1
python3.7:
* torch==1.12.0
* torchaudio==0.12.0

4.打包
pyinstaller wavvad.spec或者pyinstaller -F wavvad.py
注意：wavvad.spec不要随意改动、覆盖，因为里面datas打包了依赖库，以及去除了多余打包的库防止运行报警告
