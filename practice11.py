scores={"徐":[120,110],"翟":[70,80],"马":[110,100]}
for name in scores:
    scores_list=scores.get(name)
    total=0
    for x in scores_list:
        total=total+x
    avg=total/len(scores_list)
    print(f"{name}平均分：{avg:.1f}")
   
