# -*- coding: utf-8 -*-

import spacy

from prefixspan import PrefixSpan

import numpy as np
import time, pickle


#
# This script implements s3.1:  
#  1. Normalizing Words
#  2. Mining Association Rules (CAR)   -> store to FreqSeqs-GGGGG-3-9-SplitAll.pickl
#  3. Calculate the quality of CARs
#


classes =  ["NONE", "Tradeoff", "Function", "Optimization", "Resource"]

# (closed CAR, generator CAR) we use generator CAR,
# this implement that we described in the paper:
#     "When a CAR is a sub-sequence of another CAR and the two CARs have the same support, 
#      CP-Detector rules out the short one, since these two CARs always appear at the same
#      time and the longer one is more informative."
params = [(False, True), (False, True), (False, True), (False, True),  (False, True)]
MINSUP = [3,             3,             3,             3,              3 ]
## ---------------------------------------------------------------------------------------------
dumpFileName = 'GGGGG-3-9-SplitAll'



wordsToMerge = [["speed", "up"], ["get", "better"], ["compared", "with"], ["crash","recovery"], 
                ["time", "zone"], ["ip","address"], ["email", "address"], ["character","set"],
                ["case","sensitive"], ["character","set"], ["character","sets"], ["contact", "address"],
                ["user", "name"], ["lead", "to"], ["leads", "to"], ["I", "/", "O"], ["warmup", "process"],
                ["buffer", "allocations"], ["resulting", "in"], ["time","it","takes"], ["duplicate","pushes"],
                ["resulting", "in"], ["responses","time"], ["request","processing"], ["unnecessary","handshakes"],
                ["useful","for"], ["connection","pooling"], ["class","name"], ["server","name"], ["port", "number"],
                ["socket", "address"],["use", "little"], ["host", "name"], ["account","name"], ["fault", "tolerance"]
                , ["comes", "at"], ["disaster", "recovery"], ["disk","I/O"]]

tagDict = {}    # word-in-description, wordTag
MapDict = {}    # (POS, wordTag), treeNodeID
MapDict_r = {}  # treeNodeID, (POS, wordTag)
ForestRaw = {}  # id, config-full-description


Sequences = [] # tmp var
Sequenceses = [] # tmp var


Sequenceses4Training = []



def MyWordTags(text):
    try:
        return tagDict[text.lower()]
    except KeyError:
        return 'OTHERS'

    
def MergeWords(doc):
    tokens = [token.text for token in doc]
    for i in range(len(tokens)): # each word in sentence
        for j in range(len(wordsToMerge)): # each phrase to merge
            match = True
            for k in range(len(wordsToMerge[j])): # each word in phrase to merge
                if wordsToMerge[j][k].lower() != tokens[i+k]:
                    match = False
                    break
            if match == True:
                with doc.retokenize() as retokenizer:
                    retokenizer.merge(doc[i: i+len(wordsToMerge[j])], attrs={"LEMMA": ' '.join(wordsToMerge[j]).lower()})
                doc = MergeWords(doc)
                return doc
    return doc


def ReadSequencesesFromFile(classfication):
    S = []
    nlp = spacy.load("en_core_web_sm")
    file = open("DATA-Train/DATA-%s"%classfication) 
    
    while 1:
        
        # read a conf-id, a description from file
        line = file.readline()
        if not line:
            break
        try:
            conf_id, conf_desc_text_raw = line.split('\t')
        except ValueError:
            print(line)
        doc = nlp(conf_desc_text_raw.strip())
        
        doc = MergeWords(doc)
        
        S.append([
                MapDict[(
                    #root.dep_, 
                    token.pos_,
                    MyWordTags(token.text)
                )] for token in doc
                if (token.pos_, MyWordTags(token.text)) != ('PUNCT', 'OTHER')
            ])
    
    Sequenceses4Training.append(S)


# Mine CARs from configuration descriptions.
# You should split the description into sentences first. 
def nlp_FreqSubsequenceMining(classfication, MINSUP=3, CLOSED=False, GENERATOR=True):
    
    Sequences.clear()
    
    print("Analyzing %s..."%classfication)
    
    nlp = spacy.load("en_core_web_sm")
    
    # Read from raw data file, then convert it to NodeID-sequences.
    file = open("./DATA-Train/DATA-%s"%classfication) 
    while 1:
        
        # read a conf-id, a description from file
        line = file.readline()
        if not line:
            break
        try:
            conf_id, conf_desc_text_raw = line.split('\t')
        except ValueError:
            print(line)
        doc = nlp(conf_desc_text_raw.strip())
        
        doc = MergeWords(doc)
        
        Sequences.append([
                MapDict[(
                    #root.dep_, 
                    token.pos_,
                    MyWordTags(token.text)
                )] for token in doc
                if (token.pos_, MyWordTags(token.text)) != ('PUNCT', 'OTHER')
            ])
    
    size = len(Sequences)
    mean_len = np.mean([len(s) for s in Sequences])
    print("Config & Desc: %d\nMean length: %.1f"%(size, mean_len))
    
    # Mining FreqSeqs from those NodeID-sequences
    # FreqSeqs = ((sup, [seq]), (sup, [seq]), ...)
    FreqSeqs = PrefixSpan(Sequences)
    tmp = FreqSeqs.frequent(
        int(MINSUP), 
        closed=CLOSED, 
        generator=GENERATOR)
    res = {}
    for FreqSeq in tmp:
        res[tuple(FreqSeq[1])] = FreqSeq[0]
        
    print("Frequent Sub-sequences: %d\n"%len(res))
    
    # FreqSeqs with support number, 
    return res
    

# assert isSubsequence(['i', 'n', 'd', 'i', 'a'],
#                      ['i', 'n', 'd', 'o', 'n', 'e', 's', 'i', 'a'])
def isSubsequence(s, t):
    index = 0
    for value in s:
        try:
            index = t.index(value, index)
        except ValueError:
            return False
        index += 1
    return True
    

def SeqIDs2SeqItems(seqIDs):
    return [MapDict_r[seqID] for seqID in seqIDs]

def SeqItemss2SeqIDs(seqItems):
    return [MapDict[seqItem] for seqItem in seqItems]

# build "tagDict" Data Structure
#   Key       : Name of MyWordTag (e.g., RESOURCE)
#   Value     : List of keywords belongs to this tag (e.g., ['buffer', 'cache', 'memory', 'thread'])
file = open("DomainSpecificSynonym") 
while 1:    
    line = file.readline()
    if not line:
        break
    words = line.split(" ")
    for word in words[1:]:
        tagDict[word.replace('$',' ').strip()] = words[0] 
file.close()


# build "MapDict" Data Structure
#   Key     : How I define a Node of language tree, currently it has 2 features (e.g., (NOUN,RESOURCE))
#   Value   : An universal NodeID (e.g., 154)
file = open("MapSemanticAbstraction2NodeID") 
while 1:
    
    line = file.readline()
    if not line:
        break
    Attri_raw, TreeNodeID = line.split(":")
    Attri = tuple(Attri_raw.split(","))
    MapDict[Attri] = TreeNodeID.strip()

file.close()
MapDict_r = dict(zip(MapDict.values(), MapDict.keys()))




FreqSeqs = []
ticks = time.time()
for i in range(len(classes)):
    F = nlp_FreqSubsequenceMining(
        classfication = classes[i], 
        MINSUP        = MINSUP[i], 
        CLOSED        = params[i][0],
        GENERATOR     = params[i][1])
    FreqSeqs.append(F)

tocks = time.time()
print("NLP & FreqSubsequenceMining processing %.1f sec."%(tocks-ticks))


print("Patterns Mined:")
for i in range(len(classes)):
    print("\t %s: %d"%(classes[i], len(FreqSeqs[i])))
print("\n\nNow dump FreqSeqs to file...")

with open('FreqSeqs-%s.pickl'%dumpFileName, 'wb') as f: 
    pickle.dump(FreqSeqs, f) 
print("Done.\n\n")


size = []   # size of configuration descriptions (NOT frequent sub-sequences)
for i in range(len(classes)):
    ReadSequencesesFromFile(classes[i])
    size.append(len(Sequenceses4Training[i]))

print("Analyzing Confidence, Support, Lift of the CARs...")
tocks = time.time()
S_C_L = [{} for _ in classes]
for i in range(len(classes)):
    
    for j in FreqSeqs[i].keys():
        # B ---> A
        # B: rule
        # A: class
        
        # A_and_B = FreqSeqs[i][j]
        A_and_B = 0
        
        B_occurALL = 0
        for k in range(len(classes)):
            if k==i:
                check = 0
                for seq in Sequenceses4Training[k]:
                    if isSubsequence(list(j), seq):
                        check = check+1
                #if check != FreqSeqs[k][j]:
                #    print(j, "%d %d"%(FreqSeqs[k][j], check))
                #else:
                #    pass
                A_and_B = check

            else:
                for seq in Sequenceses4Training[k]:
                    if isSubsequence(list(j), seq):
                        B_occurALL = B_occurALL + 1
                        
        support = A_and_B/sum(size)

        B_occurALL = B_occurALL+A_and_B
        confidence = float(A_and_B)/float(B_occurALL)
        
        lift = confidence/(size[i]/sum(size))
                
        if lift > 1.5 and confidence > 1.0/len(classes):
            S_C_L[i][j] = tuple(["SupportNum=%d/%d"%(FreqSeqs[i][j], size[i]),    # 0
                                 float(int(support*1000))/1000,                   # 1
                                 float(int(confidence*1000))/1000,                # 2
                                 float(int(lift*1000))/1000])                     # 3
    
    S_C_L[i] = sorted(S_C_L[i].items(), key=lambda x:x[1][2], reverse=True) # sorted by confidence
   
    
ticks = time.time()
print("Done (%.1f sec), dumping to file"%(ticks-tocks))

with open('S_C_L-%s.pickl'%dumpFileName, 'wb') as f: 
    pickle.dump(S_C_L, f) 

print("Done")
