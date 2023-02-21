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

thr=None

#создаём функцию, для конвертирования любого файла в mono.wav 16 pcm
def audio2wav(path):
	global errorflag
	#конвертируем любой файл в wav моно 16 pcm
	ffmpeg.input(path).output('output.wav', ac=1, ar=16000, loglevel="error").run()
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
	try: os.remove("output.wav")
	except: pass
	audio2wav(path)
	if errorflag:return
	# передаём всю задачу транскрибации висперу.
	startupinfo = subprocess.STARTUPINFO()
	startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

	#here we construct the command line for whisperCPP    
	cmd = f"main.exe -f output.wav -m {model} -l {language} --otxt"

	#here we call the program with extra parameters to capture whisperCPP output
	process=subprocess.Popen(cmd,
		startupinfo=startupinfo,
		stdout=subprocess.PIPE,
		stdin=subprocess.PIPE,
		stderr=subprocess.STDOUT)
	progress=[0, 0, ""]
	#here we print whisperCPP output to the Gooey window
	log=b''
	ln=b''
	while True:
		if not tx.empty() and tx.get=="fuck":
			proc.kill()
			return
		if process.poll() is None:
			outs, errs = proc.communicate()
			rx.put([-4, -4])
			with open("error.log","rb") as f: f.write(log)
			return

		try:
			outs, errs = proc.communicate(timeout=15)
		except TimeoutExpired:
			proc.kill()
			outs, errs = proc.communicate()
			rx.put([-4, -4])
			with open("error.log","rb") as f: f.write(log)
			return
		log+=ln
		ln+=outs
		if not b'\n' in ln: continue
		line1=ln.decode('utf-8').rstrip()
		print(line1)
		if "whisper_init" in line1: progress[2]="loading models..."
		if "main: processing" in line1:
			y=line1.split(" ")
			progress=[-2, float(y[y.index("sec),")-1]), "transcribing...")
		if "saving" in line1: progress=[progress[1], progress[1], "finished!"]
		if "total time" in line1: progress[2]=line1
		if "-->" in line1:
			stamps=line1.split(" --> ")[1].split("]")[0].split(":")
			if len(stamps)!=3:print("stamps! ", stamps)
			progress[0]=int(stamps[0])*3600 + int(stamps[1])*60 + float(stamps[2])
		rx.put(progress)


	try: os.remove("output.wav")
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