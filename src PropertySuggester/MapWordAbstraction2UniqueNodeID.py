# -*- coding: utf-8 -*-

################
##  Convert "(POS, Semantic)" to an universal unique ID
################


name2 = "POSs"
POSs = list()

name3 = "Domain_Specific_Synonyms"
MyWordTags = list()


file = open("Domain_Specific_Synonyms") 
while 1:
    
    line = file.readline()
    if not line:
        break
    POSs.append(line.strip())

file.close()


file = open("POSs") 
while 1:
    
    line = file.readline()
    if not line:
        break
    words = line.split(" ")
    for word in words:
        word.replace('-',' ')
    MyWordTags.append(words)

file.close()


TreeNodeID = 0
file = open("MapSemanticAbstraction2NodeID", "w")
for POS in POSs:
    for MyWordTag in MyWordTags:
        TreeNodeID = TreeNodeID + 1
        file.write(POS + "," + MyWordTag[0].strip() + ':' + str(TreeNodeID) + '\n')
file.close()