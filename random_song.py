from music import *

import random
import song

class RandomSong():
	@staticmethod
	def random_song(root,
					legal_pitches,
					scale,
					num_phrases=3,
					phrase_length=4,
					num_verses=2,
					verse_length=2,
					tempo=80,
					num_mutations=0):

		test_song = song.Song(root=root, tempo=tempo, legal_pitches=legal_pitches)

		chords = [song.Chord(root, scale, test_song) for _ in range(phrase_length)]
		[chord.initialize_note_seq(default=REST) for chord in chords]

		phrase = song.Phrase(chords, test_song)
		chord_phrases = [phrase for _ in range(num_phrases)]
		verse = song.Verse(chord_phrases, test_song)
		verses = [verse for _ in range(num_verses)]
		test_song.add_verses(verses)

		for _ in range(num_mutations):
			test_song.recursive_mutate()

		return test_song