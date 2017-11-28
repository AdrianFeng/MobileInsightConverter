##supercode
##ul_tx_latency_analyzer

for each PDCP packet p:
	start_time = find_load_2_buffer(p.time_stamp, p.bytes)
	last_rlc_packet = find_last_rlc_packet(p.time_stamp)
    end_time = find_last_PUSCH(last_rlc_packet.time_stamp)
    return start_time - end_time

__all__ = ["UlTxLatencyAnalyzer"]

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from kpi_analyzer import KpiAnalyzer

class UlTxLatencyAnalyzer(KpiAnalyzer):
    """
    An KPI analyzer to monitor and manage uplink latency 
    """
    def __init__(self):
        KpiAnalyzer.__init__(self)

        self.add_source_callback(self.__msg_callback)
        self.last_bytes = {} # 
        self.buffer = {} # 

        self.cur_pdcp_fn = None # Record current [sys_fn, sub_fn] for analyzer
        self.last_pdcp_fn = None
        self.time_pdcp_counter = 0
        self.time_to_analyse = []

        self.cur_mac_fn = None
        self.last_mac_fn = None
        self.time_mac_counter = 0
        self.mac_new_buffer = []
        self.last_buffer = [0, 0] ##[time, bytes]
        self.cur_buffer = []

        self.cur_pdcch_fn = None
        self.last_pdcch_fn = None
        self.time_pdcch_counter = 0

        self.cur_pusch_fn = None
        self.last_pusch_fn = None
        self.time_pusch_counter = 0

        self.cur_rlc_fn = None
        self.last_rlc_fn = None
        self.time_rlc_counter = 0

        self.pdcp_ul_msg = {}
        self.rlc_ul_msg = {}
        self.mac_ul_msg = {}
        self.pdcch_ul_msg = {}
        self.pusch_ul_msg = {}

    def set_source(self, source):
        """
        Set the trace source. Enable the cellular signaling messages

        :param source: the trace source (collector).
        """
        KpiAnalyzer.set_source(self, source)

        # Phy-layer logs
        source.enable_log("LTE_PHY_PUSCH_Tx_Report")
        source.enable_log("LTE_MAC_UL_Buffer_Status_Internal")
        source.enable_log("LTE_PDCCH_PHICH_Indication_Report")
        source.enable_log("LTE_PDCP_UL_Cipher_Data_PDU")
        source.enable_log("LTE_RLC_UL_AM_All_PDU")

    # def __del_lat_stat(self):
    #     """
    #     Delete one lat_buffer after it is matched with rlc packet
    #     :return:
    #     """
    #     del self.lat_stat[0]

    def __msg_callback(self, msg):

        if msg.type_id == "LTE_PDCP_UL_Cipher_Data_PDU":
            log_item = msg.data.decode()
            if 'Subpackets' in log_item:
                for i in range(0, len(log_item['Subpackets'])):
                	sub_pdcp_fn = int(log_item['Subpackets'][i]['Sub FN'])
                	sys_pdcp_fn = int(log_item['Subpackets'][i]['Sys FN'])
                	cur_pdcp_fn = sys_pdcp_fn * 10 + sub_pdcp_fn + time_pdcp_counter * 10240
                	if (last_pdcp_fn and last_pdcp_fn > cur_pdcp_fn):
                		time_pdcp_counter ++
                		cur_pdcp_fn += 10240
                	last_pdcp_fn = cur_pdcp_fn
                	time_to_analyse.append(cur_pdcp_fn)
                	if cur_pdcp_fn not in pdcp_ul_msg:
                		pdcp_ul_msg[cur_pdcp_fn] = log_item['Subpackets'][i]
                	else:
                		pdcp_ul_msg[cur_pdcp_fn].append(log_item['Subpackets'][i])
            for p_time in time_to_analyse:
            	if(cur_mac_fn >= p_time and cur_rlc_fn >= p_time and ):


        if msg.type_id == "LTE_MAC_UL_Buffer_Status_Internal":
            log_item = msg.data.decode()
            if 'Subpackets' in log_item:
                for i in range(0, len(log_item['Subpackets'])):
                	if 'Samples' in log_item['Subpackets'][i]:
                		for sample in log_item['Subpackets'][i]['Samples']:
		                	sub_mac_fn = int(sample['Sub FN'])
		                	sys_mac_fn = int(sample['Sys FN'])
		                	if (sys_mac_fn <= 1023 and sub_mac_fn <= 9):
			                	cur_mac_fn = sys_mac_fn * 10 + sub_mac_fn + time_mac_counter * 10240
			                	if (last_mac_fn and last_mac_fn > cur_mac_fn):
			                		time_mac_counter ++
			                		cur_mac_fn += 10240
			                	last_mac_fn = cur_mac_fn
		                		mac_ul_msg[cur_mac_fn] = sample['LCIDs'][3]
		                	elif not mac_ul_msg:
		                		last_mac_fn = 8564
		                		cur_mac_fn = 8564
		                		mac_ul_msg[cur_mac_fn] = sample['LCIDs'][3]
		                	else:
		                		cur_mac_fn = last_mac_fn + 1
		                		last_mac_fn = cur_mac_fn
		                		mac_ul_msg[cur_mac_fn] = sample['LCIDs'][3]
		                	cur_buffer = [cur_mac_fn, sample['LCIDs'][3][]]  ###!!!!!		         
	                		if cur_buffer[1] > last_buffer[1]:
	                			mac_new_buffer.append([cur_buffer[0], cur_buffer[1]-last_buffer[1]])
	                		last_buffer = cur_buffer



		if msg.type_id == "LTE_PDCCH_PHICH_Indication_Report":
			log_item = msg.data.decode()
            if 'Records' in log_item:
            	for i in range(0, len(log_item['Records'])):
                    sys_pdcch_fn = int(log_item['Records'][i]['PDCCH Timing SFN'])
                	sub_pdcch_fn = int(log_item['Subpackets'][i]['PDCCH Timing Sub-FN'])
                	cur_pdcch_fn = sys_pdcch_fn * 10 + sub_pdcch_fn + time_pdcch_counter * 10240
                	if (last_pdcch_fn and last_pdcch_fn > cur_pdcch_fn):
                		time_pdcch_counter ++
                		cur_pdcch_fn += 10240
                	last_pdcch_fn = cur_pdcch_fn
                	if cur_pdcch_fn not in pdcch_ul_msg:
                		pdcch_ul_msg[cur_pdcch_fn] = log_item['Records'][i]
                	else:
                		pdcch_ul_msg[cur_pdcch_fn].append(log_item['Records'][i])

        if msg.type_id == "LTE_PHY_PUSCH_Tx_Report":
			log_item = msg.data.decode()
            if 'Records' in log_item:
            	for i in range(0, len(log_item['Records'])):
                	cur_pusch_fn = int(log_item['Records'][i]['Current SFN SF']) + time_pusch_counter * 10240
                	if (last_pusch_fn and last_pusch_fn > cur_pusch_fn):
                		time_pusch_counter ++
                		cur_pusch_fn += 10240
                	last_pusch_fn = cur_pusch_fn
                	if cur_pusch_fn not in pusch_ul_msg:
                		pusch_ul_msg[cur_pusch_fn] = log_item['Records'][i]
                	else:
                		pusch_ul_msg[cur_pusch_fn].append(log_item['Records'][i])

        if msg.type_id == "LTE_RLC_UL_AM_All_PDU":
			log_item = msg.data.decode()
            if 'Subpackets' in log_item:
                for i in range(0, len(log_item['Subpackets'])):
                	if 'RLCUL PDUs' in log_item['Subpackets'][i]:
                		for sample in log_item['Subpackets'][i]['RLCUL PDUs']:
                			if sample['PDU TYPE'] == 'RLCUL DATA':
                				sub_rlc_fn = int(sample['sub_fn'])
                				sys_rlc_fn = int(sample['sys_fn'])
			                	if (sys_rlc_fn <= 1023 and sub_rlc_fn <= 9):
				                	cur_rlc_fn = sys_rlc_fn * 10 + sub_rlc_fn + time_rlc_counter * 10240
				                	if (last_rlc_fn and last_rlc_fn > cur_rlc_fn):
				                		time_rlc_counter ++
				                		cur_rlc_fn += 10240
				                	last_rlc_fn = cur_rlc_fn
				                if 'RLC DATA LI' in sample:
				                	if cur_rlc_fn not in rlc_ul_msg:
				                		rlc_ul_msg[cur_rlc_fn] = [len(sample['RLC DATA LI'])+1, sample]
				                	else:
				                		rlc_ul_msg[cur_rlc_fn].append([len(sample['RLC DATA LI'])+1, sample])
				                else:
				                	if cur_rlc_fn not in rlc_ul_msg:
				                		rlc_ul_msg[cur_rlc_fn] = [1, sample]
				                	else:
				                		rlc_ul_msg[cur_rlc_fn].append([1, sample])








                    if 'Samples' in log_item['Subpackets'][i]:
                        # print log_item
                        for sample in log_item['Subpackets'][i]['Samples']:
                            sub_fn = int(sample['Sub FN'])
                            sys_fn = int(sample['Sys FN'])
                            # Incorrect sys_fn and sub_fn are normally 1023 and 15
                            if not (sys_fn >= 1023 and sub_fn >= 9): # if the sys_fn and sub_fn are valid, update
                                if self.cur_fn:
                                    # reset historical data if time lag is bigger than 2ms
                                    lag = sys_fn * 10 + sub_fn - self.cur_fn[0] * 10 - self.cur_fn[1]
                                    if lag > 2 or -10238 < lag < 0:

                                        self.last_bytes = {}
                                        self.buffer = {}
                                        self.ctrl_pkt_sfn = {}
                                self.cur_fn = [sys_fn, sub_fn]
                            elif self.cur_fn: # if invalid and inited, add current sfn
                                self.cur_fn[1] += 1
                                if self.cur_fn[1] == 10:
                                    self.cur_fn[1] = 0
                                    self.cur_fn[0] += 1
                                if self.cur_fn[0] == 1024:
                                    self.cur_fn = [0, 0]
                            if not self.cur_fn:
                                break

                            for lcid in sample['LCIDs']:
                                idx = lcid['Ld Id']
                                #FIXME: Are these initializations valid?
                                if 'New Compressed Bytes' not in lcid:
                                    if 'New bytes' not in lcid:
                                        new_bytes = 0
                                    else:
                                        new_bytes = int(lcid['New bytes'])
                                else:
                                    new_bytes = int(lcid['New Compressed Bytes'])
                                ctrl_bytes = 0 if 'Ctrl bytes' not in lcid else int(lcid['Ctrl bytes'])
                                total_bytes = new_bytes + ctrl_bytes if 'Total Bytes' not in lcid else int(lcid['Total Bytes'])

                                # print 'total:', total_bytes

                                if idx not in self.buffer:
                                    self.buffer[idx] = []
                                if idx not in self.last_bytes:
                                    self.last_bytes[idx] = 0
                                if idx not in self.ctrl_pkt_sfn:
                                    self.ctrl_pkt_sfn[idx] = None

                                # add new packet to buffer
                                if not new_bytes == 0:
                                    # TODO: Need a better way to decided if it is a new packet or left packet
                                    if new_bytes > self.last_bytes[idx]:
                                        new_bytes = new_bytes - self.last_bytes[idx]
                                        self.buffer[idx].append([(self.cur_fn[0], self.cur_fn[1]), new_bytes])

                                if not ctrl_bytes == 0:
                                    total_bytes -= 2
                                    if not self.ctrl_pkt_sfn[idx]:
                                        self.ctrl_pkt_sfn[idx] = (self.cur_fn[0], self.cur_fn[1])
                                else:
                                    if self.ctrl_pkt_sfn[idx]:
                                        ctrl_pkt_delay = self.cur_fn[0] * 10 + self.cur_fn[1] \
                                                         - self.ctrl_pkt_sfn[idx][0] * 10 - self.ctrl_pkt_sfn[idx][1]
                                        ctrl_pkt_delay += 10240 if ctrl_pkt_delay < 0 else 0
                                        self.ctrl_pkt_sfn[idx] = None
                                        # self.log_info(str(log_item['timestamp']) + " UL_CTRL_PKT_DELAY: " + str(ctrl_pkt_delay))
                                        
                                        bcast_dict = {}
                                        bcast_dict['timestamp'] = str(log_item['timestamp'])
                                        bcast_dict['delay'] = str(ctrl_pkt_delay)
                                        self.broadcast_info("UL_CTRL_PKT_DELAY", bcast_dict)

                                if self.last_bytes[idx] > total_bytes:
                                    sent_bytes = self.last_bytes[idx] - total_bytes
                                    while len(self.buffer[idx]) > 0 and sent_bytes > 0:
                                        pkt = self.buffer[idx][0]
                                        if pkt[1] <= sent_bytes:
                                            pkt_delay = self.cur_fn[0] * 10 + self.cur_fn[1] \
                                                             - pkt[0][0] * 10 - pkt[0][1]
                                            pkt_delay += 10240 if pkt_delay < 0 else 0
                                            self.buffer[idx].pop(0)
                                            sent_bytes -= pkt[1]
                                            self.lat_stat.append((log_item['timestamp'], \
                                                                 self.cur_fn[0], self.cur_fn[1], pkt[1], pkt_delay))
                                            # self.log_info(str(log_item['timestamp']) + " UL_PKT_DELAY: " + str(pkt_delay))
                                            bcast_dict = {}
                                            bcast_dict['timestamp'] = str(log_item['timestamp'])
                                            bcast_dict['delay'] = str(pkt_delay)
                                            self.broadcast_info("UL_PKT_DELAY", bcast_dict)
                                        else:
                                            pkt[1] -= sent_bytes
                                self.last_bytes[idx] = total_bytes

                            self.queue_length = sum(self.last_bytes.values()) 

# def find_load_2_buffer(p_time, p_bytes):
# 	if mac_buffer[0][1] >= p_bytes: 
# 		mac_buffer[0][1] -= p_bytes

# 		return mac_buffer[0][0] ##mac_buffer[time, bytes] stores the logs loaded into the buffer
# 	else 

