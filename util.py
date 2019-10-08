import random


def random_swap(l):
	n = len(l)
	a = random.randint(0, n-1)
	b = random.randint(0, n-1)
	l[b], l[a] = l[a], l[b]

def random_copy(l):
	d = sum([e.get_duration() for e in l])
	idx = random.randint(0, len(l)-1)
	elm = l[idx]
	elm_copy = elm.copy()
	l[idx] = elm_copy
	assert d == sum([e.get_duration() for e in l])

def random_merge(l):
	d = sum([e.get_duration() for e in l])

	if len(l) >= 2:
		firstIdx = random.randint(0, len(l)-2)
		firstDur = l[firstIdx].get_duration()
		secondDur = l[firstIdx+1].get_duration()
		duration_scale = (firstDur+secondDur)/(1.0*firstDur)
		l[firstIdx] = l[firstIdx].copy()
		l[firstIdx].scale_duration(duration_scale)
		del l[firstIdx+1]

	temp_sum = sum([e.get_duration() for e in l])
	if not abs(round(d, 4) - round(temp_sum, 4)) < 0.0002: print round(d, 4), round(temp_sum, 4)
	assert abs(round(d, 4) - round(temp_sum, 4)) < 0.0002

def random_repeat(l):
	idx = random.randint(0, len(l)-1)
	elm_to_repeat = l[idx]
	elm_copy = elm_to_repeat.copy()
	random_idx = random.randint(0, len(l))
	l.insert(random_idx, elm_copy)

def random_split(l):
	d = sum([e.get_duration() for e in l])

	idx = random.randint(0, len(l)-1)
	elm_to_split = l[idx]
	for note in elm_to_split.get_all_notes():
		if note.duration < 0.25:
			return
	elm_to_split = elm_to_split.copy()
	l[idx] = elm_to_split
	elm_to_split.scale_duration(0.5)
	elm_copy = elm_to_split.copy()
	l.insert(idx+1, elm_copy)
	
	temp_sum = sum([e.get_duration() for e in l])
	if not abs(round(d, 4) - round(temp_sum, 4)) < 0.0002: print round(d, 4), round(temp_sum, 4)
	assert abs(round(d, 4) - round(temp_sum, 4)) < 0.0002

def chord_list_to_melody(chords):
	return [c.note_from_chord() for c in chords]
