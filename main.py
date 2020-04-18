from keras.preprocessing.image import img_to_array
from object_detection.utils import label_map_util
from pypylon import genicam, pylon
from PIL import Image, ImageTk
from openpyxl import Workbook
import keras.backend as K
import tensorflow as tf
from _thread import *
import tkinter as tk
import numpy as np
import threading
import datetime
import binascii
import imutils
import pymysql
import socket
import pickle
import glob
import time
import cv2
import gc
import os
import re

config = tf.ConfigProto()
config.gpu_options.allow_growth = True
sess = tf.Session(config=config)

# 바탕화면 경로 변수 설정
BASE_PATH = os.getcwd()
DESKTOP = '/'.join(BASE_PATH.split(os.path.sep)[:-1])

# tk 인스턴스 생성(gui)
root = tk.Tk()

# 기본 상태표시줄을 override
# root.overrideredirect(True)

num_classes = 10
min_confidence = 0.9
 

# 바탕화면 폴더로 컴퓨터 번호판단
COMM = 0
for i in range(5):
    if os.path.isdir(f'{DESKTOP}/COMM{i}'):
        COMM = i


# PLC ip : 1호라인 - 10.10.4.21 / 2호라인 - 10.10.4.22
HOST = f'10.10.4.2{(COMM+1)//2}'
# HOST = 'localhost' # test
PORT = 4000 + (COMM + 1) % 2


SERIAL = ['23301052', '23219221', '23301073', '23301086']
camSerial = SERIAL[COMM - 1]

# camSerial = '23301072' # test

print(HOST, PORT, camSerial)
# create a context manager that makes this model the default one for
# executio

#모델 위치 변경 필요
#------------------------------------------------------
dataPath = DESKTOP+'/내장형USB/이미지'
partialPath = DESKTOP + '/내장형USB/분할이미지'
insresPath = DESKTOP+'/내장형USB/검증결과'
excelPath = DESKTOP+'/내장형USB/엑셀'
CIM = DESKTOP+'/내장형USB/Cim'
#------------------------------------------------------
FONT = ("gothic", 16, 'bold')
LFONT = ("gothic", 22, 'bold')
BFONT = ("gothic", 34, 'bold')

labelMap = [0, 2, 5, 7, 1, 4, 6, 9]
# print(BASE_PATH, DESKTOP)


def imread(filename, flags=cv2.IMREAD_COLOR, dtype=np.uint8):
    try: 
        n = np.fromfile(filename, dtype) 
        img = cv2.imdecode(n, flags) 
        return img 
    except Exception as e: 
        print(e) 
        return None


def imwrite(filename, img, params=None):
    try:
        ext = os.path.splitext(filename)[1]
        result, n = cv2.imencode(ext, img, params)

        if result:
            with open(filename, mode='w+b') as f:
                n.tofile(f)
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False


class MainFrame(tk.Frame):
    #변수 선언
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        # TK Image Variables
        self.main_frame_img = ImageTk.PhotoImage(file = 'bg/bg.png')
        self.main_frame_ng = ImageTk.PhotoImage(file = 'bg/ng.png')
        self.main_frame_ok = ImageTk.PhotoImage(file = 'bg/ok.png')
        self.main_frame_empty = ImageTk.PhotoImage(file = 'bg/cam_blank_main.png')
        self.main_frame_block = ImageTk.PhotoImage(file = 'bg/logo_block.png')
        self.main_frame_small_ok = ImageTk.PhotoImage(file = 'bg/ok_p.png')
        self.main_frame_small_ng = ImageTk.PhotoImage(file = 'bg/ng_p.png')
        self.main_frame_red_lamp = ImageTk.PhotoImage(file = 'bg/red.png')
        self.main_frame_green_lamp = ImageTk.PhotoImage(file = 'bg/green.png')
        self.main_frame_row = [ImageTk.PhotoImage(file = f'bg/sel{i}.png') for i in range(1, 6)] + [ImageTk.PhotoImage(file = 'bg/row.png')] * 3
        self.main_frame_exit = ImageTk.PhotoImage(file = 'bg/exitWindow.png')
        self.main_frame_alarm = ImageTk.PhotoImage(file = 'bg/alarmWindow.png')
        self.main_frame_config = ImageTk.PhotoImage(file = 'bg/configWindow.png')
        # self.main_frame_selection = ImageTk.PhotoImage(file = 'bg/selectionWindow.png')
        self.main_frame_confirm = ImageTk.PhotoImage(file = 'bg/confirmWindow.png')
        self.main_frame_button = ImageTk.PhotoImage(file = 'bg/button.png')

        # Inspection list variables(Inspection status)
        # self.selection_print = ['충전로고\n인쇄상태', '  띠로고\n인쇄상태', '    범퍼\n누락상태','외관 상태','이종 검사','추가 예정','추가 예정','추가 예정']

        # self.selection_text = ['충전로고 인쇄상태', '띠로고 인쇄상태', '범퍼누락상태','외관 상태','이종 검사','추가 예정','추가 예정','추가 예정']
        self.partial_bool = [True] * 4 + [False] * 4 # 현재 사용중인 항목
        self.row_current = 4 # 현재 검사현황 항목 개수

        # Window Flag variables
        self.show_config = False    # CONFIG
        self.show_confirm = False   # CONFIRM(RESET)
        self.show_selection = False # SELECTION(INSPECTION)
        self.show_alarm = False     # ALARM(PLC DISCONNECTED)
        self.show_exit = False

        self.block = False
        self.slow = False

        # Inspection Count variables
        self.ok = 0
        self.ng = 0
        self.total = 0

        # Thread Flag variables
        self.recording = False # True if video needs to be recorded

        # Create the widgets
        self.create_widgets()

    
        # Partial inspection image variables
        self.cvtimg1 = [None] * 5
        self.cvtshow1 = [None] * 5
        self.img_path1 = [None] * 5
        self.open_pickle()


    def create_widgets(self):
        self.grid(row = 0, column = 0)
        self.main_canvas = tk.Canvas(self, width = 1920, height = 1080)
        self.bg_image = self.main_canvas.create_image(0, 0, image = self.main_frame_img, anchor = 'nw')
        self.camera_lamp = self.main_canvas.create_image(314, 104, image = self.main_frame_red_lamp, anchor = 'center')
        self.plc_lamp = self.main_canvas.create_image(521, 104, image = self.main_frame_red_lamp, anchor = 'center')
        self.ng_image = self.main_canvas.create_image(1545, 897, image = self.main_frame_ng, anchor = 'nw', state='hidden')
        self.ok_image = self.main_canvas.create_image(1185, 897, image = self.main_frame_ok, anchor = 'nw', state='hidden')
        self.block_image = self.main_canvas.create_image(1162, 657, image = '', anchor = 'nw')
        self.cam_image = self.main_canvas.create_image(76, 151, image = self.main_frame_empty, anchor= 'nw')
        self.backup_image = self.main_canvas.create_image(76, 151, image = self.main_frame_empty, anchor= 'nw')
        self.fps_text_view = self.main_canvas.create_text(100, 200, text = '0', font=(LFONT, 20, 'bold'), fill="green")
        self.partial_image = [self.main_canvas.create_image(71 + (220 * i), 912, image = '', anchor = 'nw') for i in range(5)]
        self.recing = self.main_canvas.create_text(150, 50, text='Recording', font=LFONT, fill="white", state='hidden')
        

        # 생산현황  
        self.product_no = self.main_canvas.create_text(1630, 200, text="품번", font=FONT, fill="white")
        self.product_type = self.main_canvas.create_text(1630, 237, text="차종", font=FONT, fill="white")
        self.lot = self.main_canvas.create_text(1630, 276, text="LOT", font=FONT, fill="white")
        self.out_time = self.main_canvas.create_text(1630, 313, text="검사시간", font=FONT, fill="white")
       
        # 검사현황
        self.partial_row = [self.main_canvas.create_image(1185, 388 + (i * 37), image = self.main_frame_row[i], anchor='nw', state='hidden') for i in range(7)] # row image
        self.partial_result = [self.main_canvas.create_image(1654.5, 388.5 + (i * 37), image = '', anchor='nw', state='hidden') for i in range(7)] # ok / ng
        for i in range(self.row_current):
            self.main_canvas.itemconfig(self.partial_row[i], state='normal')
            self.main_canvas.itemconfig(self.partial_result[i], state='normal')

        # 생산정보
        self.total_count = self.main_canvas.create_text(1278, 787, text=str(self.total), font=FONT, fill="white")
        self.ng_count = self.main_canvas.create_text(1679, 787, text=str(self.ng), font=FONT, fill="white")
        self.ok_count = self.main_canvas.create_text(1477, 787, text=str(self.ok), font=FONT, fill="white")
       
        # 알림, 환경설정, 종료확인창
        self.confirm_window = self.main_canvas.create_image(960, 540, image = self.main_frame_confirm, anchor= 'center', state = 'hidden')
        # self.selection_window = self.main_canvas.create_image(960, 540, image = self.main_frame_selection, anchor= 'center', state = 'hidden')
        self.exit_window = self.main_canvas.create_image(960, 540, image = self.main_frame_exit, anchor= 'center', state = 'hidden')
        self.config_window = self.main_canvas.create_image(960, 540, image = self.main_frame_config, anchor= 'center', state = 'hidden')
        self.alarm_window = self.main_canvas.create_image(960, 540, image=self.main_frame_alarm,  anchor= 'center', state = 'hidden')

        # 검증선택
        # self.selection_buttons = [self.main_canvas.create_text(769 + 381 * (i % 2), 378 + 139 * (i // 2), 
        # text=self.selection_print[i], font=LFONT, fill='white', state='hidden') for i in range(8)]

        # 환경설정
        self.recMode = self.main_canvas.create_text(844, 454, text="OFF", font=BFONT, fill='white', state='hidden')
        self.saveMode = self.main_canvas.create_text(1317, 454, text="ALL", font=BFONT, fill='white', state='hidden')
        self.saveText = ['ALL', 'OK', 'NG' ]


        # Bind the Button events
        self.main_canvas.bind('<Button-1>', self.main_btn)
        self.main_canvas.bind('<Double-Button-1>', self.main_btn_db)
        self.main_canvas.pack()

    def closing_event(self):
        savelist = [self.ok, self.ng, self.total]
        print(f'[ Info ] {savelist}')
        pickle.dump(savelist, open("savecount.pickle", "wb"))
        print('[ System ] Count Information saved!')


    def open_pickle(self):
        try:
            read_file = open("savecount.pickle", "rb")
            load_count = pickle.load(read_file)
            read_file.close()
            print(load_count)
            self.ok = load_count[0]
            self.ng = load_count[1]
            self.total = load_count[2]
            self.main_canvas.itemconfig(self.ok_count, text = self.ok)
            self.main_canvas.itemconfig(self.ng_count, text = self.ng)
            self.main_canvas.itemconfig(self.total_count, text = self.total)
        except:
            print('pickle is not define')
            self.ok = 0
            self.ng = 0
            self.total = 0
            self.main_canvas.itemconfig(self.ok_count, text = self.ok)
            self.main_canvas.itemconfig(self.ng_count, text = self.ng)
            self.main_canvas.itemconfig(self.total_count, text = self.total)

    def show_img(self, image):
        img = cv2.resize(image, dsize=(1060, 727), interpolation=cv2.INTER_AREA).copy()
        self.cvtimg = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
        self.cvtshow = Image.fromarray(self.cvtimg)
        self.img_path = ImageTk.PhotoImage(image=self.cvtshow)
        self.main_canvas.itemconfig(self.cam_image, image = self.img_path)
        self.backup = self.img_path
        self.main_canvas.itemconfig(self.backup_image, image = self.backup)

    def show_partial_image(self, image, idx):
        img = cv2.resize(image, dsize=(190, 140), interpolation=cv2.INTER_AREA).copy()
        self.cvtimg1[idx] = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
        self.cvtshow1[idx] = Image.fromarray(self.cvtimg1[idx])
        self.img_path1[idx] = ImageTk.PhotoImage(image=self.cvtshow1[idx])
        self.main_canvas.itemconfig(self.partial_image[idx], image = self.img_path1[idx])
        
    def main_btn(self, event):
        x = event.x
        y = event.y
        # print(x, y)
        
        # ADD MOUSE EVENTS
        # PLAIN MODE
        if not (self.show_config or self.show_confirm or self.show_selection or self.show_alarm or self.show_exit):
            if x < 140 and y < 130: # CONFIG
                self.show_config = True
                self.main_canvas.itemconfig(self.config_window, state='normal')
                self.main_canvas.itemconfig(self.recMode, state='normal')
                self.main_canvas.itemconfig(self.saveMode, state='normal')

            if 1850 < x and y < 70:
                self.main_canvas.itemconfig(self.exit_window, state='normal')
                self.show_exit = True

            # if 1185 < x < 1885 and 347 < y < 380 and self.row_current < 7: # ADD INSPECTION LABEL
            #     self.main_canvas.itemconfig(self.selection_window, state='normal')
            #     for i in range(8):
            #         self.main_canvas.itemconfig(self.selection_buttons[i], state='normal')
            #     self.show_selection = True
                # print(self.show_selection)

            if 1783 < x < 1882 and 724 < y < 805: # RESET
                self.main_canvas.itemconfig(self.confirm_window, state='normal')
                self.show_confirm = True

        # SELECTION MODE
        # elif self.show_selection:
        #     if not (510 < x < 1410 and 170 < y < 910):
        #         self.main_canvas.itemconfig(self.selection_window, state='hidden')
        #         for i in range(8):
        #             self.main_canvas.itemconfig(self.selection_buttons[i], state='hidden')
        #         self.show_selection = False
        #     else: 
        #         for i in range(8):
        #             if 644 + (381 * (i % 2)) < x < 894 + (381 * (i % 2)) and 326 + (139 * (i // 2)) < y < 426 + (139 * (i // 2)):
        #                 if not self.partial_bool[i]:
        #                     INS.ins_labels.append(i)
        #                     self.main_canvas.itemconfig(self.partial_row[self.row_current], state='normal')
        #                     self.row_current += 1

        # EXIT MODE
        elif self.show_exit:
            if not (660 < x < 1260 and 390 < y < 690):
                self.main_canvas.itemconfig(self.exit_window, state='hidden')
                self.show_exit = False
            elif y > 540:
                if x > 959:
                    self.main_canvas.itemconfig(self.exit_window, state='hidden')
                    self.show_exit = False
                else :
                    self.closing_event()
                    exit()


        # CONFIRM MODE
        elif self.show_confirm:
            if not (660 < x < 1260 and 390 < y < 690):
                self.main_canvas.itemconfig(self.confirm_window, state='hidden')
                self.main_canvas.itemconfig(self.recMode, state='hidden')
                self.main_canvas.itemconfig(self.saveMode, state='hidden')

                self.show_confirm = False
            elif y > 540:
                if x > 959:
                    self.main_canvas.itemconfig(self.confirm_window, state='hidden')
                    self.show_confirm = False
                else :
                    self.ok = 0
                    self.ng = 0
                    self.total = 0
                    self.main_canvas.itemconfig(self.ok_count, text='0')
                    self.main_canvas.itemconfig(self.ng_count, text='0')
                    self.main_canvas.itemconfig(self.total_count, text='0')
                    self.main_canvas.itemconfig(self.confirm_window, state='hidden')
                    self.show_confirm = False

        # CONFIG MODE
        elif self.show_config: ### 촬영 모드 여기로 이동
            if not (510 < x < 1410 and 170 < y < 910):
                self.main_canvas.itemconfig(self.config_window, state='hidden')
                self.main_canvas.itemconfig(self.saveMode, state='hidden')
                self.main_canvas.itemconfig(self.recMode, state='hidden')

                self.show_config = False

            # 촬영모드 버튼
            elif 547 < x < 898 and 380 < y < 530:
                self.recording = not self.recording
                self.main_canvas.itemconfig(self.recing, state='normal' if self.recording else 'hidden')
                self.main_canvas.itemconfig(self.recMode, text='ON' if self.recording else 'OFF')
                SC.client_socket.send(b'S 025' if self.recording else b'S 100')
                print('S 025' if self.slow else 'S 100')

            # 저장모드 버튼
            elif 1022 < x < 1370 and 380 < y < 530:
                CTH.save_mode = (CTH.save_mode + 1) % 3
                self.main_canvas.itemconfig(self.saveMode, text=self.saveText[CTH.save_mode])

        elif self.show_alarm:
            self.main_canvas.itemconfig(self.alarm_window, state='hidden')
            self.show_alarm = False
        
    # DOUBLE CLICK EVENTS
    def main_btn_db(self, event):
        x = event.x
        y = event.y
        print('DOUBLE: ', x, y)
        
        # ADD MOUSE EVENTS

        if 1187 < x < 1887 and 680 < y < 800: # Hide/Show Prod Info
            self.block = not self.block
            self.main_canvas.itemconfig(self.block_image, image = self.main_frame_block if self.block else '')
            self.main_canvas.itemconfig(self.ng_count, state='hidden' if self.block else 'normal')
            self.main_canvas.itemconfig(self.total_count, state='hidden' if self.block else 'normal')
            self.main_canvas.itemconfig(self.ok_count, state='hidden' if self.block else 'normal')


class cameraRTSP(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.inspection = False # Inspection flag
        self.ins_result = False # Inspection result
        self.reset = False
        self.save_mode = 0  # 0 : all, 1 : ok, 2 : ng
        self.inspection_False_result_save = None
        self.session_ending = None
        self.result_Status = [False, False, False, False]
        self.fps_text = 0
        self.modelDic = {
            ## (k, v) = 사양 , 차종
            '96125-C7AC0' : 'GB PE L(스프링)',
            '96125-C7010' : 'GP PE R(스프링)',
            '96125-C7000' : 'IB FL(스프링)',
            '96125-J5100' : 'CK',
            '96125-M6000' : 'DE EV',
            '96125-M6110' : 'BD(반원)',
            '96125-M6010' : 'BD(사각)',
            '96125-K4000' : 'OS EV',
            '96125-K0000' : 'SK3',
            '96125-J7010' : 'CD',
            '96125-Q5000' : 'SP2',
            '96125-K2550' : 'QXI',
            '96125-K2350' : 'QX',
            '96125-J7020' : 'CD CUV(원형)',
            '96125-J7030' : 'CD CUV(사각)',
            '96125-K2100' : 'AI3',
            '96125-K2300' : 'AI3',
            '96125-Q5500' : 'SP2',
            '96125-C7020' : 'IB FL(락킹)',
            '96125-C7BF0' : 'GB PE R(락킹)',
            '96125-K2150' : 'SU2',
            '96125-C7BC0' : 'GB PE L(락킹)',
            '96125-CC000' : 'QY',
            '96125-C7HC0' : 'HCI PE',
            '96125-S9000' : 'ON(사각)',
            '96125-S9010' : 'ON(반원)',
            '96125-S9200' : 'ON(원형)',
            '96125-S8000' : 'LX2',
            '96125-L1000' : 'DN8',
            '96125-L2000' : 'DL3(반원)',
            '96125-L2100' : 'DL3(원형)',
            '96125-L2200' : 'DL3(NON C)',
            '96125-F6000' : 'YG PE(세로)',
            '96125-F6500' : 'YG PE(가로)',
            '96125-2J000' : 'HM PE2',
            '96125-G8000' : 'IG PE(가로)',
            '96125-R1000' : 'BR2',
            '96125-P2100' : 'MQ4 L',
            '96125-P2000' : 'MQ4 R',
            '96125-G8100' : 'IG PE(세로)',
            '96125-AA000' : 'CN7',
            '96125-F6600' : 'GL3',
            '96125-H0200' : 'FB PE',
            '96125-Q0500' : 'I20'
        }

        if COMM < 3:
            self.typeDic = {
                ## (k, v) = 사양 , 차종
                ## 1번라인
                ' 1': '96125-C7AC0',
                ' 2': '96125-C7010',
                ' 3': '96125-C7000',
                ' 4': '96125-J5100',
                ' 5': '96125-M6000',
                ' 6': '96125-M6110',
                ' 7': '96125-M6010',
                ' 8': '96125-K4000',
                ' 9': '96125-K0000',
                '10': '96125-J7010',        
                '11': '96125-Q5000',
                '12': '96125-K2550',
                '13': '96125-K2350',        
                '14': '96125-J7020',
                '15': '96125-J7030',
                '16': '96125-K2100',
                '17': '96125-K2300',
                '18': '96125-Q5500',
                '19': '96125-C7020',
                '20': '96125-C7BF0',
                '21': '96125-K2150',
                '22': '96125-C7BC0',
                '23': '96125-CC000',        
                '24': '96125-C7HC0',
                '25': '96125-15',
                '26': '96125-16',
                '27': '96125-17',
                '28': '96125-18',
                '29': '96125-19',     
                '30': '96125-20',
            }
        else:
            self.typeDic = {
                ## 2번 라인
                ' 1': '96125-S9000',
                ' 2': '96125-S9010',
                ' 3': '96125-S9200',
                ' 4': '96125-S8000',
                ' 5': '96125-L1000',
                ' 6': '96125-L2000',
                ' 7': '96125-L2100',
                ' 8': '96125-L2200',
                ' 9': '96125-F6000',
                '10': '96125-F6500',
                '11': '96125-2J000',
                '12': '96125-G8000',
                '13': '96125-R1000',
                '14': '96125-P2100',
                '15': '96125-P2000',
                '16': '96125-G8100',
                '17': '96125-AA000',
                '18': '96125-F6600',
                '19': '96125-H0200',
                '20': '96125-Q0500',
                
            }


        if not os.path.isdir(DESKTOP+'/내장형USB'):
            os.mkdir(DESKTOP+'/내장형USB')
        if not os.path.isdir(dataPath):
            os.mkdir(dataPath)
        if not os.path.isdir(insresPath):
            os.mkdir(insresPath)        
        if not os.path.isdir(CIM):
            os.mkdir(CIM)
        if not os.path.isdir(excelPath):
            os.mkdir(excelPath)

    def clock(self):
        TIME = time.localtime(time.time())
        self.YYYY = TIME.tm_year
        self.MM = TIME.tm_mon
        self.DD = TIME.tm_mday
        H = TIME.tm_hour
        M = TIME.tm_min
        S = TIME.tm_sec
        dt = f'{self.YYYY:04d}-{self.MM:02d}-{self.DD:02d} {H:02d}:{M:02d}:{S:02d}'
        DT = datetime.datetime(self.YYYY, self.MM, self.DD)
        tm = DT + datetime.timedelta(days=1)
        self.nday = f'{self.YYYY:04d}-{tm.month:02d}-{tm.day:02}'
        # print(self.nday)

        self.currentDatetime = dt
        self.Date = dt.split(' ')[0]
        self.Time = dt.split(' ')[1]
        main_frame.main_canvas.itemconfig(main_frame.out_time, text=dt)


    def run(self):
        writer = None
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        try:
            info = pylon.DeviceInfo()
            #카메라 시리얼 넘버 변경 필요
            info.SetSerialNumber(camSerial) ###

            camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice(info))
            camera.Open()

            # set configurations
            # camera.Width.SetValue(2448)
            # camera.Height.SetValue(2048)
            # camera.DigitalShift.SetValue(2)
            # camera.ExposureTimeRaw.SetValue(3000)

            print("Using device", camera.GetDeviceInfo().GetModelName())

            camera.MaxNumBuffer = 5

            camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly) 
            
            converter = pylon.ImageFormatConverter()

            converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            # converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

            main_frame.main_canvas.itemconfig(main_frame.camera_lamp, image=main_frame.main_frame_green_lamp)

            insCount = 0
            pointFrame = [0, 5, 30, 43, 61] # 메인화면 밑에 5개 사진 몇번째 프레임 저장할지
            self.pointIns = [False] * 5 # 5개 프레임 검증결과
            self.saved = True # 결과저장 플래그
            ins_text = {True: 'ng', False: 'ok'}
            imgPath = ''
            pType = bc = None # pType - 차종번호(1~30) , bc - 바코드값
            init = False # 초기화 플래그
            recCount = 0 # 녹화 카운트 변수

            while camera.IsGrabbing():
                text = re.sub('[-=+,#/\?:^$.@*\"※~&%ㆍ!』\\‘|\(\)\[\]\<\>`\'…》]', '', str(time.time()))
                self.clock()

                startTime = time.time()

                grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

                if grabResult.GrabSucceeded():
                    image = converter.Convert(grabResult)
                    self.img = image.GetArray()
                    # img = self.img.copy()

                    # RESET1
                    if self.reset:
                        # print('if reset')
                        self.reset = False
                        main_frame.main_canvas.itemconfig(main_frame.ng_image, state = 'hidden')
                        main_frame.main_canvas.itemconfig(main_frame.ok_image, state = 'hidden')
                        for i in range(main_frame.row_current):
                            main_frame.main_canvas.itemconfig(main_frame.partial_result[i], state = 'hidden')
                        main_frame.show_img(self.img)
                        self.inspection = False
                        self.saved = True
                        self.init = False
                        self.result_Status = [False, False, False, False]
                        self.fps_text = 0
                        main_frame.main_canvas.itemconfig(main_frame.fps_text_view, text = self.fps_text)
                        if writer is not None:
                            writer.release()
                            writer = None
                        continue


                    #insepction
                    # start
                    if self.inspection:
                        if not init:
                            print('enter init')
                            # startTime = time.time()
                            if bc is not None and bc != SC.barcode:
                                recCount = 0
                            else:
                                print('same barcode')
                            self.saved = False
                            bc = SC.barcode
                            values = bc.split(' ')
                            pType = SC.prodType
                            if self.typeDic[pType] not in bc:
                                self.ins_result = True
                                print("Barcode Error")
                            lotNo = values[2]
                            init = True
                            if not os.path.isdir(f'{insresPath}/{pType}'):
                                os.mkdir(f'{insresPath}/{pType}')

                            if not os.path.isdir(f'{insresPath}/{pType}/{self.YYYY:04d}'):
                                os.mkdir(f'{insresPath}/{pType}/{self.YYYY:04d}')

                            if not os.path.isdir(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}'):
                                os.mkdir(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}')

                            if not os.path.isdir(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}'):
                                os.mkdir(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}')

                            if not os.path.isdir(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}/ok'):
                                os.mkdir(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}/ok')

                            if not os.path.isdir(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}/ng'):
                                os.mkdir(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}/ng')

                            if not os.path.isdir(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}/ok/{SC.barcode}'):
                                os.mkdir(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}/ok/{SC.barcode}')

                            if not os.path.isdir(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}/ng/{SC.barcode}'):
                                os.mkdir(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}/ng/{SC.barcode}')

                        
                        # Data recording
                        # if main_frame.recording and recCount < 10000:
                        #     imwrite(f'data/{bc}/image_{text}.jpg', self.img)
                        #     recCount += 1

                        if main_frame.recording:
                            if writer is None:
                                writer = cv2.VideoWriter(f'data/{bc}{recCount}.avi', fourcc, 24, (2448, 2048), True)
                                recCount += 1
                            writer.write(self.img)

                        result_value = False

                        # BYPASS 아닐때
                        if not SC.bypass:
                            self.fps_text += 1
                            
                            saved = True
                            partial_result, result_value, self.img = INS.inspection(self.img)
                            self.ins_result = self.ins_result or result_value
                            # print('ins_result:', self.ins_result)
                            
                            # 5개 표시
                            if insCount in pointFrame:
                                idx = pointFrame.index(insCount)
                                self.pointIns[idx] = result_value
                                main_frame.show_partial_image(self.img, idx)
                            print(self.pointIns)

                            # 검증 결과 저장
                            resText = 'ng' if result_value else 'ok'
                            if (self.save_mode == 1 and not result_value) or (self.save_mode == 2 and result_value) or self.save_mode == 0 :
                                imwrite(f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}/{resText}/image_{text}.jpg', self.img)
                                imgPath = f'{insresPath}/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}/{resText}/image_{text}.jpg'

                            if self.ins_result == True:
                                self.inspection_False_result_save = True
                            
                            if self.session_ending == None:
                                if self.inspection_False_result_save == True:
                                    main_frame.main_canvas.itemconfig(main_frame.ng_image, state = 'normal')
                                    main_frame.main_canvas.itemconfig(main_frame.ok_image, state = 'hidden')
                                else:
                                    main_frame.main_canvas.itemconfig(main_frame.ng_image, state = 'normal' if self.ins_result else 'hidden')
                                    main_frame.main_canvas.itemconfig(main_frame.ok_image, state = 'hidden' if self.ins_result else 'normal')
                            
                            for i,result in enumerate(partial_result):
                                if result == True:
                                    self.result_Status[i] = True
                            for i in range(main_frame.row_current):
                                main_frame.main_canvas.itemconfig(main_frame.partial_result[i], image = main_frame.main_frame_small_ng if self.result_Status[i] else main_frame.main_frame_small_ok, state='normal')
                                #main_frame.main_canvas.itemconfig(main_frame.partial_result[i], image = main_frame.main_frame_small_ng if partial_result[i] else main_frame.main_frame_small_ok, state='normal')
                            
                            ###########
                            main_frame.main_canvas.itemconfig(main_frame.fps_text_view, text = self.fps_text)
                            insCount += 1

             
                    # reset
                    elif self.saved == False:
                        if main_frame.recording: # 촬영모드면서 바이패스일때
                            if writer is not None:
                                writer.release()
                                writer = None
                                init = False
                            pass
                        # print("[INFO] Elapesed time : ", time.time() - startTime)
                        init = False
                        # main_frame.total += 1
                        
                        # if CTH.ins_result == True and SC.bypass == False:
                        #     main_frame.ng += 1
                        #     main_frame.main_canvas.itemconfig(main_frame.ng_image, state = 'normal')
                        #     main_frame.main_canvas.itemconfig(main_frame.ok_image, state = 'hidden')
                        # elif CTH.ins_result == True and SC.bypass == True:
                        #     main_frame.ok += 1
                        #     main_frame.main_canvas.itemconfig(main_frame.ng_image, state = 'hidden')
                        #     main_frame.main_canvas.itemconfig(main_frame.ok_image, state = 'normal')
                        # elif CTH.ins_result == False:
                        #     main_frame.ok += 1
                        #     main_frame.main_canvas.itemconfig(main_frame.ng_image, state = 'hidden')
                        #     main_frame.main_canvas.itemconfig(main_frame.ok_image, state = 'normal')
                        CTH.inspection_False_result_save = None
                        main_frame.total += 1
                        main_frame.ng += 1 if self.ins_result else 0
                        main_frame.ok += 0 if self.ins_result else 1
                        
                        main_frame.main_canvas.itemconfig(main_frame.total_count, text=str(main_frame.total))
                        main_frame.main_canvas.itemconfig(main_frame.ok_count, text=str(main_frame.ok))
                        main_frame.main_canvas.itemconfig(main_frame.ng_count, text=str(main_frame.ng))
                        main_frame.main_canvas.itemconfig(main_frame.ng_image, state = 'hidden')
                        main_frame.main_canvas.itemconfig(main_frame.ok_image, state = 'hidden')
                        for i in range(main_frame.row_current):
                            main_frame.main_canvas.itemconfig(main_frame.partial_result[i], state = 'hidden')
                            # main_frame.main_canvas.itemconfig(main_frame.partial_result[i], image = main_frame.main_frame_small_ng if self.ins_result[i] else main_frame.main_frame_small_ok, state='normal')

                        valueList = [
                            ("lot", f"{lotNo}"),
                            ("date", "now()"),
                            ("result", f"'{ins_text[self.ins_result]}'"),
                            ("point1", f"'{ins_text[self.pointIns[0]]}'"),
                            ("point2", f"'{ins_text[self.pointIns[1]]}'"),
                            ("point3", f"'{ins_text[self.pointIns[2]]}'"),
                            ("point4", f"'{ins_text[self.pointIns[3]]}'"),
                            ("point5", f"'{ins_text[self.pointIns[4]]}'"),
                            ("barcode", f"'{bc}'"),
                            # Only self.saved in DB
                            ("imgpath", f"'{imgPath}'"),
                            ("name", f"'{self.typeDic[pType]}'"),
                            ("type", f"'{self.modelDic[self.typeDic[pType]]}'")
                        ]
                        mdb.writeSql(valueList) # db write

                        mdb.readSql(text=self.Date, StartDate=self.Date, EndDate=self.nday) # Excel Write(Cim)

                        #Excel Write(엑셀)
                        dirText = f'/{pType}/{self.YYYY:04d}/{self.MM:02d}/{self.DD:02d}/'
                        mdb.readSql(barcode=bc, dir=dirText, text=bc)
                        self.saved = True
                        insCount = 0
                        self.pointIns = [False] * 5
                        self.result_Status = [False, False, False, False]
                        self.fps_text = 0

                    main_frame.show_img(self.img)
                    # print("[INFO] Elapsed time:", time.time() - startTime)

                else:
                    # 프레임 grab 실패시
                    print("Error: ", grabResult.ErrorCode, grabResult.ErrorDescription)
                grabResult.Release()
            camera.Close()

        # 카메라 Exception Handler
        except genicam.GenericException as e:
            # Error handling.
            print("An exception occurred : ", e)
            main_frame.main_canvas.itemconfig(main_frame.camera_lamp, image=main_frame.main_frame_red_lamp)
            exitCode = 1


class MysqlDB():
    def __init__(self):
        self.host = 'localhost'
        self.user = 'root'
        self.password = 'yous7051!'
        self.dbname = 'unick'

    def readSql(self, text, dir = None, typeName=None, result=None, StartDate=None, EndDate=None, barcode=None):
        db = pymysql.connect(host=self.host, user=self.user, password=self.password, db=self.dbname, charset="utf8")
        curs = db.cursor()
        sql = "select no, lot, date, result, point1, point2, point3, point4, point5, barcode, imgpath from log"
        addvalue = False

        if typeName is not None:
            add = " WHERE " if addvalue is False else " AND "
            addvalue = True

            sql = sql + add + "type='{}'".format(typeName)

        if result is not None:
            add = " WHERE " if addvalue is False else " AND "
            addvalue = True

            sql = sql + add + "result='{}'".format(result)

        if StartDate is not None:
            add = " WHERE " if addvalue is False else " AND "
            addvalue = True

            sql = sql + add + "date >= '{}'".format(StartDate)

        if EndDate is not None:
            add = " WHERE " if addvalue is False else " AND "
            addvalue = True

            sql = sql + add + "date <= '{} 23:59:59'".format(EndDate)

        if barcode is not None:
            add = " WHERE " if addvalue is False else " AND "
            addvalue = True

            sql = sql + add + "barcode='{}'".format(barcode)

        curs.execute(sql)
        rows = curs.fetchall()
        
        self.writeExcel(rows, text)
        db.close()

    def writeSql(self, valueList):
        db = pymysql.connect(host=self.host, user=self.user, password=self.password, db=self.dbname, charset="utf8")
        param = values = ""
        curs = db.cursor()
        for name, val in valueList:
            param = param + name + ", "
            values = values + val + ", "

        sql = "INSERT INTO log ({}) VALUES ({})".format(param[:-2], values[:-2])
        
        curs.execute(sql)
        db.commit()
        db.close()

    def writeExcel(self, data, text, dirName = None):
        wb = Workbook()
        ws = wb.active
        ws.append(('NO','LOT', '검사완료시간', '최종판정', '검사항목1판정', '검사항목2판정', '검사항목3판정', '검사항목4판정', '검사항목5판정', '바코드', '사진경로'))

        for num, row in enumerate(data):
            raw = []
            raw.append(str(num+1))

            for col, i in enumerate(row[1:]):
                if col > 9:
                    break
                raw.append(str(i))

            ws.append(raw)

        if dirName is None:
            wb.save(DESKTOP+"/내장형USB/Cim/output{}.xlsx".format(text))
        else:
            wb.save(excelPath + dirName + text + '.xlsx')


class SocketCommunication(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        # BYPASS 읽어오기
        r = open('bypass.txt', mode='rt')
        by = r.read(3)
        self.bypass = True if 'on' in by else False

        # TEST
        self.prodType = '10'
        self.barcode = '96125-C7AC0 200402 24302 UNICK'

        print("BYPASS", 'ON' if self.bypass else 'OFF')

    def run(self):
        try:
            self.connect()
            currStep = 0
            # self.client_socket.send(b'S 100')
        except:
            self.connect()

        while True:
            try:
                if currStep == 2:
                    to = 40.0 if main_frame.slow else 10.0
                else:
                    to = None

                # self.client_socket.settimeout(to)
                data = self.client_socket.recv(1024)
                data = data.decode()
                print('recv:', data)

                data_sub = data[0]
                # if data_sub == 'M':
                #     data = data[-2:]
                #     print("모델 기종신호 데이터 : ", data)
                #     INS.loadModel(data)

                #     # text = b'M\x00OK'
                #     # SC.client_socket.send(text)
                # try:
                #     if data_sub == 'M':
                #         data = data[-1]
                #         print("모델 기종신호 데이터 : ", data)
                #         # INS.loadModel(data)

                #         text = b'comp'
                #         self.client_socket.send(text)

                # except Exception as e:
                #     print(f'[ Error ] {e}')
                #     continue

                if 'UNICK' in data:
                    # print('qr recv')
                    currStep = 1
                    # print('Step ', currStep)

                    self.barcode, time = data.split('UNICK')
                    self.barcode += 'UNICK'
                    self.prodType = time[10:]
                    # if ' ' in self.prodType:
                    #     self.prodType.replace(' ','0')
 
                    main_frame.main_canvas.itemconfig(main_frame.product_no, text=CTH.typeDic[self.prodType])
                    main_frame.main_canvas.itemconfig(main_frame.product_type, text=CTH.modelDic[CTH.typeDic[self.prodType]])
                    main_frame.main_canvas.itemconfig(main_frame.lot, text=self.barcode)

                    text = b'comp'
                    self.client_socket.send(text)

                    print('comp sent')
                    CTH.session_ending = None
                    CTH.ins_result = False
                    # print('[TEST] PRODUCT TYPE :', time[10:])
                    # print('[TEST] PRODUCT HEX :', binascii.unhexlify(time[9:]))

                elif 'start' in data:
                    currStep = 2
                    # print('Step ', currStep)
                    CTH.inspection = True
                    self.client_socket.send(b'comp1')
                    print('comp1 sent')

                elif 'reset' in data:
                    currStep = 3
                    # print('Step ', currStep)
                    # print('reset recv')
                    CTH.inspection = False 
                    if CTH.inspection_False_result_save == True and self.bypass == False:
                        text = 'ng'
                    elif CTH.inspection_False_result_save == True and self.bypass == True:
                        text = 'ok'
                    elif CTH.inspection_False_result_save == None:
                        text = 'ok'
                    
                    # text = 'ng' if CTH.inspection_False_result_save and self.bypass else 'ok'
                    # text = 'ng' if CTH.ins_result and not self.bypass else 'ok'
                    # text = 'ng' if CTH.ins_result else 'ok'
                    # text = 'ok'
                    text = text.encode()
                    self.client_socket.send(text)
                    print("reset response: ",text)
                    
                    CTH.session_ending = True

                elif 'RESET1' in data:
                    currStep = 0
                    CTH.reset = True
                    self.client_socket.send(b'INIT')
                    print('INIT sent')
                
                elif 'BYPASS' in data:
                    w = open('bypass.txt', mode='wt')

                    self.bypass = not self.bypass
                    print('[INFO] BYPASS', 'ON' if self.bypass else 'OFF')
                    self.client_socket.send(b'BYPASS' if self.bypass else b'NOPASS')
                    w.write('on' if self.bypass else 'off')
                    w.close()
                elif data_sub == 'M':
                    data = data[-1]
                    print(f'[ System ] Model number : {data}')
                    # INS.loadModel(data)

                    text = b'mok'
                    self.client_socket.send(text)
                    print('send ', text)
                else:
                    pass
                    # print('Not an Option')
                    # self.client_socket.send(b'na')

            except socket.timeout as e:
                currStep = 0
                print("Start Timed Out : ", e)
                #CTH.inspection = False 
                #text = 'ng' if CTH.ins_result and not self.bypass else 'ok'
                #text = text.encode()
                CTH.reset = True
                self.client_socket.send(b'TIME')
                print("TIME sent")

            except AttributeError as e:
                print("Attribute error :", e)
                self.client_socket.close()
                print('[INFO] Client Closed. Reconnecting...')
                self.connect()

            except Exception as e:
                print("Exception :",e)
                main_frame.main_canvas.itemconfig(main_frame.plc_lamp, image='')
                main_frame.main_canvas.itemconfig(main_frame.alarm_window, state='normal')
                main_frame.show_alarm = True
                self.client_socket.close()
                print('[INFO] Client Closed. Reconnecting...')
                self.connect()


    def connect(self):
        print("CONNECTING...")

        self.client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM) 
        connected = False
        print('Notice : [Socket not Connected]')

        while True:
            if not connected:
                try:
                    self.client_socket.connect((HOST, PORT)) 
                    print('Notice : [Socket Connected]')
                    main_frame.main_canvas.itemconfig(main_frame.plc_lamp, image=main_frame.main_frame_green_lamp)
                    main_frame.main_canvas.itemconfig(main_frame.alarm_window, state='hidden')
                    main_frame.show_alarm = False
                    break
                except:
                    pass
            else:
                try:
                    self.client_socket.send(b' ')
                except:
                    print('Notice : [Socket not Connected]')
                    self.client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                    connected = False
                    pass
                time.sleep(1000)



    def cleanText(self, readData):
        data = b'\x00'
        data = binascii.hexlify(data).decode()
        qdata = bytearray.fromhex(data).decode()

        readData = binascii.hexlify(readData).decode()
        try:
            readData = bytearray.fromhex(readData).decode()
            readData = readData.replace(qdata, '')
        except:
            pass
        text = re.sub('[-=+,#/\?:^$.@*\"※~&%ㆍ!』\\‘|\(\)\[\]\<\>`\'…》]', '', readData)

        return text


class InspectionClass():
    def __init__(self):
        self.ins_labels = [0, 1, 2, 3] # Labels that are being inspected
        self.inspection_percent = [0.99, 0.9, 0.99, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9]
        self.loadModel()


    def loadModel(self, mNumber = None):

        if mNumber == None:
            model_path = f'model/frozen_inference_graph.pb'
            label_path = f'model/classes.pbtxt'
        else:
            model_path = f'model/{mNumber}/frozen_inference_graph.pb'
            label_path = f'model/{mNumber}/classes.pbtxt'

        try:
            K.clear_session()
            gc.collect()
            del self.model, self.sess
        except:
            pass

        # initialize the model
        self.model = tf.Graph()

        with self.model.as_default():
        	# initialize the graph definition
        	graphDef = tf.GraphDef()

        	# load the graph from disk
        	with tf.gfile.GFile(model_path, "rb") as f:
        		serializedGraph = f.read()
        		graphDef.ParseFromString(serializedGraph)
        		tf.import_graph_def(graphDef, name="")

        # load the class labels from disk
        labelMap = label_map_util.load_labelmap(label_path)
        categories = label_map_util.convert_label_map_to_categories(
        	labelMap, max_num_classes=num_classes,
        	use_display_name=True)
        self.categoryIdx = label_map_util.create_category_index(categories)

        # create a session to perform inference
        with self.model.as_default():
        	self.sess = tf.Session(graph=self.model)

        # grab a reference to the input image tensor and the boxes
        # tensor
        self.imageTensor = self.model.get_tensor_by_name("image_tensor:0")
        self.boxesTensor = self.model.get_tensor_by_name("detection_boxes:0")

        # for each bounding box we would like to know the score
        # (i.e., probability) and class label
        self.scoresTensor = self.model.get_tensor_by_name("detection_scores:0")
        self.classesTensor = self.model.get_tensor_by_name("detection_classes:0")
        self.numDetections = self.model.get_tensor_by_name("num_detections:0")
        
        testimg = cv2.imread('test.jpg')
        self.inspection(testimg)
        
        ###기종변경 신호 전송###

    def inspection(self, image):
        result = False
        session_count = None
        res_labels = [False] * num_classes
        insMap = [labelMap[i] for i in self.ins_labels]

        # prepare the image for detection
        (H, W) = image.shape[:2]

        if W > H and W > 640:
        	image = imutils.resize(image, width=640)

        # # otherwise, check to see if we should resize along the
        # # height
        elif H > W and H > 480:
        	image = imutils.resize(image, height=480)

        (H, W) = image.shape[:2]

        output = image.copy()

        image = cv2.cvtColor(image.copy(), cv2.COLOR_BGR2RGB)
        image = np.expand_dims(image, axis=0)

        # perform inference and compute the bounding boxes,
        # probabilities, and class labels
        (boxes, scores, labels, N) = self.sess.run(
            [self.boxesTensor, self.scoresTensor, self.classesTensor, self.numDetections],
            feed_dict={self.imageTensor: image})

        # squeeze the lists into a single dimension
        boxes = np.squeeze(boxes)
        scores = np.squeeze(scores)
        labels = np.squeeze(labels)

        cv2.rectangle(output, (1, 1), (637, 533), (0, 255, 0), 3)

        # loop over the bounding box predictions
        for (box, score, label) in zip(boxes, scores, labels):
            # if the predicted probability is less than the minimum
            # confidence, ignore it
            if score < min_confidence:
                continue
            
            # scale the bounding box from the range [0, 1] to [W, H]
            (startY, startX, endY, endX) = box
            startX = int(startX * W)
            startY = int(startY * H)
            endX = int(endX * W)
            endY = int(endY * H)

            
            # draw the prediction on the output image
            label = self.categoryIdx[label]
            idx = int(label["id"]) - 1
            
            if idx not in insMap:
                continue

            if ((idx == 0) or (idx == 2)) and (score < 0.99):
                continue

            # for i in range(0, 10):
            #     if idx == i:
            #         if score < self.inspection_percent[i]:
            #             session_count = True
            #             break

            # if session_count == True:
            #     continue

            showlabel = "{}: {} = {:.2f}".format(idx, label["name"], score)
                
            cv2.rectangle(output, (startX, startY), (endX, endY), (0, 0, 255), 2)
            cv2.putText(output, showlabel, (startX, startY), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            result = True
            res_labels[idx] = True
            
        if result:
            cv2.rectangle(output, (1, 1), (637, 533), (0, 0, 255), 5)
        # print('returning:', result)
        return [res_labels[i] for i in insMap], result, output
        
#메인프레임
main_frame = MainFrame(master=root)
main_frame.tkraise()

mdb = MysqlDB()
INS = InspectionClass()

SC = SocketCommunication()
SC.daemon=True
SC.start()

CTH = cameraRTSP()
CTH.daemon=True
CTH.start()

root.mainloop()
