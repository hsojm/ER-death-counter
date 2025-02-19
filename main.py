import win32gui, win32ui, win32con
import pytesseract
import numpy as np
import time
from ctypes import windll
import cv2
import json

WINDOW_NAME = None
WINDOW_ID = None
CONFIG = None

with open('config.json', 'r') as file:
	CONFIG = json.load(file)

def capture_win_alt():
    # Adapted from https://stackoverflow.com/questions/19695214/screenshot-of-inactive-window-printwindow-win32gui

	windll.user32.SetProcessDPIAware()
	hwnd = win32gui.FindWindow(None, WINDOW_NAME)
	img = None
	if hwnd:
		left, top, right, bottom = win32gui.GetClientRect(hwnd)
		w = right - left
		h = bottom - top

		hwnd_dc = win32gui.GetWindowDC(hwnd)
		mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
		save_dc = mfc_dc.CreateCompatibleDC()
		bitmap = win32ui.CreateBitmap()
		bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
		save_dc.SelectObject(bitmap)

		# If Special K is running, this number is 3. If not, 1
		result = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)

		bmpinfo = bitmap.GetInfo()
		bmpstr = bitmap.GetBitmapBits(True)

		# if the window wasn't found, the array conversion will fail. If so, don't return an image.
		try:
			img = cv2.cvtColor(np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo["bmHeight"], bmpinfo["bmWidth"], 4)), cv2.COLOR_BGR2RGB)
		except Exception as e:
			print(e)
			return None

		#crop coords
		x = int(CONFIG["crop_dimensions"]['x'])
		y = int(CONFIG["crop_dimensions"]['y'])
		width = int(CONFIG["crop_dimensions"]['width'])
		height = int(CONFIG["crop_dimensions"]['height'])

		img = img[y:y+height, x:x+width] # crop image

		img = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2GRAY)

		normalized_gray_image = cv2.normalize(img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

		cv2.imwrite("cropped.png", normalized_gray_image)

		win32gui.DeleteObject(bitmap.GetHandle())
		save_dc.DeleteDC()
		mfc_dc.DeleteDC()
		win32gui.ReleaseDC(hwnd, hwnd_dc)

	return img

# find name of window
def get_window_name():
	def winEnumHandler(hwnd, ctx):
		global WINDOW_NAME, WINDOW_ID
		if win32gui.IsWindowVisible(hwnd):
			win_name = win32gui.GetWindowText(hwnd)
			if str(CONFIG['window_name']) in win_name.lower():
				WINDOW_ID = hwnd
				WINDOW_NAME = win_name
	win32gui.EnumWindows(winEnumHandler, None)

def write_to_file():
	text = ''
	with open(CONFIG['counter_text_path'], 'r') as file:
		text = file.read()

	text = text.replace(CONFIG['counter_text_layout'], '').strip()
	try:
		curr_num = int(text)
		print('current', curr_num)
		curr_num = curr_num + 1
		with open(CONFIG['counter_text_path'], 'w') as file:
			file.write(CONFIG['counter_text_layout'] + ' ' + str(curr_num))
	except:
		raise Exception('Failed to get number of deaths')


if __name__ == '__main__':
	pytesseract.pytesseract.tesseract_cmd = str(CONFIG['tesseract_path'])
	num_saved = 0
	while True:
		start = time.time()
		get_window_name()
		end = time.time()
		# print('window name: ', end-start)

		start = time.time()
		img = capture_win_alt()
		end = time.time()
		# print('capture win alt: ', end-start)

		start = time.time()
		found = False
		if img is not None:
			text = pytesseract.image_to_string(img)
			# if text.lower():
			# 	cv2.imwrite(f"cropped_{num_saved}.png", img)
			# 	num_saved += 1
			if 'youdied' in text.lower().replace(' ', '').strip():
				found = True
				write_to_file()
		end = time.time()

		# print('read/write time: ', end-start)
		if img is not None and not found:
			time.sleep(0.4)
		else:
			time.sleep(5) # sleep for longer if we failed to find the window. It is probably minimized.
