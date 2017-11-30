#!/usr/bin/env python3
# author: Jiuru Shao

import os
from src.log_parser import MobileInsightXmlToListConverter
from functools import reduce
from typing import List
import functools

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

    def mergeTwoRLC(self, processed, nextRLC, lastFI) -> List:
        # merge 2 RLC packet, input to reduce()
        n = nextRLC.find_value("LI") + 1 - int(nextRLC.find_value("FI")[1])  # number of complete PDCP packets
        if not processed:
            lastFI = nextRLC.find_value("FI")[1]
            return [nextRLC.time_stamp] * n
        else:
            assert lastFI == nextRLC.find_value("FI")[0]
            lastFI = nextRLC.find_value("FI")[1]
            return processed + [nextRLC.time_stamp] * n

    def mergeRLC(self) -> List:
        return reduce(functools.partial(self.mergeTwoRLC, lastFI="0"), self.RLC_packets, [])


def main():

    RLC_packets, _, PHY_packets \
        = MobileInsightXmlToListConverter.convert_dl_xml_to_list("../logs/cr_dl_rlc.txt")

    for r in RLC_packets:
        print(r)

    # how to get the number of li in a single RLC packets
    # number_of_li = packet.information_dict.get("NUMBER OF LI", None)
    # return value if it has li otherwise None

    analyzer = DlTxDelayAnalyzer()
    analyzer.RLC_packets = RLC_packets
    rlc = analyzer.mergeRLC()
    for t in rlc:
        print(t)

    # print(len(PDCP_packets))
    # analyzer.PDCP_packets = PDCP_packets
    # analyzer.RLC_packets = RLC_packets  # sorted by descending timestamp
    # analyzer.PHY_packets = PHY_packets
    # analyzer.analyze()

if __name__ == '__main__':
    main()



