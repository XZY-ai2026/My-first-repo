scores={"徐":[120,110],"翟":[70,80],"马":[110,100]}
for name in scores:
    scores_list=scores.get(name)
    total=0
    for x in scores_list:
        total=total+x
    avg=total/len(scores_list)
    print(f"{name},{avg:.1f}")
with open ("student_scores.txt","w",encoding="utf-8") as f:
    for name in scores:
        scores_list=scores.get(name)
        total=0
        for x in scores_list:
            total=total+x
        avg=total/len(scores_list)
        line = f"{name},{avg:.1f}"
        f.write(f"{line}\n")
with open ("student_scores.txt","r",encoding="utf-8") as f:
    for line in f:
        print(line,end="")

