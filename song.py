"""Contains classes for representing song with melody and chords.

Example of song structure:

					        Song
					 _________________
					/        |        \
				 Verse     Verse     Verse
				 / |        /  \        \
		  Phrase Phrase Phrase Phrase  Phrase
		  /  ...   ...   ...    ...  ...  \
	   Chord                             Chord
	   /  ...  ...  ...  ...  ...  ...  ... \
	  Note                                  Note

"""

import music
import random
import util


ROOT = music.C4
LEGAL_PITCHES = [ROOT+intv for intv in music.MAJOR_SCALE]



class Mutatable(object):
	"""An element of a song that may mutate (e.g. chords,verses)"""
	def __init__(self):
		self.mutated = False # To ensure mutation <= once per generation

	def _get_children(self):
		"""Returns list of immediate descendents"""
		return []

	def _mutate(self):
		"""Mutates object in place"""
		raise UnimplementedError

	def recursive_mutate(self):
		"""Calls _mutate on self and all descendents"""
		if not self.mutated:
			self._mutate()
			self.mutated = True
			for child in self._get_children():
				child.recursive_mutate()
			self._finish_generation()

	def _finish_generation(self):
		self.mutated = False

	def copy(self):
		"""Return an identical object"""
		raise UnimplementedError

	def get_duration(self):
		"""Return the absolute duration of the object in the song"""
		raise UnimplementedError

	def get_all_notes(self):
		"""Returns a list of all leaf Notes"""
		raise UnimplementedError



class Note(Mutatable):
	"""A note is the atomic object of a song."""
	def __init__(self, pitch, duration, song):
		super(Note, self).__init__()
		self.pitch = pitch # From the jython music library
		self.duration = duration # A float, usually a power of 2
		self.mutate_prob = 0.005 # Probability of mutating per generation
		self.song = song # Song that this Note belongs to

	def get_pitch(self):
		return self.pitch

	def _mutate(self):
		"""A note can only mutate by changing its pitch."""
		if not self.mutated:
			if random.random() < self.mutate_prob:
				idx = self.song.legal_pitches.index(self.pitch)
				idx = random.randint(-3, 3) % len(self.song.legal_pitches)
				self.pitch = self.song.legal_pitches[idx]

	def copy(self):
		return Note(self.pitch, self.duration, self.song)

	def get_duration(self):
		return self.duration

	def scale_duration(self, scaleFactor):
		self.duration *= scaleFactor

	def get_all_notes(self):
		return [self]



class Chord(Mutatable):
	"""A chord is defined by its root and inversion.
	It also contains a Note list, which is the melody.
	"""
	def __init__(self, root, scale, song, note_seq=None, inversion=1, play=True):
		super(Chord, self).__init__()
		self.root = root # Index into scale
		self.scale = scale # List of jython pitches (length 8)
		self.note_seq = note_seq # A list of Notes
		self.song = song # The Song this Chord belongs to
		self.mutate_prob = 0.05 # Probability of mutating per generation
		self.inversion = inversion # Order of constituent pitches (1, 2, or 3)
		self.play = play

		assert self.root < 8
		assert len(self.scale) == 7, len(self.scale)

	def get_pitches(self, inversion=None):
		pitches = []
		if inversion is None:
			inversion = self.inversion
		# 1-3-5
		if inversion == 1:
			pitches.append(self.scale[self.root])
			pitches.append(self.scale[(self.root+2)%7])
			pitches.append(self.scale[(self.root+4)%7])
		# 3-5-1
		elif inversion == 2:
			pitches.append(self.scale[self.root]+12)
			pitches.append(self.scale[(self.root+2)%7])
			pitches.append(self.scale[(self.root+4)%7])
		# 5-3-1
		elif inversion == 3:
			pitches.append(self.scale[self.root]+12)
			pitches.append(self.scale[(self.root+2)%7]+12)
			pitches.append(self.scale[(self.root+4)%7])
		else:
			raise('Invalid inversion "'+str(self.inversion)+'"')

		return pitches

	def notes_from_chord(self, num_notes=1):
		"""Returns random notes belonging to the chord."""
		pitches = [music.REST]+self.get_pitches(1)
		notes = []
		note_dur = self.get_duration()/(1.0*num_notes)
		for _ in range(num_notes):
			pitch = random.choice(pitches)
			note = Note(pitch, note_dur, self.song)
			notes.append(note)
		return notes

	def reset_notes(self):
		num_notes = len(self.note_seq)
		self.note_seq = self.notes_from_chord(num_notes=num_notes)

	def _mutate(self):
		if random.random() < self.mutate_prob:
			# change inversion
			if random.random() < 0.25:
				self.inversion = random.choice(range(1, 4))

			# change root
			if random.random() < 0.25:
				r = random.choice(range(7))
				self.root = r
				# have notes follow root change
				self.reset_notes()
			
			if random.random() < 0.05:
				# merge two notes
				if random.random() < 0.5:
					util.random_merge(self.note_seq)
				# split a note
				else:
					util.random_split(self.note_seq)

			# swap 2 notes
			if random.random() < 0.05:
				util.random_swap(self.note_seq)

			# turn on or off for playback
			if random.random() < 0.5:
				self.play = not self.play

	def initialize_note_seq(self, default=None):
		if default is not None:
			self.note_seq = [Note(default, 1.0, self.song)]
		else:
			self.note_seq = self.notes_from_chord()

	def _get_children(self):
		return self.note_seq

	def copy(self):
		new_seq = [n.copy() for n in self.note_seq]
		return Chord(self.root, self.scale, self.song, new_seq, self.inversion)

	def get_duration(self):
		if self.note_seq is None:
			return 1.0
		return sum([e.get_duration() for e in self.note_seq])

	def scale_duration(self, scale_factor):
		notes = set(self.get_all_notes())
		for note in notes:
			note.scale_duration(scale_factor)

	def get_all_notes(self):
		return self.note_seq



class MutatableSequence(Mutatable):
	"""A mutatable list of Mutatables.

	Contains several methods of mutation for sequences."""
	def __init__(self, sequence, song):
		super(MutatableSequence, self).__init__()
		self.sequence = sequence # a list of Mutatables
		self.mutate_prob = None # Probability of mutating per generation
		self.song = song # Song that sequence belongs to

	def _get_children(self):
		return self.sequence

	def _mutate(self):
		if random.random() < self.mutate_prob:
			
			if random.random() < 0.1:
				# merge two elements
				if random.random() < 0.5:
					util.random_merge(self.sequence)
				# split an element
				else:
					util.random_split(self.sequence)

			# swap 2 elements
			if random.random() < 0.1:
				util.random_swap(self.sequence)

			# repeat element
			if random.random() < 0.1:
				util.random_repeat(self.sequence)

			# copy self
			if random.random() < 0.1:
				util.random_copy(self.sequence)

	def get_duration(self):
		return sum([e.get_duration() for e in self.sequence])

	def scale_duration(self, scale_factor):
		notes = set(self.get_all_notes())
		for note in notes:
			note.scale_duration(scale_factor)

	def get_all_notes(self):
		all_notes = []
		for child in self._get_children():
			all_notes.extend(child.get_all_notes())
		return all_notes


class Phrase(MutatableSequence):
	def __init__(self, sequence, song):
		super(Phrase, self).__init__(sequence, song)
		self.mutate_prob = 0.15

	def copy(self):
		return Phrase([x.copy() for x in self.sequence], self.song)	



class Verse(MutatableSequence):
	def __init__(self, sequence, song):
		super(Verse, self).__init__(sequence, song)
		self.mutate_prob = 0.1

	def copy(self):
		return Verse([x.copy() for x in self.sequence], self.song)



class Song(Mutatable):
	"""Top level object containing everything for a song."""
	def __init__(self, root, tempo, legal_pitches):
		super(Song, self).__init__()
		self.tempo = tempo # beats per minute
		self.verse_seq = [] # list of Verses
		self.mutate_prob = 0.1 # Probability of mutating per generation
		self.root = root # Key of the song, pitch from music library
		self.legal_pitches = legal_pitches # Pitches from music library

	def _get_children(self):
		return self.verse_seq

	def _mutate(self):
		if random.random() < self.mutate_prob:
			# change tempo
			if random.random() < 0.5:
				self.tempo += random.randint(-10, 10)
			# swap two verse sequences
			if random.random() < 0.05:
				util.random_swap(self.verse_seq)

	def copy(self):
		verse_seq = [v.copy() for v in self.verse_seq]
		song_copy = Song(self.root, self.tempo, self.legal_pitches)
		song_copy.add_verses(verse_seq)
		return song_copy

	def add_verses(self, verses):
		self.verse_seq.extend(verses)

	def write_to_midi(self, outfile="out.mid"):
		song = music.Score("Song", self.tempo)
		chords = music.Part(music.PIANO, 1)
		melody = music.Part(music.VIBES, 0)
		melody_phrase = music.Phrase(0.0)
		chord_phrase = music.Phrase(0.0)

		all_chords_pitches = []
		all_chords_durations = []
		all_melody_pitches = []
		all_melody_durations = []

		for verse in self.verse_seq:
			for phrase in verse.sequence:
				for chord in phrase.sequence:
					if chord.play:
						all_chords_pitches.append(chord.get_pitches())
					else:
						all_chords_pitches.append(music.REST)
					all_chords_durations.append(chord.get_duration())
					for note in chord.note_seq:
						all_melody_pitches.append(note.get_pitch())
						all_melody_durations.append(note.get_duration())

		chord_phrase.addNoteList(all_chords_pitches, all_chords_durations)
		melody_phrase.addNoteList(all_melody_pitches, all_melody_durations)
		chords.addPhrase(chord_phrase)
		melody.addPhrase(melody_phrase)
		song.addPart(chords)
		song.addPart(melody)

		music.Write.midi(song, outfile)
		print "Written to "+outfile


