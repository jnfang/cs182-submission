CS182 Artificial Intelligence Project

=========

# To run our program, first go into the jythonMusic directory and run
`sh jython.sh ../evolution.py num_gens gen0_filename1 genx_file_name2 critic1,critic2`

where command line arguments are as follows:
- Int - number of generations to run (i.e. 100)
- Initial file name - file name for MIDI file for generation 0 best song
- Final file name - file name for MIDI file after specified number of generations
- String - critics used that follows from shortened names and delimited by commas (i.e. “Tempo” → critic.TempoCritic())


# Sample command:
`sh jython.sh ../evolution.py 2critic_gen0 2critic_gen100 ChordProgression,Tempo 100`

While running the the file, console will first print the initialization of the Jython Music script with “Audio:” specifications. Then subsequent outputs delineating:
`Writing initial MIDI to: 2critic_gen0`

`Writing final MIDI to: 2critic_gen100`

`Running critics: ChordProgressionCritic, TempoCritic`

`Running for 100 generations`

These should reflect the command line arguments entered.
The two files `2critic_gen0.mid`, `2critic_gen100.mid` are written to the results directory where those files are already in place from running the demo.

As we are iterating through generations our program also outputs the generation count for every 10 generations and the best fitness score for that generation.

At generation: 0

Best fitness: 0.566056910569
...


After the generations are completed, Jython Music will output to terminal that it is writing the MIDI files and when the completion status for the second file is shown
(i.e.Written to ../results/2critic_gen100.mid)
you will need to Ctr-C exit out of the script. This is an attribute of the Jython Music library script.

To view and hear the generated MIDI files, we can open them with any music composition software. Directions for installing Finale Notepad 2012 can be found here and an account must created
http://www.finalemusic.com/products/finale-notepad/resources/
Directions for installing MuseScore can be found here
https://musescore.org/
