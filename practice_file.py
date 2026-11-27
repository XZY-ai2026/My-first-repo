#写文件
with open ("notes.txt","w",encoding="utf-8") as f:
    f.write("hello\n")
    f.write("worde\n")
    f.write("徐\n")

#读文件
with open ("notes.txt","r",encoding="utf-8") as f:
    content=f.read()
    print(content)

#逐行读
with open ("notes.txt","r",encoding="utf-8") as f:
    for line in f:
        print(line)


