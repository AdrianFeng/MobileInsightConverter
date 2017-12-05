#!/usr/bin/env python3
# author: Jiuru Shao

import os
from src.log_parser import MobileInsightXmlToListConverter
from functools import reduce
from typing import List


def mergeTwoRLCEnd(processed, nextRLC) -> List:
    # merge 2 RLC packet, input to reduce()
    n = nextRLC.find_value("LI") + 1 - int(nextRLC.find_value("FI")[1])  # number of complete PDCP packets
    # print(nextRLC.find_value('sys_fn') + ' ' + nextRLC.find_value('sub_fn') + ' ' + str(n))
    if not processed:
        return [nextRLC.time_stamp] * n
    else:
        return processed + [nextRLC.time_stamp] * n


def mergeTwoRLCStart(processed, nextRLC) -> List:
    # merge 2 RLC packet, input to reduce()
    n = nextRLC.find_value("LI") + 1 - int(nextRLC.find_value("FI")[0])  # number of complete PDCP packets
    # print(nextRLC.find_value('sys_fn') + ' ' + nextRLC.find_value('sub_fn') + ' ' + str(n))
    if not processed:
        return [nextRLC.time_stamp] * n
    else:
        return processed + [nextRLC.time_stamp] * n



def checkRLC(RLC_packets):
    for i in range(0, len(RLC_packets)-1):
        assert RLC_packets[i].find_value('FI')[1] == RLC_packets[i+1].find_value('FI')[0]


def mergeRLC(RLC_packets):
    checkRLC(RLC_packets)
    ends = reduce(mergeTwoRLCEnd, RLC_packets, [])
    starts = reduce(mergeTwoRLCStart, RLC_packets, [])
    assert(len(ends) == len(starts))
    return zip(starts, ends)




class DlTxDelayAnalyzer(object):
    def __init__(self):
        self.txdelay = 0.0
        self.totalPackets = 0
        self.PHY_packets = []
        self.mergedRLCPackets = []

    def analyze(self):
        for t_start, t_end in self.mergedRLCPackets:
            PHY_packet = self.first_PHY_of_RLC(t_start)
            if not PHY_packet:
                print("Can't find PDCP for RLC at (%d, %d)" % (t_start, t_end))
            else:
                self.txdelay += t_end - PHY_packet.time_stamp
                self.totalPackets += 1
                print(t_end, PHY_packet.time_stamp, t_end - PHY_packet.time_stamp)
        print(self.totalPackets, self.txdelay)

    def first_PHY_of_RLC(self, RLC_time_stamp):
        i = 0
        while self.PHY_packets[i].time_stamp > RLC_time_stamp:
            i += 1

        lastNDI = self.PHY_packets[i].find_value("NDI")
        lastHarqId = self.PHY_packets[i].find_value("HARQ ID")
        lastPHY = self.PHY_packets[i]
        for PHY_packet in self.PHY_packets[i+1:]:
            if PHY_packet.find_value("HARQ ID") == lastHarqId:
                if PHY_packet.find_value("NDI") != lastNDI:
                    return lastPHY
                else:
                    lastPHY = PHY_packet
            else:
                pass

        return None




def main():
    RLC_packets, PHY_packets \
        = MobileInsightXmlToListConverter.convert_dl_xml_to_list("../logs/cr_dl_full.txt")
    #
    # print(len(PHY_packets))
    # for p in PHY_packets:
    #     print(p.time_stamp)

    #for t in RLC_packets:
    #    print(t.time_stamp, t.find_value('FI'))
    checkRLC(RLC_packets)
    rlc = mergeRLC(RLC_packets)

    analyzer = DlTxDelayAnalyzer()
    analyzer.PHY_packets = PHY_packets
    analyzer.mergedRLCPackets = rlc
    analyzer.analyze()

if __name__ == '__main__':
    main()



