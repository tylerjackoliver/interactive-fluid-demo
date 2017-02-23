#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 20 13:45:55 2017

@author: feeg6003
"""

class CycleOption:    
    def __init__(self, name, key, options, current=0):
        self._name = name
        self._key = key
        self._current = current
        self._options = options
        
    def poll_for_key(self, key):
        if key == ord(self._key):
            self._current = (self._current + 1) % len(self._options)
            return True
        else:
            return False
        
    @property
    def current(self):
        return self._current
        
    def __str__(self):
        return "{}({})={}".format(self._name, self._key, 
                self._options[self._current])
    
    
class RangeOption:
    def __init__(self, name, keys, range, step, current=0):
        assert len(keys) == 2
        assert len(range) == 2
        self._name = name
        self._keys = keys
        self._current = max(min(current, range[1]), range[0])
        self._range = range
        self._step = step
                
    def poll_for_key(self, key):
        if key == ord(self._keys[0]):            
            self._current = max(self._current - self._step, self._range[0])
            return True        
        if key == ord(self._keys[1]):
            self._current = min(self._current + self._step, self._range[1])
            return True
        else:
            return False
        
    @property
    def current(self):
        return self._current
    
    def __str__(self):
        return "{}({}/{})={:.2f}".format(self._name, self._keys[0], 
                self._keys[1], self._current)
    
a = CycleOption('Mode', 'm', ['Smoke', 'Velocity'])

print(a)

b = RangeOption('Speed', ['-','='], [0.05, 3], 0.05, 1)

print(b)