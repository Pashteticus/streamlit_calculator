import os

os.system("python -m pip install xlsxwriter")
os.system("python -m pip install openpyxl")

import re
import streamlit as st
import zipfile
from io import BytesIO
import pandas as pd
from datetime import date
from currency_codes import get_currency_by_code, CurrencyNotFoundError
import requests
from xml.etree import ElementTree

import requests
import xml.etree.ElementTree as ET
from functools import lru_cache

@lru_cache(maxsize=100000)
def get_currency_rate(from_to_currency=None, date=None):
    try:
        list_foreign_currency = [currency for currency in from_to_currency if currency != 'RUB']
        list_ration_currency = []
        current_currency_rate = requests.get(f'https://www.cbr.ru/scripts/XML_daily.asp?date_req={date}')

        def get_parameter_currency_from_response(searching_value, char_code_currency):
            paramentr = ET.fromstring(current_currency_rate.text). \
                find(f'./Valute[CharCode="{char_code_currency}"]/{searching_value}').text
            if searching_value == 'Nominal':
                return int(paramentr)
            else:
                return float(paramentr.replace(',', '.'))

        def get_currency_ratio_with_rub(foreign_currency):
            nominal = get_parameter_currency_from_response("Nominal", foreign_currency)
            rub_for_nominal_currency = get_parameter_currency_from_response("Value", foreign_currency)
            count_currency_for_one_rub = nominal / rub_for_nominal_currency
            return count_currency_for_one_rub

        for currency in list_foreign_currency:
            list_ration_currency.append(get_currency_ratio_with_rub(currency))

        if from_to_currency[0] == 'RUB':
            return list_ration_currency[0]
        elif from_to_currency[1] == 'RUB':
            return 1 / list_ration_currency[0]
        else:
            return list_ration_currency[1] / list_ration_currency[0]
    except:
        return 0


class NalogSummarizer:
    def __init__(self):
        self.final_df = {
            "act": pd.DataFrame(
                columns=["Дата", "Переоценка", "Валюта", "Валюта/RUB", "Тикер", "Операция", "Кол-во", "Сумма",
                         "Сумма RUB"]),
            "ft_act": pd.DataFrame(
                columns=["Дата", "Переоценка", "Валюта", "Валюта/RUB", "Тикер", "Операция", "Кол-во", "Сумма",
                         "Сумма RUB"]),
            "ft_non_act": pd.DataFrame(
                columns=["Дата", "Переоценка", "Валюта", "Валюта/RUB", "Тикер", "Операция", "Кол-во", "Сумма",
                         "Сумма RUB"]),
            "div": pd.DataFrame(
                columns=["Дата", "Валюта", "Валюта/RUB", "Источник", "Доход", "Удержано", "Доход RUB", "Удержано RUB",
                         "Удержано %", "Ставка", "Зачтено RUB", "Доплата RUB", "Описание"]),
            "proc": pd.DataFrame(
                columns=["Дата", "Валюта", "Валюта/RUB", "Источник", "Доход", "Удержано", "Расход", "Доход RUB",
                         "Удержано RUB",
                         "Удержано %", "Ставка", "Зачтено RUB", "Доплата RUB", "Описание"]),
            "moves": pd.DataFrame(
                columns=["Год", "Актив", "Валюта", "Код валюты", "Начало", "Зачислено", "Списано", "Конец"])
        }
        self.non_act_tick = {"PR", "MF", "RUON", "1MFR", "CR", "CNY",
                             "Eu", "Si", "USDRUBF", "EURRUBF", "CNYRUBF",
                             "TY", "TRY", "HK", "HKD", "AE", "AED", "I2", "INR",
                             "KZ", "KZT", "AR", "AMD", "ED", "AU", "AUDU", "GU",
                             "GBPU", "CA", "UCAD", "CF", "UCHF", "JP", "UJPY", "TR",
                             "UTRY", "UC", "UCNY", "EC", "ECAD", "EG", "EGBP", "EJ", "EJPY",
                             "BR", "GD", "GOLD", "GL", "GLDRUBF", "PD", "PLD", "PT", "PLT",
                             "SV", "SILV", "SA", "SUGR", "SL", "SLV", "AM", "ALMIN",
                             "CL", "Co", "GO", "GLD", "Nl", "Zn", "NG", "WH", "W4",
                             "WHEAT", "Su", "SUGAR", "Si", "CR", "CNY"}

    def summarize_final_df(self):
        # summarize dividends
        summ_div = [["Всего", '', '', '', '', '', self.final_df['div']['Доход RUB'].sum(),
                     self.final_df['div']['Удержано RUB'].sum(), "10%", "13%",
                     self.final_df['div']['Зачтено RUB'].sum(), self.final_df['div']['Доплата RUB'].sum(), '']]
        summ_div = pd.DataFrame(summ_div, columns=self.final_df['div'].columns)
        self.final_df['div'] = pd.concat([self.final_df['div'], summ_div], ignore_index=True)

        # summarize acts
        try:
            sm = self.final_df['act']['Сумма RUB'].sum()
            summ_act = [
                ["Всего", '', '', '', '', '', '', '', self.final_df['act']['Сумма RUB'].sum()],
                self.final_df['act'].columns,
                ["Доходы", '', '', '', '', '', '', '',
                 self.final_df['act'][self.final_df['act']['Операция'] == 'Реализация']['Сумма RUB'].sum()],
                ["Расходы", '', '', '', '', '', '', '',
                 self.final_df['act'][self.final_df['act']['Операция'] == 'Приобретение']['Сумма RUB'].sum()],
                ["Ставка", '', '', '', '', '', '', '', "13%"],
                ["Доплаты RUB", '', '', '', '', '', '', '', max(0, 0.13 * sm)],
                ["Убыток", '', '', '', '', '', '', '', -min(0, sm)],
                ["Начало истории", '', '', '', '', '', '', '', self.final_df['act']['Дата'].iloc[0]]
            ]
            summ_act = pd.DataFrame(summ_act, columns=self.final_df['act'].columns)
            self.final_df['act'] = self.final_df['act'].reset_index().drop(columns=['index']).sort_values(by='Тикер')
            self.final_df['act'] = pd.concat([self.final_df['act'], summ_act], ignore_index=True)
        except:
            pass

        # summarize ft_act2
        try:
            sm = self.final_df['ft_act']['Сумма RUB'].sum()
            summ_act = [
                ["Всего", '', '', '', '', '', '', '', self.final_df['ft_act']['Сумма RUB'].sum()],
                ["Доходы", '', '', '', '', '', '', '',
                 self.final_df['ft_act'][self.final_df['ft_act']['Операция'] == 'Продажа']['Сумма RUB'].sum()],
                ["Расходы", '', '', '', '', '', '', '',
                 self.final_df['ft_act'][self.final_df['ft_act']['Операция'] == 'Покупка']['Сумма RUB'].sum()],
                ["Убыток", '', '', '', '', '', '', '', -min(0, sm)],
                ["Начало истории", '', '', '', '', '', '', '', self.final_df['ft_act']['Дата'].iloc[0]]
            ]
            summ_act = pd.DataFrame(summ_act, columns=self.final_df['ft_act'].columns)
            self.final_df['ft_act'] = self.final_df['ft_act'].reset_index().drop(columns=['index']).sort_values(
                by='Тикер')
            self.final_df['ft_act'] = pd.concat([self.final_df['ft_act'], summ_act], ignore_index=True)
        except:
            pass

        # summarize ft_act3
        try:
            sm = self.final_df['ft_non_act']['Сумма RUB'].sum()
            summ_act = [
                ["Всего", '', '', '', '', '', '', '', self.final_df['ft_non_act']['Сумма RUB'].sum()],
                ["Доходы", '', '', '', '', '', '', '',
                 self.final_df['ft_non_act'][self.final_df['ft_non_act']['Операция'] == 'Продажа']['Сумма RUB'].sum()],
                ["Расходы", '', '', '', '', '', '', '',
                 self.final_df['ft_non_act'][self.final_df['ft_non_act']['Операция'] == 'Покупка']['Сумма RUB'].sum()],
                ["Убыток", '', '', '', '', '', '', '', -min(0, sm)],
                ["Начало истории", '', '', '', '', '', '', '', self.final_df['ft_non_act']['Дата'].iloc[0]]
            ]
            summ_act = pd.DataFrame(summ_act, columns=self.final_df['ft_non_act'].columns)
            self.final_df['ft_non_act'] = self.final_df['ft_non_act'].reset_index().drop(columns=['index']).sort_values(
                by='Тикер')
            self.final_df['ft_non_act'] = pd.concat([self.final_df['ft_non_act'], summ_act], ignore_index=True)
        except:
            pass

    def get_csv_moves(self, df):
        lines = [df.iloc[i][0].split(',') for i in range(len(df))]
        useful_lines = []
        for ln in lines:
            if 'Period' in ln:
                year = ln[-1][1:5]
        for line in lines:
            lin = [x.lower() for x in line]
            merg_line = ''.join(lin)
            if 'отчет о денежных' in merg_line and 'базовой' not in merg_line:
                if 'data' in merg_line:
                    useful_lines.append(line[2:])
        nw = []
        cur = []
        for i in range(0, len(useful_lines)):
            cur.append(useful_lines[i])
            if 'Конечная расчетная сумма средств' in cur[-1]:
                nw.append(cur)
                cur = []
        useful_lines = nw
        fact_lines = []
        for val in useful_lines:
            cur_row = [year, "Денежные средства", val[0][1]]
            try:
                cur_row.append(get_currency_by_code(val[0][1]).numeric_code)
            except CurrencyNotFoundError:
                cur_row.append("")
            cur_row.append(float(val[0][2]))
            z, s = 0, 0
            for el in val[1:-2]:
                if float(el[2]) > 0:
                    z += float(el[2])
                else:
                    s += float(el[2])
            cur_row += [z, s]
            cur_row.append(float(val[-2][2]))
            fact_lines.append(cur_row)

        act_df = pd.DataFrame(fact_lines,
                              columns=["Год", "Актив", "Валюта", "Код валюты", "Начало", "Зачислено", "Списано",
                                       "Конец"])
        act_df['Больше 600к'] = ["Да" if act_df['Зачислено'].iloc[i] + act_df['Списано'].iloc[i] >= 600000 else "Нет"
                                 for i in range(len(act_df))]
        self.final_df['moves'] = pd.concat([self.final_df['moves'], act_df], ignore_index=True)

    def get_csv_dividend(self, df):
        lines = [df.iloc[i][0].split(',') for i in range(len(df))]
        cur_header = []
        useful_lines = []
        useful_header = []
        for lin in lines:
            if "Header" in lin:
                cur_header = lin
            line = [x.lower() for x in lin]
            merge_line = ''.join(line)
            if 'data' in merge_line and ('дивиденды' in line or 'удерживаемый налог' in line) and not 'nav' in \
                                                                                                      merge_line and not 'отчет' in merge_line and not 'всего' in line:
                useful_header = cur_header
                useful_lines.append(lin)
        act_df = pd.DataFrame()
        res = pd.DataFrame(useful_lines, columns=useful_header)
        res = res[res['Удерживаемый налог'] == 'Дивиденды']
        act_df['Дата'] = [x for x in res['Дата']]
        act_df['Валюта'] = [x.upper() for x in res['Валюта']]
        act_df['Валюта/RUB'] = [
            get_currency_rate(tuple([act_df['Валюта'].iloc[i].upper(), "RUB"]),
                              date=f"{str(act_df['Дата'].iloc[i])[8:10]}/{str(act_df['Дата'].iloc[i])[5:7]}/{str(act_df['Дата'].iloc[i])[:4]}")
          if len(
                str(act_df['Дата'].iloc[i])) > 0 else 0 for i in range(len(act_df))]
        act_df["Источник"] = [x.split()[0].upper()[:x.index('(')] for x in res['Описание']]
        act_df["Доход"] = [float(''.join([w for w in x if w.isdigit() or w == '.'])) for x in res['Сумма']]
        act_df["Удержано"] = act_df['Доход'] * 0.1
        act_df["Доход RUB"] = act_df['Доход'] * act_df['Валюта/RUB']
        act_df["Удержано RUB"] = act_df['Доход RUB'] * 0.1
        act_df['Удержано %'] = "10%"
        act_df['Ставка'] = "13%"
        act_df['Зачтено RUB'] = act_df["Удержано RUB"]
        act_df['Доплата RUB'] = act_df['Доход RUB'] * 0.03
        act_df['Описание'] = res['Описание']
        self.final_df['div'] = pd.concat([self.final_df['div'], act_df], ignore_index=True)

    def get_csv_act(self, df):
        lines = [df.iloc[i][0].split(',') for i in range(len(df))]
        cur_header = []
        useful_lines = []
        useful_header = []
        for line in lines:
            if "Header" in line:
                cur_header = line
            line = [x.lower() for x in line]
            merge_line = ''.join(line)
            if ('акции' in line or 'акция' in line) and 'сделк' in merge_line and \
                    'total' not in merge_line and 'order' in merge_line:
                useful_header = cur_header
                useful_lines.append(line[1:])
        act_df = pd.DataFrame()
        useful_lines = useful_lines[:-1]
        res = pd.DataFrame(useful_lines, columns=useful_header)
        act_df['Дата'] = ['-'.join(re.findall("\d+", x)) for x in res['Символ']]
        act_df['Переоценка'] = act_df['Дата']
        act_df['Валюта'] = [x.upper() for x in res['Класс актива']]
        act_df['Валюта/RUB'] = [
            get_currency_rate(tuple([act_df['Валюта'].iloc[i].upper(), "RUB"]),
                              date=f"{str(act_df['Дата'].iloc[i][8:10])}/{str(act_df['Дата'].iloc[i][5:7])}/{str(act_df['Дата'].iloc[i][:4])}")
            if len(
                str(act_df['Дата'].iloc[i])) > 0 else 0 for i in range(len(act_df))]
        act_df["Тикер"] = [x.upper() for x in res['Валюта']]
        act_df["Операция"] = "Приобретение"
        act_df["Кол-во"] = [float(x) if len(x) > 0 else 0 for x in res['Количество']]
        act_df["Сумма"] = [float(x) if len(x) > 0 else 0 for x in res['Цена транзакции']]
        act_df2 = act_df.copy()
        act_df2['Операция'] = 'Реализация'
        act_df2['Кол-во'] = [-float(x) if len(x) > 0 else 0 for x in res['Количество']]
        act_df2['Сумма'] = res['Цена закрытия'].astype('float')
        act_df = pd.concat((act_df, act_df2), axis=0)
        act_df['Сумма RUB'] = -act_df['Валюта/RUB'] * act_df['Сумма'] * act_df['Кол-во']
        act_df = act_df.sort_values(by=['Дата', 'Операция'])
        self.final_df['act'] = pd.concat([self.final_df['act'], act_df], ignore_index=True)

    def parse_csv(self, df):
        try:
            self.get_csv_act(df)
        except Exception as e:
            print("ERROR CSV ACT", e)
        try:
            self.get_csv_dividend(df)
        except Exception as e:
            print("ERROR CSV DIV", e)
        try:
            self.get_csv_moves(df)
        except Exception as e:
            print("ERROR CSV MOVES", e)

    def parse_xlsx(self, df):
        try:
            self.get_xlsx_f(df)
        except Exception as e:
            print("ERROR XLSX F", e)
        try:
            self.get_xlsx_act(df)
        except Exception as e:
            print("ERROR XLSX ACT", e)
        try:
            self.get_xlsx_ff(df)
        except Exception as e:
            print("ERROR XLSX FF", e)

    def get_xlsx_ff(self, df):
        dff = df.copy()
        for i in range(1, len(dff)):
            if 'Валюта' in ''.join([str(x) for x in dff.iloc[i].values]):
                val = dff.iloc[i].values[2]
            if 'Тикер' in dff.iloc[i].values and 'сделк' in ''.join([str(x) for x in dff.iloc[i - 1].values]):
                dff.columns = dff.iloc[i]
                dff = dff.iloc[i + 1:]
                break
        dff = dff[(dff['Вид'] == 'Купля') + (dff['Вид'] == 'Продажа')]
        dff = dff.reset_index()
        res_df = pd.DataFrame()
        res_df['Дата'] = ['-'.join(re.findall('\d+', x)[:3][::-1]) for x in dff['Время']]
        res_df['Переоценка'] = res_df['Дата']
        res_df['Валюта'] = val
        res_df['Валюта/RUB'] = [
            get_currency_rate(tuple([res_df['Валюта'].iloc[i].upper(), "RUB"]),
                              date=f"{res_df['Дата'].iloc[i][8:10]}/{res_df['Дата'].iloc[i][5:7]}/{res_df['Дата'].iloc[i][:4]}")
            if len(
                res_df['Дата'].iloc[i]) > 0 else 0 for i in range(len(res_df))]
        res_df['Тикер'] = dff['Тикер']
        res_df['Операция'] = dff['Вид'].str.replace('Купля', 'Приобретение')
        res_df['Кол-во'] = abs(dff['Кол-во'])
        res_df['Сумма'] = [-dff['Сумма'].iloc[i] if res_df['Операция'].iloc[i] == 'Покупка' else dff['Сумма'].iloc[i]
                           for i in
                           range(len(dff))]
        res_df['Сумма RUB'] = res_df['Сумма'] * res_df['Валюта/RUB']
        act_ind, non_act_ind = [], []
        for i in range(len(res_df)):
            if res_df['Тикер'].iloc[i] in self.non_act_tick:
                non_act_ind.append(i)
            else:
                act_ind.append(i)
        self.final_df['ft_act'] = pd.concat([self.final_df['ft_act'], res_df.iloc[act_ind]], ignore_index=True)
        self.final_df['ft_non_act'] = pd.concat([self.final_df['ft_non_act'], res_df.iloc[non_act_ind]],
                                                ignore_index=True)

    def get_xlsx_f(self, df):
        dct = {'Рубль': 'RUB', 'Доллар': "USD", "Dollar": "USD", "RUB": "RUB", "USD": "USD"}
        full_df = df.copy()
        df = df[df.columns[:7]]
        df = pd.concat((df, full_df[full_df.columns[12]]), axis=1)
        df.columns = ['Дата', 'Время', 'Тип', 'Тикер', 'Операция', 'Кол-во', 'Цена', 'Валюта']
        df = df[(df['Операция'] == 'Покупка') + (df['Операция'] == 'Продажа')]
        df = df.dropna()
        df['Цена'] = df['Цена'].astype(float)
        df['Кол-во'] = df['Кол-во'].astype(float)
        df = df.reset_index()
        res_df = pd.DataFrame()
        res_df['Дата'] = [x.date() for x in df['Дата']]
        res_df['Переоценка'] = res_df['Дата']
        res_df['Валюта'] = [dct[x] for x in df['Валюта']]

        res_df['Валюта/RUB'] = [
            get_currency_rate(tuple([res_df['Валюта'].iloc[i].upper(), "RUB"]),
                              date=f"{res_df['Дата'].iloc[i].day}/{res_df['Дата'].iloc[i].month}/{res_df['Дата'].iloc[i].year}")
            if len(
                res_df['Дата'].iloc[i]) > 0 else 0 for i in range(len(res_df))]

        res_df['Дата'] = ['-'.join([str(res_df['Дата'].iloc[i].year),
                                    str(res_df['Дата'].iloc[i].month),
                                    str(res_df['Дата'].iloc[i].day)]) for i in range(len(res_df['Дата']))]
        res_df['Переоценка'] = res_df['Дата']
        res_df['Тикер'] = [x.split('-')[0] for x in df['Тикер']]
        res_df['Операция'] = df['Операция']
        res_df['Кол-во'] = df['Кол-во']
        res_df['Сумма'] = [-df['Цена'].iloc[i] if df['Операция'].iloc[i] == 'Покупка' else df['Цена'].iloc[i] for i in
                           range(len(df))]
        res_df['Сумма RUB'] = res_df['Валюта/RUB'] * res_df['Сумма'] * res_df['Кол-во']
        act_ind, non_act_ind = [], []
        for i in range(len(res_df)):
            if res_df['Тикер'].iloc[i] in self.non_act_tick:
                non_act_ind.append(i)
            else:
                act_ind.append(i)
        self.final_df['ft_act'] = pd.concat([self.final_df['ft_act'], res_df.iloc[act_ind]], ignore_index=True)
        self.final_df['ft_non_act'] = pd.concat([self.final_df['ft_non_act'], res_df.iloc[non_act_ind]],
                                                ignore_index=True)

    def get_xlsx_act(self, df):
        dff = df.copy()
        dff = dff[abs(dff[' Прибыль в RUR ']) > 0]
        dff2 = dff.copy()
        dff[' Операция '] = 'Реализация'
        dff2[' Операция '] = 'Приобретение'
        dff2[' Сумма '] = dff2[' Сумма '] - dff2[' Прибыль ']
        dff2[' Количество '] = -dff2[' Количество ']
        dff2[' Цена '] = dff2[' Сумма '] / dff2[' Количество ']
        dff2[' Дата расчетов '] = dff[' Дата расчетов '].iloc[0]
        dff = pd.concat((dff, dff2), axis=0)
        res = pd.DataFrame()
        res['Дата'] = dff[' Дата расчетов ']
        res['Переоценка'] = res['Дата']
        res['Валюта'] = dff[' Валюта ']
        res['Валюта/RUB'] = dff[' Курс валюты ']
        res['Тикер'] = dff[' Тикер ']
        res['Операция'] = dff[' Операция ']
        res['Кол-во'] = dff[' Количество ']
        res['Сумма'] = dff[' Сумма ']
        res['Сумма RUB'] = res['Сумма'] * res['Валюта/RUB']
        res['Кол-во'] = -res['Кол-во']
        res = res.sort_values(by=['Дата', 'Операция'])
        self.final_df['act'] = pd.concat([self.final_df['act'], res], ignore_index=True)

    def get_main_df(self):
        df = pd.DataFrame()
        return df

    def save_res(self, result_path):
        writer = pd.ExcelWriter(result_path, engine='xlsxwriter')
        main_df = self.get_main_df()
        main_df.to_excel(writer, sheet_name='Главная', index=False)
        self.final_df['act'].to_excel(writer, sheet_name='Табл. 1', index=False)
        self.final_df['ft_act'].to_excel(writer, sheet_name='Табл. 2', index=False)
        self.final_df['ft_non_act'].to_excel(writer, sheet_name='Табл. 3', index=False)
        self.final_df['div'].to_excel(writer, sheet_name='Табл. 4 Дивиденды', index=False)
        self.final_df['proc'].to_excel(writer, sheet_name='Табл. 5 Проценты', index=False)
        self.final_df['moves'].to_excel(writer, sheet_name='Табл. 6 Движение средств', index=False)
        writer.close()

    def process_file(self, file_path):
        if file_path[-3:] == 'csv':
            df = pd.read_csv(file_path, sep='delimeter', engine='python')
            self.parse_csv(df)
        else:
            df = pd.read_excel(file_path)
            self.parse_xlsx(df)

    def process_files(self, file_path, result_path):
        files = file_path.split(',')
        end_path = result_path
        for i, file in enumerate(files):
            self.process_file(file)
        self.summarize_final_df()
        self.save_res(end_path)


def save_uploaded_file(uploaded_file):
    with open(os.path.join("tempDir", uploaded_file.name), "wb") as f:
        f.write(uploaded_file.getbuffer())


def main():
    prs = NalogSummarizer()
    st.title("Генератор финансовых отчётов")

    # Загрузка нескольких файлов
    uploaded_files = st.file_uploader("Выберите файлы", accept_multiple_files=True)
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            save_uploaded_file(uploaded_file)

    # Смотрим тип файлов xlsx или csv и запускаем скрипт из main.py с нужными аргументами
    if st.button("Создать отчёт"):
        # Получаем имена скачанных файлов в дирректории и записываем их в список
        full_paths = [os.path.join("tempDir", name) for name in os.listdir("tempDir")]

        if len(full_paths) == 1:
            prs.process_files(full_paths[0], "resultDir/result.xlsx")
        # Случай, если у нас несколько файлов на вход
        else:
            # Запускаем скрипт с нужными аргументами
            prs.process_files(",".join(full_paths), "resultDir/result.xlsx")

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_name in os.listdir("resultDir"):
                file_path = os.path.join("resultDir", file_name)
                zip_file.write(file_path, file_name)

        # Очистка временной директории

        for file_name in os.listdir("tempDir"):
            os.remove(os.path.join("tempDir", file_name))

        # Скачиваем архив и очищаем его после
        st.download_button(label="Скачать архив",
                           data=zip_buffer,
                           file_name="result.zip",
                           mime='application/zip')
        for file_name in os.listdir("resultDir"):
            os.remove(os.path.join("resultDir", file_name))
        # Убираем прикреплённые файлы из интерфейса streamlit
        st.empty()


if __name__ == "__main__":
    if not os.path.exists('tempDir'):
        os.makedirs('tempDir')
    else:
        for file_name in os.listdir("tempDir"):
            os.remove(os.path.join("tempDir", file_name))
    if not os.path.exists('resultDir'):
        os.makedirs('resultDir')
    main()
