from evolution import *
import critic_util
import music
import collections

ROOT = 0
SCALE = [music.C4+intv for intv in music.MAJOR_SCALE]
LEGAL_PITCHES = SCALE+[music.REST, music.C5]
SURVIVAL_RATE = 0.5

class Critic(): 
	def critique_song(self):
		raise UnimplementedError

class TempoCritic(Critic):
	def __init__(self, tempo=40):
		self.tempo = tempo

	def critique_song(self, song):
		fitness = 1.0/(1.0+abs(song.tempo-self.tempo))
		return fitness

class LengthCritic(Critic):
	def __init__(self, length=16):
		self.length = length

	def critique_song(self, song):
		total_notes = 0
		for verse in song.verse_seq:
			for phrase in verse.sequence:
				for chord in phrase.sequence: 
					if chord.note_seq is not None:
						for note in chord.note_seq:
							total_notes += 1
		fitness = 1.0/(1.0+abs(total_notes-self.length))
		return fitness

class ChordCountCritic(Critic):
	def __init__(self, length=4):
		self.length = length

	def critique_song(self, song):
		total_chords = 0
		for verse in song.verse_seq:
			for phrase in verse.sequence:
				for chord in phrase.sequence:
					total_chords += 1
		fitness = 1.0/(1.0+abs(total_chords-self.length))
		return fitness

class AscendingMelodyCritic(Critic):
	# Gives +1 if two adjacent notes are ascending by a step or half step
	def critique_song(self, song):
		previous_note_pitch = 0
		total_notes = 0
		total_score = 0
		for verse in song.verse_seq:
			for phrase in verse.sequence:
				for chord in phrase.sequence:
					if chord.note_seq is not None:
						for note in chord.note_seq:
							dist = note.pitch - previous_note_pitch
							if dist == 1 or dist == 2:
								total_score += 1
							total_notes += 1
							previous_note_pitch = note.pitch
		return total_score/(1.0*total_notes)


class DescendingMelodyCritic(Critic):
	# Gives +1 if two adjacent notes are descending by a step or half step
	def critique_song(self, song):
		previous_note_pitch = 0
		total_notes = 0
		total_score = 0
		for verse in song.verse_seq:
			for phrase in verse.sequence:
				for chord in phrase.sequence:
					if chord.note_seq is not None:
						for note in chord.note_seq:
							dist = note.pitch - previous_note_pitch
							if dist == -1 or dist == -2:
								total_score += 1
							total_notes += 1
							previous_note_pitch = note.pitch
		return total_score/(1.0*total_notes)						

class RhythmCritic(Critic):
	def __init__(self, rhythm=10.0):
		self.best_rhythm = rhythm
	# Assumes greater standard deviation in durations up to 10.0 means more sophisticated song
	def critique_song(self, song):
		sum_devs = 0.0
		num_opps = 0
		for verse in song.verse_seq:
			for phrase in verse.sequence:
				for chord in phrase.sequence:
					if chord.note_seq is None:
							sum_devs+=0.0
							continue
					else:
						durations = [e.get_duration() for e in chord.note_seq]
						num_opps+=1
						sum_devs+=critic_util.stdev(durations)
		avg_devs = sum_devs/num_opps
		return 1.0/(1.0+abs(self.best_rhythm - avg_devs))


class MajorCritic(Critic):
	# Assumes more major chords are more pleasing to the year
	def critique_song(self, song):
		num_major_chords = 0
		for verse in song.verse_seq:
			for phrase in verse.sequence:
				for chord in phrase.sequence:
					num_major_chords+= critic_util.is_major_chord(chord)
		return num_major_chords

class MinorCritic(Critic):
	# Assumes more minor chords are more pleasing to the year
	def critique_song(self, song):
		num_major_chords = 0
		num_chords = 0
		for verse in song.verse_seq:
			for phrase in verse.sequence:
				for chord in phrase.sequence:
					num_major_chords+= critic_util.is_major_chord(chord)
					num_chords += 1
		major_frac = num_major_chords/(1.0*num_chords)
		return 1.0-major_frac


class ChordProgressionCritic(Critic):
	# Prefers a given chord progression (given by triads)
	def __init__(self, progression):
		self.progression = progression

	def critique_song(self, song):
		total_progression_score = 1
		total_opportunities = 0
		position_in_progression = 0

		num_major_chords = 0
		for verse in song.verse_seq:
			for phrase in verse.sequence:
				for chord in phrase.sequence:
					total_opportunities += 1
					if chord.root == self.progression[position_in_progression]:
						total_progression_score += 1
						position_in_progression += 1
						position_in_progression %= len(self.progression)
					else:
						position_in_progression = 0

		return total_progression_score/(1.0*total_opportunities)

class FollowingEmCritic(Critic):
	def critique_song(self, song):
		# Assumes em ->am or F as sign of better song beacuse 93% of songs follow this sequence
		progression_count = 0
		progression_opps = 0
		for verse in song.verse_seq:
			for phrase in verse.sequence:
				for index,chord in enumerate(phrase.sequence):
					# e minor in C major 
					if chord.root == 3 and (not index == len(phrase.sequence)) and chord.scale == music.MAJOR_SCALE:
						progression_opps+=1
						if phrase.sequence[index+1].root == 4 or phrase.sequence[index+1].root == 6: 
							progression_count+=1
		if progression_opps == 0:
			return 0
		return progression_count*1.0/progression_opps


class MeterDurationCritic(Critic):
	# Assumes rhythm that follows one of the poetic meters is better
	@staticmethod
	def get_patterns():
		IAMB = [0.5, 1]
		ANAPEST = [0.5, 0.5, 1]
		TROCHEE = [1, 0.5]
		DACTYL = [1, 0.5, 0.5]
		AMPHIBRACH = [0.5, 1, 0.5]
		return [IAMB, ANAPEST, TROCHEE, DACTYL, AMPHIBRACH]

	def critique_song(self, song):
		patterns = self.get_patterns()
		metric_matches = 0.0
		total_notes = 0
		for verse in song.verse_seq:
			for phrase in verse.sequence:
				for chord in phrase.sequence:
					for index, note in enumerate(chord.note_seq):
						total_notes+=1
						if index % 3 == 0 and index > 2:
							segment = [chord.note_seq[index-2].duration, chord.note_seq[index-1].duration, note.duration]
							ratios = map(lambda x:1.0-x*1.0/max(segment), segment)
							deviation_from_ratios = sum(ratios)
							metric_matches+=(1.0/(1+0.01+deviation_from_ratios))
						if index % 2 == 0 and index > 1:
							segment = [chord.note_seq[index-1].duration, note.duration]
							ratios = map(lambda x: 1.0-x*1.0/max(segment), segment)
							deviation_from_ratios = sum(ratios)
							metric_matches+=(1.0/(1+0.01+deviation_from_ratios))
		return metric_matches/(total_notes*2.0)

class ChordDurationRepetitionCritic(Critic):
	# Assumes fewer kinds of durations is better
	def critique_song(self, song):
		all_durations = {}
		for verse in song.verse_seq:
			for phrase in verse.sequence:
				for chord in phrase.sequence:
					for note in chord.note_seq:
						if note in all_durations:
							all_durations[note]+=1
						else:
							all_durations[note] = 1
		return 1.0/len(all_durations)

class RestRatioCritic(Critic):
	# Assumes getting close to a ratio between notes and rests are better
	def __init__(self, ratio=4.0):
		self.ratio = ratio # non-rest to rest ratio

	def critique_song(self, song):
		rest_duration = 0.0
		note_duration = 0.0
		for verse in song.verse_seq:
			for phrase in verse.sequence:
				for chord in phrase.sequence:
					for note in chord.note_seq:
						if note.pitch == music.REST:
							rest_duration+= note.duration
						else:
							note_duration+= note.duration
		return 1.0/(1.0+abs(self.ratio - (note_duration/(1.0+rest_duration))))

