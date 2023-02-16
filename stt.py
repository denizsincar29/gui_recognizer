# отдельный файл с логикой программы
import os
import wave
import ffmpeg
import json
from pprint import pprint #подключили Pprint для красоты выдачи текста
from vosk import Model, KaldiRecognizer
from queue import Queue
from threading import Thread
# последние два модуля- это посылатель команд и потоки.
# чтобы программа не висла, транскрибацию выполняем в отдельном потоке, иначе обработчик событий не будет вызываться и винда подумает, что не отвечает.

models=os.listdir("models") # список моделей
errorflag=False
tx=Queue()
rx=Queue()

thr=None

#создаём функцию, для конвертирования любого файла в mono.wav 16 pcm
def audio2wav(path):
	global errorflag
	#конвертируем любой файл в wav моно 16 pcm
	ffmpeg.input(path).output('mono.wav', ac=1, ar=16000, loglevel="error").run()
	# os.system("ffmpeg.exe -hide_banner -loglevel error -i "+ path+ " -ac 1 -ar 16000"+" mono.wav")
	errorflag=not os.path.exists("mono.wav")
	if not errorflag:
		print('готово! из '+path+' в mono.wav')
		return
	# если этот код не возвратил, значет функция пошла дальше и файла не существует.
	print("ошиба!")

# функция для транскрибации файла, которая должна вызываться потоком.
def thread_transcribe(path, language):
	# удаляем моно.вав если он есть, иначе выкинет исключение.
	try: os.remove("mono.wav")
	except: pass
	# мы ускорим программу, добавив ещё один поток, который конвертирует аудио в вав. будет происходить, пока инициализируется модель языка. а чтобы не началась транскрибация раньше, мы подождём завершения потока.
	thr2=Thread(target=audio2wav, args=(path, ))
	thr2.start()
	# ok! мы создали поток. пока он выполняется, инициализируем модель языка и распознаём.
	model = Model(os.path.join("models", language)) # путь до модели распознавания
	# ждём, пока не завершится поток, который конвертирует аудио. иначе он скажет, что такого файла нет.
	thr2.join() # если поток завершился раньше, это ничего не делает.
	if errorflag:return
	#открываем и читаем моно файл
	rec_file = wave.open('mono.wav', 'rb')
	rec = KaldiRecognizer(model, rec_file.getframerate())
	rec.SetWords(True)

	total=rec_file.getnframes()
	step=4000
	data_length=0
	rx.put([-2, total])
	while True:
		if not tx.empty() and tx.get()=="fuck": return
		data = rec_file.readframes(step)
		data_length+=step
		if len(data) == 0:
			data_length=total
			break
		if data_length>total:
			print("progress ", data_length, " but max is", total)
			data_length=total
		if rec.AcceptWaveform(data):
			pass #print(rec.Result())
		else:
			pass # print('распознавание...')
		rx.put([data_length, total]) # передаём главному потоку состояние распознавания
	rx.put([-1, -1])
	#вводим строковую выдачу для результатов
	results = [] # это всё потом будет нужно
	textResults = []#это тоже
	# конвертируем распознанные результаты в словарик
	resultDict = json.loads(rec.Result())
	# сохраняем в список
	results.append(resultDict)
					# сохраняем значение text в список
	textResults.append(resultDict.get("text" , ''))

	#			# финальные результаты
	resultDict = json.loads(rec.Result())
	results.append(resultDict)
	textResults.append(resultDict.get("text", ''))

	text="\n".join(textResults)
	#pprint(text) #вывели результат на экран
	with open('text.txt', 'a', encoding='utf-8') as f2: #открыли файл для записи распознанного текста
		f2.write(text) #записали в файл txt


	rec_file.close()
	try: os.remove("mono.wav")
	except: pass


# а эта функция создаёт поток, который выполняется в фоне. его и надо вызывать из гуя.
# не инициализируй сразу модель. прямо во время транскрибации инициализируем. иначе нужно будет создавать ещё одну функцию с потоком, 1000000 проверок и кучу говнокода.
def transcribe(path, language):
	global thr # даём питону знать, что мы будем использовать глобальную переменную испод функции. иначе питон скажет: error! govnocode!
	# проверяем. если транскрибирует, то возвращаем фолс и всё!
	if thr is not None and thr.is_alive():return False
	print("language: ", language, "path: ", path)
	thr=Thread(target=thread_transcribe, args=(path, language))
	thr.start() # запускаем поток.
	return True