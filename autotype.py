import pyautogui
from time import sleep

pyautogui.PAUSE = 0.0
pyautogui.FAILSAFE = True

print('Open correct window!')
sleep(5)
for i in range(15):
    line = list('%03d' % i + '\n')
    pyautogui.typewrite(line, interval=0.01)
