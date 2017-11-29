#!/usr/bin/env python3
# author: Jiuru Shao

import os
from src.log_parser import MobileInsightXmlToListConverter

class DlTxDelayAnalyzer(object):
    def __init__(self):
        self.txdelay = 0.0
        self.totatPackets = 0
        self.PDCP_packets = []
        self.RLC_packets = []   # sorted by descending timestamp
        self.MAC_packets = []
        self.PHY_packets = []

    def analyze(self):
        self.firstTime = self.PDCP_packets[-1].time_stamp
        for PDCP_packet in self.PDCP_packets:
            d = self.PDCP_delay(PDCP_packet)
            print('delay: ' + str(d) + ' frame')
            self.txdelay += d
        return self.txdelay / self.totatPackets

    def PDCP_delay(self, PDCP_packet):
        firstRLC = self.first_RLC_of_PDCP(PDCP_packet.time_stamp)
        self.totatPackets = len(self.PDCP_packets)
        if not firstRLC:
            self.totatPackets -= 1
            return 0
        firstPHY = self.first_PHY_of_RLC(firstRLC.time_stamp)
        if not firstPHY:
            self.totatPackets -= 1
            return 0
        
        result = PDCP_packet.time_stamp - firstPHY.time_stamp
        del firstPHY
        return result
        
    def first_RLC_of_PDCP(self, PDCP_time_stamp):
        i = 0
        while self.RLC_packets[i].time_stamp > PDCP_time_stamp:
            i += 1
        for RLC_packet in self.RLC_packets[i:]:
            if RLC_packet.find_value("FI")[0] == "0":
                return RLC_packet
        return None

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


def main():

    RLC_packets, PDCP_packets, PHY_packets = MobileInsightXmlToListConverter.convert_xml_to_list("../logs/cr_dl_unit.txt")

    analyzer = DlTxDelayAnalyzer()

    print(len(PDCP_packets))
    analyzer.PDCP_packets = PDCP_packets
    analyzer.RLC_packets = RLC_packets  # sorted by descending timestamp
    analyzer.PHY_packets = PHY_packets
    analyzer.analyze()


# for packet in RLC_packets:
#     print(packet)
#
# for packet in PHY_packets:
#     print(packet)
#
# for packet in PDCP_packets:
#     print(packet)

# result_list = []
# for child in root:
#     new_dict = OrderedDict()
#     parse_xml(child, new_dict)
#     result_list.append(new_dict)
#
#
# for element in result_list:
#     print_dict(element, 0)


if __name__ == '__main__':
    main()



