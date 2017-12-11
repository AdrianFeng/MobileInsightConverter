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
        print(RLC_packets[i].find_value('real_time'), RLC_packets[i+1].find_value('real_time'),
             RLC_packets[i].find_value('SN'), RLC_packets[i+1].find_value('SN'),)
        assert RLC_packets[i].find_value('FI')[1] == RLC_packets[i+1].find_value('FI')[0]


def mergeRLC(RLC_packets):
    checkRLC(RLC_packets)
    ends = reduce(mergeTwoRLCEnd, RLC_packets, [])
    starts = reduce(mergeTwoRLCStart, RLC_packets, [])
    assert(len(ends) == len(starts))
    return zip(starts, ends)


def mergeRLC2(RLC_packets):

    mergedRLC = []
    start, end, startIdx = None, None, None
    for idx, r in enumerate(RLC_packets):
        if r.find_value('FI') == '00':
            mergedRLC += [(r.time_stamp, r.time_stamp, idx)] * (r.find_value('LI') + 1)
            start, end, startIdx = None, None, None
        elif r.find_value('FI') == '01': # we have a start ts, and we should pick the smallest ts of this PDCP
            # add possible 'small' PDCP
            mergedRLC += r.find_value('LI') * [(r.time_stamp, r.time_stamp, idx)]
            start, end, startIdx = r.time_stamp, r.time_stamp, idx
        elif r.find_value('FI') == '11':
            if r.find_value('LI') == 0: # no packet should be added
                startIdx = idx if start > r.time_stamp else startIdx
                start = min(start, r.time_stamp)
                end = max(end, r.time_stamp)
            else:   # we come to the end of a PDCP + (LI-1)*small PDCP + start of next PDCP
                startIdx = idx if start > r.time_stamp else startIdx
                start = min(start, r.time_stamp)
                end = max(end, r.time_stamp)
                mergedRLC += [(start, end, startIdx)]
                # add possible 'small' PDCP
                mergedRLC += [(r.time_stamp, r.time_stamp, idx)] * (r.find_value('LI') - 1)
                # the beginning of next PDCP
                start, end, startIdx = r.time_stamp, r.time_stamp, idx
        else: # 10
            if r.find_value('LI') == 0:
                startIdx = idx if start > r.time_stamp else startIdx
                start = min(start, r.time_stamp)
                end = max(end, r.time_stamp)
                mergedRLC += [(start, end, startIdx)]
                start, end, startIdx = None, None, None
            else:
                startIdx = idx if start > r.time_stamp else startIdx
                start = min(start, r.time_stamp)
                end = max(end, r.time_stamp)
                mergedRLC += [(start, end, startIdx)]
                mergedRLC += [(r.time_stamp, r.time_stamp, idx)] * r.find_value('LI')
                start, end, startIdx = None, None, None
    return mergedRLC


class DlTxDelayAnalyzer(object):
    def __init__(self):
        self.txdelay = 0.0
        self.totalPackets = 0
        self.PHY_packets = []
        self.mergedRLCPackets = []
        self.RLC2PHY = {}

    def analyze(self):

        CDF_count_dict = {}
        for t_start, t_end, idx in self.mergedRLCPackets:
            PHY_ts, RLC_real_time, PHY_real_time = self.RLC2PHY.get(idx,( None, None, None))
            if not PHY_ts:
                print("Can't find PHY for RLC at (%d, %d)" % (t_start, t_end))
            else:
                self.txdelay += t_end - PHY_ts
                self.totalPackets += 1
                print(PHY_ts, ",", t_start, "," ,t_end, ",", t_end - PHY_ts, ", RLC_real_time", RLC_real_time,  ", PHY_real_time", PHY_real_time)
        print(self.totalPackets, self.txdelay)

        #
        # for t_start, t_end, idx in self.mergedRLCPackets:
        #      PHY_ts, RLC_real_time, PHY_real_time= self.RLC2PHY.get(idx, None)
        #     if PHY_ts:





    def first_PHY_of_RLC(self, RLC_time_stamp):

        i = 0
        while self.PHY_packets[i].time_stamp > RLC_time_stamp:
            i += 1


        if self.PHY_packets[i].find_value('Did Recombining') == 'No':
            return self.PHY_packets.pop(i)

        # assert self.PHY_packets[i].time_stamp == RLC_time_stamp
        lastNDI = self.PHY_packets[i].find_value("NDI")
        lastHarqId = self.PHY_packets[i].find_value("HARQ ID")
        lastTBIndex = self.PHY_packets[i].find_value("TB Index")

        copyPHY = self.PHY_packets[:]
        for idx in range(i+1, len(copyPHY)):
            PHY_packet = copyPHY[idx]
            if PHY_packet.find_value("HARQ ID") == lastHarqId and PHY_packet.find_value('TB Index') == lastTBIndex:
                if PHY_packet.find_value("CRC Result") == 'Pass':
                    return self.PHY_packets.pop(i)
                else:
                    i = idx
            else:
                pass

        return None




def main():
    RLC_packets, PHY_packets \
        = MobileInsightXmlToListConverter.convert_dl_xml_to_list("../logs/cr_dl_full.txt")


    RLC_index_PHY_time_dict = {}

    analyzer = DlTxDelayAnalyzer()
    analyzer.PHY_packets = PHY_packets
    for index, RLC_packet in enumerate(RLC_packets):

        # if RLC_packet.time_stamp == 202789:
        #     print(" asdasdsa ", index , len(RLC_packets))
        #
        # print(RLC_packet.find_value("real_time"), RLC_packet.find_value("SN"), RLC_packet.time_stamp)

        PHY_packet = analyzer.first_PHY_of_RLC(RLC_packet.time_stamp)
        if PHY_packet:
            RLC_index_PHY_time_dict[index] = (PHY_packet.time_stamp, RLC_packet.find_value("real_time"), PHY_packet.find_value("real_time"))
        else:
            # raise Exception("PHY can not be found")
            print("Phy cannot be found")


    # for p in PHY_packets:
    #     print(p.time_stamp)
    #
    # for p in PHY_packets:
    #     print(p.time_stamp)
    #

    # for t in RLC_packets:
    #     print(t.time_stamp, t.find_value('SN'))

    checkRLC(RLC_packets)
    rlc = mergeRLC2(RLC_packets)
    #
    for i, r in enumerate(rlc):
        if r[0] > 11050:
            break
        else:
            print(i, r)

    analyzer = DlTxDelayAnalyzer()
    analyzer.RLC2PHY = RLC_index_PHY_time_dict
    analyzer.PHY_packets = PHY_packets
    analyzer.mergedRLCPackets = rlc

    analyzer.analyze()

if __name__ == '__main__':
    main()



