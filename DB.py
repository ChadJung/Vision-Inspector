import pymysql
from openpyxl import Workbook
import os

BASE_PATH = os.getcwd()
DESKTOP = '/'.join(BASE_PATH.split(os.path.sep)[:-1])

class MysqlDB():
    def __init__(self, host="localhost", user="root", password="yous7051!", db="unick"):
        self.db = pymysql.connect(host=host, user=user, password=password, db=db, charset="utf8")

    def readSql(self, text, typeName=None, result=None, StartDate=None, EndDate=None):
        curs = self.db.cursor()
        sql = "select no, lot, date, result, point1, point2, point3, point4, point5, barcode, imgpath from log"
        addvalue = False

        if typeName is not None:
            add = " WHERE " if addvalue is False else " AND "
            addvalue = True

            sql = sql + add + "name='{}'".format(typeName)

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

        curs.execute(sql)
        rows = curs.fetchall()
        
        self.writeExcel(rows, text)

    def writeSql(self, valueList):
        param = values = ""
        curs = self.db.cursor()
        for name, val in valueList:
            param = param + name + ", "
            values = values + val + ", "

        sql = "INSERT INTO log ({}) VALUES ({})".format(param[:-2], values[:-2])
        
        curs.execute(sql)
        self.db.commit()

    def writeExcel(self, data, text):
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

        wb.save(DESKTOP+"/data/excel/output{}.xlsx".format(text))
