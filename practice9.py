s=[312,432,111,444,987]
s.insert(1,222)
s[0]=333
print(len(s))
print(sorted(s))
print(max(s))
he=0
for x in s:
    he=he+x
    avg=he/len(s)
print(he)
print(f"平均分：{avg:.1f}")