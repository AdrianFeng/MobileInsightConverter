# from collections import OrderedDict
import xml.etree.ElementTree as ET
# Author: Zhen Feng


class AtomPacket(object):
    def __init__(self, information_dict, time_stamp, packet_type):
        self.information_dict = information_dict
        self.time_stamp = time_stamp
        self.type = packet_type

    def find_value(self, key):
        return self.information_dict.get(key, None)

    def __str__(self):
        result = ["time_stamp", str(self.time_stamp), "type", str(self.type), "information", str(self.information_dict)]
        return " ".join(result)

    def __repr__(self):
        return self.__str__()


class MobileInsightXmlToListConverter(object):

    @staticmethod
    def convert_xmltree_to_dict(root, current_dict):
        """
        convert xml_element to dictionary where each value can be
        a pure value or a dict or list of dict
        example:
        <dm_log_packet>
            <pair key="log_msg_len">436</pair>
            <pair key="type_id">LTE_PHY_PDSCH_Stat_Indication</pair>
            <pair key="timestamp">2017-11-16 23:48:06.186771</pair>
            <pair key="Records" type="list">
                <list>
                    <item type="dict">
                        <dict>
                            <pair key="Subframe Num">6</pair>
                            <pair key="Frame Num">78</pair>
                            <pair key="Num RBs">3</pair>
                        </dict>
                    </item>
                </list>
            </pair>
        <dm_log_packet>
        dict:
        {   "log_msg_len":436,
            "type_id": "LTE_PHY_PDSCH_Stat_Indication",
            "timestamp": "2017-11-16 23:48:06.186771",
            "records": [{"Subframe":6, "Frame Num": 78, "Num RBs": 3}]
        }
        :param root: current xml root
        :param current_dict: the dictionary that current level
               xml elements will be added in
        :return: None
        """
        for child in root:
            if "type" in child.attrib and child.attrib["type"] == "list":
                list_result = []
                current_dict[child.attrib["key"]]=list_result
                list_of_elements = child[0]
                for element in list_of_elements:
                    if "type" in element.attrib and element.attrib["type"] == "dict":
                        dict_root = element[0]
                        new_dict = {}
                        MobileInsightXmlToListConverter.convert_xmltree_to_dict(dict_root, new_dict)
                    list_result.append(new_dict)
            else:
                current_dict[child.attrib["key"]] = child.text

    @staticmethod
    def print_dict(current_dict, number_space):
        """
        print value inside a dict
        :param current_dict: the dict that needs to be printed
        :param number_space: initial number of space before starting to print
        :return:
        """
        for key, value in current_dict.items():
            if isinstance(value, str):
                print("  "*number_space, key, value)
            else:
                print("  " * number_space, key, ":")
                for element in value:
                    MobileInsightXmlToListConverter.print_dict(element, number_space+1)

    @staticmethod
    def convert_dl_xml_to_list(dl_xml_file):
        """
        parse out list of packets from mobile insight log file
        :param xml_file: file that needs to be parsed
        :return:
        """
        tree = ET.parse(dl_xml_file)
        root = tree.getroot()

        RLC_packets, PHY_packets = [], {}
        RLC_counter, PHY_counter = 0, 0
        RLC_fn, PHY_fn = None, None

        for child in root:
            new_dict = {}
            MobileInsightXmlToListConverter.convert_xmltree_to_dict(child, new_dict)

            if "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_PDCP_DL_Cipher_Data_PDU":
                # subpackets = new_dict["Subpackets"]
                # for subpacket in subpackets:
                #     datas = subpacket["PDCPDL CIPH DATA"]
                #     for data in datas:
                #         sys_fn = int(data["Sys FN"])
                #         sub_fn = int(data["Sub FN"])
                #
                #         time_stamp = PDCP_counter * 10240 + sys_fn * 10 + sub_fn
                #
                #         if PDCP_fn and PDCP_fn > time_stamp:
                #             PDCP_counter += 1
                #             time_stamp += 10240
                #
                #         PDCP_fn = time_stamp
                #
                #         current_packet = AtomPacket(data, time_stamp, "PDCP")
                #
                #         current_list = PDCP_packets.get(time_stamp, [])
                #         current_list.append(current_packet)
                #
                #         PDCP_packets[time_stamp] = current_list
                pass

            elif "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_RLC_DL_AM_All_PDU":
                subpackets = new_dict["Subpackets"]
                for subpacket in subpackets:
                    datas = subpacket["RLCDL PDUs"]
                    for data in datas:

                        # only collect the actual data instead of control data
                        if data["PDU TYPE"] == "RLCDL DATA":
                            sys_fn = int(data["sys_fn"])
                            sub_fn = int(data["sub_fn"])
                            time_stamp = RLC_counter * 10240 + sys_fn * 10 + sub_fn

                            if RLC_fn and RLC_fn > time_stamp:
                                RLC_counter += 1
                                time_stamp += 10240
                            RLC_fn = time_stamp

                            current_packet = AtomPacket(data, time_stamp, "RLC")

                            # this is where number of LI is being added
                            if "RLC DATA LI" in data:
                                current_packet.information_dict["NUMBER OF LI"]\
                                    = len(data["RLC DATA LI"])

                            RLC_packets.append(current_packet)

            elif "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_PHY_PDSCH_Stat_Indication":
                records = new_dict["Records"]
                for record in records:
                    frame_num = int(record["Frame Num"])
                    subframe_num = int(record["Subframe Num"])

                    time_stamp = PHY_counter * 10240 + frame_num * 10 + subframe_num

                    if PHY_fn and PHY_fn > time_stamp:
                        PHY_counter += 1
                        time_stamp += 10240

                    PHY_fn = time_stamp

                    current_list = PHY_packets.get(time_stamp, [])
                    transport_blocks = record["Transport Blocks"]
                    for transport_block in transport_blocks:
                        current_packet = AtomPacket(transport_block, time_stamp,
                                                    "PHY")
                        current_list.append(current_packet)
                    PHY_packets[time_stamp] = current_list

            elif "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_MAC_DL_Transport_Block":
                pass
            else:
                print("packets cannot clarify, packets <%s - %s - %s> drops" % (
                    new_dict["timestamp"], new_dict["Version"],
                    new_dict["log_msg_len"]))

        PHY_time_stamps = list(PHY_packets.keys())
        PHY_time_stamps.sort(reverse=True)

        RLC_packets.sort(key=lambda packet: packet.time_stamp, reverse=True)

        # RLC packets is a list of packets sorted by time stamps in descending
        # order
        return RLC_packets, PHY_time_stamps, PHY_packets

    @staticmethod
    def convert_ul_xml_to_list(ul_xml_file, last_mac_fn = None, cur_mac_fn = None ):

        tree = ET.parse(ul_xml_file)
        root = tree.getroot()

        PDCP_packets, RLC_packets, PHY_PUSCH_packets, MAC_packets, PHY_PDCCH_packets = \
        {},           {},          {},          {},          {}

        PDCP_counter, RLC_counter, PHY_PUSCH_counter, MAC_counter, PHY_PDCCH_counter = \
        0,            0,           0,           0,           0

        PDCP_fn, RLC_fn, PHY_PUSCH_fn, MAC_fn, PHY_PDCCH_fn = \
        None,    None,   None,   None,   None

        for child in root:
            new_dict = {}
            MobileInsightXmlToListConverter.convert_xmltree_to_dict(child,
                                                                new_dict)

            if "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_PDCP_UL_Cipher_Data_PDU":
                subpackets = new_dict["Subpackets"]
                for subpacket in subpackets:
                    datas = subpacket["PDCPUL CIPH DATA"]
                    for data in datas:

                        sys_fn = int(data["Sys FN"])
                        sub_fn = int(data["Sub FN"])

                        time_stamp = PDCP_counter * 10240 + sys_fn*10 + sub_fn

                        if PDCP_fn and PDCP_fn > time_stamp:
                            PDCP_counter += 1
                            time_stamp += 10240
                        PDCP_fn = time_stamp

                        current_packet = AtomPacket(data, time_stamp, "PDCP")

                        current_list = PDCP_packets.get(time_stamp, [])
                        current_list.append(current_packet)

                        PDCP_packets[time_stamp] = current_list
            elif "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_PHY_PDCCH_PHICH_Indication_Report":
                    records = new_dict["Records"]
                    for record in records:
                        sys_fn = int(record["PDCCH Timing SFN"])
                        sub_fn = int(record["PDCCH Timing Sub-FN"])
                        time_stamp = PHY_PDCCH_counter * 10240 + sys_fn * 10 + sub_fn

                        if PHY_PDCCH_fn and PHY_PDCCH_fn > time_stamp:
                            PHY_PDCCH_counter += 1
                            time_stamp += 10240

                        PHY_PDCCH_fn = time_stamp

                        current_packet = AtomPacket(record, time_stamp, "PHY_PDCCH")
                        current_list = PHY_PDCCH_packets.get(time_stamp, [])
                        current_list.append(current_packet)
                        PHY_PDCCH_packets[time_stamp] = current_list

            elif "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_PHY_PUSCH_Tx_Report":
                records = new_dict["Records"]
                for record in records:
                    time_stamp = PHY_PUSCH_counter * 10240 + int(record["Current SFN SF"])
                    if PHY_PUSCH_fn and PHY_PUSCH_fn > time_stamp:
                        PHY_PUSCH_counter += 1
                        time_stamp += 10240
                    PHY_PUSCH_fn = time_stamp

                    current_packet = AtomPacket(record, time_stamp, "PHY_PUSCH")
                    current_list = PHY_PUSCH_packets.get(time_stamp, [])
                    current_list.append(current_packet)

                    PHY_PUSCH_packets[time_stamp] = current_list
            elif  "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_RLC_UL_AM_All_PDU":
                subpackets = new_dict["Subpackets"]
                for subpacket in subpackets:
                    datas = subpacket["RLCUL PDUs"]
                    for data in datas:
                        if data["PDU TYPE"] == "RLCUL DATA":

                            sys_fn = int(data["sys_fn"])
                            sub_fn = int(data["sub_fn"])

                            time_stamp = RLC_counter * 1024 + sys_fn * 10 + sub_fn

                            if RLC_fn and RLC_fn > time_stamp:
                                RLC_counter += 1
                                time_stamp += 1024

                            RLC_fn = time_stamp
                            current_packet = AtomPacket(data, time_stamp, "RLC")

                            if "RLC DATA LI" in data:
                                current_packet.information_dict["NUMBER OF LI"] \
                                    = len(data["RLC DATA LI"])

                            current_list = RLC_packets.get(time_stamp, [])
                            current_list.append(current_packet)

                            RLC_packets[time_stamp] = current_list
            elif "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_MAC_UL_Buffer_Status_Internal":
                subpackets = new_dict["Subpackets"]
                for subpacket in subpackets:
                    if "Samples" in subpacket:
                        samples = subpacket["Samples"]
                        for sample in samples:
                            sub_mac_fn = int(sample['Sub FN'])
                            sys_mac_fn = int(sample['Sys FN'])

                            time_stamp = None
                            if not MAC_fn:
                                MAC_fn = last_mac_fn
                                time_stamp = cur_mac_fn
                            elif sys_mac_fn <= 1023 and sub_mac_fn <= 9:
                                    time_stamp = MAC_counter * 10240 + \
                                                 sys_mac_fn * 10 + sub_mac_fn
                                    if MAC_fn and MAC_fn > time_stamp:
                                        MAC_counter +=1
                                        time_stamp += 10240
                                    MAC_fn = time_stamp
                            else:
                                time_stamp = MAC_fn + 1
                                MAC_fn = time_stamp

                            current_packet = AtomPacket(sample["LCIDs"][3], time_stamp, "MAC")

                            current_list = MAC_packets.get(time_stamp, [])
                            current_list.append(current_packet)

                            MAC_packets[time_stamp] = current_list

        PDCP_time_stamps = list(PDCP_packets.keys())
        RLC_time_stamps = list(RLC_packets.keys())
        PHY_PUSCH_time_stamps = list(PHY_PUSCH_packets.keys())
        MAC_time_stamps = list(MAC_packets.keys())
        PHY_PDCCH_time_stamps = list(PHY_PDCCH_packets.keys())

        PDCP_time_stamps.sort(reverse=True)
        RLC_time_stamps.sort(reverse=True)
        PHY_PDCCH_time_stamps.sort(reverse=True)
        MAC_time_stamps.sort(reverse=True)
        PHY_PUSCH_time_stamps.sort(reverse=True)

        return RLC_time_stamps, RLC_packets, PDCP_time_stamps, PDCP_packets, \
               PHY_PUSCH_time_stamps, PHY_PUSCH_packets, PHY_PDCCH_time_stamps, \
<<<<<<< HEAD
               PHY_PDCCH_packets, MAC_time_stamps, MAC_packets
=======
               PHY_PDCCH_packets, MAC_time_stamps, MAC_packets







>>>>>>> 06c7a18832c59d043917439d8f634747f09db3aa
