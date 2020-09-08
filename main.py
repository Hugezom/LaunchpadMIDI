import numpy as np
import launchpad_py
import mido
from pygame import midi
from pygame import time as ptime
import os
import time
import threading
from copy import deepcopy

class LpMIDI:
    def __init__(self,instrument_id=0,mid_path='mids/'):
        assert self.init_launchpad()
        
        self.config_volume=True
        self.config_not_stop=False
        self.config_not_mute=False
        self.config_solo=True
        self.config_record=False
        self.config_session=True
        self.config_play_continuously=False
        
        self.can_stop=True
        self.should_press_key=None
        self.thread_polling=None
        self.thread_tempo=None
        self.thread_note=None
        
        self.instrument_id_origin=instrument_id
        self.speed=1
        self.mid_num=0
        self.midlist=[i for i in os.listdir('mids/') if i.endswith('.mid')]
        
        self.button2config={(8,1):'self.config_volume',
                            (8,5):'self.config_not_stop',
                            (8,6):'self.config_not_mute',
                            (8,7):'self.config_solo',
                            (8,8):'self.config_record',
                            (4,0):'self.config_session',
                            (7,0):'self.config_play_continuously'}
        
        self.button2func={(0,0):'last_instrument',
                          (1,0):'next_instrument',
                          (2,0):'last_mid',
                          (3,0):'next_mid',
                          (8,2):'reset_speed',
                          (8,3):'speed_up',
                          (8,4):'speed_down'}
        
        self.player=midi.Output(0)
        self.player.set_instrument(instrument_id)
        self.instrument_id=instrument_id
        
        basicLED={}
        for i in range(8):
            for j in [2,4,6,8]:
                basicLED[(i,j)]=(0,20,0)
        for j in [1,3,5,7]:
            for i in [1,2,4,5,6]:
                basicLED[(i,j)]=(20,20,0)
            for i in [0,3,7]:
                basicLED[(i,j)]=(0,0,0)
        
        for i,j in self.button2func.keys():
            basicLED[(i,j)]=(10,20,0)
        
        self.basicLED=basicLED
        
        c4=np.array([48,50,52,53,55,57,59,60])
        c4_=np.array([47,49,51,52,54,56,58,59])
        c5=c4+12
        c5_=c4_+12
        c6=c5+12
        c6_=c5_+12
        
        c3=c4-12
        c3_=c4_-12
        
        poss=[]
        for j in [2,4,6,8,1,3,5,7]:
            for i in range(8):
                poss.append((i,j))
        
        note2xy={}
        for i,j in zip(np.r_[c6,c5,c4,c3,c6_,c5_,c4_,c3_],poss):
            note2xy[i]=note2xy.get(i,[])+[j]
        
        xy2note={}
        for note in note2xy.keys():
            for x,y in note2xy[note]:
                xy2note[(x,y)]=note
        
        self.note2xy=note2xy
        self.xy2note=xy2note
        
        self.LED_init()
        self.polling()
        
    def map_note():
        1
    
    def note_on(self,note,velocity):
        if self.config_record:
            LpMIDI.map_note(note)
        if self.config_volume:
            self.player.note_on(note,velocity)
        
    def note_off(self,note,velocity):
        if self.config_record:
            LpMIDI.map_note(note)
        if self.config_volume:
            self.player.note_off(note,velocity)
    
    def get_buttons(self):
        lp=self.lp
        
        self.loop_get=True
        lp.ButtonFlush()
        while self.loop_get:
            state=lp.ButtonStateXY()
            if len(state)==0:
                continue
            x,y,velocity=state
            if (x,y) in self.xy2note.keys():
                note=self.xy2note[(x,y)]
                if velocity:
                    if self.config_volume:
                        self.player.note_on(note,velocity)
                    r,g,b=[i*3 for i in self.currentLED[(x,y)]]
                    if r==g==b==0:
                        r,g,b=0,60,0
                    lp.LedCtrlXY(x,y,r,g,b)
                else:
                    if self.config_volume:
                        self.player.note_off(note,velocity)
                    r,g,b=self.currentLED[(x,y)]
                    lp.LedCtrlXY(x,y,r,g,b)
                    if self.should_press_key:
                        if (x,y) in self.should_press_key:
                            self.should_press_key=None
            
            elif (x,y) in self.button2func.keys():
                if velocity:
                    if (x,y) in self.currentLED.keys():
                        r,g,b=[i*3 for i in self.currentLED[(x,y)]]
                        lp.LedCtrlXY(x,y,r,g,b)
                        
                    if self.button2func[(x,y)]=='next_instrument':
                        self.instrument_id+=1
                        self.player.set_instrument(instrument_id=self.instrument_id)
                        
                    elif self.button2func[(x,y)]=='last_instrument':
                        self.instrument_id=self.instrument_id-1 if self.instrument_id>0 else 0
                        self.player.set_instrument(instrument_id=self.instrument_id)
                        
                    elif self.button2func[(x,y)]=='last_mid':
                        if self.midlist!=[]:
                            self.mid_num=self.mid_num-1 if -self.mid_num<len(self.midlist) else 0
                        print('Select: %s'%self.midlist[self.mid_num])
                        
                    elif self.button2func[(x,y)]=='next_mid':
                        if self.midlist!=[]:
                            self.mid_num=self.mid_num+1 if self.mid_num<len(self.midlist) else 0
                        print('Select: %s'%self.midlist[self.mid_num])
                        
                else:
                        r,g,b=self.currentLED[(x,y)]
                        lp.LedCtrlXY(x,y,r,g,b)
                        
            elif (x,y) in self.button2config.keys():
                if velocity:
                    str_config=self.button2config[(x,y)]
                    exec('%s = not %s'%(str_config,str_config))
                    if eval(str_config):
                        lp.LedCtrlXY(x,y,0,10,20)
                    else:
                        lp.LedCtrlXY(x,y,20,0,0)
                    
                    if str_config=='self.config_session':
                        if self.config_session:
                            self.LED_init()
                        else:
                            while not self.can_stop:
                                pass
                            self.speed=1
                            self.player.close()
                            self.player=midi.Output(0)
                            self.player.set_instrument(self.instrument_id)
                            self.lp.Reset()
                    
                    elif str_config=='self.config_solo' and self.config_solo:
                        self.config_not_mute=False
                        lp.LedCtrlXY(8,6,20,0,0)
                    
                    elif str_config=='self.config_not_mute' and self.config_not_mute:
                        self.config_solo=False
                        lp.LedCtrlXY(8,7,20,0,0)
                        
                    elif str_config=='self.config_not_stop':
                        if self.config_not_stop:
                            if self.config_play_continuously:
                                act=threading.Thread(target=self.play_continuously)
                                act.start()
                            else:
                                self.play_mid(self.mid_num)
                            
                        else:
                            while not self.can_stop:
                                pass
                            self.player.close()
                            self.player=midi.Output(0)
                            self.player.set_instrument(self.instrument_id)
                            self.LED_init()
                            
    def play_continuously(self):
        while self.config_play_continuously:
            while self.config_play_continuously and self.thread_note!=None:
                1
            time.sleep(1)
            self.play_mid(self.mid_num)
            self.config_not_stop=True
            time.sleep(1)
        self.config_not_stop=False
    
    def polling(self):
        self.thread_polling=threading.Thread(target=self.get_buttons)
        self.thread_polling.start()
        
    def init_launchpad(self):
        self.lp=launchpad_py.LaunchpadMk2()
        rr=self.lp.Open( 0, "mk2" )
        if rr:
            print( " - Launchpad Mk2: OK" )
        else:
            print( " - Launchpad Mk2: ERROR" )
        return rr
    
    def LED_init(self):
        for x,y in self.basicLED.keys():
            r,g,b=self.basicLED[(x,y)]
            self.lp.LedCtrlXY(x,y,r,g,b)
        
        for x,y in self.button2config.keys():
            if eval(self.button2config[(x,y)]):
                self.lp.LedCtrlXY(x,y,0,10,20)
            else:
                self.lp.LedCtrlXY(x,y,20,0,0)
        self.currentLED=deepcopy(self.basicLED)
    
    def light_up(self,note,times,velocity):
        self.note_on(note,velocity)
        if note in self.note2xy.keys():
            for (x,y) in self.note2xy[note]:
                if velocity==0:
                    if self.basicLED[(x,y)]==(0,0,0):
                        self.lp.LedCtrlXY(x,y,20,0,20)
                        self.currentLED[(x,y)]=(20,0,20)
                    else:
                        self.lp.LedCtrlXY(x,y,20,0,0)
                        self.currentLED[(x,y)]=(20,0,0)
                else:
                    if self.basicLED[(x,y)]==(0,0,0):
                        self.lp.LedCtrlXY(x,y,0,20,20)
                        self.currentLED[(x,y)]=(0,20,20)
                    else:
                        self.lp.LedCtrlXY(x,y,0,0,20)
                        self.currentLED[(x,y)]=(0,0,20)

    def light_off(self,note,times,velocity):
        self.note_off(note,velocity)
        if note in self.note2xy.keys():
            for x,y in self.note2xy[note]:
                r,g,b=self.basicLED[x,y]
                self.lp.LedCtrlXY(x,y,r,g,b)
                self.currentLED[(x,y)]=(r,g,b)
                
    def play_tempo(self,tempos,clocks_per_click):
        for msg in tempos:
            if not self.config_session or not self.config_not_stop:
                break
            if msg.type=='set_tempo':
                self.tempo=msg.tempo
                time.sleep(mido.tick2second(msg.time,4*clocks_per_click/self.speed,self.tempo))
        self.thread_tempo=None

    def play_note(self,notes,clocks_per_click):
        msg_sess={}
        for msg in notes:
            if not self.config_session or not self.config_not_stop:
                break
            self.can_stop=False
            if msg.type=='note_on':
                msg_note_times=msg_sess.get(msg.note,0)
                msg_sess[msg.note]=msg_sess.get(msg.note,0)+1
                time.sleep(mido.tick2second(msg.time,4*clocks_per_click/self.speed,self.tempo))
                self.light_up(msg.note,msg_note_times,msg.velocity)
            elif msg.type=='note_off':
                msg_sess[msg.note]-=1
                time.sleep(mido.tick2second(msg.time,4*clocks_per_click/self.speed,self.tempo))
                self.light_off(msg.note,msg_sess[msg.note],msg.velocity)
            self.can_stop=True
        self.thread_note=None
        self.config_not_stop=False
        self.LED_init()
        print('Next: %s'%self.midlist[self.mid_num])
        
    def play_note_by_step(self,notes):
        msg_sess={}
        notes=[msg for msg in notes if msg.type in ['note_on']]
        for i in range(len(notes)):
            if not self.config_session or not self.config_not_stop:
                break
            if i<len(notes)-1:
                msg_n=notes[i+1]
                self.light_up(msg_n.note,0,0)
            msg=notes[i]
            #self.can_stop=False
            msg_note_times=msg_sess.get(msg.note,0)
            msg_sess[msg.note]=msg_sess.get(msg.note,0)+1
            self.light_up(msg.note,msg_note_times,msg.velocity)
            if msg.note in self.note2xy.keys():
                self.should_press_key=self.note2xy[msg.note]
                while self.should_press_key and self.config_session:
                    if not self.config_session:
                        break
                self.light_off(msg.note,msg_note_times,msg.velocity)
            #self.can_stop=True
        self.thread_note=None
        self.config_not_stop=False
        self.LED_init()
                
    def play_midi(self,path):
        assert self.speed
        self.LED_init()
        mid = mido.MidiFile(path)
        if self.thread_tempo or self.thread_note:
            self.config_session=False
            self.config_session=True
                
        if self.config_solo:
            self.config_not_mute=False
            self.lp.LedCtrlXY(8,6,20,0,0)
            
            self.thread_note=threading.Thread(target=self.play_note_by_step,args=(mid.tracks[2],))
            self.thread_note.start()
            
        else:    
            clocks_per_click=mid.tracks[0][0].clocks_per_click
            self.thread_tempo=threading.Thread(target=self.play_tempo,args=(mid.tracks[1],clocks_per_click))
            self.thread_note=threading.Thread(target=self.play_note,args=(mid.tracks[2],clocks_per_click))
            self.thread_tempo.start()
            self.thread_note.start()
            
    def play_mid(self,mid_num=None):
        if self.midlist==[]:
            return
        mid_num=mid_num if mid_num!=None else 0
        mid_name=self.midlist[mid_num]
        mid_path='mids/%s'%mid_name
        print('Playing: %d.%s'%(mid_num,mid_name))
        self.play_midi(mid_path)
        self.mid_num=self.mid_num+1 if self.mid_num<len(self.midlist)-1 else 0
        print('Next: %s'%self.midlist[self.mid_num])
        
    def show_midlist(self):
        for i in range(len(self.midlist)):
            print(i,self.midlist[i])
