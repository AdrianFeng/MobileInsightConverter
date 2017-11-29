#!/usr/bin/env python3
# author: Zhonglin Zhang, Zhengxu Xia

import os
from src.log_parser import MobileInsightXmlToListConverter

generate_buffer(MAC_packets)
for PDCP_packet in self.PDCP_packets: 
    start_time = load_2_buffer(PDCP_packet.time_stamp) # pdcp layer
    last_rlc_time = find_last_rlc(PDCP_packet.time_stamp) # rlc layer
    end_time = find_last_pusch(last_rlc_time) # physical layer
    return end_time - start_time

class UlTxLatencyAnalyzer(object):
    def __init__(self):
        self.PDCP_packets = {}
        self.RLC_packets = {}
        self.MAC_packets = {}
        self.PDCCH_packets = {}
        self.PUSCH_packets = {}
        self.PDCP_times = []
        self.RLC_times = []
        self.MAC_times = []
        self.PDCCH_times = []
        self.PUSCH_times = []
        self.mac_buffer = []
    

    def computer_rlc_bytes(self, ts):
        rlc_bytes = 0
        for subpacket in self.RLC_packets[ts]:
            if ('LI' in subpacket):
                LI_num = len(subpacket['LI']) + 1
                header_len = cal_header_length(LI_num)
            else:
                header_len = cal_header_length(1)
                rlc_bytes += (subpacket[bytes] - header_len)
        return rlc_bytes



    def generate_buffer(self, MAC_packets):
        last_buffer_bytes = 0
        rlc_bytes = 0
        LI_num = 0
        header_len = 0
        
        for ts in self.MAC_times:
            MAC_packet = self.MAC_packets[ts]
            
            ##if mac buffer become larger, 
            
            if (MAC_packet[bytes] > last_buffer_bytes): # new pdcp pkts coming in for sure
                if (ts in self.RLC_packets):
                    rlc_bytes = computer_rlc_bytes(ts) 
                    self.mac_buffer.append([ts, MAC_packet[bytes] - last_buffer_bytes + rlc_bytes])
                else:
                    self.mac_buffer.append([ts, MAC_packet[bytes] - last_buffer_bytes])
                    
            ##if mac buffer become smaller,
            ##means there are rlc packets sent
            elif (MAC_packet[bytes] < last_buffer_bytes):
                assert (ts in self.RLC_packets) ##gurantee there is rlc packet
                rlc_bytes = computer_rlc_bytes(ts)
                assert (MAC_packet[bytes] + rlc_bytes >= last_buffer_bytes) ##guarantee no buffer lost
                ##there is new buffer at the same time
                if (MAC_packet[bytes] + rlc_bytes > last_buffer_bytes):
                    self.mac_buffer.append([ts, MAC_packets[bytes] + rlc_bytes - last_buffer_bytes])
                    
            ##mac buffer stays the same
            else:
                if (ts in self.RLC_packets):   ##if there is rlc packet sent
                    rlc_bytes = computer_rlc_bytes(ts) 
                    self.mac_buffer.append([ts, rlc_bytes])
                    
               
                    


    def load_2_buffer(self, pdcp_time):
        packet = self.PDCP_packets[pdcp_time]
        assert packet['bytes'] <= self.mac_buffer[0][1]
        ts = self.mac_buffer[0][0]
        self.mac_buffer[0][1] -= packet['bytes']
        if (self.mac_buffer[0][1] == 0):
            self.mac_buffer.pop(0)
        return ts
    
    
    def find_last_rlc(self, pdcp_time):
        #first_rlc_pkt = self.RLC_packets[pdcp_time]
        
    def find_last_pusch(self, last_rlc_time):
        # timestamp = last_rlc_time
        # while PUSCH pkt exists at last_rlc_time:
        #    if NACK exists at timestamp + 4ms in PDCCH timestamps:
        #        timestamp += 4ms
        #    if ACK exists at timestamp + 4ms in PDCCH:
        #        return pusch_pkts[timestamp]
        
        ts = last_rlc_time
       
        while (ts in self.PUSCH_packets): # data pkt appears in pusch layer at ts
            if (ts + 4 in self.PDCCH_pacekts):
                
                pdcch_pkt = self.PDCCH_pacekts[ts + 4]
                records = pdcch_pkt.find_value("Records")
                response = records["PHICH Value"]
                
                # check ack/nack for pkt sent after 4ms
                if (response eq "NACK"):
                    ts += 8 # expect pkt resent at ts + 8
                elif(response eq "ACK"):
                    return ts
                else:
                    print("4ms after packet sent, there is a record but not NACK or ACK.")
            else:
                print("4ms after packet sent, neither NACK nor ACK received.")
    
    
    def cal_header_length(k):
        if(k % 2 == 0):
            header = 1 + 1.5 * k
        else:
            header = 0.5 + 1.5 * k
        return header 
