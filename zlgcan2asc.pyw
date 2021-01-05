# !/bin/env python3
# coding:utf8
# MAKE BY XUHONG_20170809 

import wx
import os
import re
from zipfile import ZipFile,ZIP_DEFLATED
from time import time as now
from time import sleep
from time import localtime,strftime
import datetime
import chardet
import threading

__author__  = "ZhangXuhong1024 <zhangxuhong1024@qq.com>"
__version__ = "V1.0.1"


def GetEncoding(file_path):
    with open(file_path, 'rb') as f:
        return chardet.detect(f.read(2048))['encoding']

class Message(object):
    Chx    = 1         # CAN通道
    ID     = 0         # CAN_ID
    Tm     = 0.0       # 时间
    Len    = 0         # 数据长度
    Data   = []        # 数据
    Type   = 'd'       # d=数据帧  r=远程帧
    Format = ' '       # 空格=标准帧 x=扩展帧
    Dir    = 'rx'      # rx=接收  tx=发送
    Completed = False  #怕是只填充的部分数据导致出错，故设置了这个FLAG。

class zlgFile(object):
    def __init__ (self,f):
        self._dataNum = 0
        self._lastTimeStamp = 0.0
        self._file = open(f,'r',encoding=GetEncoding(f))
        _ = self._file.readline() # 第一行是表头,没卵用,直接扔了.
        self.lastIndex = 0

    def __del__ (self):
        if not self._file.closed:
            self._file.close()

    def __iter__(self):
        return self
 
    def __next__(self):
        msg = self.GetMessage()
        if msg == None:
            raise StopIteration
        return msg

    def GetMessage (self):
        if self._file.closed:
            return
        can = Message()
        s = self._file.readline()
        if s=='':
            return
        s = re.sub(r",\s*([\da-fA-F]{8})\s*H,\s*",",0x\g<1>,",s)
        s = re.sub(r"[\s,]+",",",s)
        s = re.sub(r",$","",s)
        l = s.split(",")
        #序号
        s = l.pop(0)
        self.lastIndex = int(s)
        #报文方向
        s = l.pop(0)
        if re.match(r"^(Receive)|(接收)$",s):
            can.Dir = 'rx'
        elif re.match(r"^(Send)|(发送)$",s):
            can.Dir = 'tx'
        else:
            return 
        #时间
        s = l.pop(0)
        tm = 0.0
        t = re.match(r"(\d\d):(\d\d):(\d\d)\.(\d\d\d)(\.\d)?",s)
        if t:
            tm  = float(t.group(4)) * 0.001
            tm += float(t.group(3))
            tm += float(t.group(2)) * 60
            tm += float(t.group(1)) * 3600
        elif re.match(r"^0x[\da-fA-F]{1,8}$",s):
            tm = float(int(s,16))
            tm /= 10000.0
        elif re.match(r"^\d{1,8}\.\d{1,8}$",s):
            tm = float(s)
            tm /= 1.0
        if tm <= self._lastTimeStamp:
            can.Tm = self._lastTimeStamp+0.000001
        else:
            can.Tm = tm
        self._lastTimeStamp = can.Tm
        #报文ID
        s = l.pop(0)
        if re.match(r"^(0x)?[\da-fA-F]{1,8}$",s):
            can.ID = int(s,16)
        #类型/格式
        s = l.pop(0)
        if re.match(r"^(Data)|(数据)|(数据帧)$",s):
            can.Type = 'd'
        elif re.match(r"^(Remote)|(远程帧)$",s):
            can.Type = 'r'
        elif re.match(r"^(Extend)|(扩展帧)$",s):
            can.Format = 'x'
        elif re.match(r"^(Standard)|(标准帧)$",s):
            can.Format = ' '
        else:
            return 
        #格式/类型
        s = l.pop(0)
        if re.match(r"^(Data)|(数据)|(数据帧)$",s):
            can.Type = 'd'
        elif re.match(r"^(Remote)|(远程帧)$",s):
            can.Type = 'r'
        elif re.match(r"^(Extend)|(扩展帧)$",s):
            can.Format = 'x'
        elif re.match(r"^(Standard)|(标准帧)$",s):
            can.Format = ' '
        else:
            return
        #长度
        s = l.pop(0)
        if re.match(r"^0x[\da-fA-F]{2}$",s):
            can.Len = int(s,16)
        elif re.match(r"^\d{1,2}$",s):
            can.Len = int(s)
        else:
            return
        #数据
        can.Data = []
        if can.Type == 'd':
            for i in range(can.Len):
                s = l.pop(0)
                if re.match(r'^[\da-fA-F]{2}$',s):
                    can.Data.append(int(s,16))
                else:
                    return
        can.Completed = True 
        self._dataNum += 1
        return can

    def Stop (self):
        if not self._file.closed:
            self._file.close()

class ascFile(object):
    def __init__ (self,f):
        self._dataNum = 0
        self._lastTimeStamp = 0.0
        self._file = open(f,'w')
        tm = localtime()
        #星期月份上下午,通过strftime获取时会变成中文.故另行用字典获取.
        s_tm_mon = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',\
                6:'Jun',7:'Jul',8:'Aug',9:'Sept',10:'Oct',\
                11:'Nov',12:'Dec'}.get(tm.tm_mon)
        s_tm_wday = {0:'Mon',1:'Tues',2:'Wed',3:'Thur',4:'Fri',\
                5:'Sat',6:'Sun'}.get(tm.tm_wday)
        s_tm_ampm = {0:'AM',1:'PM'}.get(0 if tm.tm_hour<13 else 1)
        s = "date {wday} {mon} %m %I:%M:%S {ampm} %Y\nbase hex timestamps absolute\n"
        s = strftime(s, tm)
        s = s.format(wday=s_tm_wday,mon=s_tm_mon,ampm=s_tm_ampm)
        self._file.write(s)
        self._file.flush()

    def __del__ (self):
        if not self._file.closed:
            self._file.close()

    def AddMessage (self, msg):
        if self._file.closed:
            return
        if not type(msg) == type(Message()):
            return
        if msg.Tm <= self._lastTimeStamp:
            msg.Tm = self._lastTimeStamp+0.000001
        candata = ""
        for d in msg.Data:
            candata += '{:0>2x} '.format(d)
        s = r'{tm:<16.6f} {ch} {canid:>8x}{f} {d} {t} {l} {data} '
        out = s.format(tm=msg.Tm, ch = msg.Chx, canid = msg.ID, d = msg.Dir,\
                t = msg.Type, l = msg.Len, f = msg.Format, data = candata )
        self._file.write(out+'\n')
        self._lastTimeStamp = msg.Tm
        self._dataNum += 1

    def Stop (self):
        self._file.write("End Triggerblock ")
        self._file.flush()
        if not self._file.closed:
            self._file.close()

class MyFileDropTarget(wx.FileDropTarget):#声明释放到的目标
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.win = window
        self.filelist = []
    def OnDropFiles(self, x, y, filenames):#释放文件处理函数数据
        self.win.Log("{}个文件被拖放到此处:\n".format(len(filenames), x, y))
        for f in filenames:
            if f not in self.filelist:
                if os.path.isfile(f) and re.match(r"(^.+\.csv$)|(^.+\.txt$)|(^.+\.CSV$)|(^.+\.TXT$)",f):
                    self.win.Log("  新添加: {}\n".format(f))
                    self.filelist.append(f)
                else:
                    self.win.Log("  已忽略: {}\n".format(f))
            else:
                self.win.Log("  已存在: {}\n".format(f))
        self.win.Log("\n")
        return True

class ConverterThread(threading.Thread):
    def __init__(self, window,filelist,opt_onefile,opt_needzip):
        super(ConverterThread, self).__init__()  # 继承
        self.setDaemon(True)  # 设置为守护线程， 即子线程是守护进程，主线程结束子线程也随之结束。
        self.win        = window
        self.opt_onefile= opt_onefile
        self.opt_needzip= opt_needzip
        self.file       = [i for i in filelist]
        self.infiles = []
        self.outfiles = []
        self.outDir     = os.path.dirname(self.file[0])

    def run(self):
        time_start = now()
        conv_file_list = []
        #检查文件是否正确读取,并确定转换文件的先后顺序.
        self.win.Log ("1-检测文件是否正确...\n")
        for f in self.file:
            if self.outDir != os.path.dirname(f):
                s = "    不允许存在多个目录的数据,请重新选择数据文件!\n"
                self.win.Log (s)
                self.win.Log ("1-检测发现异常,退出转换!\n\n")
                self.win.FinishConverter()
                return
        for f in self.file:
            try:
                zlg = zlgFile(f)
                if zlg.GetMessage() == None:
                    raise Exception("数据读不了")
                zlg.Stop()
                conv_file_list.append((f,zlg.lastIndex))
            except Exception:
                self.win.Log ("    文件有误: {}\n".format(os.path.basename(f)))
        if len(conv_file_list) == 0:
            self.win.Log ("1-检测完成,没有数据文件需要被转换的!\n\n".format(len(self.file)))
            self.win.FinishConverter()
            return
        if self.opt_onefile:
            conv_file_list.sort(key=lambda x:x[1])
        self.file = [i[0] for i in conv_file_list]
        if self.opt_onefile:
            self.outfiles.append(self.file[0] + r'.asc')
        self.win.Log ("1-检测完成,如下{}个数据文件将被转换:\n".format(len(self.file)))
        for f in self.file:
            self.win.Log ("    {}\n".format(os.path.basename(f)))
        sleep(3)
        #转换为ASC文件.
        i=0
        l=len(self.file)
        self.win.Log ("2-开始转换CAN数据为ASC格式...\n")
        if self.opt_onefile:
            fd = ascFile(self.outfiles[0])
        for f in self.file:
            i += 1
            self.win.Log ("2-({}/{})当前正在转换文件: {}\n".format(i,l,os.path.basename(f)))
            try:
                if not self.opt_onefile:
                    fd = ascFile(f+r'.asc')
                    self.outfiles.append(f + r'.asc')
                fs = zlgFile(f)
                for msg in fs:
                    fd.AddMessage(msg)
                fs.Stop()
                if not self.opt_onefile:
                    fd.Stop()
                self.win.Log ("2-({}/{})转换结束,本次共转换CAN数据{}条!\n".format(i,l,fs._dataNum))
            except Exception:
                self.win.Log ("2-({}/{})转换转换出错了!\n".format(i,l,os.path.basename(f)))
        self.win.Log ("2-转换CAN数据完成!\n")
        self.file.clear()
        try:
            fd.Stop()
        except Exception:
            pass
        #打包成ZIP文件.
        if self.opt_needzip:
            i=0
            l=len(self.outfiles)
            outfile = os.path.join(self.outDir, "out.zip")
            self.win.Log ("3-开始打包成zip文件...\n")
            with ZipFile(outfile, "w",ZIP_DEFLATED,compresslevel=9) as fz:
                for f in self.outfiles:
                    i += 1
                    self.win.Log ("3-({}/{})当前正在打包文件: {}\n".format(i,l,os.path.basename(f)))
                    fz.write(f, os.path.basename(f))
                    os.remove(f)
            self.win.Log ("3-打包zip文件完成!\n")
        time_end = now()
        self.win.Log('\n')
        self.win.Log ("全部文件转换结束,共耗时{}秒！\n".format(time_end-time_start))
        self.win.Log ("输出文件如下:\n".format(time_end-time_start))
        if self.opt_needzip:
            outfile = os.path.join(self.outDir, "out.zip")
            self.win.Log ("  {}\n".format(outfile))
        else:
            for f in self.outfiles:
                self.win.Log ("    {}\n".format(f))
        self.win.Log('\n')
        self.win.FinishConverter()

class MainFrame (wx.Frame):
    def __init__ (self):
        wx.Frame.__init__(self, None, -1, "CANtest数据转CANoe数据", size=(600,400))
        self.panel = wx.Panel(self, -1)
        self.SetMinSize((600,400))
        str_zlg2ascVer = "当前zlgcan2asc脚本版本为：" + __version__ 
        self.label = wx.StaticText(self.panel, -1, str_zlg2ascVer)
        s = "请把需要转换的CSV数据文件或者TXT数据文件,拖入此框框中,\n"
        s += "然后点击“开始转换”按钮!\n\n" 
        self.text = wx.TextCtrl(self.panel, -1, s, style=wx.TE_MULTILINE|wx.HSCROLL)
        self.df = MyFileDropTarget(self)#将文本控件作为释放到的目标
        self.text.SetEditable(False)
        self.text.SetDropTarget(self.df)
        s1 = "全部转换结果合并到同一个asc文件中.(适用于实时记录文件合并.)"
        self.onefile = wx.CheckBox(self.panel, -1, s1)
        s2 = "输出的asc文件顺便打包成zip压缩文件.(减少输出文件大小.)"
        self.needzip = wx.CheckBox(self.panel, -1, s2)
        self.button = wx.Button(self.panel, -1, "开始转换")
        self.Bind(wx.EVT_BUTTON, self.OnConverterButton,self.button)
        self.button.SetDefault()
        # setup the layout with sizers
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.label,   0, wx.ALL, 5)
        sizer.Add(self.text,    1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(self.onefile, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(self.needzip, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(self.button,  0, wx.EXPAND|wx.ALL, 5)
        self.panel.SetSizer(sizer)

    def Log (self,txt):
        self.text.AppendText(txt)
        
    def FinishConverter (self):
        self.onefile.Enable()
        self.needzip.Enable()

    def OnConverterButton (self, event):
        if hasattr(self, "Conv") and self.Conv.is_alive():
            self.Log("正在转换中,莫急躁!\n")
            return
        if len(self.df.filelist) == 0:
            self.Log("请把需要转换的数据文件,拖入此框框中!\n\n")
            return
        self.onefile.Disable()
        self.needzip.Disable()
        opt_onefile = self.onefile.GetValue()
        opt_needzip = self.needzip.GetValue()
        self.Conv= ConverterThread(self, self.df.filelist, opt_onefile, opt_needzip)
        self.Conv.start()
        self.df.filelist.clear()


if __name__ == "__main__":
    app = wx.App()
    frame = MainFrame()
    frame.Show()
    app.MainLoop()

# 命令行,不带GUI那种.
# if __name__ == "__main__":
#     str_zlg2ascVer = "当前zlgcan2asc脚本版本为：" + __version__ 
#     print (str_zlg2ascVer)
#     time_start = now()
#     filelist = []
#     for f in os.listdir('.'):
#         if os.path.isfile(f) and re.match(r"(^.+\.csv$)|(^.+\.txt$)|(^.+\.CSV$)|(^.+\.TXT$)",f): 
#             filelist.append(f)
#     print ("当前目录下CSV文件和TXT文件，共查找到{}个！".format(len(filelist)))
#     for f in filelist:
#         print ("正在从文件{}转换CAN数据到文件{}中...".format(f,f+r'.asc'))
#         try:
#             fs = zlgFile(f)
#             fd = ascFile(f+r+'.asc')
#             for msg in fs:
#                 fd.AddMessage(msg)
#             fs.Stop()
#             fd.Stop()
#             print ("转换结束，本次共转换CAN数据{}条！".format(fd._dataNum))
#         except Exception:
#             print ("转换转换出错了！")
#     time_end = now()
#     print ("全部文件转换结束，共耗时{}秒！".format(time_end-time_start))
#     print ("请点击关闭按键关闭窗口，或30秒后自动退出！")
#     sleep(30)
