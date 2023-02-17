import markdown
with open("readme.md", "r", encoding="UTF-8") as f:
	a=f.read()
with open("help.htm", "w", encoding="UTF-8") as f:
	s=markdown.markdown(a)
	s=f'<html>\n<head>\n<meta charset="utf-8">\n<title>справка по программе транскрибатор</title>\n</head>\n<body>\n{s}\n</body>\n</html>'
	f.write(s)