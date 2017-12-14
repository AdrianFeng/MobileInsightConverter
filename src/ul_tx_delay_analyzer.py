#!/usr/bin/env python3
# Author: Zhonglin Zhang, Zhengxu Xia

import csv, sys

from dl_tx_delay_analyzer import mergeRLC
from log_parser import MobileInsightXmlToListConverter


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
        '''
        because each PDCP packet can be cut and recombined on RLC layer,
        we divide RLC packets into subpackets and merge those that were cut before
        to get PDCP packets from RLC logs and 
        generate a list of time stamp pair [start, end] for each PDCP packet
        start: the first RLC packet time corresponds to PDCP
        end: the last RLC packet time  
        '''
        mergedRLCPackets = mergeRLC(self.RLC_packets) # last arrived rlc timestamps
        
        end_timestamps = []
        for ts_pair in mergedRLCPackets:
            end_timestamps.append(self.find_last_pusch(ts_pair[1]))
        
        start_timestamps = []
        self.generate_buffer(self.MAC_packets)
        
        for pkt in self.PDCP_packets:
            
            pdcp_bytes = int(pkt.find_value('PDU Size'))

            start_timestamps.append(self.load_2_buffer(pdcp_bytes)) # pdcp layer

        print("Number of start timestamps: ", len(start_timestamps))

        print("Number of end timestamps: ", len(end_timestamps))
        
        total_delays = []
        mac_delays = []
        phy_delays = []

        print(len(start_timestamps))
        mergedRLCPackets = list(mergeRLC(self.RLC_packets))

        # export the delay data into a csv file
        with open('ul_full_delay.csv', 'w') as csvfile:
            dataWriter = csv.writer(csvfile, delimiter=',')
            dataWriter.writerow(['Total Delay', 'Mac Delay', 'Tx Delay'])
            for idx in range(len(start_timestamps)):
                start = start_timestamps[idx]   #the time when data first loaded to buffer
                end = end_timestamps[idx]       #the last pusch packet time 
                rlc_t = mergedRLCPackets[idx][0]  #begin to send the first rlc packet
                if (end == None or start == None):
                    continue
                dataWriter.writerow([end - start, rlc_t - start, end - rlc_t])

                total_delays.append(end - start)
                mac_delays.append(rlc_t - start)
                phy_delays.append(end - rlc_t)
                print("Load to Buffer: " + str(start) + " RLC Start: " + str(rlc_t) +  " End: " + str(end))
                print("Total Delay: " + str(end - start) + " MAC delay: " + str(rlc_t - start) + " Tx delay: " + str(end - rlc_t))

        avg_tl_delay = sum(total_delays) / len(total_delays)
        avg_mac_delay = sum(mac_delays) / len(mac_delays)
        avg_phy_delay = sum(phy_delays) / len(phy_delays)

        print("Average delay time: " + str(avg_tl_delay) + " ms")
        print("Average MAC delay time: " + str(avg_mac_delay) + " ms")
        print("Average Tx delay time: " + str(avg_phy_delay) + " ms")

    
    '''
    calculate the actual data size in the MAC buffer according to RLC PDU Bytes
    MAC size = RLC PDU Size - RLC header length
    '''
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


    '''
    simulate the packet transmission process on MAC layer with a Queue structure
    this function generate a list of pair [time, bytes]
    [time: the time stamp when new bytes are loaded into the buffer space 
    bytes: the new bytes from PDCP layer]
    the list in chronological order
    '''
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
                
                #specific cases
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

                ##some specific cases
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
                    
               
                    

    '''
    when there is a RLC packet sent, go to mac_buffer list to 
    get the corresponding data bytes from buffer and return the load time 
    '''
    def load_2_buffer(self, pdcp_bytes):
        
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
    
    '''
    calculate the header length in RLC packet
    if the RLC packet has the even number k of subpackets (LI):
        header length = 1 + 1.5 x k
    if has the odd number k:
        header length = 0.5 + 1.5 x k
    '''
    def cal_header_length(self, k):
        if(k % 2 == 0):
            header = 1 + 1.5 * k
        else:
            header = 0.5 + 1.5 * k
        return int(header)


def main():

    file_path = sys.argv[1]
    RLC_packets, RLC_packets_dict, PDCP_packets, \
    PHY_PUSCH_time_stamps, PHY_PUSCH_packets, PHY_PDCCH_time_stamps, \
    PHY_PDCCH_packets, MAC_time_stamps, MAC_packets \
        = MobileInsightXmlToListConverter.convert_ul_xml_to_list(ul_xml_file=file_path, last_mac_fn=8564, cur_mac_fn=8564)
    
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
    
    
    



