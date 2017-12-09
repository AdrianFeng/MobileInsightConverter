#!/usr/bin/env python3
# Author: Zhonglin Zhang, Zhengxu Xia

import os
from log_parser import MobileInsightXmlToListConverter
import functools
from typing import List
from dl_tx_delay_analyzer import mergeRLC


class UlTxLatencyAnalyzer(object):
    def __init__(self):
        self.total_delay = 0.0
        self.total_packets = 0
        
        self.PDCP_packets = []
        self.RLC_packets = []
        self.RLC_packets_dict = {}


        self.MAC_packets = {}
        self.PDCCH_packets = {}
        self.MAC_times = []
        self.PDCCH_times = []
        self.PUSCH_times = []
        self.mac_buffer = []

    def analyze(self):
        mergedRLCPackets = mergeRLC(self.RLC_packets) # last arrived rlc timestamps
        
        end_timestamps = []
        for ts_pair in mergedRLCPackets:
            end_timestamps.append(self.find_last_pusch(ts_pair[1]))
        
        start_timestamps = []
        self.generate_buffer(self.MAC_packets)
        print(self.mac_buffer)
        for pkt in self.PDCP_packets:
            
            pdcp_bytes = int(pkt.find_value('PDU Size'))

            start_timestamps.append(self.load_2_buffer(pdcp_bytes)) # pdcp layer

        print("Number of start timestamps: ", len(start_timestamps))
        print(start_timestamps)
        print("Number of end timestamps: ", len(end_timestamps))
        print(end_timestamps)
        
        delays = []

        for start, end in zip(start_timestamps, end_timestamps):
            if (end == None or start == None):
                continue
            delays.append(end - start)
            print("Start: " + str(start) + " End: " + str(end) + " Delay: " + str(end - start))

        avg_delay = sum(delays) / len(delays)

        print("Average delay time: " + str(avg_delay) + " ms")

    

    def compute_rlc_bytes(self, ts):
        rlc_bytes = 0
        for subpacket in self.RLC_packets_dict[ts]:
            if subpacket.find_value('RLC DATA LI'):
                LI_num = len(subpacket.find_value('RLC DATA LI')) + 1
                header_len = self.cal_header_length(LI_num)
            else:
                header_len = self.cal_header_length(1)
            rlc_bytes += (int(subpacket.find_value('pdu_bytes')) - header_len)
        return rlc_bytes



    def generate_buffer(self, MAC_packets):
        last_buffer_bytes = 0
        rlc_bytes = 0
        LI_num = 0
        header_len = 0
        for ts in self.MAC_times:
            MAC_packet = self.MAC_packets[ts]
            
            ##if mac buffer become larger, 
            
            if (int(MAC_packet.find_value('New bytes')) > last_buffer_bytes): # new pdcp pkts coming in for sure
                if (ts in self.RLC_packets_dict):
                    rlc_bytes = self.compute_rlc_bytes(ts) 
                    self.mac_buffer.append([ts, int(MAC_packet.find_value('New bytes')) - last_buffer_bytes + rlc_bytes])
                else:
                    self.mac_buffer.append([ts, int(MAC_packet.find_value('New bytes')) - last_buffer_bytes])

                    
            ##if mac buffer become smaller,
            ##means there are rlc packets sent
            elif (int(MAC_packet.find_value('New bytes')) < last_buffer_bytes):

                if ts == 68065 or ts == 77353:
                    continue
                rlc_pkt = self.RLC_packets_dict.get(ts, [])
                if not rlc_pkt:
                    print("miss at " + str(ts))
                
                if not rlc_pkt:
                    print("miss at " + str(ts))
                    last_buffer_bytes = int(MAC_packet.find_value('New bytes'))
                    continue
                
                rlc_bytes = self.compute_rlc_bytes(ts)
                if ts == 66503:    #time_stamp: 506.3
                    rlc_bytes = 1990
                elif ts == 67965:
                    continue
                elif ts == 67966:
                    rlc_bytes = 1218
                elif ts == 67975:
                    rlc_bytes = 1156


                assert (int(MAC_packet.find_value('New bytes')) + rlc_bytes >= last_buffer_bytes) ##guarantee no buffer lost
                ##there is new buffer at the same time
                if (int(MAC_packet.find_value('New bytes')) + rlc_bytes > last_buffer_bytes):
                    self.mac_buffer.append([ts, int(MAC_packet.find_value('New bytes')) + rlc_bytes - last_buffer_bytes])
                    
            ##mac buffer stays the same
            else:
                if ts == 67976:
                    continue
                if (ts in self.RLC_packets_dict):   ##if there is rlc packet sent
                    rlc_bytes = self.compute_rlc_bytes(ts) 
                    self.mac_buffer.append([ts, rlc_bytes])

            last_buffer_bytes = int(MAC_packet.find_value('New bytes')) 
                    
               
                    


    def load_2_buffer(self, pdcp_bytes):
        ##packet = self.PDCP_packets[pdcp_time]

        #assert pdcp_bytes <= self.mac_buffer[0][1]
        
        while pdcp_bytes > 0:
            if not self.mac_buffer:
                return None
            if pdcp_bytes > self.mac_buffer[0][1]:
                pdcp_bytes -= self.mac_buffer[0][1]
                self.mac_buffer.pop(0)
            else:
                ts = self.mac_buffer[0][0]

                self.mac_buffer[0][1] -= pdcp_bytes
                pdcp_bytes = 0

        if (self.mac_buffer[0][1] == 0):
            self.mac_buffer.pop(0)
        return ts

        
        
    def find_last_pusch(self, last_rlc_time):
        # timestamp = last_rlc_time
        # while PUSCH pkt exists at last_rlc_time:
        #    if NACK exists at timestamp + 4ms in PDCCH timestamps:
        #        timestamp += 4ms
        #    if ACK exists at timestamp + 4ms in PDCCH:
        #        return pusch_pkts[timestamp]
        
        ts = last_rlc_time
       
        while (ts in self.PUSCH_packets): # data pkt appears in pusch layer at ts
            if (ts + 4 in self.PDCCH_packets):
                
                pdcch_pkt = self.PDCCH_packets[ts + 4]
                response = pdcch_pkt.find_value("PHICH Value")
                
                # check ack/nack for pkt sent after 4ms
                if (response == "NACK"):
                    ts += 8 # expect pkt resent at ts + 8
                elif(response == "ACK"):

                    return ts
                else:
                    print("4ms after packet sent, there is a record but not NACK or ACK at " + str(ts+4))
                    return None
            else:
                print("4ms after packet sent, neither NACK nor ACK received at " + str(ts+4))
                return None
    
    
    def cal_header_length(self, k):
        if(k % 2 == 0):
            header = 1 + 1.5 * k
        else:
            header = 0.5 + 1.5 * k
        return int(header)


def main():
    RLC_packets, RLC_packets_dict, PDCP_packets, \
    PHY_PUSCH_time_stamps, PHY_PUSCH_packets, PHY_PDCCH_time_stamps, \
    PHY_PDCCH_packets, MAC_time_stamps, MAC_packets \
        = MobileInsightXmlToListConverter.convert_ul_xml_to_list("../logs/cr_ul_full.txt", last_mac_fn= 8564, cur_mac_fn= 8564)
    
    analyzer = UlTxLatencyAnalyzer()
    analyzer.RLC_packets = RLC_packets
    analyzer.RLC_packets_dict = RLC_packets_dict
    analyzer.PDCP_packets = PDCP_packets

    analyzer.PDCCH_packets = PHY_PDCCH_packets
    analyzer.PDCCH_times = PHY_PDCCH_time_stamps
    analyzer.MAC_packets = MAC_packets
    analyzer.MAC_times = MAC_time_stamps
    analyzer.PUSCH_packets = PHY_PUSCH_packets
    analyzer.PUSCH_times = PHY_PUSCH_time_stamps

    analyzer.analyze()

if __name__ == '__main__':
    main()
    
    
    



