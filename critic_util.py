import math
import music

def average(s): 
	return sum(s) * 1.0 / len(s)

def variance(s): 
	return map(lambda x: (x - average(s))**2, s)

def stdev(s): 
	return math.sqrt(average(variance(s)))

def is_major_chord(chord):
		if not chord.scale == [music.C4+intv for intv in music.MAJOR_SCALE]:
			return 0
		else:
			if chord.root == 0 or chord.root == 3 or chord.root == 4 or chord.root == 7:
				return 1
			return 0
