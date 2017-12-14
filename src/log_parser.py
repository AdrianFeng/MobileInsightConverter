#!/usr/bin/env python3
# Author: Zhen Feng

import xml.etree.ElementTree as ET


class AtomPacket(object):
    def __init__(self, information_dict, time_stamp, packet_type):

        # the dictionary that contains all the recorded information about
        # this packet
        self.information_dict = information_dict

        # this is not the real time stamp, it is combination of
        # sub_frame number and frame number
        # if want to access real time stamp considering using
        # find_value("real_time")
        self.time_stamp = time_stamp

        # this defines the packet's type
        # it can be RLC , PHY, PDCP
        self.type = packet_type

    def find_value(self, key):
        """
        find the value of this packets given a key
        :param key:
        :return:
        """
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
        parse out list of packets from mobile insight down-link log file
        please see _dl_list_reorder to know how each packet is order in
        the corresponding list

        :param dl_xml_file: file that needs to be parsed
        :return: ordered RLC packets list, ordered PHY packets list , and ordered
                PDCP packets list
        """
        tree = ET.parse(dl_xml_file)
        root = tree.getroot()

        RLC_packets, PHY_packets, PDCP_packets = [], [], []
        RLC_counter, PHY_counter = -1, 0
        RLC_fn, PHY_fn = None, None
        RLC_packets_SN_set = set()

        for child in root:
            new_dict = {}
            MobileInsightXmlToListConverter.convert_xmltree_to_dict(child, new_dict)

            if "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_PDCP_DL_Cipher_Data_PDU":
                pass

            elif "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_MAC_DL_Transport_Block":
                pass

            elif "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_RLC_DL_AM_All_PDU":
                real_time = new_dict["timestamp"][-12:]
                subpackets = new_dict["Subpackets"]

                for subpacket in subpackets:

                    datas = subpacket["RLCDL PDUs"]
                    subpackets_list = []

                    for data in datas:

                        # only collect the actual data instead of control data
                        if data["PDU TYPE"] == "RLCDL DATA" and data["rb_cfg_idx"] != "33":

                            if RLC_counter == -1:
                                RLC_counter = max(PHY_counter, RLC_counter)

                            sys_fn = int(data["sys_fn"])
                            sub_fn = int(data["sub_fn"])
                            time_stamp = RLC_counter * 10240 + sys_fn * 10 + sub_fn

                            if RLC_fn and RLC_fn > time_stamp:
                                RLC_counter += 1
                                time_stamp += 10240

                            RLC_fn = time_stamp

                            current_packet = AtomPacket(data, time_stamp, "RLC")

                            # add real time stamp
                            current_packet.information_dict["real_time"] = real_time
                            # get the SN
                            current_SN = int(current_packet.information_dict["SN"])

                            # check if SN already exist since a same RLC packet
                            # can be sent multiple times

                            if current_SN in RLC_packets_SN_set:
                                print("RLC real time ", real_time, " time stamp ", time_stamp , "SN", current_SN)
                                continue

                            RLC_packets_SN_set.add(current_SN)

                            current_packet.information_dict["SN"] = current_SN

                            # this is where number of LI is being added
                            if "RLC DATA LI" in data:
                                current_packet.information_dict["LI"]\
                                    = len(data["RLC DATA LI"])
                            else:
                                current_packet.information_dict["LI"] = 0
                            subpackets_list.append(current_packet)

                    RLC_packets.append(subpackets_list)

            elif "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_PHY_PDSCH_Stat_Indication":

                # get the last 12 digits of time stamp since that is enough
                real_time = new_dict["timestamp"][-12:]
                records = new_dict["Records"]

                for record in records:

                    frame_num = int(record["Frame Num"])
                    subframe_num = int(record["Subframe Num"])
                    time_stamp = PHY_counter * 10240 + frame_num * 10 + subframe_num

                    if PHY_fn and PHY_fn > time_stamp:
                        PHY_counter += 1
                        time_stamp += 10240

                    PHY_fn = time_stamp

                    transport_blocks = record["Transport Blocks"]
                    for transport_block in transport_blocks:
                        current_packet = AtomPacket(transport_block, time_stamp,
                                                    "PHY")
                        current_packet.information_dict["real_time"] = real_time
                        PHY_packets.append(current_packet)

            else:
                print("packets cannot clarify, packets <%s - %s - %s> drops" % (
                    new_dict["timestamp"], new_dict["Version"],
                    new_dict["log_msg_len"]))

        RLC_packets, PHY_packets, PDCP_packets \
            = MobileInsightXmlToListConverter.\
            _dl_list_reorder(RLC_packets=RLC_packets, PHY_packets=PHY_packets)

        return RLC_packets, PHY_packets

    @staticmethod
    def _dl_list_reorder(RLC_packets = None, PHY_packets= None , PDCP_packets = None):
        """

        new_RLC_packets will be in ascending order by its sequence number
        new_PHY_packets will be in descending order by its time_stamp (noted,
        this is not real time stamp)

        :param RLC_packets:
        :param PHY_packets:
        :param PDCP_packets:
        :return: new_RLC_packets, new_PHY_packets, new_PDCP_packets
        """
        new_RLC_packets, new_PHY_packets, new_PDCP_packets = [], [], []
        if RLC_packets:
            counter, prev_start = 0, None
            for sub_list in RLC_packets:
                max_SN, min_SN = float("-inf"), float("inf")

                if not sub_list:
                    continue

                for packet in sub_list:
                    max_SN = max(packet.find_value("SN"), max_SN)
                    min_SN = min(packet.find_value("SN"), min_SN)

                if 0 <= max_SN - min_SN <= 1000:

                    for packet in sub_list:
                        packet.information_dict["SN"] = packet.find_value(
                            "SN") + counter * 1024
                        new_RLC_packets.append(packet)
                else:

                    sub_list.sort(key=lambda packet: packet.find_value("SN"),
                                  reverse=True)
                    prev_SN = None

                    for packet in sub_list:
                        current_SN = packet.find_value("SN") + counter * 1024
                        if prev_SN and prev_SN - current_SN >= 1000:
                            counter += 1
                            current_SN += 1024
                        packet.information_dict["SN"] = current_SN

                        new_RLC_packets.append(packet)
                        prev_SN = current_SN

            new_RLC_packets.sort(key=lambda packet: packet.find_value("SN"),
                                 reverse=False)
        if PHY_packets:

            new_PHY_packets = sorted(PHY_packets, key=lambda packet: packet.time_stamp, reverse=True)

        if PDCP_packets:
            pass

        return new_RLC_packets, new_PHY_packets, new_PDCP_packets

    @staticmethod
    def convert_ul_xml_to_list(ul_xml_file, last_mac_fn=None, cur_mac_fn=None):
        """
        Function that will parse packets xml file and return each layers packets
        as a dictionary where key is time_stamp and value is AtomPacket contains
        information about that packet. Then time_stamp will separately stored in
        a list and that list will be sorted in ascending order

        :param ul_xml_file:
        :param last_mac_fn: start mac_fn, this may be useful
        :param cur_mac_fn:
        :return: each layer's time_stamp_packet_dict and list_of_time_stamp
        """

        tree = ET.parse(ul_xml_file)
        root = tree.getroot()

        PDCP_packets, RLC_packets, RLC_packets_dict, PHY_PUSCH_packets, MAC_packets, PHY_PDCCH_packets = \
        [],           [],          {},       {},          {},          {}

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

                        PDCP_packets.append(current_packet)

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
                        PHY_PDCCH_packets[time_stamp] = current_packet

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

                    PHY_PUSCH_packets[time_stamp] = current_packet
            elif  "type_id" in new_dict and new_dict[
                "type_id"] == "LTE_RLC_UL_AM_All_PDU":
                subpackets = new_dict["Subpackets"]
                for subpacket in subpackets:
                    datas = subpacket["RLCUL PDUs"]
                    for data in datas:
                        if data["PDU TYPE"] == "RLCUL DATA":
                            sys_fn = int(data["sys_fn"])
                            sub_fn = int(data["sub_fn"])

                            time_stamp = RLC_counter * 10240 + sys_fn * 10 + sub_fn

                            if RLC_fn and RLC_fn > (time_stamp + 900):
                                RLC_counter += 1
                                time_stamp += 10240

                            RLC_fn = time_stamp
                            current_packet = AtomPacket(data, time_stamp, "RLC")

                            if "RLC DATA LI" in data:
                                current_packet.information_dict["LI"]\
                                    = len(data["RLC DATA LI"])
                            else:
                                current_packet.information_dict["LI"] = 0

                            RLC_packets.append(current_packet)
                            current_list = RLC_packets_dict.get(time_stamp, [])
                            current_list.append(current_packet)

                            RLC_packets_dict[time_stamp] = current_list

                            
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

                            if int(sample["LCIDs"][0]["New bytes"]) > 0:
                                current_packet = AtomPacket(sample["LCIDs"][0], time_stamp, "MAC")
                            elif int(sample["LCIDs"][1]["New bytes"]) > 0:
                                current_packet = AtomPacket(sample["LCIDs"][1], time_stamp, "MAC")
                            elif int(sample["LCIDs"][2]["New bytes"]) > 0:
                                current_packet = AtomPacket(sample["LCIDs"][2], time_stamp, "MAC")
                            else:
                                current_packet = AtomPacket(sample["LCIDs"][3], time_stamp, "MAC")

                            MAC_packets[time_stamp] = current_packet



        PHY_PUSCH_time_stamps = list(PHY_PUSCH_packets.keys())
        MAC_time_stamps = list(MAC_packets.keys())
        PHY_PDCCH_time_stamps = list(PHY_PDCCH_packets.keys())

        PHY_PDCCH_time_stamps.sort(reverse=True)
        MAC_time_stamps.sort(reverse=False)
        PHY_PUSCH_time_stamps.sort(reverse=True)

        return RLC_packets, RLC_packets_dict, PDCP_packets, \
               PHY_PUSCH_time_stamps, PHY_PUSCH_packets, PHY_PDCCH_time_stamps,\
               PHY_PDCCH_packets, MAC_time_stamps, MAC_packets


if __name__ == "__main__":
    RLC_packets, PHY_packets \
        = MobileInsightXmlToListConverter.convert_dl_xml_to_list("../logs/cr5.txt")

    for packet in RLC_packets:
        print(packet.time_stamp, packet.find_value("SN"))








