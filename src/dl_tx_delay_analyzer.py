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
        #print(RLC_packets[i].find_value('real_time'), RLC_packets[i+1].find_value('real_time'),
        #      RLC_packets[i].find_value('SN'), RLC_packets[i+1].find_value('SN'),)
        assert RLC_packets[i].find_value('FI')[1] == RLC_packets[i+1].find_value('FI')[0]


def mergeRLC(RLC_packets):
    checkRLC(RLC_packets)
    ends = reduce(mergeTwoRLCEnd, RLC_packets, [])
    starts = reduce(mergeTwoRLCStart, RLC_packets, [])
    assert(len(ends) == len(starts))
    return zip(starts, ends)


def mergeRLC2(RLC_packets):
    checkRLC(RLC_packets)
    mergedRLC = []
    start, end = None, None
    for r in RLC_packets:
        if r.find_value('FI') == '00':
            mergedRLC += [(r.time_stamp, r.time_stamp)] * (r.find_value('LI') + 1)
            start, end = None, None
        elif r.find_value('FI') == '01': # we have a start ts, and we should pick the smallest ts of this PDCP
            # add possible 'small' PDCP
            mergedRLC += r.find_value('LI') * [(r.time_stamp, r.time_stamp)]
            start, end = r.time_stamp, r.time_stamp
        elif r.find_value('FI') == '11':
            if r.find_value('LI') == 0: # no packet should be added
                start = min(start, r.time_stamp)
                end = max(end, r.time_stamp)
            else:   # we come to the end of a PDCP + (LI-1)*small PDCP + start of next PDCP
                start = min(start, r.time_stamp)
                end = max(end, r.time_stamp)
                mergedRLC += [(start, end)]
                # add possible 'small' PDCP
                mergedRLC += [(r.time_stamp, r.time_stamp)] * (r.find_value('LI') - 1)
                # the beginning of next PDCP
                start, end = r.time_stamp, r.time_stamp
        else: # 10
            if r.find_value('LI') == 0:
                start = min(start, r.time_stamp)
                end = max(end, r.time_stamp)
                mergedRLC += [(start, end)]
                start, end = None, None
            else:
                start = min(start, r.time_stamp)
                end = max(end, r.time_stamp)
                mergedRLC += [(start, end)]
                mergedRLC += [(r.time_stamp, r.time_stamp)] * r.find_value('LI')
                start, end = None, None
    return mergedRLC


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
                print("Can't find PHY for RLC at (%d, %d)" % (t_start, t_end))
            else:
                self.txdelay += t_end - PHY_packet.time_stamp
                self.totalPackets += 1
                print(PHY_packet.find_value('real_time'), PHY_packet.time_stamp, t_end, t_end - PHY_packet.time_stamp)
        print(self.totalPackets, self.txdelay)

    def first_PHY_of_RLC(self, RLC_time_stamp):
        i = 0
        while self.PHY_packets[i].time_stamp > RLC_time_stamp:
            i += 1


        # assert self.PHY_packets[i].time_stamp == RLC_time_stamp


        lastNDI = self.PHY_packets[i].find_value("NDI")
        lastHarqId = self.PHY_packets[i].find_value("HARQ ID")
        j = i
        for idx in range(j+1, len(self.PHY_packets)):
            PHY_packet = self.PHY_packets[idx]
            if PHY_packet.find_value("HARQ ID") == lastHarqId:
                if PHY_packet.find_value("NDI") != lastNDI:
                    return self.PHY_packets.pop(i)
                else:
                    i = idx
            else:
                pass

        return None




def main():
    RLC_packets, PHY_packets \
        = MobileInsightXmlToListConverter.convert_dl_xml_to_list("../logs/cr_dl_full.txt")

    print(PHY_packets)

    RLC_index_PHY_time_dict = {}

    analyzer = DlTxDelayAnalyzer()
    analyzer.PHY_packets = PHY_packets
    for index, RLC_packet in enumerate(RLC_packets):
        PHY_packet = analyzer.first_PHY_of_RLC(RLC_packet.time_stamp)
        if PHY_packet:
            RLC_index_PHY_time_dict[index] = PHY_packet.time_stamp
        else:
            # raise Exception("PHY can not be found")
            print("Phy cannot be found ")
    print(RLC_index_PHY_time_dict)

    # for p in PHY_packets:
    #     print(p.time_stamp)
    #
    print(len(PHY_packets))
    # for p in PHY_packets:
    #     print(p.time_stamp)
    #

    # for t in RLC_packets:
    #     print(t.time_stamp, t.find_value('SN'))

    # checkRLC(RLC_packets)
    # rlc = mergeRLC2(RLC_packets)
    #
    # for r in rlc:
    #     print(r)

    analyzer = DlTxDelayAnalyzer()
    analyzer.PHY_packets = PHY_packets
    analyzer.mergedRLCPackets = rlc
    analyzer.analyze()

if __name__ == '__main__':
    main()



