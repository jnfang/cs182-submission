from random_song import RandomSong as rs
import critic
import random
import music
import critic_util
import sys

ROOT = 0
SCALE = [music.C4+intv for intv in music.MAJOR_SCALE]
LEGAL_PITCHES = SCALE+[music.REST, music.C5]
SURVIVAL_RATE = 0.5
SURVIVAL_NOISE = 0.0
CROSSOVER_RATE = 1.0

class Evolution(object):
	def __init__(self,
				 size,
				 root=ROOT,
				 scale=SCALE,
				 legal_pitches=LEGAL_PITCHES,
				 survival_rate=SURVIVAL_RATE, 
				 survival_noise=SURVIVAL_NOISE):
		self.size = size
		self.generation = 0
		self.root = root
		self.scale = scale
		self.legal_pitches = legal_pitches
		self.survival_rate = survival_rate
		self.survival_noise = survival_noise
		self.population = self.birth()

	def birth(self):
		"""Returns set of random Songs of size specified on initialization"""
		return [rs.random_song(self.root, self.legal_pitches, self.scale) for x in xrange(self.size)]

	def get_parents(self):
		"""Calls fitness functions and sorts to return the most fit parents by surival rate"""
		pop_data = []
		for s in self.population:
			fitness = self.get_fitness(s)
			pop_data.append((s, fitness))
		sorted(pop_data, key=lambda x:x[1], reverse=True)
		survived = pop_data[:int(len(pop_data)*self.survival_rate)]
		if self.survival_noise > 0.0:
			to_choose = pop_data[int(len(pop_data)*self.survival_rate):]
			spots_left = (int) (len(to_choose)*self.survival_noise)
			survived += random.sample(to_choose, spots_left)
		return [x[0] for x in survived]

	def next_generation(self):
		"""Calls mingle to create next generation"""
		parents = self.get_parents()
		[p.recursive_mutate() for p in parents]
		self.population = self.mingle(parents, self.size)
		self.generation +=1

	def mingle(self, mutated_parents, num_offspring):
		"""Returns the new population from the mutated parents"""
		children = []
		num_children = 0
		num_parents = len(mutated_parents)
		random.shuffle(mutated_parents)
		idx = 0
		while num_children < num_offspring:
			parent_one = mutated_parents[idx % num_parents]
			parent_two = mutated_parents[(idx + 1) % num_parents]
			children.append(self.crossover(parent_one, parent_two))
			idx += 2
			num_children += 1

		return children

	def get_current_best_song(self):
		"""Returns the most fit song using current fitness function"""
		pop_data = []
		for s in self.population:
			fitness = self.get_fitness(s)
			pop_data.append((s, fitness))
		sorted(pop_data, key=lambda x:x[1], reverse=True)
		return pop_data[0][0]

	def crossover(self, parent_one, parent_two):
		"""Simple crossover in which the more fit parent is chosen"""
		if self.get_fitness(parent_one) > self.get_fitness(parent_two):
			return parent_one.copy()
		return parent_two.copy()

	def get_fitness(self, song):
		raise UnimplementedError

class ConstantEvolution(Evolution):

	def get_fitness(self, song):
		"""Only selects for Songs that are fast in order to test alg correctness"""
		return song.tempo

class CriticEvolution(Evolution):
	def __init__(self,
				 size,
				 critics,
				 root=ROOT,
				 scale=SCALE,
				 legal_pitches=LEGAL_PITCHES,
				 survival_rate=SURVIVAL_RATE,
				 survival_noise=SURVIVAL_NOISE):

		self.critics = critics
		super(CriticEvolution, self).__init__(size, root, scale, legal_pitches, survival_rate)

	def get_fitness(self, song):
		fitnesses = []
		for critic in self.critics:
			fitnesses.append(critic.critique_song(song))
		return sum(fitnesses)

class CriticCrossoverEvolution(CriticEvolution):
	def __init__(self,
				 size,
				 critics,
				 root=ROOT,
				 scale=SCALE,
				 legal_pitches=LEGAL_PITCHES,
				 survival_rate=SURVIVAL_RATE,
				 survival_noise=SURVIVAL_NOISE,
				 crossover_rate=CROSSOVER_RATE):

		self.crossover_rate = crossover_rate
		self.critics = critics
		super(CriticEvolution, self).__init__(size, root, scale, legal_pitches, survival_rate)

	def crossover(self, parent_one, parent_two):
		"""Simulates random crossover between parents over one and two points of crossover"""
		prob = random.random() 
		if prob > self.crossover_rate:
			max_crossing_pt = min(len(parent_one.verse_seq), len(parent_two.verse_seq))
			pivot = random.randint(0, max_crossing_pt)
			new_parent = parent_two.copy()
			new_parent.verse_seq = parent_two.verse_seq[:pivot] + parent_one.verse_seq[pivot:]
			return new_parent
		elif prob > self.crossover_rate*2:
			better_parent = parent_two
			other_parent = parent_one
			if self.get_fitness(parent_one) > self.get_fitness(parent_two):
				better_parent = parent_one
				other_parent = parent_two
			cross_pts = sorted(random.sample(xrange(len(other_parent.verse_seq)), 2))
			insert_pts = sorted(random.sample(xrange(len(better_parent.verse_seq)), 2))
			new_parent = better_parent.copy()
			new_parent.verse_seq = better_parent.verse_seq[insert_pts[0]:] + other_parent.verse_seq[insert_pts[0]:insert_pts[1]] + better_parent.verse_seq[insert_pts[1]:]
			return new_parent
		else:
			return super(CriticCrossoverEvolution, self).crossover(parent_one, parent_two)			

def parse_critics(critics_str):
	critics_dict = {"Tempo": critic.TempoCritic(), "Length":critic.LengthCritic(), "ChordCount":critic.ChordCountCritic(), "AscendingMelody":critic.AscendingMelodyCritic(),"DescendingMelody": critic.DescendingMelodyCritic(), "Rhythm": critic.RhythmCritic(), "Major": critic.MajorCritic(), "Minor": critic.MinorCritic(), "ChordProgression": critic.ChordProgressionCritic([0,3,4]), "FollowingEm": critic.FollowingEmCritic(), "MeterDuration": critic.MeterDurationCritic(), "ChordDurationRepetition": critic.ChordDurationRepetitionCritic(), "RestRatio": critic.RestRatioCritic()}
	critics = []
	for one_critic in input_critics:
		critics.append(critics_dict[one_critic])
	return critics

if __name__ == '__main__':
	print "\n\nWriting initial MIDI to: ", sys.argv[1]
	print "\nWriting final MIDI to: ", sys.argv[2]

	input_critics = sys.argv[3].split(",")
	critics = parse_critics(input_critics)
	print_critics = ""
	for index, single_critic in enumerate(critics):
		if not index == len(critics)-1:
			print_critics+=(single_critic.__class__.__name__ +", ")
		else:
			print_critics+=(single_critic.__class__.__name__)
	print "\nRunning critics: ", print_critics

	print "\nRunning for ", sys.argv[4], " generations\n"
	num_gens = int(sys.argv[4])
	evo = CriticEvolution(100, critics)
	first_best_song = evo.get_current_best_song()
	for x in xrange(num_gens):
		evo.next_generation()
		if x % 10 == 0: 
			print "At generation: ", x 
			print "Best fitness: ", evo.get_fitness(evo.get_current_best_song())
	last_best_song = evo.get_current_best_song()
	first_best_song.write_to_midi("../results/"+ sys.argv[1]+".mid")
	last_best_song.write_to_midi("../results/" + sys.argv[2]+".mid")


