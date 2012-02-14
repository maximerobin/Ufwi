# -*- coding: utf-8 -*-
"""
Copyright (C) 2010-2011 EdenWall Technologies
Written by François Toussenel <ftoussenel AT edenwall.com>

This file is part of NuFirewall. 
 
 NuFirewall is free software: you can redistribute it and/or modify 
 it under the terms of the GNU General Public License as published by 
 the Free Software Foundation, version 3 of the License. 
 
 NuFirewall is distributed in the hope that it will be useful, 
 but WITHOUT ANY WARRANTY; without even the implied warranty of 
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
 GNU General Public License for more details. 
 
 You should have received a copy of the GNU General Public License 
 along with NuFirewall.  If not, see <http://www.gnu.org/licenses/>

"""

class Thresholds:
    sane = 75
    alert1 = 80
    alert2 = 85
    last_alert = 90
    insane = 95

    # Ordered from lowest to highest threshold
    levels = [sane, alert1, alert2, last_alert, insane]

    @staticmethod
    def in_threshold(criticity):
        if criticity >= Thresholds.insane:
            return Thresholds.insane
        if criticity >= Thresholds.last_alert:
            return Thresholds.last_alert
        if criticity >= Thresholds.alert2:
            return Thresholds.alert2
        if criticity >= Thresholds.alert1:
            return Thresholds.alert1
        if criticity >= Thresholds.sane:
            return Thresholds.sane
        return 0

    @staticmethod
    def compare_thresholds(criticity1, criticity2):
        if Thresholds.in_threshold(criticity1) == \
                Thresholds.in_threshold(criticity2):
            return 0
        if criticity1 < criticity2:
            return 1
        return -1

    @staticmethod
    def threshold_equal(criticity1, criticity2):
        return Thresholds.compare_thresholds(criticity1, criticity2) == 0

    @staticmethod
    def threshold_higher(criticity1, criticity2):
        return Thresholds.compare_thresholds(criticity1, criticity2) == 1

    @staticmethod
    def threshold_lower(criticity1, criticity2):
        return Thresholds.compare_thresholds(criticity1, criticity2) == -1

    @staticmethod
    def level(criticity):
        threshold = Thresholds.in_threshold(criticity)
        try:
            return Thresholds.levels.index(threshold)
        except ValueError:
            return 0
