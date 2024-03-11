'''
для добавления тикеров смотирм строчку 85
'''


import os

os.system("python -m pip install xlsxwriter")
os.system("python -m pip install openpyxl")

import re
import streamlit as st
import numpy as np
import zipfile
from io import BytesIO
import shutil
import pandas as pd
from datetime import date
from currency_codes import get_currency_by_code, CurrencyNotFoundError
import requests
from xml.etree import ElementTree

import requests
import xml.etree.ElementTree as ET
from functools import lru_cache

# код для получения валют
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
        # это переменная со всеми суммаризованными данными
        self.final_df = {
            "main_df": pd.DataFrame(),
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
        # вот сюда добавляем тикеры для таблицы 3, все остальные автоматически будут отнесены к таблице 2
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
    def get_min_data(self):
        mn = []
        for nm in self.final_df:
            if len(self.final_df) == 0:
                continue
            for ct in self.final_df[nm]:
                if 'дата' in ct.lower():
                    if 'Ставка' in self.final_df[nm][ct].values:
                        mn.append(str(self.final_df[nm][ct].iloc[:-7].min()))
                    else:
                        mn.append(str(self.final_df[nm][ct].iloc[:-6].min()))
        if len(mn) == 0:
            return "Нет данных"
        return min(mn)

    def get_max_data(self):
        mn = []
        for nm in self.final_df:
            if len(self.final_df) == 0:
                continue
            for ct in self.final_df[nm]:
                if 'дата' in ct.lower():
                    if 'Ставка' in self.final_df[nm][ct].values:
                        mn.append(str(self.final_df[nm][ct].iloc[:-7].max()))
                    else:
                        mn.append(str(self.final_df[nm][ct].iloc[:-6].max()))
        while 'Всего' in mn:
            mn = [x for x in mn if x != 'Всего']
        if len(mn) == 0:
            return "Нет данных"
        return max(mn)

    def summarize_final_df(self):
        # summarize dividends
        main_sum = 0
        main_df_div = [self.final_df['div']['Доход RUB'].sum(), self.final_df['div']['Удержано RUB'].sum(), self.final_df['div']['Доплата RUB'].sum()]
        try:
            act_sm = self.final_df['act']['Сумма RUB'].sum()
        except:
            act_sm = 0
        if len(self.final_df['div']) > 0:
            try:
                summ_div = [["Всего", '', '', '', '', '', self.final_df['div']['Доход RUB'].sum(),
                             self.final_df['div']['Удержано RUB'].sum(), "10%", "13%",
                             self.final_df['div']['Зачтено RUB'].sum(), self.final_df['div']['Доплата RUB'].sum(), '']]
                summ_div = pd.DataFrame(summ_div, columns=self.final_df['div'].columns)
                self.final_df['div'] = pd.concat([self.final_df['div'], summ_div], ignore_index=True)
                main_sum += max(self.final_df['div']['Доплата RUB'].sum(), 0)
            except Exception as e:
                print("ERROR SUM DIV", e)
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
            main_sum += max(0, 0.13 * sm)
            summ_act = pd.DataFrame(summ_act, columns=self.final_df['act'].columns)
            self.final_df['act']['Сумма RUB'] = np.round(self.final_df['act']['Сумма RUB'], 2)
            self.final_df['act'] = self.final_df['act'].reset_index().drop(columns=['index'])
            self.final_df['act'] = pd.concat([self.final_df['act'], summ_act], ignore_index=True)
        except Exception as e:
            print(f"SUM ACT ERROR: {e}")

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
            main_sum += max(self.final_df['ft_act']['Сумма RUB'].sum() * 0.13, 0)
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
            main_sum += max(0.13 * self.final_df['ft_non_act']['Сумма RUB'].sum(), 0)
            summ_act = pd.DataFrame(summ_act, columns=self.final_df['ft_non_act'].columns)
            self.final_df['ft_non_act'] = self.final_df['ft_non_act'].reset_index().drop(columns=['index']).sort_values(
                by='Тикер')
            self.final_df['ft_non_act'] = pd.concat([self.final_df['ft_non_act'], summ_act], ignore_index=True)
        except:
            pass

        # create main sheet
        try:
            src = [["Описание", "Налоговая база", "Удержано налогов", "Налоги к уплате"],
                   ["Прибыль от реализации ЦБ", act_sm, "", max(0, 0.13*act_sm)],
                   ["Прибыль от реализации ПФИ", "", "", ""],
                   ["Дивидендный доход", main_df_div[0], main_df_div[1], main_df_div[2]],
                   ["Доплата по ставке 15%", "", "", ""],
                   ["Всего", act_sm+main_df_div[0], "", max(0, 0.13*act_sm)+main_df_div[2]],
                   ["", "", "", ""],
                   ["Справочная информация", "", "", ""],
                   ["Брокеры", "", "", ""],
                   ["Счеты брокера", "", "", ""],
                   ["Отчетный год", "", "", self.get_max_data()],
                   ["Год начала истории", "", "", self.get_min_data()],
                   ["Корректировка после отчетного года", "", "", "нет"],
                   ["Страна резиденства", "", "", "RU"],
                   ["Валюта исчисления налогов", "", "", "RUB"],
                   ]
            self.final_df['main_df'] = pd.DataFrame(src)
        except Exception as e:
            print("ERROR MAIN SUM", e)

    def get_csv_moves(self, df):
        # функция для получения движения денежных средств из csv файлов (broker interactive llc например)
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
        # функция для получения информации о дивидендах
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
        act_df["Доход"] = [round(float(''.join([w for w in x if w.isdigit() or w == '.'])),2 ) for x in res['Сумма']]
        act_df["Удержано"] = [round(x*0.1, 2) for x in act_df['Доход']]
        act_df["Доход RUB"] = np.round(act_df['Доход'] * act_df['Валюта/RUB'], 2)
        act_df["Удержано RUB"] = np.round(act_df['Доход RUB'] * 0.1, 2)
        act_df['Удержано %'] = "10%"
        act_df['Ставка'] = "13%"
        act_df['Зачтено RUB'] = np.round(act_df["Удержано RUB"], 0)
        act_df['Доплата RUB'] = np.round(act_df['Доход RUB'] * 0.03, 0)
        act_df['Описание'] = res['Описание']
        self.final_df['div'] = pd.concat([self.final_df['div'], act_df], ignore_index=True)

    def get_csv_act(self, df):
        # функция для получения акций
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
        useful_lines = useful_lines
        res = pd.DataFrame(useful_lines, columns=useful_header)
        res['Количество'] = res['Количество'].astype(float)
        act_df['Дата'] = ['-'.join(re.findall("\d+", x)) for x in res['Символ']]
        act_df['Переоценка'] = act_df['Дата']
        act_df['Валюта'] = [x.upper() for x in res['Класс актива']]
        act_df['Валюта/RUB'] = [
            get_currency_rate(tuple([act_df['Валюта'].iloc[i].upper(), "RUB"]),
                              date=f"{str(act_df['Дата'].iloc[i][8:10])}/{str(act_df['Дата'].iloc[i][5:7])}/{str(act_df['Дата'].iloc[i][:4])}")
            if len(
                str(act_df['Дата'].iloc[i])) > 0 else 0 for i in range(len(act_df))]
        act_df["Тикер"] = [x.upper() for x in res['Валюта']]
        act_df["Операция"] = ["Приобретение" if x > 0 else "Реализация" for x in res['Количество']]
        act_df["Кол-во"] = res['Количество']
        act_df["Сумма"] = np.round([float(x) if len(x) > 0 else 0 for x in res['Выручка']], 2)
        act_df['Сумма RUB'] = np.round(act_df['Валюта/RUB'] * act_df['Сумма'], 2)
        if 'Комиссия/плата' in res:
            act_df2 = act_df.copy()
            act_df2['Операция'] = 'Торговая комиссия'
            act_df2['Кол-во'] = 0
            act_df2['Сумма'] = np.round([float(x) for x in res['Комиссия/плата']], 2)
            act_df2['Сумма RUB'] = act_df2['Сумма'] * act_df2['Валюта/RUB']
            act_df = pd.concat((act_df, act_df2), axis=0)
        act_df = act_df.sort_values(by=['Дата', 'Операция'])
        self.final_df['act'] = pd.concat([self.final_df['act'], act_df], ignore_index=True)

    def parse_csv(self, df):
        # функция для того, чтобы получить всю информацию из csv файлов
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

    def get_dif_xlsx_act(self, df):
        dff = df.copy()
        res = pd.DataFrame()
        q = [''.join([w for w in x if w != ' ']) for x in df.columns]
        dff.columns = q
        res['Дата'] = [str(x)[:10] for x in dff['Дата']]
        res['Переоценка'] = res['Дата']
        res['Валюта'] = dff['Валюта']
        res['Валюта/RUB'] = [
            get_currency_rate(tuple([res['Валюта'].iloc[i].upper(), "RUB"]),
                              date=f"{res['Дата'].iloc[i][8:10]}/{res['Дата'].iloc[i][5:7]}/{res['Дата'].iloc[i][:4]}")
            if len(
                res['Дата'].iloc[i]) > 0 else 0 for i in range(len(res))]
        res['Тикер'] = dff['Тикер']
        res['Операция'] = ['Приобретение' if 'Покупка' in x else 'Реализация' for x in dff['Операция']]
        res['Кол-во'] = [float(dff['Количество'].iloc[i]) if res['Операция'].iloc[i] == 'Приобретение' else -float(dff['Количество'].iloc[i]) for i in range(len(dff['Количество']))]
        res['Сумма'] = dff['Сумма']
        res['Сумма RUB'] = res['Сумма'] * res['Валюта/RUB']
        if 'Комиссия' in dff:
            act_df2 = res.copy()
            act_df2['Операция'] = 'Торговая комиссия'
            act_df2['Кол-во'] = 0
            act_df2['Сумма'] = np.round([float(x) for x in dff['Комиссия']], 2)
            act_df2['Сумма RUB'] = -act_df2['Сумма'] * act_df2['Валюта/RUB']
            res = pd.concat((res, act_df2), axis=0)
        res = res.sort_values(by=['Дата', 'Операция'])
        self.final_df['act'] = pd.concat([self.final_df['act'], res], ignore_index=True)

    def get_dif_xlsx_div(self, df):
        dff = df.copy()
        q = [''.join([w for w in x if w != ' ']) for x in df.columns]
        dff.columns = q
        act_df = pd.DataFrame()
        act_df['Дата'] = [str(x)[:10] for x in dff['Дата']]
        act_df['Валюта'] = [x for x in dff['Валюта']]
        act_df['Валюта/RUB'] = [
            get_currency_rate(tuple([act_df['Валюта'].iloc[i].upper(), "RUB"]),
                              date=f"{str(act_df['Дата'].iloc[i])[8:10]}/{str(act_df['Дата'].iloc[i])[5:7]}/{str(act_df['Дата'].iloc[i])[:4]}")
            if len(
                str(act_df['Дата'].iloc[i])) > 0 else 0 for i in range(len(act_df))]
        act_df["Источник"] = [x for x in dff['Тикер']]
        act_df["Доход"] = [round(float(''.join([w for w in str(x) if str(w).isdigit() or w == '.'])), 2) for x in dff['Сумма']]
        act_df["Доход"] += np.array([round(float(''.join([w for w in str(x) if str(w).isdigit() or w == '.'])), 2) for x in dff['Налогуброкера']])
        act_df["Удержано"] = [round(x * 0.1, 2) for x in act_df['Доход']]
        act_df["Доход RUB"] = np.round(act_df['Доход'] * act_df['Валюта/RUB'], 2)
        act_df["Удержано RUB"] = np.round(act_df['Доход RUB'] * 0.1, 2)
        act_df['Удержано %'] = "10%"
        act_df['Ставка'] = "13%"
        act_df['Зачтено RUB'] = np.round(act_df["Удержано RUB"], 0)
        act_df['Доплата RUB'] = np.round(act_df['Доход RUB'] * 0.03, 0)
        act_df['Описание'] = dff['Комментарий']
        self.final_df['div'] = pd.concat([self.final_df['div'], act_df], ignore_index=True)

    def get_dif_xlsx(self, sheets, sheet_names):
        for sh in sheet_names:
            if 'trades' in sh.lower():
                self.get_dif_xlsx_act(sheets.parse(sh))
            elif 'corpactions' in sh.lower():
                self.get_dif_xlsx_div(sheets.parse(sh))

    def parse_xlsx(self, file_path=None):
        df = pd.read_excel(file_path)
        # функция для получения информации из xlsx файлов
        try:
            with pd.ExcelFile(file_path) as xl:
                sh_names = xl.sheet_names
                self.get_dif_xlsx(xl, sh_names)
        except Exception as e:
            print("ERROR XLSX", e)
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
        # получаем фьючерсы
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
                str(res_df['Дата'].iloc[i])) > 0 else 0 for i in range(len(res_df))]
        res_df['Тикер'] = dff['Тикер']
        res_df['Операция'] = dff['Вид'].str.replace('Купля', 'Приобретение')
        res_df['Кол-во'] = abs(dff['Кол-во'])
        res_df['Сумма'] = np.round([-dff['Сумма'].iloc[i] if res_df['Операция'].iloc[i] == 'Покупка' else dff['Сумма'].iloc[i]
                           for i in
                           range(len(dff))], 2)
        res_df['Сумма RUB'] = np.round(res_df['Сумма'] * res_df['Валюта/RUB'], 2)
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
        # получаем фьючерсы (другой брокер)
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
                str(res_df['Дата'].iloc[i])) > 0 else 0 for i in range(len(res_df))]

        res_df['Дата'] = ['-'.join([str(res_df['Дата'].iloc[i].year),
                                    str(res_df['Дата'].iloc[i].month),
                                    str(res_df['Дата'].iloc[i].day)]) for i in range(len(res_df['Дата']))]
        res_df['Переоценка'] = res_df['Дата']
        res_df['Тикер'] = [x.split('-')[0] for x in df['Тикер']]
        res_df['Операция'] = df['Операция']
        res_df['Кол-во'] = df['Кол-во']
        res_df['Сумма'] = np.round([-df['Цена'].iloc[i] if df['Операция'].iloc[i] == 'Покупка' else df['Цена'].iloc[i] for i in
                           range(len(df))], 2)
        res_df['Сумма RUB'] = np.round(res_df['Валюта/RUB'] * res_df['Сумма'] * res_df['Кол-во'], 2)
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
        # получаем акции из xlsx
        dff = df.copy()
        dff = dff[abs(dff[' Прибыль в RUR ']) > 0]
        dff2 = dff.copy()
        dff[' Операция '] = 'Реализация'
        dff2[' Операция '] = 'Приобретение'
        dff2[' Сумма '] = np.round(dff2[' Сумма '] - dff2[' Прибыль '], 2)
        dff2[' Количество '] = -dff2[' Количество ']
        dff2[' Цена '] = np.round( dff2[' Сумма '] / dff2[' Количество '], 2)
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

    def save_res(self, result_path):
        # сохраняем все данные в итоговую xlsx таблицу с учетом форматирования на размер ячеек
        writer = pd.ExcelWriter(result_path, engine='xlsxwriter')
        self.final_df['main_df'].to_excel(writer, sheet_name='Главная', index=False)
        if len(self.final_df['act']) > 0:
            self.final_df['act'].to_excel(writer, sheet_name='Табл. 1', index=False)
            worksheet = writer.sheets['Табл. 1']
            for i, col in enumerate(self.final_df['act'].columns):
                column_len = self.final_df['act'][col].astype(str).str.len().max()
                column_width = max(column_len, len(col))
                worksheet.set_column(i, i, column_width)

        if len(self.final_df['ft_act']) > 0:
            self.final_df['ft_act'].to_excel(writer, sheet_name='Табл. 2', index=False)
            worksheet = writer.sheets['Табл. 2']
            for i, col in enumerate(self.final_df['act'].columns):
                column_len = self.final_df['act'][col].astype(str).str.len().max()
                column_width = max(column_len, len(col))
                worksheet.set_column(i, i, column_width)
        if len(self.final_df['ft_non_act']) > 0:
            self.final_df['ft_non_act'].to_excel(writer, sheet_name='Табл. 3', index=False)
            worksheet = writer.sheets['Табл. 3']
            for i, col in enumerate(self.final_df['act'].columns):
                column_len = self.final_df['act'][col].astype(str).str.len().max()
                column_width = max(column_len, len(col))
                worksheet.set_column(i, i, column_width)
        if len(self.final_df['div']) > 0:
            self.final_df['div'].to_excel(writer, sheet_name='Табл. 4 Дивиденды', index=False)
            worksheet = writer.sheets['Табл. 4 Дивиденды']
            for i, col in enumerate(self.final_df['act'].columns):
                column_len = self.final_df['act'][col].astype(str).str.len().max()
                column_width = max(column_len, len(col))
                worksheet.set_column(i, i, column_width)
        if len(self.final_df['proc']) > 0:
            self.final_df['proc'].to_excel(writer, sheet_name='Табл. 5 Проценты', index=False)
            worksheet = writer.sheets['Табл. 5 Проценты']
            for i, col in enumerate(self.final_df['act'].columns):
                column_len = self.final_df['act'][col].astype(str).str.len().max()
                column_width = max(column_len, len(col))
                worksheet.set_column(i, i, column_width)
        if len(self.final_df['moves']) > 0:
            self.final_df['moves'].to_excel(writer, sheet_name='Табл. 6 Движение средств', index=False)
            worksheet = writer.sheets['Табл. 6 Движение средств']
            for i, col in enumerate(self.final_df['act'].columns):
                column_len = self.final_df['act'][col].astype(str).str.len().max()
                column_width = max(column_len, len(col))
                worksheet.set_column(i, i, column_width)
        writer.close()

    # открываем и начинаем парсить файлы
    def process_file(self, file_path):
        if file_path[-3:] == 'csv':
            df = pd.read_csv(file_path, sep='delimeter', engine='python')
            self.parse_csv(df)
        else:
            self.parse_xlsx(file_path)

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

# streamlit приложение
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
