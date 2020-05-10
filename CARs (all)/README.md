## FreqSeqs-GGGGG-3-8-splitAll.pickl

	FreqSeqs = ((sup, [CAR]), (sup, [CAR]), ...)

	```python
	with open('FreqSeqs-%s.pickl'%dataFileName, 'rb') as f: 
	    FreqSeqs = pickle.load(f)
	```

## S_C_L-GGGGG-3-8-splitAll.pickl:

	S_C_L is FreqSeqs + the quality of FreqSeqs

	```python
	with open('S_C_L-%s.pickl'%dataFileName, 'rb') as f: 
    	S_C_L = pickle.load(f)
    ```