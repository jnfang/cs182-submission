################################################################################################################
# audio.py      Version 1.0         30-Oct-2014       Chris Benson and Bill Manaris

###########################################################################
#
# This file is part of Jython Music.
#
# Copyright (C) 2014 Chris Benson and Bill Manaris
#
#    Jython Music is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
#    (at your option) any later version.
#
#    Jython Music is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Jython Music.  If not, see <http://www.gnu.org/licenses/>.
#
###########################################################################

#
# Imports jSyn packages into jython.  Also provides additional functionality related to audio manipulation and playback.
#
#
# REVISIONS:
#
# 1.0   30-Oct-2014 (bm) First draft.
#

from music import *


##### jSyn synthesizer ######################################
# create the jSyn synthesizer (one synthesizer for everything)

from java.io import *  # for File

from com.jsyn import *
from com.jsyn.data import *
from com.jsyn.unitgen import *
from com.jsyn.util import *

from math import *

class jSyn_AudioEngine():
   """Encasulates a jSyn synthesizer.  Only one may exist (no need for more).
      We modularize the synth and its operations in a class for convenience.
   """
   
   instance = None      # only one instance allowed (no need for more)
   
   def __init__(self):
   
      self.FRAMERATE = 44100                 # default frame rate
      self.inputPortID = -1                  # use default audio input
      self.numberInputs = 2                  # stereo (use 1 for mono)
      self.outputPortID = -1                 # use default audio output
      self.numberOutputs = 2                 # stereo (use 1 for mono)
      
      if jSyn_AudioEngine.instance == None:  # first time?
      
         self.synth = JSyn.createSynthesizer()   # create synthesizer         
         jSyn_AudioEngine.instance = self        # remember the only allowable instance         
         
         self.samples = []                       # holds audio samples connected to synthesizer

      else:                                  # an instance already exists
         print "Only one jSyn audio engine may exist (use existing one)."

   def start(self):
      """Starts the synthesizer."""
      self.synth.start(self.FRAMERATE, self.inputPortID, self.numberInputs, self.outputPortID, self.numberOutputs) # start the synth  (will need parameters if the sample is a live sample for number of inputs and their ID's)
      for sample in self.samples:   # and all the sample lineOut units
         sample.lineOut.start()
  
   def stop(self):
      """Stops the synthesizer."""
      
      self.synth.stop()             # stop the synth      
      for sample in self.samples:   # and all the sample lineOut units
         sample.lineOut.stop()

# *** This should probably be happening inside AudioSample() - much cleaner.
   def add(self, sample):
      """Connects an audio sample to the jSyn lineOut unit."""
      
      self.synth.add( sample.player )   # add the sample's player to the synth
      self.synth.add( sample.amplitudeSmoother )  # add the sample's amplitude linearRamp to the synth
      self.synth.add( sample.panLeft )  # add the sample's left pan control to the synth
      self.synth.add( sample.panRight ) # add the sample's right pan control to the synth
      self.synth.add( sample.lineOut )  # add the sample's output mixer to the synth
      self.samples.append( sample )     # remember this sample

   def addLive(self, sample):
      """Connects an live sample to the jSyn lineOut unit."""
      
      self.synth.add( sample.player )   # add the sample's player to the synth
      self.synth.add( sample.lineOut )  # add the sample's lineOut to the synth
      self.synth.add( sample.lineIn  )
      self.synth.add( sample.writer )
      self.samples.append( sample )     # remember this sample
   
# *** NOTE:  This synthesizer should be started only when an audio file (AudioSample) is created.
#            Perhaps do the same with the Java synthesizer above?  Is that synthesizer needed?

# create the jSyn synthesizer (again, only one for everything)
jSyn = jSyn_AudioEngine()
jSyn.start()                 # should this be happening here? (or inside the Audio class, when needed?) ***

##### AudioSample class ######################################

import os   # to check if provided filename exists

class AudioSample():
   """
   Encapsulates a sound object created from an external audio file, which can be played once,
   looped, paused, resumed, and stopped.  Also, each sound has a MIDI pitch associated with it
   (default is A4), so we can play different pitches with it (through pitch shifting).
   Finally, we can set/get its volume (0-127).
      
   Ideally, an audio object will be created with a specific pitch in mind.
      
   Supported data formats are WAV or AIF files (16, 24 and 32 bit PCM, and 32-bit float).
   """
   
   def __init__(self, filename, pitch=A4, volume=127):
   
      # ensure the file exists (jSyn will NOT complain on its own)
      if not os.path.isfile(filename):
         raise ValueError("File '" + str(filename) + "' does not exist.")
         
      # file exists, so continue   
      self.filename = filename
      
      self.defaultPitch = pitch  # the default pitch of the audio file (sample)
      self.pitch = pitch         # holds playback MIDI pitch (may be different from default pitch)
      self.frequency = self.__convertPitchToFrequency__(pitch)  # holds the frequency equivalent of the current MIDI pitch
      
      # remember is sample is paused or not - needed for function isPaused()
      self.hasPaused = False

      # load and create the audio sample
      SampleLoader.setJavaSoundPreferred( False )  # use internal jSyn sound processes
      datafile = File(self.filename)               # get sound file 
      self.sample = SampleLoader.loadFloatSample( datafile )  # load it as a a jSyn sample     
      self.channels = self.sample.getChannelsPerFrame()       # get number of channels in sample

      # create lineOut unit (it mixes output to computer's audio (DAC) card)
      self.lineOut = LineOut()    

      # create panning control (we simulate this using two pan controls, one for the left channel and
      # another for the right channel) - to pan we adjust their respective pan
      self.panLeft  = Pan()
      self.panRight = Pan()

      # NOTE: The two pan controls have only one of their outputs (as their names indicate)
      # connected to LineOut.  This way, we can set their pan value as we would normally, and not worry
      # about clipping (i.e., doubling the output amplitude).  Also, this works for both mono and
      # stereo samples.

      # create sample player (mono or stereo, as needed) and connect to lineOut mixer
      if self.channels == 1:    # mono audio?
         self.player = VariableRateMonoReader()                  # create mono sample player

         self.player.output.connect( 0, self.panLeft.input, 0)   # connect single channel to pan control 
         self.player.output.connect( 0, self.panRight.input, 0) 

      elif self.channels == 2:  # stereo audio?
         self.player = VariableRateStereoReader()                # create stereo sample player

         self.player.output.connect( 0, self.panLeft.input, 0)   # connect both channels to pan control 
         self.player.output.connect( 1, self.panRight.input, 0) 

      else:
         raise TypeError( "Can only play mono or stereo samples." )

      # now, connect pan control to mixer
      self.panLeft.output.connect( 0, self.lineOut.input, 0 ) 
      self.panRight.output.connect( 1, self.lineOut.input, 1 ) 

      # now, that panning is set up, initialize it to center
      self.panning = 63                # ranges from 0 (left) to 127 (right) - 63 is center
      self.setPanning( self.panning )  # and initialize
      
      # smooth out (linearly ramp) changes in player amplitude (without this, we get clicks)
      self.amplitudeSmoother = LinearRamp()
      self.amplitudeSmoother.output.connect( self.player.amplitude )   # connect to player's amplitude
      self.amplitudeSmoother.input.setup( 0.0, 0.5, 1.0 )              # set minimum, current, and maximum settings for control
      self.amplitudeSmoother.time.set( 0.2 )                           # and how many seconds to take for smoothing amplitude changes
             
             
      # play at original pitch
      self.player.rate.set( self.sample.getFrameRate() )  

      self.volume = volume           # holds current volume (0 - 127)
      self.setVolume( self.volume )  # set the desired volume      
      
 
      # NOTE:  Adding to global jSyn synthesizer
      jSyn.add(self)   # connect sample unit to the jSyn synthesizer
     
      
   ### functions to control playback and looping ######################
   def play(self, start=0, size=-1):
      """
      Play the sample once from the millisecond 'start' until the millisecond 'start'+'size' 
      (size == -1 means to the end). If 'start' and 'size' are omitted, play the complete sample.
      """
      # for faster response, restart playing (as opposed to queue at the end)
      if self.isPlaying():      # is another play is on?
         self.stop()            # yes, so stop it

      self.loop(1, start, size)
      

   def loop(self, times = -1, start=0, size=-1):
      """
      Repeat the sample indefinitely (times = -1), or the specified number of times 
      from millisecond 'start' until millisecond 'start'+'size' (size == -1 means to the end).
      If 'start' and 'size' are omitted, repeat the complete sample.
      """
    
      startFrames = self.__msToFrames__(start)
      sizeFrames = self.__msToFrames__(size)

      self.lineOut.start()   # should this be here?
      
      if size == -1:   # to the end?
         sizeFrames = self.sample.getNumFrames() - startFrames  # calculate number of frames to the end

      if times == -1:   # loop forever?
         self.player.dataQueue.queueLoop( self.sample, startFrames, sizeFrames )
         
      else:             # loop specified number of times
         self.player.dataQueue.queueLoop( self.sample, startFrames, sizeFrames, times-1 )     
      
   def stop(self):
      """
      Stop the sample play.
      """
      self.player.dataQueue.clear()   
      self.hasPaused = False          # reset
      
   def isPlaying(self):
      """
      Returns True if the sample is still playing.
      """
      return self.player.dataQueue.hasMore()   
      
   def isPaused(self):
      """
      Returns True if the sample is paused.
      """
      return self.hasPaused   
      
   def pause(self):
      """
      Pause the sample play (remembers current position for resume).
      """
      self.hasPaused = True
      self.lineOut.stop() 
   
   def resume(self):
      """
      Resume playing the sample (from the paused position).
      """
      self.lineOut.start()
      self.hasPaused = False          # reset

   ### functions to control playback parameters (pitch, frequency, and volume) ##########
   def setPitch(self, pitch):
      """
      Set the sample pitch (through pitch shifting from sample's base pitch).
      """
      self.pitch = pitch    # remember new playback pitch      
      self.frequency = self.__convertPitchToFrequency__(pitch)  # and corresponding pitch frequency
            
      semitones = pitch - self.defaultPitch  # get the pitch change in semitones                    
   
      # calculate the change in playback rate, and adjust the playback rate
      rateChange = self.__getFrequencyChangeBySemitones__( self.getFrameRate(), semitones )   
      self.__setPlaybackRate__( self.getFrameRate() + rateChange )        

   def getPitch(self):
      """
      Return the sample's current pitch (it may be different from the default pitch).
      """
      return self.pitch
         
   def getDefaultPitch(self):
      """
      Return the sample's default pitch.
      """
      return self.defaultPitch
         
   def setFrequency(self, freq):
      """
      Set the sample pitch frequency.
      """      
      self.setPitch( self.__convertFrequencyToPitch__(freq) )
            
   def getFrequency(self):
      """
      Return the playback frequency.
      """      
      return self.frequency
         
   def setPanning(self, panning):
      """
      Set the panning of the sample (panning ranges from 0 - 127).
      """
      self.panning = panning                                     # remember new panning
      panValue     = mapValue(self.panning, 0, 127, -1.0, 1.0)   # map panning from 0, 127 to -1.0, 1.0

      # NOTE: The two pan controls have only one of their outputs (as their names indicate)
      # connected to LineOut.  This way, we can set their pan value as we would normally, and not worry
      # about clipping (i.e., doubling the output amplitude).  Also, this works for both mono and
      # stereo samples.

      self.panLeft.pan.set( panValue )                           # and set it
      self.panRight.pan.set( panValue )                    
  
   def getPanning(self):
      """
      Return the current panning of the sample (panning ranges from 0 - 127).
      """
      return self.panning

   def setVolume(self, volume):
      """
      Set the volume (amplitude) of the sample (volume ranges from 0 - 127).
      """
      self.volume = volume                                 # remember new volume
      amplitude = mapValue(self.volume, 0, 127, 0.0, 1.0)  # map volume to amplitude
      #self.player.amplitude.set( amplitude )               # and set it
      self.amplitudeSmoother.input.set( amplitude )        # and set it
   
   def getVolume(self):
      """
      Return the current volume (amplitude) of the sample (volume ranges from 0 - 127).
      """
      return self.volume
      

   ### low-level functions related to FrameRate and PlaybackRate  ######################
   def getFrameRate(self):
      """
      Return the sample's default recording rate (e.g., 44100.0 Hz).
      """
      return self.sample.getFrameRate()

   def __setPlaybackRate__(self, newRate):
      """
      Set the sample's playback rate (e.g., 44100.0 Hz).
      """
      self.player.rate.set( newRate )
         
   def __getPlaybackRate__(self):
      """
      Return the sample's playback rate (e.g., 44100.0 Hz).
      """
      return self.player.rate.get()
         
   def __msToFrames__(self, milliseconds):
      """
      Converts milliseconds to frames based on the frame rate of the sample
      """
      return int(self.getFrameRate() * (milliseconds / 1000.0))
      
      
   ### helper functions for various conversions  ######################

   # Calculate frequency in Hertz based on MIDI pitch. Middle C is 60.0. You
   # can use fractional pitches so 60.5 would give you a pitch half way
   # between C and C#.  (by Phil Burk (C) 2009 Mobileer Inc)
   def __convertPitchToFrequency__(self, pitch):
      """
      Convert MIDI pitch to frequency in Hertz.
      """
      concertA = 440.0
      return concertA * 2.0 ** ((pitch - 69) / 12.0)

   def __convertFrequencyToPitch__(self, freq):
      """
      Converts pitch frequency (in Hertz) to MIDI pitch.
      """
      concertA = 440.0
      return log(freq / concertA, 2.0) * 12.0 + 69

   # following conversions between frequencies and semitones based on code 
   # by J.R. de Pijper, IPO, Eindhoven
   # see http://users.utu.fi/jyrtuoma/speech/semitone.html
   def __getSemitonesBetweenFrequencies__(self, freq1, freq2):
      """
      Calculate number of semitones between two frequencies.
      """
      semitones = (12.0 / log(2)) * log(freq2 / freq1)
      return int(semitones)

   def __getFrequencyChangeBySemitones__(self, freq, semitones):
      """
      Calculates frequency change, given change in semitones, from a frequency.
      """
      freqChange = (exp(semitones * log(2) / 12) * freq) - freq
      return freqChange
   
   
   
############################LiveSample Class####################################
 
class LiveSample():
   """
   Encapsulates a sound object created from (real time) recorded audio, which can
   be played once,looped, paused, resumed, and stopped.  Also, each sound has a
   MIDI pitch associated with it (default is A4), so we can play different pitches
   with it (through pitch shifting). Finally, we can set/get its volume (0-127).

   NOTE:  'maxSizeInSeconds' (default is 30) specifies the longest possible live 
          recording.  It should be increased as needed (keeping in mind that it
          uses up memory.)
   """
   
   def __init__(self, maxSizeInSeconds=30, pitch = A4, volume = 127): 

      print "LiveSample: you may record up to", maxSizeInSeconds, "seconds."
      
      self.SampleSize = maxSizeInSeconds*1000    # convert to milliseconds
      self.LOOP_CHANNELS  = 2 # 1 (for mono) or 2 (for stereo) - affects recording time (stereo cuts time down by half)
      self.MAX_LOOP_TIME  = self.__msToFrames__(self.SampleSize)
   
      # create sytnhesizer
      self.synth = JSyn.createSynthesizer()   # create synthsizer
   
      # create units
      self.lineIn       = LineIn()                  # create input line (stereo)
      self.lineOut      = LineOut()                 # create output line (stereo)
      self.writer       = FixedRateStereoWriter()   # captures incoming audio
      self.player       = VariableRateStereoReader()   # plays back looped audio
      self.sample       = FloatSample(self.MAX_LOOP_TIME, self.LOOP_CHANNELS)  # holds recorded audio
      
      self.panning = 63 #Set panning to center
      self.panLeft = Pan() # Pan control for the left channel
      self.panRight = Pan() # Pan control for the right channel
      self.setPanning(self.panning) #Initialize panning to center (63)
      
      self.volume = volume # holds current volume (0-127)
      self.setVolume(self.volume) # sets desired volume
      
      self.defaultPitch = pitch # the default pitch of the audio file (sample)
      self.pitch = pitch # holds playback MIDI pitch (may be different from default pitch   ****Might rename pitch to referencePitch)
      
      self.frequency = self.__convertPitchToFrequency__(pitch) # holds the frequency equivalent of the current MIDI pitch.
      
      # create time stamp variables
      self.beginRecordingTimeStamp = None    # holds timestamp of when we start recording
      self.endRecordingTimeStamp   = None    # holds timestamp of when we stop recording
      self.pauseMarker = SampleMarker()      # Creates a place marker that will be used when playing sample is paused
      self.recordedSampleSize = None         # holds overall length of time of sample rounded to nearest int
      
      self.recordingFlag = False             # boolean flag that is only true when the sample is being written to
      self.monitoringFlag = False            # boolean flag that is only true when monitor is turned on
      
      # connect line input to the sample writer (recorder)
      self.lineIn.output.connect(0, self.writer.input, 0)
      self.lineIn.output.connect(0, self.writer.input, 1)

      # connect sample reader (playback) to pan pot
      self.player.output.connect(0, self.panLeft.input, 0)
      self.player.output.connect(1, self.panRight.input, 0)
      
      # connect panned sample to line output
      self.panLeft.output.connect (0, self.lineOut.input, 0)
      self.panRight.output.connect (1, self.lineOut.input, 1)
      
      self.player.rate.set(jSyn.FRAMERATE)

      jSyn.addLive(self) # connect sample unit to the jSyn synthesizer
      
      #jSyn.start()
#############################################################################################################
   
   def startRecording(self):
      """
      Writes input port data to the sample and creates a time stamp to hold the position of the
      beginning of the sample.
      """
      print "You have started recording"
      # get a time stamp (in milliseconds), value returned as double
      self.beginRecordingTimeStamp = jSyn.synth.createTimeStamp() # holds timestamp of when we start recording
      #print self.beginRecordingTimeStamp
      # start recording into the sample
      # (sample gets written into by the writer)
      self.writer.dataQueue.queueOn( self.sample )
      self.writer.start()
      self.recordingFlag = True  # Recording has started
      
      
   def stopRecording(self):
      """
      Stops writing to the sample by stopping the writer. Another time stamp is created to hold the position
      of the end of the sample and an overall duration of the sample is calculated. This overall time is then
      converted to frames.
      """
      print "You have stopped recording"
      # stop recording into the sample
      self.writer.dataQueue.queueOff( self.sample )
      self.writer.stop()
      
      self.recordingFlag = False  # Recording has stopped
      
      # get a time stamp (in milliseconds), value returned as a double
      self.endRecordingTimeStamp =  jSyn.synth.createTimeStamp() # holds timestamp of when we stop recording
      
      # now, calculate the number of recorded frames in the sample   
      sampleDuration = self.endRecordingTimeStamp.getTime() - self.beginRecordingTimeStamp.getTime()  # recording duration in seconds
      
      
      if sampleDuration > (self.SampleSize / 1000): #If the recording time for the sample exceeds the allotted amount of recording time trim recording to max time allotted.
         print "You recorded more than allotted time, you recorded for a length of ", sampleDuration, " seconds!!"
         sampleDuration = self.SampleSize / 1000
      
      
      self.recordedSampleSize = int(jSyn.FRAMERATE * sampleDuration)      # convert to frames, then type casted to int since TimeStamp.getTime() returns a double and
                                                                           # and an int is needed for queueLoop(Sequential Data, int,int)
                                                                           # recordedSampleSize holds complete time length of recorded sample rounded to nearest int
      
   def isRecording(self):
      """
      Returns true if the LiveSample is recording
      """
      return self.recordingFlag

   def startMonitoring(self):
      """
      Turns sound-thru on, by connecting line in to line out.
      This allows us to hear (monitor) what's being captured 
      by the microphone, through the speakers.
      """
      
      self.monitoringFlag = True # Monitor is on
      # connect line input to the line output (to hear what you are recording)
      self.lineIn.output.connect(0, self.lineOut.input, 0)
      self.lineIn.output.connect(0, self.lineOut.input, 1)
      
   def stopMonitoring(self):
      """
      Turns sound-thru off by disconnecting line in from line out.
      """
      self.monitoringFlag = False  # Monitor is off
      # connect line input to the line output (to hear what you are recording)
      self.lineIn.output.disconnect(0, self.lineOut.input, 0)
      self.lineIn.output.disconnect(0, self.lineOut.input, 1)
      
   def isMonitoring(self):
      """
      Returns true if monitor is on
      """
      return self.monitoringFlag
   
   def play(self): 
      """
      Play the sample once from the millisecond 'start' until the end of the sample (size = the total time of recorded sample).
      If 'start' and 'size' is omitted, play complete sample
      !'start' and 'size' typecasted to ints for queueLoop function parameters??!
      """
      # start playing back from the sample (loop it)
      # (sample frames get retrieved by the reader)
      
      self.player.dataQueue.queueLoop( self.sample, self.pauseMarker.position, self.recordedSampleSize, 0 )   # playback (loop) the recorded portion of the sample once
      #self.player.start() #Don't need since Player is started when lineOut is started in AudioEngine
      self.lineOut.start()
   
   
   def loop(self, times = -1 , start = 0, size = -1):
      """
      Repeat the sample indefinitely (times = -1), or the specified number of times
      from millisecond 'start' to 'size' (size = the length of the recorded sample).
      !'start' and 'size' typecasted to ints for queueLoop function parameters??!
      """
      if size == -1:
         size = self.recordedSampleSize
      
      if start == 0:   # used for later if wanting to give option to user to play a small portion of their sample
         start = self.pauseMarker.position
         
      if times == -1: #If times = -1 then loop the sample continuously
         self.player.dataQueue.queueLoop(self.sample, start, size)
         
      if times == 0:
         raise ValueError("0 was passed as the number of times the sample is to be played!")
         
      else:
         self.player.dataQueue.queueLoop(self.sample, start, size, times - 1) #Subtract 1 from LoopIterations since the LoopIterations passed to function is really the number of times
                                                                              #the loop should repeat after the first playing
      self.lineOut.start()
          
   def isPlaying(self):
      """
      Returns True if the recorded sample is playing.
      """ 
      return self.player.dataQueue.hasMore()
   
   def stop(self):
      """
      Stops sample from playing any further and restarts the sample from the beginning
      """
      self.player.dataQueue.clear()
      
   def pause(self):
      """
      Pause the sample play (pauseMarker remembers current position for resume)
      """
      self.sample.addMarker(self.pauseMarker) #Adds a marker at the location to start from when sample is resumed
      self.lineOut.stop()
      
   def resume(self):
      """
      Resume Playing the sample from the paused position
      """
      # start playing back from the sample (loop it)
      # (sample frames get retrieved by the reader)   
      self.player.dataQueue.queueLoop( self.sample, self.pauseMarker.position, self.recordedSampleSize )   # playback (loop) the recorded portion of the sample
      
      #self.player.start()
      self.lineOut.start()

   def copy(self):
      """
      Copies the specified sample into a seperate new sample.
      The new sample will change its recordedSampleSize to the specified samples recordedSampleSize 
      """
      copySample = LiveSample(self.SampleSize/1000, self.pitch, self.volume) #SampleSize passed in seconds
      copySample.beginRecordingTimeStamp = self.beginRecordingTimeStamp
      copySample.endRecordingTimeStamp = self.endRecordingTimeStamp
      copySample.recordedSampleSize = self.recordedSampleSize #Copies the Recorded LiveSample's size so that the new LiveSample is the same length
      
      for i in range(self.sample.getNumFrames()):
         copySample.writeDouble(i, self.sample.readDouble(i)) #copies each piece of data from the original sample to the copied sample, frame by frame.

      return copySample
   

   def erase(self):
      """
      Erases all contents of the specified sample.
      """
      if(self.isPlaying() == True): #if sample is playing stop sample before erasing
         self.stop()

      self.writer.dataQueue.clear() #clear the dataQueue so recording of the sample will start at the beginning.
      for i in range(self.sample.getNumFrames()):
         self.sample.writeDouble(i,0.0) #erases all data within sample, where 0.0 is the default empty data value
      
   
   def setPitch(self,pitch):
      """
      Set the sample pitch (through pitch shifting from sample's base pitch)
      """
      self.pitch = pitch #new playback pitch
      print " This is the pitch you specified ", self.pitch
      self.frequency = self.__convertPitchToFrequency__(pitch)
      print " This is frequency ", self.frequency
      semitones = pitch - self.defaultPitch # get the pitch change in semitones
      print " This is semitones ", semitones
      rateChange = self.__getFrequencyChangeBySemitones__( self.getFrameRate(), semitones)  ##Need to be able to set the play.rate with the sample instead of jSyn.FRAMERATE to get this to work
      print " rateChange ", rateChange
      self.__setPlaybackRate__(self.getFrameRate() + rateChange)
      
   
   def getPitch(self):
      """
      Return the sample's current pitch (it may be different from the default pitch).
      """
      return self.pitch
   
   def getDefaultPitch(self):
      """
      Return the sample's default pitch.
      """
      return self.defaultPitch
   
   def setFrequency(self, freq):
      """
      Set the sample pitch frequency.
      """
      self.setPitch(self.__convertFrequencyToPitch__(freq))
      
   def getFrequency(self):
      """
      Return the playback frequency
      """
      return self.frequency
   
   def setPanning(self,panning):
      """
      Set the panning of the sample (panning ranges from 0 - 127)
      """
      self.panning = panning
 
      panValue = mapValue(self.panning,0,127,-1.0,1.0) #map panning from 0,127 to -1.0,1.0
      
      self.panLeft.pan.set(panValue)
      self.panRight.pan.set(panValue)
      
   def getPanning(self):
      """
      Return the current panning of the sample (panning ranges from 0 - 127)
      """
      return self.panning
   
   def setVolume(self,volume):
      """
      Set the volume (amplitude) of the sample (volume ranges from 0-127)
      """
      self.volume = volume
      
      amplitude = mapValue(self.volume,0,127,0.0,1.0) #map volume to amplitude
      self.player.amplitude.set(amplitude)
      
   def getVolume(self):
      """
      Return the current volume (amplitude) of the sample (volume ranges from 0 - 127)
      """
      #print self.volume
      return self.volume
   
######## low-level functions related to FrameRate and PlaybackRate ############################
   
   def getFrameRate(self):
      """
      Return the sample's default recording rate (e.g., 44100.0 Hz).
      """
      #return self.sample.getFrameRate()
      return jSyn.FRAMERATE
      
   def __setPlaybackRate__(self,newRate):
      """
      Set the sample's playback rate (e.g., 44100.0 Hz)
      """
      self.player.rate.set(newRate)
      
   def __getPlaybackRate__(self):
      """
      Return the sample's playback rate (e.g., 44100.0 Hz)
      """
      return self.player.rate.get()
   
   def __msToFrames__(self, milliseconds):
      """
      Converts milliseconds to frames based on the frame rate of the sample
      """
      return jSyn.FRAMERATE*(milliseconds/1000) # max looper sample recording time converted to frames
   
######### Helper Functions for Various Conversions ##################################################################
   
   def __convertPitchToFrequency__(self,pitch):
      """
      Convert MIDI pitch to frequency in Hertz.
      """
      concertA = 440.0
      return concertA * 2.0 **((pitch- 69) / 12.0)
   
   def __convertFrequencyToPitch__(self,freq):
      """
      Converts pitch frequency (in Hertz) to MIDI pitch.
      """
      concertA = 440.0
      return log(freq / concertA, 2.0) * 12.0 + 69
   
   def __getSemitonesBetweenFrequencies__(self,freq1,freq2):
      """
      Calculate number of semitones between two frequencies.
      """
      semitones = (12.0 / log(2)) * log(freq2 / freq1)
      return int(semitones)
   
   def __getFrequencyChangeBySemitones__(self,freq,semitones):
      """
      Calculates frequency change, given change in semitones, from a frequency.
      """
      freqChange = (exp(semitones * log(2) / 12) * freq) - freq
      return freqChange
           
