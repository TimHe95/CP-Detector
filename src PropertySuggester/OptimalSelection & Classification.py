# -*- coding: utf-8 -*-

import spacy

from scipy.stats import norm
import numpy as np
import time, random, pickle, heapq

import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText

from sklearn.metrics import precision_score, recall_score, accuracy_score, classification_report




## ---------------------------------------------------------------------------------------------
# 1: RandomN
# 0 :TopN
RandomNOrTopN = 1
haha = [2*kk for kk in range(3,251)] # number of CARs ("Num" in paper)
classes =        ["NONE",   "Tradeoff", "Function", "Optimization", "Resource"  ]
dataFileName = 'GGGGG-3-8-splitAll'
## ---------------------------------------------------------------------------------------------


## ----- for visualization -----
PP =    []
RR =    []
AA_N =  []
## ------------------------------

manual_patterns = [('VERB','IMPROVE'), ('NOUN','PERF_POS')]

wordsToMerge = [["speed", "up"], ["get", "better"], ["compared", "with"], ["crash","recovery"], 
                ["time", "zone"], ["ip","address"], ["email", "address"], ["character","set"],
                ["case","sensitive"], ["character","set"], ["character","sets"], ["contact", "address"],
                ["user", "name"], ["lead", "to"], ["leads", "to"], ["I", "/", "O"], ["warmup", "process"],
                ["buffer", "allocations"], ["resulting", "in"], ["time","it","takes"], ["duplicate","pushes"],
                ["resulting", "in"], ["responses","time"], ["request","processing"], ["unnecessary","handshakes"],
                ["useful","for"], ["connection","pooling"], ["class","name"], ["server","name"], ["port", "number"],
                ["socket", "address"],["use", "little"], ["host", "name"], ["account","name"], ["fault", "tolerance"],
                ["comes", "at"], ["disaster", "recovery"], ["disk","I/O"]]


tagDict = {}    # word-in-description, wordTag
MapDict = {}    # (POS, wordTag), treeNodeID
MapDict_r = {}  # treeNodeID, (POS, wordTag)
Sequenceses4Testing = []


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

def ReadSequenceses4Testing(classfication):
    S = []
    
    # should be donwloaded first
    nlp = spacy.load("en_core_web_sm")
    
    file = open("DATA-Test/DATA-%s"%classfication) 
    
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
    
    Sequenceses4Testing.append(S)

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
file = open("Domain_Specific_Synonyms") 
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
file = open("MapSentAtrri2TreeNodeID") 
while 1:
    
    line = file.readline()
    if not line:
        break
    Attri_raw, TreeNodeID = line.split(":")
    Attri = tuple(Attri_raw.split(","))
    MapDict[Attri] = TreeNodeID.strip()

file.close()
MapDict_r = dict(zip(MapDict.values(), MapDict.keys()))



size = []   # size of configuration descriptions (NOT frequent sub-sequences)
FreqSeqs = []
S_C_L = []
with open('./FreqSeqs-%s.pickl'%dataFileName, 'rb') as f: 
    FreqSeqs = pickle.load(f)
with open('./S_C_L-%s.pickl'%dataFileName, 'rb') as f: 
    S_C_L = pickle.load(f)

print("CARs Loaded:")
for i in range(len(classes)):
    print("\t %s: %d"%(classes[i], len(FreqSeqs[i])))
print("\n\n")


# read configuration & description
y_true = []
for i in range(len(classes)):
    ReadSequenceses4Testing(classes[i])
    size.append(len(Sequenceses4Testing[i]))
    y_true.extend([i for _ in range(size[i])])
    
    ######
    # You may want to know if we sorted by F-score, if the result could be better
    # (Answer is no)
    ######
    #S_C_L[i] = sorted(S_C_L[i], key=lambda x:1/(1/x[1][1] + 1/x[1][2]), reverse=True)

for ha in haha:
    
    RandomK =  [ha for _ in classes] 
    print("\n\n++++++++++++++++++++++ CARs = ", ha, "++++++++++++++++++++++")

    
    tocks = time.time()
    
    R_mC_mL = [[] for _ in classes]
    saved_patterns = {clas:[[], tuple([-1,-1,-1,-1])] for clas in classes}
    
    for i in range(len(classes)):
        
        
        harms = []
        converges = False
        while True:
        #for iterations in range(repeatitions):
            
            coverage = [0 for _ in range(size[i])]
            Total_confidence = 0
            Total_lift = 0
            div = 0
            patterns = 0
            
            # Random-N
            if RandomNOrTopN:
                sampled_patterns = random.sample(
                    S_C_L[i][:int(len(S_C_L[i]))], 
                    min(RandomK[i], int(len(S_C_L[i]))))
            # Top-N
            else:
                sampled_patterns = S_C_L[i][:min(RandomK[i], len(S_C_L[i]))]
                
                
            # calculate Recall, Mean_Confidence, Mean_Lift, Harmonic for these patterns
            for selected_pattern in sampled_patterns:
                patterns += 1
                for idx in range(len(Sequenceses4Testing[i])):
                    if isSubsequence(list(selected_pattern[0]), Sequenceses4Testing[i][idx]):
                        coverage[idx] = 1
                        Total_confidence = Total_confidence+selected_pattern[1][2]
                        Total_lift = Total_lift+selected_pattern[1][3]
                        div = div+1
            
            # save Recall, Mean_Confidence, Mean_Lift, Harmonic
            Misses = [miss for miss, x in enumerate(coverage) if x==0]
            Recall = coverage.count(1)/size[i]
            Mean_Confidence = Total_confidence/div
            Mean_Lift = Total_lift/div
            Harmonic = 2/(1/Recall + 1/Mean_Confidence)
            R_mC_mL[i].append(tuple([
                float(int(Recall*1000))/1000,             # 0
                float(int(Mean_Confidence*1000))/1000,    # 1
                float(int(Mean_Lift*1000))/1000,          # 2
                float(int(Harmonic*1000))/1000,           # 3
                Misses]))                                 # 4
            
            # If the Harmonic is currently the max, save it.
            # saved_patterns["Resource"]:
            #   [ 
            #     [(,,,),(,,,,,),(,)...],                       # a list of pattern sampled for Resource.
            #     (Recall, Mean_Confidence, Mean_Lift, Harmonic)
            #   ]
            if Harmonic > saved_patterns[classes[i]][1][3]:
                saved_patterns[classes[i]] = [
                    [list(selected_pattern) for selected_pattern in sampled_patterns],
                    R_mC_mL[i][-1]  # it is just get "appended" before
                    ]
            
            # for TopN, we do not need to repeat.
            if not RandomNOrTopN:
                break
            
            # do we get statisticaly "optimal" CARs, judge in following
            harms.append(Harmonic)
            if np.std(harms) == 0:
                continue
            else:
                d_harms = norm(loc=np.mean(harms), scale=np.std(harms))
                # by this, we think we find the near-optimal pattern for a class
                # we mentioned this in s3.1.1
                if d_harms.cdf(max(harms)) > 0.999:
                    break
        
        # Convert the save patterns to human readable format
        for sp in range(len(saved_patterns[classes[i]][0])):
            saved_patterns[classes[i]][0][sp][0] = SeqIDs2SeqItems(saved_patterns[classes[i]][0][sp][0])
            
    ticks = time.time()
    print("Selecting near optimal CARs uses %.1f sec."%(ticks-tocks))
    
    
    
    ####################
    ##     TESTING    ## 
    ####################
    y_prid = []    
    Sequenceses_TestSet = []
    y_votes = []
    asd = 0
    for i in range(len(classes)):
        
        Sequenceses_TestSet.append(Sequenceses4Testing[i])
        
        # test which pattern match? with what confidence?
        for testID, seq_t in enumerate(Sequenceses_TestSet[i]):
            goodMatches = []
            badMatches = []
            votedSum = [0 for k in range(len(classes))]
            # test for all patterns in all classes
            for j in range(len(classes)):
                # test for all patterns in each classes
                for pat, mtr in saved_patterns[classes[j]][0]:
                    # match
                    if isSubsequence(SeqItemss2SeqIDs(pat), seq_t):
                        votedSum[j] += mtr[2]
                        # same class, if match, then GOOD
                        if i==j:
                            goodMatches.append(tuple([pat, 1*mtr[2]]))
                        # different class, if match, then BAD
                        else:
                            badMatches.append(tuple([pat, -1*mtr[2]]))    

            y_prid.append(  votedSum.index(max(votedSum))  )
            y_votes.append( tuple([y_true[asd], y_prid[-1], votedSum] ) )
            asd += 1
    
    
    #####################
    ##   Future Work   ##
    ##  TopN Accuracy  ##
    #####################
    '''
    TopN_Accuracy = []
    for topN in range(1, len(classes)+1):
        y_prid_TopN = []
        for y_tru, y_pdct, votes in y_votes:
            if y_tru in heapq.nlargest(topN, range(len(votes)), key=votes.__getitem__):
                y_prid_TopN.append(y_tru)
            else:
                y_prid_TopN.append(y_pdct)
        AccuracyTopN = accuracy_score(y_true, y_prid_TopN)
        print("Top-%d Accuracy: %.3f"%(topN, AccuracyTopN))
        TopN_Accuracy.append(AccuracyTopN)
    AA_N.append(TopN_Accuracy)
    '''
    
    ### Since if all votes are 0, our classifier do not label, 
    ### so the "Recall" should count them as False Negative
    y_new_true = []
    y_new_pred = []
    for a,b,c in y_votes:
        if sum(c) != 0:
            y_new_true.append(a)
            y_new_pred.append(b)
    Precision_new = precision_score(y_new_true, y_new_pred, average='weighted')
    
    ### Since if all votes are 0, our classifier do not label, 
    ### so the "Recall" should count them as False Negative
    y_new_true = []
    y_new_pred = []
    for a,b,c in y_votes:
        if sum(c) != 0:
            y_new_true.append(a)
            y_new_pred.append(b)
        else:
            y_new_true.append(a)
            y_new_pred.append((a+1)%5)
    Recall_new = recall_score(y_new_true, y_new_pred, average='weighted')
    
    # for visualization
    PP.append(Precision_new)
    RR.append(Recall_new)
    
    tock = time.time()
    print("Testing uses %.1f sec."%(tock-ticks))
  
    
## A simple visualization
plt.plot(haha, PP, color='red',    linewidth=1)
plt.plot(haha, RR, color='orange', linewidth=1)
plt.show()


# To see the voting details, uncomment the following code
'''
res = []
for a,b,c in y_votes:
    if a == b:
        res.append(str([a,b, str([int(cc*10)/10 for cc in c])]))
f= open("good.txt","w")
f.write('\n'.join(res))
f.close()

res = []
for a,b,c in y_votes:
    if not a == b:
        res.append(str([a,b, str([int(cc*10)/10 for cc in c])]))
f= open("bad.txt","w")
f.write('\n'.join(res))
f.close()
'''