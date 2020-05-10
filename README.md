# CP-Detector
CP-Detector: Using Configuration-related Performance Properties to Expose Performance Bugs

To run the property suggester,
  
## Step 1
 
Install requirements:
 
```bash
pip install -U prefixspan t
```
```bash
pip install spacy
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-2.2.0/en_core_web_sm-2.2.0.tar.gz
```
and check all directory name in the three pyhon script fit the envirnment

## Step 2

Generate universal unique id for each normalized word.  
e.g., (NN, Resource) --> 58 (NN, Volume) --> 89 etc.
```bash
python MapWordAbstraction2UniqueNodeID.py
```

## Step 3
1. Normalizing Words  
2. Mining Association Rules (CARs)  
3. Calculate the quality for each (CARs)  
```bash
python Preprocessing & Mining.py
```
This will generate 10^6 - 10^7 CARs, we save it to disk (`FreqSeq`), and the quality of each CAR (`S_C_L`, stands for support, confidence, lift). 

## Step 4
4. Selecting Optimal rules.  
5. build a voting classifier
```bash
python OptimalSelection & Classification.py
```
you can choose to use the `Random-N` or `Top-N` by changing `RandomNOrTopN` to `1` or `0`.

## Step 5

The result will be shown in python console, or we provide simple visualization code to help you.
