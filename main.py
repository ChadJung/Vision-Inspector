import binascii
import datetime
import glob
import os
import pickle
import re
import socket
import threading
import time
import tkinter as tk

import cv2
import numpy as np
from openpyxl import Workbook

from _thread import *
from DB import MysqlDB
from inspection import InspectionClass
from KoreanPathCV2 import imread, imwrite
from MainFrame import MainFrame
from PIL import Image, ImageTk
from pypylon import genicam, pylon

root = tk.Tk()
root.overrideredirect(True)

HOST = '10.10.4.21' # PLC IP
PORT = 4001         # PLC PORT

# HOST = 'localhost'

BASE_PATH = os.getcwd()
DESKTOP = '/'.join(BASE_PATH.split(os.path.sep)[:-1])

#------------------------------------------------------
dataPath = DESKTOP+'/data/images'
insresPath = DESKTOP+'/data/insResult'
#------------------------------------------------------


class cameraRTSP(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.inspection = False # Inspection flag
        self.ins_result = False # Inspection result

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

        if not os.path.isdir(DESKTOP+'/data'):
            os.mkdir(DESKTOP+'/data')
            os.mkdir(DESKTOP+'/data/excel')
            os.mkdir(DESKTOP+f'/{dataPath}')
            os.mkdir(DESKTOP+f'/{insresPath}')        

    def clock(self):
        TIME = time.localtime(time.time())
        YYYY = TIME.tm_year
        MM = TIME.tm_mon
        DD = TIME.tm_mday
        H = TIME.tm_hour
        M = TIME.tm_min
        S = TIME.tm_sec
        dt = f'{YYYY:04d}-{MM:02d}-{DD:02d} {H:02d}:{M:02d}:{S:02d}'
        DT = datetime.datetime(YYYY, MM, DD)
        tm = DT + datetime.timedelta(days=1)
        self.nday = f'{YYYY:04d}-{tm.month:02d}-{tm.day:02}'
        # print(self.nday)

        self.currentDatetime = dt
        self.Date = dt.split(' ')[0]
        self.Time = dt.split(' ')[1]
        main_frame.main_canvas.itemconfig(main_frame.out_time, text=dt)


    def run(self):

        try:
            info = pylon.DeviceInfo()
            #카메라 시리얼 넘버 변경 필요
            info.SetSerialNumber("23219221") ###

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
            converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

            main_frame.main_canvas.itemconfig(main_frame.camera_lamp, image=main_frame.main_frame_green_lamp)

            frameCount = insCount = outCount = 0
            pointFrame = [0, 5, 10, 15, 20] ### 몇번째 프레임인지 테스트 필요
            self.pointIns = [False] * 5
            saved = True
            ins_text = {True: 'ng', False: 'ok'}
            imgPath = ''
            while camera.IsGrabbing():

                self.clock()

                startTime = time.time()

                grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

                if grabResult.GrabSucceeded():
                    image = converter.Convert(grabResult)
                    self.img = image.GetArray()
                    # img = self.img.copy()
                    #insepction
                    if self.inspection:
                        startTime = time.time()
                        saved = False
                        bc = SC.barcode
                        values = bc.split(' ')
                        modelName = values[0]
                        lotNo = values[2]


                        text = re.sub('[-=+,#/\?:^$.@*\"※~&%ㆍ!』\\‘|\(\)\[\]\<\>`\'…》]', '', str(time.time()))

                        # Data recording
                        if main_frame.recording and len(os.listdir('data/images')) < 10000:
                            imwrite(f'{dataPath}/image_{text}.jpg', self.img)

                        saved = self.ins_result = False

                        # Inspection result recording
                        partial_result, self.ins_result, self.img = INS.inspection(self.img)
                        # print('ins_result:', self.ins_result)
                        if insCount in pointFrame:
                            idx = pointFrame.index(insCount)
                            imwrite(f'{insresPath}/image_{text}.jpg', self.img)
                            main_frame.show_partial_image(self.img, idx)

                        main_frame.main_canvas.itemconfig(main_frame.ng_image, state = 'normal' if self.ins_result else 'hidden')
                        main_frame.main_canvas.itemconfig(main_frame.ok_image, state = 'hidden' if self.ins_result else 'normal')
                        # print(partial_result)
                        for i in range(main_frame.row_current):
                            main_frame.main_canvas.itemconfig(main_frame.partial_result[i], image = main_frame.main_frame_small_ng if partial_result[i] else main_frame.main_frame_small_ok)
                        insCount += 1

             

                    elif saved == False:
                        main_frame.total += 1
                        main_frame.ng += 1 if self.ins_result else 0
                        main_frame.ok += 0 if self.ins_result else 1
                        
                        main_frame.main_canvas.itemconfig(main_frame.total_count, text=str(main_frame.total))
                        main_frame.main_canvas.itemconfig(main_frame.ok_count, text=str(main_frame.ok))
                        main_frame.main_canvas.itemconfig(main_frame.ng_count, text=str(main_frame.ng))

                        bc = SC.barcode
                        values = bc.split(' ')
                        modelName = values[0]
                        lotNo = values[2]
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
                            # Only saved in DB
                            ("imgpath", f"'{imgPath}'"),
                            ("name", f"'{modelName}'"),
                            ("type", f"'{self.modelDic[modelName]}'")
                        ]
                        mdb.writeSql(valueList)
                        mdb.readSql(text=self.Date, StartDate=self.Date, EndDate=self.nday)
                        saved = True
                        insCount = 0
                        self.ins_result = True if True in self.pointIns else False
                        self.pointIns = [False] * 5

                    main_frame.show_img(self.img)
                    # print("[INFO] Elapsed time:", time.time() - startTime)
                else:
                    print("Error: ", grabResult.ErrorCode, grabResult.ErrorDescription)
                grabResult.Release()
            camera.Close()

        except genicam.GenericException as e:
            # Error handling.
            print("An exception occurred : ", e)
            main_frame.main_canvas.itemconfig(main_frame.camera_lamp, image=main_frame.main_frame_red_lamp)


class SocketCommunication(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        print('Notice : [Socket Connecting. wait please]')
        self.client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM) 
        self.client_socket.connect((HOST, PORT)) 
        print('Notice : [Socket Connected]')
        main_frame.main_canvas.itemconfig(main_frame.plc_lamp, image=main_frame.main_frame_green_lamp)
        # self.client_socket.send(b'ready')
        # print('ready sent')
        self.barcode = '96125-L2200 200326 52524 UNICK'

    def run(self):
        prev = None # prev fetched time
        while True:
            try:
                data = self.client_socket.recv(1024)
                data = data.decode()
                print('recv:', data)

                if 'UNICK' in data:
                    # print('qr recv')
                    self.barcode, tmty = data.split('UNICK')
                    ### 시간 + 기종번호 ###
                    self.barcode += ' UNICK'

                    values = self.barcode.split(' ')
                    modelName = values[0]
                    lotNo = values[2]
 
                    main_frame.main_canvas.itemconfig(main_frame.product_no, text=modelName)
                    main_frame.main_canvas.itemconfig(main_frame.product_type, text=CTH.modelDic[modelName])
                    main_frame.main_canvas.itemconfig(main_frame.lot, text=self.barcode)

                    text = b'comp'
                    self.client_socket.send(text)

                    print('comp sent')


                elif 'start' in data:
                    # print('start recv')
                    CTH.inspection = True
                    self.client_socket.send(b'comp1')
                    print('comp1 sent')


                elif 'reset' in data:
                    # print('reset recv')
                    CTH.inspection = False 
                    text = 'ng' if CTH.ins_result else 'ok'
                    text += self.barcode[:-5]
                    text = text.encode()
                    self.client_socket.send(text)
                    print("reset response: ",text)
                    
                else:
                    print('Not an Option')
                    #self.client_socket.send(b'na')

            except Exception as e:
                print(e)
                main_frame.main_canvas.itemconfig(main_frame.plc_lamp, image='')
                # self.client_socket.send(b'EXIT')
                self.client_socket.close()
                print('Notice : [Client Closed]')
                break


    def cleanText(readData):
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


#메인프레임
INS = InspectionClass()
main_frame = MainFrame(master=root, INS=INS)
main_frame.tkraise()

mdb = MysqlDB()


SC = SocketCommunication()
SC.daemon=True
SC.start()

CTH = cameraRTSP()
CTH.daemon=True
CTH.start()

root.mainloop()
