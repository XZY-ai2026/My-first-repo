scores={"徐":120,"翟":70,"马":110,"李":90}
scores["徐"]=130
name=input("请输入姓名：")
result=scores.get(name,"查无此人")
print(f"分数为：{result}")
