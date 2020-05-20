import tkinter as tk

from PIL import Image, ImageTk

# Fonts
FONT = ("Impact 보통", 16, 'bold')
LFONT = ("Impact 보통", 22, 'bold')

class MainFrame(tk.Frame):
    #변수 선언
    def __init__(self, master=None, INS=None):
        super().__init__(master)
        self.master = master
        self.INS = INS
        # TK Image Variables
        self.main_frame_img = ImageTk.PhotoImage(file = 'bg/bg.png')
        self.main_frame_ng = ImageTk.PhotoImage(file = 'bg/ng.png')
        self.main_frame_ok = ImageTk.PhotoImage(file = 'bg/ok.png')
        self.main_frame_empty = ImageTk.PhotoImage(file = 'bg/cam_blank_main.png')
        self.main_frame_block = ImageTk.PhotoImage(file = 'bg/logo_block.png')
        self.main_frame_small_ok = ImageTk.PhotoImage(file = 'bg/ok_s.png')
        self.main_frame_small_ng = ImageTk.PhotoImage(file = 'bg/ng_s.png')
        self.main_frame_red_lamp = ImageTk.PhotoImage(file = 'bg/red.png')
        self.main_frame_green_lamp = ImageTk.PhotoImage(file = 'bg/green.png')
        self.main_frame_row = ImageTk.PhotoImage(file = 'bg/row.png')
        self.main_frame_config = ImageTk.PhotoImage(file = 'bg/configWindow.png')
        self.main_frame_selection = ImageTk.PhotoImage(file = 'bg/selectionWindow.png')
        self.main_frame_confirm = ImageTk.PhotoImage(file = 'bg/confirmWindow.png')

        # Inspection list variables(Inspection status)
        self.selection_print = ['충전로고\n인쇄상태', '  띠로고\n인쇄상태', '    범퍼\n누락상태','외관 상태','이종 검사','추가 예정','추가 예정','추가 예정']

        self.selection_text = ['충전로고 인쇄상태', '띠로고 인쇄상태', '범퍼누락상태','외관 상태','이종 검사','추가 예정','추가 예정','추가 예정']
        self.main_frame_partial_text = ['충전로고 인쇄상태', '띠로고 인쇄상태', '범퍼누락상태','외관 상태', '', '', '', ''] # 추가항목
        self.row_current = 4 # 현재 검사현황 항목 개수

        # Window Flag variables
        self.show_config = False    # CONFIG
        self.show_confirm = False   # CONFIRM(RESET)
        self.show_selection = False # SELECTION(INSPECTION)
        self.block = False

        # Inspection Count variables
        self.ok = 0
        self.ng = 0
        self.total = 0

        # Create the widgets
        self.create_widgets()

        # Thread Flag variables
        self.recording = False # True if video needs to be recorded
    
        # Partial inspection image variables
        self.cvtimg1 = [None] * 5
        self.cvtshow1 = [None] * 5
        self.img_path1 = [None] * 5


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
        self.partial_image = [self.main_canvas.create_image(71 + (220 * i), 911, image = '', anchor = 'nw') for i in range(5)]

        # 생산현황  
        self.product_no = self.main_canvas.create_text(1630, 200, text="품번", font=FONT, fill="white")
        self.product_type = self.main_canvas.create_text(1630, 237, text="차종", font=FONT, fill="white")
        self.lot = self.main_canvas.create_text(1630, 276, text="LOT", font=FONT, fill="white")
        self.out_time = self.main_canvas.create_text(1630, 313, text="검사시간", font=FONT, fill="white")
       
        # 검사현황
        self.partial_row = [self.main_canvas.create_image(1185, 388 + (i * 37), image = self.main_frame_row, anchor='nw', state='hidden') for i in range(7)] # row image
        self.partial_result = [self.main_canvas.create_image(1654.5, 388.5 + (i * 37), image = '', anchor='nw', state='hidden') for i in range(7)] # ok / ng
        self.partial_text = [self.main_canvas.create_text(1408, 406 + (i * 37), text=self.main_frame_partial_text[i], font=FONT, fill="white", state='hidden') for i in range(7)] # inspection label
        for i in range(self.row_current):
            self.main_canvas.itemconfig(self.partial_row[i], state='normal')
            self.main_canvas.itemconfig(self.partial_result[i], state='normal')
            self.main_canvas.itemconfig(self.partial_text[i], state='normal')

        # 생산정보
        self.total_count = self.main_canvas.create_text(1278, 787, text=str(self.total), font=FONT, fill="white")
        self.ng_count = self.main_canvas.create_text(1477, 787, text=str(self.ng), font=FONT, fill="white")
        self.ok_count = self.main_canvas.create_text(1679, 787, text=str(self.ok), font=FONT, fill="white")
       
        # 알림, 환경설정, 검증선택창
        self.confirm_window = self.main_canvas.create_image(960, 540, image = self.main_frame_confirm, anchor= 'center', state = 'hidden')
        self.selection_window = self.main_canvas.create_image(960, 540, image = self.main_frame_selection, anchor= 'center', state = 'hidden')
        self.config_window = self.main_canvas.create_image(960, 540, image = self.main_frame_config, anchor= 'center', state = 'hidden')

        # 검증선택
        self.selection_buttons = [self.main_canvas.create_text(769 + 381 * (i % 2), 378 + 139 * (i // 2), 
        text=self.selection_print[i], font=LFONT, fill='white', state='hidden') for i in range(8)]


        # Bind the Button events
        self.main_canvas.bind('<Button-1>', self.main_btn)
        self.main_canvas.bind('<Double-Button-1>', self.main_btn_db)
        self.main_canvas.pack()


    def remove_content(self, num): # For removing inspection points(labels)
        # print(f'remove: {num}')
        self.INS.ins_labels.pop(num)
        print(self.INS.ins_labels)
        self.main_canvas.itemconfig(self.partial_row[self.row_current-1], state='hidden')
        self.main_canvas.itemconfig(self.partial_text[self.row_current-1], state='hidden')
        self.main_canvas.itemconfig(self.partial_result[self.row_current-1], state='hidden')
        self.main_frame_partial_text[num:-1] = self.main_frame_partial_text[num + 1:]
        for i in range(num, self.row_current-1):
            self.main_canvas.itemconfig(self.partial_text[i], text=self.main_frame_partial_text[i])
        self.main_frame_partial_text[self.row_current-1] = ''


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
        print(x, y)
        
        # ADD MOUSE EVENTS
        # PLAIN MODE
        if not (self.show_config or self.show_confirm or self.show_selection):
            if x < 140 and y < 130: # CONFIG
                self.show_config = True
                self.main_canvas.itemconfig(self.config_window, state='normal')

            if 1185 < x < 1885 and 347 < y < 380 and self.row_current < 7: # ADD INSPECTION LABEL
                self.main_canvas.itemconfig(self.selection_window, state='normal')
                for i in range(8):
                    self.main_canvas.itemconfig(self.selection_buttons[i], state='normal')
                self.show_selection = True
                print(self.show_selection)

            for i in range(self.row_current): # REMOVE INSPECTION LABEL
                if 1843 < x < 1883 and 387 + (37 * i) < y < 421 + (37 * i):
                        remove = i
                        self.remove_content(remove)
                        self.row_current -= 1
                        # print("row:", self.row_current)
                        # print('content:', self.main_frame_partial_text)


            if 1783 < x < 1882 and 724 < y < 805: # RESET
                self.main_canvas.itemconfig(self.confirm_window, state='normal')
                self.show_confirm = True

        # SELECTION MODE
        elif self.show_selection:
            if not (510 < x < 1410 and 170 < y < 910):
                self.main_canvas.itemconfig(self.selection_window, state='hidden')
                for i in range(8):
                    self.main_canvas.itemconfig(self.selection_buttons[i], state='hidden')
                self.show_selection = False
            else: 
                for i in range(8):
                    if 644 + (381 * (i % 2)) < x < 894 + (381 * (i % 2)) and 326 + (139 * (i // 2)) < y < 426 + (139 * (i // 2)):
                        if self.selection_text[i] not in self.main_frame_partial_text:
                            self.INS.ins_labels.append(i)
                            self.main_frame_partial_text[self.row_current] = self.selection_text[i]
                            self.main_canvas.itemconfig(self.partial_row[self.row_current], state='normal')
                            self.main_canvas.itemconfig(self.partial_text[self.row_current], text=self.selection_text[i], state='normal')
                            self.row_current += 1
                        # print("row:", self.row_current)
                        # print('content:', self.main_frame_partial_text)
                        # self.main_canvas.itemconfig(self.selection_window, state='hidden')
                        # self.show_selection = False

        # CONFIRM MODE
        elif self.show_confirm:
            if not (660 < x < 1260 and 390 < y < 690):
                self.main_canvas.itemconfig(self.confirm_window, state='hidden')
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
                self.show_config = False


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
