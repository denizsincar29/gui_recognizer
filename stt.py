# отдельный файл с логикой программы
import os
import ffmpeg
import subprocess
import json
from queue import Queue
from threading import Thread
# последние два модуля- это посылатель команд и потоки.
# чтобы программа не висла, транскрибацию выполняем в отдельном потоке, иначе обработчик событий не будет вызываться и винда подумает, что не отвечает.
models=['auto', 'ru', 'en', 'tr', 'de', 'es',  'fr', 'ja', 'pt', 'pl', 'ca', 'nl','ar','sv','it','id','zh','ko','hi','fi','vi','iw','uk','el','ms','cs','ro','da','hu','ta','no','th','ur','hr','bg','lt','la','mi','ml','cy','sk','te','fa','lv','bn','sr','az','sl','kn','et','mk','br','eu','is','hy','ne','mn','bs','kk','sq','sw','gl','mr','pa','si','km','sn','yo','so','af','oc','ka','be','tg','sd','gu','am','yi','lo','uz','fo','ht','ps','tk','nn','mt','sa','lb','my','bo','tl','mg','as','tt','haw','ln','ha','ba','jw','su']
model="ggml-small.bin"

errorflag=False
tx=Queue()
rx=Queue()
stdq=Queue()

thr=None
process=None

# создаём функцию для получения stdout.
def enqueue_output(out, queue):
	try:
		for line in iter(out.readline, b''):
			queue.put(line.decode("UTF-8"))
	except Exception as e: print("excepted ", e)

#создаём функцию, для конвертирования любого файла в mono.wav 16 pcm
def audio2wav(path):
	global errorflag
	#конвертируем любой файл в wav моно 16 pcm
	ffmpeg.input(path).output('output.wav', ac=1, ar=16000, loglevel="error").run()
	# os.system("ffmpeg.exe -hide_banner -loglevel error -i "+ path+ " -ac 1 -ar 16000"+" mono.wav")
	errorflag=not os.path.exists("output.wav")
	if not errorflag:
		print('готово! из '+path+' в mono.wav')
		return
	# если этот код не возвратил, значет функция пошла дальше и файла не существует.
	print("ошиба!")

# функция для транскрибации файла, которая должна вызываться потоком.
def thread_transcribe(path, language, output):
	global process
	# удаляем моно.вав если он есть, иначе выкинет исключение.
	try: os.remove("output.wav")
	except: pass
	audio2wav(path)
	if errorflag:return
	# передаём всю задачу транскрибации висперу.
	startupinfo = subprocess.STARTUPINFO()
	#startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

	#here we construct the command line for whisperCPP    
	cmd = f'whisper/main.exe -f "..\\output.wav" -m "{model}" -l {language} -pp -o{output}'
	print(cmd)
	#here we call the program with extra parameters to capture whisperCPP output
	process=subprocess.Popen(cmd,
		cwd="whisper/",
		startupinfo=startupinfo,
		stdout=subprocess.PIPE,
		stdin=subprocess.PIPE,
		stderr=subprocess.STDOUT)
	progress=[0, 0, ""]
	ln=b''

	# запускаем поток читалки stdout иначе повесит к хренам.
	th = Thread(target=enqueue_output, args=(process.stdout, stdq), daemon=True)
	th.start()

	while True:
		if process==None: return
		if not tx.empty() and tx.get()=="fuck":
			process.kill()
			process=None
			return
		poll=process.poll()
		if poll is not None:
			outs, errs = process.communicate()
			rx.put([-4, poll])
			with open("error.log","a") as f: f.write(outs+errs)
			process=None
			return
		if stdq.empty(): continue
		line=stdq.get_nowait()
		line1=line.rstrip()
		print(line1)
		if "whisper_init" in line1: progress[2]="loading models..."
		progress[2]=line1

		if "main: processing" in line1:
			y=line1.split(" ")
			progress=[-2, round(float(y[y.index("sec),")-1])), "transcribing..."]
		if "saving" in line1: progress=[progress[1], progress[1], "finished!"]
		if "-->" in line1:
			stamps=line1.split(" --> ")[1].split("]")[0].split(":")
			if len(stamps)!=3:print("stamps! ", stamps)
			progress[0]=int(stamps[0])*3600 + int(stamps[1])*60 + round(float(stamps[2]))
		rx.put(progress)


	try: os.remove("output.wav")
	except: pass


# а эта функция создаёт поток, который выполняется в фоне. его и надо вызывать из гуя.
# не инициализируй сразу модель. прямо во время транскрибации инициализируем. иначе нужно будет создавать ещё одну функцию с потоком, 1000000 проверок и кучу говнокода.
def transcribe(path, language, output):
	global thr # даём питону знать, что мы будем использовать глобальную переменную испод функции. иначе питон скажет: error! govnocode!
	# проверяем. если транскрибирует, то возвращаем фолс и всё!
	if thr is not None and thr.is_alive():return False
	thr=Thread(target=thread_transcribe, args=(path, language, output))
	thr.start() # запускаем поток.
	return True