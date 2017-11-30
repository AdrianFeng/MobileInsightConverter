#!/usr/bin/env python3
# Author: Zhonglin Zhang, Zhengxu Xia

import os
from src.log_parser import MobileInsightXmlToListConverter


class UlTxLatencyAnalyzer(object):
    def __init__(self):
        self.total_delay = 0.0
        self.total_packets = 0
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

    def analyze(self):
        self.generate_buffer(self.MAC_packets)
        for ts in self.PDCP_times:
            for pdcp_packet in self.PDCP_packets[ts]:
                pdcp_bytes = pdcp_packet.find_value('PDU Size')
                ##PDCP_packet = self.PDCP_packets[ts] 
                ##start_time = self.load_2_buffer(PDCP_packet.find_value(time_stamp)) # pdcp layer
                ##last_rlc_time = self.find_last_rlc(PDCP_packet.find_value(time_stamp)) # rlc layer
                start_time = self.load_2_buffer(pdcp_bytes) # pdcp layer
                last_rlc_time = self.find_last_rlc(ts) # rlc layer
                end_time = self.find_last_pusch(last_rlc_time) # physical layer
                if(start_time > 0 and end_time > 0 and end_time > start_time):
                    delay_time = end_time - start_time
                    self.total_packets += 1
                    self.total_delay += delay_time
                    print("Delay Time: " + delay_time)
        av_delay = self.total_delay / self.total_packets
        print("Total packets: " + self.total_packets)
        print("Total delay time: " + self.total_delay)
        print("Average delay time: " + av_delay)

    

    def computer_rlc_bytes(self, ts):
        rlc_bytes = 0
        for subpacket in self.RLC_packets[ts]:
            if subpacket.find_value('RLC DATA LI'):
                LI_num = len(subpacket.find_value('RLC DATA LI')) + 1
                header_len = self.cal_header_length(LI_num)
            else:
                header_len = self.cal_header_length(1)
            rlc_bytes += (subpacket.find_value('pdu_bytes') - header_len)
        return rlc_bytes



    def generate_buffer(self, MAC_packets):
        last_buffer_bytes = 0
        rlc_bytes = 0
        LI_num = 0
        header_len = 0
        
        for ts in self.MAC_times:
            MAC_packet = self.MAC_packets[ts]
            
            ##if mac buffer become larger, 
            
            if (MAC_packet.find_value('New_bytes') > last_buffer_bytes): # new pdcp pkts coming in for sure
                if (ts in self.RLC_packets):
                    rlc_bytes = self.computer_rlc_bytes(ts) 
                    self.mac_buffer.append([ts, MAC_packet.find_value('New_bytes') - last_buffer_bytes + rlc_bytes])
                else:
                    self.mac_buffer.append([ts, MAC_packet.find_value('New_bytes') - last_buffer_bytes])
                    
            ##if mac buffer become smaller,
            ##means there are rlc packets sent
            elif (MAC_packet.find_value('New_bytes') < last_buffer_bytes):
                assert (ts in self.RLC_packets) ##gurantee there is rlc packet
                rlc_bytes = self.computer_rlc_bytes(ts)
                assert (MAC_packet.find_value('New_bytes') + rlc_bytes >= last_buffer_bytes) ##guarantee no buffer lost
                ##there is new buffer at the same time
                if (MAC_packet.find_value('New_bytes') + rlc_bytes > last_buffer_bytes):
                    self.mac_buffer.append([ts, MAC_packet.find_value('New_bytes') + rlc_bytes - last_buffer_bytes])
                    
            ##mac buffer stays the same
            else:
                if (ts in self.RLC_packets):   ##if there is rlc packet sent
                    rlc_bytes = self.computer_rlc_bytes(ts) 
                    self.mac_buffer.append([ts, rlc_bytes])
                    
               
                    


    def load_2_buffer(self, pdcp_bytes):
        ##packet = self.PDCP_packets[pdcp_time]
        assert pdcp_bytes <= self.mac_buffer[0][1]
        ts = self.mac_buffer[0][0]
        self.mac_buffer[0][1] -= pdcp_bytes
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

def main():
    RLC_time_stamps, RLC_packets, PDCP_time_stamps, PDCP_packets, \
    PHY_PUSCH_time_stamps, PHY_PUSCH_packets, PHY_PDCCH_time_stamps, \
    PHY_PDCCH_packets, MAC_time_stamps, MAC_packets \
        = MobileInsightXmlToListConverter.convert_ul_xml_to_list("../logs/cr_ul_unit.txt", last_mac_fn= 8564, cur_mac_fn= 8564)
    analyzer = UlTxLatencyAnalyzer()
    analyzer.RLC_packets = RLC_packets
    analyzer.RLC_times = RLC_time_stamps
    analyzer.PDCP_packets = PDCP_packets
    analyzer.PDCP_times = PDCP_time_stamps
    analyzer.PDCCH_packets = PHY_PDCCH_packets
    analyzer.PDCCH_times = PHY_PDCCH_time_stamps
    analyzer.MAC_packets = MAC_packets
    analyzer.MAC_times = MAC_time_stamps
    analyzer.PUSCH_packets = PHY_PUSCH_packets
    analyzer.PUSCH_times = PHY_PUSCH_time_stamps


    analyzer.analyze()

    if __name__ == '__main__':
        main()
    
    
    



