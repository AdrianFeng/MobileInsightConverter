#!/usr/bin/env python3
# author: Jiuru Shao

import os
from src.log_parser import MobileInsightXmlToListConverter
from functools import reduce
from typing import List

class DlTxDelayAnalyzer(object):
    def __init__(self):
        self.txdelay = 0.0
        self.totalPackets = 0
        self.PDCP_packets = []
        self.RLC_packets = []   # sorted by descending timestamp
        self.MAC_packets = []
        self.PHY_packets = []

    def analyze(self):
        mergedRLCPackets = self.mergeRLC()
        for t in mergedRLCPackets:
            PHY_packet = self.first_PHY_of_RLC(t)
            if not PHY_packet:
                print("Can't find PDCP for RLC at " + t)
            else:
                self.txdelay += t - PHY_packet.time_stamp
                self.totalPackets += 1

    def first_PHY_of_RLC(self, RLC_time_stamp):
        i = 0
        while self.PHY_packets[i].time_stamp > RLC_time_stamp:
            i += 1
        #assert self.PHY_packets[i].time_stamp == RLC_time_stamp
        lastNDI = self.PHY_packets[i].find_value("NDI")
        lastHarqId = self.PHY_packets[i].find_value("HARQ ID")
        for PHY_packet in self.PHY_packets[i+1:]:
            if PHY_packet.find_value("HARQ ID") == lastHarqId and PHY_packet.find_value("NDI") != lastNDI:
                return PHY_packet
        return None

    def mergeTwoRLC(self, processed, nextRLC) -> List:
        # merge 2 RLC packet, input to reduce()

        n = nextRLC.find_value("LI") + 1 - int(nextRLC.find_value("FI")[1])  # number of complete PDCP packets
        print(nextRLC.find_value('sys_fn') + ' ' + nextRLC.find_value('sub_fn') + ' ' + str(n))
        if not processed:
            return [nextRLC.time_stamp] * n
        else:
            return processed + [nextRLC.time_stamp] * n

    def mergeRLC(self) -> List:
        return reduce(self.mergeTwoRLC, self.RLC_packets[::-1], [])


def main():

    RLC_packets, PHY_time_stamps, PHY_packets \
        = MobileInsightXmlToListConverter.convert_dl_xml_to_list("../logs/cr_dl_rlc.txt")

    for t in RLC_packets:
        print(t)

    analyzer = DlTxDelayAnalyzer()
    analyzer.RLC_packets = RLC_packets
    rlc = analyzer.mergeRLC()
    for t in rlc:
        print(t.)

if __name__ == '__main__':
    main()



