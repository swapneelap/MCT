#!/usr/bin/python3
from pandas_datareader import data as pdr
import yfinance as yf
import math
import numpy as np
import datetime as dt
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

daysFullAvg = 200
daysHalfAvg = 50
signalDays = 30
strengthDays = 14
RSIavgDays = 9
RSImatureDays = 260
finalFrame = pd.DataFrame()
symFrame = pd.DataFrame()
toWrite = pd.DataFrame()
################ FUNCTIONS ####################################

def Flip( frame ):
    "Flips the frame if not in past to present order."
    dateDelta = frame.at[0, 'Date'] - frame.at[1, 'Date']
    if dateDelta.days > 0:
        frame['Date'] = frame['Date'].values[::-1]
        frame['Close'] = frame['Close'].values[::-1]

    return frame;

def DropNAN( frame ):
    "Removes the NAN in .csv"
    faults = np.array([])
    for index in range(0, frame.shape[0]):
        if math.isnan(frame.at[index, 'Close']):
            faults = np.append(faults, [index])

    frame = frame.drop(faults)
    frame = frame.sort_index().reset_index(drop=True)
    return frame;

def DataRefining( frame ):
    "Adds the missing days' Close valus to make the data smooth"
    totalDays = frame.at[frame.shape[0]-1, 'Date'] - frame.at[0, 'Date']
    for index in range(1, totalDays.days+1):

        dateDelta = frame.at[index, 'Date'] - frame.at[index-1, 'Date']

        if dateDelta.days > 1:
            for delta in range(1, dateDelta.days):
                newRow = pd.DataFrame({'Date':(frame.at[index-1, 'Date'] + dt.timedelta(days=delta)), 'Close':frame.at[index-1, 'Close']}, index=[index+delta-1.5])
                frame = frame.append(newRow, ignore_index=False)
                frame = frame.sort_index().reset_index(drop=True)

    return frame;

def FullAverage( frame ):
    "Full exponential moving average"
    zeros = [0.0] * frame.shape[0]
    frame['FullAvg'] = zeros
    fullAvg = 0
    percentage = 2.0/(daysFullAvg+1)
    for index in range(0, frame.shape[0]):
        if index < daysFullAvg-1:
            fullAvg = fullAvg + frame.at[index, 'Close']
        elif index == daysFullAvg-1:
            fullAvg = (fullAvg + frame.at[index, 'Close'])/daysFullAvg
            frame.at[index, 'FullAvg'] = fullAvg
        else:
            fullAvg = (frame.at[index, 'Close'] * percentage) + (fullAvg * (1-percentage))
            frame.at[index, 'FullAvg'] = fullAvg

    return frame;

def HalfAverage( frame ):
    "Half exponential moving average"
    zeros = [0.0] * frame.shape[0]
    frame['HalfAvg'] = zeros
    halfAvg = 0
    percentage = 2.0/(daysHalfAvg+1)
    for index in range(0, frame.shape[0]):
        if index < daysHalfAvg-1:
            halfAvg = halfAvg + frame.at[index, 'Close']
        elif index == daysHalfAvg-1:
            halfAvg = (halfAvg + frame.at[index, 'Close'])/daysHalfAvg
            frame.at[index, 'HalfAvg'] = halfAvg
        else:
            halfAvg = (frame.at[index, 'Close'] * percentage) + (halfAvg * (1-percentage))
            frame.at[index, 'HalfAvg'] = halfAvg

    return frame;

def MACD( frame ):
    "Moving Average Convergence Divergence"
    zeros = [0.0] * frame.shape[0]
    frame['MACD'] = zeros
    frame['MACDsignal'] = zeros
    frame['MACDsignalDiff'] = zeros
    daysMACD = daysFullAvg
    daysMACDsig = daysMACD + signalDays
    macdSignal = 0
    percentage = 2.0/(signalDays+1)

    for index in range(daysMACD-1, frame.shape[0]):
        frame.at[index, 'MACD'] = frame.at[index, 'HalfAvg'] - frame.at[index, 'FullAvg']
        if index < daysMACDsig-1:
            macdSignal = macdSignal + frame.at[index, 'MACD']
        elif index == daysMACDsig-1:
            macdSignal = (macdSignal + frame.at[index, 'MACD'])/signalDays
            frame.at[index, 'MACDsignal'] = macdSignal
        else:
            macdSignal = (frame.at[index, 'MACD'] * percentage) + (macdSignal * (1-percentage))
            frame.at[index, 'MACDsignal'] = macdSignal

    for index in range(daysMACDsig-1, frame.shape[0]):
        frame.at[index, 'MACDsignalDiff'] = frame.at[index, 'MACD'] - frame.at[index, 'MACDsignal']

    return frame;

def BollingerBands( frame ):
    zeros = [0.0] * frame.shape[0]
    frame['UpperBand'] = zeros
    frame['LowerBand'] = zeros
    STD = 0
    days = daysHalfAvg

    for index in range(days-1, frame.shape[0]):
        group = np.array([])
        for subIndex in range(index-(days-1), index+1):
            group = np.append(group, [frame.at[subIndex, 'Close']])
        STD = np.std(group)
        frame.at[index, 'UpperBand'] = frame.at[index, 'HalfAvg'] + (2.0*STD)
        frame.at[index, 'LowerBand'] = frame.at[index, 'HalfAvg'] - (2.0*STD)

    return frame;

def RSI( frame ):
    "Relative Strength Indicator"
    zeros = [0.0] * frame.shape[0]
    frame['RSI'] = zeros

    averageGain = 0
    averageLoss = 0

    for index in range(1, frame.shape[0]):
        signedDiff = frame.at[index, 'Close'] - frame.at[index-1, 'Close']
        priceDiff = abs(signedDiff)
        if index < strengthDays-1:
            if signedDiff >= 0:
                averageGain = averageGain + priceDiff
            else:
                averageLoss = averageLoss + priceDiff
        elif index == strengthDays-1:
            if signedDiff >=0:
                averageGain = (averageGain + priceDiff)/strengthDays
                averageLoss = averageLoss/strengthDays
                frame.at[index, 'RSI'] = 100.0 - (100/(1+(averageGain/averageLoss)))
            else:
                averageGain = averageGain/strengthDays
                averageLoss = (averageLoss + priceDiff)/strengthDays
                frame.at[index, 'RSI'] = 100.0 - (100/(1+(averageGain/averageLoss)))
        else:
            if signedDiff >=0:
                averageGain = ((averageGain * (strengthDays-1))+priceDiff)/strengthDays
                averageLoss = averageLoss * (strengthDays-1)/strengthDays
                frame.at[index, 'RSI'] = 100.0 - (100/(1+(averageGain/averageLoss)))
            else:
                averageGain = averageGain * (strengthDays-1)/strengthDays
                averageLoss = ((averageLoss * (strengthDays-1))+priceDiff)/strengthDays
                frame.at[index, 'RSI'] = 100.0 - (100/(1+(averageGain/averageLoss)))

    frame['RSIavg'] = zeros
    days = RSIavgDays
    rsiAverage = 0
    percentage = 2.0/(1+days)
    for index in range((strengthDays-1)+RSImatureDays, frame.shape[0]):
        if index < (strengthDays-1)+RSImatureDays+days-1:
            rsiAverage = rsiAverage + frame.at[index, 'RSI']
        elif index == (strengthDays-1)+RSImatureDays+days-1:
            rsiAverage = (rsiAverage+frame.at[index, 'RSI'])/days
            frame.at[index, 'RSIavg'] = rsiAverage
        else:
            rsiAverage = (frame.at[index, 'RSI'] * percentage) + (rsiAverage * (1-percentage))
            frame.at[index, 'RSIavg'] = rsiAverage

    return frame;

def SD200( frame ):
    collection = np.array([])
    for index in range(frame.shape[0]-200, frame.shape[0]):
        collection = np.append(collection, [(frame.at[index, 'Close']-frame.at[(index-1), 'Close'])/frame.at[(index-1), 'Close']])
    SD = np.std(collection)
    return SD

def BUY( SYM ):
    global finalFrame
    compnayName = SYM
    today = dt.datetime.today()
    endDate = today.strftime('%Y-%m-%d')
    startDate = dt.datetime.strptime(endDate, '%Y-%m-%d') - dt.timedelta(days=1900)

    rawData = pdr.get_data_yahoo(compnayName, start=startDate, end=endDate)
    dataFrame = pd.DataFrame(rawData, columns=["Close"])
    dataFrame.reset_index(level=['Date'], inplace=True)
    dataFrame.Date = pd.to_datetime(dataFrame.Date, format='%Y-%m-%d')

    dataFrame = Flip(dataFrame)
    dataFrame = DropNAN(dataFrame)
    dataFrame = DataRefining(dataFrame)

    dataFrame = FullAverage(dataFrame)
    dataFrame = HalfAverage(dataFrame)
    dataFrame = MACD(dataFrame)

    SD = SD200(dataFrame)

    index = dataFrame.shape[0] - 1
    currentMACD = dataFrame.at[index, 'MACD']
    currentMACDdiff = dataFrame.at[index, 'MACDsignalDiff']
    MACDdiffdiff = dataFrame.at[index, 'MACDsignalDiff'] - dataFrame.at[index-1, 'MACDsignalDiff']

    if currentMACDdiff > 0 and MACDdiffdiff > 0 and currentMACD > 0:
        finalFrame = finalFrame.append({'SYMBOL':SYM, 'MACD Signal Diff':currentMACDdiff, 'MSD Diff':MACDdiffdiff, 'STD':SD}, ignore_index=True)

#######################################################################

today = dt.datetime.today()
endDate = today.strftime('%Y-%m-%d')
startDate = dt.datetime.strptime(endDate, '%Y-%m-%d') - dt.timedelta(days=1900)
'''
fileOpen = pd.read_csv('NSE.csv')
for index in range(0, fileOpen.shape[0]):
    RAWlistDate = dt.datetime.strptime(fileOpen.at[index, ' LISTING'], '%d-%b-%Y')
    listDate = RAWlistDate.strftime('%Y-%m-%d')
    listDate = dt.datetime.strptime(listDate, '%Y-%m-%d')

    if startDate > listDate:
        symFrame = symFrame.append({'SYMBOL':fileOpen.at[index, 'SYMBOL']}, ignore_index=True)

for index in range(0, symFrame.shape[0]):
    symFrame.at[index, 'SYMBOL'] = symFrame.at[index, 'SYMBOL'] + '.NS'
'''
symFrame = pd.read_csv('./nasdaqlisted_test.txt', sep='|', names=('SYMBOL', 'CNAME', 'CATAGORY', 'TEST', 'FSTATUS', 'RLSIZE', 'ETF', 'NEXTS'))

for index in range(0, symFrame.shape[0]):
    if symFrame.at[index, 'TEST'] == 'N' and symFrame.at[index, 'ETF'] == 'N':
        print("Processing...", symFrame.at[index, 'SYMBOL'])
        BUY(symFrame.at[index, 'SYMBOL'])

finalFrame.sort_values(by=['STD'], inplace=True)
finalFrame = finalFrame.reset_index(drop=True)
#toWrite = finalFrame.head(30)
for index in range(0,30):
    toWrite = toWrite.append({'SYMBOL':finalFrame.at[index, 'SYMBOL'], 'MACD Signal Diff':finalFrame.at[index, 'MACD Signal Diff'], 'MSD Diff':finalFrame.at[index, 'MSD Diff'], 'STD':finalFrame.at[index, 'STD']}, ignore_index=True)

toWrite.sort_values(by=['MSD Diff'], inplace=True, ascending=False)
toWrite.to_csv('Selected_stocks.csv', index=False)
