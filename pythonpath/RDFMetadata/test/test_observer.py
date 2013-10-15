# test_observer - unit tests for observer support class
#
# Copyright 2013 Commons Machinery http://commonsmachinery.se/
#
# Authors: Peter Liljenberg <peter@commonsmachinery.se>
#
# Distributed under an GPLv2 license, please see LICENSE in the top dir.


import unittest

from ..observer import Subject, Event


class AddOnce(object):
    def __init__(self, subj, obs):
        self.subj = subj
        self.obs = obs
        
    def __call__(self, ev):
        if self.obs:
            self.subj.register_observer(self.obs)
            self.obs = None

class RemoveOnce(object):
    def __init__(self, subj, obs):
        self.subj = subj
        self.obs = obs

    def __call__(self, subj):
        if self.obs:
            self.subj.unregister_observer(self.obs)
            self.obs = None


class NotifyOnce(object):
    def __init__(self, subj, ev):
        self.subj = subj
        self.ev = ev
        self.in_callback = False

    def __call__(self, subj):
        assert not self.in_callback

        if self.ev:
            try:
                self.in_callback = True
                self.subj.notify_observers(self.ev)
                self.ev = None
            finally:
                self.in_callback = False



class TestObserver(unittest.TestCase):
    def test_basic(self):

        subj = Subject()
        obs1 = []
        obs2 = []

        subj.register_observer(obs1.append)
        subj.register_observer(obs2.append)

        ev1 = Event()
        subj.notify_observers(ev1)

        self.assertListEqual(obs1, [ev1])
        self.assertListEqual(obs2, [ev1])


        subj.unregister_observer(obs1.append)

        ev2 = Event()
        subj.notify_observers(ev2)

        self.assertListEqual(obs1, [ev1])
        self.assertListEqual(obs2, [ev1, ev2])


    def test_register_during_notification(self):

        subj = Subject()

        target_obs = []
        subj.register_observer(AddOnce(subj, target_obs.append))
        
        #
        # Check that the added observer didn't get the event that triggered the addition
        # 

        subj.notify_observers(Event())
        self.assertListEqual(target_obs, [])

        #
        # But it should get subsequent events
        # 

        ev = Event()
        subj.notify_observers(ev)
        self.assertListEqual(target_obs, [ev])


    def test_register_and_unregister_during_notification(self):

        subj = Subject()

        #
        # If we both register and unregister during the same event, it should be a noop
        # 
        target_obs = []
        subj.register_observer(AddOnce(subj, target_obs.append))
        subj.register_observer(RemoveOnce(subj, target_obs.append))
        
        subj.notify_observers(Event())
        self.assertListEqual(target_obs, [])


    def test_notification_during_notification(self):

        subj = Subject()

        target_obs = []
        subj.register_observer(target_obs.append)

        ev1 = Event()
        ev2 = Event()

        subj.register_observer(NotifyOnce(subj, ev2))
        
        #
        # Check that the notifications are processed sequentially
        # 

        subj.notify_observers(ev1)
        self.assertListEqual(target_obs, [ev1, ev2])
